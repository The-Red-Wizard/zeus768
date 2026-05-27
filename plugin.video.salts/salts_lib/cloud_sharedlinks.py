"""
SALTS - Shared-link cloud mode for providers that have no usable account API.

Used by Sync.com and iDrive (and any other "paste a public share link"
source).  The user maintains a JSON list in the Kodi profile:

    special://profile/addon_data/plugin.video.salts/sharedlinks_<provider>.json

Each entry:
    { "url": "...", "label": "optional friendly name" }

The resolver extracts a direct, debrid-pushable URL from each link page when
possible; otherwise it returns the original share URL so the user can still
push it to a debrid service that supports the host.

Provider helper exposed for cloud_library.py:
    add_link(provider), remove_link(provider),
    is_authed(provider), list_all_videos(provider, progress_cb=None),
    get_stream_url(provider, file_id), get_share_url(provider, file_id)

`file_id` here is just the index (as string) into the saved JSON list.
"""
import json
import os
import re

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
from urllib.request import Request, urlopen

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = 'SALTS'

DATA = xbmcvfs.translatePath(
    f'special://profile/addon_data/{ADDON_ID}/'
)

VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.ts',
             '.flv', '.wmv', '.mpg', '.mpeg', '.m2ts')


def _store(provider):
    return os.path.join(DATA, f'sharedlinks_{provider}.json')


def _load(provider):
    fp = _store(provider)
    if not os.path.isfile(fp):
        return []
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            return json.load(fh) or []
    except Exception:
        return []


def _save(provider, items):
    try:
        os.makedirs(DATA, exist_ok=True)
        with open(_store(provider), 'w', encoding='utf-8') as fh:
            json.dump(items, fh, indent=2)
    except Exception as e:
        xbmc.log(f'sharedlinks save {provider}: {e}', xbmc.LOGWARNING)


def is_authed(provider):
    return len(_load(provider)) > 0


def add_link(provider):
    url = xbmcgui.Dialog().input(
        f'Paste {provider.capitalize()} share link',
        type=xbmcgui.INPUT_ALPHANUM)
    if not url:
        return
    label = xbmcgui.Dialog().input(
        'Friendly name (or leave blank to derive from URL)',
        type=xbmcgui.INPUT_ALPHANUM) or ''
    items = _load(provider)
    items.append({'url': url.strip(), 'label': label.strip()})
    _save(provider, items)
    xbmcgui.Dialog().notification(
        ADDON_NAME, f'{provider.capitalize()}: added link', ADDON_ICON)


def remove_link(provider):
    items = _load(provider)
    if not items:
        xbmcgui.Dialog().notification(
            ADDON_NAME, f'{provider.capitalize()}: no links', ADDON_ICON)
        return
    labels = [i.get('label') or i.get('url', '')[:60] for i in items]
    idx = xbmcgui.Dialog().select('Remove link', labels)
    if idx < 0:
        return
    items.pop(idx)
    _save(provider, items)
    xbmcgui.Dialog().notification(
        ADDON_NAME, f'{provider.capitalize()}: link removed', ADDON_ICON)


def _derive_name(entry):
    if entry.get('label'):
        return entry['label']
    url = entry.get('url', '')
    tail = url.rstrip('/').rsplit('/', 1)[-1]
    return tail or url


def list_all_videos(provider, progress_cb=None):
    items = _load(provider)
    out = []
    for i, e in enumerate(items):
        name = _derive_name(e)
        # If the link itself looks like a filename, keep extension intact.
        if '.' not in name.rsplit('.', 1)[-1][:5]:
            name = f'{name}.mp4'
        out.append({
            'id': str(i),
            'name': name,
            'size': 0,
            'mimeType': 'video/mp4',
            'modifiedTime': '',
        })
        if progress_cb:
            try:
                progress_cb(i + 1, len(out))
            except Exception:
                pass
    return out


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------

_SYNC_DIRECT_RE = re.compile(
    r'"(?:download_url|file_url|streaming_url|preview_url)"\s*:\s*"([^"]+)"',
    re.I)
