"""
SALTS Scrapers - Stremio Addon Protocol Scrapers
Torrentio, MediaFusion, Comet, CyberFlix, Annatar, PeerFlix
zeus768 for Kodi 21+

Uses the Stremio addon stream API to fetch sources.
All Stremio addons follow: GET {base}/stream/{type}/{imdb_id}.json

Requires IMDB ID - converts from TMDB ID via TMDB API.
"""
import re
import json
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus

from scrapers.base_scraper import BaseScraper
from salts_lib import log_utils

TMDB_KEY = '8265bd1679663a7ea12ac168da84d2e8'
TMDB_BASE = 'https://api.themoviedb.org/3'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Modern browser headers that bypass most Cloudflare WAF rules used by
# elfhosted / strem.fun / *.strem.io.  Without these the new gateways
# return HTTP 403 (seen for Comet + MediaFusion in v2.9.17 logs).
_BROWSER_HEADERS = {
    'User-Agent': UA,
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'sec-ch-ua': '"Chromium";v="120", "Google Chrome";v="120", "Not?A_Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# Cache TMDB→IMDB lookups in memory for the session
_imdb_cache = {}


def _tmdb_to_imdb(tmdb_id, media_type='movie'):
    """Convert TMDB ID to IMDB ID via TMDB API external_ids endpoint."""
    if not tmdb_id:
        return None
    cache_key = f'{media_type}_{tmdb_id}'
    if cache_key in _imdb_cache:
        return _imdb_cache[cache_key]
    
    try:
        ep_type = 'movie' if media_type == 'movie' else 'tv'
        url = f'{TMDB_BASE}/{ep_type}/{tmdb_id}/external_ids?api_key={TMDB_KEY}'
        req = Request(url, headers={'User-Agent': UA})
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))
        imdb_id = data.get('imdb_id', '')
        if imdb_id:
            _imdb_cache[cache_key] = imdb_id
            return imdb_id
    except Exception as e:
        log_utils.log(f'TMDB→IMDB lookup failed for {tmdb_id}: {e}', xbmc.LOGDEBUG)
    return None


def _tmdb_search_imdb(title, year='', media_type='movie'):
    """Search TMDB by title/year to get IMDB ID."""
    try:
        ep_type = 'movie' if media_type == 'movie' else 'tv'
        params = f'api_key={TMDB_KEY}&query={quote_plus(title)}'
        if year:
            yr_key = 'year' if media_type == 'movie' else 'first_air_date_year'
            params += f'&{yr_key}={year}'
        url = f'{TMDB_BASE}/search/{ep_type}?{params}'
        req = Request(url, headers={'User-Agent': UA})
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))
        results = data.get('results', [])
        if results:
            found_id = results[0].get('id')
            if found_id:
                return _tmdb_to_imdb(str(found_id), media_type)
    except Exception as e:
        log_utils.log(f'TMDB search→IMDB failed for {title}: {e}', xbmc.LOGDEBUG)
    return None


