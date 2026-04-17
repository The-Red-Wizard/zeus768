# -*- coding: utf-8 -*-
"""
Poseidon Player - Premium IPTV Addon
Author: poseidon12
Version: 2.5.0
Features: Live TV, EPG Guide, Poseidon Guide (EPG Grid), VOD with Genres, Series, Favorites, Search, Recently Watched, Catch-up, Reminders
IPTV Manager Integration for Full TV Guide
NEW: Background service for keep-alive streams & reminder notifications
FIXED: Persistent login state, Stream stability with HLS/m3u8 + inputstream.adaptive
"""

import sys
import os
import json
import time
import urllib.parse
from datetime import datetime, timedelta
import requests
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

# ============================================================================
# ADDON INITIALIZATION
# ============================================================================
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

# Handle sys.argv safely - for service mode or direct execution
try:
    HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1
    BASE_URL = sys.argv[0] if len(sys.argv) > 0 else ''
except (ValueError, IndexError):
    HANDLE = -1
    BASE_URL = ''

# Create data directory
if not xbmcvfs.exists(ADDON_DATA):
    xbmcvfs.mkdirs(ADDON_DATA)

# ============================================================================
# HELPER FUNCTIONS (DEFINED EARLY FOR USE THROUGHOUT)
# ============================================================================
def log(message, level=xbmc.LOGINFO):
    """Log message to Kodi log"""
    xbmc.log(f"[{ADDON_ID}] {message}", level)

def notify(message, title=ADDON_NAME, icon=xbmcgui.NOTIFICATION_INFO, time=5000):
    """Show notification"""
    xbmcgui.Dialog().notification(title, message, icon, time)

def build_url(query):
    """Build plugin URL with query parameters"""
    return f"{BASE_URL}?{urllib.parse.urlencode(query)}"

def format_time(timestamp):
    """Format Unix timestamp to readable time"""
    try:
        return datetime.fromtimestamp(int(timestamp)).strftime('%H:%M')
    except:
        return ''

def format_date(timestamp):
    """Format Unix timestamp to readable date"""
    try:
        return datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M')
    except:
        return ''

def format_duration(start, end):
    """Calculate and format duration"""
    try:
        duration = int(end) - int(start)
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except:
        return ''

def get_stream_format():
    """Get preferred stream format from settings (default: m3u8 for better stability)"""
    return ADDON.getSetting('stream_format') or 'm3u8'

def build_live_stream_url(stream_id):
    """Build live stream URL with configured format"""
    if not SESSION.is_valid():
        return None
    stream_format = get_stream_format()
    return f"{SESSION.dns}/live/{SESSION.username}/{SESSION.password}/{stream_id}.{stream_format}"

def build_live_listitem(stream_url, title, icon='', fanart=''):
    """Build a ListItem for live stream playback with inputstream.adaptive support"""
    li = xbmcgui.ListItem(label=title, path=stream_url)
    li.setArt({
        'thumb': icon,
        'icon': icon,
        'fanart': fanart or os.path.join(ADDON_PATH, 'fanart.jpg')
    })
    li.setProperty('IsPlayable', 'true')
    
    # Use inputstream.adaptive for m3u8 streams for better buffering
    stream_format = get_stream_format()
    if stream_format == 'm3u8':
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
    
    return li

def play_live_stream(stream_id, title='Live TV', icon=''):
    """Play a live stream with proper inputstream handling"""
    stream_url = build_live_stream_url(stream_id)
    if not stream_url:
        notify("Cannot play stream - not authenticated", icon=xbmcgui.NOTIFICATION_ERROR)
        return
    
    li = build_live_listitem(stream_url, title, icon)
    
    # Add to history
    add_to_history('live', stream_id, title, icon)
    
    xbmc.Player().play(stream_url, li)
    log(f"Playing live stream: {title} ({stream_id}) - Format: {get_stream_format()}")

