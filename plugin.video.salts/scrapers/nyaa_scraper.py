"""
SALTS Scrapers - Nyaa Torrent Scraper (Anime)
Revived by zeus768 for Kodi 21+
"""
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils

class NyaaScraper(TorrentScraper):
 """Nyaa torrent site scraper - Anime focused"""
 
 BASE_URL = 'https://nyaa.si'
 NAME = 'Nyaa'
 
 def search(self, query, media_type='movie'):
 """Search Nyaa for anime torrents"""
 results = []
 
 try:
 # Category: Anime
 search_url = f'{self.BASE_URL}/?f=0&c=1_2&q={quote_plus(query)}&s=seeders&o=desc'
 
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 
 # Find torrent rows
 rows = soup.select('table.torrent-list tbody tr')
 
 for row in rows[:50]:
 try:
 # Category and title
 cols = row.select('td')
 if len(cols) < 6:
 continue
 
 # Title (column 2)
 title_cell = cols[1]
 title_link = title_cell.select_one('a:not(.comments)')
 if not title_link:
 continue
 
 title = title_link.get('title', '') or title_link.get_text(strip=True)
 detail_url = urljoin(self.BASE_URL, title_link['href'])
 
 # Links (column 3)
 links_cell = cols[2]
 magnet_link = links_cell.select_one('a[href^="magnet:"]')
 
 if not magnet_link:
 continue
 
 magnet = magnet_link['href']
 
 # Size (column 4)
 size = cols[3].get_text(strip=True) if len(cols) > 3 else 'Unknown'
 
 # Seeds (column 6)
 seeds = int(cols[5].get_text(strip=True)) if len(cols) > 5 else 0
 
 # Peers (column 7)
 peers = int(cols[6].get_text(strip=True)) if len(cols) > 6 else 0
 
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
 'host': 'Nyaa'
 })
 
 except Exception as e:
 log_utils.log_error(f'Nyaa: Error parsing row: {e}')
 continue
 
 except Exception as e:
 log_utils.log_error(f'Nyaa: Search error: {e}')
 
 return results
