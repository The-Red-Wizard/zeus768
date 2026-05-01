# -*- coding: utf-8 -*-
"""Vidsrc resolver — vidsrcme.ru -> cloudnestra rcp -> prorcp -> hls/mp4 sources.

This resolver returns a *list* of candidate streams (one per server / quality
variant) so the addon can present a link/quality picker to the user.

Key fixes vs 1.0.1:
  * Multiple regex variants for locating the `prorcp` link (some pages now
    embed it as base64-encoded data, JS redirect, or window.location).
  * Per-{vN} CDN host substitution and concurrent probing.
  * Master m3u8 variant parsing -> exposes 4K / 1080 / 720 / 480 / 360 lines.
  * Detects HLS vs MP4 sources and tags each candidate.
  * Robust fallback to ResolveURL.
"""
import re
import requests

from .common import get_setting, get_setting_bool, log

DEFAULT_HOST = 'vidsrcme.ru'
TIMEOUT = 20
PROBE_TIMEOUT = 8

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# Known Cloudnestra CDN hostnames used with {vN} placeholders (fallback pool).
# Order matters — most reliable first.
CDN_POOL = [
    'shadowlandschronicles.com',
    'cdn-centaurus.com',
    'cdn-fnc.com',
    'shadowlands-cdn.com',
    'nestra-cdn.com',
    'cloudnestra.com',
    'tmstr-cdn.com',
]

# Quality buckets (height, label) - used to bucket master.m3u8 variants.
QUALITY_BUCKETS = [
    (2160, '4K'),
    (1440, '1440p'),
    (1080, '1080p'),
    (720, '720p'),
    (480, '480p'),
    (360, '360p'),
    (240, '240p'),
]

# Preferred order for auto-play (matches user's request: 4K → 1080 → 720 → 480 → 360)
QUALITY_ORDER = ['4K', '1440p', '1080p', '720p', '480p', '360p', '240p', 'HLS', 'MP4', 'AUTO']


def _host():
    h = (get_setting('vidsrc_host', DEFAULT_HOST) or DEFAULT_HOST).strip().rstrip('/')
    if h.startswith('http'):
        h = re.sub(r'^https?://', '', h)
    return h or DEFAULT_HOST


def _session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': UA,
        'Accept-Language': 'en-GB,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    return s


def _build_embed_url(media_type, tmdb_id, season=None, episode=None, imdb_id=None):
    host = _host()
    ident = imdb_id or tmdb_id
    if media_type == 'movie':
        return 'https://%s/embed/movie/%s' % (host, ident)
    parts = ['https://%s/embed/tv/%s' % (host, ident)]
    if season is not None:
        parts.append(str(season))
    if episode is not None:
        parts.append(str(episode))
    return '/'.join(parts)


def _extract_servers(html):
    """Find every cloudnestra rcp source on the embed page."""
    servers = []
    seen = set()

    def _add(url, name='Cloudnestra'):
        if url and url not in seen:
            seen.add(url)
            servers.append({'type': 'cloudnestra', 'url': url, 'name': name})

    for m in re.finditer(r'src=["\'](//cloudnestra\.com/rcp/[^"\']+)["\']', html):
        _add('https:' + m.group(1))
    for m in re.finditer(r'src=["\'](https?://cloudnestra\.com/rcp/[^"\']+)["\']', html):
        _add(m.group(1))
    for m in re.finditer(r'data-hash=["\']([^"\']+)["\']', html):
        _add('https://cloudnestra.com/rcp/' + m.group(1))
    # Server picker UI: <ul ... data-server data-hash=...>
    for m in re.finditer(r'data-hash=["\']([^"\']+)["\'][^>]*data-i=["\'](\d+)["\']', html):
        _add('https://cloudnestra.com/rcp/' + m.group(1), 'Cloudnestra #%s' % m.group(2))

    log('Vidsrc: found %d server(s) in embed page' % len(servers))
    return servers


