import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs
import os
import sys
import json
import time
import hashlib
import threading

ADDON = xbmcaddon.Addon()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_ID = ADDON.getAddonInfo('id')
FANART = os.path.join(ADDON_PATH, 'fanart.jpg')
MEDIA = os.path.join(ADDON_PATH, 'resources', 'media')
SKIN_PATH = os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', '1080i')

# Cache directory for faster menu loading
CACHE_DIR = xbmcvfs.translatePath('special://temp/tinklepad_cache/')
CACHE_EXPIRY = 3600  # 1 hour cache


def ensure_cache_dir():
    """Ensure cache directory exists"""
    if not xbmcvfs.exists(CACHE_DIR):
        xbmcvfs.mkdirs(CACHE_DIR)


def get_cache(cache_key, expiry=CACHE_EXPIRY):
    """Get cached data if valid"""
    try:
        ensure_cache_dir()
        cache_file = os.path.join(CACHE_DIR, f'{cache_key}.json')
        if xbmcvfs.exists(cache_file):
            stat = xbmcvfs.Stat(cache_file)
            if time.time() - stat.st_mtime() < expiry:
                with xbmcvfs.File(cache_file, 'r') as f:
                    return json.loads(f.read())
    except Exception as e:
        xbmc.log(f'[Tinklepad] Cache read error: {e}', xbmc.LOGDEBUG)
    return None


def set_cache(cache_key, data):
    """Save data to cache"""
    try:
        ensure_cache_dir()
        cache_file = os.path.join(CACHE_DIR, f'{cache_key}.json')
        with xbmcvfs.File(cache_file, 'w') as f:
            f.write(json.dumps(data))
    except Exception as e:
        xbmc.log(f'[Tinklepad] Cache write error: {e}', xbmc.LOGDEBUG)


def clear_cache():
    """Clear all cached data"""
    try:
        if xbmcvfs.exists(CACHE_DIR):
            dirs, files = xbmcvfs.listdir(CACHE_DIR)
            for f in files:
                xbmcvfs.delete(os.path.join(CACHE_DIR, f))
        return True
    except:
        return False


def gold(text):
    return f"[COLOR FFFFD700][B]{text}[/B][/COLOR]"


def add_menu_items(handle, items, cache_key=None):
    """Builds menus with Fanart and Golden Eagle branding"""
    for label, action, icon, *extra in items:
        params = extra[0] if extra else {}
        url = f"{sys.argv[0]}?action={action}"
        if params:
            import urllib.parse
            url += "&" + urllib.parse.urlencode(params)
        
        list_item = xbmcgui.ListItem(label)
        icon_path = os.path.join(MEDIA, icon)
        
        list_item.setArt({
            'icon': icon_path,
            'thumb': icon_path,
            'fanart': FANART,
            'poster': icon_path
        })
        
        xbmcplugin.addDirectoryItem(handle, url, list_item, isFolder=True)
    
    xbmcplugin.setContent(handle, 'addons')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def play_intro():
    try:
        show_video = ADDON.getSetting('startup_video').lower() == 'true'
        already_played = ADDON.getSetting('first_run_played').lower() == 'true'
        if ADDON.getSetting('startup_video') == "": 
            show_video = True
    except:
        show_video = True
        already_played = False

    if show_video and not already_played:
        path = os.path.join(MEDIA, 'startup.mp4')
        if os.path.exists(path):
            player = xbmc.Player()
            player.play(path)
            xbmc.executebuiltin("ActivateWindow(fullscreenvideo)")
            while player.isPlaying():
                xbmc.sleep(500)
            ADDON.setSetting('first_run_played', 'true')


# ==================== CUSTOM XML SEARCH DIALOG ====================

