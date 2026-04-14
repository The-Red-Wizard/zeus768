# -*- coding: utf-8 -*-
"""
Orion v3.5.0 - Episode Dialog Handler
Netflix-style episode grid with BIG thumbnails
"""

import os
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')

# Control IDs from EpisodeDialog.xml
CONTROL_EPISODES_PANEL = 500
CONTROL_BACK_BUTTON = 50
CONTROL_PREV_SEASON = 151
CONTROL_NEXT_SEASON = 152
CONTROL_PREV_PAGE = 600
CONTROL_NEXT_PAGE = 700

# Window properties
PROP_SHOW_TITLE = 'show_title'
PROP_SHOW_BACKDROP = 'show_backdrop'
PROP_SEASON_NUMBER = 'season_number'
PROP_EPISODE_COUNT = 'episode_count'
PROP_TOTAL_SEASONS = 'total_seasons'
PROP_CURRENT_PAGE = 'current_page'
PROP_TOTAL_PAGES = 'total_pages'

# Items per page (5 columns x 3 rows)
ITEMS_PER_PAGE = 15


class EpisodeDialog(xbmcgui.WindowXMLDialog):
    """Netflix-style episode grid dialog"""
    
    def __init__(self, *args, **kwargs):
        self.show_data = kwargs.get('show_data', {})
        self.episodes = kwargs.get('episodes', [])
        self.season_number = kwargs.get('season_number', 1)
        self.total_seasons = kwargs.get('total_seasons', 1)
        self.selected_episode = None
        self.callback = kwargs.get('callback', None)
        self.season_change_callback = kwargs.get('season_change_callback', None)
        
        self.current_page = 1
        self.total_pages = max(1, (len(self.episodes) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        
        xbmcgui.WindowXMLDialog.__init__(self, *args)
    
    def onInit(self):
        """Initialize dialog with episode data"""
        # Set show info
        self.setProperty(PROP_SHOW_TITLE, self.show_data.get('title', ''))
        self.setProperty(PROP_SHOW_BACKDROP, self.show_data.get('backdrop', ''))
        self.setProperty(PROP_SEASON_NUMBER, str(self.season_number))
        self.setProperty(PROP_EPISODE_COUNT, str(len(self.episodes)))
        self.setProperty(PROP_TOTAL_SEASONS, str(self.total_seasons))
        
        # Load first page
        self._load_page(1)
    
    def _load_page(self, page_num):
        """Load a page of episodes"""
        self.current_page = page_num
        self.setProperty(PROP_CURRENT_PAGE, str(self.current_page))
        self.setProperty(PROP_TOTAL_PAGES, str(self.total_pages))
        
        try:
            episode_panel = self.getControl(CONTROL_EPISODES_PANEL)
            episode_panel.reset()
            
            # Calculate slice indices
            start_idx = (page_num - 1) * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, len(self.episodes))
            
            page_episodes = self.episodes[start_idx:end_idx]
            
            for ep in page_episodes:
                ep_num = ep.get('episode_number', 0)
                ep_name = ep.get('name', f'Episode {ep_num}')
                still = ep.get('still_path', '')
                air_date = ep.get('air_date', '')
                runtime = ep.get('runtime', 0)
                progress = ep.get('progress', 0)  # Watch progress percentage (0-100)
                watched = ep.get('watched', False)  # Fully watched flag
                
                # Format runtime
                runtime_str = ''
                if runtime:
                    runtime_str = f'{runtime}m'
                
                # Calculate progress bar width (max 360px for focused, 364px for unfocused)
                progress_width = ''
                if progress > 0:
                    progress_width = str(int(360 * progress / 100))
                
                li = xbmcgui.ListItem(label=ep_name)
                li.setArt({
                    'thumb': still,
                    'icon': still,
                    'fanart': still
                })
                li.setProperty('episode_num', str(ep_num))
                li.setProperty('air_date', air_date)
                li.setProperty('runtime', runtime_str)
                li.setProperty('plot', ep.get('overview', ''))
                
                # Progress properties
                if progress > 0:
                    li.setProperty('progress', str(progress))
                    li.setProperty('progress_width', progress_width)
                if watched:
                    li.setProperty('watched', 'true')
                
                episode_panel.addItem(li)
                
        except Exception as e:
            xbmc.log(f'[Orion] Error loading episodes page: {e}', xbmc.LOGERROR)
    
    def onClick(self, controlId):
        """Handle click events"""
        if controlId == CONTROL_EPISODES_PANEL:
            # Episode selected
            episode_panel = self.getControl(CONTROL_EPISODES_PANEL)
            selected_item = episode_panel.getSelectedItem()
            if selected_item:
                self.selected_episode = int(selected_item.getProperty('episode_num'))
                self.close()
                if self.callback:
                    self.callback(self.season_number, self.selected_episode)
        
        elif controlId == CONTROL_BACK_BUTTON:
            self.close()
        
        elif controlId == CONTROL_PREV_PAGE:
            if self.current_page > 1:
                self._load_page(self.current_page - 1)
        
        elif controlId == CONTROL_NEXT_PAGE:
            if self.current_page < self.total_pages:
                self._load_page(self.current_page + 1)
        
        elif controlId == CONTROL_PREV_SEASON:
            if self.season_number > 1 and self.season_change_callback:
                self.close()
                self.season_change_callback(self.season_number - 1)
        
        elif controlId == CONTROL_NEXT_SEASON:
            if self.season_number < self.total_seasons and self.season_change_callback:
                self.close()
                self.season_change_callback(self.season_number + 1)
    
    def onAction(self, action):
        """Handle navigation actions"""
        action_id = action.getId()
        
        # Back/Previous menu
        if action_id in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            self.close()
        
        # Select
        elif action_id == xbmcgui.ACTION_SELECT_ITEM:
            focused_id = self.getFocusId()
            if focused_id == CONTROL_EPISODES_PANEL:
                self.onClick(CONTROL_EPISODES_PANEL)


def show_episode_dialog(show_data, episodes, season_number, total_seasons=1, 
                        callback=None, season_change_callback=None):
    """
    Show the Netflix-style episode grid dialog
    
    Args:
        show_data: dict with keys: title, backdrop
        episodes: list of dicts with keys: episode_number, name, still_path, 
                 air_date, runtime, overview
        season_number: current season number
        total_seasons: total number of seasons
        callback: function to call with (season, episode) when episode selected
        season_change_callback: function to call with new season number
    
    Returns:
        Tuple of (season_number, episode_number) or None if cancelled
    """
    skin_path = os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', '1080i')
    
    dialog = EpisodeDialog(
        'EpisodeDialog.xml',
        skin_path,
        'default',
        '1080i',
        show_data=show_data,
        episodes=episodes,
        season_number=season_number,
        total_seasons=total_seasons,
        callback=callback,
        season_change_callback=season_change_callback
    )
    dialog.doModal()
    
    selected_ep = dialog.selected_episode
    del dialog
    
    if selected_ep:
        return (season_number, selected_ep)
    return None
