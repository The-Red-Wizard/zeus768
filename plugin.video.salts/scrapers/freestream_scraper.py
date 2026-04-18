"""
Free Stream Scraper for SALTS
Provides direct playable streams from free embed providers (VidSrc, 2Embed, etc.)
No debrid required - plays straight in Kodi.
"""
import xbmc
import xbmcaddon

from scrapers.base_scraper import BaseScraper

ADDON = xbmcaddon.Addon()


class FreeStreamScraper(BaseScraper):
 """Scraper that returns free direct streams from embed APIs"""
 
 def __init__(self):
 super().__init__()
 self.name = 'FreeStream'
 self.base_url = ''
 
 def get_name(self):
 return 'FreeStream'
 
 def is_enabled(self):
 return ADDON.getSetting('freestream_enabled') != 'false'
 
 def search(self, query, media_type='movie', tmdb_id='', imdb_id='',
 season='', episode='', title='', year=''):
 """
 Search for free streams. Uses tmdb_id/imdb_id directly if available,
 otherwise parses title/year from query string.
 """
 from salts_lib.free_streams import get_free_streams
 
 sources = []
 
 # Parse title and year from query if not provided
 if not title:
 import re
 # Query format: "Title Year" or "Title SxxExx"
 match = re.match(r'^(.+?)\s+(\d{4})$', query)
 if match:
 title = match.group(1).strip()
 year = match.group(2)
 else:
 match = re.match(r'^(.+?)\s+S(\d+)E(\d+)$', query, re.IGNORECASE)
 if match:
 title = match.group(1).strip()
 if not season:
 season = match.group(2)
 if not episode:
 episode = match.group(3)
 else:
 title = query
 
 try:
 free_sources = get_free_streams(
 tmdb_id=tmdb_id,
 imdb_id=imdb_id,
 title=title,
 year=year,
 media_type=media_type,
 season=season,
 episode=episode
 )
 
 for fs in free_sources:
 sources.append({
 'title': f"[FREE] {fs.get('provider', 'Stream')} - Direct Play",
 'url': fs['url'],
 'quality': fs.get('quality', 'HD'),
 'host': fs.get('provider', 'FreeStream'),
 'direct': True,
 'seeds': 9999, # High priority so free streams sort first
 'size': '',
 'magnet': '',
 })
 
 except Exception as e:
 xbmc.log(f'FreeStream scraper error: {e}', xbmc.LOGERROR)
 
 return sources
