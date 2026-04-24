"""
Custom stream resolvers for Bones provider
Handles Streamtape and LuluVid/LuluVDO without requiring ResolveURL.
Updated 2026-01 — multiple streamtape obfuscation patterns, hardened error handling.
"""
import re
import xbmc
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

_STREAMTAPE_HOSTS = (
    'streamtape.com', 'streamtape.to', 'streamtape.net', 'streamtape.cc',
    'streamta.pe', 'streamtape.xyz', 'streamtape.site', 'streamtape.online',
    'streamadblocker.xyz', 'stape.fun', 'shavetape.cash',
)
_LULU_HOSTS = ('luluvid.com', 'luluvdo.com')


def _is_streamtape(url):
    u = (url or '').lower()
    return any(h in u for h in _STREAMTAPE_HOSTS)


def _is_lulu(url):
    u = (url or '').lower()
    return any(h in u for h in _LULU_HOSTS)


def resolve(url):
    """Resolve a stream URL to a direct playable link. Returns URL or None."""
    if not url:
        return None
    if _is_streamtape(url):
        return _resolve_streamtape(url)
    if 'luluvdo.com' in url.lower():
        return _resolve_luluvdo(url)
    if 'luluvid.com' in url.lower():
        return _resolve_luluvid(url)
    # Unknown host — return as-is so caller can fall back to ResolveURL
    return url


def _fetch(url, referer=None):
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    if referer:
        headers['Referer'] = referer
    req = Request(url, headers=headers)
    resp = urlopen(req, timeout=15)
    return resp.read().decode('utf-8', errors='ignore')


def _resolve_streamtape(url):
    """Resolve Streamtape /v/<id>/<name> or /e/<id> URL to a direct MP4 link."""
    try:
        # Normalize /v/<id> → /e/<id> which is the embed page (simpler markup)
        m = re.search(r'streamtape\.[a-z]+/(?:v|e)/([A-Za-z0-9]+)', url, re.IGNORECASE)
        embed_url = url
        if m:
            embed_url = f'https://streamtape.com/e/{m.group(1)}'

        html = _fetch(embed_url, referer='https://streamtape.com/')

        # --- Method 1: innerHTML = 'x' + ('y').substring(a).substring(b) -----
        match = re.search(
            r"getElementById\(['\"]\w+['\"]\)\.innerHTML\s*=\s*"
            r"['\"]([^'\"]+)['\"]\s*\+\s*\(['\"]([^'\"]+)['\"]\)"
            r"\.substring\((\d+)\)\.substring\((\d+)\)",
            html,
        )
        if match:
            base = match.group(1)
            token_raw = match.group(2)
            sub1 = int(match.group(3))
            sub2 = int(match.group(4))
            token = token_raw[sub1:][sub2:]
            return _normalize_st_url(base + token)

        # --- Method 2: innerHTML = 'x' + ('y').substring(a) ------------------
        match = re.search(
            r"getElementById\(['\"]\w+['\"]\)\.innerHTML\s*=\s*"
            r"['\"]([^'\"]+)['\"]\s*\+\s*\(['\"]([^'\"]+)['\"]\)"
            r"\.substring\((\d+)\)",
            html,
        )
        if match:
            base = match.group(1)
            token_raw = match.group(2)
            sub_idx = int(match.group(3))
            token = token_raw[sub_idx:]
            return _normalize_st_url(base + token)

        # --- Method 3: concatenated string form inside any JS var -----------
        # e.g.  robotlink = ('/get_video?id=xxx&expires=...&ip=...&token='+('abcdef').substring(3)).substring(...)
        match = re.search(
            r"\(['\"]([^'\"]+/get_video\?[^'\"]*)['\"]\s*\+\s*"
            r"\(['\"]([^'\"]+)['\"]\)\.substring\((\d+)\)",
            html,
        )
        if match:
            base = match.group(1)
            token = match.group(2)[int(match.group(3)):]
            return _normalize_st_url(base + token)

        # --- Method 4: raw div content fallback -----------------------------
        match = re.search(r'id=["\'](?:norobotlink|ideoooolink|captchalink)["\'][^>]*>([^<]+)<', html)
        if match:
            link = match.group(1).strip()
            return _normalize_st_url(link)

        xbmc.log('Streamtape: could not extract video URL (patterns not found)', xbmc.LOGWARNING)
        return None

    except HTTPError as e:
        xbmc.log(f'Streamtape HTTP {e.code}: {e.reason}', xbmc.LOGWARNING)
        return None
    except URLError as e:
        xbmc.log(f'Streamtape network error: {e.reason}', xbmc.LOGWARNING)
        return None
    except Exception as e:
        xbmc.log(f'Streamtape resolve error: {e}', xbmc.LOGWARNING)
        return None


