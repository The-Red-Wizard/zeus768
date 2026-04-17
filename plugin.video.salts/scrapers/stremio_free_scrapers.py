"""
SALTS Scrapers - Stremio Free Stream Addons (No Debrid Required)
Added by zeus768 for maximum source coverage

These scrapers connect to various Stremio addon APIs that provide
free streaming links without requiring debrid services.
"""
import re
import json
import xbmc
import xbmcaddon
from urllib.request import urlopen, Request
from urllib.parse import quote_plus, urlencode
from .base_scraper import BaseScraper
from salts_lib import log_utils

ADDON = xbmcaddon.Addon()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


class StremioAddonScraper(BaseScraper):
    """Base class for Stremio addon scrapers"""
    
    ADDON_URL = ''
    NAME = 'StremioBase'
    
    def _get_imdb_id(self, title, year, media_type='movie'):
        """Get IMDB ID from TMDB"""
        try:
            search_type = 'movie' if media_type == 'movie' else 'tv'
            url = f'https://api.themoviedb.org/3/search/{search_type}'
            params = {
                'api_key': '8265bd1679663a7ea12ac168da84d2e8',
                'query': title,
                'year': year
            }
            query = '&'.join(f'{k}={quote_plus(str(v))}' for k, v in params.items())
            req = Request(f'{url}?{query}', headers={'User-Agent': UA})
            resp = urlopen(req, timeout=10)
            data = json.loads(resp.read().decode('utf-8'))
            
            if data.get('results'):
                tmdb_id = data['results'][0]['id']
                # Get external IDs
                ext_url = f'https://api.themoviedb.org/3/{search_type}/{tmdb_id}/external_ids?api_key=8265bd1679663a7ea12ac168da84d2e8'
                req2 = Request(ext_url, headers={'User-Agent': UA})
                resp2 = urlopen(req2, timeout=10)
                ext_data = json.loads(resp2.read().decode('utf-8'))
                return ext_data.get('imdb_id', '')
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: IMDB lookup error: {e}')
        return ''
    
    def _fetch_stremio_streams(self, imdb_id, media_type='movie', season=None, episode=None):
        """Fetch streams from Stremio addon"""
        if not self.ADDON_URL or not imdb_id:
            return []
        
        try:
            if media_type == 'movie':
                url = f'{self.ADDON_URL}/stream/movie/{imdb_id}.json'
            else:
                url = f'{self.ADDON_URL}/stream/series/{imdb_id}:{season}:{episode}.json'
            
            req = Request(url, headers={'User-Agent': UA})
            resp = urlopen(req, timeout=15)
            data = json.loads(resp.read().decode('utf-8'))
            
            sources = []
            for stream in data.get('streams', []):
                source = {
                    'scraper': self.NAME,
                    'quality': self._parse_quality(stream.get('title', '') + stream.get('name', '')),
                    'name': stream.get('name', stream.get('title', self.NAME)),
                    'size': '',
                    'seeds': 0,
                    'type': 'stream'
                }
                
                if stream.get('url'):
                    source['url'] = stream['url']
                elif stream.get('infoHash'):
                    source['magnet'] = self._make_magnet(stream['infoHash'], stream.get('title', 'video'))
                    source['type'] = 'torrent'
                    source['hash'] = stream['infoHash']
                else:
                    continue
                
                # Parse additional info
                title = stream.get('title', '') or stream.get('description', '')
                size_match = re.search(r'(\d+\.?\d*)\s*(GB|MB)', title, re.I)
                if size_match:
                    source['size'] = f'{size_match.group(1)} {size_match.group(2).upper()}'
                
                sources.append(source)
            
            return sources
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Fetch error: {e}')
            return []
    
    def _make_magnet(self, info_hash, name):
        """Create magnet link"""
        trackers = [
            'udp://tracker.opentrackr.org:1337/announce',
            'udp://open.stealth.si:80/announce',
            'udp://tracker.torrent.eu.org:451/announce',
            'udp://exodus.desync.com:6969/announce'
        ]
        tracker_str = '&tr='.join([quote_plus(t) for t in trackers])
        return f'magnet:?xt=urn:btih:{info_hash}&dn={quote_plus(name)}&tr={tracker_str}'
    
    def search(self, query, media_type='movie'):
        return []
    
    def get_movie_sources(self, title, year=''):
        imdb_id = self._get_imdb_id(title, year, 'movie')
        if imdb_id:
            return self._fetch_stremio_streams(imdb_id, 'movie')
        return []
    
    def get_episode_sources(self, title, year, season, episode):
        imdb_id = self._get_imdb_id(title, year, 'tvshow')
        if imdb_id:
            return self._fetch_stremio_streams(imdb_id, 'series', season, episode)
        return []


