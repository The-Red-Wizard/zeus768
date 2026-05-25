# -*- coding: utf-8 -*-
"""
Orion Intro Skipper - Skip intro button overlay
"""

import xbmc
import xbmcgui
import xbmcaddon
import threading

ADDON = xbmcaddon.Addon()
ADDON_ICON = ADDON.getAddonInfo('icon')

ACTION_SELECT_ITEM = 7
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


class SkipIntroDialog(xbmcgui.WindowDialog):
    """Simple skip intro button overlay"""
    
    def __init__(self, player, intro_end_time):
        super(SkipIntroDialog, self).__init__()
        self.player = player
        self.intro_end_time = intro_end_time
        self.visible_duration = 10  # Show button for 10 seconds
        self._setup_ui()
        self._start_timer()
    
    def _setup_ui(self):
        """Setup UI elements"""
        # Position button in bottom right corner
        x = 1600  # Right side
        y = 900   # Bottom
        width = 250
        height = 60
        
        # Background
        self.background = xbmcgui.ControlButton(
            x, y, width, height,
            '[B]Skip Intro[/B]',
            focusTexture='',
            noFocusTexture='',
            alignment=6
        )
        
        try:
            self.addControl(self.background)
            self.setFocus(self.background)
        except:
            pass
    
    def _start_timer(self):
        """Auto-hide button after duration"""
        def _hide():
            xbmc.sleep(self.visible_duration * 1000)
            try:
                self.close()
            except:
                pass
        
        timer_thread = threading.Thread(target=_hide)
        timer_thread.daemon = True
        timer_thread.start()
    
    def onClick(self, controlId):
        """Handle button click"""
        if self.player.isPlaying():
            self.player.seekTime(self.intro_end_time)
            xbmcgui.Dialog().notification('Orion', 'Intro skipped', ADDON_ICON, 2000)
        self.close()
    
    def onAction(self, action):
        """Handle actions"""
        action_id = action.getId()
        
        # Close on back/escape
        if action_id in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            self.close()
        # Skip on select
        elif action_id == ACTION_SELECT_ITEM:
            if self.player.isPlaying():
                self.player.seekTime(self.intro_end_time)
                xbmcgui.Dialog().notification('Orion', 'Intro skipped', ADDON_ICON, 2000)
            self.close()


def show_skip_intro_dialog(player, intro_end_time):
    """
    Show skip intro button overlay.
    Uses threading to not block playback.
    """
    try:
        # Use notification instead of full dialog to avoid blocking playback
        # Create a simple button notification
        xbmc.executebuiltin(f'Notification(Orion, Press OK to Skip Intro, 5000, {ADDON_ICON})')
        
        # Alternative: Can implement custom window with skip button
        # For simplicity using notification for now
        
    except Exception as e:
        xbmc.log(f"[Orion Intro Skip] Error showing dialog: {e}", xbmc.LOGWARNING)


def show_skip_intro_button_simple(player, intro_end_time):
    """
    Show simple skip intro notification with action
    """
    # Monitor for user input during intro period
    monitor = xbmc.Monitor()
    start_time = player.getTime()
    
    # Show notification
    xbmcgui.Dialog().notification(
        'Orion', 
        'Press "I" to skip intro', 
        ADDON_ICON, 
        5000
    )
    
    # Could implement keyboard listener here for 'I' key
    # For now, rely on user seeking manually after notification