def _parse_server_pool(body):
    """Extract a list of CDN hostnames from JS in the prorcp page."""
    pool = []
    for m in re.finditer(r"""(?:servers|cdns|hosts|srv|cdn_list)\s*[:=]\s*\[([^\]]+)\]""", body, re.I):
        for s in re.findall(r"""['"]([a-z0-9.\-]+\.[a-z]{2,})['"]""", m.group(1), re.I):
            if s not in pool:
                pool.append(s)
    for s in re.findall(r'tmstr\d?\.([a-z0-9.\-]+\.[a-z]{2,})', body, re.I):
        if s not in pool:
            pool.append(s)
    for s in re.findall(r'app\d?\.([a-z0-9.\-]+\.[a-z]{2,})', body, re.I):
        if s not in pool:
            pool.append(s)
    log('Vidsrc: parsed %d pool hostnames from page' % len(pool))
    return pool


def _expand_templates(raw_file, page_pool):
    """Given a raw file string with optional {vN} placeholders and ' or '
    separators, return a list of concrete candidate URLs."""
    parts = [p.strip() for p in re.split(r'\s+or\s+', raw_file) if p.strip()]
    pool = list(dict.fromkeys((page_pool or []) + CDN_POOL))

    candidates = []
    for part in parts:
        placeholders = sorted(set(re.findall(r'\{v(\d+)\}', part)))
        if not placeholders:
            if part not in candidates:
                candidates.append(part)
            continue
        for host in pool:
            url = part
            for n in placeholders:
                url = url.replace('{v%s}' % n, host)
            if url not in candidates:
                candidates.append(url)
    log('Vidsrc: expanded to %d candidate URLs' % len(candidates))
    return candidates


def _probe(url, referer, sess):
    try:
        r = sess.get(url, headers={'Referer': referer,
                                   'Origin': 'https://' + referer.split('/')[2]},
                     timeout=PROBE_TIMEOUT, stream=True, allow_redirects=True)
        ok = 200 <= r.status_code < 300
        text = ''
        if ok:
            try:
                text = r.raw.read(8192).decode('utf-8', errors='replace')
            except Exception:
                text = ''
        r.close()
        log('Vidsrc probe %s -> %d' % (url[:90], r.status_code))
        return ok, text
    except Exception as e:
        log('Vidsrc probe failed %s: %s' % (url[:90], e))
        return False, ''


def _parse_master_m3u8(text, base_url):
    """Parse #EXT-X-STREAM-INF lines and return list of (label, url, height, bandwidth)."""
    if '#EXTM3U' not in text or '#EXT-X-STREAM-INF' not in text:
        return []
    variants = []
    lines = text.splitlines()
    base = base_url.rsplit('/', 1)[0] + '/'
    for i, line in enumerate(lines):
        if line.startswith('#EXT-X-STREAM-INF'):
            res_m = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
            bw_m = re.search(r'BANDWIDTH=(\d+)', line)
            height = int(res_m.group(2)) if res_m else 0
            bw = int(bw_m.group(1)) if bw_m else 0
            uri = lines[i + 1].strip() if i + 1 < len(lines) else ''
            if not uri or uri.startswith('#'):
                continue
            if not uri.startswith('http'):
                uri = base + uri
            label = 'AUTO'
            for h, ql in QUALITY_BUCKETS:
                if height >= h:
                    label = ql
                    break
            variants.append({'label': label, 'url': uri, 'height': height, 'bandwidth': bw})
    return variants


_CF_MARKERS = ('Attention Required', 'cf-error-details', 'Just a moment',
               'Enable JavaScript and cookies', 'challenge-platform')


def _looks_like_cf_challenge(body):
    if not body:
        return False
    head = body[:4096]
    return any(m in head for m in _CF_MARKERS)


