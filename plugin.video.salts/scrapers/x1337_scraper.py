"""
SALTS Scrapers - 1337x Torrent Scraper
Revived by zeus768 for Kodi 21+
"""
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils

class X1337Scraper(TorrentScraper):
    """1337x torrent site scraper"""
    
    BASE_URL = 'https://1337x.to'
    NAME = '1337x'
    
    # Mirror sites
    MIRRORS = [
        'https://1337x.to',
        'https://1337x.st',
        'https://x1337x.ws',
        'https://1337x.is',
        'https://1337x.gd'
    ]
    
    def __init__(self, timeout=30):
        super().__init__(timeout)
        self._find_working_domain()
    
    def _find_working_domain(self):
        """Find a working mirror"""
        for mirror in self.MIRRORS:
            try:
                response = self.session.get(mirror, timeout=5)
                if response.status_code == 200:
                    self.BASE_URL = mirror
                    return
            except:
                continue
    
    def search(self, query, media_type='movie'):
        """Search 1337x for torrents"""
        results = []
        
        try:
            # Category based on media type
            if media_type == 'movie':
                category = 'Movies'
            elif media_type == 'tvshow':
                category = 'TV'
            else:
                category = ''
            
            search_url = f'{self.BASE_URL}/search/{quote_plus(query)}/1/'
            if category:
                search_url = f'{self.BASE_URL}/category-search/{quote_plus(query)}/{category}/1/'
            
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find torrent rows
            rows = soup.select('table.table-list tbody tr')
            
            for row in rows[:50]:  # Limit to 50 results
                try:
                    # Title and link
                    title_cell = row.select_one('td.name')
                    if not title_cell:
                        continue
                    
                    link = title_cell.select_one('a:nth-of-type(2)')
                    if not link:
                        continue
                    
                    title = link.get_text(strip=True)
                    detail_url = urljoin(self.BASE_URL, link['href'])
                    
                    # Seeds and peers
                    seeds_cell = row.select_one('td.seeds')
                    peers_cell = row.select_one('td.leeches')
                    
                    seeds = int(seeds_cell.get_text(strip=True)) if seeds_cell else 0
                    peers = int(peers_cell.get_text(strip=True)) if peers_cell else 0
                    
                    # Size
                    size_cell = row.select('td.size')
                    size = size_cell[0].get_text(strip=True).split('\n')[0] if size_cell else 'Unknown'
                    
                    # Get magnet from detail page
                    magnet = self._get_magnet(detail_url)
                    if not magnet:
                        continue
                    
                    # Parse quality
                    quality = self._parse_quality(title)
                    
                    results.append({
                        'title': title,
                        'url': detail_url,
                        'magnet': magnet,
                        'quality': quality,
                        'size': size,
                        'seeds': seeds,
                        'peers': peers,
                        'host': '1337x'
                    })
                    
                except Exception as e:
                    log_utils.log_error(f'1337x: Error parsing row: {e}')
                    continue
            
        except Exception as e:
            log_utils.log_error(f'1337x: Search error: {e}')
        
        return results
    
    def _get_magnet(self, detail_url):
        """Get magnet link from detail page"""
        try:
            html = self._http_get(detail_url, cache_limit=24)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            magnet_link = soup.select_one('a[href^="magnet:"]')
            
            if magnet_link:
                return magnet_link['href']
            
        except Exception as e:
            log_utils.log_error(f'1337x: Error getting magnet: {e}')
        
        return None
