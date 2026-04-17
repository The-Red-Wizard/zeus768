# -*- coding: utf-8 -*-
"""
Genesis Background Service
Handles Trakt scrobbling during playback.
"""
import xbmc
import xbmcaddon
import time

ADDON_ID = 'plugin.video.genesis'


class GenesisService(xbmc.Monitor):
    """Background service for Genesis"""
    
    def __init__(self):
        super().__init__()
        self.addon = xbmcaddon.Addon()
        xbmc.log('Genesis Service: Started', xbmc.LOGINFO)
    
    def onSettingsChanged(self):
        """Called when addon settings change"""
        self.addon = xbmcaddon.Addon()
        xbmc.log('Genesis Service: Settings changed', xbmc.LOGDEBUG)
    
    def run(self):
        """Main service loop"""
        xbmc.sleep(30000)
        
        while not self.abortRequested():
            if self.waitForAbort(10):
                break
        
        xbmc.log('Genesis Service: Stopped', xbmc.LOGINFO)


if __name__ == '__main__':
    service = GenesisService()
    service.run()