def _find_next_hop(body, current_host):
    """Find the next-hop iframe/redirect URL in a cloudnestra-like page.

    Tries a wide range of patterns so we still resolve when cloudnestra
    renames the /prorcp/ endpoint. Returns an absolute URL or None.
    """
    if not body:
        return None

    # 1. Iframe src anywhere in the body (the rcp page is basically a single
    #    <iframe src="..."> now). Prefer same-origin / relative URLs over
    #    absolute third-party URLs (ads, analytics) to avoid mis-picking.
    iframes = []
    for m in re.finditer(r'<iframe[^>]+src=["\']([^"\'#]+)["\']', body, re.I):
        href = m.group(1).strip()
        if not href or href.startswith('about:') or href.lower() == '#':
            continue
        iframes.append(href)
    iframes.sort(key=lambda h: 0 if h.startswith('/') else 1)
    if iframes:
        return _abs_url(iframes[0], current_host)

    # 2. Classic /prorcp/ style paths (kept for back-compat) and new variants
    #    like /prosrc/, /rcp2/, /source/ with the same base64-ish hash suffix.
    for pat in (
        r"""src\s*[:=]\s*['"]([^'"]*?/prorcp/[^'"]+)['"]""",
        r"""['"](/prorcp/[A-Za-z0-9+/=_\-]+)['"]""",
        r"""(/prorcp/[A-Za-z0-9+/=_\-]{8,})""",
        r"""['"](/(?:prosrc|rcp2|source|embed/player)/[A-Za-z0-9+/=_\-]{8,})['"]""",
        r"""window\.location(?:\.href)?\s*=\s*['"]([^'"]+)['"]""",
        r"""location\.replace\(\s*['"]([^'"]+)['"]""",
    ):
        m = re.search(pat, body)
        if m:
            return _abs_url(m.group(1), current_host)

    return None


def _abs_url(href, current_host):
    if href.startswith('//'):
        return 'https:' + href
    if href.startswith('/'):
        return 'https://' + current_host + href
    if href.startswith('http'):
        return href
    return 'https://' + current_host + '/' + href


