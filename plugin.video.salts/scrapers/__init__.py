"""
SALTS Scrapers Package
Revived by zeus768 for Kodi 21+

Includes scrapers for:
- Torrent Sites: 1337x, YTS, EZTV, TorrentGalaxy, Nyaa, ThePirateBay, LimeTorrents, Torrentz2, RARBG
- Streaming Sites: PrimeWire, WatchSeries, Movie4K, SolarMovie
- Indexer Aggregators: Jackett, Prowlarr
- APIs: TorrentAPI
"""

from .base_scraper import BaseScraper, TorrentScraper

# Import torrent scrapers
from .x1337_scraper import X1337Scraper
from .yts_scraper import YTSScraper
from .eztv_scraper import EZTVScraper
from .torrentgalaxy_scraper import TorrentGalaxyScraper
from .nyaa_scraper import NyaaScraper
from .tpb_scraper import TPBScraper
from .limetorrents_scraper import LimeTorrentsScraper
from .torrentz2_scraper import Torrentz2Scraper
from .rarbg_scraper import RARBGScraper
from .jackett_scraper import JackettScraper
from .prowlarr_scraper import ProwlarrScraper
from .torrentapi_scraper import TorrentAPIScraper

# Import streaming site scrapers (modernized legacy scrapers)
from .primewire_scraper import PrimeWireScraper
from .watchseries_scraper import WatchSeriesScraper
from .movie4k_scraper import Movie4KScraper
from .solarmovie_scraper import SolarMovieScraper

# List of all scraper classes
ALL_SCRAPERS = [
    # Primary torrent sites
    X1337Scraper,
    YTSScraper,
    EZTVScraper,
    TorrentGalaxyScraper,
    TPBScraper,
    
    # Secondary torrent sites
    LimeTorrentsScraper,
    Torrentz2Scraper,
    RARBGScraper,
    
    # Anime
    NyaaScraper,
    
    # Streaming sites (modernized legacy)
    PrimeWireScraper,
    WatchSeriesScraper,
    Movie4KScraper,
    SolarMovieScraper,
    
    # Indexer aggregators (requires user setup)
    JackettScraper,
    ProwlarrScraper,
    
    # APIs
    TorrentAPIScraper,
]

def get_all_scrapers():
    """Get list of all scraper classes"""
    return ALL_SCRAPERS

def get_enabled_scrapers():
    """Get list of enabled scraper instances"""
    enabled = []
    for scraper_cls in ALL_SCRAPERS:
        try:
            scraper = scraper_cls()
            if scraper.is_enabled():
                enabled.append(scraper)
        except Exception:
            pass
    return enabled

def get_scraper_by_name(name):
    """Get scraper class by name"""
    for scraper_cls in ALL_SCRAPERS:
        if scraper_cls.NAME.lower() == name.lower():
            return scraper_cls
    return None

# ScraperVideo class for compatibility
class ScraperVideo:
    """Video information for scraper searches"""
    
    def __init__(self, video_type, title, year='', slug='', season='', episode='', ep_title=''):
        self.video_type = video_type
        self.title = title
        self.year = year
        self.slug = slug
        self.season = season
        self.episode = episode
        self.ep_title = ep_title
    
    def __str__(self):
        if self.video_type == 'episode':
            return f'{self.title} S{self.season:02d}E{self.episode:02d}'
        elif self.year:
            return f'{self.title} ({self.year})'
        return self.title
