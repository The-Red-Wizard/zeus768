"""
SALTS Scrapers - Movie4K/KinoX Scraper (Modernized)
Original by tknorris, Updated by zeus768 for Kodi 21+
"""
import re
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from salts_lib import log_utils
from salts_lib.constants import QUALITIES

QUALITY_MAP = {
 '0': 'CAM', '1': 'TS', '2': 'SD', '3': 'SD', '4': '720p', '5': '1080p'
}

class Movie4KScraper(BaseScraper):
 """Movie4K/KinoX streaming site scraper"""
 
 BASE_URL = 'https://movie4k.to'
 NAME = 'Movie4K'
 
 # Mirror sites
 MIRRORS = [
 'https://movie4k.to',
 'https://movie4k.st',
 'https://movie4k.run',
 'https://kinox.to'
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
 """Search Movie4K"""
 results = []
 
 try:
 search_url = f'{self.BASE_URL}/movies.php'
 params = {
 'list': 'search',
 'search': query
 }
 
 cookies = {'onlylanguage': 'en', 'lang': 'en'}
 
 html = self._http_get(search_url, params=params, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 
 # Find results
 for row in soup.select('#tablemoviesindex tr, .movie-item'):
 try:
 link = row.select_one('a[href*="movie"], a[href*="film"]')
 if not link:
 continue
 
 title = link.get_text(strip=True)
 url = link.get('href', '')
 
 # Check if TV show vs movie
 is_tvshow = '(TVshow)' in title or 'serie' in url.lower()
 if media_type == 'movie' and is_tvshow:
 continue
 if media_type == 'tvshow' and not is_tvshow:
 continue
 
 title = title.replace('(TVshow)', '').strip()
 
 # Try to extract year
 year_match = re.search(r'(\d{4})', str(row))
 year = year_match.group(1) if year_match else ''
 
 results.append({
 'title': title,
 'year': year,
 'url': url,
 'quality': 'HD',
 'host': 'Movie4K'
 })
 
 except Exception as e:
 continue
 
 except Exception as e:
 log_utils.log_error(f'Movie4K: Search error: {e}')
 
 return results
 
 def get_sources(self, url):
 """Get sources from a Movie4K page"""
 sources = []
 
 try:
 full_url = urljoin(self.BASE_URL, url)
 html = self._http_get(full_url, cache_limit=0.5)
 
 if not html:
 return sources
 
 # Pattern for link extraction
 pattern = r'links\[\d+\].*?href=\\"([^\\]+).*?alt=\\"([^\s]+)'
 
 for match in re.finditer(pattern, html):
 try:
 link_url, host = match.groups()
 
 if not link_url.startswith('/'):
 link_url = '/' + link_url
 
 # Check quality from smiley
 quality = 'SD'
 smiley_match = re.search(r'/smileys/(\d+)\.gif', html[match.start():match.start()+500])
 if smiley_match:
 quality = QUALITY_MAP.get(smiley_match.group(1), 'SD')
 
 sources.append({
 'url': urljoin(self.BASE_URL, link_url),
 'host': host.lower(),
 'quality': quality,
 'direct': False
 })
 
 except Exception as e:
 continue
 
 except Exception as e:
 log_utils.log_error(f'Movie4K: Get sources error: {e}')
 
 return sources
