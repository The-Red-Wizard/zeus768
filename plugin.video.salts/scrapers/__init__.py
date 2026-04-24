"""
SALTS Scrapers Package - STREAM ALL THE SOURCES!
Revived and MASSIVELY EXPANDED by zeus768 for Kodi 21+

==========================================================
TOTAL SCRAPERS: 120+ SOURCES
==========================================================

FREE STREAMS (No Debrid Required):
- VidSrc variants (xyz, cc, in, pm, nl, pro, me, to)
- 2Embed variants
- Embed.su, AutoEmbed, MultiEmbed, VidLink, VidPlay
- FlixHQ, BFlix, HDToday, Soap2Day, LookMovie
- FMovies, GoMovies, 123Movies, Putlocker
- AZMovies, YesMovies, MoviesJoy, StreamLord
- And 40+ more streaming sites!

STREMIO FREE ADDONS:
- Torrentio (Free Mode), MediaFusion, Comet
- CyberFlix, PeerFlix, Braflix
- KnightCrawler, Jackettio, AIOStreams
- PublicDomainMovies, TheMovieArchive
- PlutoTV, Tubi, and more!

TORRENT SITES:
- 1337x, YTS, EZTV, TorrentGalaxy, TPB
- Nyaa, LimeTorrents, Torrentz2, RARBG
- Kickass, MagnetDL, GLODLS, iDope
- SolidTorrents, BitSearch, TorLock
- TorrentFunk, TorrentsCSV, and more!

INTERNATIONAL:
- Russian: RuTracker, RuTor, NNM-Club
- Chinese: DyTT, BTBTT
- French: Torrent9, YggTorrent
- Asian Drama: DramaCool, KissAsian, WatchAsian

ANIME:
- Nyaa, SubsPlease, AnimeTosho, TokyoTosho
- Zoro, 9Anime, GogoAnime, AniWave, HiAnime
- AnimePahe, KickAssAnime, AllAnime

AGGREGATORS:
- Jackett, Prowlarr, TorrentAPI
"""

from .base_scraper import BaseScraper, TorrentScraper
from .bones_scraper import BonesScraper

# ==========================================================
# STREAMTAPE / LULUVDO EXTRA SOURCES (NEW 2026-02)
# Independent sites only (NOT thechains24.com)
# ==========================================================
from .streamtape_lulu_scrapers import (
    GokuStreamtapeScraper,
    GokuTVStreamtapeScraper,
    FrenchStreamScraper,
    PutlockerFmScraper,
    MyFlixerHostScraper,
    FmoviesHostScraper,
    SoaperHostScraper,
    HdtodayHostScraper,
    FlixtorHostScraper,
    MoviesJoyHostScraper,
    DDGStreamtapeScraper,
    ST_LULU_SCRAPERS,
)

# ==========================================================
# CORE FREE STREAM SCRAPERS
# ==========================================================
from .freestream_scraper import FreeStreamScraper

# ==========================================================
# STREMIO PROTOCOL SCRAPERS (Original)
# ==========================================================
from .stremio_scrapers import (
    TorrentioScraper,
    MediaFusionScraper,
    CometScraper,
    CyberFlixScraper,
    AnnatarScraper,
    PeerFlixScraper,
    EasyNewsScraper,
)

# ==========================================================
# STREMIO FREE ADDONS (NEW)
# ==========================================================
from .stremio_free_scrapers import (
    VidSrcMeScraper,
    VidSrcToScraper,
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
    STREMIO_FREE_SCRAPERS,
)

