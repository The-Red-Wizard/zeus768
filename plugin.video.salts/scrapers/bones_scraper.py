"""
Bones Scraper - Direct stream links provider
"""
import re
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from .base_scraper import BaseScraper

ADDON = xbmcaddon.Addon()
SOURCE_URL = 'https://thechains24.com/ABSOLUTION/MOVIES/newm.NEW.txt'

# Module-level cache
_bones_cache = []
_bones_cache_time = 0


class BonesScraper(BaseScraper):
 NAME = 'Bones'
 BASE_URL = 'https://thechains24.com'

 def is_enabled(self):
 return True # Always enabled as a direct link provider

 def _fetch_catalog(self):
 global _bones_cache, _bones_cache_time
 import time

 # Cache for 1 hour
 if _bones_cache and (time.time() - _bones_cache_time) < 3600:
 return _bones_cache

 try:
 req = Request(SOURCE_URL, headers={'User-Agent': 'SALTS Kodi Addon'})
 response = urlopen(req, timeout=15)
 raw = response.read().decode('utf-8', errors='ignore')
 except Exception as e:
 xbmc.log(f'Bones: Fetch failed: {e}', xbmc.LOGWARNING)
 return []

 movies = []
 # Split raw text by streamtape/luluvid URLs
 parts = re.split(r'(https?://(?:streamtape\.com|luluvid\.com)/[^\s]+)', raw)

 i = 0
 while i < len(parts):
 chunk = parts[i].strip()
 if not chunk or chunk.startswith('http'):
 i += 1
 continue

 # Extract IMDB ID if present
 imdb_match = re.search(r'(tt\d{7,})', chunk)
 imdb_id = imdb_match.group(1) if imdb_match else ''

 # Clean title
 title_text = chunk
 if imdb_id:
 title_text = title_text[:title_text.rfind(imdb_id)].strip()
 title_text = re.sub(r'https?://[^\s]+', '', title_text).strip()
 lines = [l.strip() for l in title_text.split('\n') if l.strip()]
 title = lines[-1] if lines else ''

 if not title or len(title) < 2:
 i += 1
 continue

 # Next part should be stream URL
 stream_url = parts[i + 1].strip() if i + 1 < len(parts) else ''
 if not stream_url or not stream_url.startswith('http'):
 i += 1
 continue

 # Gather remaining text for images
 remainder = parts[i + 2] if i + 2 < len(parts) else ''

 # Check for second stream URL
 stream_url_2 = ''
 if i + 3 < len(parts) and re.match(r'https?://(?:streamtape|luluvid)', parts[i + 3]):
 stream_url_2 = parts[i + 3].strip()
 remainder = parts[i + 4] if i + 4 < len(parts) else ''
 i += 2

 # Extract images
 image_urls = re.findall(
 r'(https?://(?:image\.tmdb\.org|www\.themoviedb\.org|m\.media-amazon\.com)/[^\s]+)',
 remainder
 )
 poster = (image_urls[0] if image_urls else '').replace('\\_', '_')
 backdrop = (image_urls[1] if len(image_urls) > 1 else poster).replace('\\_', '_')

 # Description
 desc = re.sub(r'https?://[^\s]+', '', remainder).strip()
 desc_lines = [l.strip() for l in desc.split('\n') if l.strip()]
 description = desc_lines[0] if desc_lines else ''

 movies.append({
 'title': title,
 'stream_url': stream_url,
 'stream_url_2': stream_url_2,
 'description': description,
 'poster': poster,
 'backdrop': backdrop,
 'imdb_id': imdb_id,
 })

 i += 2

 xbmc.log(f'Bones: Parsed {len(movies)} movies', xbmc.LOGINFO)
 _bones_cache = movies
 _bones_cache_time = time.time()
 return movies

 def search(self, video_type, title, year, season='', episode=''):
 """Search Bones for matching movie. Returns SALTS-format source list."""
 if video_type != 'movie':
 return []

 catalog = self._fetch_catalog()
 query = title.lower().strip()
 query_no_year = re.sub(r'\s*\(?\d{4}\)?\s*$', '', query).strip()

 results = []
 for movie in catalog:
 mtitle = movie['title'].lower()
 if query_no_year in mtitle or mtitle in query_no_year:
 quality = '720p'
 if '1080p' in movie['stream_url'].lower():
 quality = '1080p'
 elif '4k' in movie['stream_url'].lower() or '2160' in movie['stream_url'].lower():
 quality = '4K'

 results.append({
 'multi-part': False,
 'class': self,
 'host': 'Bones',
 'quality': quality,
 'label': f"[Bones] {movie['title']}",
 'rating': None,
 'views': None,
 'direct': True,
 'url': movie['stream_url'],
 'is_free_link': True,
 'source': 'Bones',
 })

 # Add second URL if available
 if movie.get('stream_url_2'):
 results.append({
 'multi-part': False,
 'class': self,
 'host': 'Bones (Mirror)',
 'quality': quality,
 'label': f"[Bones Mirror] {movie['title']}",
 'rating': None,
 'views': None,
 'direct': True,
 'url': movie['stream_url_2'],
 'is_free_link': True,
 'source': 'Bones',
 })
 return results

 def get_catalog(self):
 """Get full Bones catalog for browsing"""
 return self._fetch_catalog()
