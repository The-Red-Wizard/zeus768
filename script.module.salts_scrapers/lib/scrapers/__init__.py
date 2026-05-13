"""
SALTS Scrapers Package - STREAM ALL THE SOURCES!
Revived and MASSIVELY EXPANDED by zeus768 for Kodi 21+

==========================================================
SLIMMED BUILD - Torrent + Stremio sources ONLY
==========================================================
This build removes:
  - All free-stream / file-hoster scrapers (VidSrc, 2Embed, FlixHQ,
    Soap2Day, FMovies, Streamtape/Doodstream/Mixdrop sites, etc.)
  - All "direct stream" hoster scrapers (Cineby, VidFast, RiveStream...)
  - Bones / TheChains / Butterbean direct-stream scrapers
  - Confirmed-dead torrent sources (RARBG, Torrentz2, Zooqle, SkyTorrents)

Kept:
  - Every Stremio protocol scraper (Torrentio, MediaFusion, Comet,
    Meteor, EasyNews + all free Stremio addons: Braflix, Cinemeta,
    KnightCrawler, Jackettio, Torrentio Free, AIOStreams, StremThru,
    MediaFlow, DDL, Anime/AnimeTosho, PlutoTV, Tubi, etc.)
  - Every live torrent scraper (1337x, YTS, EZTV, Nyaa, TPB,
    TorrentGalaxy, LimeTorrents, Kickass, SolidTorrents,
    TorrentDownload, BitSearch, TorLock, TorrentFunk, YourBittorrent,
    LeetX, TorrentsCSV, SolidTorrents2, Torrent9, RuTracker, RuTor,
    NNM-Club, BTBTT, SubsPlease, TokyoTosho, AnimeTosho)
  - Torrent aggregators (Jackett, Prowlarr, TorrentAPI, PlanetScrapers)
"""

# ----------------------------------------------------------
# Base classes
# ----------------------------------------------------------
from .base_scraper import BaseScraper, TorrentScraper

# ----------------------------------------------------------
# IMPORTANT: keep these imports so plugin.video.salts can still
# perform `isinstance(scraper, FreeStreamScraper)` checks and any
# residual code paths continue to resolve. The classes are *not*
# added to ALL_SCRAPERS so they will never run.
# ----------------------------------------------------------
from .freestream_scraper import FreeStreamScraper  # noqa: F401  (kept for plugin compat)

# ----------------------------------------------------------
# STREMIO PROTOCOL SCRAPERS
# ----------------------------------------------------------
from .stremio_scrapers import (
    TorrentioScraper,
    MediaFusionScraper,
    CometScraper,
    MeteorScraper,
    EasyNewsScraper,
)

# ----------------------------------------------------------
# STREMIO FREE ADDONS
# ----------------------------------------------------------
from .stremio_free_scrapers import (
    StreamingCommunityScraper,
    BraflixScraper,
    TheMovieArchiveScraper,
    PublicDomainMoviesScraper,
    WatchHubScraper,
    CinemetaScraper,
    KnightCrawlerScraper,
    JackettioScraper,
    OrionoidScraper,
    TPBPlusScraper,
    YTSScraper_Stremio,
    RARBG_StremioScraper,
    Torrentio_FreeScraper,
    AIOStreamsScraper,
    StremThruScraper,
    MediaFlowScraper,
    DDLStreamScraper,
    AnimeScraper_Stremio,
    AnimeToshoScraper_Stremio,
    LocalTVScraper,
    PlutoTVScraper,
    TubiScraper,
)

# ----------------------------------------------------------
# CORE TORRENT SCRAPERS
# ----------------------------------------------------------
from .x1337_scraper import X1337Scraper
from .yts_scraper import YTSScraper
from .eztv_scraper import EZTVScraper
from .nyaa_scraper import NyaaScraper
from .tpb_scraper import TPBScraper
from .torrentgalaxy_scraper import TorrentGalaxyScraper
from .limetorrents_scraper import LimeTorrentsScraper

# ----------------------------------------------------------
# EXTRA TORRENT SCRAPERS
# (Zooqle dropped - site dead since Nov 2022)
# ----------------------------------------------------------
from .extra_scrapers import (
    KickassScraper,
    RuTrackerScraper,
    SolidTorrentsScraper,
    TorrentDownloadScraper,
)

# ----------------------------------------------------------
# INTERNATIONAL / ANIME TORRENT SCRAPERS
# ----------------------------------------------------------
from .international_scrapers import (
    RuTorScraper,
    NNMClubScraper,
    BTBTTScraper,
    SubsPleaseScaper,
    TokyoToshoScraper,
    AnimeToshoScraper,
)

# ----------------------------------------------------------
# ADDITIONAL TORRENT SCRAPERS
# (SkytorrentScraper dropped - skytorrents.org offline since 2017)
# ----------------------------------------------------------
from .additional_torrent_scrapers import (
    BitSearchScraper,
    TorrentDownloads2Scraper,
    TorLockScraper,
    TorrentFunkScraper,
    YourBittorrentScraper,
    LeetXScraper,
    TorrentsCSVScraper,
    SolidTorrents2Scraper,
    Torrent9Scraper,
)

