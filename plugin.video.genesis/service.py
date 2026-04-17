# -*- coding: utf-8 -*-
"""
Test1 Background Service
Handles Trakt scrobbling during playback.
"""
import xbmc
import xbmcaddon
import time

ADDON_ID = 'plugin.video.genesis'


class Test1Service(xbmc.Monitor):
    """Background service for Test1"""
    
    def __init__(self):
        super().__init__()
        self.addon = xbmcaddon.Addon()
        xbmc.log('Test1 Service: Started', xbmc.LOGINFO)
    
    def onSettingsChanged(self):
        """Called when addon settings change"""
        self.addon = xbmcaddon.Addon()
        xbmc.log('Test1 Service: Settings changed', xbmc.LOGDEBUG)
    
    def run(self):
        """Main service loop"""
        xbmc.sleep(30000)
        
        while not self.abortRequested():
            if self.waitForAbort(10):
                break
        
        xbmc.log('Test1 Service: Stopped', xbmc.LOGINFO)


if __name__ == '__main__':
    service = Test1Service()
    service.run()
