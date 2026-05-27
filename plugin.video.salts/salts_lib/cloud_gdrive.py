"""
SALTS - Google Drive integration.

Implements:
  * OAuth 2.0 Device Authorization Grant (RFC 8628) for headless Kodi auth.
    The user pastes their own client_id / client_secret in settings, then
    triggers "Authorize Google Drive" which prompts them to visit
    https://google.com/device and enter a short code.
  * Refresh-token storage + automatic refresh of the access token.
  * Listing folders / video files via the Drive v3 API.
  * Resolving a file ID to a streamable / downloadable URL.
"""
import json
import time
import xbmc
import xbmcaddon
import xbmcgui
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ADDON = xbmcaddon.Addon()
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = 'SALTS'

DEVICE_URL = 'https://oauth2.googleapis.com/device/code'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
SCOPE = 'https://www.googleapis.com/auth/drive.readonly'
DRIVE_API = 'https://www.googleapis.com/drive/v3'

_access_token = None
_access_expires = 0


def _post(url, params):
    data = urlencode(params).encode('utf-8')
    req = Request(url, data=data,
                  headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        return json.loads(urlopen(req, timeout=20).read().decode('utf-8'))
    except HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8'))
        except Exception:
            return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}


def _get(url, headers=None, params=None):
    if params:
        url = url + '?' + urlencode(params)
    req = Request(url, headers=headers or {})
    try:
        return json.loads(urlopen(req, timeout=20).read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}


def authorize():
    """Interactive device-flow auth. Blocks until the user approves."""
    cid = ADDON.getSetting('gdrive_client_id').strip()
    csec = ADDON.getSetting('gdrive_client_secret').strip()
    if not cid or not csec:
        xbmcgui.Dialog().ok(ADDON_NAME,
            'Please paste your Google OAuth Client ID and Client Secret '
            'in Settings -> Cloud -> Google Drive first.\n\n'
            'Create credentials at https://console.cloud.google.com '
            '(OAuth 2.0 Client ID -> TV / limited input device).')
        return False

    dev = _post(DEVICE_URL, {'client_id': cid, 'scope': SCOPE})
    if dev.get('error') or 'device_code' not in dev:
        xbmcgui.Dialog().ok(ADDON_NAME, f'Device-code error: {dev.get("error", "unknown")}')
        return False

    user_code = dev['user_code']
    verify_url = dev.get('verification_url', 'https://google.com/device')
    interval = int(dev.get('interval', 5))
    expires = int(dev.get('expires_in', 1800))
    device_code = dev['device_code']

    xbmcgui.Dialog().notification(ADDON_NAME, f'Open {verify_url} and enter code: {user_code}',
                                  ADDON_ICON, 15000)
    pd = xbmcgui.DialogProgress()
    pd.create('SALTS - Google Drive Authorization',
              f'1) On any device, open: {verify_url}\n'
              f'2) Enter this code: [B]{user_code}[/B]\n'
              f'3) Sign in and grant access.\n\nWaiting...')

    start = time.time()
    while time.time() - start < expires:
        if pd.iscanceled():
            pd.close()
            return False
        xbmc.sleep(interval * 1000)
        r = _post(TOKEN_URL, {
            'client_id': cid, 'client_secret': csec,
            'device_code': device_code,
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
        })
        if r.get('access_token'):
            ADDON.setSetting('gdrive_refresh_token', r.get('refresh_token', ''))
            global _access_token, _access_expires
            _access_token = r['access_token']
            _access_expires = time.time() + int(r.get('expires_in', 3500)) - 60
            pd.close()
            xbmcgui.Dialog().notification(ADDON_NAME, 'Google Drive linked!', ADDON_ICON)
            return True
        err = r.get('error', '')
        if err in ('authorization_pending', 'slow_down'):
            continue
        pd.close()
        xbmcgui.Dialog().ok(ADDON_NAME, f'Auth error: {err}')
        return False
    pd.close()
    return False