# ----------------------------------------------------------
# AGGREGATORS (Jackett / Prowlarr / etc - torrent indexers)
# ----------------------------------------------------------
from .jackett_scraper import JackettScraper
from .prowlarr_scraper import ProwlarrScraper
from .planetscrapers_scraper import PlanetScraper
from .torrentapi_scraper import TorrentAPIScraper


# ==========================================================
# MASTER SCRAPER LIST - Torrent + Stremio sources only
# Order matters (faster / more reliable first)
# ==========================================================
ALL_SCRAPERS = [
    # ---------- STREMIO PROTOCOL (Debrid + Free) ----------
    TorrentioScraper,
    MediaFusionScraper,
    CometScraper,
    MeteorScraper,
    EasyNewsScraper,

    # ---------- STREMIO FREE ADDONS ----------
    BraflixScraper,
    StreamingCommunityScraper,
    TheMovieArchiveScraper,
    PublicDomainMoviesScraper,
    WatchHubScraper,
    CinemetaScraper,
    KnightCrawlerScraper,
    JackettioScraper,
    OrionoidScraper,
    TPBPlusScraper,
    YTSScraper_Stremio,
    RARBG_StremioScraper,
    Torrentio_FreeScraper,
    AIOStreamsScraper,
    StremThruScraper,
    MediaFlowScraper,
    DDLStreamScraper,
    PlutoTVScraper,
    TubiScraper,
    LocalTVScraper,

    # ---------- PRIMARY TORRENT SITES ----------
    X1337Scraper,
    YTSScraper,
    EZTVScraper,
    TPBScraper,
    TorrentGalaxyScraper,
    SolidTorrentsScraper,

    # ---------- SECONDARY TORRENT SITES ----------
    LimeTorrentsScraper,
    KickassScraper,
    TorrentDownloadScraper,

    # ---------- ADDITIONAL TORRENT SITES ----------
    BitSearchScraper,
    TorrentDownloads2Scraper,
    TorLockScraper,
    TorrentFunkScraper,
    YourBittorrentScraper,
    LeetXScraper,
    TorrentsCSVScraper,
    SolidTorrents2Scraper,

    # ---------- ANIME TORRENTS ----------
    NyaaScraper,
    AnimeScraper_Stremio,
    AnimeToshoScraper_Stremio,
    SubsPleaseScaper,
    TokyoToshoScraper,
    AnimeToshoScraper,

    # ---------- RUSSIAN TORRENT SOURCES ----------
    RuTrackerScraper,
    RuTorScraper,
    NNMClubScraper,

    # ---------- CHINESE TORRENT SOURCES ----------
    BTBTTScraper,

    # ---------- FRENCH TORRENT SOURCES ----------
    Torrent9Scraper,

    # ---------- AGGREGATORS (require user setup) ----------
    JackettScraper,
    ProwlarrScraper,
    TorrentAPIScraper,

    # ---------- META AGGREGATOR ----------
    PlanetScraper,
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


def get_scraper_count():
    """Get total number of scrapers"""
    return len(ALL_SCRAPERS)


def get_scrapers_by_category():
    """Get scrapers organized by category"""
    return {
        'stremio_protocol': [
            TorrentioScraper, MediaFusionScraper, CometScraper,
            MeteorScraper, EasyNewsScraper,
        ],
        'stremio_free': [
            BraflixScraper, StreamingCommunityScraper, TheMovieArchiveScraper,
            PublicDomainMoviesScraper, WatchHubScraper, CinemetaScraper,
            KnightCrawlerScraper, JackettioScraper, OrionoidScraper,
            TPBPlusScraper, YTSScraper_Stremio, RARBG_StremioScraper,
            Torrentio_FreeScraper, AIOStreamsScraper, StremThruScraper,
            MediaFlowScraper, DDLStreamScraper, PlutoTVScraper,
            TubiScraper, LocalTVScraper,
        ],
        'torrent_primary': [
            X1337Scraper, YTSScraper, EZTVScraper, TPBScraper,
            TorrentGalaxyScraper, SolidTorrentsScraper,
        ],
        'torrent_secondary': [
            LimeTorrentsScraper, KickassScraper, TorrentDownloadScraper,
            BitSearchScraper, TorrentDownloads2Scraper, TorLockScraper,
            TorrentFunkScraper, YourBittorrentScraper, LeetXScraper,
            TorrentsCSVScraper, SolidTorrents2Scraper,
        ],
        'anime': [
            NyaaScraper, AnimeScraper_Stremio, AnimeToshoScraper_Stremio,
            SubsPleaseScaper, TokyoToshoScraper, AnimeToshoScraper,
        ],
        'international': [
            RuTrackerScraper, RuTorScraper, NNMClubScraper,
            BTBTTScraper, Torrent9Scraper,
        ],
        'aggregators': [
            JackettScraper, ProwlarrScraper, TorrentAPIScraper,
            PlanetScraper,
        ],
    }


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


# Print scraper count on import (for debugging)
import xbmc
xbmc.log(f'SALTS: Loaded {len(ALL_SCRAPERS)} scrapers (torrent + Stremio only)', xbmc.LOGINFO)
