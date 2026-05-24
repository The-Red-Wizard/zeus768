"""
SALTS - MEGA.nz integration via the `mega.py` library.

Lazy-imports `mega` so the addon still loads when the lib isn't installed.
If missing, prompts the user to install it (pip install mega.py inside Kodi).
"""
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = 'SALTS'

_session = None  # cached Mega() instance


def _mega():
    """Return a logged-in Mega() instance, or None on failure."""
    global _session
    if _session is not None:
        return _session
    try:
        from mega import Mega  # type: ignore
    except Exception:
        xbmcgui.Dialog().ok(ADDON_NAME,
            'The "mega.py" Python library is not installed.\n\n'
            'Install it inside Kodi:\n'
            '  pip install --user mega.py\n\n'
            'Or use the Emergent build that ships with it preinstalled.')
        return None
    email = ADDON.getSetting('mega_email').strip()
    pw = ADDON.getSetting('mega_password').strip()
    if not (email and pw):
        xbmcgui.Dialog().ok(ADDON_NAME,
            'Please set your MEGA email + password in '
            'Settings -> Cloud -> MEGA.nz first.')
        return None
    try:
        m = Mega().login(email, pw)
        _session = m
        return m
    except Exception as e:
        xbmcgui.Dialog().ok(ADDON_NAME, f'MEGA login failed: {e}')
        return None


def is_authed():
    return bool(ADDON.getSetting('mega_email').strip() and
                ADDON.getSetting('mega_password').strip())


_VIDEO_EXTS = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.wmv', '.flv',
               '.webm', '.ts', '.m2ts', '.mpg', '.mpeg')


def list_all_videos(progress_cb=None):
    """Return [{'id':node_handle,'name':...,'size':...}, ...] for every video file."""
    m = _mega()
    if not m:
        return []
    out = []
    try:
        files = m.get_files()  # {handle: node_dict}
    except Exception as e:
        xbmcgui.Dialog().notification(ADDON_NAME, f'MEGA list error: {e}', ADDON_ICON)
        return []
    scanned = 0
    for handle, node in files.items():
        # type 0 = file, 1 = folder. We want files only.
        if node.get('t') != 0:
            continue
        name = (node.get('a') or {}).get('n', '') if isinstance(node.get('a'), dict) else ''
        if not name:
            continue
        if not name.lower().endswith(_VIDEO_EXTS):
            continue
        out.append({
            'id': handle,
            'name': name,
            'size': node.get('s', 0),
        })
        scanned += 1
        if progress_cb and scanned % 25 == 0:
            try:
                progress_cb(scanned, len(out))
            except Exception:
                pass
    if progress_cb:
        try:
            progress_cb(scanned, len(out))
        except Exception:
            pass
    return out


def get_stream_url(handle):
    """Resolve a node handle to a temporary streamable HTTPS URL."""
    m = _mega()
    if not m:
        return None
    try:
        # mega.py exposes get_link / export_link for shared, and
        # _node_data + _download_url for direct. Public link is what
        # debrid services can also use, so return that.
        return m.get_link({handle: m.get_files()[handle]})
    except Exception:
        try:
            return m.export(handle)
        except Exception as e:
            xbmcgui.Dialog().notification(ADDON_NAME, f'MEGA URL error: {e}', ADDON_ICON)
            return None
