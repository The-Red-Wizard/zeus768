"""
SALTS Scrapers - Stremio Addon Protocol Scrapers
Torrentio, MediaFusion, Comet, CyberFlix, Annatar, PeerFlix
zeus768 for Kodi 21+

Uses the Stremio addon stream API to fetch sources.
All Stremio addons follow: GET {base}/stream/{type}/{imdb_id}.json

Requires IMDB ID - converts from TMDB ID via TMDB API.
"""
import re
import json
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus

from scrapers.base_scraper import BaseScraper
from salts_lib import log_utils

TMDB_KEY = '8265bd1679663a7ea12ac168da84d2e8'
TMDB_BASE = 'https://api.themoviedb.org/3'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Cache TMDB→IMDB lookups in memory for the session
_imdb_cache = {}


def _tmdb_to_imdb(tmdb_id, media_type='movie'):
 """Convert TMDB ID to IMDB ID via TMDB API external_ids endpoint."""
 if not tmdb_id:
 return None
 cache_key = f'{media_type}_{tmdb_id}'
 if cache_key in _imdb_cache:
 return _imdb_cache[cache_key]
 
 try:
 ep_type = 'movie' if media_type == 'movie' else 'tv'
 url = f'{TMDB_BASE}/{ep_type}/{tmdb_id}/external_ids?api_key={TMDB_KEY}'
 req = Request(url, headers={'User-Agent': UA})
 resp = urlopen(req, timeout=10)
 data = json.loads(resp.read().decode('utf-8'))
 imdb_id = data.get('imdb_id', '')
 if imdb_id:
 _imdb_cache[cache_key] = imdb_id
 return imdb_id
 except Exception as e:
 log_utils.log(f'TMDB→IMDB lookup failed for {tmdb_id}: {e}', xbmc.LOGDEBUG)
 return None


def _tmdb_search_imdb(title, year='', media_type='movie'):
 """Search TMDB by title/year to get IMDB ID."""
 try:
 ep_type = 'movie' if media_type == 'movie' else 'tv'
 params = f'api_key={TMDB_KEY}&query={quote_plus(title)}'
 if year:
 yr_key = 'year' if media_type == 'movie' else 'first_air_date_year'
 params += f'&{yr_key}={year}'
 url = f'{TMDB_BASE}/search/{ep_type}?{params}'
 req = Request(url, headers={'User-Agent': UA})
 resp = urlopen(req, timeout=10)
 data = json.loads(resp.read().decode('utf-8'))
 results = data.get('results', [])
 if results:
 found_id = results[0].get('id')
 if found_id:
 return _tmdb_to_imdb(str(found_id), media_type)
 except Exception as e:
 log_utils.log(f'TMDB search→IMDB failed for {title}: {e}', xbmc.LOGDEBUG)
 return None


