"""
SALTS - MediaFire integration (public folder + account login mode).

Supports two modes:
1. Anonymous public folder mode (via folder keys)
2. Account login mode (email + password for full access)

MediaFire closed their public developer self-signup around 2019, but we can
still use the API with user credentials for account-based access.

Public folder mode uses:
    /folder/get_content.php?folder_key=<KEY>&content_type=files

Account mode uses session tokens from:
    /user/get_session_token.php

Files are resolved via:
    /file/get_links.php?quick_key=<QK>&link_type=direct_download

Storage:
    mediafire_folders.json - public folder keys
    mediafire_session.json - account session data

Public surface:
  is_authed(), authorize(), logout(),
  list_all_videos(progress_cb=None),
  get_stream_url(file_id), get_share_url(file_id)
"""
import json
import os
import re
import hashlib
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = 'SALTS'

API = 'https://www.mediafire.com/api/1.5'

DATA = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
STORE = os.path.join(DATA, 'mediafire_folders.json')
SESSION_STORE = os.path.join(DATA, 'mediafire_session.json')

VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.ts',
             '.flv', '.wmv', '.mpg', '.mpeg', '.m2ts')

# Folder URL examples we accept:
#   https://www.mediafire.com/folder/abc123def456/MyMovies
#   https://app.mediafire.com/abc123def456
#   abc123def456
_KEY_RE = re.compile(r'(?:folder/|app\.mediafire\.com/)([a-z0-9]{8,})', re.I)


def _get(path, params):
    params = dict(params or {})
    params['response_format'] = 'json'
    url = f'{API}{path}?{urlencode(params)}'
    try:
        with urlopen(Request(url, headers={'User-Agent': 'SALTS/1.0'}),
                     timeout=25) as resp:
            return json.loads(resp.read().decode('utf-8')).get('response', {})
    except Exception as e:
        xbmc.log(f'MediaFire GET {path}: {e}', xbmc.LOGWARNING)
        return {'result': 'Error', 'message': str(e)}


def _load_folders():
    if not os.path.isfile(STORE):
        return []
    try:
        with open(STORE, 'r', encoding='utf-8') as fh:
            return json.load(fh) or []
    except Exception:
        return []


def _save_folders(items):
    try:
        os.makedirs(DATA, exist_ok=True)
        with open(STORE, 'w', encoding='utf-8') as fh:
            json.dump(items, fh, indent=2)
    except Exception as e:
        xbmc.log(f'MediaFire folders save: {e}', xbmc.LOGWARNING)


def _extract_key(text):
    text = (text or '').strip()
    if not text:
        return ''
    m = _KEY_RE.search(text)
    if m:
        return m.group(1)
    # Accept a raw key if it looks like one.
    if re.fullmatch(r'[a-z0-9]{8,}', text, re.I):
        return text
    return ''