# Control IDs from source_search.xml
SEARCH_CTRL_FANART = 100
SEARCH_CTRL_POSTER = 200
SEARCH_CTRL_TITLE = 300
SEARCH_CTRL_META = 301
SEARCH_CTRL_GENRES = 302
SEARCH_CTRL_HEADER = 501
SEARCH_CTRL_PROVIDER = 502
SEARCH_CTRL_SOURCES = 503
SEARCH_CTRL_PROGRESS_BAR = 504
SEARCH_CTRL_PROGRESS_PCT = 505
SEARCH_CTRL_CANCEL_BTN = 550
SEARCH_CTRL_VIEW_BTN = 551

# Provider progress bars and status
SEARCH_CTRL_FREE_BAR = 610
SEARCH_CTRL_FREE_STATUS = 611
SEARCH_CTRL_DDL_BAR = 620
SEARCH_CTRL_DDL_STATUS = 621
SEARCH_CTRL_TORRENT_BAR = 630
SEARCH_CTRL_TORRENT_STATUS = 631
SEARCH_CTRL_PREMIUM_BAR = 640
SEARCH_CTRL_PREMIUM_STATUS = 641


class TinklepadSearchWindow(xbmcgui.WindowXMLDialog):
    """
    Custom XML Search Progress Window with Golden Theme
    Uses threading to run scrapers in background while updating UI
    """
    
    def __init__(self, *args, **kwargs):
        self.title = kwargs.get('title', '')
        self.year = kwargs.get('year', '')
        self.fanart = kwargs.get('fanart', '')
        self.poster = kwargs.get('poster', '')
        self.plot = kwargs.get('plot', '')
        self.rating = kwargs.get('rating', '')
        self.runtime = kwargs.get('runtime', '')
        self.genres = kwargs.get('genres', '')
        self.content_type = kwargs.get('content_type', 'movie')
        
        self.cancelled = False
        self.search_complete = False
        self.sources_count = 0
        self.progress = 0
        self.current_provider = ''
        
        # Provider-specific counts
        self.free_count = 0
        self.ddl_count = 0
        self.torrent_count = 0
        self.premium_count = 0
        
        # Scraper callback
        self.scraper_callback = None
        self.scraper_thread = None
        self.all_sources = []
        
        xbmcgui.WindowXMLDialog.__init__(self)
    
    def onInit(self):
        """Initialize window with metadata"""
        try:
            # Set window properties for XML binding
            display_title = f'{self.title} ({self.year})' if self.year else self.title
            
            self.setProperty('fanart', self.fanart or FANART)
            self.setProperty('poster', self.poster)
            self.setProperty('title', display_title)
            
            # Build meta line (rating, runtime)
            meta_parts = []
            if self.rating:
                meta_parts.append(f'★ {self.rating}')
            if self.runtime:
                meta_parts.append(f'{self.runtime} min')
            if self.year:
                meta_parts.append(str(self.year))
            self.setProperty('meta_line', ' | '.join(meta_parts))
            
            self.setProperty('genres', self.genres)
            self.setProperty('current_provider', 'Initializing...')
            self.setProperty('sources_found', '0 Sources Found')
            self.setProperty('progress_percent', '0%')
            
            # Initialize provider status
            self.setProperty('free_status', 'Pending...')
            self.setProperty('ddl_status', 'Pending...')
            self.setProperty('torrent_status', 'Pending...')
            self.setProperty('premium_status', 'Pending...')
            
            # Set initial focus
            self.setFocusId(SEARCH_CTRL_CANCEL_BTN)
            
            xbmc.log('[Tinklepad] Search window initialized', xbmc.LOGINFO)
            
        except Exception as e:
            xbmc.log(f'[Tinklepad] Search window init error: {e}', xbmc.LOGERROR)
    
    def start_search(self, scraper_func, *args, **kwargs):
        """Start scraper in background thread"""
        self.scraper_callback = scraper_func
        self.scraper_thread = threading.Thread(
            target=self._run_scrapers,
            args=args,
            kwargs=kwargs,
            daemon=True
        )
        self.scraper_thread.start()
    
    def _run_scrapers(self, *args, **kwargs):
        """Run scrapers in background thread"""
        try:
            if self.scraper_callback:
                self.all_sources = self.scraper_callback(
                    *args,
                    progress_callback=self.update_progress,
                    cancel_check=self.is_cancelled,
                    **kwargs
                )
                self.search_complete = True
                
                # Final update
                self.update_progress(
                    progress=100,
                    current_provider='Search Complete!',
                    sources_count=len(self.all_sources)
                )
        except Exception as e:
            xbmc.log(f'[Tinklepad] Scraper thread error: {e}', xbmc.LOGERROR)
            self.search_complete = True
    
    def update_progress(self, progress=0, current_provider='', sources_count=0,
                       free_count=0, ddl_count=0, torrent_count=0, premium_count=0,
                       free_progress=0, ddl_progress=0, torrent_progress=0, premium_progress=0):
        """Update progress display from scraper thread (thread-safe)"""
        self.progress = progress
        self.sources_count = sources_count
        self.current_provider = current_provider
        self.free_count = free_count
        self.ddl_count = ddl_count
        self.torrent_count = torrent_count
        self.premium_count = premium_count
        
        # Use executebuiltin for thread-safe UI updates
        try:
            self.setProperty('current_provider', f'Searching: {current_provider}')
            self.setProperty('sources_found', f'{sources_count} Sources Found')
            self.setProperty('progress_percent', f'{progress}%')
            
            # Update provider-specific status
            if free_count > 0:
                self.setProperty('free_status', f'Found: {free_count} links')
            elif free_progress > 0:
                self.setProperty('free_status', 'Searching...')
            
            if ddl_count > 0:
                self.setProperty('ddl_status', f'Found: {ddl_count} links')
            elif ddl_progress > 0:
                self.setProperty('ddl_status', 'Searching...')
                
            if torrent_count > 0:
                self.setProperty('torrent_status', f'Found: {torrent_count} links')
            elif torrent_progress > 0:
                self.setProperty('torrent_status', 'Searching...')
                
            if premium_count > 0:
                self.setProperty('premium_status', f'Found: {premium_count} links')
            elif premium_progress > 0:
                self.setProperty('premium_status', 'Searching...')
                
        except Exception as e:
            xbmc.log(f'[Tinklepad] Progress update error: {e}', xbmc.LOGDEBUG)
    
    def is_cancelled(self):
        """Check if search was cancelled"""
        return self.cancelled
    
    def get_sources(self):
        """Get collected sources after search completes"""
        return self.all_sources
    
    def onClick(self, controlId):
        """Handle button clicks"""
        if controlId == SEARCH_CTRL_CANCEL_BTN:
            self.cancelled = True
            self.close()
        elif controlId == SEARCH_CTRL_VIEW_BTN:
            if self.search_complete or self.sources_count > 0:
                self.close()
    
    def onAction(self, action):
        """Handle remote/keyboard actions"""
        action_id = action.getId()
        
        # Back/escape actions
        if action_id in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU, 
                         xbmcgui.ACTION_STOP, 92):
            self.cancelled = True
            self.close()


