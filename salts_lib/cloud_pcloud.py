"""
SALTS - pCloud integration.

Uses pCloud's public JSON API (https://api.pcloud.com or eapi.pcloud.com for
EU accounts).  Auth via username+password -> persistent auth token stored in
the Kodi settings.  Provides the same surface as cloud_gdrive / cloud_mega:

  is_authed(), authorize(), logout(),
  list_all_videos(progress_cb=None),
  get_stream_url(file_id), get_share_url(file_id)

`file_id` here is the pCloud `fileid` (integer, stored as string).
"""
import json
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = 'SALTS'

VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.ts',
             '.flv', '.wmv', '.mpg', '.mpeg', '.m2ts')


def _api_base():
    region = (ADDON.getSetting('pcloud_region') or 'global').strip().lower()
    return 'https://eapi.pcloud.com' if region == 'eu' else 'https://api.pcloud.com'


def _get(path, params):
    url = f'{_api_base()}{path}?{urlencode(params)}'
    try:
        with urlopen(Request(url, headers={'User-Agent': 'SALTS/1.0'}),
                     timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        xbmc.log(f'pCloud GET {path}: {e}', xbmc.LOGWARNING)
        return {'error': str(e)}


def is_authed():
    return bool(ADDON.getSetting('pcloud_auth_token').strip())


def authorize():
    """Username + password -> persistent auth token."""
    user = ADDON.getSetting('pcloud_username').strip()
    pwd = ADDON.getSetting('pcloud_password').strip()
    if not user or not pwd:
        xbmcgui.Dialog().ok(ADDON_NAME,
            'Set pCloud email and password in Settings -> Cloud -> pCloud '
            'first, then press Authorize pCloud again.')
        return False

    r = _get('/userinfo',
             {'getauth': 1, 'logout': 0, 'username': user, 'password': pwd})
    if r.get('result') != 0 or not r.get('auth'):
        msg = r.get('error') or f'result={r.get("result")}'
        xbmcgui.Dialog().ok(ADDON_NAME, f'pCloud login failed: {msg}')
        return False

    ADDON.setSetting('pcloud_auth_token', r['auth'])
    xbmcgui.Dialog().notification(ADDON_NAME, 'pCloud linked!', ADDON_ICON)
    return True


def logout():
    tok = ADDON.getSetting('pcloud_auth_token').strip()
    if tok:
        _get('/logout', {'auth': tok})
    ADDON.setSetting('pcloud_auth_token', '')
    xbmcgui.Dialog().notification(ADDON_NAME, 'pCloud logged out', ADDON_ICON)


def _auth():
    return ADDON.getSetting('pcloud_auth_token').strip()


def _walk(folder_id, out, progress_cb, scanned_box):
    r = _get('/listfolder', {'auth': _auth(), 'folderid': folder_id,
                             'nofiles': 0, 'iconformat': 'id'})
    if r.get('result') != 0:
        return
    contents = (r.get('metadata') or {}).get('contents') or []
    for item in contents:
        scanned_box[0] += 1
        if item.get('isfolder'):
            _walk(item.get('folderid'), out, progress_cb, scanned_box)
            continue
        name = item.get('name', '')
        if not name.lower().endswith(VIDEO_EXT):
            # Be lenient: also accept by detected category (1=image, 2=video)
            if item.get('category') != 2:
                continue
        out.append({
            'id': str(item.get('fileid') or ''),
            'name': name,
            'size': int(item.get('size') or 0),
            'mimeType': item.get('contenttype', 'video/mp4'),
            'modifiedTime': item.get('modified', ''),
        })
        if progress_cb and (scanned_box[0] % 25 == 0):
            try:
                progress_cb(scanned_box[0], len(out))
            except Exception:
                pass


def list_all_videos(progress_cb=None):
    if not is_authed():
        return []
    out, scanned = [], [0]
    _walk(0, out, progress_cb, scanned)   # 0 = root folder
    if progress_cb:
        try:
            progress_cb(scanned[0], len(out))
        except Exception:
            pass
    return out


def get_stream_url(file_id):
    """Resolve to a direct streaming URL (host + path returned by pCloud)."""
    if not file_id:
        return None
    r = _get('/getfilelink', {'auth': _auth(), 'fileid': file_id,
                              'forcedownload': 0, 'skipfilename': 1})
    if r.get('result') != 0:
        return None
    hosts = r.get('hosts') or []
    path = r.get('path') or ''
    if not hosts or not path:
        return None
    return f'https://{hosts[0]}{path}'


def get_share_url(file_id):
    """Create / reuse a public link and return its direct download URL."""
    if not file_id:
        return None
    r = _get('/getfilepublink', {'auth': _auth(), 'fileid': file_id})
    code = r.get('code')
    if not code:
        # Sometimes pCloud refuses dup creation; query existing publinks.
        return None
    pl = _get('/getpublinkdownload', {'code': code})
    hosts = pl.get('hosts') or []
    path = pl.get('path') or ''
    if hosts and path:
        return f'https://{hosts[0]}{path}'
    return f'https://my.pcloud.com/publink/show?code={code}'