# ==================== STREMIO FREE ADDONS ====================

class VidSrcMeScraper(StremioAddonScraper):
    """VidSrc.me Stremio Addon - Multiple free providers"""
    NAME = 'VidSrc.me'
    ADDON_URL = 'https://vidsrc.me/stremio'
    
    def is_enabled(self):
        return ADDON.getSetting('vidsrcme_enabled') != 'false'


class VidSrcToScraper(StremioAddonScraper):
    """VidSrc.to - Free streaming"""
    NAME = 'VidSrc.to'
    ADDON_URL = 'https://vidsrc.to/stremio'
    
    def is_enabled(self):
        return ADDON.getSetting('vidsrcto_enabled') != 'false'


class StreamingCommunityScraper(StremioAddonScraper):
    """StreamingCommunity - Italian & English streams"""
    NAME = 'StreamingCommunity'
    ADDON_URL = 'https://streamingcommunity.stremio.it'
    
    def is_enabled(self):
        return ADDON.getSetting('streamingcommunity_enabled') != 'false'


class BraflixScraper(StremioAddonScraper):
    """Braflix - Free movies & TV"""
    NAME = 'Braflix'
    ADDON_URL = 'https://braflix.stremio.bar'
    
    def is_enabled(self):
        return ADDON.getSetting('braflix_enabled') != 'false'


class TheMovieArchiveScraper(StremioAddonScraper):
    """TheMovieArchive - Public domain & free movies"""
    NAME = 'TheMovieArchive'
    ADDON_URL = 'https://themoviearchive.site/stremio'
    
    def is_enabled(self):
        return ADDON.getSetting('themoviearchive_enabled') != 'false'


class PublicDomainMoviesScraper(StremioAddonScraper):
    """Public Domain Movies - Legal free movies"""
    NAME = 'PublicDomainMovies'
    ADDON_URL = 'https://pdom.stremio.com'
    
    def is_enabled(self):
        return ADDON.getSetting('publicdomainmovies_enabled') != 'false'


class OpenSubsScraper(StremioAddonScraper):
    """OpenSubtitles - Subtitle provider (bonus feature)"""
    NAME = 'OpenSubtitles'
    ADDON_URL = 'https://opensubtitles.strem.io'
    
    def is_enabled(self):
        return ADDON.getSetting('opensubs_enabled') != 'false'


class WatchHubScraper(StremioAddonScraper):
    """WatchHub - Multi-source aggregator"""
    NAME = 'WatchHub'
    ADDON_URL = 'https://watchhub.strem.fun'
    
    def is_enabled(self):
        return ADDON.getSetting('watchhub_enabled') != 'false'


class CinemetaScraper(StremioAddonScraper):
    """Cinemeta - Official Stremio metadata + streams"""
    NAME = 'Cinemeta'
    ADDON_URL = 'https://cinemeta-catalogs.strem.io'
    
    def is_enabled(self):
        return ADDON.getSetting('cinemeta_enabled') != 'false'


class KnightCrawlerScraper(StremioAddonScraper):
    """KnightCrawler - Torrent aggregator"""
    NAME = 'KnightCrawler'
    ADDON_URL = 'https://knightcrawler.elfhosted.com'
    
    def is_enabled(self):
        return ADDON.getSetting('knightcrawler_enabled') != 'false'


class JackettioScraper(StremioAddonScraper):
    """Jackettio - Jackett for Stremio"""
    NAME = 'Jackettio'
    ADDON_URL = 'https://jackettio.elfhosted.com'
    
    def is_enabled(self):
        return ADDON.getSetting('jackettio_enabled') != 'false'


class OrionoidScraper(StremioAddonScraper):
    """Orionoid - Premium torrent indexer"""
    NAME = 'Orionoid'
    ADDON_URL = 'https://orionoid.com/stremio'
    
    def is_enabled(self):
        return ADDON.getSetting('orionoid_enabled') != 'false'


