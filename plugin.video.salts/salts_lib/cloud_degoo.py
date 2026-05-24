"""
SALTS - Degoo cloud storage integration.

Provides two modes of operation:
1. Full account browsing via unofficial reverse-engineered Degoo GraphQL API
2. Shared-link mode for public Degoo share links (like Sync.com/iDrive)

**IMPORTANT**: Degoo has NO official public API. This implementation uses:
- Unofficial reverse-engineered GraphQL API (github.com/bernd-wechner/Degoo)
- May break at any time if Degoo changes their backend
- Account suspension risk with automated access
- Use at your own risk

To enable Degoo in SALTS:
1. Settings → Cloud → Degoo
2. Choose mode:
   a) Full Account Mode: Enter email + password, press "Authorize Degoo"
   b) Shared-Link Mode: Paste public Degoo share links

The module exposes the standard cloud-provider interface:
    is_authed(), list_all_videos(progress_cb=None),
    get_stream_url(file_id), get_share_url(file_id)
"""

import json
import os
import re
import sys
from urllib.parse import urljoin, quote
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_NAME = 'SALTS'

# Video file extensions
VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.ts',
             '.flv', '.wmv', '.mpg', '.mpeg', '.m2ts', '.3gp', '.divx')

# Degoo API configuration (from reverse-engineered API)
DEGOO_API_URL = "https://production-appsync.degoo.com/graphql"
DEGOO_LOGIN_URL = "https://rest-api.degoo.com/login"
DEGOO_TOKEN_URL = "https://rest-api.degoo.com/access-token/v2"
DEGOO_API_KEY = "da2-vs6twz5vnjdavpqndtbzg3prra"
DEGOO_USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0'

# Degoo item categories
DEGOO_CATS = {
    0: "File",
    1: "Device",
    2: "Folder",
    3: "Image",
    4: "Video",
    5: "Music",
    6: "Document",
    10: "Recycle Bin",
}

# Max items per API request (Degoo limitation)
DEGOO_LIMIT_MAX = 1000

# Shared links storage
DATA = xbmc.translatePath(
    f'special://profile/addon_data/{ADDON_ID}/'
) if hasattr(xbmc, 'translatePath') else ADDON.getAddonInfo('profile')


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _log(msg, level=xbmc.LOGDEBUG):
    """Log message to Kodi log."""
    try:
        xbmc.log(f'cloud_degoo: {msg}', level)
    except Exception:
        pass


def _is_video(name):
    """Check if filename is a video file based on extension."""
    return name.lower().endswith(VIDEO_EXT)


def _store_tokens():
    """Get path to Degoo auth tokens storage file."""
    try:
        os.makedirs(DATA, exist_ok=True)
    except Exception:
        pass
    return os.path.join(DATA, 'degoo_tokens.json')


def _store_sharedlinks():
    """Get path to Degoo shared links storage file."""
    try:
        os.makedirs(DATA, exist_ok=True)
    except Exception:
        pass
    return os.path.join(DATA, 'sharedlinks_degoo.json')


def _load_tokens():
    """Load Degoo authentication tokens from file."""
    fp = _store_tokens()
    if not os.path.isfile(fp):
        return {}
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            return json.load(fh) or {}
    except Exception as e:
        _log(f'Failed to load tokens: {e}', xbmc.LOGWARNING)
        return {}


def _save_tokens(tokens):
    """Save Degoo authentication tokens to file."""
    try:
        with open(_store_tokens(), 'w', encoding='utf-8') as fh:
            json.dump(tokens, fh, indent=2)
    except Exception as e:
        _log(f'Failed to save tokens: {e}', xbmc.LOGWARNING)


def _load_sharedlinks():
    """Load Degoo shared links from file."""
    fp = _store_sharedlinks()
    if not os.path.isfile(fp):
        return []
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            return json.load(fh) or []
    except Exception:
        return []


def _save_sharedlinks(links):
    """Save Degoo shared links to file."""
    try:
        with open(_store_sharedlinks(), 'w', encoding='utf-8') as fh:
            json.dump(links, fh, indent=2)
    except Exception as e:
        _log(f'Failed to save shared links: {e}', xbmc.LOGWARNING)


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------

def _get_mode():
    """
    Determine which mode is active:
    - 'account': Full account browsing mode
    - 'sharedlinks': Shared-link mode
    - None: No mode configured
    """
    mode = ADDON.getSetting('degoo_mode') or 'account'
    
    if mode == 'account':
        tokens = _load_tokens()
        if tokens.get('Token') and tokens.get('x-api-key'):
            return 'account'
    
    # Check shared links as fallback or explicit mode
    links = _load_sharedlinks()
    if links:
        return 'sharedlinks'
    
    return None