# ==========================================================
# EXTENDED FREE STREAMING SCRAPERS (NEW - 50+ sources)
# ==========================================================
from .extended_free_scrapers import (
    # VidSrc Variants
    VidSrcXYZScraper,
    VidSrcCCScraper,
    VidSrcInScraper,
    VidSrcPMScraper,
    VidSrcNLScraper,
    VidSrcProScraper,
    # 2Embed Variants
    TwoEmbedScraper,
    TwoEmbedOrgScraper,
    # Embed Services
    EmbedSuScraper,
    AutoEmbedScraper,
    MultiEmbedScraper,
    VidLinkScraper,
    VidPlayScraper,
    MoviesAPIScraper,
    NontonGoScraper,
    SmashyStreamScraper,
    RgShortsScraper,
    # Streaming Sites
    FlixHQScraper,
    BFlixTVScraper,
    HDTodayScraper,
    Soap2DayScraper,
    LookMovieScraper,
    AZMoviesScraper,
    YesMoviesScraper,
    FMoviesScraper,
    GoMoviesScraper,
    Movies123Scraper,
    StreamLordScraper,
    MoviesJoyScraper,
    SFlix2Scraper,
    PutlockerScraper,
    WatchSeriesHDScraper,
    M4UFreesScraper,
    YifyMoviesScraper,
    SolarMovieScraper2,
    XMovies8Scraper,
    IOMoviesScraper,
    CMoviesHDScraper,
    # Asian Drama
    WatchAsianScraper,
    KissAsianScraper,
    DramaCoolScraper,
    ViewAsianScraper,
    AsianLoadScraper,
    # Anime
    ZoroScraper,
    NineAnimeScraper,
    GogoAnimeScraper,
    AniWaveScraper,
    HiAnimeScraper,
    AnimePaheScraper,
    AnimeFlixScraper,
    KickAssAnimeScraper,
    YugenAnimeScraper,
    AllAnimeScraper,
    AnimeSugeScraper,
    AniwatchScraper,
    EXTENDED_FREE_SCRAPERS,
)

# ==========================================================
# CORE TORRENT SCRAPERS
# ==========================================================
from .x1337_scraper import X1337Scraper
from .yts_scraper import YTSScraper
from .eztv_scraper import EZTVScraper
from .torrentgalaxy_scraper import TorrentGalaxyScraper
from .nyaa_scraper import NyaaScraper
from .tpb_scraper import TPBScraper
from .limetorrents_scraper import LimeTorrentsScraper
from .torrentz2_scraper import Torrentz2Scraper
from .rarbg_scraper import RARBGScraper

# ==========================================================
# EXTRA TORRENT SCRAPERS
# ==========================================================
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

# ==========================================================
# INTERNATIONAL SCRAPERS
# ==========================================================
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

# ==========================================================
# ADDITIONAL TORRENT SCRAPERS (NEW)
# ==========================================================
from .additional_torrent_scrapers import (
    BitSearchScraper,
    TorrentDownloads2Scraper,
    TorLockScraper,
    TorrentFunkScraper,
    YourBittorrentScraper,
    LeetXScraper,
    TorrentsCSVScraper,
    SolidTorrents2Scraper,
    AcgTorrentScraper,
    Torrent9Scraper,
    YggTorrentScraper,
    EtHDScraper,
    SkytorrentScraper,
    ADDITIONAL_TORRENT_SCRAPERS,
)

# ==========================================================
# STREAMING SITE SCRAPERS
# ==========================================================
from .primewire_scraper import PrimeWireScraper
from .watchseries_scraper import WatchSeriesScraper
from .movie4k_scraper import Movie4KScraper
from .solarmovie_scraper import SolarMovieScraper
from .butterbeansrstop_scraper import ButterbeanSRStopScraper

# ==========================================================
# AGGREGATORS
# ==========================================================
from .jackett_scraper import JackettScraper
from .prowlarr_scraper import ProwlarrScraper
from .torrentapi_scraper import TorrentAPIScraper


