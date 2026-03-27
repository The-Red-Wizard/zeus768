"""
SALTS Scrapers - Jackett Integration
Connects to Jackett server for unified torrent indexer access
Revived by zeus768 for Kodi 21+
"""
import re
import json
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, quote_plus

import xbmcaddon

from .base_scraper import TorrentScraper
from salts_lib import log_utils

ADDON = xbmcaddon.Addon()

class JackettScraper(TorrentScraper):
    """Jackett torrent indexer aggregator"""
    
    NAME = 'Jackett'
    
    def __init__(self, timeout=60):
        super().__init__(timeout)
        self.BASE_URL = ADDON.getSetting('jackett_url') or 'http://localhost:9117'
        self.api_key = ADDON.getSetting('jackett_api_key') or ''
    
    def is_enabled(self):
        """Check if Jackett is configured and enabled"""
        if not ADDON.getSetting('jackett_enabled') == 'true':
            return False
        
        if not self.BASE_URL or not self.api_key:
            return False
        
        return True
    
    def search(self, query, media_type='movie'):
        """Search all Jackett indexers"""
        results = []
        
        if not self.is_enabled():
            return results
        
        try:
            # Use Jackett's "all" indexer endpoint
            search_url = f'{self.BASE_URL}/api/v2.0/indexers/all/results'
            
            params = {
                'apikey': self.api_key,
                'Query': query
            }
            
            # Add category filter
            if media_type == 'movie':
                params['Category[]'] = [2000, 2010, 2020, 2030, 2040, 2045, 2050, 2060]  # Movies
            elif media_type == 'tvshow':
                params['Category[]'] = [5000, 5010, 5020, 5030, 5040, 5045, 5050, 5060, 5070, 5080]  # TV
            
            # Jackett returns JSON
            headers = {'Accept': 'application/json'}
            
            response = self.session.get(search_url, params=params, headers=headers, timeout=self.timeout)
            
            if response.status_code != 200:
                log_utils.log_error(f'Jackett: HTTP {response.status_code}')
                return results
            
            data = response.json()
            
            torrents = data.get('Results', [])
            
            for torrent in torrents[:100]:  # Limit results
                try:
                    title = torrent.get('Title', '')
                    
                    # Magnet or download link
                    magnet = torrent.get('MagnetUri', '')
                    link = torrent.get('Link', '')
                    
                    if not magnet and not link:
                        continue
                    
                    # If no magnet, try to get it from the link
                    if not magnet and link:
                        if link.startswith('magnet:'):
                            magnet = link
                        else:
                            # Download link - try to get magnet from info hash
                            info_hash = torrent.get('InfoHash', '')
                            if info_hash:
                                magnet = self._make_magnet(info_hash, title)
                    
                    # Size
                    size_bytes = torrent.get('Size', 0)
                    size = self._format_size(size_bytes) if size_bytes else 'Unknown'
                    
                    # Seeds and peers
                    seeds = torrent.get('Seeders', 0) or 0
                    peers = torrent.get('Peers', 0) or 0
                    
                    # Indexer name
                    indexer = torrent.get('Tracker', 'Unknown')
                    
                    # Parse quality
                    quality = self._parse_quality(title)
                    
                    # IMDB info if available
                    imdb = torrent.get('Imdb', '')
                    
                    results.append({
                        'title': f'[{indexer}] {title}',
                        'url': link or magnet,
                        'magnet': magnet,
                        'quality': quality,
                        'size': size,
                        'seeds': seeds,
                        'peers': peers,
                        'host': f'Jackett/{indexer}',
                        'indexer': indexer,
                        'imdb': imdb
                    })
                    
                except Exception as e:
                    log_utils.log_error(f'Jackett: Error parsing result: {e}')
                    continue
            
        except Exception as e:
            log_utils.log_error(f'Jackett: Search error: {e}')
        
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
    
    def get_indexers(self):
        """Get list of configured indexers"""
        if not self.is_enabled():
            return []
        
        try:
            url = f'{self.BASE_URL}/api/v2.0/indexers'
            params = {'apikey': self.api_key}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return []
            
            indexers = response.json()
            return [i for i in indexers if i.get('configured', False)]
            
        except Exception as e:
            log_utils.log_error(f'Jackett: Error getting indexers: {e}')
            return []
    
    def test_connection(self):
        """Test Jackett connection"""
        try:
            url = f'{self.BASE_URL}/api/v2.0/server/config'
            params = {'apikey': self.api_key}
            
            response = self.session.get(url, params=params, timeout=10)
            return response.status_code == 200
            
        except:
            return False
