"""
SALTS Scrapers - PrimeWire Scraper (Modernized)
Original by tknorris, Updated by zeus768 for Kodi 21+
"""
import re
import base64
from urllib.parse import urljoin, quote_plus, urlparse
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from salts_lib import log_utils
from salts_lib.constants import VIDEO_TYPES, QUALITIES

QUALITY_MAP = {'DVD': 'HD', 'TS': 'SD', 'CAM': 'CAM', 'HD': '720p'}

class PrimeWireScraper(BaseScraper):
    """PrimeWire streaming site scraper"""
    
    BASE_URL = 'https://www.primewire.tf'
    NAME = 'PrimeWire'
    
    # Mirror sites
    MIRRORS = [
        'https://www.primewire.tf',
        'https://www.primewire.li',
        'https://www.primewire.ag',
        'https://primewire.mx'
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
        """Search PrimeWire"""
        results = []
        
        try:
            # Get search key first
            html = self._http_get(self.BASE_URL, cache_limit=0)
            key_match = re.search(r'name="key"\s+value="([^"]+)"', html)
            key = key_match.group(1) if key_match else ''
            
            search_url = f'{self.BASE_URL}/index.php'
            params = {
                'search_keywords': query,
                'key': key,
                'search_section': '1' if media_type == 'movie' else '2'
            }
            
            html = self._http_get(search_url, params=params, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find results
            for item in soup.select('.index_item'):
                try:
                    link = item.select_one('a[href*="/watch-"]')
                    if not link:
                        continue
                    
                    title_text = link.get('title', '') or link.get_text(strip=True)
                    # Parse title and year
                    match = re.match(r'Watch\s+(.+?)(?:\s*\((\d{4})\))?$', title_text)
                    if match:
                        title = match.group(1).strip()
                        year = match.group(2) or ''
                    else:
                        title = title_text.replace('Watch ', '')
                        year = ''
                    
                    url = link['href']
                    
                    results.append({
                        'title': title,
                        'year': year,
                        'url': url,
                        'quality': 'HD',
                        'host': 'PrimeWire'
                    })
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            log_utils.log_error(f'PrimeWire: Search error: {e}')
        
        return results
    
    def get_sources(self, url):
        """Get sources from a PrimeWire page"""
        sources = []
        
        try:
            full_url = urljoin(self.BASE_URL, url)
            html = self._http_get(full_url, cache_limit=0.5)
            
            if not html:
                return sources
            
            # Pattern for source extraction
            pattern = r'url=([^&]+)&(?:amp;)?domain=([^&]+)'
            
            for match in re.finditer(pattern, html):
                try:
                    encoded_url, encoded_host = match.groups()
                    
                    # Decode base64
                    try:
                        source_url = base64.b64decode(encoded_url).decode('utf-8')
                        host = base64.b64decode(encoded_host).decode('utf-8').lower()
                    except:
                        continue
                    
                    # Get quality from context
                    quality = 'SD'
                    for q_name, q_val in QUALITY_MAP.items():
                        if q_name.lower() in html[max(0, match.start()-100):match.start()].lower():
                            quality = q_val
                            break
                    
                    sources.append({
                        'url': source_url,
                        'host': host,
                        'quality': quality,
                        'direct': False
                    })
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            log_utils.log_error(f'PrimeWire: Get sources error: {e}')
        
        return sources
