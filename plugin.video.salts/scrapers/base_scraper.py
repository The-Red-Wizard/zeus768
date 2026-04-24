"""
SALTS Scrapers - Base Scraper Class
Revived by zeus768 for Kodi 21+
Uses native urllib (no external requests module)
"""
import abc
import re
import json
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
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
        self._headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
    
    @classmethod
    def get_name(cls):
        """Get scraper name"""
        return cls.NAME
    
    def is_enabled(self):
        """Check if scraper is enabled"""
        setting_id = f'{self.NAME.lower().replace(" ", "_")}_enabled'
        return ADDON.getSetting(setting_id) != 'false'
    
    def _http_get(self, url, params=None, data=None, headers=None, cache_limit=8):
        """Make HTTP GET/POST request with caching using native urllib"""
        cache_url = url + str(params or {})
        
        # Check cache
        _, cached = self.db.get_cached_url(cache_url, cache_limit)
        if cached:
            return cached
        
        try:
            # Build URL with params
            request_url = url
            if params:
                query_str = '&'.join(f'{k}={quote_plus(str(v))}' for k, v in params.items())
                separator = '&' if '?' in url else '?'
                request_url = f'{url}{separator}{query_str}'
            
            # Build headers
            hdrs = self._headers.copy()
            if headers:
                hdrs.update(headers)
            
            # Build request
            post_data = None
            if data:
                if isinstance(data, dict):
                    post_data = '&'.join(f'{k}={quote_plus(str(v))}' for k, v in data.items()).encode('utf-8')
                    hdrs['Content-Type'] = 'application/x-www-form-urlencoded'
                elif isinstance(data, str):
                    post_data = data.encode('utf-8')
                elif isinstance(data, bytes):
                    post_data = data
            
            req = Request(request_url, data=post_data, headers=hdrs)
            resp = urlopen(req, timeout=self.timeout)
            html = resp.read().decode('utf-8', errors='replace')
            
            # Cache the response
            self.db.cache_url(cache_url, html)
            
            return html
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: HTTP error for {url}: {e}')
            return ''
    
    def _http_get_json(self, url, params=None, headers=None, cache_limit=8):
        """Make HTTP GET and return parsed JSON"""
        html = self._http_get(url, params=params, headers=headers, cache_limit=cache_limit)
        if html:
            try:
                return json.loads(html)
            except Exception:
                pass
        return None
    
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
        
        size_str = size_str.strip().upper()
        
        if re.match(r'[\d.]+\s*(B|KB|MB|GB|TB)', size_str):
            return size_str
        
        return size_str
    
    def _extract_hash(self, text):
        """Extract info hash from magnet or text"""
        match = re.search(r'btih:([a-fA-F0-9]{40})', text)
        if match:
            return match.group(1).lower()
        
        match = re.search(r'btih:([a-zA-Z2-7]{32})', text)
        if match:
            return match.group(1).lower()
        
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
        """Search for content. Returns list of result dicts."""
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