# ==================== CUSTOM XML SOURCE SELECT DIALOG ====================

# Control IDs from source_select.xml
SELECT_CTRL_FANART = 100
SELECT_CTRL_POSTER = 200
SELECT_CTRL_TOTAL = 201
SELECT_CTRL_4K = 202
SELECT_CTRL_1080P = 203
SELECT_CTRL_720P = 204
SELECT_CTRL_SD = 205
SELECT_CTRL_DEBRID = 206
SELECT_CTRL_TITLE = 300
SELECT_CTRL_LIST = 1000
SELECT_CTRL_SCROLLBAR = 1001
SELECT_CTRL_CANCEL = 501


class TinklepadSourceSelectWindow(xbmcgui.WindowXMLDialog):
    """
    Custom XML Source Selection Window with Golden Theme
    Displays sources in a beautiful scrollable list
    """
    
    def __init__(self, *args, **kwargs):
        self.sources = kwargs.get('sources', [])
        self.title = kwargs.get('title', '')
        self.year = kwargs.get('year', '')
        self.fanart = kwargs.get('fanart', '')
        self.poster = kwargs.get('poster', '')
        self.debrid_status = kwargs.get('debrid_status', '')
        
        self.selected_index = -1
        
        xbmcgui.WindowXMLDialog.__init__(self)
    
    def onInit(self):
        """Initialize source selection window"""
        try:
            display_title = f'{self.title} ({self.year})' if self.year else self.title
            
            # Set window properties
            self.setProperty('fanart', self.fanart or FANART)
            self.setProperty('poster', self.poster)
            self.setProperty('title', display_title)
            self.setProperty('total_sources', str(len(self.sources)))
            self.setProperty('debrid_status', self.debrid_status)
            
            # Count by quality
            count_4k = sum(1 for s in self.sources if s.get('quality') == '4K')
            count_1080p = sum(1 for s in self.sources if s.get('quality') == '1080p')
            count_720p = sum(1 for s in self.sources if s.get('quality') in ('720p', 'HD'))
            count_sd = sum(1 for s in self.sources if s.get('quality') in ('480p', 'SD', 'CAM'))
            
            self.setProperty('quality_4k', f'4K: {count_4k}' if count_4k else '')
            self.setProperty('quality_1080p', f'1080p: {count_1080p}' if count_1080p else '')
            self.setProperty('quality_720p', f'720p: {count_720p}' if count_720p else '')
            self.setProperty('quality_sd', f'SD: {count_sd}' if count_sd else '')
            
            # Populate source list
            self._populate_source_list()
            
            # Set focus to list
            self.setFocusId(SELECT_CTRL_LIST)
            
            xbmc.log(f'[Tinklepad] Source select window initialized with {len(self.sources)} sources', xbmc.LOGINFO)
            
        except Exception as e:
            xbmc.log(f'[Tinklepad] Source select init error: {e}', xbmc.LOGERROR)
    
    def _populate_source_list(self):
        """Populate the source list control"""
        try:
            list_control = self.getControl(SELECT_CTRL_LIST)
            list_control.reset()
            
            for i, source in enumerate(self.sources):
                provider = source.get('provider', 'Unknown')
                quality = source.get('quality', 'HD')
                host = source.get('host', '')
                
                # Build label
                if source.get('free') and source.get('direct_play'):
                    label = f'[COLOR lime][FREE][/COLOR] {provider}'
                    source_type = 'Free Stream'
                elif source.get('torrent'):
                    label = f'[COLOR orange][TORRENT][/COLOR] {provider}'
                    source_type = 'Torrent/Magnet'
                elif source.get('debrid'):
                    label = f'[COLOR gold][DDL][/COLOR] {provider}'
                    source_type = 'Direct Download'
                else:
                    label = provider
                    source_type = host or 'Stream'
                
                # Extract size
                import re
                size_match = re.search(r'\[(\d+(?:\.\d+)?\s*(?:GB|MB))\]', source.get('label', ''))
                size = size_match.group(1) if size_match else ''
                
                # Quality color
                quality_colors = {
                    '4K': 'FFFF4444',
                    '1080p': 'FF00FF00', 
                    '720p': 'FF4488FF',
                    'HD': 'FF4488FF',
                    '480p': 'FFAAAAAA',
                    'SD': 'FFAAAAAA',
                    'CAM': 'FFFF8800'
                }
                quality_color = quality_colors.get(quality, 'FFFFFFFF')
                
                # Create list item
                li = xbmcgui.ListItem(label)
                li.setProperty('source_type', source_type)
                li.setProperty('quality', quality)
                li.setProperty('quality_color', quality_color)
                li.setProperty('size', size)
                li.setProperty('host', host)
                li.setProperty('index', str(i))
                
                list_control.addItem(li)
                
        except Exception as e:
            xbmc.log(f'[Tinklepad] Source list population error: {e}', xbmc.LOGERROR)
    
    def get_selected_index(self):
        """Get the selected source index"""
        return self.selected_index
    
    def onClick(self, controlId):
        """Handle item selection"""
        if controlId == SELECT_CTRL_LIST:
            try:
                list_control = self.getControl(SELECT_CTRL_LIST)
                selected_item = list_control.getSelectedItem()
                if selected_item:
                    self.selected_index = int(selected_item.getProperty('index'))
                    xbmc.log(f'[Tinklepad] Selected source index: {self.selected_index}', xbmc.LOGINFO)
                    self.close()
            except Exception as e:
                xbmc.log(f'[Tinklepad] Selection error: {e}', xbmc.LOGERROR)
        
        elif controlId == SELECT_CTRL_CANCEL:
            self.selected_index = -1
            self.close()
    
    def onAction(self, action):
        """Handle remote/keyboard actions"""
        action_id = action.getId()
        
        # Back/escape
        if action_id in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU,
                         xbmcgui.ACTION_STOP, 92):
            self.selected_index = -1
            self.close()
        
        # Select action
        elif action_id == xbmcgui.ACTION_SELECT_ITEM:
            focused_id = self.getFocusId()
            if focused_id == SELECT_CTRL_LIST:
                self.onClick(SELECT_CTRL_LIST)


