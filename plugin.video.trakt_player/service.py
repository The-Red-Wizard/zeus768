# -*- coding: utf-8 -*-
"""
Trakt Player Background Service
Handles:
- New episode notifications
- Pre-cache monitoring during playback
"""
import xbmc
import xbmcaddon
import time

ADDON_ID = 'plugin.video.trakt_player'


class TraktPlayerService(xbmc.Monitor):
    """Background service for Trakt Player"""
    
    def __init__(self):
        super().__init__()
        self.addon = xbmcaddon.Addon()
        self._last_notification_check = 0
        self._notification_interval = 3600  # Check every hour
        self._precache_monitor = None
        xbmc.log('TraktPlayer Service: Started', xbmc.LOGINFO)
    
    def onSettingsChanged(self):
        """Called when addon settings change"""
        self.addon = xbmcaddon.Addon()
        xbmc.log('TraktPlayer Service: Settings changed', xbmc.LOGDEBUG)
    
    def _check_notifications(self):
        """Check for new episode notifications"""
        try:
            from resources.lib import notifications
            notifications.run_check()
        except Exception as e:
            xbmc.log(f'TraktPlayer Service: Notification check error: {e}', xbmc.LOGERROR)
    
    def _check_precache(self):
        """Check if we need to trigger pre-caching"""
        try:
            from resources.lib import precache
            monitor = precache.get_monitor()
            if monitor:
                monitor.check_and_precache()
        except Exception as e:
            xbmc.log(f'TraktPlayer Service: Pre-cache check error: {e}', xbmc.LOGDEBUG)
    
    def run(self):
        """Main service loop"""
        # Initial delay before first check
        xbmc.sleep(30000)  # 30 seconds
        
        # Do initial notification check
        if self.addon.getSetting('enable_notifications') == 'true':
            self._check_notifications()
            self._last_notification_check = time.time()
        
        while not self.abortRequested():
            # Check every 10 seconds
            if self.waitForAbort(10):
                break
            
            current_time = time.time()
            
            # Check notifications periodically
            if self.addon.getSetting('enable_notifications') == 'true':
                if current_time - self._last_notification_check > self._notification_interval:
                    self._check_notifications()
                    self._last_notification_check = current_time
            
            # Check pre-cache during playback
            if self.addon.getSetting('enable_precache') == 'true':
                self._check_precache()
        
        xbmc.log('TraktPlayer Service: Stopped', xbmc.LOGINFO)


if __name__ == '__main__':
    service = TraktPlayerService()
    service.run()
