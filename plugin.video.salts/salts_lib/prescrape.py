"""
SALTS Library - Pre-Scrape Manager
Background scraping with hover detection and 24hr TTL cache.
"""
import threading
import time
import xbmc
import xbmcaddon
from . import log_utils
from .db_utils import DB_Connection

ADDON = xbmcaddon.Addon()


class PreScrapeManager:
    """Manages background pre-scraping of titles on hover.
    
    Usage: call `on_focus(cache_key, title, year, ...)` when a list item
    receives focus. After `hover_ms` milliseconds, a background scrape fires
    if the user is still on the same item. Results are stored in the
    hover_cache table (24hr TTL).
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.db = DB_Connection()
        self.hover_ms = 2000  # 2 second hover threshold
        self._current_key = None
        self._timer = None
        self._scraping = set()  # keys currently being scraped
        self._max_concurrent = 2
    
    def on_focus(self, cache_key, title, year='', media_type='movie',
                 season='', episode='', tmdb_id=''):
        """Called when a list item receives focus.
        Starts a 2s timer; if still focused after 2s, triggers background scrape.
        """
        self._current_key = cache_key
        
        # Cancel any pending timer
        if self._timer:
            self._timer.cancel()
        
        # Check if already cached
        cached = self.db.get_hover_cache(cache_key)
        if cached:
            return  # Already have results
        
        # Check if already scraping
        if cache_key in self._scraping:
            return
        
        # Too many concurrent scrapes
        if len(self._scraping) >= self._max_concurrent:
            return
        
        # Start timer
        self._timer = threading.Timer(
            self.hover_ms / 1000.0,
            self._start_scrape,
            args=(cache_key, title, year, media_type, season, episode, tmdb_id)
        )
        self._timer.daemon = True
        self._timer.start()
    
    def _start_scrape(self, cache_key, title, year, media_type, season, episode, tmdb_id):
        """Actually launch the background scrape"""
        # Verify user is still on the same item
        if self._current_key != cache_key:
            return
        
        if cache_key in self._scraping:
            return
        
        self._scraping.add(cache_key)
        
        thread = threading.Thread(
            target=self._do_scrape,
            args=(cache_key, title, year, media_type, season, episode, tmdb_id),
            daemon=True
        )
        thread.start()
    
    def _do_scrape(self, cache_key, title, year, media_type, season, episode, tmdb_id):
        """Background scrape worker"""
        try:
            from scrapers import get_all_scrapers
            from scrapers.freestream_scraper import FreeStreamScraper
            
            debrid_enabled = (
                ADDON.getSetting('realdebrid_enabled') == 'true' or
                ADDON.getSetting('premiumize_enabled') == 'true' or
                ADDON.getSetting('alldebrid_enabled') == 'true' or
                ADDON.getSetting('torbox_enabled') == 'true'
            )
            
            all_sources = []
            scrapers = get_all_scrapers()
            
            # Only use top 4 fastest scrapers for pre-scrape (the "4-Link Rule")
            scraper_count = 0
            max_scrapers = 4
            
            for scraper in scrapers:
                if scraper_count >= max_scrapers:
                    break
                
                try:
                    if not scraper.is_enabled():
                        continue
                    
                    is_free = isinstance(scraper, FreeStreamScraper)
                    if not debrid_enabled and not is_free:
                        continue
                    
                    if media_type == 'movie':
                        results = scraper.get_movie_sources(title, year)
                    else:
                        results = scraper.get_episode_sources(title, year, season, episode)
                    
                    if results:
                        all_sources.extend(results)
                        scraper_count += 1
                except Exception:
                    continue
            
            if all_sources:
                self.db.cache_hover(cache_key, all_sources)
                log_utils.log(f'Pre-scraped {len(all_sources)} sources for: {title} ({year})', xbmc.LOGDEBUG)
        
        except Exception as e:
            log_utils.log(f'Pre-scrape error for {title}: {e}', xbmc.LOGDEBUG)
        
        finally:
            self._scraping.discard(cache_key)
    
    def get_cached(self, cache_key):
        """Get pre-scraped results if available"""
        return self.db.get_hover_cache(cache_key)
    
    def is_ready(self, cache_key):
        """Check if pre-scraped results are ready"""
        return self.db.get_hover_cache(cache_key) is not None
    
    def cleanup(self):
        """Cancel pending timers and prune old cache"""
        if self._timer:
            self._timer.cancel()
        self.db.prune_hover_cache(24)