def _load_session():
    """Load account session data."""
    if not os.path.isfile(SESSION_STORE):
        return None
    try:
        with open(SESSION_STORE, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return None


def _save_session(session_data):
    """Save account session data."""
    try:
        os.makedirs(DATA, exist_ok=True)
        with open(SESSION_STORE, 'w', encoding='utf-8') as fh:
            json.dump(session_data, fh, indent=2)
    except Exception as e:
        xbmc.log(f'MediaFire session save: {e}', xbmc.LOGWARNING)


def _clear_session():
    """Clear account session."""
    try:
        if os.path.isfile(SESSION_STORE):
            os.remove(SESSION_STORE)
    except Exception:
        pass


def is_authed():
    """Check if authenticated (either account or public folders)."""
    return _load_session() is not None or len(_load_folders()) > 0


def login_with_account(email, password):
    """Login with MediaFire account credentials.
    Returns True on success, False otherwise."""
    if not email or not password:
        return False
    
    # Try to get session token using email/password
    # MediaFire API endpoint for getting session token
    try:
        params = {
            'email': email,
            'password': password,
            'response_format': 'json'
        }
        url = f'{API}/user/get_session_token.php?{urlencode(params)}'
        req = Request(url, headers={'User-Agent': 'SALTS/1.0'})
        
        with urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            response = data.get('response', {})
            
            if response.get('result') == 'Success':
                session_token = response.get('session_token', '')
                if session_token:
                    session_data = {
                        'session_token': session_token,
                        'email': email,
                        'mode': 'account'
                    }
                    _save_session(session_data)
                    return True
            elif response.get('result') == 'Error':
                msg = response.get('message', 'Unknown error')
                xbmcgui.Dialog().ok(ADDON_NAME, 
                    f'MediaFire login failed:\n{msg}')
                return False
    except Exception as e:
        xbmc.log(f'MediaFire account login error: {e}', xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(ADDON_NAME,
            'MediaFire login failed. Please check your credentials.')
    
    return False


def authorize():
    """Prompt user to choose between account login or public folder."""
    options = ['Login with Account (Email + Password)', 'Add Public Folder Link']
    idx = xbmcgui.Dialog().select('MediaFire Authorization', options)
    
    if idx == 0:
        # Account login
        email = xbmcgui.Dialog().input('Enter MediaFire Email', type=xbmcgui.INPUT_ALPHANUM)
        if not email:
            return False
        
        password = xbmcgui.Dialog().input('Enter MediaFire Password', 
                                         type=xbmcgui.INPUT_ALPHANUM,
                                         option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if not password:
            return False
        
        if login_with_account(email, password):
            xbmcgui.Dialog().notification(ADDON_NAME, 
                f'MediaFire account connected: {email}', ADDON_ICON, 4000)
            return True
        return False
    
    elif idx == 1:
        # Public folder mode
        raw = xbmcgui.Dialog().input(
            'Paste MediaFire public folder link or key',
            type=xbmcgui.INPUT_ALPHANUM)
        key = _extract_key(raw)
        if not key:
            xbmcgui.Dialog().ok(ADDON_NAME,
                'That does not look like a MediaFire folder key.\n\n'
                'On the MediaFire site, right-click your folder -> '
                'Share -> "Anyone with the link". Copy the link (it looks '
                'like https://www.mediafire.com/folder/ABC123DEF456/Movies) '
                'and paste the whole URL here.')
            return False

        # Verify the folder is reachable.
        probe = _get('/folder/get_info.php', {'folder_key': key})
        if probe.get('result') != 'Success':
            xbmcgui.Dialog().ok(
                ADDON_NAME,
                'MediaFire rejected that folder key.\n\n'
                'Make sure the folder is shared "Anyone with the link" '
                '(not just "people I invite"), then try again.')
            return False

        label = (probe.get('folder_info') or {}).get('name') or key
        items = _load_folders()
        if not any(it.get('key') == key for it in items):
            items.append({'key': key, 'label': label})
            _save_folders(items)
        xbmcgui.Dialog().notification(
            ADDON_NAME, f'MediaFire folder added: {label}', ADDON_ICON, 4000)
        return True
    
    return False


def logout():
    """Remove account or folder (or all of them)."""
    session = _load_session()
    folders = _load_folders()
    
    if not session and not folders:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No MediaFire connection',
                                      ADDON_ICON)
        return
    
    options = []
    if session:
        options.append(f'[B]Logout Account[/B] ({session.get("email", "")})') 
    
    if folders:
        for i in folders:
            options.append(f'{i["label"]}   ({i["key"]})')
        options.append('[B]Remove ALL Folders[/B]')
    
    idx = xbmcgui.Dialog().select('Remove MediaFire Connection', options)
    if idx < 0:
        return
    
    if session and idx == 0:
        # Logout account
        _clear_session()
        xbmcgui.Dialog().notification(ADDON_NAME,
                                      'MediaFire account logged out',
                                      ADDON_ICON)
        return
    
    # Adjust index if account is present
    folder_offset = 1 if session else 0
    folder_idx = idx - folder_offset
    
    if folder_idx == len(folders):
        # Remove all folders
        _save_folders([])
        xbmcgui.Dialog().notification(ADDON_NAME,
                                      'All MediaFire folders removed',
                                      ADDON_ICON)
        return
    
    if 0 <= folder_idx < len(folders):
        folders.pop(folder_idx)
        _save_folders(folders)
        xbmcgui.Dialog().notification(ADDON_NAME,
                                      'MediaFire folder removed', ADDON_ICON)


def _list_content(folder_key, content_type, chunk):
    return _get('/folder/get_content.php', {
        'folder_key': folder_key,
        'content_type': content_type,   # 'files' or 'folders'
        'chunk': chunk,
        'chunk_size': 100,
        'order_by': 'name',
    })


def _walk(folder_key, out, progress_cb, scanned_box):
    # Files
    chunk = 1
    while True:
        r = _list_content(folder_key, 'files', chunk)
        if r.get('result') != 'Success':
            break
        files = (r.get('folder_content') or {}).get('files') or []
        for f in files:
            scanned_box[0] += 1
            name = f.get('filename', '')
            if not name.lower().endswith(VIDEO_EXT):
                continue
            out.append({
                'id': f.get('quickkey', ''),
                'name': name,
                'size': int(f.get('size') or 0),
                'mimeType': f.get('mimetype') or 'video/mp4',
                'modifiedTime': f.get('created') or '',
            })
        if (r.get('folder_content') or {}).get('more_chunks') != 'yes':
            break
        chunk += 1
        if progress_cb:
            try:
                progress_cb(scanned_box[0], len(out))
            except Exception:
                pass

    # Subfolders
    chunk = 1
    while True:
        r = _list_content(folder_key, 'folders', chunk)
        if r.get('result') != 'Success':
            break
        sub = (r.get('folder_content') or {}).get('folders') or []
        for fl in sub:
            _walk(fl.get('folderkey', ''), out, progress_cb, scanned_box)
        if (r.get('folder_content') or {}).get('more_chunks') != 'yes':
            break
        chunk += 1


def _list_content_with_session(folder_key, content_type, chunk, session_token):
    """List folder content using authenticated session."""
    return _get('/folder/get_content.php', {
        'folder_key': folder_key,
        'content_type': content_type,
        'chunk': chunk,
        'chunk_size': 100,
        'order_by': 'name',
        'session_token': session_token,
    })


def _walk_account(folder_key, out, progress_cb, scanned_box, session_token):
    """Walk MediaFire account folders with authentication."""
    # Files
    chunk = 1
    while True:
        r = _list_content_with_session(folder_key, 'files', chunk, session_token)
        if r.get('result') != 'Success':
            break
        files = (r.get('folder_content') or {}).get('files') or []
        for f in files:
            scanned_box[0] += 1
            name = f.get('filename', '')
            if not name.lower().endswith(VIDEO_EXT):
                continue
            out.append({
                'id': f.get('quickkey', ''),
                'name': name,
                'size': int(f.get('size') or 0),
                'mimeType': f.get('mimetype') or 'video/mp4',
                'modifiedTime': f.get('created') or '',
            })
        if (r.get('folder_content') or {}).get('more_chunks') != 'yes':
            break
        chunk += 1
        if progress_cb:
            try:
                progress_cb(scanned_box[0], len(out))
            except Exception:
                pass

    # Subfolders
    chunk = 1
    while True:
        r = _list_content_with_session(folder_key, 'folders', chunk, session_token)
        if r.get('result') != 'Success':
            break
        sub = (r.get('folder_content') or {}).get('folders') or []
        for fl in sub:
            _walk_account(fl.get('folderkey', ''), out, progress_cb, scanned_box, session_token)
        if (r.get('folder_content') or {}).get('more_chunks') != 'yes':
            break
        chunk += 1


def list_all_videos(progress_cb=None):
    out, scanned = [], [0]
    
    # Try account mode first
    session = _load_session()
    if session and session.get('session_token'):
        session_token = session['session_token']
        # List from root folder for account
        _walk_account('myfiles', out, progress_cb, scanned, session_token)
    
    # Also include public folders
    for entry in _load_folders():
        _walk(entry.get('key', ''), out, progress_cb, scanned)
    
    if progress_cb:
        try:
            progress_cb(scanned[0], len(out))
        except Exception:
            pass
    return out


def get_stream_url(file_id):
    """Resolve a quickkey to a direct-download URL (works without auth for
    files that live in a public folder)."""
    if not file_id:
        return None
    r = _get('/file/get_links.php', {
        'quick_key': file_id,
        'link_type': 'direct_download',
    })
    if r.get('result') != 'Success':
        return None
    links = r.get('links') or []
    if not links:
        return None
    return links[0].get('direct_download') or links[0].get('normal_download')


def get_share_url(file_id):
    """Public download-page URL (debrid-friendly)."""
    if not file_id:
        return None
    r = _get('/file/get_links.php', {
        'quick_key': file_id,
        'link_type': 'normal_download',
    })
    if r.get('result') == 'Success':
        links = r.get('links') or []
        if links:
            return (links[0].get('normal_download') or
                    f'https://www.mediafire.com/file/{file_id}')
    return f'https://www.mediafire.com/file/{file_id}'
