# -*- coding: utf-8 -*-
"""
Orion Netflix-style Settings Dialog
"""

import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')

ACTION_SELECT_ITEM = 7
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

CATEGORY_LIST = 100
SETTINGS_LIST = 200
SAVE_BTN = 300
CLOSE_BTN = 301

# Settings structure - matches settings.xml IDs
SETTINGS_CATEGORIES = [
    {
        'name': 'Appearance',
        'items': [
            {'id': 'netflix_skin_enabled', 'label': 'Netflix-Style Skin', 'desc': 'Enable/disable the Netflix-style skin for all views', 'type': 'bool'},
            {'id': 'use_custom_skin', 'label': 'Fullscreen Link Picker', 'desc': 'Use fullscreen overlay for source picker', 'type': 'bool'},
            {'id': 'use_custom_menu', 'label': 'Sidebar Main Menu', 'desc': 'Use sidebar-style main menu', 'type': 'bool'},
            {'id': 'use_netflix_submenu', 'label': 'Netflix Submenus', 'desc': 'Use Netflix-style for Movies/TV/Kids/Trakt', 'type': 'bool'},
            {'id': 'use_netflix_search', 'label': 'Netflix Search', 'desc': 'Use Netflix-style search results grid', 'type': 'bool'},
        ]
    },
    {
        'name': 'Accounts',
        'items': [
            {'id': 'tmdb_api_key', 'label': 'TMDB API Key', 'desc': 'API key for The Movie Database', 'type': 'text'},
            {'id': 'trakt_client_id', 'label': 'Trakt Client ID', 'desc': 'Your Trakt API client ID', 'type': 'text'},
            {'id': 'trakt_client_secret', 'label': 'Trakt Client Secret', 'desc': 'Your Trakt API client secret', 'type': 'text'},
        ]
    },
    {
        'name': 'Debrid Services',
        'items': [
            {'id': 'realdebrid_enabled', 'label': 'Real-Debrid', 'desc': 'Enable Real-Debrid premium links', 'type': 'bool'},
            {'id': 'realdebrid_token', 'label': 'Real-Debrid API Token', 'desc': 'Your Real-Debrid API token', 'type': 'text'},
            {'id': 'premiumize_enabled', 'label': 'Premiumize', 'desc': 'Enable Premiumize premium links', 'type': 'bool'},
            {'id': 'premiumize_token', 'label': 'Premiumize API Token', 'desc': 'Your Premiumize API token', 'type': 'text'},
            {'id': 'alldebrid_enabled', 'label': 'AllDebrid', 'desc': 'Enable AllDebrid premium links', 'type': 'bool'},
            {'id': 'alldebrid_token', 'label': 'AllDebrid API Token', 'desc': 'Your AllDebrid API token', 'type': 'text'},
            {'id': 'torbox_enabled', 'label': 'TorBox', 'desc': 'Enable TorBox debrid service', 'type': 'bool'},
            {'id': 'torbox_token', 'label': 'TorBox API Token', 'desc': 'Your TorBox API token', 'type': 'text'},
        ]
    },
    {
        'name': 'Scrapers',
        'items': [
            {'id': 'scraper_1337x', 'label': '1337x', 'desc': 'Enable 1337x torrent scraper', 'type': 'bool'},
            {'id': 'scraper_yts', 'label': 'YTS', 'desc': 'Enable YTS torrent scraper', 'type': 'bool'},
            {'id': 'scraper_eztv', 'label': 'EZTV', 'desc': 'Enable EZTV torrent scraper', 'type': 'bool'},
            {'id': 'scraper_torrentgalaxy', 'label': 'TorrentGalaxy', 'desc': 'Enable TorrentGalaxy scraper', 'type': 'bool'},
            {'id': 'scraper_piratebay', 'label': 'The Pirate Bay', 'desc': 'Enable The Pirate Bay scraper', 'type': 'bool'},
            {'id': 'scraper_nyaa', 'label': 'Nyaa', 'desc': 'Enable Nyaa anime scraper', 'type': 'bool'},
        ]
    },
    {
        'name': 'Playback',
        'items': [
            {'id': 'preferred_quality', 'label': 'Preferred Quality', 'desc': 'Default quality filter for sources', 'type': 'select', 'options': ['All', '4K', '1080p', '720p']},
            {'id': 'auto_play', 'label': 'Auto-Play Best Source', 'desc': 'Automatically play the best available source', 'type': 'bool'},
            {'id': 'auto_next_episode', 'label': 'Up Next Auto-Play', 'desc': 'Show Up Next overlay and auto-play next episode', 'type': 'bool'},
            {'id': 'source_timeout', 'label': 'Source Timeout (seconds)', 'desc': 'Maximum time to search for sources', 'type': 'text'},
        ]
    },
    {
        'name': 'Advanced',
        'items': [
            {'id': 'clear_cache', 'label': 'Clear Cache', 'desc': 'Clear all cached data', 'type': 'action'},
            {'id': 'clear_history', 'label': 'Clear Watch History', 'desc': 'Remove all watch history', 'type': 'action'},
            {'id': 'clear_favorites', 'label': 'Clear All Favorites', 'desc': 'Remove all favorite items', 'type': 'action'},
        ]
    },
]