# ==================== HELPER FUNCTIONS ====================

def create_search_dialog(title='', year='', fanart='', poster='', plot='', 
                         rating='', runtime='', genres='', content_type='movie'):
    """
    Create and return the custom search progress window
    Falls back to standard dialog if XML fails
    """
    try:
        window = TinklepadSearchWindow(
            'source_search.xml',
            ADDON_PATH,
            'Default',
            '1080i',
            title=title,
            year=year,
            fanart=fanart,
            poster=poster,
            plot=plot,
            rating=rating,
            runtime=runtime,
            genres=genres,
            content_type=content_type
        )
        return window
    except Exception as e:
        xbmc.log(f'[Tinklepad] Custom search dialog failed, using fallback: {e}', xbmc.LOGWARNING)
        return TinklepadSearchDialogFallback(
            title=title, year=year, fanart=fanart, poster=poster,
            plot=plot, rating=rating, runtime=runtime, genres=genres,
            content_type=content_type
        )


def show_source_select(sources, title='', year='', fanart='', poster='', debrid_status=''):
    """
    Show source selection dialog and return selected index
    Falls back to standard dialog if XML fails
    """
    if not sources:
        return -1
    
    try:
        window = TinklepadSourceSelectWindow(
            'source_select.xml',
            ADDON_PATH,
            'Default',
            '1080i',
            sources=sources,
            title=title,
            year=year,
            fanart=fanart,
            poster=poster,
            debrid_status=debrid_status
        )
        window.doModal()
        selected = window.get_selected_index()
        del window
        return selected
    except Exception as e:
        xbmc.log(f'[Tinklepad] Custom source select failed, using fallback: {e}', xbmc.LOGWARNING)
        return show_source_select_fallback(sources, title, year, fanart, poster, debrid_status)


