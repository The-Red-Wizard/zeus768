# -*- coding: utf-8 -*-
"""
Orion Main Menu - Fullscreen custom home screen with sidebar navigation
Netflix/Plex style interface with content rows
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
SIDEBAR_LIST = 100
SETTINGS_BTN = 101
PLAY_BTN = 154
ROW1_LIST = 200
ROW2_LIST = 205
ROW3_LIST = 210
ROW4_LIST = 215


class MainMenuDialog(xbmcgui.WindowXMLDialog):
    """
    Fullscreen main menu with sidebar navigation and content rows.
    """
    
    def __init__(self, *args, **kwargs):
        self.menu_items = kwargs.get('menu_items', [])
        self.row1_items = kwargs.get('row1_items', [])
        self.row2_items = kwargs.get('row2_items', [])
        self.row3_items = kwargs.get('row3_items', [])
        self.row4_items = kwargs.get('row4_items', [])
        self.hero_data = kwargs.get('hero_data', {})
        self.row_titles = kwargs.get('row_titles', {})
        
        self.selected_action = None
        self.selected_item = None
        self.stay_in_menu = True  # Flag to keep menu alive
        
        super(MainMenuDialog, self).__init__(*args)
    
    def onInit(self):
        """Initialize the dialog"""
        # Set hero section properties
        self.setProperty('hero_title', self.hero_data.get('title', 'Continue Watching'))
        self.setProperty('hero_main', self.hero_data.get('main', 'CONTINUE WATCHING'))
        self.setProperty('hero_subtitle', self.hero_data.get('subtitle', ''))
        self.setProperty('featured_title', self.hero_data.get('featured', ''))
        self.setProperty('backdrop', self.hero_data.get('backdrop', ADDON_FANART))
        
        # Set row titles
        self.setProperty('row1_title', self.row_titles.get('row1', 'TRENDING MOVIES'))
        self.setProperty('row2_title', self.row_titles.get('row2', 'NEW TV SHOWS'))
        self.setProperty('row3_title', self.row_titles.get('row3', 'POPULAR'))
        self.setProperty('row4_title', self.row_titles.get('row4', 'YOUR WATCHLIST'))
        
        # Populate sidebar menu
        self._populate_sidebar()
        
        # Populate content rows
        self._populate_row(ROW1_LIST, self.row1_items)
        self._populate_row(ROW2_LIST, self.row2_items)
        self._populate_row(ROW3_LIST, self.row3_items)
        self._populate_row(ROW4_LIST, self.row4_items)
        
        # Focus on sidebar
        self.setFocusId(SIDEBAR_LIST)
    
    def _populate_sidebar(self):
        """Populate the sidebar navigation"""
        sidebar = self.getControl(SIDEBAR_LIST)
        sidebar.reset()
        
        for item in self.menu_items:
            li = xbmcgui.ListItem(label=item.get('label', ''))
            # Set actual icon image path
            icon_path = item.get('icon_path', '')
            li.setProperty('icon_path', icon_path)
            li.setProperty('action', item.get('action', ''))
            sidebar.addItem(li)
    
    def _populate_row(self, control_id, items):
        """Populate a content row"""
        try:
            row_list = self.getControl(control_id)
            row_list.reset()
            
            for item in items[:10]:  # Limit to 10 items per row
                li = xbmcgui.ListItem(label=item.get('title', ''))
                backdrop = item.get('backdrop', ADDON_FANART)
                poster = item.get('poster', ADDON_ICON)
                li.setArt({
                    'poster': poster,
                    'thumb': poster,
                    'fanart': backdrop
                })
                
                rating = item.get('rating', 0)
                if rating:
                    li.setProperty('rating', f'{rating:.1f}')
                
                li.setProperty('tmdb_id', str(item.get('id', '')))
                li.setProperty('media_type', item.get('media_type', 'movie'))
                li.setProperty('year', str(item.get('year', '')))
                
                # Progress bar support (max width 175px for portrait tiles)
                progress = item.get('progress', 0)
                if progress and int(progress) > 0:
                    li.setProperty('progress', str(progress))
                    li.setProperty('progress_width', str(int(175 * int(progress) / 100)))
                
                row_list.addItem(li)
        except Exception as e:
            xbmc.log(f"[Orion] Error populating row {control_id}: {e}", xbmc.LOGWARNING)
    
    def onClick(self, controlId):
        """Handle control clicks"""
        xbmc.log(f"[Orion] onClick called with controlId: {controlId}", xbmc.LOGINFO)
        
        if controlId == SIDEBAR_LIST:
            sidebar = self.getControl(SIDEBAR_LIST)
            selected = sidebar.getSelectedItem()
            if selected:
                self.selected_action = selected.getProperty('action')
                xbmc.log(f"[Orion] Sidebar action: {self.selected_action}", xbmc.LOGINFO)
                self.close()
        
        elif controlId == SETTINGS_BTN:
            self.selected_action = 'open_settings'
            self.close()
        
        elif controlId == PLAY_BTN:
            self.selected_action = 'play_hero'
            self.close()
        
        elif controlId in [ROW1_LIST, ROW2_LIST, ROW3_LIST, ROW4_LIST]:
            row_list = self.getControl(controlId)
            selected = row_list.getSelectedItem()
            if selected:
                self.selected_item = {
                    'id': selected.getProperty('tmdb_id'),
                    'media_type': selected.getProperty('media_type'),
                    'title': selected.getLabel(),
                    'year': selected.getProperty('year')
                }
                self.selected_action = 'open_item'
                xbmc.log(f"[Orion] Row item selected for source search: {self.selected_item}", xbmc.LOGINFO)
                self.close()
    
    def onAction(self, action):
        """Handle remote/keyboard actions"""
        action_id = action.getId()
        
        if action_id in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            # Check what's focused - if sidebar is focused on Home, close. Otherwise go to sidebar
            focus_id = self.getFocusId()
            
            if focus_id == SIDEBAR_LIST:
                # If on sidebar, check if Home is selected
                try:
                    sidebar = self.getControl(SIDEBAR_LIST)
                    selected_pos = sidebar.getSelectedPosition()
                    if selected_pos == 0:  # Home is first item
                        # User wants to exit the addon
                        self.selected_action = 'exit'
                        self.close()
                    else:
                        # Navigate back to Home item in sidebar
                        sidebar.selectItem(0)
                except:
                    self.selected_action = 'exit'
                    self.close()
            else:
                # Navigate to sidebar
                self.setFocusId(SIDEBAR_LIST)
        
        elif action_id == ACTION_SELECT_ITEM:
            focus_id = self.getFocusId()
            xbmc.log(f"[Orion] ACTION_SELECT_ITEM on focus_id: {focus_id}", xbmc.LOGINFO)
            self.onClick(focus_id)
    
    def onControl(self, control):
        """Handle control interactions (alternative click handler)"""
        controlId = control.getId()
        xbmc.log(f"[Orion] onControl called with controlId: {controlId}", xbmc.LOGINFO)
        self.onClick(controlId)
    
    def get_result(self):
        """Return the selected action and item"""
        return self.selected_action, self.selected_item


def show_main_menu(menu_items, row1_items=None, row2_items=None, row3_items=None, 
                   row4_items=None, hero_data=None, row_titles=None):
    """
    Show the fullscreen main menu.
    
    Args:
        menu_items: List of sidebar menu items [{label, action, icon_key}]
        row1_items - row4_items: Content for each row [{title, poster, id, media_type, rating}]
        hero_data: Hero section data {title, main, subtitle, backdrop, featured}
        row_titles: Row title labels {row1, row2, row3, row4}
    
    Returns:
        Tuple of (action_string, selected_item_dict or None)
    """
    dialog = MainMenuDialog(
        'MainMenuDialog.xml',
        ADDON_PATH,
        'Default',
        '1080i',
        menu_items=menu_items,
        row1_items=row1_items or [],
        row2_items=row2_items or [],
        row3_items=row3_items or [],
        row4_items=row4_items or [],
        hero_data=hero_data or {},
        row_titles=row_titles or {}
    )
    
    dialog.doModal()
    result = dialog.get_result()
    del dialog
    
    return result
