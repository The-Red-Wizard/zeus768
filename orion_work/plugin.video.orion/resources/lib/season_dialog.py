# -*- coding: utf-8 -*-
"""
Orion v3.5.0 - Season Dialog Handler
Netflix-style season selector for TV shows
"""

import os
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')

# Control IDs from SeasonDialog.xml
CONTROL_SEASONS_LIST = 500
CONTROL_BACK_BUTTON = 50

# Window property IDs
PROP_SHOW_TITLE = 'show_title'
PROP_SHOW_BACKDROP = 'show_backdrop'
PROP_SHOW_META = 'show_meta'
PROP_SHOW_PLOT = 'show_plot'
PROP_TOTAL_EPISODES = 'total_episodes'
PROP_SEASON_COUNT = 'season_count'


class SeasonDialog(xbmcgui.WindowXMLDialog):
    """Netflix-style season selector dialog"""
    
    def __init__(self, *args, **kwargs):
        self.show_data = kwargs.get('show_data', {})
        self.seasons = kwargs.get('seasons', [])
        self.selected_season = None
        self.callback = kwargs.get('callback', None)
        xbmcgui.WindowXMLDialog.__init__(self, *args)
    
    def onInit(self):
        """Initialize dialog with show data"""
        # Set show info
        self.setProperty(PROP_SHOW_TITLE, self.show_data.get('title', ''))
        self.setProperty(PROP_SHOW_BACKDROP, self.show_data.get('backdrop', ''))
        self.setProperty(PROP_SHOW_PLOT, self.show_data.get('overview', ''))
        
        # Build meta string: Year • Rating • Seasons • Genre
        meta_parts = []
        if self.show_data.get('year'):
            meta_parts.append(self.show_data['year'])
        if self.show_data.get('rating'):
            meta_parts.append(f"★ {self.show_data['rating']:.1f}")
        if len(self.seasons) > 0:
            meta_parts.append(f"{len(self.seasons)} Seasons")
        if self.show_data.get('genres'):
            meta_parts.append(self.show_data['genres'])
        self.setProperty(PROP_SHOW_META, ' • '.join(meta_parts))
        
        # Count total episodes
        total_eps = sum(s.get('episode_count', 0) for s in self.seasons)
        self.setProperty(PROP_TOTAL_EPISODES, str(total_eps))
        self.setProperty(PROP_SEASON_COUNT, str(len(self.seasons)))
        
        # Populate seasons list
        self._populate_seasons()
    
    def _populate_seasons(self):
        """Populate the seasons list control"""
        try:
            season_list = self.getControl(CONTROL_SEASONS_LIST)
            season_list.reset()
            
            for season in self.seasons:
                season_num = season.get('season_number', 0)
                name = season.get('name', f'Season {season_num}')
                poster = season.get('poster', '')
                episode_count = season.get('episode_count', 0)
                
                li = xbmcgui.ListItem(label=name)
                li.setArt({
                    'poster': poster,
                    'thumb': poster,
                    'icon': poster
                })
                li.setProperty('season_number', str(season_num))
                li.setProperty('episode_count', str(episode_count))
                
                season_list.addItem(li)
                
        except Exception as e:
            xbmc.log(f'[Orion] Error populating seasons: {e}', xbmc.LOGERROR)
    
    def onClick(self, controlId):
        """Handle click events"""
        if controlId == CONTROL_SEASONS_LIST:
            # Season selected
            season_list = self.getControl(CONTROL_SEASONS_LIST)
            selected_item = season_list.getSelectedItem()
            if selected_item:
                self.selected_season = int(selected_item.getProperty('season_number'))
                self.close()
                if self.callback:
                    self.callback(self.selected_season)
        
        elif controlId == CONTROL_BACK_BUTTON:
            self.close()
    
    def onAction(self, action):
        """Handle navigation actions"""
        action_id = action.getId()
        
        # Back/Previous menu
        if action_id in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            self.close()
        
        # Select
        elif action_id == xbmcgui.ACTION_SELECT_ITEM:
            focused_id = self.getFocusId()
            if focused_id == CONTROL_SEASONS_LIST:
                self.onClick(CONTROL_SEASONS_LIST)


def show_season_dialog(show_data, seasons, callback=None):
    """
    Show the Netflix-style season selector dialog
    
    Args:
        show_data: dict with keys: title, backdrop, overview, year, rating, genres
        seasons: list of dicts with keys: season_number, name, poster, episode_count
        callback: function to call with selected season number
    
    Returns:
        Selected season number or None if cancelled
    """
    skin_path = os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', '1080i')
    
    dialog = SeasonDialog(
        'SeasonDialog.xml',
        skin_path,
        'default',
        '1080i',
        show_data=show_data,
        seasons=seasons,
        callback=callback
    )
    dialog.doModal()
    
    selected = dialog.selected_season
    del dialog
    return selected