# ---------------------------------------------------------------------------
# Full Account Mode - Degoo GraphQL API
# ---------------------------------------------------------------------------

def _graphql_request(query, variables, operation_name):
    """
    Execute a GraphQL request to Degoo API.
    
    :param query: GraphQL query string
    :param variables: Query variables dict
    :param operation_name: Operation name
    :returns: Response data dict or None on error
    """
    tokens = _load_tokens()
    if not tokens.get('Token') or not tokens.get('x-api-key'):
        _log('No auth tokens available', xbmc.LOGWARNING)
        return None
    
    request_data = {
        "operationName": operation_name,
        "variables": variables,
        "query": query
    }
    
    headers = {
        'x-api-key': tokens['x-api-key'],
        'Content-Type': 'application/json',
        'User-Agent': DEGOO_USER_AGENT,
    }
    
    try:
        data = json.dumps(request_data).encode('utf-8')
        req = Request(DEGOO_API_URL, data=data, headers=headers)
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            
            if 'errors' in result:
                messages = [e.get('message', str(e)) for e in result['errors']]
                _log(f'{operation_name} errors: {messages}', xbmc.LOGWARNING)
                return None
            
            return result.get('data')
    except Exception as e:
        _log(f'{operation_name} request failed: {e}', xbmc.LOGWARNING)
        return None


def _get_file_children(parent_id, next_token=None):
    """
    Get children of a Degoo folder.
    
    :param parent_id: Degoo folder ID (0 for root)
    :param next_token: Pagination token for continued enumeration
    :returns: Tuple of (items list, next_token or None)
    """
    # Minimal properties needed for file listing
    properties = """
        ID
        Name
        FilePath
        Size
        Category
        URL
        MetadataID
        ParentID
        DeviceID
        IsInRecycleBin
    """
    
    query = f"""
    query GetFileChildren5($Token: String!, $ParentID: String, $Limit: Int!, $Order: Int!, $NextToken: String) {{
        getFileChildren5(Token: $Token, ParentID: $ParentID, Limit: $Limit, Order: $Order, NextToken: $NextToken) {{
            Items {{ {properties} }}
            NextToken
        }}
    }}
    """
    
    tokens = _load_tokens()
    variables = {
        "Token": tokens['Token'],
        "ParentID": f"{parent_id}",
        "Limit": DEGOO_LIMIT_MAX,
        "Order": 3
    }
    
    if next_token:
        variables["NextToken"] = next_token
    
    data = _graphql_request(query, variables, "GetFileChildren5")
    if not data or 'getFileChildren5' not in data:
        return ([], None)
    
    result = data['getFileChildren5']
    items = result.get('Items', [])
    next_token = result.get('NextToken')
    
    # Process items to convert IDs to int and add category names
    for item in items:
        try:
            item['ID'] = int(item.get('ID', 0))
            item['ParentID'] = int(item.get('ParentID', 0))
            item['Size'] = int(item.get('Size', 0))
            item['CategoryName'] = DEGOO_CATS.get(item.get('Category', 0), 'Unknown')
        except Exception:
            pass
    
    return (items, next_token)


def _walk_degoo_tree(parent_id=0, progress_cb=None):
    """
    Recursively walk Degoo directory tree and yield video files.
    
    :param parent_id: Starting folder ID (0 for root)
    :param progress_cb: Optional callback function (found_count, found_count)
    :yields: Dict with keys: id, name, size, mimeType, modifiedTime
    """
    found = 0
    stack = [parent_id]
    seen_folders = set()
    
    while stack:
        current_id = stack.pop()
        
        if current_id in seen_folders:
            continue
        seen_folders.add(current_id)
        
        # Get all children with pagination support
        next_token = None
        while True:
            items, next_token = _get_file_children(current_id, next_token)
            
            for item in items:
                cat = item.get('CategoryName', '')
                name = item.get('Name', '')
                item_id = item.get('ID', 0)
                
                # Add folders to stack for traversal
                if cat in ('Folder', 'Device'):
                    stack.append(item_id)
                
                # Yield video files
                elif _is_video(name):
                    found += 1
                    if progress_cb:
                        try:
                            progress_cb(found, found)
                        except Exception:
                            pass
                    
                    yield {
                        'id': str(item_id),
                        'name': name,
                        'size': item.get('Size', 0),
                        'mimeType': 'video/mp4',
                        'modifiedTime': '',
                    }
            
            # Break pagination loop if no more items
            if not next_token:
                break