# ==================== FALLBACK DIALOGS (Standard Kodi) ====================

class TinklepadSearchDialogFallback:
    """
    Fallback search dialog using standard Kodi DialogProgress
    Used when custom XML window fails
    """
    
    def __init__(self, title='', year='', fanart='', poster='', plot='', 
                 rating='', runtime='', genres='', content_type='movie'):
        self.title = title
        self.year = year
        self.cancelled = False
        self.sources_count = 0
        self.progress = 0
        self.search_complete = False
        self.all_sources = []
        
        display_title = f'{title} ({year})' if year else title
        
        self.dialog = xbmcgui.DialogProgress()
        self.dialog.create(
            'TINKLEPAD - Source Link Search',
            f'[COLOR gold][B]{display_title}[/B][/COLOR]\n\nInitializing providers...'
        )
    
    def show(self):
        """Compatibility method"""
        pass
    
    def start_search(self, scraper_func, *args, **kwargs):
        """Start scraper (runs synchronously in fallback mode)"""
        pass
    
    def update_progress(self, progress=0, current_provider='', sources_count=0, **kwargs):
        """Update progress dialog"""
        self.progress = progress
        self.sources_count = sources_count
        
        if self.dialog:
            free_count = kwargs.get('free_count', 0)
            ddl_count = kwargs.get('ddl_count', 0)
            torrent_count = kwargs.get('torrent_count', 0)
            
            line1 = f'[COLOR gold]Provider:[/COLOR] {current_provider}'
            line2 = f'[COLOR lime]Sources Found: {sources_count}[/COLOR]'
            if free_count or ddl_count or torrent_count:
                line3 = f'Free: {free_count} | DDL: {ddl_count} | Torrent: {torrent_count}'
            else:
                line3 = f'Progress: {progress}%'
            self.dialog.update(progress, f'{line1}\n{line2}\n{line3}')
    
    def is_cancelled(self):
        """Check if cancelled"""
        if self.dialog:
            return self.dialog.iscanceled()
        return self.cancelled
    
    def get_sources(self):
        return self.all_sources
    
    def close(self):
        """Close dialog"""
        if self.dialog:
            self.dialog.close()
    
    def doModal(self):
        """Compatibility - dialog is already shown"""
        pass


