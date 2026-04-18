"""
SALTS Scrapers - YTS (YIFY) Torrent Scraper
Revived by zeus768 for Kodi 21+
"""
import re
import json
from urllib.parse import quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils

class YTSScraper(TorrentScraper):
 """YTS/YIFY torrent site scraper - Movies only"""
 
 BASE_URL = 'https://yts.mx'
 API_URL = 'https://yts.mx/api/v2'
 NAME = 'YTS'
 
 # Mirror sites
 MIRRORS = [
 'https://yts.mx',
 'https://yts.rs',
 'https://yts.lt',
 'https://yts.am'
 ]
 
 def __init__(self, timeout=30):
 super().__init__(timeout)
 self._find_working_domain()
 
 def _find_working_domain(self):
 """Find a working mirror"""
 for mirror in self.MIRRORS:
 try:
 response = self.session.get(f'{mirror}/api/v2/list_movies.json', timeout=5)
 if response.status_code == 200:
 self.BASE_URL = mirror
 self.API_URL = f'{mirror}/api/v2'
 return
 except:
 continue
 
 def search(self, query, media_type='movie'):
 """Search YTS for movies"""
 results = []
 
 # YTS only has movies
 if media_type == 'tvshow':
 return results
 
 try:
 # Use API for searching
 api_url = f'{self.API_URL}/list_movies.json'
 params = {
 'query_term': query,
 'limit': 50,
 'sort_by': 'seeds'
 }
 
 html = self._http_get(api_url, params=params, cache_limit=1)
 if not html:
 return results
 
 data = json.loads(html)
 
 if data.get('status') != 'ok':
 return results
 
 movies = data.get('data', {}).get('movies', [])
 
 for movie in movies:
 try:
 title = movie.get('title_long', movie.get('title', ''))
 year = movie.get('year', '')
 imdb_code = movie.get('imdb_code', '')
 
 torrents = movie.get('torrents', [])
 
 for torrent in torrents:
 quality = torrent.get('quality', 'HD')
 size = torrent.get('size', 'Unknown')
 seeds = torrent.get('seeds', 0)
 peers = torrent.get('peers', 0)
 info_hash = torrent.get('hash', '')
 
 if not info_hash:
 continue
 
 # Create magnet
 magnet = self._make_magnet(info_hash, f'{title} [{quality}] [YTS.MX]')
 
 # Type (BluRay, WEB, etc.)
 torrent_type = torrent.get('type', '')
 
 display_title = f'{title} ({year}) [{quality}]'
 if torrent_type:
 display_title += f' [{torrent_type}]'
 
 results.append({
 'title': display_title,
 'url': f'{self.BASE_URL}/movie/{imdb_code}',
 'magnet': magnet,
 'quality': quality,
 'size': size,
 'seeds': seeds,
 'peers': peers,
 'host': 'YTS'
 })
 
 except Exception as e:
 log_utils.log_error(f'YTS: Error parsing movie: {e}')
 continue
 
 except Exception as e:
 log_utils.log_error(f'YTS: Search error: {e}')
 
 return results
