"""
SALTS Service - Background service for scheduled tasks
Revived by zeus768 for Kodi 21+
"""
import xbmc
import xbmcaddon
import time

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')

class SALTSMonitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.update_interval = 3600  # 1 hour
        
    def onSettingsChanged(self):
        """Called when addon settings are changed"""
        xbmc.log(f'{ADDON_NAME}: Settings changed', xbmc.LOGINFO)

def main():
    """Main service loop"""
    monitor = SALTSMonitor()
    xbmc.log(f'{ADDON_NAME}: Service started', xbmc.LOGINFO)
    
    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break
    
    xbmc.log(f'{ADDON_NAME}: Service stopped', xbmc.LOGINFO)

if __name__ == '__main__':
    main()