class StremioBaseScraper(BaseScraper):
 """Base class for all Stremio addon protocol scrapers.
 
 Subclasses set BASE_URL and NAME. The stream API is:
 GET {BASE_URL}/stream/{type}/{id}.json
 
 where type = 'movie' or 'series'
 and id = IMDB ID (for series: {imdb_id}:{season}:{episode})
 """
 
 BASE_URL = ''
 NAME = 'Stremio'
 is_free = False # Override in subclasses for free stream scrapers
 
 def __init__(self, timeout=15):
 super().__init__(timeout)
 self._stremio_headers = {
 'User-Agent': UA,
 'Accept': 'application/json',
 }
 
 def _get_stremio_streams(self, stremio_type, stremio_id):
 """Call the Stremio stream API and return parsed JSON."""
 url = f'{self.BASE_URL}/stream/{stremio_type}/{stremio_id}.json'
 try:
 req = Request(url, headers=self._stremio_headers)
 resp = urlopen(req, timeout=self.timeout)
 data = json.loads(resp.read().decode('utf-8'))
 return data.get('streams', [])
 except Exception as e:
 log_utils.log(f'{self.NAME}: API error for {url}: {e}', xbmc.LOGDEBUG)
 return []
 
 def _resolve_imdb_id(self, tmdb_id='', title='', year='', media_type='movie'):
 """Get IMDB ID from TMDB ID or title search."""
 imdb_id = None
 if tmdb_id:
 imdb_id = _tmdb_to_imdb(tmdb_id, media_type)
 if not imdb_id and title:
 imdb_id = _tmdb_search_imdb(title, year, media_type)
 return imdb_id
 
 def _parse_stremio_stream(self, stream):
 """Parse a single Stremio stream object into SALTS source format.
 
 Stremio streams can have:
 - url: direct stream URL
 - infoHash + fileIdx: torrent
 - name: e.g. "Torrentio\n4K" 
 - title: e.g. "Movie.2024.2160p.WEB-DL\n 150 8.5 GB ️ YTS"
 """
 result = {
 'title': '',
 'url': '',
 'magnet': '',
 'quality': 'SD',
 'host': self.NAME,
 'direct': False,
 'seeds': 0,
 'size': '',
 }
 
 name = stream.get('name', '')
 title_text = stream.get('title', stream.get('description', ''))
 
 # Parse quality from name/title
 full_text = f'{name} {title_text}'
 result['quality'] = self._parse_quality(full_text)
 
 # Parse seeds from title ( 150 or Seeds: 150)
 seeds_match = re.search(r'\s*(\d+)', title_text)
 if not seeds_match:
 seeds_match = re.search(r'[Ss]eeds?:?\s*(\d+)', title_text)
 if seeds_match:
 result['seeds'] = int(seeds_match.group(1))
 
 # Parse size from title ( 8.5 GB or Size: 8.5 GB)
 size_match = re.search(r'\s*([\d.]+\s*[KMGT]B)', title_text, re.IGNORECASE)
 if not size_match:
 size_match = re.search(r'[Ss]ize:?\s*([\d.]+\s*[KMGT]B)', title_text, re.IGNORECASE)
 if size_match:
 result['size'] = size_match.group(1)
 
 # Build display title
 clean_title = title_text.split('\n')[0] if title_text else name.replace('\n', ' ')
 clean_name = name.replace('\n', ' ').strip()
 result['title'] = f'[{clean_name}] {clean_title}' if clean_name else clean_title
 
 # Extract source (torrent or direct URL)
 info_hash = stream.get('infoHash', '')
 direct_url = stream.get('url', '')
 
 if info_hash:
 # Build magnet link
 dn = quote_plus(clean_title or 'Unknown')
 trackers = [
 'udp://tracker.opentrackr.org:1337/announce',
 'udp://open.stealth.si:80/announce',
 'udp://tracker.torrent.eu.org:451/announce',
 'udp://tracker.bittor.pw:1337/announce',
 'udp://public.popcorn-tracker.org:6969/announce',
 'udp://tracker.dler.org:6969/announce',
 'udp://exodus.desync.com:6969',
 'udp://open.demonii.com:1337/announce',
 ]
 tr_str = '&tr='.join([quote_plus(t) for t in trackers])
 result['magnet'] = f'magnet:?xt=urn:btih:{info_hash}&dn={dn}&tr={tr_str}'
 
 file_idx = stream.get('fileIdx')
 if file_idx is not None:
 result['magnet'] += f'&fileIndex={file_idx}'
 
 if not result['seeds']:
 result['seeds'] = 1 # Default for torrent sources
 
 elif direct_url:
 result['url'] = direct_url
 result['direct'] = True
 if not result['seeds']:
 result['seeds'] = 9999 # High priority for direct streams
 else:
 return None
 
 return result
 
 def search(self, query, media_type='movie', tmdb_id='', title='', year='',
 season='', episode='', **kwargs):
 """Search Stremio addon for streams."""
 sources = []
 
 # Parse title/year from query if not provided
 if not title:
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
 
 # Resolve IMDB ID
 mt = 'movie' if media_type == 'movie' else 'tv'
 imdb_id = self._resolve_imdb_id(tmdb_id, title, year, mt)
 
 if not imdb_id:
 log_utils.log(f'{self.NAME}: No IMDB ID found for {title} ({year})', xbmc.LOGDEBUG)
 return sources
 
 # Build Stremio API call
 if media_type == 'movie':
 stremio_type = 'movie'
 stremio_id = imdb_id
 else:
 stremio_type = 'series'
 s = int(season) if season else 1
 e = int(episode) if episode else 1
 stremio_id = f'{imdb_id}:{s}:{e}'
 
 streams = self._get_stremio_streams(stremio_type, stremio_id)
 
 for stream in streams:
 try:
 source = self._parse_stremio_stream(stream)
 if source:
 source['host'] = self.NAME
 sources.append(source)
 except Exception as e:
 log_utils.log(f'{self.NAME}: Stream parse error: {e}', xbmc.LOGDEBUG)
 continue
 
 log_utils.log(f'{self.NAME}: Found {len(sources)} sources for {title}', xbmc.LOGINFO)
 return sources


# ======================================================================
# TORRENTIO - The biggest Stremio torrent aggregator
# Indexes: 1337x, ThePirateBay, RARBG, YTS, EZTV, TorrentGalaxy, etc.
# ======================================================================

