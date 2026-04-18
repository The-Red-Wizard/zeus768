"""
SALTS Scrapers - TorrentGalaxy Scraper
Revived by zeus768 for Kodi 21+
"""
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils

class TorrentGalaxyScraper(TorrentScraper):
 """TorrentGalaxy torrent site scraper"""
 
 BASE_URL = 'https://torrentgalaxy.to'
 NAME = 'TorrentGalaxy'
 
 # Mirror sites
 MIRRORS = [
 'https://torrentgalaxy.to',
 'https://torrentgalaxy.mx',
 'https://tgx.rs'
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
 """Search TorrentGalaxy for torrents"""
 results = []
 
 try:
 # Category based on media type
 if media_type == 'movie':
 category = 'c3=1&' # Movies
 elif media_type == 'tvshow':
 category = 'c41=1&' # TV
 else:
 category = ''
 
 search_url = f'{self.BASE_URL}/torrents.php?{category}search={quote_plus(query)}'
 
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 
 # Find torrent rows
 rows = soup.select('div.tgxtablerow')
 
 for row in rows[:50]:
 try:
 # Title and link
 title_link = row.select_one('a.txlight')
 if not title_link:
 continue
 
 title = title_link.get('title', '') or title_link.get_text(strip=True)
 detail_url = urljoin(self.BASE_URL, title_link['href'])
 
 # Magnet link
 magnet_link = row.select_one('a[href^="magnet:"]')
 if not magnet_link:
 continue
 
 magnet = magnet_link['href']
 
 # Seeds and peers
 spans = row.select('span')
 seeds = 0
 peers = 0
 
 for span in spans:
 text = span.get_text(strip=True)
 if 'Seeders' in span.get('title', ''):
 seeds = int(text) if text.isdigit() else 0
 elif 'Leechers' in span.get('title', ''):
 peers = int(text) if text.isdigit() else 0
 
 # Size
 size_span = row.select_one('span.badge-secondary')
 size = size_span.get_text(strip=True) if size_span else 'Unknown'
 
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
 'host': 'TorrentGalaxy'
 })
 
 except Exception as e:
 log_utils.log_error(f'TorrentGalaxy: Error parsing row: {e}')
 continue
 
 except Exception as e:
 log_utils.log_error(f'TorrentGalaxy: Search error: {e}')
 
 return results