_SYNC_LINKID_RE = re.compile(
    r'sync\.com/dl/([A-Za-z0-9]+)(?:/|#|"|\b)', re.I)
_SYNC_CONFIG_LINKID_RE = re.compile(
    r'"link_id"\s*:\s*"([A-Za-z0-9]+)"', re.I)
_SYNC_CACHEKEY_RE = re.compile(
    r'"cachekey"\s*:\s*"([A-Za-z0-9]+)"', re.I)
_IDRIVE_DIRECT_RE = re.compile(
    r'(https?://[^"\'\s]+\.(?:mp4|mkv|avi|mov|m4v|webm)[^"\'\s]*)', re.I)
_GENERIC_VIDEO_RE = re.compile(
    r'(https?://[^"\'\s]+\.(?:mp4|mkv|avi|mov|m4v|webm)(?:\?[^"\'\s]*)?)', re.I)


def _fetch_html(url, timeout=15):
    try:
        req = Request(url, headers={
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0 Safari/537.36'),
            'Accept-Language': 'en-US,en;q=0.9',
        })
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        xbmc.log(f'sharedlinks fetch {url}: {e}', xbmc.LOGDEBUG)
        return ''


def _sync_resolve(url, html):
    """Sync.com share pages embed `link_id` + `cachekey` in JS; the public
    download endpoint is /getlinkmeta which returns a JSON blob containing
    a signed `download_url`.  We try the meta endpoint first, then fall
    back to scraping any direct URL we find on the page."""
    import json as _json

    link_id = None
    m = _SYNC_LINKID_RE.search(url) or _SYNC_LINKID_RE.search(html)
    if m:
        link_id = m.group(1)
    if not link_id:
        m = _SYNC_CONFIG_LINKID_RE.search(html)
        if m:
            link_id = m.group(1)
    cachekey = None
    m = _SYNC_CACHEKEY_RE.search(html)
    if m:
        cachekey = m.group(1)

    if link_id:
        for endpoint in ('https://cp.sync.com/getlinkmeta',
                         'https://www.sync.com/getlinkmeta'):
            try:
                body = {'linkID': link_id}
                if cachekey:
                    body['cachekey'] = cachekey
                data = _json.dumps(body).encode('utf-8')
                req = Request(endpoint, data=data, headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 SALTS',
                })
                with urlopen(req, timeout=15) as r:
                    meta = _json.loads(r.read().decode('utf-8', 'ignore'))
                for k in ('download_url', 'streaming_url',
                          'preview_url', 'file_url'):
                    v = meta.get(k) if isinstance(meta, dict) else None
                    if isinstance(v, str) and v.startswith('http'):
                        return v.replace('\\/', '/')
            except Exception as e:
                xbmc.log(f'sharedlinks sync meta: {e}', xbmc.LOGDEBUG)

    m = _SYNC_DIRECT_RE.search(html)
    if m:
        return m.group(1).replace('\\/', '/')
    return None


def _resolve(provider, url):
    """Best-effort extraction of a direct video URL from a share page."""
    if not url:
        return None
    html = _fetch_html(url)
    if not html:
        return None
    if provider == 'sync':
        direct = _sync_resolve(url, html)
        if direct:
            return direct
    if provider == 'idrive':
        m = _IDRIVE_DIRECT_RE.search(html)
        if m:
            return m.group(1)
    # Generic last resort: first .mp4/.mkv URL on the page.
    m = _GENERIC_VIDEO_RE.search(html)
    return m.group(1) if m else None


def _get_entry(provider, file_id):
    try:
        idx = int(file_id)
    except Exception:
        return None
    items = _load(provider)
    if 0 <= idx < len(items):
        return items[idx]
    return None


def get_stream_url(provider, file_id):
    e = _get_entry(provider, file_id)
    if not e:
        return None
    direct = _resolve(provider, e.get('url', ''))
    return direct or e.get('url')


def get_share_url(provider, file_id):
    """For debrid we always hand back the original share URL - the debrid host
    is usually better at solving these than we are."""
    e = _get_entry(provider, file_id)
    return e.get('url') if e else None
