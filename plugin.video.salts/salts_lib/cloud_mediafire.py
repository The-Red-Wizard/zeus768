"""
SALTS - MediaFire integration (anonymous public-folder mode).

MediaFire closed their public developer self-signup around 2019, so the
old email+password+application_id+signature flow is no longer reachable
for new users.  Fortunately MediaFire's REST API v1.5 lets us walk any
folder marked "Share -> Anyone with the link" anonymously via:

    /folder/get_content.php?folder_key=<KEY>&content_type=files
    /folder/get_content.php?folder_key=<KEY>&content_type=folders

and resolve files via:

    /file/get_links.php?quick_key=<QK>&link_type=direct_download

No api_key, no application_id, no signature.  The user pastes one or
more public folder keys (or full mediafire.com/folder/<key>/... URLs)
into Settings; SALTS walks every one and indexes the videos.

Folder list is stored at:
    special://profile/addon_data/plugin.video.salts/mediafire_folders.json

Public surface (unchanged for cloud_library.py):
  is_authed(), authorize(), logout(),
  list_all_videos(progress_cb=None),
  get_stream_url(file_id), get_share_url(file_id)
"""
import json
import os
import re
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


def is_authed():
    return len(_load_folders()) > 0


def authorize():
    """Prompt the user for a MediaFire public folder link or key."""
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


def logout():
    """Remove a folder (or all of them)."""
    items = _load_folders()
    if not items:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No MediaFire folders',
                                      ADDON_ICON)
        return
    labels = [f'{i["label"]}   ({i["key"]})' for i in items] + \
             ['[B]Remove ALL[/B]']
    idx = xbmcgui.Dialog().select('Remove MediaFire folder', labels)
    if idx < 0:
        return
    if idx == len(items):
        _save_folders([])
        xbmcgui.Dialog().notification(ADDON_NAME,
                                      'All MediaFire folders removed',
                                      ADDON_ICON)
        return
    items.pop(idx)
    _save_folders(items)
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


def list_all_videos(progress_cb=None):
    out, scanned = [], [0]
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