def _normalize_st_url(link):
    """Normalize an extracted streamtape token into a full URL with stream=1."""
    link = link.strip()
    if link.startswith('//'):
        full = 'https:' + link
    elif link.startswith('http'):
        full = link
    elif link.startswith('/'):
        full = 'https://streamtape.com' + link
    else:
        full = 'https://streamtape.com/' + link
    if 'stream=1' not in full:
        full += ('&' if '?' in full else '?') + 'stream=1'
    xbmc.log(f'Streamtape resolved: {full[:120]}', xbmc.LOGINFO)
    return full


def _resolve_luluvid(url):
    """Resolve LuluVid URL - fetches embed page from luluvdo.com"""
    try:
        html = _fetch(url, referer='https://luluvid.com/')

        iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+luluvdo\.com[^"\']+)["\']', html)
        if iframe:
            return _resolve_luluvdo(iframe.group(1))

        file_id_match = re.search(r'/[de]/([a-zA-Z0-9]+)', url)
        if file_id_match:
            return _resolve_luluvdo(f'https://luluvdo.com/e/{file_id_match.group(1)}')

        xbmc.log('LuluVid: could not find embed', xbmc.LOGWARNING)
        return None
    except Exception as e:
        xbmc.log(f'LuluVid resolve error: {e}', xbmc.LOGWARNING)
        return None


def _resolve_luluvdo(embed_url):
    """Resolve LuluVDO embed page - unpack JS to get HLS URL"""
    try:
        html = _fetch(embed_url, referer='https://luluvid.com/')

        packed_match = re.search(
            r"eval\(function\(p,a,c,k,e,d\)\{.*?\}\('(.*?)',\s*(\d+)\s*,\s*(\d+)\s*,\s*'(.*?)'\s*\.split\('\|'\)",
            html, re.DOTALL,
        )

        if not packed_match:
            # Try to find a direct m3u8/mp4 in the raw html before giving up
            for patt in (r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
                         r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)'):
                m = re.search(patt, html)
                if m:
                    xbmc.log(f'LuluVDO resolved (raw): {m.group(1)[:120]}', xbmc.LOGINFO)
                    return m.group(1)
            xbmc.log('LuluVDO: no packed JS or direct URL found', xbmc.LOGWARNING)
            return None

        payload = packed_match.group(1)
        radix = int(packed_match.group(2))
        symtab = packed_match.group(4).split('|')

        def replacer(m):
            word = m.group(0)
            try:
                n = int(word, radix)
                return symtab[n] if n < len(symtab) and symtab[n] else word
            except (ValueError, IndexError):
                return word

        unpacked = re.sub(r'\b\w+\b', replacer, payload)

        m3u8_match = re.search(r'(https?://[^\s"\'\\}]+\.m3u8[^\s"\'\\}]*)', unpacked)
        if m3u8_match:
            xbmc.log(f'LuluVDO resolved: {m3u8_match.group(1)[:120]}', xbmc.LOGINFO)
            return m3u8_match.group(1)

        mp4_match = re.search(r'(https?://[^\s"\'\\}]+\.mp4[^\s"\'\\}]*)', unpacked)
        if mp4_match:
            xbmc.log(f'LuluVDO resolved (mp4): {mp4_match.group(1)[:120]}', xbmc.LOGINFO)
            return mp4_match.group(1)

        xbmc.log('LuluVDO: could not extract video URL from unpacked JS', xbmc.LOGWARNING)
        return None

    except Exception as e:
        xbmc.log(f'LuluVDO resolve error: {e}', xbmc.LOGWARNING)
        return None