def _get_file_url(file_id):
    """
    Get direct download URL for a Degoo file.
    
    :param file_id: Degoo file ID
    :returns: Direct URL or None
    """
    properties = """
        ID
        Name
        URL
        Size
    """
    
    query = f"""
    query GetOverlay4($Token: String!, $ID: IDType!) {{
        getOverlay4(Token: $Token, ID: $ID) {{
            {properties}
        }}
    }}
    """
    
    tokens = _load_tokens()
    variables = {
        "Token": tokens['Token'],
        "ID": {"FileID": int(file_id)}
    }
    
    data = _graphql_request(query, variables, "GetOverlay4")
    if not data or 'getOverlay4' not in data:
        return None
    
    overlay = data['getOverlay4']
    return overlay.get('URL')


# ---------------------------------------------------------------------------
# Shared-Link Mode (like Sync.com/iDrive)
# ---------------------------------------------------------------------------

_DEGOO_DIRECT_RE = re.compile(
    r'(https?://[^"\'\s]+\.(?:mp4|mkv|avi|mov|m4v|webm)[^"\'\s]*)',
    re.I)


def _resolve_shared_link(url):
    """
    Best-effort extraction of direct video URL from Degoo share page.
    
    :param url: Degoo share URL
    :returns: Direct URL or None
    """
    if not url:
        return None
    
    try:
        headers = {
            'User-Agent': DEGOO_USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.9',
        }
        req = Request(url, headers=headers)
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        
        # Try to find direct video URL in page
        match = _DEGOO_DIRECT_RE.search(html)
        if match:
            return match.group(1)
        
        # TODO: Add more sophisticated Degoo share link parsing
        # based on their web app structure
        
    except Exception as e:
        _log(f'Failed to resolve Degoo share link: {e}', xbmc.LOGDEBUG)
    
    return None


# ---------------------------------------------------------------------------
# Public interface for cloud_library.py
# ---------------------------------------------------------------------------

def is_authed():
    """
    Check if Degoo is configured (either mode).
    
    :returns: True if either account mode or shared-link mode is configured
    """
    mode = _get_mode()
    return mode is not None


def list_all_videos(progress_cb=None):
    """
    List all video files from Degoo (uses active mode).
    
    :param progress_cb: Optional callback function (current, total)
    :returns: List of dicts with keys: id, name, size, mimeType, modifiedTime
    """
    mode = _get_mode()
    
    if mode == 'account':
        # Full account browsing mode
        return list(_walk_degoo_tree(0, progress_cb=progress_cb))
    
    elif mode == 'sharedlinks':
        # Shared-link mode
        links = _load_sharedlinks()
        out = []
        for i, entry in enumerate(links):
            label = entry.get('label') or entry.get('url', '')[:60]
            name = label if label else f'degoo_link_{i}.mp4'
            
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
    
    return []


def get_stream_url(file_id):
    """
    Get streaming URL for a file.
    
    :param file_id: File ID (Degoo ID for account mode, index for shared-link mode)
    :returns: Direct streaming URL or None
    """
    mode = _get_mode()
    
    if mode == 'account':
        # Full account mode - get direct URL from Degoo API
        return _get_file_url(file_id)
    
    elif mode == 'sharedlinks':
        # Shared-link mode - resolve share link
        try:
            idx = int(file_id)
        except Exception:
            return None
        
        links = _load_sharedlinks()
        if 0 <= idx < len(links):
            url = links[idx].get('url', '')
            direct = _resolve_shared_link(url)
            return direct or url
    
    return None


def get_share_url(file_id):
    """
    Get share URL for a file (for debrid services).
    
    :param file_id: File ID
    :returns: Share URL or None
    """
    mode = _get_mode()
    
    if mode == 'account':
        # For account mode, get the direct URL (same as stream URL)
        return _get_file_url(file_id)
    
    elif mode == 'sharedlinks':
        # For shared-link mode, return original share URL
        try:
            idx = int(file_id)
        except Exception:
            return None
        
        links = _load_sharedlinks()
        if 0 <= idx < len(links):
            return links[idx].get('url')
    
    return None


# ---------------------------------------------------------------------------
# Settings helpers (called from settings menu)
# ---------------------------------------------------------------------------