# ============================================================================
# SESSION STORAGE (SAVED - Credentials persisted in addon settings)
# ============================================================================
class SessionManager:
    """Manages session credentials - SAVED to addon settings with persistent auth state"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.user_info = None
            cls._instance.server_info = None
            cls._instance._load_saved_credentials()
        return cls._instance
    
    def _load_saved_credentials(self):
        """Load credentials from Kodi addon settings"""
        self.dns = ADDON.getSetting('dns').rstrip('/') or None
        self.username = ADDON.getSetting('username') or None
        self.password = ADDON.getSetting('password') or None
    
    @property
    def authenticated(self):
        """Check authenticated state from settings (persistent across addon restarts)"""
        return ADDON.getSetting('authenticated') == 'true'
    
    @authenticated.setter
    def authenticated(self, value):
        """Store authenticated state in settings"""
        ADDON.setSetting('authenticated', 'true' if value else 'false')
    
    def set_credentials(self, dns, username, password):
        """Set and SAVE credentials to addon settings"""
        self.dns = dns.rstrip('/')
        self.username = username
        self.password = password
        self.authenticated = False
        
        ADDON.setSetting('dns', self.dns)
        ADDON.setSetting('username', self.username)
        ADDON.setSetting('password', self.password)
        log(f"Credentials saved for user: {self.username}")
    
    def clear(self):
        """Clear credentials from memory AND settings"""
        self.dns = None
        self.username = None
        self.password = None
        self.authenticated = False
        self.user_info = None
        self.server_info = None
        
        ADDON.setSetting('dns', '')
        ADDON.setSetting('username', '')
        ADDON.setSetting('password', '')
        ADDON.setSetting('authenticated', 'false')
    
    def is_valid(self):
        return all([self.dns, self.username, self.password])
    
    def has_saved_credentials(self):
        """Check if credentials are saved in settings"""
        return bool(ADDON.getSetting('dns') and ADDON.getSetting('username') and ADDON.getSetting('password'))

SESSION = SessionManager()

# ============================================================================
# DATA STORAGE (Favorites, Recently Watched, Reminders)
# ============================================================================
class DataStorage:
    """Persistent storage for favorites, watch history, and reminders"""
    
    def __init__(self, filename):
        self.filepath = os.path.join(ADDON_DATA, filename)
        self.data = self._load()
    
    def _load(self):
        try:
            if xbmcvfs.exists(self.filepath):
                with xbmcvfs.File(self.filepath, 'r') as f:
                    content = f.read()
                    if content and content.strip():
                        return json.loads(content)
        except Exception as e:
            log(f"Data load error for {self.filepath}: {e}", xbmc.LOGERROR)
        return []
    
    def _save(self):
        try:
            with xbmcvfs.File(self.filepath, 'w') as f:
                f.write(json.dumps(self.data))
        except Exception as e:
            log(f"Data save error: {e}", xbmc.LOGERROR)
    
    def add(self, item):
        for existing in self.data:
            if existing.get('id') == item.get('id') and existing.get('type') == item.get('type'):
                self.data.remove(existing)
                break
        self.data.insert(0, item)
        self.data = self.data[:100]
        self._save()
    
    def remove(self, item_id, item_type):
        self.data = [i for i in self.data if not (i.get('id') == item_id and i.get('type') == item_type)]
        self._save()
    
    def exists(self, item_id, item_type):
        return any(i.get('id') == item_id and i.get('type') == item_type for i in self.data)
    
    def get_all(self):
        return self.data.copy()
    
    def clear(self):
        self.data = []
        self._save()

FAVORITES = DataStorage('favorites.json')
HISTORY = DataStorage('history.json')
REMINDERS = DataStorage('reminders.json')

# ============================================================================
# ENHANCED EPG CACHE WITH PERSISTENCE
# ============================================================================
class EPGCache:
    """Enhanced EPG cache with file persistence for fast loading"""
    
    def __init__(self):
        self.cache_file = os.path.join(ADDON_DATA, 'epg_cache.json')
        self.channels_cache_file = os.path.join(ADDON_DATA, 'channels_cache.json')
        self.categories_cache_file = os.path.join(ADDON_DATA, 'categories_cache.json')
        self.cache = self._load_cache(self.cache_file)
        self.channels = self._load_cache(self.channels_cache_file)
        self.categories = self._load_cache(self.categories_cache_file)
    
    def _load_cache(self, filepath):
        try:
            if xbmcvfs.exists(filepath):
                with xbmcvfs.File(filepath, 'r') as f:
                    content = f.read()
                    if content and content.strip():
                        data = json.loads(content)
                        if isinstance(data, dict):
                            return data
        except Exception as e:
            log(f"Cache load error for {filepath}: {e}", xbmc.LOGERROR)
        return {'timestamp': 0, 'data': {}}
    
    def _save_cache(self, filepath, data):
        try:
            with xbmcvfs.File(filepath, 'w') as f:
                f.write(json.dumps(data))
        except Exception as e:
            log(f"Cache save error: {e}", xbmc.LOGERROR)
    
    def get_epg(self, stream_id):
        return self.cache.get('data', {}).get(str(stream_id), [])
    
    def set_epg(self, stream_id, epg_data):
        if 'data' not in self.cache:
            self.cache['data'] = {}
        self.cache['data'][str(stream_id)] = epg_data
        self.cache['timestamp'] = time.time()
        self._save_cache(self.cache_file, self.cache)
    
    def set_bulk_epg(self, epg_dict):
        """Set multiple EPG entries at once"""
        if 'data' not in self.cache:
            self.cache['data'] = {}
        self.cache['data'].update(epg_dict)
        self.cache['timestamp'] = time.time()
        self._save_cache(self.cache_file, self.cache)
    
    def get_channels(self, cat_id=None):
        if cat_id:
            return self.channels.get('data', {}).get(str(cat_id), [])
        return self.channels.get('all', [])
    
    def set_channels(self, channels, cat_id=None):
        if 'data' not in self.channels:
            self.channels['data'] = {}
        if cat_id:
            self.channels['data'][str(cat_id)] = channels
        else:
            self.channels['all'] = channels
        self.channels['timestamp'] = time.time()
        self._save_cache(self.channels_cache_file, self.channels)
    
    def get_categories(self, cat_type='live'):
        return self.categories.get('data', {}).get(cat_type, [])
    
    def set_categories(self, categories, cat_type='live'):
        if 'data' not in self.categories:
            self.categories['data'] = {}
        self.categories['data'][cat_type] = categories
        self.categories['timestamp'] = time.time()
        self._save_cache(self.categories_cache_file, self.categories)
    
    def is_epg_stale(self):
        refresh_mins = int(ADDON.getSetting('epg_refresh') or 30)
        return (time.time() - self.cache.get('timestamp', 0)) > (refresh_mins * 60)
    
    def is_channels_stale(self):
        # Channels cache valid for 1 hour
        return (time.time() - self.channels.get('timestamp', 0)) > 3600
    
    def is_categories_stale(self):
        # Categories cache valid for 6 hours
        return (time.time() - self.categories.get('timestamp', 0)) > 21600
    
    def clear_all(self):
        self.cache = {'timestamp': 0, 'data': {}}
        self.channels = {'timestamp': 0, 'data': {}}
        self.categories = {'timestamp': 0, 'data': {}}
        self._save_cache(self.cache_file, self.cache)
        self._save_cache(self.channels_cache_file, self.channels)
        self._save_cache(self.categories_cache_file, self.categories)

EPG_CACHE = EPGCache()

# ============================================================================
# API FUNCTIONS WITH CACHING
# ============================================================================
def api_request(action, extra_params=None, timeout=30):
    """Make API request to Xtream Codes server"""
    if not SESSION.is_valid():
        return None
    
    url = f"{SESSION.dns}/player_api.php?username={SESSION.username}&password={SESSION.password}&action={action}"
    if extra_params:
        url += extra_params
    
    try:
        log(f"API Request: {action}{extra_params or ''}")
        response = requests.get(url, timeout=timeout, headers={'User-Agent': 'Kodi/20.0'})
        response.raise_for_status()
        data = response.json()
        log(f"API Response for {action}: {type(data)} - {str(data)[:200]}")
        return data
    except requests.exceptions.Timeout:
        log(f"API Timeout: {action}", xbmc.LOGERROR)
        notify("Connection timeout. Please try again.", icon=xbmcgui.NOTIFICATION_ERROR)
    except requests.exceptions.RequestException as e:
        log(f"API Error: {e}", xbmc.LOGERROR)
        notify("Connection error. Check your server.", icon=xbmcgui.NOTIFICATION_ERROR)
    except json.JSONDecodeError as e:
        log(f"Invalid JSON response: {action} - {e}", xbmc.LOGERROR)
    return None

def authenticate():
    """Authenticate with Xtream Codes server"""
    if not SESSION.is_valid():
        return False
    
    try:
        url = f"{SESSION.dns}/player_api.php?username={SESSION.username}&password={SESSION.password}"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if data.get('user_info', {}).get('auth') == 1:
            SESSION.authenticated = True
            SESSION.user_info = data.get('user_info', {})
            SESSION.server_info = data.get('server_info', {})
            return True
        else:
            notify("Authentication failed. Check credentials.", icon=xbmcgui.NOTIFICATION_ERROR)
            return False
    except Exception as e:
        log(f"Auth error: {e}", xbmc.LOGERROR)
        notify("Failed to connect to server.", icon=xbmcgui.NOTIFICATION_ERROR)
        return False

def get_live_categories_cached():
    """Get live categories with caching"""
    if not EPG_CACHE.is_categories_stale():
        cached = EPG_CACHE.get_categories('live')
        if cached:
            return cached
    
    categories = api_request("get_live_categories")
    if categories:
        EPG_CACHE.set_categories(categories, 'live')
    return categories or []

def get_live_streams_cached(cat_id):
    """Get live streams with caching"""
    if not EPG_CACHE.is_channels_stale():
        cached = EPG_CACHE.get_channels(cat_id)
        if cached:
            return cached
    
    streams = api_request("get_live_streams", f"&category_id={cat_id}")
    if streams:
        EPG_CACHE.set_channels(streams, cat_id)
    return streams or []

def get_all_live_streams_cached():
    """Get all live streams from all categories"""
    all_streams = []
    categories = get_live_categories_cached()
    
    for cat in categories:
        streams = get_live_streams_cached(cat.get('category_id'))
        if streams:
            for stream in streams:
                stream['category_name'] = cat.get('category_name', 'Unknown')
            all_streams.extend(streams)
    
    return all_streams

def get_epg_for_stream(stream_id, limit=10):
    """Get EPG data for a specific stream with caching"""
    if not EPG_CACHE.is_epg_stale():
        cached = EPG_CACHE.get_epg(stream_id)
        if cached:
            return cached
    
    data = api_request("get_short_epg", f"&stream_id={stream_id}&limit={limit}")
    if data and 'epg_listings' in data:
        EPG_CACHE.set_epg(stream_id, data['epg_listings'])
        return data['epg_listings']
    return []

def get_full_epg(stream_id):
    """Get full EPG data for a stream"""
    data = api_request("get_simple_data_table", f"&stream_id={stream_id}")
    if data and 'epg_listings' in data:
        return data['epg_listings']
    return []

# ============================================================================
# IPTV MANAGER INTEGRATION
# ============================================================================
class IPTVManager:
    """Integration with IPTV Manager for full TV Guide"""
    
    def __init__(self, port):
        self.port = port
    
    def via_socket(func):
        """Decorator to send data via socket"""
        import socket
        def wrapper(self):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', self.port))
            try:
                result = func(self)
                sock.sendall(json.dumps(result).encode())
            finally:
                sock.close()
        return wrapper
    
    @via_socket
    def send_channels(self):
        """Generate M3U playlist for IPTV Manager"""
        if not SESSION.is_valid():
            if not SESSION.has_saved_credentials():
                return {'version': 1, 'streams': []}
            SESSION._load_saved_credentials()
            if not authenticate():
                return {'version': 1, 'streams': []}
        
        channels = []
        categories = get_live_categories_cached()
        
        for cat in categories:
            cat_name = cat.get('category_name', 'Unknown')
            streams = get_live_streams_cached(cat.get('category_id'))
            
            for stream in streams:
                stream_id = stream.get('stream_id')
                name = stream.get('name', 'Unknown')
                icon = stream.get('stream_icon', '')
                epg_id = stream.get('epg_channel_id', str(stream_id))
                
                stream_format = get_stream_format()
                play_url = f"{SESSION.dns}/live/{SESSION.username}/{SESSION.password}/{stream_id}.{stream_format}"
                
                channels.append({
                    'name': name,
                    'stream': play_url,
                    'id': epg_id,
                    'logo': icon,
                    'group': cat_name,
                    'radio': False
                })
        
        return {'version': 1, 'streams': channels}
    
    @via_socket
    def send_epg(self):
        """Generate XMLTV EPG for IPTV Manager"""
        if not SESSION.is_valid():
            if not SESSION.has_saved_credentials():
                return {'version': 1, 'epg': []}
            SESSION._load_saved_credentials()
            if not authenticate():
                return {'version': 1, 'epg': []}
        
        epg_data = []
        categories = get_live_categories_cached()
        
        for cat in categories:
            streams = get_live_streams_cached(cat.get('category_id'))
            
            for stream in streams:
                stream_id = stream.get('stream_id')
                epg_id = stream.get('epg_channel_id', str(stream_id))
                
                # Get EPG for this stream
                epg_listings = get_epg_for_stream(stream_id, limit=50)
                
                for prog in epg_listings:
                    start_ts = int(prog.get('start_timestamp', 0))
                    end_ts = int(prog.get('stop_timestamp', 0))
                    
                    if start_ts and end_ts:
                        epg_data.append({
                            'start': datetime.fromtimestamp(start_ts).strftime('%Y-%m-%d %H:%M:%S'),
                            'stop': datetime.fromtimestamp(end_ts).strftime('%Y-%m-%d %H:%M:%S'),
                            'channel': epg_id,
                            'title': prog.get('title', ''),
                            'description': prog.get('description', ''),
                            'subtitle': '',
                            'episode': '',
                            'genre': '',
                            'image': ''
                        })
        
        return {'version': 1, 'epg': epg_data}

def iptv_manager_channels():
    """Entry point for IPTV Manager channel request"""
    port = int(sys.argv[2])
    IPTVManager(port).send_channels()

def iptv_manager_epg():
    """Entry point for IPTV Manager EPG request"""
    port = int(sys.argv[2])
    IPTVManager(port).send_epg()

# ============================================================================
# FORCE LOGIN DIALOG
# ============================================================================
def force_login(silent=False):
    """Force user to login before accessing main menu
    
    Args:
        silent: If True, skip notifications for already authenticated sessions
    """
    dialog = xbmcgui.Dialog()
    
    if SESSION.has_saved_credentials():
        SESSION._load_saved_credentials()
        
        # If already authenticated (persistent state), just verify credentials are valid
        if SESSION.authenticated and SESSION.is_valid():
            # Quick validation - no notification needed for returning users
            log("Session already authenticated, skipping login dialog")
            return True
        
        # Show progress only for re-authentication
        progress = xbmcgui.DialogProgress()
        progress.create("Poseidon Player", "Logging in with saved credentials...")
        
        if authenticate():
            progress.close()
            # Only show notification on first login of session (when not silent)
            if not silent:
                exp_date = SESSION.user_info.get('exp_date', '')
                if exp_date:
                    try:
                        exp_str = datetime.fromtimestamp(int(exp_date)).strftime('%Y-%m-%d')
                        notify(f"Welcome back! Account expires: {exp_str}")
                    except:
                        notify("Welcome back!")
                else:
                    notify("Welcome back!")
            return True
        else:
            progress.close()
            # Auth failed, clear the persistent state
            SESSION.authenticated = False
            dialog.ok(
                "Poseidon Player",
                "Saved credentials are invalid or expired.\n\n"
                "Please enter new credentials."
            )
    else:
        dialog.ok(
            "Poseidon Player",
            "Welcome to Poseidon Player!\n\n"
            "Please enter your Xtream Codes credentials.\n"
            "Your login will be saved for next time."
        )
    
    # Get DNS/Server URL
    dns = dialog.input("Enter Server URL (e.g., http://server.com:8080)", type=xbmcgui.INPUT_ALPHANUM)
    if not dns:
        return False
    
    if not dns.startswith('http://') and not dns.startswith('https://'):
        dns = 'http://' + dns
    
    username = dialog.input("Enter Username", type=xbmcgui.INPUT_ALPHANUM)
    if not username:
        return False
    
    password = dialog.input("Enter Password", type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
    if not password:
        return False
    
    SESSION.set_credentials(dns, username, password)
    
    progress = xbmcgui.DialogProgress()
    progress.create("Poseidon Player", "Authenticating...")
    
    success = authenticate()
    progress.close()
    
    if success:
        exp_date = SESSION.user_info.get('exp_date', '')
        if exp_date:
            try:
                exp_str = datetime.fromtimestamp(int(exp_date)).strftime('%Y-%m-%d')
                notify(f"Welcome! Account expires: {exp_str}")
            except:
                notify("Login successful!")
        else:
            notify("Login successful!")
        return True
    else:
        SESSION.clear()
        return False

# ============================================================================
# MAIN MENU
# ============================================================================
def main_menu():
    """Display main menu"""
    items = [
        {"label": "[COLOR gold]TV Guide[/COLOR]", "action": "tv_guide_choice", "icon": "DefaultTVShows.png"},
        {"label": "[COLOR cyan]Live TV[/COLOR]", "action": "live_categories", "icon": "DefaultTVShows.png"},
        {"label": "[COLOR orange]Movies (VOD)[/COLOR]", "action": "vod_categories", "icon": "DefaultMovies.png"},
        {"label": "[COLOR lime]TV Series[/COLOR]", "action": "series_categories", "icon": "DefaultTVShows.png"},
        {"label": "[COLOR red]Favorites[/COLOR]", "action": "favorites", "icon": "DefaultFavourites.png"},
        {"label": "[COLOR magenta]Search[/COLOR]", "action": "search_menu", "icon": "DefaultAddonsSearch.png"},
        {"label": "[COLOR yellow]Recently Watched[/COLOR]", "action": "recently_watched", "icon": "DefaultRecentlyAddedMovies.png"},
        {"label": "[COLOR purple]Catch-up TV[/COLOR]", "action": "catchup_categories", "icon": "DefaultYear.png"},
        {"label": "[COLOR blue]Reminders[/COLOR]", "action": "reminders_menu", "icon": "DefaultYear.png"},
        {"label": "[COLOR white]Refresh EPG Cache[/COLOR]", "action": "refresh_epg", "icon": "DefaultAddonService.png"},
        {"label": "[COLOR gray]Account Info[/COLOR]", "action": "account_info", "icon": "DefaultAddonService.png"},
        {"label": "[COLOR gray]Logout[/COLOR]", "action": "logout", "icon": "DefaultAddonNone.png"},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(label=item['label'])
        li.setArt({
            'icon': os.path.join(ADDON_PATH, 'icon.png'),
            'thumb': os.path.join(ADDON_PATH, 'icon.png'),
            'fanart': os.path.join(ADDON_PATH, 'fanart.jpg')
        })
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': item['action']}), li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

# ============================================================================
# TV GUIDE CHOICE POPUP
# ============================================================================
def show_tv_guide_choice():
    """Show popup to choose between List view and Poseidon Guide"""
    dialog = xbmcgui.Dialog()
    
    options = [
        "List View (Simple EPG List)",
        "Poseidon Guide (Full Grid EPG)"
    ]
    
    choice = dialog.select("TV Guide - Choose View", options)
    
    if choice == 0:
        # List view - show simple EPG categories
        show_epg_guide()
    elif choice == 1:
        # Poseidon Guide - launch grid
        launch_poseidon_guide()

# ============================================================================
# LAUNCH POSEIDON GUIDE (SEPARATE ADDON)
# ============================================================================
def launch_poseidon_guide():
    """Launch the separate Poseidon Guide program addon"""
    GUIDE_ADDON_ID = 'program.poseidonguide'
    
    try:
        # Check if Poseidon Guide is installed
        xbmcaddon.Addon(GUIDE_ADDON_ID)
        # Launch it
        xbmc.executebuiltin(f'RunAddon({GUIDE_ADDON_ID})')
    except Exception as e:
        log(f"Poseidon Guide not installed: {e}")
        # Fallback to built-in guide
        dialog = xbmcgui.Dialog()
        choice = dialog.yesno(
            "Poseidon Guide",
            "Poseidon Guide addon is not installed.\n\n"
            "Would you like to use the built-in EPG guide instead?\n\n"
            "For the best experience, install program.poseidonguide"
        )
        if choice:
            show_poseidon_guide()

# ============================================================================
# POSEIDON GUIDE - BUILT-IN FALLBACK EPG GRID
# ============================================================================
class PoseidonGuideWindow(xbmcgui.WindowXML):
    """Custom EPG Grid Window like the reference image"""
    
    def __init__(self, *args, **kwargs):
        self.channels = kwargs.get('channels', [])
        self.epg_data = kwargs.get('epg_data', {})
        self.current_channel_index = 0
        self.current_time_offset = 0
        self.hours_to_display = int(ADDON.getSetting('epg_hours') or 3)
        self.channel_list_id = 50
        self.program_panel_id = 51
        super(PoseidonGuideWindow, self).__init__(*args, **kwargs)
    
    def onInit(self):
        """Called when window is initialized"""
        self.populate_channels()
        self.update_time_headers()
    
    def populate_channels(self):
        """Populate the channel list"""
        channel_list = self.getControl(self.channel_list_id)
        channel_list.reset()
        
        for i, channel in enumerate(self.channels):
            li = xbmcgui.ListItem(label=channel.get('name', 'Unknown'))
            li.setProperty('channel_num', str(channel.get('num', i + 1)))
            li.setProperty('stream_id', str(channel.get('stream_id', '')))
            li.setArt({'thumb': channel.get('stream_icon', '')})
            channel_list.addItem(li)
    
    def update_time_headers(self):
        """Update time slot headers"""
        now = datetime.now()
        start_time = now + timedelta(minutes=self.current_time_offset * 30)
        
        for i in range(6):
            slot_time = start_time + timedelta(minutes=i * 30)
            try:
                label = self.getControl(201 + i)
                label.setLabel(slot_time.strftime('%H:%M'))
            except:
                pass
    
    def onAction(self, action):
        """Handle user actions"""
        action_id = action.getId()
        
        # Navigation
        if action_id in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK]:
            self.close()
        elif action_id == xbmcgui.ACTION_MOVE_LEFT:
            self.current_time_offset = max(0, self.current_time_offset - 1)
            self.update_time_headers()
        elif action_id == xbmcgui.ACTION_MOVE_RIGHT:
            self.current_time_offset += 1
            self.update_time_headers()
        elif action_id == xbmcgui.ACTION_SELECT_ITEM:
            self.play_selected_channel()
        elif action_id == xbmcgui.ACTION_CONTEXT_MENU:
            self.show_context_menu()
    
    def onClick(self, control_id):
        """Handle clicks"""
        if control_id == self.channel_list_id:
            self.play_selected_channel()
    
    def play_selected_channel(self):
        """Play the selected channel"""
        channel_list = self.getControl(self.channel_list_id)
        selected = channel_list.getSelectedItem()
        if selected:
            stream_id = selected.getProperty('stream_id')
            if stream_id and SESSION.is_valid():
                play_url = build_live_stream_url(stream_id)
                li = build_live_listitem(play_url, selected.getLabel(), selected.getArt('thumb'))
                xbmc.Player().play(play_url, li)
    
    def show_context_menu(self):
        """Show context menu for reminders"""
        channel_list = self.getControl(self.channel_list_id)
        selected = channel_list.getSelectedItem()
        if selected:
            stream_id = selected.getProperty('stream_id')
            channel_name = selected.getLabel()
            
            options = ["Set Reminder", "View Full EPG", "Add to Favorites"]
            choice = xbmcgui.Dialog().contextmenu(options)
            
            if choice == 0:  # Set Reminder
                self.set_reminder_for_channel(stream_id, channel_name)
            elif choice == 1:  # View Full EPG
                self.close()
                show_channel_epg(stream_id, channel_name)
            elif choice == 2:  # Add to Favorites
                icon = selected.getArt('thumb')
                add_favorite('live', stream_id, channel_name, icon)
    
    def set_reminder_for_channel(self, stream_id, channel_name):
        """Set a reminder for an upcoming program"""
        epg = get_epg_for_stream(stream_id, limit=20)
        now = time.time()
        
        future_programs = [p for p in epg if int(p.get('start_timestamp', 0)) > now]
        
        if not future_programs:
            notify("No upcoming programs found")
            return
        
        options = []
        for prog in future_programs[:10]:
            start_time = format_time(prog.get('start_timestamp', 0))
            title = prog.get('title', 'Unknown')
            options.append(f"{start_time} - {title}")
        
        choice = xbmcgui.Dialog().select("Select Program for Reminder", options)
        if choice >= 0:
            prog = future_programs[choice]
            add_reminder(
                stream_id, 
                channel_name, 
                prog.get('title', 'Unknown'),
                prog.get('start_timestamp', 0)
            )

def show_poseidon_guide():
    """Show the Poseidon Guide EPG Grid"""
    progress = xbmcgui.DialogProgress()
    progress.create("Poseidon Guide", "Loading channels and EPG data...")
    
    # Get all channels
    all_channels = get_all_live_streams_cached()
    
    if not all_channels:
        progress.close()
        notify("No channels found. Please check your connection.", icon=xbmcgui.NOTIFICATION_ERROR)
        return
    
    # Sort by channel number
    all_channels.sort(key=lambda x: int(x.get('num', 0) or 0))
    
    # Get EPG data for channels
    epg_data = {}
    total = min(len(all_channels), 50)  # Limit initial load
    
    for i, channel in enumerate(all_channels[:total]):
        if progress.iscanceled():
            break
        progress.update(int((i / total) * 100), f"Loading EPG for {channel.get('name', '')}...")
        stream_id = channel.get('stream_id')
        epg = get_epg_for_stream(stream_id, limit=20)
        if epg:
            epg_data[str(stream_id)] = epg
    
    progress.close()
    
    # Open the guide window - use a dialog-based approach instead of WindowXML
    show_poseidon_guide_dialog(all_channels, epg_data)

def show_poseidon_guide_dialog(channels, epg_data):
    """Show EPG Guide using a list dialog (fallback for WindowXML)"""
    now = time.time()
    
    # Build display list
    display_items = []
    channel_data = []
    
    for channel in channels:
        stream_id = str(channel.get('stream_id'))
        name = channel.get('name', 'Unknown')
        num = channel.get('num', '')
        
        epg = epg_data.get(stream_id, [])
        current_prog = None
        next_prog = None
        
        for prog in epg:
            start = int(prog.get('start_timestamp', 0))
            end = int(prog.get('stop_timestamp', 0))
            
            if start <= now <= end:
                current_prog = prog
            elif start > now and not next_prog:
                next_prog = prog
                break
        
        if current_prog:
            prog_title = current_prog.get('title', '')
            start_time = format_time(current_prog.get('start_timestamp', 0))
            end_time = format_time(current_prog.get('stop_timestamp', 0))
            display = f"{num}. {name}\n  NOW: {prog_title} ({start_time}-{end_time})"
            if next_prog:
                next_title = next_prog.get('title', '')
                next_start = format_time(next_prog.get('start_timestamp', 0))
                display += f"\n  NEXT: {next_title} @ {next_start}"
        else:
            display = f"{num}. {name}\n  No EPG data"
        
        display_items.append(display)
        channel_data.append(channel)
    
    # Show selection dialog
    while True:
        choice = xbmcgui.Dialog().select(
            "Poseidon Guide - Select Channel",
            display_items,
            useDetails=False
        )
        
        if choice < 0:
            break
        
        # Show options for selected channel
        channel = channel_data[choice]
        stream_id = channel.get('stream_id')
        channel_name = channel.get('name', 'Unknown')
        icon = channel.get('stream_icon', '')
        
        options = ["Play Channel", "Set Reminder", "View Full EPG", "Add to Favorites"]
        action = xbmcgui.Dialog().contextmenu(options)
        
        if action == 0:  # Play
            play_url = build_live_stream_url(stream_id)
            li = build_live_listitem(play_url, channel_name, icon)
            xbmc.Player().play(play_url, li)
            break
        elif action == 1:  # Set Reminder
            set_reminder_dialog(stream_id, channel_name)
        elif action == 2:  # View Full EPG
            xbmc.executebuiltin(f'Container.Update({build_url({"action": "channel_epg", "stream_id": stream_id, "name": channel_name})})')
            break
        elif action == 3:  # Add to Favorites
            add_favorite('live', stream_id, channel_name, icon)

def set_reminder_dialog(stream_id, channel_name):
    """Set a reminder for an upcoming program"""
    epg = get_epg_for_stream(stream_id, limit=20)
    now = time.time()
    
    future_programs = [p for p in epg if int(p.get('start_timestamp', 0)) > now]
    
    if not future_programs:
        notify("No upcoming programs found")
        return
    
    options = []
    for prog in future_programs[:10]:
        start_time = format_time(prog.get('start_timestamp', 0))
        title = prog.get('title', 'Unknown')
        options.append(f"{start_time} - {title}")
    
    choice = xbmcgui.Dialog().select("Select Program for Reminder", options)
    if choice >= 0:
        prog = future_programs[choice]
        add_reminder(
            stream_id, 
            channel_name, 
            prog.get('title', 'Unknown'),
            prog.get('start_timestamp', 0)
        )

# ============================================================================
# REMINDERS
# ============================================================================
def add_reminder(stream_id, channel_name, program_title, start_timestamp):
    """Add a reminder for a program"""
    reminder = {
        'id': f"{stream_id}_{start_timestamp}",
        'type': 'reminder',
        'stream_id': stream_id,
        'channel_name': channel_name,
        'program_title': program_title,
        'start_timestamp': int(start_timestamp),
        'added': time.time()
    }
    REMINDERS.add(reminder)
    
    start_str = format_time(start_timestamp)
    notify(f"Reminder set: {program_title} at {start_str}")

def remove_reminder(reminder_id):
    """Remove a reminder"""
    REMINDERS.remove(reminder_id, 'reminder')
    notify("Reminder removed")
    xbmc.executebuiltin('Container.Refresh')

def list_reminders():
    """List all reminders"""
    reminders = REMINDERS.get_all()
    now = time.time()
    
    # Filter out past reminders
    active_reminders = [r for r in reminders if int(r.get('start_timestamp', 0)) > now]
    
    if not active_reminders:
        notify("No active reminders")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    # Sort by start time
    active_reminders.sort(key=lambda x: x.get('start_timestamp', 0))
    
    for reminder in active_reminders:
        stream_id = reminder.get('stream_id')
        channel_name = reminder.get('channel_name', 'Unknown')
        program_title = reminder.get('program_title', 'Unknown')
        start_ts = reminder.get('start_timestamp', 0)
        reminder_id = reminder.get('id')
        
        start_str = format_date(start_ts)
        label = f"[COLOR cyan]{program_title}[/COLOR]"
        label2 = f"[COLOR gray]{channel_name} | {start_str}[/COLOR]"
        
        li = xbmcgui.ListItem(label=f"{label}\n{label2}")
        li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
        
        stream_format = get_stream_format()
        play_url = build_live_stream_url(stream_id)
        context = [
            ("Remove Reminder", f"RunPlugin({build_url({'action': 'remove_reminder', 'reminder_id': reminder_id})})"),
            ("Play Channel Now", f"PlayMedia({SESSION.dns}/live/{SESSION.username}/{SESSION.password}/{stream_id}.{stream_format})"),
        ]
        li.addContextMenuItems(context)
        
        # Clicking plays the channel
        li.setProperty('IsPlayable', 'true')
        
        # Set inputstream.adaptive for m3u8 format
        if stream_format == 'm3u8':
            li.setProperty('inputstream', 'inputstream.adaptive')
            li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        
        xbmcplugin.addDirectoryItem(HANDLE, play_url, li, False)
    
    xbmcplugin.endOfDirectory(HANDLE)

def reminders_menu():
    """Show reminders menu"""
    items = [
        {"label": "[COLOR cyan]View Reminders[/COLOR]", "action": "view_reminders"},
        {"label": "[COLOR yellow]Clear All Reminders[/COLOR]", "action": "clear_reminders"},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(label=item['label'])
        li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': item['action']}), li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def clear_reminders():
    """Clear all reminders"""
    if xbmcgui.Dialog().yesno("Clear Reminders", "Are you sure you want to clear all reminders?"):
        REMINDERS.clear()
        notify("All reminders cleared")
        xbmc.executebuiltin('Container.Refresh')

# ============================================================================
# EPG / TV GUIDE
# ============================================================================
def show_epg_guide():
    """Show EPG Guide menu"""
    categories = get_live_categories_cached()
    if not categories:
        notify("Failed to load TV Guide", icon=xbmcgui.NOTIFICATION_ERROR)
        return
    
    items = [
        {"label": "[COLOR gold]All Channels EPG[/COLOR]", "action": "epg_all_channels"},
    ]
    
    for cat in categories:
        items.append({
            "label": f"[COLOR cyan]{cat.get('category_name', 'Unknown')}[/COLOR]",
            "action": "epg_category",
            "cat_id": cat.get('category_id')
        })
    
    for item in items:
        li = xbmcgui.ListItem(label=item['label'])
        li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
        
        url_params = {'action': item['action']}
        if 'cat_id' in item:
            url_params['cat_id'] = item['cat_id']
        
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def show_epg_all_channels():
    """Show EPG for all channels"""
    progress = xbmcgui.DialogProgress()
    progress.create("Loading EPG", "Fetching channel data...")
    
    categories = get_live_categories_cached()
    if not categories:
        progress.close()
        notify("Failed to load channels", icon=xbmcgui.NOTIFICATION_ERROR)
        return
    
    all_channels = []
    total = len(categories)
    
    for i, cat in enumerate(categories):
        if progress.iscanceled():
            break
        progress.update(int((i / total) * 100), f"Loading {cat.get('category_name', '')}...")
        streams = get_live_streams_cached(cat.get('category_id'))
        if streams:
            all_channels.extend(streams)
    
    progress.close()
    display_channels_with_epg(all_channels)

def show_epg_category(cat_id):
    """Show EPG for a specific category"""
    progress = xbmcgui.DialogProgress()
    progress.create("Loading EPG", "Fetching channel data...")
    
    streams = get_live_streams_cached(cat_id)
    progress.close()
    
    if not streams:
        notify("No channels found", icon=xbmcgui.NOTIFICATION_ERROR)
        return
    
    display_channels_with_epg(streams)

def display_channels_with_epg(channels):
    """Display channels with their current/next EPG info"""
    now = time.time()
    stream_format = get_stream_format()
    
    for ch in channels:
        stream_id = ch.get('stream_id')
        name = ch.get('name', 'Unknown Channel')
        num = ch.get('num', '')
        icon = ch.get('stream_icon', '')
        
        epg = get_epg_for_stream(stream_id, limit=5)
        
        current_prog = None
        next_prog = None
        
        for prog in epg:
            start = int(prog.get('start_timestamp', 0))
            end = int(prog.get('stop_timestamp', 0))
            
            if start <= now <= end:
                current_prog = prog
            elif start > now and not next_prog:
                next_prog = prog
        
        if current_prog:
            prog_title = current_prog.get('title', '')
            start_time = format_time(current_prog.get('start_timestamp', 0))
            end_time = format_time(current_prog.get('stop_timestamp', 0))
            
            try:
                start_ts = int(current_prog.get('start_timestamp', 0))
                end_ts = int(current_prog.get('stop_timestamp', 0))
                progress_pct = int(((now - start_ts) / (end_ts - start_ts)) * 100)
                progress_str = f"[{progress_pct}%]"
            except:
                progress_str = ""
            
            label = f"[COLOR white]{num}[/COLOR] [COLOR gold]{name}[/COLOR]"
            label2 = f"[COLOR cyan]NOW: {prog_title}[/COLOR] ({start_time}-{end_time}) {progress_str}"
            
            if next_prog:
                next_title = next_prog.get('title', '')
                next_start = format_time(next_prog.get('start_timestamp', 0))
                label2 += f"\n[COLOR gray]NEXT: {next_title} @ {next_start}[/COLOR]"
        else:
            label = f"[COLOR white]{num}[/COLOR] [COLOR gold]{name}[/COLOR]"
            label2 = "[COLOR gray]No EPG data available[/COLOR]"
        
        play_url = build_live_stream_url(stream_id)
        li = xbmcgui.ListItem(label=label, label2=label2)
        li.setArt({'thumb': icon, 'icon': icon, 'fanart': os.path.join(ADDON_PATH, 'fanart.jpg')})
        
        info = li.getVideoInfoTag()
        info.setTitle(name)
        if current_prog:
            info.setPlot(current_prog.get('description', ''))
        
        # Set inputstream.adaptive for m3u8 format for better buffering
        if stream_format == 'm3u8':
            li.setProperty('inputstream', 'inputstream.adaptive')
            li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        
        context = [
            ("Add to Favorites", f"RunPlugin({build_url({'action': 'add_favorite', 'type': 'live', 'id': stream_id, 'name': name, 'icon': icon})})"),
            ("View Full EPG", f"Container.Update({build_url({'action': 'channel_epg', 'stream_id': stream_id, 'name': name})})"),
            ("Set Reminder", f"RunPlugin({build_url({'action': 'set_reminder_channel', 'stream_id': stream_id, 'name': name})})"),
            ("Catch-up TV", f"Container.Update({build_url({'action': 'channel_catchup', 'stream_id': stream_id, 'name': name})})"),
        ]
        li.addContextMenuItems(context)
        
        li.setProperty('IsPlayable', 'true')
        
        xbmcplugin.addDirectoryItem(HANDLE, play_url, li, False)
    
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def show_channel_epg(stream_id, channel_name):
    """Show full EPG schedule for a channel"""
    epg = get_full_epg(stream_id)
    if not epg:
        epg = get_epg_for_stream(stream_id, limit=50)
    
    if not epg:
        notify("No EPG data available for this channel")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    now = time.time()
    
    for prog in epg:
        title = prog.get('title', 'Unknown Program')
        desc = prog.get('description', '')
        start = int(prog.get('start_timestamp', 0))
        end = int(prog.get('stop_timestamp', 0))
        
        start_str = format_date(start)
        end_str = format_time(end)
        duration = format_duration(start, end)
        
        if start <= now <= end:
            color = "cyan"
            status = "[NOW PLAYING]"
        elif end < now:
            color = "gray"
            status = "[ENDED]"
        else:
            color = "white"
            status = ""
        
        label = f"[COLOR {color}]{start_str} - {end_str}[/COLOR] ({duration})"
        label2 = f"[COLOR gold]{title}[/COLOR] {status}"
        
        li = xbmcgui.ListItem(label=f"{label}\n{label2}")
        li.setArt({'fanart': os.path.join(ADDON_PATH, 'fanart.jpg')})
        
        info = li.getVideoInfoTag()
        info.setTitle(title)
        info.setPlot(desc)
        
        # Context menu for reminders
        if start > now:
            context = [
                ("Set Reminder", f"RunPlugin({build_url({'action': 'add_reminder_direct', 'stream_id': stream_id, 'channel_name': channel_name, 'program_title': title, 'start_timestamp': start})})"),
            ]
            li.addContextMenuItems(context)
        
        if end < now:
            catchup_url = build_url({
                'action': 'play_catchup',
                'stream_id': stream_id,
                'start': start,
                'end': end
            })
            li.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(HANDLE, catchup_url, li, False)
        else:
            xbmcplugin.addDirectoryItem(HANDLE, "", li, False)
    
    xbmcplugin.endOfDirectory(HANDLE)

def do_refresh_epg():
    """Refresh all EPG cache"""
    progress = xbmcgui.DialogProgress()
    progress.create("Refreshing EPG", "Please wait...")
    
    EPG_CACHE.clear_all()
    
    categories = api_request("get_live_categories")
    if categories:
        EPG_CACHE.set_categories(categories, 'live')
        
        total = len(categories)
        all_epg = {}
        
        for i, cat in enumerate(categories):
            if progress.iscanceled():
                break
            
            cat_name = cat.get('category_name', '')
            progress.update(int((i / total) * 100), f"Loading {cat_name}...")
            
            streams = api_request("get_live_streams", f"&category_id={cat.get('category_id')}")
            if streams:
                EPG_CACHE.set_channels(streams, cat.get('category_id'))
                
                for stream in streams:
                    stream_id = stream.get('stream_id')
                    data = api_request("get_short_epg", f"&stream_id={stream_id}&limit=10")
                    if data and 'epg_listings' in data:
                        all_epg[str(stream_id)] = data['epg_listings']
        
        if all_epg:
            EPG_CACHE.set_bulk_epg(all_epg)
    
    progress.close()
    notify("EPG cache refreshed successfully!")

# ============================================================================
# LIVE TV
# ============================================================================
def list_live_categories():
    """List live TV categories"""
    categories = get_live_categories_cached()
    if not categories:
        notify("Failed to load categories", icon=xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for cat in categories:
        name = cat.get('category_name', 'Unknown')
        cat_id = cat.get('category_id')
        
        li = xbmcgui.ListItem(label=f"[COLOR cyan]{name}[/COLOR]")
        li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
        
        url = build_url({'action': 'live_streams', 'cat_id': cat_id})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def list_live_streams(cat_id):
    """List live streams in a category"""
    streams = get_live_streams_cached(cat_id)
    if not streams:
        notify("No channels found", icon=xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    now = time.time()
    stream_format = get_stream_format()
    
    for s in streams:
        stream_id = s.get('stream_id')
        name = s.get('name', 'Unknown')
        icon = s.get('stream_icon', '')
        num = s.get('num', '')
        
        epg = get_epg_for_stream(stream_id, limit=2)
        now_playing = ""
        if epg:
            for prog in epg:
                start = int(prog.get('start_timestamp', 0))
                end = int(prog.get('stop_timestamp', 0))
                if start <= now <= end:
                    now_playing = prog.get('title', '')
                    break
        
        if now_playing:
            label = f"[COLOR white]{num}[/COLOR] {name} | [COLOR cyan]{now_playing}[/COLOR]"
        else:
            label = f"[COLOR white]{num}[/COLOR] {name}"
        
        play_url = build_live_stream_url(stream_id)
        li = xbmcgui.ListItem(label=label)
        li.setArt({'thumb': icon, 'icon': icon, 'fanart': os.path.join(ADDON_PATH, 'fanart.jpg')})
        
        info = li.getVideoInfoTag()
        info.setTitle(name)
        
        # Set inputstream.adaptive for m3u8 format for better buffering
        if stream_format == 'm3u8':
            li.setProperty('inputstream', 'inputstream.adaptive')
            li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        
        context = [
            ("Add to Favorites", f"RunPlugin({build_url({'action': 'add_favorite', 'type': 'live', 'id': stream_id, 'name': name, 'icon': icon})})"),
            ("View EPG", f"Container.Update({build_url({'action': 'channel_epg', 'stream_id': stream_id, 'name': name})})"),
            ("Set Reminder", f"RunPlugin({build_url({'action': 'set_reminder_channel', 'stream_id': stream_id, 'name': name})})"),
            ("Catch-up TV", f"Container.Update({build_url({'action': 'channel_catchup', 'stream_id': stream_id, 'name': name})})"),
        ]
        li.addContextMenuItems(context)
        
        li.setProperty('IsPlayable', 'true')
        
        xbmcplugin.addDirectoryItem(HANDLE, play_url, li, False)
    
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

# ============================================================================
# VOD (MOVIES) WITH GENRES AND METADATA
# ============================================================================
VOD_GENRES = {
    'Action': ['action', 'adventure'],
    'Comedy': ['comedy', 'comedies'],
    'Drama': ['drama'],
    'Horror': ['horror', 'thriller'],
    'Sci-Fi': ['sci-fi', 'science fiction', 'scifi'],
    'Romance': ['romance', 'romantic'],
    'Documentary': ['documentary', 'documentaries', 'docs'],
    'Animation': ['animation', 'animated', 'anime', 'cartoon'],
    'Family': ['family', 'kids', 'children'],
    'Sports': ['sports', 'sport'],
    'Music': ['music', 'musical'],
    'War': ['war', 'military'],
    'Western': ['western'],
    'Crime': ['crime', 'criminal'],
    'Mystery': ['mystery'],
    'Fantasy': ['fantasy'],
    'History': ['history', 'historical'],
    'Biography': ['biography', 'biographic'],
}

def list_vod_categories():
    """List VOD categories with genre organization"""
    genres_menu = [
        {"label": "[COLOR orange]All Movies[/COLOR]", "action": "vod_all"},
        {"label": "[COLOR cyan]By Category[/COLOR]", "action": "vod_by_category"},
        {"label": "[COLOR gold]Top Rated[/COLOR]", "action": "vod_top_rated"},
        {"label": "[COLOR lime]Recently Added[/COLOR]", "action": "vod_recent"},
    ]
    
    for item in genres_menu:
        li = xbmcgui.ListItem(label=item['label'])
        li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': item['action']}), li, True)
    
    li = xbmcgui.ListItem(label="[COLOR magenta]Browse by Genre[/COLOR]")
    li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'vod_genres'}), li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def list_vod_genres():
    """List available genres for VOD"""
    for genre in sorted(VOD_GENRES.keys()):
        li = xbmcgui.ListItem(label=f"[COLOR orange]{genre}[/COLOR]")
        li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
        url = build_url({'action': 'vod_genre', 'genre': genre})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def list_vod_by_genre(genre_name):
    """List VOD filtered by genre"""
    categories = api_request("get_vod_categories")
    if not categories:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    keywords = VOD_GENRES.get(genre_name, [genre_name.lower()])
    matching_cats = []
    
    for cat in categories:
        cat_name = cat.get('category_name', '').lower()
        for kw in keywords:
            if kw in cat_name:
                matching_cats.append(cat.get('category_id'))
                break
    
    if not matching_cats:
        all_vod = []
        for cat in categories:
            streams = api_request("get_vod_streams", f"&category_id={cat.get('category_id')}")
            if streams:
                all_vod.extend(streams)
        
        filtered = [v for v in all_vod if any(kw in v.get('name', '').lower() for kw in keywords)]
        display_vod_streams(filtered)
    else:
        all_streams = []
        for cat_id in matching_cats:
            streams = api_request("get_vod_streams", f"&category_id={cat_id}")
            if streams:
                all_streams.extend(streams)
        display_vod_streams(all_streams)

def list_vod_by_category():
    """List VOD categories"""
    categories = api_request("get_vod_categories")
    if not categories:
        notify("Failed to load VOD categories", icon=xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for cat in categories:
        name = cat.get('category_name', 'Unknown')
        cat_id = cat.get('category_id')
        
        li = xbmcgui.ListItem(label=f"[COLOR orange]{name}[/COLOR]")
        li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
        
        url = build_url({'action': 'vod_streams', 'cat_id': cat_id})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def list_vod_streams(cat_id):
    """List VOD streams in a category"""
    streams = api_request("get_vod_streams", f"&category_id={cat_id}")
    display_vod_streams(streams)

def list_all_vod():
    """List all VOD movies"""
    categories = api_request("get_vod_categories")
    if not categories:
        notify("Failed to load VOD categories", icon=xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    progress = xbmcgui.DialogProgress()
    progress.create("Loading Movies", "Please wait...")
    
    all_vod = []
    total = len(categories)
    
    for i, cat in enumerate(categories):
        if progress.iscanceled():
            break
        progress.update(int((i / total) * 100), f"Loading {cat.get('category_name', '')}...")
        streams = api_request("get_vod_streams", f"&category_id={cat.get('category_id')}")
        if streams:
            all_vod.extend(streams)
    
    progress.close()
    display_vod_streams(all_vod)

def list_top_rated_vod():
    """List top-rated VOD movies"""
    categories = api_request("get_vod_categories")
    if not categories:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    progress = xbmcgui.DialogProgress()
    progress.create("Loading Top Rated", "Please wait...")
    
    all_vod = []
    total = len(categories)
    
    for i, cat in enumerate(categories):
        if progress.iscanceled():
            break
        progress.update(int((i / total) * 100))
        streams = api_request("get_vod_streams", f"&category_id={cat.get('category_id')}")
        if streams:
            all_vod.extend(streams)
    
    progress.close()
    
    all_vod.sort(key=lambda x: float(x.get('rating', 0) or 0), reverse=True)
    display_vod_streams(all_vod[:100])

def list_recent_vod():
    """List recently added VOD"""
    categories = api_request("get_vod_categories")
    if not categories:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    progress = xbmcgui.DialogProgress()
    progress.create("Loading Recent", "Please wait...")
    
    all_vod = []
    total = len(categories)
    
    for i, cat in enumerate(categories):
        if progress.iscanceled():
            break
        progress.update(int((i / total) * 100))
        streams = api_request("get_vod_streams", f"&category_id={cat.get('category_id')}")
        if streams:
            all_vod.extend(streams)
    
    progress.close()
    
    all_vod.sort(key=lambda x: int(x.get('added', 0) or 0), reverse=True)
    display_vod_streams(all_vod[:100])

def display_vod_streams(streams):
    """Display VOD streams with full metadata - FIXED to fetch detailed info"""
    if not streams:
        notify("No movies found")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for m in streams:
        stream_id = m.get('stream_id')
        name = m.get('name', 'Unknown Movie')
        icon = m.get('stream_icon', '')
        rating = m.get('rating', '')
        year = m.get('year', '')
        genre = m.get('genre', '')
        plot = m.get('plot', '')
        cast = m.get('cast', '')
        director = m.get('director', '')
        duration = m.get('duration', '')
        duration_secs = m.get('duration_secs', 0)
        releasedate = m.get('releaseDate', m.get('release_date', ''))
        tmdb_id = m.get('tmdb_id', '')
        backdrop = m.get('cover_big', m.get('backdrop_path', icon))
        
        # If we don't have metadata, try to fetch it
        if not plot or not year or not cast:
            vod_info = api_request("get_vod_info", f"&vod_id={stream_id}", timeout=10)
            if vod_info:
                info_data = vod_info.get('info', {})
                movie_data = vod_info.get('movie_data', {})
                
                # Extract metadata from info
                if not plot:
                    plot = info_data.get('plot', info_data.get('description', ''))
                if not year:
                    year = info_data.get('year', info_data.get('releasedate', '')[:4] if info_data.get('releasedate') else '')
                if not cast:
                    cast = info_data.get('cast', info_data.get('actors', ''))
                if not director:
                    director = info_data.get('director', '')
                if not genre:
                    genre = info_data.get('genre', '')
                if not rating:
                    rating = info_data.get('rating', '')
                if not icon:
                    icon = info_data.get('cover_big', info_data.get('movie_image', ''))
                if not backdrop:
                    backdrop = info_data.get('backdrop_path', info_data.get('cover_big', icon))
                if not duration_secs:
                    duration_secs = info_data.get('duration_secs', 0)
                if not tmdb_id:
                    tmdb_id = info_data.get('tmdb_id', '')
        
        label = name
        if year:
            label += f" [COLOR gray]({year})[/COLOR]"
        if rating:
            try:
                label += f" [COLOR yellow]{float(rating):.1f}[/COLOR]"
            except:
                pass
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': icon,
            'thumb': icon,
            'icon': icon,
            'fanart': backdrop,
            'banner': backdrop,
            'landscape': backdrop
        })
        
        # Set full video metadata
        info = li.getVideoInfoTag()
        info.setTitle(name)
        info.setOriginalTitle(m.get('o_name', name))
        info.setPlot(plot or 'No description available')
        info.setPlotOutline(plot[:200] if plot else '')
        info.setMediaType('movie')
        
        if year:
            try:
                info.setYear(int(year))
            except:
                pass
        
        if rating:
            try:
                info.setRating(float(rating), votes=0, type='tmdb', isdefault=True)
            except:
                pass
        
        if genre:
            if isinstance(genre, str):
                info.setGenres([g.strip() for g in genre.split(',')])
            else:
                info.setGenres([genre])
        
        if director:
            info.setDirectors([d.strip() for d in director.split(',')])
        
        if cast:
            cast_list = [c.strip() for c in cast.split(',')]
            actors = []
            for i, actor_name in enumerate(cast_list[:10]):
                actors.append(xbmc.Actor(actor_name, '', i, ''))
            info.setCast(actors)
        
        if duration_secs:
            try:
                info.setDuration(int(duration_secs))
            except:
                pass
        elif duration:
            try:
                parts = duration.split(':')
                if len(parts) == 2:
                    secs = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    secs = int(duration) * 60
                info.setDuration(secs)
            except:
                pass
        
        if releasedate:
            try:
                info.setPremiered(releasedate)
            except:
                pass
        
        if tmdb_id:
            info.setUniqueID(str(tmdb_id), 'tmdb', True)
        
        # Stream info
        info.addVideoStream(xbmc.VideoStreamDetail(width=1920, height=1080, codec='h264'))
        info.addAudioStream(xbmc.AudioStreamDetail(channels=2, codec='aac', language='en'))
        
        context = [
            ("Add to Favorites", f"RunPlugin({build_url({'action': 'add_favorite', 'type': 'vod', 'id': stream_id, 'name': name, 'icon': icon})})"),
            ("Movie Info", f"RunPlugin({build_url({'action': 'vod_info', 'stream_id': stream_id})})"),
        ]
        li.addContextMenuItems(context)
        
        container = m.get('container_extension', 'mp4')
        play_url = f"{SESSION.dns}/movie/{SESSION.username}/{SESSION.password}/{stream_id}.{container}"
        li.setProperty('IsPlayable', 'true')
        
        xbmcplugin.addDirectoryItem(HANDLE, play_url, li, False)
    
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DURATION)
    xbmcplugin.endOfDirectory(HANDLE)

def show_vod_info(stream_id):
    """Show detailed VOD info"""
    info = api_request("get_vod_info", f"&vod_id={stream_id}")
    if not info:
        notify("Failed to load movie info")
        return
    
    movie_data = info.get('info', {})
    
    dialog_text = f"""
