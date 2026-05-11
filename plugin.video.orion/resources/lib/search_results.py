# -*- coding: utf-8 -*-
"""
Orion Netflix-style Search - Custom fullscreen search results dialog
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

# Control IDs
RESULTS_GRID = 9000
NEW_SEARCH_BTN = 9010
MOVIES_BTN = 9011
TV_SHOWS_BTN = 9012
BACK_BTN = 9013


class SearchResultsDialog(xbmcgui.WindowXMLDialog):
    """Netflix-style search results grid dialog."""

    def __init__(self, *args, **kwargs):
        self.results = kwargs.get('results', [])
        self.query = kwargs.get('query', '')
        self.media_type = kwargs.get('media_type', 'multi')
        
        self.selected_action = None
        self.selected_item = None
        self.new_media_type = None
        
        super(SearchResultsDialog, self).__init__(*args)

    def onInit(self):
        """Initialize the dialog with search results"""
        self.setProperty('search_query', self.query)
        self.setProperty('results_count', str(len(self.results)))
        self._populate_results()
        
        xbmc.sleep(50)
        if self.results:
            self.setFocusId(RESULTS_GRID)
        else:
            self.setFocusId(NEW_SEARCH_BTN)

    def _populate_results(self):
        """Fill the grid with search result items"""
        try:
            grid = self.getControl(RESULTS_GRID)
            grid.reset()

            for item in self.results:
                li = xbmcgui.ListItem(label=item.get('title', ''))
                poster = item.get('poster', ADDON_ICON)
                backdrop = item.get('backdrop', ADDON_FANART)
                li.setArt({
                    'poster': backdrop if backdrop and backdrop != ADDON_FANART else poster,
                    'thumb': backdrop if backdrop and backdrop != ADDON_FANART else poster,
                    'fanart': backdrop
                })

                rating = item.get('rating', 0)
                if rating:
                    li.setProperty('rating', f'{rating:.1f}')
                li.setProperty('year', str(item.get('year', '')))
                li.setProperty('tmdb_id', str(item.get('id', '')))
                li.setProperty('media_type', item.get('media_type', 'movie'))
                grid.addItem(li)
        except Exception as e:
            xbmc.log(f"[Orion] Error populating search results: {e}", xbmc.LOGWARNING)

    def onClick(self, controlId):
        xbmc.log(f"[Orion] SearchResults onClick: {controlId}", xbmc.LOGINFO)

        if controlId == RESULTS_GRID:
            try:
                grid = self.getControl(RESULTS_GRID)
                selected = grid.getSelectedItem()
                if selected:
                    self.selected_action = 'select_item'
                    self.selected_item = {
                        'id': selected.getProperty('tmdb_id'),
                        'media_type': selected.getProperty('media_type'),
                        'title': selected.getLabel(),
                        'year': selected.getProperty('year')
                    }
                    self.close()
            except Exception as e:
                xbmc.log(f"[Orion] Grid click error: {e}", xbmc.LOGWARNING)

        elif controlId == NEW_SEARCH_BTN:
            self.selected_action = 'new_search'
            self.close()

        elif controlId == MOVIES_BTN:
            self.selected_action = 'filter'
            self.new_media_type = 'movie'
            self.close()

        elif controlId == TV_SHOWS_BTN:
            self.selected_action = 'filter'
            self.new_media_type = 'tv'
            self.close()

        elif controlId == BACK_BTN:
            self.selected_action = 'back'
            self.close()

    def onAction(self, action):
        action_id = action.getId()
        if action_id in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            self.selected_action = 'back'
            self.close()
        elif action_id == ACTION_SELECT_ITEM:
            self.onClick(self.getFocusId())

    def get_result(self):
        return self.selected_action, self.selected_item, self.new_media_type


def show_search_results(results, query, media_type='multi'):
    """
    Show Netflix-style search results dialog.

    Returns:
        Tuple of (action, selected_item, new_media_type)
    """
    dialog = SearchResultsDialog(
        'SearchResultsDialog.xml',
        ADDON_PATH,
        'Default',
        '1080i',
        results=results,
        query=query,
        media_type=media_type
    )

    dialog.doModal()
    result = dialog.get_result()
    del dialog
    return result