def login():
    """
    Authorize Degoo account (full account mode).
    Shows login dialog and stores tokens on success.
    """
    # Get credentials
    email = xbmcgui.Dialog().input(
        'Degoo Email',
        type=xbmcgui.INPUT_ALPHANUM)
    if not email:
        return
    
    password = xbmcgui.Dialog().input(
        'Degoo Password',
        type=xbmcgui.INPUT_ALPHANUM,
        option=xbmcgui.ALPHANUM_HIDE_INPUT)
    if not password:
        return
    
    # Show progress dialog
    pd = xbmcgui.DialogProgress()
    pd.create(ADDON_NAME, 'Logging into Degoo...')
    
    try:
        # Prepare login request
        body = {
            "GenerateToken": True,
            "Username": email,
            "Password": password
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': DEGOO_USER_AGENT,
            'Referer': 'https://app.degoo.com/',
            'Origin': 'https://app.degoo.com',
        }
        
        data = json.dumps(body).encode('utf-8')
        req = Request(DEGOO_LOGIN_URL, data=data, headers=headers)
        
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        
        pd.update(50, 'Getting access token...')
        
        # Handle new token flow (RefreshToken → AccessToken)
        if 'RefreshToken' in result:
            refresh_token = result['RefreshToken']
            token_body = {"RefreshToken": refresh_token}
            token_data = json.dumps(token_body).encode('utf-8')
            
            token_req = Request(DEGOO_TOKEN_URL, data=token_data, headers=headers)
            with urlopen(token_req, timeout=30) as token_resp:
                token_result = json.loads(token_resp.read().decode('utf-8'))
            
            if 'AccessToken' in token_result:
                token = token_result['AccessToken']
            else:
                raise Exception('Failed to get access token')
        
        elif 'Token' in result:
            token = result['Token']
        else:
            raise Exception('No token received from Degoo')
        
        # Store tokens
        tokens = {
            'Token': token,
            'x-api-key': DEGOO_API_KEY
        }
        _save_tokens(tokens)
        
        # Update addon setting to use account mode
        ADDON.setSetting('degoo_mode', 'account')
        
        pd.update(100, 'Login successful!')
        xbmc.sleep(1000)
        pd.close()
        
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            'Degoo account authorized',
            ADDON_ICON)
    
    except Exception as e:
        pd.close()
        _log(f'Degoo login failed: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().ok(
            ADDON_NAME,
            f'Degoo login failed:\n{str(e)}')


def logout():
    """Clear Degoo account credentials."""
    try:
        os.remove(_store_tokens())
    except Exception:
        pass
    
    xbmcgui.Dialog().notification(
        ADDON_NAME,
        'Degoo account disconnected',
        ADDON_ICON)


def add_shared_link():
    """Add a Degoo public share link (shared-link mode)."""
    url = xbmcgui.Dialog().input(
        'Paste Degoo share link',
        type=xbmcgui.INPUT_ALPHANUM)
    if not url:
        return
    
    label = xbmcgui.Dialog().input(
        'Friendly name (optional)',
        type=xbmcgui.INPUT_ALPHANUM) or ''
    
    links = _load_sharedlinks()
    links.append({'url': url.strip(), 'label': label.strip()})
    _save_sharedlinks(links)
    
    # Update mode to shared links if not in account mode
    if not _load_tokens().get('Token'):
        ADDON.setSetting('degoo_mode', 'sharedlinks')
    
    xbmcgui.Dialog().notification(
        ADDON_NAME,
        'Degoo share link added',
        ADDON_ICON)


def remove_shared_link():
    """Remove a Degoo share link."""
    links = _load_sharedlinks()
    if not links:
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            'No Degoo links configured',
            ADDON_ICON)
        return
    
    labels = [e.get('label') or e.get('url', '')[:60] for e in links]
    idx = xbmcgui.Dialog().select('Remove Degoo link', labels)
    if idx < 0:
        return
    
    links.pop(idx)
    _save_sharedlinks(links)
    
    xbmcgui.Dialog().notification(
        ADDON_NAME,
        'Degoo link removed',
        ADDON_ICON)


def test_connection():
    """Test Degoo connection from settings menu."""
    mode = _get_mode()
    
    if not mode:
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            'Degoo not configured',
            ADDON_ICON)
        return
    
    if mode == 'account':
        # Test account mode by fetching user info
        try:
            properties = "Name Email TotalQuota UsedQuota"
            query = f"""
            query GetUserInfo($Token: String!) {{
                getUserInfo(Token: $Token) {{ {properties} }}
            }}
            """
            
            tokens = _load_tokens()
            variables = {"Token": tokens['Token']}
            
            data = _graphql_request(query, variables, "GetUserInfo")
            if data and 'getUserInfo' in data:
                user = data['getUserInfo']
                xbmcgui.Dialog().ok(
                    'Degoo Connection OK',
                    f"Account: {user.get('Email', 'Unknown')}\n"
                    f"Name: {user.get('Name', 'Unknown')}")
            else:
                raise Exception('Failed to get user info')
        
        except Exception as e:
            _log(f'Connection test failed: {e}', xbmc.LOGWARNING)
            xbmcgui.Dialog().ok(
                ADDON_NAME,
                f'Degoo connection failed:\n{str(e)}')
    
    elif mode == 'sharedlinks':
        links = _load_sharedlinks()
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            f'Degoo: {len(links)} share link(s) configured',
            ADDON_ICON)
