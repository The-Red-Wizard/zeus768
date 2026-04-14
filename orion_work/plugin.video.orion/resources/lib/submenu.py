# -*- coding: utf-8 -*-
"""
Orion Netflix-style Submenu - Custom dialog for Movies, TV Shows, and Trakt lists
Features horizontal poster carousels, backdrop banners, and card-based layouts
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
CATEGORY_TABS = 110
WATCH_BTN = 160
INFO_BTN = 161
ROW1_LIST = 200
ROW2_LIST = 300


class SubmenuDialog(xbmcgui.WindowXMLDialog):
    """
    Netflix-style submenu dialog with horizontal poster carousels,
    backdrop banners, and category tabs.
    """
    
    def __init__(self, *args, **kwargs):
        self.page_title = kwargs.get('page_title', 'Movies')
        self.page_subtitle = kwargs.get('page_subtitle', 'Browse all movies')
        self.categories = kwargs.get('categories', [])  # Tab filters
        self.row1_items = kwargs.get('row1_items', [])  # Main content
        self.row2_items = kwargs.get('row2_items', [])  # Genres/categories
        self.row1_title = kwargs.get('row1_title', 'Popular')
        self.row2_title = kwargs.get('row2_title', 'Genres')
        self.menu_type = kwargs.get('menu_type', 'movies')  # movies, tvshows, trakt
        
        self.selected_action = None
        self.selected_item = None
        self.selected_category = None
        self.current_focus_item = None
        
        super(SubmenuDialog, self).__init__(*args)
    
    def onInit(self):
        """Initialize the dialog"""
        # Set page properties
        self.setProperty('page_title', self.page_title)
        self.setProperty('page_subtitle', self.page_subtitle)
        self.setProperty('row1_title', self.row1_title)
        self.setProperty('row2_title', self.row2_title)
        
        # Set initial hero backdrop
        if self.row1_items:
            first_item = self.row1_items[0]
            self.setProperty('hero_backdrop', first_item.get('backdrop', ADDON_FANART))
            self._update_selected_info(first_item)
        else:
            self.setProperty('hero_backdrop', ADDON_FANART)
        
        # Populate category tabs first (always have items)
        self._populate_categories()
        
        # Populate content rows
        self._populate_row(ROW1_LIST, self.row1_items)
        self._populate_row(ROW2_LIST, self.row2_items)
        
        # Update page info
        self._update_page_info()
        
        # Focus on category tabs first (always populated), then move to content
        xbmc.sleep(50)  # Small delay to let controls initialize
        try:
            if self.categories:
                self.setFocusId(CATEGORY_TABS)
                # Auto-move down to content if available
                if self.row1_items:
                    xbmc.sleep(50)
                    self.setFocusId(ROW1_LIST)
            elif self.row1_items:
                self.setFocusId(ROW1_LIST)
        except Exception as e:
            xbmc.log(f"[Orion] Focus error: {e}", xbmc.LOGWARNING)
    
    def _populate_categories(self):
        """Populate the category filter tabs"""
        if not self.categories:
            return
        
        try:
            tab_list = self.getControl(CATEGORY_TABS)
            tab_list.reset()
            
            for cat in self.categories:
                li = xbmcgui.ListItem(label=cat.get('label', ''))
                li.setProperty('action', cat.get('action', ''))
                li.setProperty('category_id', str(cat.get('id', '')))
                tab_list.addItem(li)
        except Exception as e:
            xbmc.log(f"[Orion] Error populating categories: {e}", xbmc.LOGWARNING)
    
    def _populate_row(self, control_id, items):
        """Populate a content row with items"""
        try:
            row_list = self.getControl(control_id)
            row_list.reset()
            
            for item in items:
                li = xbmcgui.ListItem(label=item.get('title', item.get('label', '')))
                
                # Set artwork
                li.setArt({
                    'poster': item.get('poster', ADDON_ICON),
                    'thumb': item.get('poster', ADDON_ICON),
                    'fanart': item.get('backdrop', ADDON_FANART)
                })
                
                # Set properties
                rating = item.get('rating', 0)
                if rating:
                    li.setProperty('rating', f'{rating:.1f}')
                
                li.setProperty('tmdb_id', str(item.get('id', '')))
                li.setProperty('media_type', item.get('media_type', 'movie'))
                li.setProperty('year', str(item.get('year', '')))
                li.setProperty('backdrop', item.get('backdrop', ADDON_FANART))
                li.setProperty('plot', item.get('plot', ''))
                li.setProperty('genres', item.get('genres', ''))
                li.setProperty('quality', item.get('quality', ''))
                li.setProperty('action', item.get('action', ''))
                li.setProperty('genre_id', str(item.get('genre_id', '')))
                
                row_list.addItem(li)
        except Exception as e:
            xbmc.log(f"[Orion] Error populating row {control_id}: {e}", xbmc.LOGWARNING)
    
    def _update_selected_info(self, item):
        """Update the hero section with selected item info"""
        title = item.get('title', item.get('label', ''))
        year = item.get('year', '')
        rating = item.get('rating', 0)
        genres = item.get('genres', '')
        plot = item.get('plot', '')
        backdrop = item.get('backdrop', ADDON_FANART)
        
        # Build meta string
        meta_parts = []
        if year:
            meta_parts.append(str(year))
        if rating:
            meta_parts.append(f"★ {rating:.1f}")
        if genres:
            meta_parts.append(genres)
        meta_string = '  •  '.join(meta_parts)
        
        self.setProperty('selected_title', title)
        self.setProperty('selected_meta', meta_string)
        self.setProperty('selected_plot', plot[:300] + '...' if len(plot) > 300 else plot)
        self.setProperty('hero_backdrop', backdrop)
        
        self.current_focus_item = item
    
    def _update_page_info(self):
        """Update page info indicator"""
        try:
            row_list = self.getControl(ROW1_LIST)
            total = row_list.size()
            pos = row_list.getSelectedPosition() + 1
            self.setProperty('page_info', f'{pos} / {total}')
        except:
            pass
    
    def onFocus(self, controlId):
        """Handle focus changes to update hero section"""
        if controlId == ROW1_LIST:
            try:
                row_list = self.getControl(ROW1_LIST)
                selected = row_list.getSelectedItem()
                if selected:
                    item = {
                        'title': selected.getLabel(),
                        'year': selected.getProperty('year'),
                        'rating': float(selected.getProperty('rating') or 0),
                        'genres': selected.getProperty('genres'),
                        'plot': selected.getProperty('plot'),
                        'backdrop': selected.getProperty('backdrop'),
                        'id': selected.getProperty('tmdb_id'),
                        'media_type': selected.getProperty('media_type')
                    }
                    self._update_selected_info(item)
                    self._update_page_info()
            except Exception as e:
                xbmc.log(f"[Orion] Error updating focus: {e}", xbmc.LOGWARNING)
    
    def onClick(self, controlId):
        """Handle control clicks"""
        xbmc.log(f"[Orion] SubmenuDialog onClick: {controlId}", xbmc.LOGINFO)
        
        if controlId == BACK_BTN:
            self.selected_action = 'back'
            self.close()
        
        elif controlId == WATCH_BTN:
            if self.current_focus_item:
                self.selected_action = 'watch'
                self.selected_item = self.current_focus_item
                xbmc.log(f"[Orion] Watch button clicked for: {self.current_focus_item}", xbmc.LOGINFO)
                self.close()
        
        elif controlId == INFO_BTN:
            if self.current_focus_item:
                self.selected_action = 'info'
                self.selected_item = self.current_focus_item
                self.close()
        
        elif controlId == CATEGORY_TABS:
            try:
                tab_list = self.getControl(CATEGORY_TABS)
                selected = tab_list.getSelectedItem()
                if selected:
                    self.selected_action = 'category'
                    self.selected_category = {
                        'action': selected.getProperty('action'),
                        'id': selected.getProperty('category_id'),
                        'label': selected.getLabel()
                    }
                    xbmc.log(f"[Orion] Category tab selected: {self.selected_category}", xbmc.LOGINFO)
                    self.close()
            except Exception as e:
                xbmc.log(f"[Orion] Category tab error: {e}", xbmc.LOGWARNING)
        
        elif controlId == ROW1_LIST:
            try:
                row_list = self.getControl(ROW1_LIST)
                selected = row_list.getSelectedItem()
                if selected:
                    self.selected_action = 'select_item'
                    self.selected_item = {
                        'id': selected.getProperty('tmdb_id'),
                        'media_type': selected.getProperty('media_type'),
                        'title': selected.getLabel(),
                        'year': selected.getProperty('year')
                    }
                    xbmc.log(f"[Orion] ROW1 item selected: {self.selected_item}", xbmc.LOGINFO)
                    self.close()
            except Exception as e:
                xbmc.log(f"[Orion] ROW1 click error: {e}", xbmc.LOGWARNING)
        
        elif controlId == ROW2_LIST:
            try:
                row_list = self.getControl(ROW2_LIST)
                selected = row_list.getSelectedItem()
                if selected:
                    self.selected_action = 'select_genre'
                    self.selected_item = {
                        'action': selected.getProperty('action'),
                        'genre_id': selected.getProperty('genre_id'),
                        'title': selected.getLabel(),
                        'media_type': self.menu_type  # Pass menu type for grid
                    }
                    xbmc.log(f"[Orion] ROW2 genre selected: {self.selected_item}", xbmc.LOGINFO)
                    self.close()
            except Exception as e:
                xbmc.log(f"[Orion] ROW2 click error: {e}", xbmc.LOGWARNING)
        
        elif controlId == CATEGORY_TABS:
            try:
                tab_list = self.getControl(CATEGORY_TABS)
                selected = tab_list.getSelectedItem()
                if selected:
                    self.selected_action = 'category'
                    self.selected_category = {
                        'action': selected.getProperty('action'),
                        'id': selected.getProperty('category_id'),
                        'label': selected.getLabel(),
                        'media_type': self.menu_type  # Pass menu type for grid
                    }
                    xbmc.log(f"[Orion] Category tab selected: {self.selected_category}", xbmc.LOGINFO)
                    self.close()
            except Exception as e:
                xbmc.log(f"[Orion] Category tab error: {e}", xbmc.LOGWARNING)
    
    def onAction(self, action):
        """Handle remote/keyboard actions"""
        action_id = action.getId()
        
        if action_id in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            self.selected_action = 'back'
            self.close()
        
        elif action_id == ACTION_SELECT_ITEM:
            focus_id = self.getFocusId()
            self.onClick(focus_id)
        
        elif action_id in [ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT]:
            # Update hero when scrolling through items
            xbmc.sleep(100)
            focus_id = self.getFocusId()
            self.onFocus(focus_id)
    
    def get_result(self):
        """Return the dialog result"""
        return self.selected_action, self.selected_item, self.selected_category


def show_submenu(page_title, page_subtitle, row1_items, row2_items=None, 
                 categories=None, row1_title='Popular', row2_title='Genres', 
                 menu_type='movies'):
    """
    Show the Netflix-style submenu dialog.
    
    Args:
        page_title: Main title (e.g., "Movies", "TV Shows", "Trakt Watchlist")
        page_subtitle: Subtitle description
        row1_items: List of content items [{title, poster, backdrop, id, media_type, rating, year, plot, genres}]
        row2_items: List of genre/category items [{label, action, genre_id}]
        categories: List of filter tabs [{label, action, id}]
        row1_title: Title for content row
        row2_title: Title for genres row
        menu_type: Type of menu (movies, tvshows, trakt)
    
    Returns:
        Tuple of (action, selected_item, selected_category)
    """
    dialog = SubmenuDialog(
        'SubmenuDialog.xml',
        ADDON_PATH,
        'Default',
        '1080i',
        page_title=page_title,
        page_subtitle=page_subtitle,
        categories=categories or [],
        row1_items=row1_items or [],
        row2_items=row2_items or [],
        row1_title=row1_title,
        row2_title=row2_title,
        menu_type=menu_type
    )
    
    dialog.doModal()
    result = dialog.get_result()
    del dialog
    
    return result