class SettingsDialog(xbmcgui.WindowXMLDialog):
    """Netflix-style settings dialog"""

    def __init__(self, *args, **kwargs):
        self.current_category = 0
        self.changed_settings = {}
        super(SettingsDialog, self).__init__(*args)

    def onInit(self):
        self._populate_categories()
        self._populate_settings(0)
        xbmc.sleep(50)
        self.setFocusId(CATEGORY_LIST)

    def _populate_categories(self):
        try:
            cat_list = self.getControl(CATEGORY_LIST)
            cat_list.reset()
            for cat in SETTINGS_CATEGORIES:
                li = xbmcgui.ListItem(label=cat['name'])
                cat_list.addItem(li)
        except Exception as e:
            xbmc.log(f"[Orion] Settings categories error: {e}", xbmc.LOGWARNING)

    def _populate_settings(self, cat_index):
        try:
            settings_list = self.getControl(SETTINGS_LIST)
            settings_list.reset()
            self.current_category = cat_index

            if cat_index >= len(SETTINGS_CATEGORIES):
                return

            category = SETTINGS_CATEGORIES[cat_index]
            for setting in category['items']:
                sid = setting['id']
                stype = setting['type']
                label = setting['label']
                desc = setting.get('desc', '')

                li = xbmcgui.ListItem(label=label, label2=desc)

                # Get current value
                if stype == 'bool':
                    val = ADDON.getSetting(sid)
                    display_val = 'ON' if val == 'true' else 'OFF'
                elif stype == 'text':
                    val = ADDON.getSetting(sid)
                    if 'token' in sid.lower() or 'secret' in sid.lower() or 'key' in sid.lower():
                        display_val = '****' + val[-4:] if len(val) > 4 else ('Set' if val else 'Not Set')
                    else:
                        display_val = val if val else 'Not Set'
                elif stype == 'select':
                    val = ADDON.getSetting(sid)
                    display_val = val if val else setting.get('options', [''])[0]
                elif stype == 'action':
                    display_val = '>'
                else:
                    display_val = ''

                li.setProperty('value', display_val)
                li.setProperty('setting_id', sid)
                li.setProperty('setting_type', stype)
                settings_list.addItem(li)
        except Exception as e:
            xbmc.log(f"[Orion] Settings populate error: {e}", xbmc.LOGWARNING)

    def onClick(self, controlId):
        if controlId == CATEGORY_LIST:
            try:
                cat_list = self.getControl(CATEGORY_LIST)
                idx = cat_list.getSelectedPosition()
                self._populate_settings(idx)
                self.setFocusId(SETTINGS_LIST)
            except:
                pass

        elif controlId == SETTINGS_LIST:
            self._handle_setting_click()

        elif controlId == SAVE_BTN:
            self._save_settings()
            xbmcgui.Dialog().notification('Orion', 'Settings saved', ADDON.getAddonInfo('icon'))
            self.close()

        elif controlId == CLOSE_BTN:
            self.close()

    def _handle_setting_click(self):
        try:
            settings_list = self.getControl(SETTINGS_LIST)
            selected = settings_list.getSelectedItem()
            if not selected:
                return

            sid = selected.getProperty('setting_id')
            stype = selected.getProperty('setting_type')

            if stype == 'bool':
                current = ADDON.getSetting(sid)
                new_val = 'false' if current == 'true' else 'true'
                ADDON.setSetting(sid, new_val)
                self.changed_settings[sid] = new_val
                selected.setProperty('value', 'ON' if new_val == 'true' else 'OFF')

            elif stype == 'text':
                current = ADDON.getSetting(sid)
                keyboard = xbmc.Keyboard(current, selected.getLabel())
                keyboard.doModal()
                if keyboard.isConfirmed():
                    new_val = keyboard.getText()
                    ADDON.setSetting(sid, new_val)
                    self.changed_settings[sid] = new_val
                    if 'token' in sid.lower() or 'secret' in sid.lower() or 'key' in sid.lower():
                        display = '****' + new_val[-4:] if len(new_val) > 4 else ('Set' if new_val else 'Not Set')
                    else:
                        display = new_val if new_val else 'Not Set'
                    selected.setProperty('value', display)

            elif stype == 'select':
                cat = SETTINGS_CATEGORIES[self.current_category]
                setting_def = None
                for s in cat['items']:
                    if s['id'] == sid:
                        setting_def = s
                        break
                if setting_def and 'options' in setting_def:
                    options = setting_def['options']
                    choice = xbmcgui.Dialog().select(selected.getLabel(), options)
                    if choice >= 0:
                        ADDON.setSetting(sid, options[choice])
                        self.changed_settings[sid] = options[choice]
                        selected.setProperty('value', options[choice])

            elif stype == 'action':
                confirm = xbmcgui.Dialog().yesno('Orion', f'Are you sure you want to {selected.getLabel().lower()}?')
                if confirm:
                    ADDON.setSetting(sid, 'true')
                    xbmcgui.Dialog().notification('Orion', f'{selected.getLabel()} completed', ADDON.getAddonInfo('icon'))

        except Exception as e:
            xbmc.log(f"[Orion] Setting click error: {e}", xbmc.LOGWARNING)

    def _save_settings(self):
        # Settings are saved immediately on change via ADDON.setSetting
        pass

    def onAction(self, action):
        action_id = action.getId()
        if action_id in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            focus_id = self.getFocusId()
            if focus_id == SETTINGS_LIST:
                self.setFocusId(CATEGORY_LIST)
            else:
                self.close()
        elif action_id == ACTION_SELECT_ITEM:
            self.onClick(self.getFocusId())


def show_settings():
    """Show Netflix-style settings dialog"""
    dialog = SettingsDialog(
        'SettingsDialog.xml',
        ADDON_PATH,
        'Default',
        '1080i'
    )
    dialog.doModal()
    del dialog