def _resolve_cloudnestra(rcp_url, sess, referer, server_name='Cloudnestra'):
    """Return a list of stream candidates from a cloudnestra rcp link."""
    try:
        r = sess.get(rcp_url, headers={'Referer': referer}, timeout=TIMEOUT)
        body = r.text
    except Exception as e:
        log('cloudnestra rcp fetch failed: %s' % e)
        return []

    rcp_host = re.sub(r'^https?://', '', rcp_url).split('/')[0]

    if _looks_like_cf_challenge(body):
        log('cloudnestra: Cloudflare challenge/block on rcp (%d bytes)' % len(body))
        return _resolveurl_single(rcp_url, referer, server_name)

    next_url = _find_next_hop(body, rcp_host)
    if not next_url:
        log('cloudnestra: no next-hop link found in %d bytes; body preview=%r'
            % (len(body), body[:220].replace('\n', ' ')))
        return _resolveurl_single(rcp_url, referer, server_name)

    log('cloudnestra: next hop -> %s' % next_url[:120])
    try:
        r2 = sess.get(next_url, headers={'Referer': rcp_url}, timeout=TIMEOUT)
        body2 = r2.text
    except Exception as e:
        log('cloudnestra next-hop fetch failed: %s' % e)
        return _resolveurl_single(rcp_url, referer, server_name)

    if _looks_like_cf_challenge(body2):
        log('cloudnestra: Cloudflare challenge/block on next-hop (%d bytes)' % len(body2))
        return _resolveurl_single(rcp_url, referer, server_name)

    mf = re.search(r"""file\s*:\s*['"]([^'"]+?)['"]""", body2)
    if not mf:
        # Some variants use sources: [{file: "..."}]
        mf = re.search(r"""sources?\s*:\s*\[\s*\{[^}]*?file\s*:\s*['"]([^'"]+?)['"]""", body2, re.S)
    if not mf:
        # Last-ditch: any http(s) URL to .m3u8/.mp4 in the body.
        mf = re.search(r"""['"](https?://[^'"\s]+?\.(?:m3u8|mp4)[^'"\s]*)['"]""", body2)
    if not mf:
        log('cloudnestra: no file: key found in next-hop body (%d bytes); preview=%r'
            % (len(body2), body2[:220].replace('\n', ' ')))
        return _resolveurl_single(rcp_url, referer, server_name)
    raw_file = mf.group(1)
    log('Vidsrc raw file: %s' % raw_file[:240])

    pool = _parse_server_pool(body2)
    candidates = _expand_templates(raw_file, pool)
    candidates = [c for c in candidates if '{v' not in c]
    if not candidates:
        log('cloudnestra: no candidates after expansion')
        return []

    headers = {
        'User-Agent': UA,
        'Referer': 'https://cloudnestra.com/',
        'Origin': 'https://cloudnestra.com',
    }

    streams = []
    seen_urls = set()
    probed_ok = 0
    probe_enabled = get_setting_bool('probe_candidates', True)

    for url in candidates[:18]:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        is_hls = '.m3u8' in url.lower()
        is_mp4 = '.mp4' in url.lower()
        proto = 'HLS' if is_hls else ('MP4' if is_mp4 else 'AUTO')

        probed = True
        body_text = ''
        if probe_enabled:
            probed, body_text = _probe(url, 'https://cloudnestra.com/', sess)
        if not probed:
            continue
        probed_ok += 1

        host = re.sub(r'^https?://', '', url).split('/')[0]
        # If it's a master HLS playlist, expose individual quality variants.
        variants = _parse_master_m3u8(body_text, url) if is_hls else []
        if variants:
            for v in variants:
                streams.append({
                    'url': v['url'],
                    'headers': headers,
                    'label': '[%s] %s • %s' % (v['label'], proto, host),
                    'quality': v['label'],
                    'proto': proto,
                    'host': host,
                    'server': server_name,
                    'height': v['height'],
                    'bandwidth': v['bandwidth'],
                })
            # Also add the master itself as AUTO (let player pick).
            streams.append({
                'url': url, 'headers': headers,
                'label': '[AUTO] %s master • %s' % (proto, host),
                'quality': 'AUTO', 'proto': proto, 'host': host,
                'server': server_name, 'height': 0, 'bandwidth': 0,
            })
        else:
            streams.append({
                'url': url, 'headers': headers,
                'label': '[%s] %s • %s' % (proto, proto, host),
                'quality': proto, 'proto': proto, 'host': host,
                'server': server_name, 'height': 0, 'bandwidth': 0,
            })

        if probed_ok >= 4:
            break

    if not streams:
        # Probing blocked — return raw candidates as-is so the user can still try.
        for url in candidates[:6]:
            host = re.sub(r'^https?://', '', url).split('/')[0]
            is_hls = '.m3u8' in url.lower()
            proto = 'HLS' if is_hls else ('MP4' if '.mp4' in url.lower() else 'AUTO')
            streams.append({
                'url': url, 'headers': headers,
                'label': '[%s] %s • %s (unprobed)' % (proto, proto, host),
                'quality': proto, 'proto': proto, 'host': host,
                'server': server_name, 'height': 0, 'bandwidth': 0,
            })
    return streams