def show_source_select_fallback(sources, title='', year='', fanart='', poster='', debrid_status=''):
    """
    Fallback source selection using standard Kodi select dialog
    """
    if not sources:
        return -1
    
    # Build labels with detailed info
    labels = []
    for s in sources:
        provider = s.get('provider', 'Unknown')
        quality = s.get('quality', 'HD')
        host = s.get('host', '')
        
        import re
        size_match = re.search(r'\[(\d+(?:\.\d+)?\s*(?:GB|MB))\]', s.get('label', ''))
        size = size_match.group(1) if size_match else ''
        
        # Build label with colors
        if s.get('free') and s.get('direct_play'):
            label = f'[COLOR lime][FREE][/COLOR] {provider}'
        elif s.get('torrent'):
            label = f'[COLOR orange][TORRENT][/COLOR] {provider}'
        elif s.get('debrid'):
            label = f'[COLOR gold][DDL][/COLOR] {provider}'
        else:
            label = provider
        
        # Add quality badge
        if quality == '4K':
            label += f' [COLOR red][B]{quality}[/B][/COLOR]'
        elif quality == '1080p':
            label += f' [COLOR lime][B]{quality}[/B][/COLOR]'
        elif quality in ('720p', 'HD'):
            label += f' [COLOR deepskyblue][B]{quality}[/B][/COLOR]'
        else:
            label += f' [{quality}]'
        
        if size:
            label += f' • {size}'
        if host and host != 'Direct':
            label += f' • [COLOR gray]{host}[/COLOR]'
        
        labels.append(label)
    
    # Build header
    display_title = f'{title} ({year})' if year else title
    
    count_free = sum(1 for s in sources if s.get('free'))
    count_4k = sum(1 for s in sources if s.get('quality') == '4K')
    count_1080p = sum(1 for s in sources if s.get('quality') == '1080p')
    
    stats_parts = []
    if count_free:
        stats_parts.append(f'[COLOR lime]{count_free} Free[/COLOR]')
    if count_4k:
        stats_parts.append(f'[COLOR red]{count_4k} 4K[/COLOR]')
    if count_1080p:
        stats_parts.append(f'[COLOR lime]{count_1080p} 1080p[/COLOR]')
    
    header = f'[COLOR gold][B]TINKLEPAD[/B][/COLOR] - {display_title}'
    if stats_parts:
        header += f'\n{len(sources)} Sources: ' + ' | '.join(stats_parts)
    
    dialog = xbmcgui.Dialog()
    return dialog.select(header, labels, useDetails=False)
