# -*- coding: utf-8 -*-
"""
Orion Netflix-style Grid View - Full page grid with pagination
Displays 30 items per page (6 columns × 5 rows) with Next/Prev navigation
"""

import xbmc
import xbmcgui
import xbmcaddon
import os

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_FANART = ADDON.getAddonInfo('fanart')

# Action codes
ACTION_SELECT_ITEM = 7
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_CONTEXT_MENU = 117
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4

# Control IDs
BACK_BTN = 50
GRID_PANEL = 500
PREV_BTN = 600
NEXT_BTN = 700

# Items per page
ITEMS_PER_PAGE = 30


class GridDialog(xbmcgui.WindowXMLDialog):
    """
    Netflix-style full grid view with page navigation.
    Shows 30 items per page (6 columns × 5 rows).
    """
    
    def __init__(self, *args, **kwargs):
        self.page_title = kwargs.get('page_title', 'Browse')
        self.page_subtitle = kwargs.get('page_subtitle', '')
        self.media_type = kwargs.get('media_type', 'movie')  # movie or tv
        self.fetch_function = kwargs.get('fetch_function', None)  # Function to fetch more pages
        self.fetch_params = kwargs.get('fetch_params', {})  # Parameters for fetch function
        self.initial_items = kwargs.get('initial_items', [])  # First page items
        self.total_pages = kwargs.get('total_pages', 1)
        self.total_results = kwargs.get('total_results', 0)
        
        self.current_page = 1
        self.all_items = {}  # Cache: {page_num: [items]}
        self.all_items[1] = self.initial_items  # Store initial items
        
        self.selected_action = None
        self.selected_item = None
        
        super(GridDialog, self).__init__(*args)
    
    def onInit(self):
        """Initialize the dialog"""
        # Set page properties
        self.setProperty('page_title', self.page_title)
        self.setProperty('page_subtitle', self.page_subtitle)
        self.setProperty('current_page', str(self.current_page))
        self.setProperty('total_pages', str(self.total_pages))
        self.setProperty('total_items', str(self.total_results))
        
        # Populate grid with first page
        self._populate_grid()
        self._update_page_info()
        
        # Focus on grid
        xbmc.sleep(50)
        self.setFocusId(GRID_PANEL)
    
    def _populate_grid(self):
        """Populate the grid panel with current page items"""
        try:
            grid = self.getControl(GRID_PANEL)
            grid.reset()
            
            items = self.all_items.get(self.current_page, [])
            
            for item in items:
                li = xbmcgui.ListItem(label=item.get('title', item.get('name', '')))
                
                # Set artwork
                poster = item.get('poster', ADDON_ICON)
                backdrop = item.get('backdrop', ADDON_FANART)
                
                li.setArt({
                    'poster': poster,
                    'thumb': poster,
                    'fanart': backdrop
                })
                
                # Set properties
                rating = item.get('rating', item.get('vote_average', 0))
                if rating:
                    li.setProperty('rating', f'{float(rating):.1f}')
                
                year = item.get('year', '')
                if not year:
                    # Extract year from release_date or first_air_date
                    date_str = item.get('release_date', item.get('first_air_date', ''))
                    if date_str and len(date_str) >= 4:
                        year = date_str[:4]
                
                li.setProperty('year', str(year))
                li.setProperty('tmdb_id', str(item.get('id', '')))
                li.setProperty('media_type', item.get('media_type', self.media_type))
                li.setProperty('backdrop', backdrop)
                li.setProperty('plot', item.get('plot', item.get('overview', '')))
                li.setProperty('genres', item.get('genres', ''))
                
                # Progress bar support
                progress = item.get('progress', 0)
                if progress and int(progress) > 0:
                    li.setProperty('progress', str(progress))
                    # Max width 348px for the grid poster card
                    progress_width = str(int(348 * int(progress) / 100))
                    li.setProperty('progress_width', progress_width)
                
                grid.addItem(li)
                
            xbmc.log(f"[Orion] Grid populated with {len(items)} items for page {self.current_page}", xbmc.LOGINFO)
            
        except Exception as e:
            xbmc.log(f"[Orion] Error populating grid: {e}", xbmc.LOGWARNING)
    
    def _update_page_info(self):
        """Update page navigation info"""
        self.setProperty('current_page', str(self.current_page))
        self.setProperty('total_pages', str(self.total_pages))
        
        # Calculate items range
        items_start = ((self.current_page - 1) * ITEMS_PER_PAGE) + 1
        items_on_page = len(self.all_items.get(self.current_page, []))
        items_end = items_start + items_on_page - 1
        
        self.setProperty('items_start', str(items_start))
        self.setProperty('items_end', str(items_end))
    
    def _fetch_page(self, page_num):
        """Fetch items for a specific page"""
        if page_num in self.all_items:
            return True  # Already cached
        
        if not self.fetch_function:
            return False
        
        try:
            xbmc.log(f"[Orion] Fetching page {page_num}...", xbmc.LOGINFO)
            
            # Show loading indicator
            self.setProperty('loading', 'true')
            
            # Call the fetch function with page number
            result = self.fetch_function(page=page_num, **self.fetch_params)
            
            if result and 'results' in result:
                # Process items
                items = []
                for item in result['results']:
                    processed = self._process_item(item)
                    items.append(processed)
                
                self.all_items[page_num] = items
                
                # Update total pages if provided
                if 'total_pages' in result:
                    self.total_pages = min(result['total_pages'], 500)  # TMDB caps at 500
                    self.setProperty('total_pages', str(self.total_pages))
                
                if 'total_results' in result:
                    self.total_results = result['total_results']
                    self.setProperty('total_items', str(self.total_results))
                
                self.setProperty('loading', '')
                return True
            
            self.setProperty('loading', '')
            return False
            
        except Exception as e:
            xbmc.log(f"[Orion] Error fetching page {page_num}: {e}", xbmc.LOGWARNING)
            self.setProperty('loading', '')
            return False
    
    def _process_item(self, item):
        """Process a TMDB item into our format"""
        from .tmdb import get_poster_url, get_backdrop_url, get_genre_names
        
        media_type = item.get('media_type', self.media_type)
        title = item.get('title', item.get('name', ''))
        
        # Get year
        date_str = item.get('release_date', item.get('first_air_date', ''))
        year = date_str[:4] if date_str and len(date_str) >= 4 else ''
        
        # Get images
        poster = get_poster_url(item.get('poster_path'))
        backdrop = get_backdrop_url(item.get('backdrop_path'))
        
        # Get genre names
        genre_ids = item.get('genre_ids', [])
        genres = get_genre_names(media_type, genre_ids) if genre_ids else ''
        
        return {
            'id': item.get('id'),
            'title': title,
            'year': year,
            'rating': item.get('vote_average', 0),
            'poster': poster or ADDON_ICON,
            'backdrop': backdrop or ADDON_FANART,
            'plot': item.get('overview', ''),
            'genres': genres,
            'media_type': media_type
        }
    
    def _go_to_page(self, page_num):
        """Navigate to a specific page"""
        if page_num < 1 or page_num > self.total_pages:
            return
        
        if page_num == self.current_page:
            return
        
        # Fetch page if needed
        if self._fetch_page(page_num):
            self.current_page = page_num
            self._populate_grid()
            self._update_page_info()
            
            # Reset focus to grid
            xbmc.sleep(50)
            self.setFocusId(GRID_PANEL)
    
    def onClick(self, controlId):
        """Handle control clicks"""
        xbmc.log(f"[Orion] GridDialog onClick: {controlId}", xbmc.LOGINFO)
        
        if controlId == BACK_BTN:
            self.selected_action = 'back'
            self.close()
        
        elif controlId == PREV_BTN:
            if self.current_page > 1:
                self._go_to_page(self.current_page - 1)
        
        elif controlId == NEXT_BTN:
            if self.current_page < self.total_pages:
                self._go_to_page(self.current_page + 1)
        
        elif controlId == GRID_PANEL:
            try:
                grid = self.getControl(GRID_PANEL)
                selected = grid.getSelectedItem()
                if selected:
                    self.selected_action = 'select_item'
                    self.selected_item = {
                        'id': selected.getProperty('tmdb_id'),
                        'media_type': selected.getProperty('media_type'),
                        'title': selected.getLabel(),
                        'year': selected.getProperty('year'),
                        'poster': selected.getArt('poster'),
                        'backdrop': selected.getProperty('backdrop'),
                        'plot': selected.getProperty('plot'),
                        'rating': selected.getProperty('rating'),
                        'genres': selected.getProperty('genres')
                    }
                    xbmc.log(f"[Orion] Grid item selected: {self.selected_item}", xbmc.LOGINFO)
                    self.close()
            except Exception as e:
                xbmc.log(f"[Orion] Grid click error: {e}", xbmc.LOGWARNING)
    
    def onAction(self, action):
        """Handle remote/keyboard actions"""
        action_id = action.getId()
        
        if action_id in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            self.selected_action = 'back'
            self.close()
        
        elif action_id == ACTION_SELECT_ITEM:
            focus_id = self.getFocusId()
            self.onClick(focus_id)
    
    def get_result(self):
        """Return the dialog result"""
        return self.selected_action, self.selected_item


def show_grid(page_title, page_subtitle='', media_type='movie', 
              fetch_function=None, fetch_params=None, 
              initial_items=None, total_pages=1, total_results=0):
    """
    Show the Netflix-style grid dialog.
    
    Args:
        page_title: Main title (e.g., "Action Movies", "Comedy TV Shows")
        page_subtitle: Subtitle/description
        media_type: 'movie' or 'tv'
        fetch_function: Function to fetch more pages - should accept 'page' parameter
        fetch_params: Additional parameters for fetch function
        initial_items: Pre-fetched first page items
        total_pages: Total number of pages available
        total_results: Total number of results
    
    Returns:
        Tuple of (action, selected_item)
    """
    dialog = GridDialog(
        'GridDialog.xml',
        ADDON_PATH,
        'Default',
        '1080i',
        page_title=page_title,
        page_subtitle=page_subtitle,
        media_type=media_type,
        fetch_function=fetch_function,
        fetch_params=fetch_params or {},
        initial_items=initial_items or [],
        total_pages=total_pages,
        total_results=total_results
    )
    
    dialog.doModal()
    result = dialog.get_result()
    del dialog
    
    return result
