"""
SALTS Scrapers - Torrent API Scraper
Uses torrent-api.theaudiodb.com or similar torrent APIs
Revived by zeus768 for Kodi 21+
"""
import re
import json
from urllib.parse import quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils

class TorrentAPIScraper(TorrentScraper):
    """Torrent API aggregator scraper"""
    
    BASE_URL = 'https://torrent-api.theaudiodb.com'
    NAME = 'TorrentAPI'
    
    # Alternative API endpoints
    APIS = [
        'https://torrent-api.theaudiodb.com',
        'https://torrentapi.org/pubapi_v2.php'  # RARBG-style API
    ]
    
    def search(self, query, media_type='movie'):
        """Search torrent APIs"""
        results = []
        
        # Try multiple API methods
        results.extend(self._search_api1(query, media_type))
        
        return results
    
    def _search_api1(self, query, media_type):
        """Search using first API format"""
        results = []
        
        try:
            # Format varies by API
            api_url = f'{self.BASE_URL}/api/v1/search'
            
            params = {
                'query': query,
                'category': 'movies' if media_type == 'movie' else 'tv'
            }
            
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            
            if response.status_code != 200:
                return results
            
            data = response.json()
            
            torrents = data.get('results', data.get('torrents', []))
            
            for torrent in torrents[:50]:
                try:
                    title = torrent.get('title', torrent.get('name', ''))
                    magnet = torrent.get('magnet', torrent.get('magnet_url', ''))
                    info_hash = torrent.get('hash', torrent.get('info_hash', ''))
                    
                    if not magnet and info_hash:
                        magnet = self._make_magnet(info_hash, title)
                    
                    if not magnet:
                        continue
                    
                    size = torrent.get('size', torrent.get('size_bytes', 'Unknown'))
                    if isinstance(size, int):
                        size = self._format_size(size)
                    
                    seeds = torrent.get('seeders', torrent.get('seeds', 0))
                    peers = torrent.get('leechers', torrent.get('peers', 0))
                    
                    quality = self._parse_quality(title)
                    
                    results.append({
                        'title': title,
                        'url': torrent.get('url', ''),
                        'magnet': magnet,
                        'quality': quality,
                        'size': str(size),
                        'seeds': int(seeds) if seeds else 0,
                        'peers': int(peers) if peers else 0,
                        'host': 'TorrentAPI'
                    })
                    
                except Exception as e:
                    log_utils.log_error(f'TorrentAPI: Error parsing: {e}')
                    continue
            
        except Exception as e:
            log_utils.log_error(f'TorrentAPI: Search error: {e}')
        
        return results
    
    def _format_size(self, bytes_size):
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024:
                return f'{bytes_size:.1f} {unit}'
            bytes_size /= 1024
        return f'{bytes_size:.1f} PB'
