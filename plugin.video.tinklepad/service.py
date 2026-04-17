"""
Tinklepad Service
Background service for token refresh and startup tasks
"""
import xbmc
import xbmcaddon
import time

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

class TinklepadService(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.refresh_interval = 3600 * 6  # Refresh tokens every 6 hours
        
    def run(self):
        xbmc.log(f'[{ADDON_ID}] Service started', xbmc.LOGINFO)
        
        # Initial delay
        self.waitForAbort(10)
        
        while not self.abortRequested():
            try:
                self.check_tokens()
            except Exception as e:
                xbmc.log(f'[{ADDON_ID}] Service error: {e}', xbmc.LOGERROR)
            
            # Wait for next check or abort
            if self.waitForAbort(self.refresh_interval):
                break
        
        xbmc.log(f'[{ADDON_ID}] Service stopped', xbmc.LOGINFO)
    
    def check_tokens(self):
        """Check and refresh debrid tokens if needed"""
        from resources.lib.debrid import debrid_manager
        
        # Check Real-Debrid token expiry
        rd_expiry = ADDON.getSetting('rd.expiry')
        if rd_expiry:
            try:
                expiry_time = int(rd_expiry)
                # Refresh if expires within 1 hour
                if expiry_time - time.time() < 3600:
                    xbmc.log(f'[{ADDON_ID}] Refreshing Real-Debrid token', xbmc.LOGINFO)
                    debrid_manager.rd_refresh_token()
            except:
                pass

if __name__ == '__main__':
    service = TinklepadService()
    service.run()
