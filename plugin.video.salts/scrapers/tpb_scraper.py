"""
SALTS Scrapers - ThePirateBay Torrent Scraper
Revived by zeus768 for Kodi 21+
"""
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils

class TPBScraper(TorrentScraper):
    """ThePirateBay torrent site scraper"""
    
    BASE_URL = 'https://thepiratebay.org'
    API_URL = 'https://apibay.org'
    NAME = 'ThePirateBay'
    
    # Proxy/Mirror sites
    MIRRORS = [
        'https://thepiratebay.org',
        'https://thepiratebay10.org',
        'https://piratebay.live',
        'https://thepiratebay.zone',
        'https://tpb.party'
    ]
    
    API_MIRRORS = [
        'https://apibay.org',
        'https://piratebay.party/api'
    ]
    
    def __init__(self, timeout=30):
        super().__init__(timeout)
        self._find_working_api()
    
    def _find_working_api(self):
        """Find a working API endpoint"""
        for api in self.API_MIRRORS:
            try:
                response = self.session.get(f'{api}/q.php?q=test', timeout=5)
                if response.status_code == 200:
                    self.API_URL = api
                    return
            except:
                continue
    
    def search(self, query, media_type='movie'):
        """Search TPB for torrents"""
        results = []
        
        try:
            # Category based on media type
            if media_type == 'movie':
                cat = '201,207'  # Movies HD
            elif media_type == 'tvshow':
                cat = '205,208'  # TV HD
            else:
                cat = '200,201,205,207,208'  # Video
            
            # Use API
            api_url = f'{self.API_URL}/q.php'
            params = {
                'q': query,
                'cat': cat
            }
            
            html = self._http_get(api_url, params=params, cache_limit=1)
            if not html:
                return results
            
            try:
                data = json.loads(html)
            except:
                # Try HTML scraping as fallback
                return self._scrape_html(query, media_type)
            
            if not data or (len(data) == 1 and data[0].get('name') == 'No results'):
                return results
            
            for item in data[:50]:
                try:
                    name = item.get('name', '')
                    info_hash = item.get('info_hash', '')
                    size = int(item.get('size', 0))
                    seeds = int(item.get('seeders', 0))
                    peers = int(item.get('leechers', 0))
                    
                    if not name or not info_hash:
                        continue
                    
                    # Create magnet
                    magnet = self._make_magnet(info_hash, name)
                    
                    # Parse quality
                    quality = self._parse_quality(name)
                    
                    # Format size
                    size_str = self._format_size(size) if size else 'Unknown'
                    
                    results.append({
                        'title': name,
                        'url': f'{self.BASE_URL}/description.php?id={item.get("id", "")}',
                        'magnet': magnet,
                        'quality': quality,
                        'size': size_str,
                        'seeds': seeds,
                        'peers': peers,
                        'host': 'ThePirateBay'
                    })
                    
                except Exception as e:
                    log_utils.log_error(f'TPB: Error parsing item: {e}')
                    continue
            
        except Exception as e:
            log_utils.log_error(f'TPB: Search error: {e}')
        
        return results
    
    def _scrape_html(self, query, media_type):
        """Fallback HTML scraping"""
        results = []
        
        try:
            for mirror in self.MIRRORS:
                try:
                    search_url = f'{mirror}/search/{quote_plus(query)}/1/99/0'
                    html = self._http_get(search_url, cache_limit=1)
                    if html:
                        break
                except:
                    continue
            else:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('table#searchResult tr')
            
            for row in rows[:50]:
                try:
                    title_link = row.select_one('a.detLink')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    
                    magnet_link = row.select_one('a[href^="magnet:"]')
                    if not magnet_link:
                        continue
                    
                    magnet = magnet_link['href']
                    
                    # Parse details from font tag
                    details = row.select_one('font.detDesc')
                    size = 'Unknown'
                    if details:
                        size_match = re.search(r'Size\s+([\d.]+\s*\w+)', details.get_text())
                        if size_match:
                            size = size_match.group(1)
                    
                    # Seeds and peers
                    tds = row.select('td')
                    seeds = int(tds[-2].get_text(strip=True)) if len(tds) >= 2 else 0
                    peers = int(tds[-1].get_text(strip=True)) if len(tds) >= 1 else 0
                    
                    quality = self._parse_quality(title)
                    
                    results.append({
                        'title': title,
                        'url': '',
                        'magnet': magnet,
                        'quality': quality,
                        'size': size,
                        'seeds': seeds,
                        'peers': peers,
                        'host': 'ThePirateBay'
                    })
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            log_utils.log_error(f'TPB scrape error: {e}')
        
        return results
    
    def _format_size(self, bytes_size):
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024:
                return f'{bytes_size:.1f} {unit}'
            bytes_size /= 1024
        return f'{bytes_size:.1f} PB'
