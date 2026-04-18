"""
SALTS Scrapers - RARBG/RarBG Mirror Scraper
Revived by zeus768 for Kodi 21+
"""
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils

class RARBGScraper(TorrentScraper):
    """RARBG mirror/clone site scraper (original RARBG is down)"""
    
    BASE_URL = 'https://rargb.to'
    NAME = 'RARBG'
    
    # RARBG clones/mirrors that still work
    MIRRORS = [
        'https://rargb.to',
        'https://rarbg.to',
        'https://proxyrarbg.org',
        'https://rarbgmirror.org'
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
        """Search RARBG mirrors"""
        results = []
        
        try:
            # Category based on media type
            if media_type == 'movie':
                category = 'movies'
            elif media_type == 'tvshow':
                category = 'tv'
            else:
                category = ''
            
            search_url = f'{self.BASE_URL}/search/?search={quote_plus(query)}'
            if category:
                search_url += f'&category={category}'
            
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find torrent rows (structure varies by mirror)
            rows = soup.select('table.lista2t tr.lista2')
            if not rows:
                rows = soup.select('tr.lista2')
            if not rows:
                rows = soup.select('table tr')[1:]  # Skip header
            
            for row in rows[:50]:
                try:
                    cols = row.select('td')
                    if len(cols) < 3:
                        continue
                    
                    # Title
                    title_link = row.select_one('a[href*="torrent/"]')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    detail_url = urljoin(self.BASE_URL, title_link['href'])
                    
                    # Try to find magnet directly
                    magnet_link = row.select_one('a[href^="magnet:"]')
                    if magnet_link:
                        magnet = magnet_link['href']
                    else:
                        # Get from detail page
                        magnet = self._get_magnet(detail_url)
                        if not magnet:
                            continue
                    
                    # Size
                    size = 'Unknown'
                    for col in cols:
                        text = col.get_text(strip=True)
                        if re.search(r'[\d.]+\s*(MB|GB|TB)', text, re.I):
                            size = text
                            break
                    
                    # Seeds and peers
                    seeds = 0
                    peers = 0
                    for col in cols[-3:]:
                        text = col.get_text(strip=True)
                        if text.isdigit():
                            if seeds == 0:
                                seeds = int(text)
                            else:
                                peers = int(text)
                                break
                    
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
                        'host': 'RARBG'
                    })
                    
                except Exception as e:
                    log_utils.log_error(f'RARBG: Error parsing row: {e}')
                    continue
            
        except Exception as e:
            log_utils.log_error(f'RARBG: Search error: {e}')
        
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
            log_utils.log_error(f'RARBG: Error getting magnet: {e}')
        
        return None