Title: {movie_data.get('name', movie_data.get('title', 'Unknown'))}
Original Title: {movie_data.get('o_name', 'N/A')}
Year: {movie_data.get('releasedate', movie_data.get('year', 'N/A'))}
Rating: {movie_data.get('rating', 'N/A')}/10
Genre: {movie_data.get('genre', 'N/A')}
Duration: {movie_data.get('duration', 'N/A')}
Director: {movie_data.get('director', 'N/A')}
Cast: {movie_data.get('cast', 'N/A')}
Country: {movie_data.get('country', 'N/A')}
TMDB ID: {movie_data.get('tmdb_id', 'N/A')}

Plot:
{movie_data.get('plot', movie_data.get('description', 'No description available'))}
    """
    
    xbmcgui.Dialog().textviewer("Movie Information", dialog_text.strip())

# ============================================================================
# TV SERIES - FIXED TO LOAD SEASONS AND EPISODES PROPERLY
# ============================================================================
def list_series_categories():
    """List series categories"""
    categories = api_request("get_series_categories")
    if not categories:
        notify("Failed to load series categories", icon=xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for cat in categories:
        name = cat.get('category_name', 'Unknown')
        cat_id = cat.get('category_id')
        
        li = xbmcgui.ListItem(label=f"[COLOR lime]{name}[/COLOR]")
        li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
        
        url = build_url({'action': 'series_list', 'cat_id': cat_id})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def list_series(cat_id):
    """List series in a category with metadata"""
    series = api_request("get_series", f"&category_id={cat_id}")
    if not series:
        notify("No series found")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for s in series:
        series_id = s.get('series_id')
        name = s.get('name', 'Unknown Series')
        icon = s.get('cover', '')
        rating = s.get('rating', '')
        year = s.get('year', '')
        plot = s.get('plot', '')
        cast = s.get('cast', '')
        director = s.get('director', '')
        genre = s.get('genre', '')
        backdrop = s.get('backdrop_path', icon)
        
        label = name
        if year:
            label += f" [COLOR gray]({year})[/COLOR]"
        if rating:
            try:
                label += f" [COLOR yellow]{float(rating):.1f}[/COLOR]"
            except:
                pass
        
        li = xbmcgui.ListItem(label=f"[COLOR lime]{label}[/COLOR]")
        li.setArt({
            'poster': icon,
            'thumb': icon,
            'icon': icon,
            'fanart': backdrop,
            'banner': backdrop
        })
        
        info = li.getVideoInfoTag()
        info.setTitle(name)
        info.setPlot(plot or 'No description available')
        info.setMediaType('tvshow')
        
        if year:
            try:
                info.setYear(int(year))
            except:
                pass
        
        if rating:
            try:
                info.setRating(float(rating), votes=0, type='tmdb', isdefault=True)
            except:
                pass
        
        if genre:
            if isinstance(genre, str):
                info.setGenres([g.strip() for g in genre.split(',')])
        
        if director:
            info.setDirectors([d.strip() for d in director.split(',')])
        
        if cast:
            cast_list = [c.strip() for c in cast.split(',')]
            actors = []
            for i, actor_name in enumerate(cast_list[:10]):
                actors.append(xbmc.Actor(actor_name, '', i, ''))
            info.setCast(actors)
        
        context = [
            ("Add to Favorites", f"RunPlugin({build_url({'action': 'add_favorite', 'type': 'series', 'id': series_id, 'name': name, 'icon': icon})})"),
        ]
        li.addContextMenuItems(context)
        
        url = build_url({'action': 'series_seasons', 'series_id': series_id})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)
    
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.endOfDirectory(HANDLE)

def list_series_seasons(series_id):
    """List seasons for a series - FIXED to properly parse API response"""
    log(f"Loading seasons for series_id: {series_id}")
    
    info = api_request("get_series_info", f"&series_id={series_id}", timeout=30)
    
    if not info:
        notify("Failed to load series info. Please try again.")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    log(f"Series info response type: {type(info)}")
    log(f"Series info keys: {info.keys() if isinstance(info, dict) else 'not a dict'}")
    
    # Get series metadata
    series_info = info.get('info', {})
    if not series_info and isinstance(info, dict):
        # Sometimes info is at top level
        series_info = info
    
    series_name = series_info.get('name', series_info.get('title', 'Unknown Series'))
    series_cover = series_info.get('cover', series_info.get('cover_big', ''))
    series_backdrop = series_info.get('backdrop_path', series_cover)
    series_plot = series_info.get('plot', series_info.get('description', ''))
    
    log(f"Series name: {series_name}, cover: {series_cover}")
    
    # Get seasons and episodes
    seasons = info.get('seasons', [])
    episodes = info.get('episodes', {})
    
    log(f"Seasons found: {len(seasons)}, Episodes dict keys: {list(episodes.keys()) if isinstance(episodes, dict) else 'not a dict'}")
    
    # If no seasons array but we have episodes, build seasons from episodes
    if not seasons and episodes:
        log("Building seasons from episodes...")
        season_nums = set()
        if isinstance(episodes, dict):
            season_nums = set(episodes.keys())
        elif isinstance(episodes, list):
            # Sometimes episodes is a flat list
            for ep in episodes:
                s_num = ep.get('season', ep.get('season_number', 1))
                season_nums.add(str(s_num))
        
        seasons = []
        for s_num in sorted(season_nums, key=lambda x: int(x) if x.isdigit() else 0):
            seasons.append({
                'season_number': int(s_num) if s_num.isdigit() else 1,
                'name': f'Season {s_num}'
            })
        log(f"Built {len(seasons)} seasons from episodes")
    
    if not seasons:
        # Try alternative: check if episodes is a list and group by season
        log("Still no seasons, trying to parse episodes directly...")
        
        # Some APIs return episodes at a different level
        all_episodes = []
        if isinstance(episodes, list):
            all_episodes = episodes
        elif isinstance(episodes, dict):
            for season_key, eps in episodes.items():
                if isinstance(eps, list):
                    for ep in eps:
                        ep['season'] = int(season_key) if str(season_key).isdigit() else 1
                        all_episodes.append(ep)
        
        if all_episodes:
            # Group by season
            season_map = {}
            for ep in all_episodes:
                s_num = ep.get('season', ep.get('season_number', 1))
                if s_num not in season_map:
                    season_map[s_num] = []
                season_map[s_num].append(ep)
            
            seasons = []
            for s_num in sorted(season_map.keys()):
                seasons.append({
                    'season_number': s_num,
                    'name': f'Season {s_num}',
                    'episodes': season_map[s_num]
                })
            
            # Store parsed episodes for later
            episodes = {str(s['season_number']): s.get('episodes', []) for s in seasons}
            log(f"Parsed {len(seasons)} seasons from flat episodes list")
    
    if not seasons:
        notify("No seasons found for this series")
        log("No seasons could be parsed from API response")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for season in seasons:
        season_num = season.get('season_number', season.get('season', 0))
        name = season.get('name', f'Season {season_num}')
        season_cover = season.get('cover', season.get('cover_big', series_cover))
        
        # Get episode count
        season_episodes = []
        if isinstance(episodes, dict):
            season_episodes = episodes.get(str(season_num), [])
        ep_count = len(season_episodes)
        
        log(f"Season {season_num}: {ep_count} episodes")
        
        label = f"[COLOR lime]{name}[/COLOR] [COLOR gray]({ep_count} episodes)[/COLOR]"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': season_cover,
            'thumb': season_cover,
            'icon': season_cover,
            'fanart': series_backdrop
        })
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(name)
        info_tag.setTvShowTitle(series_name)
        info_tag.setSeason(int(season_num))
        info_tag.setPlot(series_plot)
        info_tag.setMediaType('season')
        
        url = build_url({'action': 'series_episodes', 'series_id': series_id, 'season': season_num})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)
    
    xbmcplugin.setContent(HANDLE, 'seasons')
    xbmcplugin.endOfDirectory(HANDLE)

def list_series_episodes(series_id, season_num):
    """List episodes for a season - FIXED to properly parse API response"""
    log(f"Loading episodes for series_id: {series_id}, season: {season_num}")
    
    info = api_request("get_series_info", f"&series_id={series_id}", timeout=30)
    
    if not info:
        notify("Failed to load episodes. Please try again.")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    # Get series metadata
    series_info = info.get('info', {})
    if not series_info and isinstance(info, dict):
        series_info = info
    
    series_name = series_info.get('name', series_info.get('title', 'Unknown Series'))
    series_cover = series_info.get('cover', series_info.get('cover_big', ''))
    series_backdrop = series_info.get('backdrop_path', series_cover)
    
    # Get episodes
    episodes_data = info.get('episodes', {})
    
    episodes = []
    if isinstance(episodes_data, dict):
        episodes = episodes_data.get(str(season_num), [])
    elif isinstance(episodes_data, list):
        # Filter episodes by season
        for ep in episodes_data:
            ep_season = ep.get('season', ep.get('season_number', 1))
            if str(ep_season) == str(season_num):
                episodes.append(ep)
    
    log(f"Found {len(episodes)} episodes for season {season_num}")
    
    if not episodes:
        notify(f"No episodes found for Season {season_num}")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    # Sort episodes by episode number
    episodes.sort(key=lambda x: int(x.get('episode_num', x.get('episode', 0)) or 0))
    
    for ep in episodes:
        ep_num = ep.get('episode_num', ep.get('episode', 0))
        title = ep.get('title', f'Episode {ep_num}')
        
        # Get episode info - can be nested
        ep_info = ep.get('info', {})
        if not ep_info:
            ep_info = ep
        
        plot = ep_info.get('plot', ep_info.get('description', ep.get('plot', '')))
        duration = ep.get('duration', ep_info.get('duration', ''))
        duration_secs = ep.get('duration_secs', ep_info.get('duration_secs', 0))
        rating = ep_info.get('rating', '')
        air_date = ep_info.get('air_date', ep_info.get('releasedate', ''))
        
        ep_icon = ep_info.get('movie_image', ep_info.get('cover_big', ep.get('movie_image', series_cover)))
        
        label = f"[COLOR white]E{ep_num}[/COLOR] - {title}"
        if duration:
            label += f" [COLOR gray]({duration})[/COLOR]"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'thumb': ep_icon,
            'icon': ep_icon,
            'fanart': series_backdrop,
            'poster': series_cover
        })
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setTvShowTitle(series_name)
        info_tag.setEpisode(int(ep_num) if str(ep_num).isdigit() else 0)
        info_tag.setSeason(int(season_num) if str(season_num).isdigit() else 1)
        info_tag.setPlot(plot or 'No description available')
        info_tag.setMediaType('episode')
        
        if rating:
            try:
                info_tag.setRating(float(rating), votes=0, type='tmdb', isdefault=True)
            except:
                pass
        
        if air_date:
            try:
                info_tag.setPremiered(air_date)
            except:
                pass
        
        if duration_secs:
            try:
                info_tag.setDuration(int(duration_secs))
            except:
                pass
        
        # Build play URL
        stream_id = ep.get('id', ep.get('stream_id'))
        container = ep.get('container_extension', 'mp4')
        
        if stream_id:
            play_url = f"{SESSION.dns}/series/{SESSION.username}/{SESSION.password}/{stream_id}.{container}"
            li.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(HANDLE, play_url, li, False)
        else:
            log(f"No stream_id found for episode {ep_num}")
            xbmcplugin.addDirectoryItem(HANDLE, "", li, False)
    
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
    xbmcplugin.endOfDirectory(HANDLE)

# ============================================================================
# FAVORITES
# ============================================================================
def list_favorites():
    """List favorite items"""
    favorites = FAVORITES.get_all()
    
    if not favorites:
        notify("No favorites yet. Add items from context menu!")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    stream_format = get_stream_format()
    
    for fav in favorites:
        fav_type = fav.get('type')
        fav_id = fav.get('id')
        name = fav.get('name', 'Unknown')
        icon = fav.get('icon', '')
        
        if fav_type == 'live':
            label = f"[COLOR cyan]{name}[/COLOR]"
            play_url = build_live_stream_url(fav_id)
            is_folder = False
        elif fav_type == 'vod':
            label = f"[COLOR orange]{name}[/COLOR]"
            play_url = f"{SESSION.dns}/movie/{SESSION.username}/{SESSION.password}/{fav_id}.mp4"
            is_folder = False
        elif fav_type == 'series':
            label = f"[COLOR lime]{name}[/COLOR]"
            play_url = build_url({'action': 'series_seasons', 'series_id': fav_id})
            is_folder = True
        else:
            continue
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'thumb': icon, 'icon': icon})
        
        if not is_folder:
            li.setProperty('IsPlayable', 'true')
            # Set inputstream.adaptive for m3u8 live streams
            if fav_type == 'live' and stream_format == 'm3u8':
                li.setProperty('inputstream', 'inputstream.adaptive')
                li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        
        context = [
            ("Remove from Favorites", f"RunPlugin({build_url({'action': 'remove_favorite', 'type': fav_type, 'id': fav_id})})"),
        ]
        li.addContextMenuItems(context)
        
        xbmcplugin.addDirectoryItem(HANDLE, play_url, li, is_folder)
    
    xbmcplugin.endOfDirectory(HANDLE)

def add_favorite(item_type, item_id, name, icon):
    """Add item to favorites"""
    FAVORITES.add({
        'type': item_type,
        'id': item_id,
        'name': name,
        'icon': icon,
        'added': time.time()
    })
    notify(f"Added to favorites: {name}")

def remove_favorite(item_type, item_id):
    """Remove item from favorites"""
    FAVORITES.remove(item_id, item_type)
    notify("Removed from favorites")
    xbmc.executebuiltin('Container.Refresh')

# ============================================================================
# RECENTLY WATCHED
# ============================================================================
def add_to_history(item_type, item_id, name, icon):
    """Add item to watch history"""
    HISTORY.add({
        'type': item_type,
        'id': item_id,
        'name': name,
        'icon': icon,
        'watched': time.time()
    })

def list_recently_watched():
    """List recently watched items"""
    history = HISTORY.get_all()
    
    if not history:
        notify("No watch history yet")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    stream_format = get_stream_format()
    
    for item in history:
        item_type = item.get('type')
        item_id = item.get('id')
        name = item.get('name', 'Unknown')
        icon = item.get('icon', '')
        
        if item_type == 'live':
            label = f"[COLOR cyan]{name}[/COLOR]"
            play_url = build_live_stream_url(item_id)
        elif item_type == 'vod':
            label = f"[COLOR orange]{name}[/COLOR]"
            play_url = f"{SESSION.dns}/movie/{SESSION.username}/{SESSION.password}/{item_id}.mp4"
        elif item_type == 'series':
            label = f"[COLOR lime]{name}[/COLOR]"
            play_url = build_url({'action': 'series_seasons', 'series_id': item_id})
        else:
            continue
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'thumb': icon, 'icon': icon})
        li.setProperty('IsPlayable', 'true')
        
        # Set inputstream.adaptive for m3u8 live streams
        if item_type == 'live' and stream_format == 'm3u8':
            li.setProperty('inputstream', 'inputstream.adaptive')
            li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        
        xbmcplugin.addDirectoryItem(HANDLE, play_url, li, False)
    
    # Add clear history option
    li = xbmcgui.ListItem(label="[COLOR red]Clear History[/COLOR]")
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'clear_history'}), li, False)
    
    xbmcplugin.endOfDirectory(HANDLE)

def clear_history():
    """Clear watch history"""
    if xbmcgui.Dialog().yesno("Clear History", "Are you sure you want to clear your watch history?"):
        HISTORY.clear()
        notify("Watch history cleared")
        xbmc.executebuiltin('Container.Refresh')

# ============================================================================
# SEARCH
# ============================================================================
def search_menu():
    """Show search menu"""
    items = [
        {"label": "[COLOR cyan]Search Live TV[/COLOR]", "action": "search_live"},
        {"label": "[COLOR orange]Search Movies[/COLOR]", "action": "search_vod"},
        {"label": "[COLOR lime]Search TV Series[/COLOR]", "action": "search_series"},
        {"label": "[COLOR gold]Search All[/COLOR]", "action": "search_all"},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(label=item['label'])
        li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': item['action']}), li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def search_content(content_type):
    """Search for content"""
    query = xbmcgui.Dialog().input("Search", type=xbmcgui.INPUT_ALPHANUM)
    if not query:
        return
    
    query_lower = query.lower()
    results = []
    
    progress = xbmcgui.DialogProgress()
    progress.create("Searching", f"Looking for '{query}'...")
    
    if content_type in ['live', 'all']:
        categories = get_live_categories_cached()
        for cat in categories:
            if progress.iscanceled():
                break
            streams = get_live_streams_cached(cat.get('category_id'))
            for s in streams:
                if query_lower in s.get('name', '').lower():
                    results.append({'type': 'live', 'data': s})
    
    if content_type in ['vod', 'all']:
        categories = api_request("get_vod_categories")
        if categories:
            for cat in categories:
                if progress.iscanceled():
                    break
                streams = api_request("get_vod_streams", f"&category_id={cat.get('category_id')}")
                if streams:
                    for s in streams:
                        if query_lower in s.get('name', '').lower():
                            results.append({'type': 'vod', 'data': s})
    
    if content_type in ['series', 'all']:
        categories = api_request("get_series_categories")
        if categories:
            for cat in categories:
                if progress.iscanceled():
                    break
                series = api_request("get_series", f"&category_id={cat.get('category_id')}")
                if series:
                    for s in series:
                        if query_lower in s.get('name', '').lower():
                            results.append({'type': 'series', 'data': s})
    
    progress.close()
    
    if not results:
        notify(f"No results found for '{query}'")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for result in results:
        r_type = result['type']
        data = result['data']
        
        stream_format = get_stream_format()
        
        if r_type == 'live':
            stream_id = data.get('stream_id')
            name = data.get('name', 'Unknown')
            icon = data.get('stream_icon', '')
            label = f"[COLOR cyan][LIVE][/COLOR] {name}"
            play_url = build_live_stream_url(stream_id)
            is_folder = False
        elif r_type == 'vod':
            stream_id = data.get('stream_id')
            name = data.get('name', 'Unknown')
            icon = data.get('stream_icon', '')
            label = f"[COLOR orange][MOVIE][/COLOR] {name}"
            container = data.get('container_extension', 'mp4')
            play_url = f"{SESSION.dns}/movie/{SESSION.username}/{SESSION.password}/{stream_id}.{container}"
            is_folder = False
        elif r_type == 'series':
            series_id = data.get('series_id')
            name = data.get('name', 'Unknown')
            icon = data.get('cover', '')
            label = f"[COLOR lime][SERIES][/COLOR] {name}"
            play_url = build_url({'action': 'series_seasons', 'series_id': series_id})
            is_folder = True
        else:
            continue
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'thumb': icon, 'icon': icon})
        
        if not is_folder:
            li.setProperty('IsPlayable', 'true')
            # Set inputstream.adaptive for m3u8 live streams
            if r_type == 'live' and stream_format == 'm3u8':
                li.setProperty('inputstream', 'inputstream.adaptive')
                li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        
        xbmcplugin.addDirectoryItem(HANDLE, play_url, li, is_folder)
    
    xbmcplugin.endOfDirectory(HANDLE)

# ============================================================================
# CATCH-UP TV
# ============================================================================
def list_catchup_categories():
    """List categories that support catch-up"""
    categories = get_live_categories_cached()
    if not categories:
        notify("Failed to load categories", icon=xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for cat in categories:
        name = cat.get('category_name', 'Unknown')
        cat_id = cat.get('category_id')
        
        li = xbmcgui.ListItem(label=f"[COLOR purple]{name}[/COLOR]")
        li.setArt({'icon': os.path.join(ADDON_PATH, 'icon.png')})
        
        url = build_url({'action': 'catchup_channels', 'cat_id': cat_id})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def list_catchup_channels(cat_id):
    """List channels in category for catch-up"""
    streams = get_live_streams_cached(cat_id)
    if not streams:
        notify("No channels found", icon=xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    # Filter channels that support catch-up (tv_archive = 1)
    catchup_channels = [s for s in streams if s.get('tv_archive', 0) == 1]
    
    if not catchup_channels:
        notify("No catch-up channels in this category")
        # Show all channels anyway
        catchup_channels = streams
    
    for ch in catchup_channels:
        stream_id = ch.get('stream_id')
        name = ch.get('name', 'Unknown')
        icon = ch.get('stream_icon', '')
        archive_duration = ch.get('tv_archive_duration', 0)
        
        label = f"[COLOR purple]{name}[/COLOR]"
        if archive_duration:
            label += f" [COLOR gray]({archive_duration} days)[/COLOR]"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'thumb': icon, 'icon': icon})
        
        url = build_url({'action': 'channel_catchup', 'stream_id': stream_id, 'name': name})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def list_channel_catchup(stream_id, channel_name):
    """List past programs for catch-up"""
    epg = get_full_epg(stream_id)
    if not epg:
        epg = get_epg_for_stream(stream_id, limit=100)
    
    if not epg:
        notify("No EPG data available for catch-up")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    now = time.time()
    
    # Filter to past programs
    past_programs = [p for p in epg if int(p.get('stop_timestamp', 0)) < now]
    
    if not past_programs:
        notify("No past programs available")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    # Sort by start time, most recent first
    past_programs.sort(key=lambda x: x.get('start_timestamp', 0), reverse=True)
    
    for prog in past_programs[:50]:
        title = prog.get('title', 'Unknown Program')
        desc = prog.get('description', '')
        start = int(prog.get('start_timestamp', 0))
        end = int(prog.get('stop_timestamp', 0))
        
        start_str = format_date(start)
        duration = format_duration(start, end)
        
        label = f"[COLOR purple]{start_str}[/COLOR] - [COLOR gold]{title}[/COLOR] ({duration})"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'fanart': os.path.join(ADDON_PATH, 'fanart.jpg')})
        
        info = li.getVideoInfoTag()
        info.setTitle(title)
        info.setPlot(desc)
        
        catchup_url = build_url({
            'action': 'play_catchup',
            'stream_id': stream_id,
            'start': start,
            'end': end
        })
        li.setProperty('IsPlayable', 'true')
        
        xbmcplugin.addDirectoryItem(HANDLE, catchup_url, li, False)
    
    xbmcplugin.endOfDirectory(HANDLE)

def play_catchup(stream_id, start, end):
    """Play catch-up content"""
    if not SESSION.is_valid():
        notify("Not logged in", icon=xbmcgui.NOTIFICATION_ERROR)
        return
    
    # Build timeshift URL
    play_url = f"{SESSION.dns}/timeshift/{SESSION.username}/{SESSION.password}/{end - start}/{start}/{stream_id}.ts"
    
    li = xbmcgui.ListItem(path=play_url)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)

# ============================================================================
# ACCOUNT INFO
# ============================================================================
def show_account_info():
    """Show account information"""
    if not SESSION.user_info:
        notify("No account information available")
        return
    
    user = SESSION.user_info
    server = SESSION.server_info or {}
    
    # Calculate expiration
    exp_date = user.get('exp_date', '')
    if exp_date:
        try:
            exp_dt = datetime.fromtimestamp(int(exp_date))
            days_left = (exp_dt - datetime.now()).days
            exp_str = f"{exp_dt.strftime('%Y-%m-%d')} ({days_left} days left)"
        except:
            exp_str = str(exp_date)
    else:
        exp_str = "Unknown"
    
    # Get connection info
    active_cons = user.get('active_cons', 0)
    max_cons = user.get('max_connections', 1)
    
    info_text = f"""
