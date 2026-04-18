"""
SALTS Scrapers - WatchSeries Scraper (Modernized)
Original by tknorris, Updated by zeus768 for Kodi 21+
"""
import re
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from salts_lib import log_utils

class WatchSeriesScraper(BaseScraper):
 """WatchSeries streaming site scraper - TV Shows"""
 
 BASE_URL = 'https://watchseries.id'
 NAME = 'WatchSeries'
 
 # Mirror sites
 MIRRORS = [
 'https://watchseries.id',
 'https://watchseries.ninja',
 'https://watchserieshd.tv',
 'https://watchseries.mn'
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
 """Search WatchSeries"""
 results = []
 
 # WatchSeries is primarily for TV shows
 if media_type == 'movie':
 return results
 
 try:
 search_url = f'{self.BASE_URL}/search/{quote_plus(query)}'
 
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 
 # Find results - adapt pattern to site structure
 for item in soup.select('.film-poster, .flw-item, .item'):
 try:
 link = item.select_one('a')
 if not link:
 continue
 
 title_el = item.select_one('.film-name, .title, h2, h3')
 title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
 
 # Extract year if present
 year_match = re.search(r'\((\d{4})\)', title)
 year = year_match.group(1) if year_match else ''
 title = re.sub(r'\s*\(\d{4}\)\s*', '', title)
 
 url = link.get('href', '')
 
 results.append({
 'title': title,
 'year': year,
 'url': url,
 'quality': 'HD',
 'host': 'WatchSeries'
 })
 
 except Exception as e:
 continue
 
 except Exception as e:
 log_utils.log_error(f'WatchSeries: Search error: {e}')
 
 return results
 
 def get_sources(self, url):
 """Get sources from a WatchSeries page"""
 sources = []
 
 try:
 full_url = urljoin(self.BASE_URL, url)
 html = self._http_get(full_url, cache_limit=0.5)
 
 if not html:
 return sources
 
 soup = BeautifulSoup(html, 'html.parser')
 
 # Find server links
 for server in soup.select('.server-item, .link-item, [data-id]'):
 try:
 link = server.select_one('a')
 if not link:
 link_url = server.get('data-link', server.get('data-url', ''))
 else:
 link_url = link.get('href', '')
 
 if not link_url:
 continue
 
 # Get host name
 host = server.get_text(strip=True) or urlparse(link_url).netloc
 
 sources.append({
 'url': link_url,
 'host': host,
 'quality': 'HD',
 'direct': False
 })
 
 except Exception as e:
 continue
 
 except Exception as e:
 log_utils.log_error(f'WatchSeries: Get sources error: {e}')
 
 return sources