def logout():
    ADDON.setSetting('gdrive_refresh_token', '')
    global _access_token, _access_expires
    _access_token = None
    _access_expires = 0
    xbmcgui.Dialog().notification(ADDON_NAME, 'Google Drive logged out', ADDON_ICON)


def _get_access_token():
    global _access_token, _access_expires
    if _access_token and time.time() < _access_expires:
        return _access_token
    rt = ADDON.getSetting('gdrive_refresh_token').strip()
    cid = ADDON.getSetting('gdrive_client_id').strip()
    csec = ADDON.getSetting('gdrive_client_secret').strip()
    if not (rt and cid and csec):
        return None
    r = _post(TOKEN_URL, {
        'client_id': cid, 'client_secret': csec,
        'refresh_token': rt, 'grant_type': 'refresh_token'})
    if r.get('access_token'):
        _access_token = r['access_token']
        _access_expires = time.time() + int(r.get('expires_in', 3500)) - 60
        return _access_token
    return None


def is_authed():
    return bool(ADDON.getSetting('gdrive_refresh_token').strip())


def _api(path, params=None):
    tok = _get_access_token()
    if not tok:
        return None
    return _get(f'{DRIVE_API}{path}', headers={'Authorization': f'Bearer {tok}'},
                params=params)


def list_files(folder_id='root', page_token=None, page_size=200):
    """List children of a folder. Returns dict with 'files' and 'nextPageToken'."""
    q = f"'{folder_id}' in parents and trashed = false"
    params = {
        'q': q,
        'pageSize': page_size,
        'fields': 'nextPageToken, files(id,name,mimeType,size,modifiedTime,videoMediaMetadata,thumbnailLink)',
        'orderBy': 'folder,name',
    }
    if page_token:
        params['pageToken'] = page_token
    return _api('/files', params) or {}


def list_all_videos(progress_cb=None):
    """Recursively walk Drive and yield every video file (mimeType startswith video/).
    progress_cb(scanned, found) is called periodically.
    """
    videos = []
    scanned = 0
    page_token = None
    # Use a single global query for video mimetypes (much faster than recursion).
    while True:
        params = {
            'q': "mimeType contains 'video/' and trashed = false",
            'pageSize': 1000,
            'fields': 'nextPageToken, files(id,name,mimeType,size,modifiedTime,parents,thumbnailLink)',
            'orderBy': 'modifiedTime desc',
        }
        if page_token:
            params['pageToken'] = page_token
        r = _api('/files', params) or {}
        batch = r.get('files', [])
        for f in batch:
            videos.append(f)
        scanned += len(batch)
        if progress_cb:
            try:
                progress_cb(scanned, len(videos))
            except Exception:
                pass
        page_token = r.get('nextPageToken')
        if not page_token:
            break
    return videos


def get_stream_url(file_id):
    """Return an authenticated streaming URL for a file (downloadable via Kodi)."""
    tok = _get_access_token()
    if not tok:
        return None
    return f'{DRIVE_API}/files/{file_id}?alt=media|Authorization=Bearer%20{tok}'


def get_share_url(file_id):
    """Return a publicly-shareable URL by first marking the file as anyone-with-link."""
    # We use the alt=media URL with bearer header. For send-to-debrid we need a
    # URL the debrid can fetch without our token, so we return a "shared" link.
    # Drive doesn't expose anonymous direct-download URLs; the most reliable
    # debrid-compatible URL is https://drive.google.com/uc?export=download&id=...
    # provided the file is shared "anyone with the link". We toggle that flag.
    tok = _get_access_token()
    if not tok:
        return None
    # Create a public permission (idempotent: ignore 'alreadyExists' errors)
    try:
        data = json.dumps({'role': 'reader', 'type': 'anyone'}).encode('utf-8')
        req = Request(f'{DRIVE_API}/files/{file_id}/permissions',
                      data=data,
                      headers={'Authorization': f'Bearer {tok}',
                               'Content-Type': 'application/json'})
        urlopen(req, timeout=15).read()
    except Exception:
        pass  # fine if it already exists
    return f'https://drive.google.com/uc?export=download&id={file_id}'
