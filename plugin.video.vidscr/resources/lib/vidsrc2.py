# -*- coding: utf-8 -*-
"""Secondary provider — vidsrc.xyz / vidsrc.to / 2embed mirror.

This provider produces a list of *candidate* streams in the same shape used by
``vidsrc.py`` so callers can pick / play them transparently.

Strategy:
  1. Build the embed URL for the chosen secondary host.
  2. Pull every iframe / source link we can find (these mirrors typically
     proxy other providers like cloudnestra, streamwish, filemoon, vidplay).
  3. Optionally hand off to ResolveURL — most of these hosts have community
     resolvers maintained inside the resolveurl module.
"""
import re
import requests

from .common import get_setting, get_setting_bool, log

TIMEOUT = 20
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# Hosts the user can choose from in settings (and that the auto-fallback /
# multi-link aggregator iterates through). Each host family has a URL
# template pair below in `_build_embed_url`.
KNOWN_HOSTS = (
    'vidsrc.xyz', 'vidsrc.to', 'vidsrc.net', 'vidsrc.cc',
    '2embed.cc', '2embed.skin',
    'multiembed.mov', 'autoembed.cc', 'embed.su',
    'moviesapi.club', 'smashystream.com',
)


def _host():
    h = (get_setting('secondary_source_host', 'vidsrc.xyz') or 'vidsrc.xyz').strip().rstrip('/')
    if h.startswith('http'):
        h = re.sub(r'^https?://', '', h)
    return h or 'vidsrc.xyz'


def _session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': UA,
        'Accept-Language': 'en-GB,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    return s


def _build_embed_url(host, media_type, tmdb_id, season=None, episode=None, imdb_id=None):
    ident = imdb_id or tmdb_id
    s, e = season or 1, episode or 1

    # vidsrc.xyz / vidsrc.to / vidsrc.net / vidsrc.cc — share routing scheme.
    if host.startswith('vidsrc.'):
        if media_type == 'movie':
            return 'https://%s/embed/movie/%s' % (host, ident)
        url = 'https://%s/embed/tv/%s' % (host, ident)
        if season is not None:
            url += '/%s' % season
        if episode is not None:
            url += '-%s' % episode
        return url

    # multiembed.mov — query-string style, accepts both IMDb and TMDB.
    if 'multiembed' in host:
        tmdb_flag = '&tmdb=1' if (not imdb_id and tmdb_id) else ''
        if media_type == 'movie':
            return 'https://%s/?video_id=%s%s' % (host, ident, tmdb_flag)
        return 'https://%s/?video_id=%s&s=%s&e=%s%s' % (host, ident, s, e, tmdb_flag)

    # autoembed.cc — uses subdomain `player.` plus path-style routing.
    if 'autoembed' in host:
        base = 'player.' + host if not host.startswith('player.') else host
        if media_type == 'movie':
            return 'https://%s/embed/movie/%s' % (base, ident)
        return 'https://%s/embed/tv/%s/%s/%s' % (base, ident, s, e)

    # embed.su — same path scheme as the vidsrc family.
    if host.endswith('embed.su'):
        if media_type == 'movie':
            return 'https://%s/embed/movie/%s' % (host, ident)
        return 'https://%s/embed/tv/%s/%s/%s' % (host, ident, s, e)

    # moviesapi.club — TMDB-only, hyphenated TV path.
    if 'moviesapi' in host:
        mid = tmdb_id or ident
        if media_type == 'movie':
            return 'https://%s/movie/%s' % (host, mid)
        return 'https://%s/tv/%s-%s-%s' % (host, mid, s, e)

    # smashystream / smashy.stream — TMDB query-string router.
    if 'smashy' in host:
        mid = tmdb_id or ident
        if media_type == 'movie':
            return 'https://embed.%s/playere.php?tmdb=%s' % (host, mid)
        return 'https://embed.%s/playere.php?tmdb=%s&season=%s&episode=%s' % (host, mid, s, e)

    # 2embed.cc / 2embed.skin (generic fallback)
    if media_type == 'movie':
        return 'https://%s/embed/%s' % (host, ident)
    return 'https://%s/embedtv/%s&s=%s&e=%s' % (host, ident, s, e)


def _extract_iframes(html):
    urls = []
    for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
        u = m.group(1)
        if u.startswith('//'):
            u = 'https:' + u
        if u and u not in urls:
            urls.append(u)
    # Also: hashes embedded via data-hash for 2embed-style server lists.
    for m in re.finditer(r'data-hash=["\']([^"\']+)["\']', html):
        urls.append('https://2embed.cc/embed/' + m.group(1))
    return urls


def _try_resolveurl(url):
    try:
        import resolveurl  # type: ignore
    except ImportError:
        return None
    try:
        hmf = resolveurl.HostedMediaFile(url=url, include_disabled=False, include_universal=True)
        if not hmf.valid_url():
            return None
        resolved = hmf.resolve()
        return resolved or None
    except Exception as e:
        log('vidsrc2: ResolveURL failed for %s: %s' % (url[:90], e))
        return None


def resolve_all(media_type, tmdb_id, season=None, episode=None, imdb_id=None):
    sess = _session()
    host = _host()
    embed_url = _build_embed_url(host, media_type, tmdb_id, season, episode, imdb_id)
    log('vidsrc2 [%s]: fetching %s' % (host, embed_url))

    try:
        r = sess.get(embed_url, timeout=TIMEOUT,
                     headers={'Referer': 'https://%s/' % host})
        if r.status_code != 200:
            log('vidsrc2: status=%s' % r.status_code)
            return []
        html = r.text
    except Exception as e:
        log('vidsrc2: fetch failed %s' % e)
        return []

    iframes = _extract_iframes(html)
    log('vidsrc2: found %d iframe candidates' % len(iframes))

    streams = []
    for i, u in enumerate(iframes):
        resolved = _try_resolveurl(u)
        if not resolved:
            continue
        is_hls = '.m3u8' in resolved.lower()
        is_mp4 = '.mp4' in resolved.lower()
        proto = 'HLS' if is_hls else ('MP4' if is_mp4 else 'AUTO')
        h = re.sub(r'^https?://', '', resolved).split('/')[0]
        streams.append({
            'url': resolved,
            'headers': {'User-Agent': UA, 'Referer': 'https://%s/' % host},
            'label': '[%s] %s • %s (%s)' % (proto, proto, h, host),
            'quality': proto,
            'proto': proto,
            'host': h,
            'server': '%s #%d' % (host, i + 1),
            'height': 0,
            'bandwidth': 0,
            'provider': 'vidsrc2',
        })
    log('vidsrc2: resolved %d streams' % len(streams))
    return streams
