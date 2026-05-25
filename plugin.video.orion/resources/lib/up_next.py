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


def show_up_next(show_title, next_episode, countdown=5):
    """
    Show Up Next overlay.
    Returns True if user wants to play next episode.
    
    Args:
        show_title: Title of the TV show
        next_episode: Dict with next episode info
        countdown: Countdown duration in seconds (default: 5)
    """
    try:
        # Try to use custom dialog if available, fallback to notification
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
        except Exception as dialog_error:
            xbmc.log(f"[Orion] Custom dialog unavailable, using fallback: {dialog_error}", xbmc.LOGWARNING)
            # Fallback: Simple countdown notification
            return _show_up_next_fallback(show_title, next_episode, countdown)
            
    except Exception as e:
        xbmc.log(f"[Orion] Up Next error: {e}", xbmc.LOGWARNING)
        return False


def _show_up_next_fallback(show_title, next_episode, countdown):
    """
    Fallback up next dialog using simple notification and progress dialog
    """
    import xbmcgui
    
    next_ep_name = next_episode.get('name', 'Next Episode')
    season = next_episode.get('season_number', 0)
    episode = next_episode.get('episode_number', 0)
    
    message = f"S{season:02d}E{episode:02d} - {next_ep_name}"
    
    # Show progress dialog with countdown
    progress = xbmcgui.DialogProgress()
    progress.create(
        f"Up Next on {show_title}",
        f"Playing in {countdown} seconds...\n{message}"
    )
    
    for i in range(countdown):
        if progress.iscanceled():
            progress.close()
            return False
        
        percent = int((i / countdown) * 100)
        remaining = countdown - i
        progress.update(
            percent,
            f"Playing in {remaining} seconds...\n{message}"
        )
        xbmc.sleep(1000)
    
    progress.close()
    return True
