"""
SALTS Service - Background service for scheduled tasks
Revived by zeus768 for Kodi 21+
"""
import xbmc
import xbmcaddon
import xbmcgui
import json
import time
import threading

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')


class SALTSMonitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.update_interval = 3600

    def onSettingsChanged(self):
        xbmc.log(f'{ADDON_NAME}: Settings changed', xbmc.LOGINFO)


class HoverScrapeMonitor:
    """Monitors the focused list item in SALTS and pre-scrapes after 2s hover."""

    def __init__(self):
        self.last_focused = None
        self.hover_start = 0
        self.hover_threshold = 2.0
        self.scrape_cache = {}
        self.enabled = ADDON.getSetting('preemptive_scrape') == 'true'
        self.running = False

    def start(self):
        if not self.enabled:
            return
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        xbmc.log(f'{ADDON_NAME}: Hover scrape monitor started', xbmc.LOGINFO)

    def stop(self):
        self.running = False

    def _monitor_loop(self):
        while self.running:
            try:
                folder = xbmc.getInfoLabel('Container.FolderPath')
                if 'plugin.video.salts' not in folder:
                    xbmc.sleep(2000)
                    continue
                label = xbmc.getInfoLabel('ListItem.Label')
                dbid = xbmc.getInfoLabel('ListItem.DBID')
                current_id = f'{label}_{dbid}'
                if current_id != self.last_focused:
                    self.last_focused = current_id
                    self.hover_start = time.time()
                elif current_id and (time.time() - self.hover_start) >= self.hover_threshold:
                    if current_id not in self.scrape_cache:
                        self._prescrape(label, dbid)
                        self.scrape_cache[current_id] = True
                        self.hover_start = time.time() + 9999
            except:
                pass
            xbmc.sleep(500)

    def _prescrape(self, title, dbid):
        try:
            xbmc.log(f'{ADDON_NAME}: Pre-scraping: {title}', xbmc.LOGDEBUG)
        except:
            pass


def run_service():
    monitor = SALTSMonitor()
    hover_monitor = HoverScrapeMonitor()
    xbmc.log(f'{ADDON_NAME}: Service started', xbmc.LOGINFO)
    hover_monitor.start()

    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break

    hover_monitor.stop()
    xbmc.log(f'{ADDON_NAME}: Service stopped', xbmc.LOGINFO)


if __name__ == '__main__':
    run_service()