Username: {user.get('username', 'N/A')}
Status: {'Active' if user.get('status', '') == 'Active' else user.get('status', 'Unknown')}
Expiration: {exp_str}
Is Trial: {'Yes' if user.get('is_trial', '0') == '1' else 'No'}

Connections: {active_cons}/{max_cons}
Created: {user.get('created_at', 'N/A')}

Server: {SESSION.dns}
Timezone: {server.get('timezone', 'N/A')}
Server Time: {server.get('time_now', 'N/A')}
    """
    
    xbmcgui.Dialog().textviewer("Account Information", info_text.strip())

def logout():
    """Logout and clear credentials"""
    confirm = xbmcgui.Dialog().yesno(
        "Logout",
        "Are you sure you want to logout?\n\n"
        "This will clear your saved credentials."
    )
    
    if confirm:
        SESSION.clear()
        EPG_CACHE.clear_all()
        notify("Logged out - credentials cleared")
        xbmc.executebuiltin('Container.Refresh')

# ============================================================================
# MAIN ROUTER
# ============================================================================
def router():
    """Main router for handling plugin actions"""
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:] if len(sys.argv) > 2 else ''))
    action = params.get('action')
    
    log(f"Action: {action}, Params: {params}")
    
    # IPTV Manager integration
    if action == 'iptv_channels':
        iptv_manager_channels()
        return
    elif action == 'iptv_epg':
        iptv_manager_epg()
        return
    
    # Check if authenticated - main menu shows notification on first login only
    if not action:
        if not SESSION.authenticated:
            if force_login(silent=False):  # Show welcome notification on first login
                main_menu()
        else:
            main_menu()
        return
    
    if action == 'logout':
        logout()
        return
    
    # For navigation actions, use silent login to avoid repeated notifications
    if not SESSION.authenticated:
        if not force_login(silent=True):  # Silent - no notification on navigation
            return
    
    # Route actions
    if action == 'tv_guide_choice':
        show_tv_guide_choice()
    elif action == 'poseidon_guide':
        launch_poseidon_guide()
    elif action == 'epg_guide':
        show_epg_guide()
    elif action == 'epg_all_channels':
        show_epg_all_channels()
    elif action == 'epg_category':
        show_epg_category(params.get('cat_id'))
    elif action == 'channel_epg':
        show_channel_epg(params.get('stream_id'), params.get('name'))
    elif action == 'refresh_epg':
        do_refresh_epg()
    elif action == 'live_categories':
        list_live_categories()
    elif action == 'live_streams':
        list_live_streams(params.get('cat_id'))
    elif action == 'vod_categories':
        list_vod_categories()
    elif action == 'vod_all':
        list_all_vod()
    elif action == 'vod_by_category':
        list_vod_by_category()
    elif action == 'vod_genres':
        list_vod_genres()
    elif action == 'vod_genre':
        list_vod_by_genre(params.get('genre'))
    elif action == 'vod_top_rated':
        list_top_rated_vod()
    elif action == 'vod_recent':
        list_recent_vod()
    elif action == 'vod_streams':
        list_vod_streams(params.get('cat_id'))
    elif action == 'vod_info':
        show_vod_info(params.get('stream_id'))
    elif action == 'series_categories':
        list_series_categories()
    elif action == 'series_list':
        list_series(params.get('cat_id'))
    elif action == 'series_seasons':
        list_series_seasons(params.get('series_id'))
    elif action == 'series_episodes':
        list_series_episodes(params.get('series_id'), params.get('season'))
    elif action == 'favorites':
        list_favorites()
    elif action == 'add_favorite':
        add_favorite(params.get('type'), params.get('id'), params.get('name'), params.get('icon'))
    elif action == 'remove_favorite':
        remove_favorite(params.get('type'), params.get('id'))
    elif action == 'recently_watched':
        list_recently_watched()
    elif action == 'clear_history':
        clear_history()
    elif action == 'search_menu':
        search_menu()
    elif action == 'search_live':
        search_content('live')
    elif action == 'search_vod':
        search_content('vod')
    elif action == 'search_series':
        search_content('series')
    elif action == 'search_all':
        search_content('all')
    elif action == 'catchup_categories':
        list_catchup_categories()
    elif action == 'catchup_channels':
        list_catchup_channels(params.get('cat_id'))
    elif action == 'channel_catchup':
        list_channel_catchup(params.get('stream_id'), params.get('name'))
    elif action == 'play_catchup':
        play_catchup(params.get('stream_id'), int(params.get('start', 0)), int(params.get('end', 0)))
    elif action == 'reminders_menu':
        reminders_menu()
    elif action == 'view_reminders':
        list_reminders()
    elif action == 'clear_reminders':
        clear_reminders()
    elif action == 'remove_reminder':
        remove_reminder(params.get('reminder_id'))
    elif action == 'set_reminder_channel':
        set_reminder_dialog(params.get('stream_id'), params.get('name'))
    elif action == 'add_reminder_direct':
        add_reminder(
            params.get('stream_id'),
            params.get('channel_name'),
            params.get('program_title'),
            params.get('start_timestamp')
        )
    elif action == 'account_info':
        show_account_info()
    elif action == 'service':
        run_background_service()
    else:
        log(f"Unknown action: {action}", xbmc.LOGWARNING)
        main_menu()

# ============================================================================
# BACKGROUND SERVICE - KEEP-ALIVE & REMINDERS
# ============================================================================
class PoseidonService(xbmc.Monitor):
    """Background service for stream keep-alive and reminder notifications"""
    
    def __init__(self):
        super().__init__()
        self.player = xbmc.Player()
        self.keep_alive_interval = 60  # Check every 60 seconds
        self.reminder_check_interval = 30  # Check reminders every 30 seconds
        self.last_keep_alive = 0
        self.last_reminder_check = 0
        log("Poseidon Background Service started")
    
    def check_reminders(self):
        """Check for upcoming reminders and notify user"""
        try:
            reminders = REMINDERS.get_all()
            now = time.time()
            reminder_advance = int(ADDON.getSetting('reminder_advance') or 5) * 60  # Convert to seconds
            
            for reminder in reminders:
                start_ts = int(reminder.get('start_timestamp', 0))
                reminder_id = reminder.get('id', '')
                
                # Check if reminder should trigger (within advance notice window)
                time_until_start = start_ts - now
                if 0 < time_until_start <= reminder_advance:
                    # Check if we already notified for this reminder
                    notified_key = f"notified_{reminder_id}"
                    if not ADDON.getSetting(notified_key):
                        program = reminder.get('program_title', 'Unknown')
                        channel = reminder.get('channel_name', 'Unknown')
                        mins = int(time_until_start / 60)
                        
                        notify(
                            f"{program} starts in {mins} min on {channel}",
                            title="Poseidon Reminder",
                            icon=xbmcgui.NOTIFICATION_INFO,
                            time=10000
                        )
                        ADDON.setSetting(notified_key, 'true')
                        log(f"Reminder triggered: {program} on {channel}")
                
                # Clean up old reminder notifications
                elif time_until_start < -300:  # 5 minutes past
                    notified_key = f"notified_{reminder_id}"
                    if ADDON.getSetting(notified_key):
                        ADDON.setSetting(notified_key, '')
        except Exception as e:
            log(f"Reminder check error: {e}", xbmc.LOGERROR)
    
    def keep_alive_check(self):
        """Monitor active playback and refresh connection if needed"""
        try:
            if self.player.isPlaying():
                # Check if it's a live stream from our addon
                playing_file = self.player.getPlayingFile()
                if SESSION.dns and SESSION.dns in playing_file and '/live/' in playing_file:
                    # Log keep-alive activity
                    log("Keep-alive: Live stream active", xbmc.LOGDEBUG)
                    
                    # Optionally refresh auth token if server supports it
                    if SESSION.is_valid() and not SESSION.authenticated:
                        log("Keep-alive: Re-authenticating session")
                        authenticate()
        except Exception as e:
            log(f"Keep-alive check error: {e}", xbmc.LOGERROR)
    
    def run(self):
        """Main service loop"""
        log("Poseidon Service: Running background tasks")
        
        while not self.abortRequested():
            current_time = time.time()
            
            # Keep-alive check
            if current_time - self.last_keep_alive >= self.keep_alive_interval:
                self.keep_alive_check()
                self.last_keep_alive = current_time
            
            # Reminder check
            if current_time - self.last_reminder_check >= self.reminder_check_interval:
                self.check_reminders()
                self.last_reminder_check = current_time
            
            # Sleep for 10 seconds before next check
            if self.waitForAbort(10):
                break
        
        log("Poseidon Background Service stopped")

def run_background_service():
    """Entry point for background service"""
    service = PoseidonService()
    service.run()

# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == '__main__':
    router()
