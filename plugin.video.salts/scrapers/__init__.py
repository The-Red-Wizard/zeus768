"""
SALTS Scrapers Package - STREAM ALL THE SOURCES!
Revived by zeus768 for Kodi 21+

Total Scrapers: 35+

Includes:
- Free Streams: VidSrc, 2Embed, AutoEmbed, MultiEmbed, Embed.su, VidLink (direct play, no debrid)
- Torrent Sites: 1337x, YTS, EZTV, TorrentGalaxy, Nyaa, ThePirateBay, LimeTorrents, Torrentz2, RARBG, Kickass, MagnetDL, GLODLS, iDope, SolidTorrents, TorrentDownload, TorrentProject, Zooqle, BTDigg
- International: RuTracker, RuTor, NNM-Club (Russian), DyTT, BTBTT (Chinese)
- Anime: Nyaa, SubsPlease, TokyoTosho, AnimeTosho, AniDex
- Streaming Sites: PrimeWire, WatchSeries, Movie4K, SolarMovie
- Indexer Aggregators: Jackett, Prowlarr
- APIs: TorrentAPI
"""

from .base_scraper import BaseScraper, TorrentScraper

# Free stream scraper (no debrid needed)
from .freestream_scraper import FreeStreamScraper

# Core torrent scrapers
from .x1337_scraper import X1337Scraper
from .yts_scraper import YTSScraper
from .eztv_scraper import EZTVScraper
from .torrentgalaxy_scraper import TorrentGalaxyScraper
from .nyaa_scraper import NyaaScraper
from .tpb_scraper import TPBScraper
from .limetorrents_scraper import LimeTorrentsScraper
from .torrentz2_scraper import Torrentz2Scraper
from .rarbg_scraper import RARBGScraper

# Extra torrent scrapers
from .extra_scrapers import (
    KickassScraper,
    RuTrackerScraper,
    BTDiggScraper,
    ZooqleScraper,
    MagnetDLScraper,
    GlodLSScraper,
    iDopeScraper,
    SolidTorrentsScraper,
    TorrentDownloadScraper,
    TorrentProjectScraper,
)

# International scrapers
from .international_scrapers import (
    RuTorScraper,
    NNMClubScraper,
    DyTTScraper,
    BTBTTScraper,
    SubsPleaseScaper,
    TokyoToshoScraper,
    AnimeToshoScraper,
    AniDexScraper,
)

# Streaming site scrapers
from .primewire_scraper import PrimeWireScraper
from .watchseries_scraper import WatchSeriesScraper
from .movie4k_scraper import Movie4KScraper
from .solarmovie_scraper import SolarMovieScraper

# Aggregators
from .jackett_scraper import JackettScraper
from .prowlarr_scraper import ProwlarrScraper
from .torrentapi_scraper import TorrentAPIScraper

# List of all scraper classes - ORDER MATTERS (faster/better first)
ALL_SCRAPERS = [
    # FREE STREAMS (no debrid needed - direct play)
    FreeStreamScraper,
    
    # PRIMARY - Fast and reliable
    X1337Scraper,
    YTSScraper,
    EZTVScraper,
    TorrentGalaxyScraper,
    TPBScraper,
    SolidTorrentsScraper,
    
    # SECONDARY - Good sources
    LimeTorrentsScraper,
    Torrentz2Scraper,
    RARBGScraper,
    KickassScraper,
    MagnetDLScraper,
    GlodLSScraper,
    iDopeScraper,
    TorrentDownloadScraper,
    
    # META SEARCH
    BTDiggScraper,
    ZooqleScraper,
    TorrentProjectScraper,
    
    # ANIME SPECIFIC
    NyaaScraper,
    SubsPleaseScaper,
    TokyoToshoScraper,
    AnimeToshoScraper,
    AniDexScraper,
    
    # RUSSIAN SOURCES
    RuTrackerScraper,
    RuTorScraper,
    NNMClubScraper,
    
    # CHINESE SOURCES
    DyTTScraper,
    BTBTTScraper,
    
    # STREAMING SITES
    PrimeWireScraper,
    WatchSeriesScraper,
    Movie4KScraper,
    SolarMovieScraper,
    
    # AGGREGATORS (require setup)
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
