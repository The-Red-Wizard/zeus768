"""
SALTS - Filepax account integration via WebDAV.

Filepax (filepax.com) is a cloud storage service that supports WebDAV access
for premium members. This module implements read-only operations for listing
and streaming video files from a Filepax account.

To enable WebDAV in Filepax:
1. Open Settings → Experimental Features in FilePax Web Drive
2. Enable the WebDAV option
3. Copy the WebDAV connection address, username, and password
4. Enter these credentials in SALTS Filepax settings

The module exposes the standard cloud-provider interface:
    is_authed(), list_all_videos(progress_cb=None),
    get_stream_url(file_id), get_share_url(file_id)

Note: Filepax WebDAV currently supports read operations only.
"""
import base64
import re
import urllib.parse
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()

VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.ts',
             '.flv', '.wmv', '.mpg', '.mpeg', '.m2ts', '.3gp', '.divx')

# Default WebDAV URL for Filepax
# Users should get this from their Filepax Settings → Experimental Features
_DEFAULT_WEBDAV_URL = 'https://filepax.com/webdav'


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _conf():
    """Return Filepax WebDAV configuration from addon settings."""
    url = (ADDON.getSetting('filepax_webdav_url') or _DEFAULT_WEBDAV_URL).strip()
    if not url.endswith('/'):
        url += '/'
    user = (ADDON.getSetting('filepax_username') or '').strip()
    pw = ADDON.getSetting('filepax_password') or ''
    return url, user, pw


def _is_video(name):
    """Check if filename is a video file based on extension."""
    return name.lower().endswith(VIDEO_EXT)


def _log(msg, level=None):
    """Log message to Kodi log."""
    try:
        xbmc.log(f'cloud_filepax: {msg}',
                 level if level is not None else xbmc.LOGDEBUG)
    except Exception:
        pass


def _auth_header(user, pw):
    """Generate HTTP Basic Authentication header."""
    token = base64.b64encode(f'{user}:{pw}'.encode('utf-8')).decode('ascii')
    return f'Basic {token}'


def _webdav_request(method, url, user, pw, depth=None, body=None, timeout=30):
    """Execute a WebDAV request with Basic authentication."""
    headers = {
        'Authorization': _auth_header(user, pw),
        'User-Agent': 'SALTS-Filepax/1.0',
    }
    if depth is not None:
        headers['Depth'] = str(depth)
    if body is not None:
        headers['Content-Type'] = 'application/xml; charset=utf-8'
        body = body.encode('utf-8')
    
    req = Request(url, data=body, headers=headers, method=method)
    return urlopen(req, timeout=timeout)


# WebDAV PROPFIND body for listing directory contents
_PROPFIND_BODY = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<d:propfind xmlns:d="DAV:">'
    '<d:prop>'
    '<d:displayname/><d:getcontentlength/><d:resourcetype/>'
    '<d:getcontenttype/><d:getlastmodified/>'
    '</d:prop>'
    '</d:propfind>'
)

# Regular expressions for parsing WebDAV XML responses
_RESP_RE = re.compile(
    r'<(?:[a-zA-Z0-9]+:)?response[^>]*>(.*?)</(?:[a-zA-Z0-9]+:)?response>',
    re.S | re.I)
_HREF_RE = re.compile(
    r'<(?:[a-zA-Z0-9]+:)?href[^>]*>(.*?)</(?:[a-zA-Z0-9]+:)?href>', re.S | re.I)
_LEN_RE = re.compile(
    r'<(?:[a-zA-Z0-9]+:)?getcontentlength[^>]*>(\d+)</', re.I)
_COLL_RE = re.compile(
    r'<(?:[a-zA-Z0-9]+:)?collection\s*/>', re.I)
_MIME_RE = re.compile(
    r'<(?:[a-zA-Z0-9]+:)?getcontenttype[^>]*>(.*?)</', re.I)


