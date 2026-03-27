"""
SALTS Scrapers - Prowlarr Integration
Alternative to Jackett for unified torrent indexer access
Revived by zeus768 for Kodi 21+
"""
import re
import json
from urllib.parse import urljoin, quote_plus

import xbmcaddon

from .base_scraper import TorrentScraper
from salts_lib import log_utils

ADDON = xbmcaddon.Addon()

class ProwlarrScraper(TorrentScraper):
    """Prowlarr torrent indexer aggregator"""
    
    NAME = 'Prowlarr'
    
    def __init__(self, timeout=60):
        super().__init__(timeout)
        self.BASE_URL = ADDON.getSetting('prowlarr_url') or 'http://localhost:9696'
        self.api_key = ADDON.getSetting('prowlarr_api_key') or ''
    
    def is_enabled(self):
        """Check if Prowlarr is configured and enabled"""
        if not ADDON.getSetting('prowlarr_enabled') == 'true':
            return False
        
        if not self.BASE_URL or not self.api_key:
            return False
        
        return True
    
    def search(self, query, media_type='movie'):
        """Search all Prowlarr indexers"""
        results = []
        
        if not self.is_enabled():
            return results
        
        try:
            # Use Prowlarr's search endpoint
            search_url = f'{self.BASE_URL}/api/v1/search'
            
            headers = {
                'X-Api-Key': self.api_key,
                'Accept': 'application/json'
            }
            
            params = {
                'query': query,
                'type': 'search'
            }
            
            # Add category filter
            if media_type == 'movie':
                params['categories'] = '2000,2010,2020,2030,2040,2045,2050,2060'
            elif media_type == 'tvshow':
                params['categories'] = '5000,5010,5020,5030,5040,5045,5050,5060,5070,5080'
            
            response = self.session.get(search_url, params=params, headers=headers, timeout=self.timeout)
            
            if response.status_code != 200:
                log_utils.log_error(f'Prowlarr: HTTP {response.status_code}')
                return results
            
            torrents = response.json()
            
            for torrent in torrents[:100]:
                try:
                    title = torrent.get('title', '')
                    
                    # Magnet or download link
                    magnet = torrent.get('magnetUrl', '')
                    link = torrent.get('downloadUrl', '')
                    
                    if not magnet and not link:
                        continue
                    
                    # If no magnet, try to create from info hash
                    if not magnet:
                        info_hash = torrent.get('infoHash', '')
                        if info_hash:
                            magnet = self._make_magnet(info_hash, title)
                    
                    # Size
                    size_bytes = torrent.get('size', 0)
                    size = self._format_size(size_bytes) if size_bytes else 'Unknown'
                    
                    # Seeds and peers
                    seeds = torrent.get('seeders', 0) or 0
                    peers = torrent.get('leechers', 0) or 0
                    
                    # Indexer name
                    indexer = torrent.get('indexer', 'Unknown')
                    
                    # Parse quality
                    quality = self._parse_quality(title)
                    
                    results.append({
                        'title': f'[{indexer}] {title}',
                        'url': link or magnet,
                        'magnet': magnet,
                        'quality': quality,
                        'size': size,
                        'seeds': seeds,
                        'peers': peers,
                        'host': f'Prowlarr/{indexer}',
                        'indexer': indexer
                    })
                    
                except Exception as e:
                    log_utils.log_error(f'Prowlarr: Error parsing result: {e}')
                    continue
            
        except Exception as e:
            log_utils.log_error(f'Prowlarr: Search error: {e}')
        
        return results
    
    def _format_size(self, bytes_size):
        """Format bytes to human readable"""
        if not bytes_size:
            return 'Unknown'
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024:
                return f'{bytes_size:.1f} {unit}'
            bytes_size /= 1024
        return f'{bytes_size:.1f} PB'
    
    def test_connection(self):
        """Test Prowlarr connection"""
        try:
            url = f'{self.BASE_URL}/api/v1/health'
            headers = {'X-Api-Key': self.api_key}
            
            response = self.session.get(url, headers=headers, timeout=10)
            return response.status_code == 200
            
        except:
            return False
