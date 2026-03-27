"""
SALTS Scrapers - Base Scraper Class
Revived by zeus768 for Kodi 21+
"""
import abc
import re
import requests
import xbmc
import xbmcaddon
from urllib.parse import urljoin, urlparse, quote_plus

from salts_lib import log_utils
from salts_lib.db_utils import DB_Connection
from salts_lib.constants import USER_AGENT, DEFAULT_TIMEOUT, QUALITY_PATTERNS

ADDON = xbmcaddon.Addon()

class BaseScraper(abc.ABC):
    """Abstract base class for all scrapers"""
    
    BASE_URL = ''
    NAME = 'Base'
    
    def __init__(self, timeout=DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.db = DB_Connection()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        })
    
    @classmethod
    def get_name(cls):
        """Get scraper name"""
        return cls.NAME
    
    def is_enabled(self):
        """Check if scraper is enabled"""
        setting_id = f'{self.NAME.lower().replace(" ", "_")}_enabled'
        return ADDON.getSetting(setting_id) != 'false'
    
    def _http_get(self, url, params=None, data=None, headers=None, cache_limit=8):
        """Make HTTP GET request with caching"""
        cache_url = url + str(params or {})
        
        # Check cache
        _, cached = self.db.get_cached_url(cache_url, cache_limit)
        if cached:
            return cached
        
        try:
            if headers:
                self.session.headers.update(headers)
            
            if data:
                response = self.session.post(url, params=params, data=data, timeout=self.timeout)
            else:
                response = self.session.get(url, params=params, timeout=self.timeout)
            
            response.raise_for_status()
            html = response.text
            
            # Cache the response
            self.db.cache_url(cache_url, html)
            
            return html
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: HTTP error for {url}: {e}')
            return ''
    
    def _parse_quality(self, text):
        """Parse quality from text"""
        text = text.lower()
        
        for quality, patterns in QUALITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return quality
        
        return 'SD'
    
    def _parse_size(self, size_str):
        """Parse size string to formatted size"""
        if not size_str:
            return 'Unknown'
        
        # Clean up the string
        size_str = size_str.strip().upper()
        
        # Check if already formatted
        if re.match(r'[\d.]+\s*(B|KB|MB|GB|TB)', size_str):
            return size_str
        
        return size_str
    
    def _extract_hash(self, text):
        """Extract info hash from magnet or text"""
        # Try to find hash in magnet link
        match = re.search(r'btih:([a-fA-F0-9]{40})', text)
        if match:
            return match.group(1).lower()
        
        # Try 32-character base32 hash
        match = re.search(r'btih:([a-zA-Z2-7]{32})', text)
        if match:
            return match.group(1).lower()
        
        # Just a hash string
        match = re.search(r'\b([a-fA-F0-9]{40})\b', text)
        if match:
            return match.group(1).lower()
        
        return None
    
    def _clean_title(self, title):
        """Clean title for comparison"""
        title = title.lower()
        title = re.sub(r'[^\w\s]', '', title)
        title = ' '.join(title.split())
        return title
    
    @abc.abstractmethod
    def search(self, query, media_type='movie'):
        """
        Search for content
        
        Args:
            query: Search query
            media_type: 'movie', 'tvshow', or 'all'
        
        Returns:
            List of result dicts with keys:
            - title: Display title
            - url: URL or magnet link
            - magnet: Magnet link (if available)
            - quality: Quality string
            - size: Size string
            - seeds: Number of seeds
            - peers: Number of peers
        """
        raise NotImplementedError
    
    def get_movie_sources(self, title, year=''):
        """Get sources for a movie"""
        query = title
        if year:
            query = f'{title} {year}'
        return self.search(query, 'movie')
    
    def get_episode_sources(self, title, year, season, episode):
        """Get sources for a TV episode"""
        query = f'{title} S{int(season):02d}E{int(episode):02d}'
        return self.search(query, 'tvshow')


class TorrentScraper(BaseScraper):
    """Base class for torrent site scrapers"""
    
    def _make_magnet(self, info_hash, name):
        """Create magnet link from hash and name"""
        trackers = [
            'udp://tracker.opentrackr.org:1337/announce',
            'udp://open.stealth.si:80/announce',
            'udp://tracker.torrent.eu.org:451/announce',
            'udp://tracker.bittor.pw:1337/announce',
            'udp://public.popcorn-tracker.org:6969/announce',
            'udp://tracker.dler.org:6969/announce',
            'udp://exodus.desync.com:6969',
            'udp://open.demonii.com:1337/announce'
        ]
        
        tracker_str = '&tr='.join([quote_plus(t) for t in trackers])
        return f'magnet:?xt=urn:btih:{info_hash}&dn={quote_plus(name)}&tr={tracker_str}'
