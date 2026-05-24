"""
SALTS - Sync.com integration (share links + account simulation).

Since Sync.com doesn't provide a public API or WebDAV access, this module
uses an enhanced shared-link approach with account-style UI:

1. Account Mode (Simulated):
   - User provides email for identification
   - Links are managed under that account context
   - Better organization and UX

2. Share Links Mode:
   - Traditional paste-share-link approach
   - Each link can be labeled
   - Supports multiple folders/files

Storage:
    sync_account.json - account info (email, mode)
    sync_links.json - shared links list

Public surface:
  is_authed(), authorize(), logout(),
  list_all_videos(progress_cb=None),
  get_stream_url(file_id), get_share_url(file_id)
"""
import json
import os
import re
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = 'SALTS'

DATA = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
ACCOUNT_STORE = os.path.join(DATA, 'sync_account.json')
LINKS_STORE = os.path.join(DATA, 'sync_links.json')

VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.ts',
             '.flv', '.wmv', '.mpg', '.mpeg', '.m2ts')

# Sync.com share link patterns
_SYNC_DIRECT_RE = re.compile(
    r'"(?:download_url|file_url|streaming_url|preview_url)"\s*:\s*"([^"]+)"',
    re.I)
_SYNC_LINKID_RE = re.compile(
    r'sync\.com/dl/([A-Za-z0-9]+)(?:/|#|"|\b)', re.I)
_SYNC_CONFIG_LINKID_RE = re.compile(
    r'"link_id"\s*:\s*"([A-Za-z0-9]+)"', re.I)
_SYNC_CACHEKEY_RE = re.compile(
    r'"cachekey"\s*:\s*"([A-Za-z0-9]+)"', re.I)


