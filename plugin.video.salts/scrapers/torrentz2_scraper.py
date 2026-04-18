"""
SALTS Scrapers - Torrentz2 Scraper (Meta-search)
Revived by zeus768 for Kodi 21+
"""
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils

class Torrentz2Scraper(TorrentScraper):
    """Torrentz2 meta-search scraper"""
    
    BASE_URL = 'https://torrentz2.nz'
    NAME = 'Torrentz2'
    
    # Mirror sites
    MIRRORS = [
        'https://torrentz2.nz',
        'https://torrentz2.eu',
        'https://torrentz.io'
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
        """Search Torrentz2"""
        results = []
        
        try:
            search_url = f'{self.BASE_URL}/search?q={quote_plus(query)}'
            
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find torrent rows
            rows = soup.select('div.results dl')
            
            for row in rows[:50]:
                try:
                    # Title
                    title_link = row.select_one('dt a')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    detail_url = urljoin(self.BASE_URL, title_link['href'])
                    
                    # Get hash from URL
                    hash_match = re.search(r'/([a-f0-9]{40})', detail_url)
                    if not hash_match:
                        continue
                    
                    info_hash = hash_match.group(1)
                    
                    # Details
                    dd = row.select_one('dd')
                    if dd:
                        dd_text = dd.get_text()
                        
                        # Size
                        size_match = re.search(r'([\d.]+\s*[KMGT]B)', dd_text, re.I)
                        size = size_match.group(1) if size_match else 'Unknown'
                        
                        # Seeds
                        seeds_match = re.search(r'(\d+)\s*seed', dd_text, re.I)
                        seeds = int(seeds_match.group(1)) if seeds_match else 0
                        
                        # Peers
                        peers_match = re.search(r'(\d+)\s*peer', dd_text, re.I)
                        peers = int(peers_match.group(1)) if peers_match else 0
                    else:
                        size = 'Unknown'
                        seeds = 0
                        peers = 0
                    
                    # Create magnet
                    magnet = self._make_magnet(info_hash, title)
                    
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
                        'host': 'Torrentz2'
                    })
                    
                except Exception as e:
                    log_utils.log_error(f'Torrentz2: Error parsing row: {e}')
                    continue
            
        except Exception as e:
            log_utils.log_error(f'Torrentz2: Search error: {e}')
        
        return results
