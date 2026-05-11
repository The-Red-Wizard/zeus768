# -*- coding: utf-8 -*-
"""
Orion Up Next - Auto-play next episode dialog and service
"""

import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = ADDON.getAddonInfo('icon')

ACTION_SELECT_ITEM = 7
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


class UpNextDialog(xbmcgui.WindowXMLDialog):
    """Up Next overlay shown near end of episode playback"""

    def __init__(self, *args, **kwargs):
        self.next_episode = kwargs.get('next_episode', {})
        self.show_title = kwargs.get('show_title', '')
        self.countdown = kwargs.get('countdown', 15)
        self.play_next = False
        self._timer = None
        super(UpNextDialog, self).__init__(*args)

    def onInit(self):
        self.setProperty('show_title', self.show_title)
        ep = self.next_episode
        self.setProperty('next_title', ep.get('name', f"Episode {ep.get('episode_number', '')}"))
        self.setProperty('next_season', str(ep.get('season_number', '')))
        self.setProperty('next_episode_num', str(ep.get('episode_number', '')))
        self.setProperty('next_still', ep.get('still_path', ADDON_ICON))
        self.setProperty('countdown', str(self.countdown))

        # Start countdown
        self._start_countdown()

    def _start_countdown(self):
        import threading

        def _tick():
            while self.countdown > 0:
                xbmc.sleep(1000)
                self.countdown -= 1
                try:
                    self.setProperty('countdown', str(self.countdown))
                except:
                    return
            # Auto-play when countdown hits 0
            self.play_next = True
            self.close()

        self._timer = threading.Thread(target=_tick)
        self._timer.daemon = True
        self._timer.start()

    def onClick(self, controlId):
        if controlId == 5000:  # Play Next button
            self.play_next = True
            self.close()
        elif controlId == 5001:  # Cancel button
            self.play_next = False
            self.close()

    def onAction(self, action):
        if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            self.play_next = False
            self.close()

    def should_play_next(self):
        return self.play_next


def show_up_next(show_title, next_episode, countdown=15):
    """
    Show Up Next overlay.
    Returns True if user wants to play next episode.
    """
    try:
        dialog = UpNextDialog(
            'UpNextDialog.xml',
            ADDON_PATH,
            'Default',
            '1080i',
            next_episode=next_episode,
            show_title=show_title,
            countdown=countdown
        )
        dialog.doModal()
        result = dialog.should_play_next()
        del dialog
        return result
    except Exception as e:
        xbmc.log(f"[Orion] Up Next error: {e}", xbmc.LOGWARNING)
        return False