def _load_account():
    """Load account data."""
    if not os.path.isfile(ACCOUNT_STORE):
        return None
    try:
        with open(ACCOUNT_STORE, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return None


def _save_account(account_data):
    """Save account data."""
    try:
        os.makedirs(DATA, exist_ok=True)
        with open(ACCOUNT_STORE, 'w', encoding='utf-8') as fh:
            json.dump(account_data, fh, indent=2)
    except Exception as e:
        xbmc.log(f'Sync.com account save: {e}', xbmc.LOGWARNING)


def _clear_account():
    """Clear account."""
    try:
        if os.path.isfile(ACCOUNT_STORE):
            os.remove(ACCOUNT_STORE)
    except Exception:
        pass


def _load_links():
    """Load share links."""
    if not os.path.isfile(LINKS_STORE):
        return []
    try:
        with open(LINKS_STORE, 'r', encoding='utf-8') as fh:
            return json.load(fh) or []
    except Exception:
        return []


def _save_links(items):
    """Save share links."""
    try:
        os.makedirs(DATA, exist_ok=True)
        with open(LINKS_STORE, 'w', encoding='utf-8') as fh:
            json.dump(items, fh, indent=2)
    except Exception as e:
        xbmc.log(f'Sync.com links save: {e}', xbmc.LOGWARNING)


def is_authed():
    """Check if authenticated (either account or links)."""
    return _load_account() is not None or len(_load_links()) > 0


def setup_account(email):
    """Setup Sync.com account context (for link organization).
    Returns True on success."""
    if not email:
        return False
    
    account_data = {
        'email': email,
        'mode': 'organized_links',
        'created': xbmc.getInfoLabel('System.Date')
    }
    _save_account(account_data)
    
    xbmcgui.Dialog().ok(
        ADDON_NAME,
        f'Sync.com account setup complete!\n\n'
        f'Account: {email}\n\n'
        f'Now add your Sync.com share links to organize your cloud library.'
    )
    return True


def add_share_link():
    """Add a Sync.com share link."""
    url = xbmcgui.Dialog().input(
        'Paste Sync.com share link',
        type=xbmcgui.INPUT_ALPHANUM)
    if not url:
        return False
    
    # Validate it's a Sync.com link
    if 'sync.com' not in url.lower():
        xbmcgui.Dialog().ok(
            ADDON_NAME,
            'This does not appear to be a valid Sync.com share link.\n\n'
            'Share links should look like:\n'
            'https://cp.sync.com/dl/abc123xyz...'
        )
        return False
    
    label = xbmcgui.Dialog().input(
        'Friendly name for this link (optional)',
        type=xbmcgui.INPUT_ALPHANUM) or ''
    
    links = _load_links()
    
    # Check for duplicates
    url_clean = url.strip()
    if any(link.get('url') == url_clean for link in links):
        xbmcgui.Dialog().notification(
            ADDON_NAME, 'This link is already added', ADDON_ICON)
        return False
    
    links.append({
        'url': url_clean,
        'label': label.strip(),
        'added': xbmc.getInfoLabel('System.Date')
    })
    _save_links(links)
    
    xbmcgui.Dialog().notification(
        ADDON_NAME, 
        f'Sync.com link added: {label or "Share Link"}', 
        ADDON_ICON, 4000)
    return True


def authorize():
    """Authorize Sync.com - setup account or add link."""
    account = _load_account()
    
    if account:
        # Already have account setup, just add a link
        return add_share_link()
    else:
        # First time - offer to setup account context
        options = [
            'Setup Account (Recommended)',
            'Just Add Share Links (No Account)'
        ]
        idx = xbmcgui.Dialog().select('Sync.com Setup', options)
        
        if idx == 0:
            # Setup account
            email = xbmcgui.Dialog().input(
                'Enter your Sync.com email\n(for organization only)',
                type=xbmcgui.INPUT_ALPHANUM)
            if not email:
                return False
            
            if setup_account(email):
                # Now add first link
                return add_share_link()
            return False
        
        elif idx == 1:
            # Just add links without account
            return add_share_link()
    
    return False


def logout():
    """Logout - remove account and/or links."""
    account = _load_account()
    links = _load_links()
    
    if not account and not links:
        xbmcgui.Dialog().notification(
            ADDON_NAME, 'No Sync.com connection', ADDON_ICON)
        return
    
    options = []
    if account:
        options.append(f'[B]Remove Account[/B] ({account.get("email", "")})')
    
    if links:
        for link in links:
            label = link.get('label') or link.get('url', '')[:50]
            options.append(f'{label}')
        options.append('[B]Remove ALL Links[/B]')
    
    idx = xbmcgui.Dialog().select('Remove Sync.com Connection', options)
    if idx < 0:
        return
    
    if account and idx == 0:
        # Remove account
        _clear_account()
        xbmcgui.Dialog().notification(
            ADDON_NAME, 'Sync.com account removed', ADDON_ICON)
        return
    
    # Handle link removal
    link_offset = 1 if account else 0
    link_idx = idx - link_offset
    
    if link_idx == len(links):
        # Remove all links
        _save_links([])
        xbmcgui.Dialog().notification(
            ADDON_NAME, 'All Sync.com links removed', ADDON_ICON)
        return
    
    if 0 <= link_idx < len(links):
        links.pop(link_idx)
        _save_links(links)
        xbmcgui.Dialog().notification(
            ADDON_NAME, 'Sync.com link removed', ADDON_ICON)


def _fetch_html(url, timeout=15):
    """Fetch HTML from URL."""
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
        xbmc.log(f'Sync.com fetch {url}: {e}', xbmc.LOGDEBUG)
        return ''


def _sync_resolve(url, html):
    """Resolve Sync.com share page to direct download URL."""
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
                xbmc.log(f'Sync.com meta: {e}', xbmc.LOGDEBUG)
    
    m = _SYNC_DIRECT_RE.search(html)
    if m:
        return m.group(1).replace('\\/', '/')
    
    return None


def _derive_name(link):
    """Derive a friendly name from link data."""
    if link.get('label'):
        return link['label']
    url = link.get('url', '')
    tail = url.rstrip('/').rsplit('/', 1)[-1]
    return tail or 'Sync File'


def list_all_videos(progress_cb=None):
    """List all videos from share links."""
    links = _load_links()
    out = []
    
    for i, link in enumerate(links):
        name = _derive_name(link)
        # If name doesn't have extension, add .mp4
        if '.' not in name.rsplit('.', 1)[-1][:5]:
            name = f'{name}.mp4'
        
        out.append({
            'id': str(i),
            'name': name,
            'size': 0,
            'mimeType': 'video/mp4',
            'modifiedTime': link.get('added', ''),
        })
        
        if progress_cb:
            try:
                progress_cb(i + 1, len(out))
            except Exception:
                pass
    
    return out


def get_stream_url(file_id):
    """Resolve share link to direct download URL."""
    try:
        idx = int(file_id)
    except Exception:
        return None
    
    links = _load_links()
    if not (0 <= idx < len(links)):
        return None
    
    link = links[idx]
    url = link.get('url', '')
    
    if not url:
        return None
    
    html = _fetch_html(url)
    if not html:
        return url  # Fallback to original URL
    
    direct = _sync_resolve(url, html)
    return direct or url


def get_share_url(file_id):
    """Get original share URL for debrid services."""
    try:
        idx = int(file_id)
    except Exception:
        return None
    
    links = _load_links()
    if 0 <= idx < len(links):
        return links[idx].get('url')
    
    return None