def _webdav_walk(base_url, user, pw, progress_cb=None):
    """
    Recursively walk WebDAV directory tree starting from base_url.
    Yields dicts with keys: id, name, size, mimeType, modifiedTime.
    """
    base_parsed = urllib.parse.urlsplit(base_url)
    base_path = base_parsed.path
    
    # Stack of directory URLs to visit
    stack = [base_url]
    seen = set()
    found = 0
    
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        
        try:
            resp = _webdav_request('PROPFIND', cur, user, pw, depth=1,
                                   body=_PROPFIND_BODY, timeout=30)
            xml = resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            _log(f'WebDAV PROPFIND {cur}: {e}', xbmc.LOGWARNING)
            continue
        
        # Parse XML response for files and folders
        for block in _RESP_RE.findall(xml):
            mh = _HREF_RE.search(block)
            if not mh:
                continue
            
            href = mh.group(1).strip()
            href = urllib.parse.unquote(href)
            
            # Build absolute URL for the resource
            if href.startswith('http://') or href.startswith('https://'):
                abs_url = href
                resource_path = urllib.parse.urlsplit(href).path
            else:
                abs_url = urllib.parse.urljoin(
                    f'{base_parsed.scheme}://{base_parsed.netloc}',
                    urllib.parse.quote(href))
                resource_path = href
            
            # Skip the directory itself
            cur_path = urllib.parse.urlsplit(cur).path
            if resource_path.rstrip('/') == cur_path.rstrip('/'):
                continue
            
            # Check if it's a directory/collection
            is_dir = bool(_COLL_RE.search(block))
            if is_dir:
                if not abs_url.endswith('/'):
                    abs_url += '/'
                stack.append(abs_url)
                continue
            
            # Extract filename
            name = resource_path.rstrip('/').rsplit('/', 1)[-1]
            if not _is_video(name):
                continue
            
            # Extract file size
            size = 0
            ml = _LEN_RE.search(block)
            if ml:
                try:
                    size = int(ml.group(1))
                except Exception:
                    size = 0
            
            # Extract MIME type
            mt = ''
            mm = _MIME_RE.search(block)
            if mm:
                mt = mm.group(1).strip()
            
            # Create file_id as relative path from base, URL-encoded
            rel_path = resource_path
            if rel_path.startswith(base_path):
                rel_path = rel_path[len(base_path):]
            rel_path = rel_path.lstrip('/')
            
            found += 1
            if progress_cb:
                try:
                    progress_cb(found, found)
                except Exception:
                    pass
            
            yield {
                'id': urllib.parse.quote(rel_path, safe='/'),
                'name': name,
                'size': size,
                'mimeType': mt or 'video/mp4',
                'modifiedTime': '',
            }


# ---------------------------------------------------------------------------
# Public interface for cloud_library.py
# ---------------------------------------------------------------------------

def is_authed():
    """Check if Filepax WebDAV credentials are configured."""
    url, user, pw = _conf()
    return bool(url and user and pw)


def list_all_videos(progress_cb=None):
    """
    List all video files from Filepax account via WebDAV.
    Returns list of dicts with keys: id, name, size, mimeType, modifiedTime.
    """
    url, user, pw = _conf()
    return list(_webdav_walk(url, user, pw, progress_cb=progress_cb))


def get_stream_url(file_id):
    """
    Get streaming URL for a file by embedding Basic auth credentials.
    This allows Kodi's player to fetch the file directly.
    """
    if not file_id:
        return None
    
    url, user, pw = _conf()
    full = urllib.parse.urljoin(url, file_id)
    parsed = urllib.parse.urlsplit(full)
    
    # Embed credentials in URL for direct playback
    u = urllib.parse.quote(user, safe='')
    p = urllib.parse.quote(pw, safe='')
    netloc = f'{u}:{p}@{parsed.netloc}'
    
    return urllib.parse.urlunsplit(
        (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def get_share_url(file_id):
    """
    Get share URL for a file.
    For WebDAV direct-play providers, this is the same as stream URL.
    """
    return get_stream_url(file_id)


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def test_connection():
    """Test Filepax WebDAV connection from settings menu."""
    import xbmcgui
    name = 'Filepax'
    icon = ADDON.getAddonInfo('icon')
    
    if not is_authed():
        xbmcgui.Dialog().notification(
            name, 'Not configured - fill in credentials first', icon)
        return
    
    try:
        url, user, pw = _conf()
        # Try a simple PROPFIND with depth 0 to test connection
        _webdav_request('PROPFIND', url, user, pw, depth=0,
                        body=_PROPFIND_BODY, timeout=15)
        xbmcgui.Dialog().notification(name, 'WebDAV connection OK', icon)
    except Exception as e:
        xbmcgui.Dialog().ok(name, f'WebDAV connection failed:\n{e}')


def logout():
    """Clear all Filepax credentials."""
    for k in ('filepax_username', 'filepax_password', 'filepax_webdav_url'):
        try:
            ADDON.setSetting(k, '')
        except Exception:
            pass
    import xbmcgui
    xbmcgui.Dialog().notification(
        'Filepax', 'Account credentials cleared', ADDON.getAddonInfo('icon'))