class StremioBaseScraper(BaseScraper):
    """Base class for all Stremio addon protocol scrapers.
    
    Subclasses set BASE_URL and NAME. The stream API is:
    GET {BASE_URL}/stream/{type}/{id}.json
    
    where type = 'movie' or 'series'
    and id = IMDB ID (for series: {imdb_id}:{season}:{episode})
    """
    
    BASE_URL = ''
    # Optional list of fallback base URLs tried in order if the primary
    # returns 403 / 5xx / DNS error. Subclasses can override.
    FALLBACK_URLS = []
    # Settings key that, if set by the user, overrides BASE_URL with a
    # full Stremio configured manifest URL like:
    #   https://comet.elfhosted.com/eyJ...config.../
    # The trailing /stream/... path is appended automatically.
    URL_SETTING = ''
    NAME = 'Stremio'
    is_free = False  # Override in subclasses for free stream scrapers
    
    def __init__(self, timeout=15):
        super().__init__(timeout)
        # Refresh per-instance addon handle so changes in the running
        # session are picked up without a restart.
        self._addon = xbmcaddon.Addon()
        self._stremio_headers = dict(_BROWSER_HEADERS)
    
    def _resolved_base_urls(self):
        """Return ordered list of base URLs to try."""
        urls = []
        # 1) User-supplied URL from settings (if any)
        if self.URL_SETTING:
            try:
                user_url = self._addon.getSetting(self.URL_SETTING) or ''
            except Exception:
                user_url = ''
            user_url = user_url.strip().rstrip('/')
            if user_url and user_url.lower().startswith(('http://', 'https://')):
                urls.append(user_url)
        # 2) Hard-coded primary
        if self.BASE_URL and self.BASE_URL not in urls:
            urls.append(self.BASE_URL.rstrip('/'))
        # 3) Hard-coded fallbacks
        for u in (self.FALLBACK_URLS or []):
            u = u.rstrip('/')
            if u and u not in urls:
                urls.append(u)
        return urls
    
    def _get_stremio_streams(self, stremio_type, stremio_id):
        """Call the Stremio stream API on each base URL until one works."""
        last_err = None
        for base in self._resolved_base_urls():
            url = f'{base}/stream/{stremio_type}/{stremio_id}.json'
            try:
                req = Request(url, headers=self._stremio_headers)
                resp = urlopen(req, timeout=self.timeout)
                raw = resp.read()
                # Some gateways gzip silently
                if raw[:2] == b'\x1f\x8b':
                    import gzip
                    raw = gzip.decompress(raw)
                data = json.loads(raw.decode('utf-8', errors='replace'))
                return data.get('streams', [])
            except HTTPError as e:
                last_err = f'HTTP {e.code} for {url}'
                # 403 / 404 -> try next mirror; 5xx also retry
                if e.code in (401, 402):
                    break  # auth required, no mirror will help
                continue
            except Exception as e:
                last_err = f'{type(e).__name__} for {url}: {e}'
                continue
        if last_err:
            log_utils.log(f'{self.NAME}: API error - {last_err}', xbmc.LOGDEBUG)
        return []
    
    def _resolve_imdb_id(self, tmdb_id='', title='', year='', media_type='movie'):
        """Get IMDB ID from TMDB ID or title search."""
        imdb_id = None
        if tmdb_id:
            imdb_id = _tmdb_to_imdb(tmdb_id, media_type)
        if not imdb_id and title:
            imdb_id = _tmdb_search_imdb(title, year, media_type)
        return imdb_id
    
    def _parse_stremio_stream(self, stream):
        """Parse a single Stremio stream object into SALTS source format.
        
        Stremio streams can have:
        - url: direct stream URL
        - infoHash + fileIdx: torrent
        - name: e.g. "Torrentio\n4K" 
        - title: e.g. "Movie.2024.2160p.WEB-DL\n 150  8.5 GB ️ YTS"
        """
        result = {
            'title': '',
            'url': '',
            'magnet': '',
            'quality': 'SD',
            'host': self.NAME,
            'direct': False,
            'seeds': 0,
            'size': '',
        }
        
        name = stream.get('name', '')
        title_text = stream.get('title', stream.get('description', ''))
        
        # Parse quality from name/title
        full_text = f'{name} {title_text}'
        result['quality'] = self._parse_quality(full_text)
        
        # Parse seeds from title ( 150 or Seeds: 150)
        seeds_match = re.search(r'\s*(\d+)', title_text)
        if not seeds_match:
            seeds_match = re.search(r'[Ss]eeds?:?\s*(\d+)', title_text)
        if seeds_match:
            result['seeds'] = int(seeds_match.group(1))
        
        # Parse size from title ( 8.5 GB or Size: 8.5 GB)
        size_match = re.search(r'\s*([\d.]+\s*[KMGT]B)', title_text, re.IGNORECASE)
        if not size_match:
            size_match = re.search(r'[Ss]ize:?\s*([\d.]+\s*[KMGT]B)', title_text, re.IGNORECASE)
        if size_match:
            result['size'] = size_match.group(1)
        
        # Build display title
        clean_title = title_text.split('\n')[0] if title_text else name.replace('\n', ' ')
        clean_name = name.replace('\n', ' ').strip()
        result['title'] = f'[{clean_name}] {clean_title}' if clean_name else clean_title
        
        # Extract source (torrent or direct URL)
        info_hash = stream.get('infoHash', '')
        direct_url = stream.get('url', '')
        
        if info_hash:
            # Build magnet link
            dn = quote_plus(clean_title or 'Unknown')
            trackers = [
                'udp://tracker.opentrackr.org:1337/announce',
                'udp://open.stealth.si:80/announce',
                'udp://tracker.torrent.eu.org:451/announce',
                'udp://tracker.bittor.pw:1337/announce',
                'udp://public.popcorn-tracker.org:6969/announce',
                'udp://tracker.dler.org:6969/announce',
                'udp://exodus.desync.com:6969',
                'udp://open.demonii.com:1337/announce',
            ]
            tr_str = '&tr='.join([quote_plus(t) for t in trackers])
            result['magnet'] = f'magnet:?xt=urn:btih:{info_hash}&dn={dn}&tr={tr_str}'
            
            file_idx = stream.get('fileIdx')
            if file_idx is not None:
                result['magnet'] += f'&fileIndex={file_idx}'
            
            if not result['seeds']:
                result['seeds'] = 1  # Default for torrent sources
        
        elif direct_url:
            result['url'] = direct_url
            result['direct'] = True
            if not result['seeds']:
                result['seeds'] = 9999  # High priority for direct streams
        else:
            return None
        
        return result
    
    def search(self, query, media_type='movie', tmdb_id='', title='', year='',
               season='', episode='', **kwargs):
        """Search Stremio addon for streams."""
        sources = []
        
        # Parse title/year from query if not provided
        if not title:
            match = re.match(r'^(.+?)\s+(\d{4})$', query)
            if match:
                title = match.group(1).strip()
                year = match.group(2)
            else:
                match = re.match(r'^(.+?)\s+S(\d+)E(\d+)$', query, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    if not season:
                        season = match.group(2)
                    if not episode:
                        episode = match.group(3)
                else:
                    title = query
        
        # Resolve IMDB ID
        mt = 'movie' if media_type == 'movie' else 'tv'
        imdb_id = self._resolve_imdb_id(tmdb_id, title, year, mt)
        
        if not imdb_id:
            log_utils.log(f'{self.NAME}: No IMDB ID found for {title} ({year})', xbmc.LOGDEBUG)
            return sources
        
        # Build Stremio API call
        if media_type == 'movie':
            stremio_type = 'movie'
            stremio_id = imdb_id
        else:
            stremio_type = 'series'
            s = int(season) if season else 1
            e = int(episode) if episode else 1
            stremio_id = f'{imdb_id}:{s}:{e}'
        
        streams = self._get_stremio_streams(stremio_type, stremio_id)
        
        for stream in streams:
            try:
                source = self._parse_stremio_stream(stream)
                if source:
                    source['host'] = self.NAME
                    sources.append(source)
            except Exception as e:
                log_utils.log(f'{self.NAME}: Stream parse error: {e}', xbmc.LOGDEBUG)
                continue
        
        log_utils.log(f'{self.NAME}: Found {len(sources)} sources for {title}', xbmc.LOGINFO)
        return sources


# ======================================================================
# TORRENTIO - The biggest Stremio torrent aggregator
# Indexes: 1337x, ThePirateBay, RARBG, YTS, EZTV, TorrentGalaxy, etc.
# ======================================================================

class TorrentioScraper(StremioBaseScraper):
    """Torrentio - Stremio's #1 torrent aggregator.
    
    Aggregates from 20+ torrent indexers including 1337x, TPB, RARBG, YTS,
    EZTV, TorrentGalaxy, KickassTorrents, and more.
    """
    BASE_URL = 'https://torrentio.strem.fun'
    FALLBACK_URLS = [
        # Mirror that responds when strem.fun is rate-limiting.
        'https://torrentio.strem.fun/sort=qualitysize',
        'https://knightcrawler.elfhosted.com',
    ]
    URL_SETTING = 'torrentio_url'
    NAME = 'Torrentio'
    is_free = False
    
    def is_enabled(self):
        addon = xbmcaddon.Addon()
        return addon.getSetting('torrentio_enabled') != 'false'


# ======================================================================
# MEDIAFUSION - Community-driven Stremio aggregator
# Supports torrent + direct streams
# ======================================================================

class MediaFusionScraper(StremioBaseScraper):
    """MediaFusion - Community torrent/stream aggregator for Stremio.
    
    Open-source, supports Real-Debrid, AllDebrid, Premiumize, and direct streams.
    Indexes from multiple torrent trackers.
    """
    BASE_URL = 'https://mediafusion.elfhosted.com'
    FALLBACK_URLS = [
        'https://mediafusion.fun',
    ]
    URL_SETTING = 'mediafusion_url'
    NAME = 'MediaFusion'
    is_free = False
    
    def is_enabled(self):
        addon = xbmcaddon.Addon()
        return addon.getSetting('mediafusion_enabled') != 'false'


# ======================================================================
# COMET - Fast Stremio torrent aggregator
# ======================================================================

class CometScraper(StremioBaseScraper):
    """Comet - Fast Stremio torrent aggregator.
    
    Lightweight and fast, supports debrid services.
    """
    # Comet's elfhosted gateway now refuses the bare /stream path with 403.
    # The default-config public endpoint still works, and the open
    # comet-cf mirror is also accepted.
    BASE_URL = 'https://comet.elfhosted.com'
    FALLBACK_URLS = [
        'https://comet-cf.elfhosted.com',
        'https://comet.fast-stream.com',
    ]
    URL_SETTING = 'comet_url'
    NAME = 'Comet'
    is_free = False
    
    def is_enabled(self):
        addon = xbmcaddon.Addon()
        return addon.getSetting('comet_enabled') != 'false'


# ======================================================================
# CYBERFLIX - Free direct streams (no debrid required)
# ======================================================================

class CyberFlixScraper(StremioBaseScraper):
    """CyberFlix - Free direct streams via Stremio protocol.
    
    Provides free streams that play directly without debrid services.
    """
    BASE_URL = 'https://cyberflix.elfhosted.com'
    NAME = 'CyberFlix'
    is_free = True
    
    def is_enabled(self):
        addon = xbmcaddon.Addon()
        return addon.getSetting('cyberflix_enabled') != 'false'
    
    def _parse_stremio_stream(self, stream):
        """Override to mark all CyberFlix streams as free/direct."""
        result = super()._parse_stremio_stream(stream)
        if result:
            if result.get('url'):
                result['direct'] = True
                result['seeds'] = 9999
                result['title'] = f"[FREE] {result['title']}"
        return result


# ======================================================================
# ANNATAR - Jackett/Prowlarr integration for Stremio
# ======================================================================

class AnnatarScraper(StremioBaseScraper):
    """Annatar - Stremio addon that indexes via Jackett/Prowlarr.
    
    Uses your Jackett/Prowlarr instance to search all configured indexers.
    Requires self-hosting or a public instance.
    """
    BASE_URL = 'https://annatar.elfhosted.com'
    NAME = 'Annatar'
    is_free = False
    
    def is_enabled(self):
        addon = xbmcaddon.Addon()
        return addon.getSetting('annatar_enabled') != 'false'


# ======================================================================
# PEERFLIX - Free P2P streams
# ======================================================================

class PeerFlixScraper(StremioBaseScraper):
    """PeerFlix - Free peer-to-peer streams.
    
    Uses P2P technology for direct playback. No debrid required.
    """
    BASE_URL = 'https://peerflix.elfhosted.com'
    NAME = 'PeerFlix'
    is_free = True
    
    def is_enabled(self):
        addon = xbmcaddon.Addon()
        return addon.getSetting('peerflix_enabled') != 'false'
    
    def _parse_stremio_stream(self, stream):
        """Override to mark PeerFlix streams as free."""
        result = super()._parse_stremio_stream(stream)
        if result and result.get('url'):
            result['direct'] = True
            result['seeds'] = 9998
            result['title'] = f"[FREE] {result['title']}"
        return result


# ======================================================================
# EASYNEWS - Usenet streams (for usenet subscribers)
# ======================================================================

class EasyNewsScraper(StremioBaseScraper):
    """EasyNews+ - Stremio addon for Usenet streams.
    
    Provides direct streams from EasyNews Usenet service.
    Requires EasyNews subscription.
    """
    BASE_URL = 'https://easynews.elfhosted.com'
    NAME = 'EasyNews+'
    is_free = False
    
    def is_enabled(self):
        addon = xbmcaddon.Addon()
        return addon.getSetting('easynews_enabled') != 'false'


# All Stremio scraper classes
ALL_STREMIO_SCRAPERS = [
    TorrentioScraper,
    MediaFusionScraper,
    CometScraper,
    CyberFlixScraper,
    AnnatarScraper,
    PeerFlixScraper,
    EasyNewsScraper,
]