def resolve_all(media_type, tmdb_id, season=None, episode=None, imdb_id=None):
    """Return a list of stream candidates."""
    sess = _session()
    embed_url = _build_embed_url(media_type, tmdb_id, season, episode, imdb_id)
    log('Vidsrc: fetching %s' % embed_url)

    try:
        r = sess.get(embed_url, timeout=TIMEOUT)
        if r.status_code != 200:
            log('Vidsrc embed status %s' % r.status_code)
            return _try_resolveurl_fallback(embed_url)
        html = r.text
    except Exception as e:
        log('Vidsrc embed fetch failed: %s' % e)
        return _try_resolveurl_fallback(embed_url)

    servers = _extract_servers(html)
    if not servers:
        return _try_resolveurl_fallback(embed_url)

    all_streams = []
    for i, srv in enumerate(servers):
        log('Vidsrc: trying server %d/%d (%s)' % (i + 1, len(servers), srv.get('name')))
        if srv['type'] == 'cloudnestra':
            all_streams.extend(_resolve_cloudnestra(srv['url'], sess, embed_url,
                                                   server_name=srv.get('name', 'Cloudnestra')))

    if not all_streams:
        # Try ResolveURL on each individual cloudnestra rcp URL (resolveurl
        # ships with a cloudnestra plugin that can handle the CF-protected
        # rcp page end-to-end). This is the primary recovery path when the
        # lightweight regex-based resolver above cannot find a next hop.
        for srv in servers:
            if srv.get('type') != 'cloudnestra':
                continue
            rstreams = _resolveurl_single(srv['url'], embed_url,
                                          srv.get('name', 'Cloudnestra'))
            if rstreams:
                all_streams.extend(rstreams)

    if not all_streams:
        ru = _try_resolveurl_fallback(embed_url)
        if ru:
            all_streams.extend(ru)

    # Sort: preferred quality order, then by bandwidth desc inside same bucket.
    def _rank(s):
        try:
            qi = QUALITY_ORDER.index(s.get('quality', 'AUTO'))
        except ValueError:
            qi = len(QUALITY_ORDER)
        return (qi, -(s.get('bandwidth') or 0), -(s.get('height') or 0))
    all_streams.sort(key=_rank)
    log('Vidsrc: %d total candidates' % len(all_streams))
    return all_streams


def resolve(media_type, tmdb_id, season=None, episode=None, imdb_id=None):
    """Backwards-compatible single-stream resolver (returns the best candidate)."""
    streams = resolve_all(media_type, tmdb_id, season, episode, imdb_id)
    return streams[0] if streams else None


def _resolveurl_single(url, referer, server_name):
    """Try ResolveURL on a single URL and wrap the result in our stream shape."""
    try:
        import resolveurl  # type: ignore
    except ImportError:
        return []
    try:
        hmf = resolveurl.HostedMediaFile(url=url, include_disabled=False,
                                         include_universal=True)
        if not hmf.valid_url():
            return []
        resolved = hmf.resolve()
        if not resolved:
            return []
        host = re.sub(r'^https?://', '', resolved).split('/')[0]
        is_hls = '.m3u8' in resolved.lower()
        is_mp4 = '.mp4' in resolved.lower()
        proto = 'HLS' if is_hls else ('MP4' if is_mp4 else 'AUTO')
        log('ResolveURL resolved %s -> %s' % (url[:80], resolved[:90]))
        return [{
            'url': resolved,
            'headers': {'User-Agent': UA, 'Referer': referer},
            'label': '[%s] %s via ResolveURL • %s' % (proto, server_name, host),
            'quality': proto, 'proto': proto, 'host': host,
            'server': server_name, 'height': 0, 'bandwidth': 0,
        }]
    except Exception as e:
        log('ResolveURL single failed for %s: %s' % (url[:80], e))
    return []


def _try_resolveurl_fallback(url):
    try:
        import resolveurl  # type: ignore
    except ImportError:
        log('ResolveURL not installed; cannot fallback')
        return []
    try:
        hmf = resolveurl.HostedMediaFile(url=url, include_disabled=False, include_universal=True)
        if not hmf.valid_url():
            log('ResolveURL: URL not valid for any resolver')
            return []
        resolved = hmf.resolve()
        if resolved:
            host = re.sub(r'^https?://', '', resolved).split('/')[0]
            is_hls = '.m3u8' in resolved.lower()
            proto = 'HLS' if is_hls else 'MP4'
            return [{
                'url': resolved, 'headers': {'User-Agent': UA},
                'label': '[%s] ResolveURL • %s' % (proto, host),
                'quality': proto, 'proto': proto, 'host': host,
                'server': 'ResolveURL', 'height': 0, 'bandwidth': 0,
            }]
    except Exception as e:
        log('ResolveURL fallback failed: %s' % e)
    return []


def stream_url_with_headers(stream):
    if not stream:
        return None
    url = stream['url']
    headers = stream.get('headers') or {}
    if not headers:
        return url
    qs = '&'.join('%s=%s' % (k, requests.utils.quote(v, safe='')) for k, v in headers.items())
    return '%s|%s' % (url, qs)