class TorrentioScraper(StremioBaseScraper):
 """Torrentio - Stremio's #1 torrent aggregator.
 
 Aggregates from 20+ torrent indexers including 1337x, TPB, RARBG, YTS,
 EZTV, TorrentGalaxy, KickassTorrents, and more.
 """
 BASE_URL = 'https://torrentio.strem.fun'
 NAME = 'Torrentio'
 is_free = False
 
 def is_enabled(self):
 addon = xbmcaddon.Addon()
 return addon.getSetting('torrentio_enabled') != 'false'


# ======================================================================
# MEDIAFUSION - Community-driven Stremio aggregator
# Supports torrent + direct streams
# ======================================================================

class MediaFusionScraper(StremioBaseScraper):
 """MediaFusion - Community torrent/stream aggregator for Stremio.
 
 Open-source, supports Real-Debrid, AllDebrid, Premiumize, and direct streams.
 Indexes from multiple torrent trackers.
 """
 BASE_URL = 'https://mediafusion.elfhosted.com'
 NAME = 'MediaFusion'
 is_free = False
 
 def is_enabled(self):
 addon = xbmcaddon.Addon()
 return addon.getSetting('mediafusion_enabled') != 'false'


# ======================================================================
# COMET - Fast Stremio torrent aggregator
# ======================================================================

class CometScraper(StremioBaseScraper):
 """Comet - Fast Stremio torrent aggregator.
 
 Lightweight and fast, supports debrid services.
 """
 BASE_URL = 'https://comet.elfhosted.com'
 NAME = 'Comet'
 is_free = False
 
 def is_enabled(self):
 addon = xbmcaddon.Addon()
 return addon.getSetting('comet_enabled') != 'false'


# ======================================================================
# CYBERFLIX - Free direct streams (no debrid required)
# ======================================================================

class CyberFlixScraper(StremioBaseScraper):
 """CyberFlix - Free direct streams via Stremio protocol.
 
 Provides free streams that play directly without debrid services.
 """
 BASE_URL = 'https://cyberflix.elfhosted.com'
 NAME = 'CyberFlix'
 is_free = True
 
 def is_enabled(self):
 addon = xbmcaddon.Addon()
 return addon.getSetting('cyberflix_enabled') != 'false'
 
 def _parse_stremio_stream(self, stream):
 """Override to mark all CyberFlix streams as free/direct."""
 result = super()._parse_stremio_stream(stream)
 if result:
 if result.get('url'):
 result['direct'] = True
 result['seeds'] = 9999
 result['title'] = f"[FREE] {result['title']}"
 return result


# ======================================================================
# ANNATAR - Jackett/Prowlarr integration for Stremio
# ======================================================================

class AnnatarScraper(StremioBaseScraper):
 """Annatar - Stremio addon that indexes via Jackett/Prowlarr.
 
 Uses your Jackett/Prowlarr instance to search all configured indexers.
 Requires self-hosting or a public instance.
 """
 BASE_URL = 'https://annatar.elfhosted.com'
 NAME = 'Annatar'
 is_free = False
 
 def is_enabled(self):
 addon = xbmcaddon.Addon()
 return addon.getSetting('annatar_enabled') != 'false'


# ======================================================================
# PEERFLIX - Free P2P streams
# ======================================================================

class PeerFlixScraper(StremioBaseScraper):
 """PeerFlix - Free peer-to-peer streams.
 
 Uses P2P technology for direct playback. No debrid required.
 """
 BASE_URL = 'https://peerflix.elfhosted.com'
 NAME = 'PeerFlix'
 is_free = True
 
 def is_enabled(self):
 addon = xbmcaddon.Addon()
 return addon.getSetting('peerflix_enabled') != 'false'
 
 def _parse_stremio_stream(self, stream):
 """Override to mark PeerFlix streams as free."""
 result = super()._parse_stremio_stream(stream)
 if result and result.get('url'):
 result['direct'] = True
 result['seeds'] = 9998
 result['title'] = f"[FREE] {result['title']}"
 return result


# ======================================================================
# EASYNEWS - Usenet streams (for usenet subscribers)
# ======================================================================

class EasyNewsScraper(StremioBaseScraper):
 """EasyNews+ - Stremio addon for Usenet streams.
 
 Provides direct streams from EasyNews Usenet service.
 Requires EasyNews subscription.
 """
 BASE_URL = 'https://easynews.elfhosted.com'
 NAME = 'EasyNews+'
 is_free = False
 
 def is_enabled(self):
 addon = xbmcaddon.Addon()
 return addon.getSetting('easynews_enabled') != 'false'


# All Stremio scraper classes
ALL_STREMIO_SCRAPERS = [
 TorrentioScraper,
 MediaFusionScraper,
 CometScraper,
 CyberFlixScraper,
 AnnatarScraper,
 PeerFlixScraper,
 EasyNewsScraper,
]
