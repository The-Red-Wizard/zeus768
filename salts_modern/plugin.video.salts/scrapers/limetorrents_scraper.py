"""
SALTS Scrapers - LimeTorrents Scraper
Revived by zeus768 for Kodi 21+
"""
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils

class LimeTorrentsScraper(TorrentScraper):
    """LimeTorrents site scraper"""
    
    BASE_URL = 'https://www.limetorrents.lol'
    NAME = 'LimeTorrents'
    
    # Mirror sites
    MIRRORS = [
        'https://www.limetorrents.lol',
        'https://www.limetorrents.co',
        'https://www.limetorrents.info',
        'https://www.limetor.com'
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
        """Search LimeTorrents"""
        results = []
        
        try:
            # Category
            if media_type == 'movie':
                category = 'movies'
            elif media_type == 'tvshow':
                category = 'tv'
            else:
                category = 'all'
            
            search_url = f'{self.BASE_URL}/search/{category}/{quote_plus(query)}/'
            
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find torrent rows
            rows = soup.select('table.table2 tr')
            
            for row in rows[:50]:
                try:
                    # Skip header row
                    if row.select('th'):
                        continue
                    
                    cols = row.select('td')
                    if len(cols) < 5:
                        continue
                    
                    # Title
                    title_link = cols[0].select_one('a.cif')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    detail_url = urljoin(self.BASE_URL, title_link['href'])
                    
                    # Size
                    size = cols[2].get_text(strip=True) if len(cols) > 2 else 'Unknown'
                    
                    # Seeds
                    seeds_text = cols[3].get_text(strip=True) if len(cols) > 3 else '0'
                    seeds = int(re.sub(r'[^\d]', '', seeds_text) or 0)
                    
                    # Peers
                    peers_text = cols[4].get_text(strip=True) if len(cols) > 4 else '0'
                    peers = int(re.sub(r'[^\d]', '', peers_text) or 0)
                    
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
                        'host': 'LimeTorrents'
                    })
                    
                except Exception as e:
                    log_utils.log_error(f'LimeTorrents: Error parsing row: {e}')
                    continue
            
        except Exception as e:
            log_utils.log_error(f'LimeTorrents: Search error: {e}')
        
        return results
    
    def _get_magnet(self, detail_url):
        """Get magnet link from detail page"""
        try:
            html = self._http_get(detail_url, cache_limit=24)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            magnet_link = soup.select_one('a.cif[href^="magnet:"]')
            
            if magnet_link:
                return magnet_link['href']
            
            # Try alternative selector
            for link in soup.select('a[href^="magnet:"]'):
                return link['href']
            
        except Exception as e:
            log_utils.log_error(f'LimeTorrents: Error getting magnet: {e}')
        
        return None
