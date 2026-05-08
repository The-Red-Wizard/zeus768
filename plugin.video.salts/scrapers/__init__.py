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
from .thechains_bones_shows_scraper import TheChainsBonesShowsScraper
from .thechains_wrestl_scraper import TheChainsWrestlScraper

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
# DIRECT STREAM SCRAPERS (NEW 2026-02)
# Easy-to-scrape sites that serve direct MP4 / M3U8 via JSON APIs.
# NO Streamtape / Doodstream / Mixdrop / Filemoon embeds.
# ==========================================================
from .direct_stream_scrapers import (
    ArchiveOrgScraper,
    CinebyScraper,
    VidFastScraper,
    RiveStreamScraper,
    UiraLiveScraper,
    NetMirrorScraper,
    VidBingeScraper,
    HollyMovieHDScraper,
    DIRECT_STREAM_SCRAPERS,
)

# ==========================================================
# STREAMTAPE / DOODSTREAM DIRECT-HOSTER SITES (NEW 2026-02 v2)
# Sites that expose Streamtape + Doodstream links directly on post pages
# (not behind heavy iframe obfuscation). zeus_resolvers handles playback.
# ==========================================================
from .streamtape_doodstream_sites import (
    VegaMoviesScraper,
    MoviesModScraper,
    HDHub4UScraper,
    SkyMoviesHDScraper,
    FilmyZillaScraper,
    MovieRulzScraper,
    MKVCinemasScraper,
    Bolly4UScraper,
    MoviesDaScraper,
    KatMovieHDScraper,
    ST_DOOD_DIRECT_SCRAPERS,
)

# ==========================================================
# STREMIO PROTOCOL SCRAPERS (Original)
# ==========================================================
from .stremio_scrapers import (
    TorrentioScraper,
    MediaFusionScraper,
    CometScraper,
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
from .nyaa_scraper import NyaaScraper
from .tpb_scraper import TPBScraper
from .torrentgalaxy_scraper import TorrentGalaxyScraper
from .limetorrents_scraper import LimeTorrentsScraper
from .torrentz2_scraper import Torrentz2Scraper
from .rarbg_scraper import RARBGScraper

# ==========================================================
# EXTRA TORRENT SCRAPERS
# ==========================================================
from .extra_scrapers import (
    KickassScraper,
    RuTrackerScraper,
    ZooqleScraper,
    SolidTorrentsScraper,
    TorrentDownloadScraper,
)

# ==========================================================
# INTERNATIONAL SCRAPERS
# ==========================================================
from .international_scrapers import (
    RuTorScraper,
    NNMClubScraper,
    BTBTTScraper,
    SubsPleaseScaper,
    TokyoToshoScraper,
    AnimeToshoScraper,
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
    Torrent9Scraper,
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
from .planetscrapers_scraper import PlanetScraper
from .torrentapi_scraper import TorrentAPIScraper


# ==========================================================
# MASTER SCRAPER LIST - ORDER MATTERS (faster/better first)
# ==========================================================
ALL_SCRAPERS = [
    # ========== BONES (Direct Stream Links) ==========
    BonesScraper,
    TheChainsBonesShowsScraper,
    TheChainsWrestlScraper,

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

    # ========== STREAMTAPE / DOODSTREAM DIRECT-HOSTER SITES (NEW v2) ==========
    # Sites that list Streamtape+Doodstream URLs directly on post pages.
    # zeus_resolvers converts them to playable mp4/m3u8 at play-time.
    VegaMoviesScraper,
    MoviesModScraper,
    HDHub4UScraper,
    SkyMoviesHDScraper,
    FilmyZillaScraper,
    MovieRulzScraper,
    MKVCinemasScraper,
    Bolly4UScraper,
    MoviesDaScraper,
    KatMovieHDScraper,

    # ========== FREE STREAMS (No Debrid - Direct Play) ==========
    # Primary Free Stream Aggregator
    FreeStreamScraper,

    # ========== DIRECT STREAM SITES (NEW 2026-02) ==========
    # Sites that return direct MP4 / M3U8 via JSON APIs.
    # No Streamtape / Doodstream / Mixdrop / Filemoon embeds.
    ArchiveOrgScraper,   # Public-domain movies + classic TV (pure MP4)
    CinebyScraper,       # cineby.ru (JSON -> m3u8)
    VidFastScraper,      # vidfast.pro (JSON -> m3u8)
    RiveStreamScraper,   # rivestream.net (JSON -> m3u8, 9 providers)
    UiraLiveScraper,     # uira.live (JSON -> m3u8)
    NetMirrorScraper,    # netmirror (JSON -> m3u8)
    VidBingeScraper,     # vidbinge.com (JSON -> m3u8)
    HollyMovieHDScraper, # hollymoviehd.cc (JSON -> m3u8)
    
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
    WatchSeriesScraper,
    SolarMovieScraper,
    ButterbeanSRStopScraper,
    
    # ========== STREMIO PROTOCOL (Debrid Enhanced) ==========
    TorrentioScraper,
    MediaFusionScraper,   # Community torrent/stream aggregator (RD/AD/PM/TorBox)
    CometScraper,         # Fast debrid-first torrent aggregator
    EasyNewsScraper,
    
    # ========== STREAMING SITES (Legacy) ==========
    PrimeWireScraper,
    Movie4KScraper,
    
    # ========== PRIMARY TORRENT SITES ==========
    X1337Scraper,
    YTSScraper,
    EZTVScraper,
    TPBScraper,
    TorrentGalaxyScraper,
    SolidTorrentsScraper,
    
    # ========== SECONDARY TORRENT SITES ==========
    LimeTorrentsScraper,
    Torrentz2Scraper,
    RARBGScraper,
    KickassScraper,
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
    SkytorrentScraper,
    
    # ========== META SEARCH ==========
    ZooqleScraper,
    
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
    BTBTTScraper,
    
    # ========== FRENCH SOURCES ==========
    Torrent9Scraper,
    
    # ========== AGGREGATORS (Require Setup) ==========
    JackettScraper,
    ProwlarrScraper,
    TorrentAPIScraper,

    # ========== AGGREGATED (Torrentio + TPB + RARBG + TGx + 1337x rolled into one) ==========
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
        'direct_streams': [
            ArchiveOrgScraper, CinebyScraper, VidFastScraper,
            RiveStreamScraper, UiraLiveScraper, NetMirrorScraper,
            VidBingeScraper, HollyMovieHDScraper,
        ],
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
        ],
        'streaming_sites': [
            FlixHQScraper, BFlixTVScraper, HDTodayScraper, Soap2DayScraper,
            LookMovieScraper, FMoviesScraper, GoMoviesScraper, Movies123Scraper,
            MoviesJoyScraper, PutlockerScraper, SolarMovieScraper,
            ButterbeanSRStopScraper,
        ],
        'torrent_primary': [
            EZTVScraper, TPBScraper,
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
            RuTrackerScraper, RuTorScraper, NNMClubScraper,
            BTBTTScraper, Torrent9Scraper,
        ],
        'aggregators': [
            JackettScraper, ProwlarrScraper, TorrentAPIScraper,
        ],
        'stremio_debrid': [
            TorrentioScraper, MediaFusionScraper, CometScraper,
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
