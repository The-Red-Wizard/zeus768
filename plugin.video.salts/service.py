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
        self.update_interval = 3600  # 1 hour
        
    def onSettingsChanged(self):
        """Called when addon settings are changed"""
        xbmc.log(f'{ADDON_NAME}: Settings changed', xbmc.LOGINFO)


class HoverScrapeMonitor:
    """Monitors the focused list item in SALTS and pre-scrapes after 2s hover.
    
    Works by polling `xbmc.getInfoLabel('Container.FolderPath')` and
    `ListItem.*` info labels to detect what's in focus.
    """
    
    def __init__(self):
        self._last_focused = None
        self._hover_start = 0
        self._hover_threshold = 2.0  # seconds
        self._scraping = set()
        self._max_concurrent = 2
    
    def check(self):
        """Called periodically from the main service loop."""
        try:
            # Only trigger when browsing inside SALTS
            folder = xbmc.getInfoLabel('Container.FolderPath')
            if 'plugin.video.salts' not in folder:
                self._last_focused = None
                return
            
            # Get the currently focused item's label and year
            title = xbmc.getInfoLabel('ListItem.Title')
            year = xbmc.getInfoLabel('ListItem.Year')
            media_type = xbmc.getInfoLabel('ListItem.DBTYPE') or 'movie'
            
            if not title or title.startswith('[B]>>'):
                self._last_focused = None
                return
            
            focus_key = f'{media_type}|{title}|{year}'
            
            if focus_key != self._last_focused:
                self._last_focused = focus_key
                self._hover_start = time.time()
                return
            
            # Check if hovered for threshold duration
            hover_time = time.time() - self._hover_start
            if hover_time < self._hover_threshold:
                return
            
            # Already triggered for this item
            if focus_key in self._scraping:
                return
            
            if len(self._scraping) >= self._max_concurrent:
                return
            
            # Check if already cached
            try:
                from salts_lib.db_utils import DB_Connection
                db = DB_Connection()
                hover_cache_key = f'hover|{focus_key}|||'
                if db.get_hover_cache(hover_cache_key):
                    return
            except Exception:
                return
            
            # Trigger background scrape
            self._scraping.add(focus_key)
            thread = threading.Thread(
                target=self._background_scrape,
                args=(focus_key, title, year, media_type),
                daemon=True
            )
            thread.start()
            
        except Exception:
            pass
    
    def _background_scrape(self, focus_key, title, year, media_type):
        """Run a lightweight scrape in the background"""
        try:
            from salts_lib.db_utils import DB_Connection
            db = DB_Connection()
            
            from scrapers import get_all_scrapers
            from scrapers.freestream_scraper import FreeStreamScraper
            
            debrid_enabled = (
                ADDON.getSetting('realdebrid_enabled') == 'true' or
                ADDON.getSetting('premiumize_enabled') == 'true' or
                ADDON.getSetting('alldebrid_enabled') == 'true' or
                ADDON.getSetting('torbox_enabled') == 'true'
            )
            
            all_sources = []
            scraper_count = 0
            max_scrapers = 4  # The "4-Link Rule"
            
            scrapers = get_all_scrapers()
            for scraper in scrapers:
                if scraper_count >= max_scrapers:
                    break
                try:
                    if not scraper.is_enabled():
                        continue
                    is_free = isinstance(scraper, FreeStreamScraper)
                    if not debrid_enabled and not is_free:
                        continue
                    
                    results = scraper.get_movie_sources(title, year)
                    if results:
                        all_sources.extend(results)
                        scraper_count += 1
                except Exception:
                    continue
            
            if all_sources:
                hover_cache_key = f'hover|{focus_key}|||'
                db.cache_hover(hover_cache_key, all_sources)
                xbmc.log(f'{ADDON_NAME}: Pre-scraped {len(all_sources)} sources for {title} ({year})', xbmc.LOGDEBUG)
        
        except Exception as e:
            xbmc.log(f'{ADDON_NAME}: Pre-scrape error: {e}', xbmc.LOGDEBUG)
        finally:
            self._scraping.discard(focus_key)


def main():
    """Main service loop"""
    monitor = SALTSMonitor()
    hover = HoverScrapeMonitor()
    xbmc.log(f'{ADDON_NAME}: Service started', xbmc.LOGINFO)
    
    while not monitor.abortRequested():
        hover.check()
        if monitor.waitForAbort(1):
            break
    
    xbmc.log(f'{ADDON_NAME}: Service stopped', xbmc.LOGINFO)


if __name__ == '__main__':
    main()
