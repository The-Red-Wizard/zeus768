"""
SALTS Scrapers - EZTV Torrent Scraper
Revived by zeus768 for Kodi 21+
"""
import re
import json
from urllib.parse import quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils

class EZTVScraper(TorrentScraper):
 """EZTV torrent site scraper - TV Shows only"""
 
 BASE_URL = 'https://eztv.re'
 API_URL = 'https://eztv.re/api'
 NAME = 'EZTV'
 
 # Mirror sites
 MIRRORS = [
 'https://eztv.re',
 'https://eztv.wf',
 'https://eztv.tf',
 'https://eztv.yt'
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
 self.API_URL = f'{mirror}/api'
 return
 except:
 continue
 
 def search(self, query, media_type='movie'):
 """Search EZTV for TV shows"""
 results = []
 
 # EZTV only has TV shows
 if media_type == 'movie':
 return results
 
 try:
 # Parse show name and episode info from query
 # Expected format: "Show Name S01E02" or "Show Name"
 match = re.match(r'(.+?)\s*[Ss](\d+)[Ee](\d+)', query)
 
 if match:
 show_name = match.group(1).strip()
 season = match.group(2)
 episode = match.group(3)
 else:
 show_name = query
 season = None
 episode = None
 
 # Search using API
 api_url = f'{self.API_URL}/get-torrents'
 params = {'limit': 100}
 
 # Try to find IMDB ID first for better results
 # For now, we'll just get latest and filter
 
 html = self._http_get(api_url, params=params, cache_limit=0.5)
 if not html:
 return results
 
 data = json.loads(html)
 
 torrents = data.get('torrents', [])
 
 # Clean show name for matching
 clean_query = self._clean_title(show_name)
 
 for torrent in torrents:
 try:
 title = torrent.get('title', '')
 
 # Check if title matches
 if clean_query not in self._clean_title(title):
 continue
 
 # Check season/episode if specified
 if season and episode:
 pattern = f'[Ss]{int(season):02d}[Ee]{int(episode):02d}'
 if not re.search(pattern, title):
 continue
 
 info_hash = torrent.get('hash', '')
 size = torrent.get('size_bytes', 0)
 seeds = torrent.get('seeds', 0)
 peers = torrent.get('peers', 0)
 magnet_url = torrent.get('magnet_url', '')
 
 if not info_hash and not magnet_url:
 continue
 
 # Use provided magnet or create one
 if magnet_url:
 magnet = magnet_url
 else:
 magnet = self._make_magnet(info_hash, title)
 
 # Parse quality
 quality = self._parse_quality(title)
 
 # Format size
 if size:
 size = self._format_size(size)
 else:
 size = 'Unknown'
 
 results.append({
 'title': title,
 'url': torrent.get('torrent_url', ''),
 'magnet': magnet,
 'quality': quality,
 'size': size,
 'seeds': seeds,
 'peers': peers,
 'host': 'EZTV'
 })
 
 except Exception as e:
 log_utils.log_error(f'EZTV: Error parsing torrent: {e}')
 continue
 
 except Exception as e:
 log_utils.log_error(f'EZTV: Search error: {e}')
 
 return results
 
 def _format_size(self, bytes_size):
 """Format bytes to human readable"""
 for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
 if bytes_size < 1024:
 return f'{bytes_size:.1f} {unit}'
 bytes_size /= 1024
 return f'{bytes_size:.1f} PB'