# ==========================================================
# MASTER SCRAPER LIST - ORDER MATTERS (faster/better first)
# ==========================================================
ALL_SCRAPERS = [
    # ========== BONES (Direct Stream Links) ==========
    BonesScraper,

    # ========== STREAMTAPE / LULUVDO EXTRA SOURCES (NEW) ==========
    # Site scrapers - search live sites for streamtape/luluvdo iframes
    GokuStreamtapeScraper,
    GokuTVStreamtapeScraper,
    PutlockerFmScraper,
    MyFlixerHostScraper,
    FmoviesHostScraper,
    SoaperHostScraper,
    HdtodayHostScraper,
    FlixtorHostScraper,
    MoviesJoyHostScraper,
    FrenchStreamScraper,
    # Last-resort web search (opt-in)
    DDGStreamtapeScraper,

    # ========== FREE STREAMS (No Debrid - Direct Play) ==========
    # Primary Free Stream Aggregator
    FreeStreamScraper,
    
    # VidSrc Network (Most Reliable Free Sources)
    VidSrcXYZScraper,
    VidSrcCCScraper,
    VidSrcInScraper,
    VidSrcPMScraper,
    VidSrcNLScraper,
    VidSrcProScraper,
    VidSrcMeScraper,
    VidSrcToScraper,
    
    # 2Embed Network
    TwoEmbedScraper,
    TwoEmbedOrgScraper,
    
    # Embed Services
    EmbedSuScraper,
    AutoEmbedScraper,
    MultiEmbedScraper,
    VidLinkScraper,
    VidPlayScraper,
    MoviesAPIScraper,
    SmashyStreamScraper,
    NontonGoScraper,
    RgShortsScraper,
    
    # ========== STREMIO FREE ADDONS ==========
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
    
    # ========== STREAMING SITES ==========
    FlixHQScraper,
    BFlixTVScraper,
    HDTodayScraper,
    Soap2DayScraper,
    LookMovieScraper,
    AZMoviesScraper,
    YesMoviesScraper,
    FMoviesScraper,
    GoMoviesScraper,
    Movies123Scraper,
    StreamLordScraper,
    MoviesJoyScraper,
    SFlix2Scraper,
    PutlockerScraper,
    WatchSeriesHDScraper,
    M4UFreesScraper,
    YifyMoviesScraper,
    SolarMovieScraper2,
    XMovies8Scraper,
    IOMoviesScraper,
    CMoviesHDScraper,
    
    # Legacy Streaming Sites
    PrimeWireScraper,
    WatchSeriesScraper,
    Movie4KScraper,
    SolarMovieScraper,
    ButterbeanSRStopScraper,
    
    # ========== STREMIO PROTOCOL (Debrid Enhanced) ==========
    TorrentioScraper,
    MediaFusionScraper,
    CometScraper,
    AnnatarScraper,
    EasyNewsScraper,
    CyberFlixScraper,
    PeerFlixScraper,
    
    # ========== PRIMARY TORRENT SITES ==========
    X1337Scraper,
    YTSScraper,
    EZTVScraper,
    TorrentGalaxyScraper,
    TPBScraper,
    SolidTorrentsScraper,
    
    # ========== SECONDARY TORRENT SITES ==========
    LimeTorrentsScraper,
    Torrentz2Scraper,
    RARBGScraper,
    KickassScraper,
    MagnetDLScraper,
    GlodLSScraper,
    iDopeScraper,
    TorrentDownloadScraper,
    
    # ========== ADDITIONAL TORRENT SITES ==========
    BitSearchScraper,
    TorrentDownloads2Scraper,
    TorLockScraper,
    TorrentFunkScraper,
    YourBittorrentScraper,
    LeetXScraper,
    TorrentsCSVScraper,
    SolidTorrents2Scraper,
    EtHDScraper,
    SkytorrentScraper,
    
    # ========== META SEARCH ==========
    BTDiggScraper,
    ZooqleScraper,
    TorrentProjectScraper,
    
    # ========== ANIME ==========
    NyaaScraper,
    ZoroScraper,
    NineAnimeScraper,
    GogoAnimeScraper,
    AniWaveScraper,
    HiAnimeScraper,
    AnimePaheScraper,
    AnimeFlixScraper,
    KickAssAnimeScraper,
    YugenAnimeScraper,
    AllAnimeScraper,
    AnimeSugeScraper,
    AniwatchScraper,
    AnimeScraper_Stremio,
    AnimeToshoScraper_Stremio,
    SubsPleaseScaper,
    TokyoToshoScraper,
    AnimeToshoScraper,
    AniDexScraper,
    AcgTorrentScraper,
    
    # ========== ASIAN DRAMA ==========
    WatchAsianScraper,
    KissAsianScraper,
    DramaCoolScraper,
    ViewAsianScraper,
    AsianLoadScraper,
    
    # ========== RUSSIAN SOURCES ==========
    RuTrackerScraper,
    RuTorScraper,
    NNMClubScraper,
    
    # ========== CHINESE SOURCES ==========
    DyTTScraper,
    BTBTTScraper,
    
    # ========== FRENCH SOURCES ==========
    Torrent9Scraper,
    YggTorrentScraper,
    
    # ========== AGGREGATORS (Require Setup) ==========
    JackettScraper,
    ProwlarrScraper,
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


def get_scraper_count():
    """Get total number of scrapers"""
    return len(ALL_SCRAPERS)


def get_scrapers_by_category():
    """Get scrapers organized by category"""
    return {
        'free_streams': [
            FreeStreamScraper, VidSrcXYZScraper, VidSrcCCScraper, VidSrcInScraper,
            VidSrcPMScraper, VidSrcNLScraper, VidSrcProScraper, VidSrcMeScraper,
            VidSrcToScraper, TwoEmbedScraper, TwoEmbedOrgScraper, EmbedSuScraper,
            AutoEmbedScraper, MultiEmbedScraper, VidLinkScraper, VidPlayScraper,
            MoviesAPIScraper, SmashyStreamScraper,
        ],
        'stremio_free': [
            BraflixScraper, StreamingCommunityScraper, TheMovieArchiveScraper,
            PublicDomainMoviesScraper, WatchHubScraper, KnightCrawlerScraper,
            Torrentio_FreeScraper, AIOStreamsScraper, PlutoTVScraper, TubiScraper,
            CyberFlixScraper, PeerFlixScraper,
        ],
        'streaming_sites': [
            FlixHQScraper, BFlixTVScraper, HDTodayScraper, Soap2DayScraper,
            LookMovieScraper, FMoviesScraper, GoMoviesScraper, Movies123Scraper,
            MoviesJoyScraper, PutlockerScraper, SolarMovieScraper,
            ButterbeanSRStopScraper,
        ],
        'torrent_primary': [
            X1337Scraper, YTSScraper, EZTVScraper, TorrentGalaxyScraper, TPBScraper,
        ],
        'torrent_secondary': [
            LimeTorrentsScraper, Torrentz2Scraper, RARBGScraper, KickassScraper,
            BitSearchScraper, TorLockScraper, TorrentsCSVScraper,
        ],
        'anime': [
            NyaaScraper, ZoroScraper, NineAnimeScraper, GogoAnimeScraper,
            AniWaveScraper, HiAnimeScraper, AnimePaheScraper,
        ],
        'asian_drama': [
            WatchAsianScraper, KissAsianScraper, DramaCoolScraper,
        ],
        'international': [
            RuTrackerScraper, RuTorScraper, NNMClubScraper, DyTTScraper,
            BTBTTScraper, Torrent9Scraper, YggTorrentScraper,
        ],
        'aggregators': [
            JackettScraper, ProwlarrScraper, TorrentAPIScraper,
        ],
        'stremio_debrid': [
            TorrentioScraper, MediaFusionScraper, CometScraper, AnnatarScraper,
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
xbmc.log(f'SALTS: Loaded {len(ALL_SCRAPERS)} scrapers', xbmc.LOGINFO)
