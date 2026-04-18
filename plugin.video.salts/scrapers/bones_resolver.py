"""
Custom stream resolvers for Bones provider
Handles Streamtape and LuluVid without requiring ResolveURL
"""
import re
import xbmc
from urllib.request import urlopen, Request
from urllib.error import URLError

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def resolve(url):
    """Resolve a stream URL to a direct playable link"""
    if 'streamtape.com' in url:
        return _resolve_streamtape(url)
    elif 'luluvid.com' in url:
        return _resolve_luluvid(url)
    elif 'luluvdo.com' in url:
        return _resolve_luluvdo(url)
    return url


def _resolve_streamtape(url):
    """Resolve Streamtape URL to direct video link"""
    try:
        headers = {'User-Agent': USER_AGENT, 'Referer': 'https://streamtape.com/'}
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='ignore')

        # Method 1: norobotlink with substring concat
        match = re.search(
            r"getElementById\('norobotlink'\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]\s*\+\s*\('([^']+)'\)\.substring\((\d+)\)\.substring\((\d+)\)",
            html
        )
        if match:
            base = match.group(1)
            token_raw = match.group(2)
            sub1 = int(match.group(3))
            sub2 = int(match.group(4))
            token = token_raw[sub1:][sub2:]
            video_url = 'https:' + base + token if not base.startswith('http') else base + token
            xbmc.log(f'Streamtape resolved (norobot): {video_url[:80]}...', xbmc.LOGINFO)
            return video_url

        # Method 2: innerHTML concat with single substring
        match = re.search(
            r"getElementById\('(?:norobotlink|ideoooolink|captchalink)'\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]\s*\+\s*\('([^']+)'\)\.substring\((\d+)\)",
            html
        )
        if match:
            base = match.group(1)
            token_raw = match.group(2)
            sub_idx = int(match.group(3))
            token = token_raw[sub_idx:]
            video_url = 'https:' + base + token if not base.startswith('http') else base + token
            xbmc.log(f'Streamtape resolved (method2): {video_url[:80]}...', xbmc.LOGINFO)
            return video_url

        # Method 3: Direct div content
        match = re.search(r'id="norobotlink"[^>]*>([^<]+)<', html)
        if match:
            link = match.group(1).strip()
            video_url = 'https:' + link if not link.startswith('http') else link
            xbmc.log(f'Streamtape resolved (div): {video_url[:80]}...', xbmc.LOGINFO)
            return video_url

        xbmc.log('Streamtape: Could not extract video URL', xbmc.LOGWARNING)
        return None

    except Exception as e:
        xbmc.log(f'Streamtape resolve error: {e}', xbmc.LOGWARNING)
        return None


def _resolve_luluvid(url):
    """Resolve LuluVid URL - fetches embed page from luluvdo.com"""
    try:
        headers = {'User-Agent': USER_AGENT, 'Referer': 'https://luluvid.com/'}
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='ignore')

        # Find the luluvdo embed iframe
        iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+luluvdo\.com[^"\']+)["\']', html)
        if iframe:
            return _resolve_luluvdo(iframe.group(1))

        # Try extracting file_id and constructing embed URL
        file_id_match = re.search(r'/[de]/([a-zA-Z0-9]+)', url)
        if file_id_match:
            embed_url = f'https://luluvdo.com/e/{file_id_match.group(1)}'
            return _resolve_luluvdo(embed_url)

        xbmc.log('LuluVid: Could not find embed', xbmc.LOGWARNING)
        return None

    except Exception as e:
        xbmc.log(f'LuluVid resolve error: {e}', xbmc.LOGWARNING)
        return None


def _resolve_luluvdo(embed_url):
    """Resolve LuluVDO embed page - unpack JS to get HLS URL"""
    try:
        headers = {'User-Agent': USER_AGENT, 'Referer': 'https://luluvid.com/'}
        req = Request(embed_url, headers=headers)
        resp = urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='ignore')

        # Extract P.A.C.K.E.R packed JS
        packed_match = re.search(
            r"eval\(function\(p,a,c,k,e,d\)\{.*?\}\('(.*?)',\s*(\d+)\s*,\s*(\d+)\s*,\s*'(.*?)'\s*\.split\('\|'\)",
            html, re.DOTALL
        )

        if not packed_match:
            xbmc.log('LuluVDO: No packed JS found', xbmc.LOGWARNING)
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

        # Extract m3u8 URL from unpacked jwplayer config
        m3u8_match = re.search(r'(https?://[^\s"\'\\}]+\.m3u8[^\s"\'\\}]*)', unpacked)
        if m3u8_match:
            video_url = m3u8_match.group(1)
            xbmc.log(f'LuluVDO resolved: {video_url[:80]}...', xbmc.LOGINFO)
            return video_url

        # Fallback: any video URL
        mp4_match = re.search(r'(https?://[^\s"\'\\}]+\.mp4[^\s"\'\\}]*)', unpacked)
        if mp4_match:
            video_url = mp4_match.group(1)
            xbmc.log(f'LuluVDO resolved (mp4): {video_url[:80]}...', xbmc.LOGINFO)
            return video_url

        xbmc.log('LuluVDO: Could not extract video URL from unpacked JS', xbmc.LOGWARNING)
        return None

    except Exception as e:
        xbmc.log(f'LuluVDO resolve error: {e}', xbmc.LOGWARNING)
        return None
