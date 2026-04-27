# -*- coding: utf-8 -*-
"""ZEUS Resolvers - built-in non-debrid hoster resolvers for SALTS.

ResolveURL (script.module.resolveurl) is the primary path, but its host
patterns lag behind the mirror-domain churn used by free file hosts
(streamtape.cc, d000d.com, dood.li, ddownload.com, mixdrop.top, etc.).
When ResolveURL returns nothing - or, for some hosts, BEFORE we even ask
ResolveURL - we try these light-weight, regex-based resolvers as a
fallback.  No external dependencies - only urllib + re.

Each resolver returns a playable URL (mp4 / m3u8) or ``None``.
The returned URL may include a ``|`` followed by request headers
(Kodi inputstream pipe-syntax).

Hosts handled: streamtape, doodstream/d000d/dood-mirror, mixdrop,
ddownload/ddl.to, ok.ru, youtube (via Piped), krakenfiles, imgnuts,
plus a generic player-page fallback for small embed hosts.
"""
import re
import json
from urllib.parse import urlparse, urljoin
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

import xbmc

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')


def _fetch(url, referer=None, timeout=20, extra_headers=None):
    headers = {
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    if referer:
        headers['Referer'] = referer
    if extra_headers:
        headers.update(extra_headers)
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace'), r.url
    except (HTTPError, URLError) as e:
        xbmc.log(f'SALTS resolver fetch failed {url}: {e}', xbmc.LOGWARNING)
        return '', url
    except Exception as e:
        xbmc.log(f'SALTS resolver fetch error {url}: {e}', xbmc.LOGERROR)
        return '', url


# Packed JS unpacker (Dean Edwards p,a,c,k,e,d) ----------------------------
_PACKED_RE = re.compile(
    r"eval\(function\(p,a,c,k,e,(?:r|d)\)\{.*?\}\s*\('(.*?)',\s*(\d+)\s*,"
    r"\s*(\d+)\s*,\s*'(.*?)'\.split\('\|'\)",
    re.DOTALL,
)


def _unpack(packed_js):
    """Unpack a Dean Edwards p.a.c.k.e.r packed JS payload."""
    m = _PACKED_RE.search(packed_js)
    if not m:
        return ''
    payload, _radix, _count, symtab = m.groups()
    radix = int(_radix)
    count = int(_count)
    words = symtab.split('|')

    def _b(n):
        digits = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        if n == 0:
            return '0'
        r = []
        num = n
        while num:
            num, d = divmod(num, radix)
            r.append(digits[d])
        return ''.join(reversed(r))

    out = payload
    for i in range(count - 1, -1, -1):
        sym = _b(i)
        if not sym:
            continue
        word = words[i] if i < len(words) else ''
        if word == '':
            continue
        out = re.sub(r'\b' + re.escape(sym) + r'\b', word, out)
    out = out.replace('\\\\', '\\').replace("\\'", "'").replace('\\"', '"')
    return out


# Mixdrop -------------------------------------------------------------------
_MIXDROP_HOSTS = (
    'mixdrop.co', 'mixdrop.to', 'mixdrop.club', 'mixdrop.top', 'mixdrop.gl',
    'mixdrop.cv', 'mixdrop.my', 'mixdrop.ag', 'mixdrop.ps', 'mixdrop.sx',
    'mixdrop.bz', 'mixdrop.is', 'mixdrop.lol', 'mixdrop.si', 'mixdrop.live',
)

_MIXDROP_DIRECT_RE = re.compile(r'wurl\s*=\s*[\'"]([^\'"]+)[\'"]')


def _is_mixdrop(url):
    h = (urlparse(url).netloc or '').lower().replace('www.', '')
    return h.startswith('mixdrop.')


def resolve_mixdrop(url):
    parsed = urlparse(url)
    path = parsed.path or '/'
    m = re.search(r'/(?:e|f)/([A-Za-z0-9_\-]+)', path)
    if not m:
        return None
    vid = m.group(1)
    primary = (parsed.netloc or 'mixdrop.co').lower().replace('www.', '')
    candidates = [primary] + [h for h in _MIXDROP_HOSTS if h != primary]

    for host in candidates:
        embed = f'https://{host}/e/{vid}'
        html, _ = _fetch(embed, referer=f'https://{host}/')
        if not html:
            continue
        unpacked = _unpack(html) or html
        m2 = _MIXDROP_DIRECT_RE.search(unpacked)
        if not m2:
            m2 = re.search(r'(https?:)?(//[^\s\'"<>]+\.mp4[^\s\'"<>]*)', unpacked)
            if m2:
                stream = m2.group(0)
                if stream.startswith('//'):
                    stream = 'https:' + stream
                return f'{stream}|User-Agent={UA}&Referer={embed}'
            continue
        stream = m2.group(1)
        if stream.startswith('//'):
            stream = 'https:' + stream
        elif stream.startswith('/'):
            stream = f'https://{host}{stream}'
        return f'{stream}|User-Agent={UA}&Referer={embed}'
    return None


# Doodstream / d000d / dood-mirror ------------------------------------------
_DOOD_HOSTS = re.compile(
    r'^(www\.)?(d[a-z0-9]*ood[a-z]*\.[a-z.]+|d0+d\.[a-z.]+|d000d\.[a-z]+|'
    r'dood\.[a-z]+|ds2play\.com|ds2video\.com)$', re.I)


def _is_doodstream(url):
    h = (urlparse(url).netloc or '').lower()
    return bool(_DOOD_HOSTS.match(h))


def resolve_doodstream(url):
    parsed = urlparse(url)
    host = parsed.netloc
    path = parsed.path or '/'
    m = re.search(r'/(?:e|d|embed)/([A-Za-z0-9_\-]+)', path)
    if not m:
        return None
    vid = m.group(1)
    embed = f'https://{host}/e/{vid}'
    html, final = _fetch(embed, referer=f'https://{host}/')
    if not html:
        return None
    pm = urlparse(final).netloc or host
    m2 = re.search(r"(/pass_md5/[A-Za-z0-9_\-/]+)", html)
    tok_m = re.search(r"makePlay\s*=\s*function[^}]*\?token=([A-Za-z0-9_\-]+)",
                      html)
    if not m2:
        return None
    base_url, _ = _fetch(f'https://{pm}{m2.group(1)}', referer=embed)
    if not base_url:
        return None
    import string
    import random
    rand = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    expiry = int(__import__('time').time() * 1000)
    token = tok_m.group(1) if tok_m else ''
    suffix = f'{rand}?token={token}&expiry={expiry}' if token else f'{rand}?expiry={expiry}'
    direct = base_url.strip() + suffix
    return f'{direct}|User-Agent={UA}&Referer={embed}'


# Streamtape ---------------------------------------------------------------
def _is_streamtape(url):
    h = (urlparse(url).netloc or '').lower().replace('www.', '')
    return h.startswith('streamtape.') or h.startswith('streamta.pe') or \
        h.startswith('shavetape.') or h.startswith('strcloud.') or \
        h.startswith('strtape.') or h.startswith('streamadblocker.')


def resolve_streamtape(url):
    parsed = urlparse(url)
    path = parsed.path or '/'
    m = re.search(r'/(?:e|v)/([A-Za-z0-9_\-]+)', path)
    if not m:
        return None
    vid = m.group(1)
    host = parsed.netloc
    embed = f'https://{host}/e/{vid}'
    html, _ = _fetch(embed, referer=f'https://{host}/')
    if not html:
        return None
    m2 = re.search(
        r"document\.getElementById\([\'\"]\w+[\'\"]\)\.innerHTML\s*=\s*"
        r"[\"\'](.+?)[\"\']\s*\+\s*[\"\']([^\"\']+)[\"\']", html)
    if not m2:
        m2 = re.search(r"id=[\"\']?(?:robotlink|ideoolink|videolink)[\"\']?>"
                       r"(?:.*?)[\"\']([^\"\']*get_video[^\"\']*)[\"\']", html)
        if not m2:
            return None
        partial = m2.group(1)
        full = 'https:' + partial if partial.startswith('//') else partial
        return f'{full}|User-Agent={UA}&Referer={embed}'
    a, b = m2.group(1), m2.group(2)
    partial = a + b[3:]
    if partial.startswith('//'):
        partial = 'https:' + partial
    elif not partial.startswith('http'):
        partial = 'https://' + partial.lstrip('/')
    return f'{partial}|User-Agent={UA}&Referer={embed}'


# DDownload / DDL.to -------------------------------------------------------
# ddownload.com (a.k.a. ddl.to) ships an XFileShare-style player. The embed
# page contains either a Dean-Edwards-packed JS payload that exposes the
# JWPlayer ``sources: [{file:"..."}]`` config OR a ``hls`` / ``file`` key.
# Common mirrors: ddownload.com, ddl.to, ddownload.co
_DDOWN_HOSTS = ('ddownload.com', 'ddl.to', 'ddownload.co')


def _is_ddownload(url):
    h = (urlparse(url).netloc or '').lower().replace('www.', '')
    return any(h == d or h.endswith('.' + d) for d in _DDOWN_HOSTS)


def resolve_ddownload(url):
    """Resolve a ddownload.com / ddl.to link to a direct mp4/m3u8."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace('www.', '') or 'ddownload.com'
    path = parsed.path or '/'
    # Accept /embed-<id>.html, /e/<id>, /<id>, /<id>/<filename>
    m = re.search(r'/embed-([A-Za-z0-9]+)', path) or \
        re.search(r'/e/([A-Za-z0-9]+)', path) or \
        re.search(r'/([A-Za-z0-9]{8,})', path)
    if not m:
        return None
    vid = m.group(1)

    # Try every mirror in turn, with the original URL's host first.
    candidates = [host] + [h for h in _DDOWN_HOSTS if h != host]
    for h in candidates:
        embed = f'https://{h}/embed-{vid}.html'
        html, _ = _fetch(embed, referer=f'https://{h}/')
        if not html:
            continue
        unpacked = _unpack(html) or html
        # JWPlayer-style: sources:[{file:"https://...mp4"}, ...]
        m2 = re.search(
            r'sources\s*:\s*\[\s*\{[^}]*?file\s*:\s*[\'"]([^\'"]+\.(?:m3u8|mp4)[^\'"]*)[\'"]',
            unpacked, re.IGNORECASE)
        if not m2:
            m2 = re.search(
                r'(?:file|hls|src)\s*:\s*[\'"]([^\'"]+\.(?:m3u8|mp4)[^\'"]*)[\'"]',
                unpacked, re.IGNORECASE)
        if not m2:
            # Bare direct stream URL anywhere in the unpacked JS
            m2 = re.search(
                r'(https?://[^\s\'"<>]+\.(?:m3u8|mp4)[^\s\'"<>]*)', unpacked)
        if not m2:
            continue
        stream = m2.group(1) if m2.lastindex else m2.group(0)
        if stream.startswith('//'):
            stream = 'https:' + stream
        return f'{stream}|User-Agent={UA}&Referer={embed}'
    return None


# ok.ru --------------------------------------------------------------------
def _is_okru(url):
    h = (urlparse(url).netloc or '').lower()
    return h in ('ok.ru', 'www.ok.ru', 'odnoklassniki.ru')


def resolve_okru(url):
    html, _ = _fetch(url, referer='https://ok.ru/')
    if not html:
        return None
    m = re.search(r'data-options="([^"]+)"', html)
    if not m:
        return None
    raw = m.group(1).replace('&quot;', '"').replace('&amp;', '&')
    try:
        cfg = json.loads(raw)
        flash = json.loads(cfg.get('flashvars', {}).get('metadata', '{}'))
    except (ValueError, AttributeError, TypeError):
        return None
    urls = flash.get('videos', []) or []
    quality_order = ['full', 'hd', 'sd', 'low', 'lowest', 'mobile']
    urls.sort(key=lambda v: quality_order.index(v.get('name', 'lowest'))
              if v.get('name', 'lowest') in quality_order else 99)
    if urls:
        return f"{urls[0].get('url')}|User-Agent={UA}&Referer={url}"
    return None


# YouTube via Piped fallback -----------------------------------------------
_PIPED_INSTANCES = (
    'https://pipedapi.kavin.rocks',
    'https://api-piped.mha.fi',
    'https://pipedapi.tokhmi.xyz',
    'https://pipedapi.adminforge.de',
)


def _is_youtube(url):
    h = (urlparse(url).netloc or '').lower()
    return ('youtube.com' in h) or ('youtu.be' in h)


def _yt_extract_id(url):
    parsed = urlparse(url)
    if 'youtu.be' in (parsed.netloc or ''):
        return parsed.path.lstrip('/').split('/')[0]
    qs = dict(p.split('=', 1) for p in (parsed.query or '').split('&') if '=' in p)
    if 'v' in qs:
        return qs['v']
    m = re.search(r'/embed/([A-Za-z0-9_\-]+)', parsed.path or '')
    if m:
        return m.group(1)
    return ''


def resolve_youtube_via_piped(url_or_id):
    vid = url_or_id if re.fullmatch(r'[A-Za-z0-9_\-]{11}', url_or_id or '') \
        else _yt_extract_id(url_or_id)
    if not vid:
        return None
    for base in _PIPED_INSTANCES:
        body, _ = _fetch(f'{base}/streams/{vid}')
        if not body:
            continue
        try:
            data = json.loads(body)
        except ValueError:
            continue
        progs = [s for s in (data.get('videoStreams') or [])
                 if not s.get('videoOnly') and s.get('format') in
                 ('MPEG_4', 'WEBM', 'MP4')]
        if not progs:
            if data.get('hls'):
                return data['hls']
            continue
        progs.sort(key=lambda s: int(s.get('quality', '0p').rstrip('p') or 0),
                   reverse=True)
        return progs[0].get('url')
    return None


# Krakenfiles --------------------------------------------------------------
def _is_kraken(url):
    h = (urlparse(url).netloc or '').lower()
    return 'krakenfiles.com' in h or 'krakencloud.net' in h


_KRAKEN_SOURCE_RE = re.compile(
    r'<source\s+[^>]*\bsrc=["\']'
    r'(https?://[^"\']*krakencloud\.net/play/video/[^"\']+)["\']',
    re.IGNORECASE)
_KRAKEN_PLAY_URL_RE = re.compile(
    r'https?://[A-Za-z0-9_.-]*krakencloud\.net/play/video/[A-Za-z0-9_-]+',
    re.IGNORECASE)
_KRAKEN_ID_RE = re.compile(
    r'krakenfiles\.com/(?:embed-video|view)/([A-Za-z0-9]+)',
    re.IGNORECASE)


def _kraken_with_headers(stream_url):
    from urllib.parse import quote_plus
    headers = (
        f'User-Agent={quote_plus(UA)}'
        f'&Referer={quote_plus("https://krakenfiles.com/")}'
        f'&Origin={quote_plus("https://krakenfiles.com")}'
    )
    return f'{stream_url}|{headers}'


def resolve_kraken(url):
    if not url:
        return None
    if 'krakencloud.net/play/video/' in url:
        return _kraken_with_headers(url)
    embed = url
    m = _KRAKEN_ID_RE.search(url)
    if m:
        embed = f'https://krakenfiles.com/embed-video/{m.group(1)}'
    html, _ = _fetch(embed, referer='https://krakenfiles.com/')
    if not html:
        return None
    play = ''
    sm = _KRAKEN_SOURCE_RE.search(html)
    if sm:
        play = sm.group(1)
    else:
        pm = _KRAKEN_PLAY_URL_RE.search(html)
        if pm:
            play = pm.group(0)
    if not play:
        xbmc.log(f'SALTS kraken: no play URL found for {embed}', xbmc.LOGWARNING)
        return None
    return _kraken_with_headers(play)


# Generic player-page scraper ----------------------------------------------
_PLAYER_FILE_RE = re.compile(
    r'(?:file|src|source|hls|hls_src|video_url|video|url)\s*:\s*'
    r'[\'"]([^\'"]+\.(?:m3u8|mp4)[^\'"]*)[\'"]', re.IGNORECASE)
_PLAYER_SOURCES_RE = re.compile(
    r'sources\s*:\s*\[(.*?)\]', re.IGNORECASE | re.DOTALL)
_DIRECT_STREAM_RE = re.compile(
    r'https?://[^\s"\'<>]+?\.(?:m3u8|mp4)(?:\?[^\s"\'<>]*)?',
    re.IGNORECASE)
_NOT_AVAILABLE_RE = re.compile(
    r'this\s+video\s+is\s+not\s+available|check\s+your\s+video\s+links|'
    r'video\s+does\s+not\s+exist|video\s+(?:has\s+been\s+)?removed|'
    r'404\s+page\s+not\s+found|file\s+not\s+found',
    re.IGNORECASE)
_PLACEHOLDER_URL_RE = re.compile(
    r'/(?:not[-_]?available|unavailable|notfound|not[-_]?found|error|'
    r'placeholder|deleted|removed|expired|sample)[^/]*\.mp4',
    re.IGNORECASE)


def _scrape_player_stream(html):
    if not html:
        return ''
    if _NOT_AVAILABLE_RE.search(html):
        return ''
    candidates = [html]
    unpacked = _unpack(html)
    if unpacked:
        candidates.append(unpacked)

    def _accept(u):
        return bool(u) and not _PLACEHOLDER_URL_RE.search(u)

    for chunk in candidates:
        m = _PLAYER_SOURCES_RE.search(chunk)
        if m:
            block = m.group(1)
            urls = [u for u in _DIRECT_STREAM_RE.findall(block) if _accept(u)]
            if urls:
                hls = [u for u in urls if '.m3u8' in u.lower()]
                return (hls or urls)[0]
        for m in _PLAYER_FILE_RE.finditer(chunk):
            cand = m.group(1)
            if _accept(cand):
                return cand
        for m in _DIRECT_STREAM_RE.finditer(chunk):
            cand = m.group(0)
            if _accept(cand):
                return cand
    return ''


_GENERIC_PLAYER_HOSTS = re.compile(
    r'(?:sawlivenow|ahvplayer|swiftplayers|playerlive|chillax|playembed|'
    r'tubeembed|smoothpre|listeamed|wolfstream|playerwish)\.', re.I)


def _is_generic_player(url):
    h = (urlparse(url).netloc or '').lower()
    return bool(_GENERIC_PLAYER_HOSTS.search(h)) or '/embed/' in (url or '').lower()


def resolve_generic_player(url):
    parsed = urlparse(url)
    host = parsed.netloc or ''
    referers = (f'https://{host}/',)
    for ref in referers:
        html, final = _fetch(url, referer=ref)
        if not html:
            continue
        stream = _scrape_player_stream(html)
        if stream:
            if stream.startswith('//'):
                stream = 'https:' + stream
            elif stream.startswith('/'):
                stream = urljoin(final or url, stream)
            return f'{stream}|User-Agent={UA}&Referer={final or url}'
    return None


# Master resolver ----------------------------------------------------------
def resolve(url):
    """Try built-in resolvers in order. Returns playable URL or None."""
    if not url:
        return None
    try:
        if _is_kraken(url):
            return resolve_kraken(url)
        if _is_mixdrop(url):
            return resolve_mixdrop(url)
        if _is_doodstream(url):
            return resolve_doodstream(url)
        if _is_streamtape(url):
            return resolve_streamtape(url)
        if _is_ddownload(url):
            return resolve_ddownload(url)
        if _is_okru(url):
            return resolve_okru(url)
        if _is_youtube(url):
            return resolve_youtube_via_piped(url)
        if _is_generic_player(url):
            return resolve_generic_player(url)
    except Exception as e:
        xbmc.log(f'SALTS built-in resolver crashed for {url}: {e}',
                 xbmc.LOGERROR)
    return None


def is_supported(url):
    """Return True if any built-in resolver claims this URL host."""
    if not url:
        return False
    try:
        return any((
            _is_kraken(url), _is_mixdrop(url), _is_doodstream(url),
            _is_streamtape(url), _is_ddownload(url), _is_okru(url),
            _is_youtube(url), _is_generic_player(url),
        ))
    except Exception:
        return False