class TPBPlusScraper(StremioAddonScraper):
    """ThePirateBay+ - Enhanced TPB for Stremio"""
    NAME = 'TPBPlus'
    ADDON_URL = 'https://thepiratebay-plus.strem.fun'
    
    def is_enabled(self):
        return ADDON.getSetting('tpbplus_enabled') != 'false'


class YTSScraper_Stremio(StremioAddonScraper):
    """YTS Stremio - YIFY movies"""
    NAME = 'YTS-Stremio'
    ADDON_URL = 'https://yts.strem.fun'
    
    def is_enabled(self):
        return ADDON.getSetting('yts_stremio_enabled') != 'false'


class RARBG_StremioScraper(StremioAddonScraper):
    """RARBG Stremio - RARBG mirror"""
    NAME = 'RARBG-Stremio'
    ADDON_URL = 'https://rarbg.strem.fun'
    
    def is_enabled(self):
        return ADDON.getSetting('rarbg_stremio_enabled') != 'false'


class Torrentio_FreeScraper(StremioAddonScraper):
    """Torrentio (Free Mode) - No debrid required"""
    NAME = 'Torrentio-Free'
    ADDON_URL = 'https://torrentio.strem.fun/sort=size'
    
    def is_enabled(self):
        return ADDON.getSetting('torrentio_free_enabled') != 'false'


class AIOStreamsScraper(StremioAddonScraper):
    """AIOStreams - All-in-One stream aggregator"""
    NAME = 'AIOStreams'
    ADDON_URL = 'https://aiostreams.elfhosted.com'
    
    def is_enabled(self):
        return ADDON.getSetting('aiostreams_enabled') != 'false'


class StremThruScraper(StremioAddonScraper):
    """StremThru - Stream passthrough service"""
    NAME = 'StremThru'
    ADDON_URL = 'https://stremthru.elfhosted.com'
    
    def is_enabled(self):
        return ADDON.getSetting('stremthru_enabled') != 'false'


class MediaFlowScraper(StremioAddonScraper):
    """MediaFlow - High quality streams"""
    NAME = 'MediaFlow'
    ADDON_URL = 'https://mediaflow.elfhosted.com'
    
    def is_enabled(self):
        return ADDON.getSetting('mediaflow_enabled') != 'false'


class DDLStreamScraper(StremioAddonScraper):
    """DDLStream - Direct download links"""
    NAME = 'DDLStream'
    ADDON_URL = 'https://ddlstream.strem.fun'
    
    def is_enabled(self):
        return ADDON.getSetting('ddlstream_enabled') != 'false'


class AnimeScraper_Stremio(StremioAddonScraper):
    """Anime Stremio - Anime aggregator"""
    NAME = 'Anime-Stremio'
    ADDON_URL = 'https://anime.strem.fun'
    
    def is_enabled(self):
        return ADDON.getSetting('anime_stremio_enabled') != 'false'


class AnimeToshoScraper_Stremio(StremioAddonScraper):
    """AnimeTosho Stremio - Anime torrents"""
    NAME = 'AnimeTosho-Stremio'
    ADDON_URL = 'https://animetosho.strem.fun'
    
    def is_enabled(self):
        return ADDON.getSetting('animetosho_stremio_enabled') != 'false'


class LocalTVScraper(StremioAddonScraper):
    """LocalTV - Local TV channels (free)"""
    NAME = 'LocalTV'
    ADDON_URL = 'https://localtv.strem.fun'
    
    def is_enabled(self):
        return ADDON.getSetting('localtv_enabled') != 'false'


class PlutoTVScraper(StremioAddonScraper):
    """PlutoTV - Free ad-supported streaming"""
    NAME = 'PlutoTV-Stremio'
    ADDON_URL = 'https://plutotv.strem.fun'
    
    def is_enabled(self):
        return ADDON.getSetting('plutotv_stremio_enabled') != 'false'


class TubiScraper(StremioAddonScraper):
    """Tubi - Free streaming service"""
    NAME = 'Tubi-Stremio'
    ADDON_URL = 'https://tubi.strem.fun'
    
    def is_enabled(self):
        return ADDON.getSetting('tubi_stremio_enabled') != 'false'


# ==================== ALL STREMIO FREE SCRAPERS ====================

STREMIO_FREE_SCRAPERS = [
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
]
