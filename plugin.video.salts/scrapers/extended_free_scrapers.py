"""
SALTS Scrapers - Enhanced Free Streaming Sources (No Debrid Required)
Direct streaming providers that don't require any debrid service.
Added by zeus768 for SALTS 2.8

Providers included:
- VidSrc variants (VidSrc.xyz, VidSrc.cc, VidSrc.in, VidSrc.pm)
- 2Embed variants
- FlixHQ, BFlixTV, HDToday
- Soap2Day, LookMovie, AZMovies, YesMovies
- FMovies, GoMovies, 123Movies
- StreamLord, MoviesJoy
- WatchAsian, KissAsian, DramaCool (Asian content)
- Zoro, 9Anime, GogoAnime, AniWave, HiAnime (Anime)
- And many more...
"""
import re
import json
import xbmc
import xbmcaddon
from urllib.request import urlopen, Request
from urllib.parse import quote_plus, urlencode
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from salts_lib import log_utils

ADDON = xbmcaddon.Addon()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


class FreeStreamBase(BaseScraper):
 """Base class for free streaming scrapers"""
 
 BASE_URL = ''
 NAME = 'FreeStreamBase'
 EMBED_PATTERN = None
 
 def _http_get(self, url, headers=None, timeout=15):
 """HTTP GET with custom headers"""
 try:
 hdrs = {'User-Agent': UA, 'Accept': '*/*'}
 if headers:
 hdrs.update(headers)
 req = Request(url, headers=hdrs)
 resp = urlopen(req, timeout=timeout)
 return resp.read().decode('utf-8', errors='replace')
 except Exception as e:
 log_utils.log_error(f'{self.NAME}: HTTP error: {e}')
 return ''
 
 def _get_imdb_id(self, title, year, media_type='movie'):
 """Get IMDB ID from TMDB"""
 try:
 search_type = 'movie' if media_type == 'movie' else 'tv'
 url = f'https://api.themoviedb.org/3/search/{search_type}'
 params = f'api_key=8265bd1679663a7ea12ac168da84d2e8&query={quote_plus(title)}'
 if year:
 params += f'&year={year}'
 
 req = Request(f'{url}?{params}', headers={'User-Agent': UA})
 resp = urlopen(req, timeout=10)
 data = json.loads(resp.read().decode('utf-8'))
 
 if data.get('results'):
 tmdb_id = data['results'][0]['id']
 ext_url = f'https://api.themoviedb.org/3/{search_type}/{tmdb_id}/external_ids?api_key=8265bd1679663a7ea12ac168da84d2e8'
 req2 = Request(ext_url, headers={'User-Agent': UA})
 resp2 = urlopen(req2, timeout=10)
 ext_data = json.loads(resp2.read().decode('utf-8'))
 return ext_data.get('imdb_id', ''), tmdb_id
 except Exception as e:
 log_utils.log_error(f'{self.NAME}: IMDB lookup error: {e}')
 return '', ''
 
 def _get_tmdb_id(self, title, year, media_type='movie'):
 """Get TMDB ID"""
 try:
 search_type = 'movie' if media_type == 'movie' else 'tv'
 url = f'https://api.themoviedb.org/3/search/{search_type}'
 params = f'api_key=8265bd1679663a7ea12ac168da84d2e8&query={quote_plus(title)}'
 if year:
 params += f'&year={year}'
 
 req = Request(f'{url}?{params}', headers={'User-Agent': UA})
 resp = urlopen(req, timeout=10)
 data = json.loads(resp.read().decode('utf-8'))
 
 if data.get('results'):
 return data['results'][0]['id']
 except Exception:
 pass
 return ''
 
 def _extract_sources_from_html(self, html):
 """Extract stream URLs from HTML"""
 sources = []
 
 # Common patterns for stream URLs
 patterns = [
 r'file["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
 r'source["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
 r'src["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
 r'file["\']?\s*[:=]\s*["\']([^"\']+\.mp4[^"\']*)["\']',
 r'source["\']?\s*[:=]\s*["\']([^"\']+\.mp4[^"\']*)["\']',
 r'["\']?(https?://[^"\']+\.m3u8[^"\']*)["\']?',
 r'["\']?(https?://[^"\']+\.mp4[^"\']*)["\']?',
 ]
 
 for pattern in patterns:
 matches = re.findall(pattern, html, re.I)
 for url in matches:
 if url and 'http' in url:
 sources.append({
 'url': url,
 'quality': self._parse_quality(url),
 'scraper': self.NAME,
 'type': 'stream',
 'name': self.NAME
 })
 
 return sources
 
 def search(self, query, media_type='movie'):
 return []


# ==================== VIDSRC VARIANTS ====================

class VidSrcXYZScraper(FreeStreamBase):
 """VidSrc.xyz - Primary free streaming"""
 NAME = 'VidSrc.xyz'
 BASE_URL = 'https://vidsrc.xyz'
 
 def is_enabled(self):
 return ADDON.getSetting('vidsrc_xyz_enabled') != 'false'
 
 def get_movie_sources(self, title, year=''):
 imdb_id, tmdb_id = self._get_imdb_id(title, year, 'movie')
 sources = []
 
 # Try IMDB first, then TMDB
 for id_type, vid_id in [('imdb', imdb_id), ('tmdb', tmdb_id)]:
 if vid_id:
 try:
 url = f'{self.BASE_URL}/embed/movie/{vid_id}'
 html = self._http_get(url)
 if html:
 sources.extend(self._extract_sources_from_html(html))
 if sources:
 break
 except Exception:
 pass
 
 # Fallback: direct API
 if not sources and (imdb_id or tmdb_id):
 vid_id = imdb_id or tmdb_id
 sources.append({
 'url': f'{self.BASE_URL}/embed/movie/{vid_id}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': f'{self.NAME} Embed'
 })
 
 return sources
 
 def get_episode_sources(self, title, year, season, episode):
 imdb_id, tmdb_id = self._get_imdb_id(title, year, 'tvshow')
 sources = []
 
 for id_type, vid_id in [('imdb', imdb_id), ('tmdb', tmdb_id)]:
 if vid_id:
 try:
 url = f'{self.BASE_URL}/embed/tv/{vid_id}/{season}/{episode}'
 html = self._http_get(url)
 if html:
 sources.extend(self._extract_sources_from_html(html))
 if sources:
 break
 except Exception:
 pass
 
 if not sources and (imdb_id or tmdb_id):
 vid_id = imdb_id or tmdb_id
 sources.append({
 'url': f'{self.BASE_URL}/embed/tv/{vid_id}/{season}/{episode}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': f'{self.NAME} Embed'
 })
 
 return sources


class VidSrcCCScraper(VidSrcXYZScraper):
 """VidSrc.cc - Backup VidSrc"""
 NAME = 'VidSrc.cc'
 BASE_URL = 'https://vidsrc.cc'
 
 def is_enabled(self):
 return ADDON.getSetting('vidsrc_cc_enabled') != 'false'


class VidSrcInScraper(VidSrcXYZScraper):
 """VidSrc.in - Another VidSrc mirror"""
 NAME = 'VidSrc.in'
 BASE_URL = 'https://vidsrc.in'
 
 def is_enabled(self):
 return ADDON.getSetting('vidsrc_in_enabled') != 'false'


class VidSrcPMScraper(VidSrcXYZScraper):
 """VidSrc.pm - VidSrc Premium mirror"""
 NAME = 'VidSrc.pm'
 BASE_URL = 'https://vidsrc.pm'
 
 def is_enabled(self):
 return ADDON.getSetting('vidsrc_pm_enabled') != 'false'


class VidSrcNLScraper(VidSrcXYZScraper):
 """VidSrc.nl - VidSrc Netherlands"""
 NAME = 'VidSrc.nl'
 BASE_URL = 'https://vidsrc.nl'
 
 def is_enabled(self):
 return ADDON.getSetting('vidsrc_nl_enabled') != 'false'


class VidSrcProScraper(VidSrcXYZScraper):
 """VidSrc.pro - VidSrc Pro"""
 NAME = 'VidSrc.pro'
 BASE_URL = 'https://vidsrc.pro'
 
 def is_enabled(self):
 return ADDON.getSetting('vidsrc_pro_enabled') != 'false'


# ==================== 2EMBED VARIANTS ====================

class TwoEmbedScraper(FreeStreamBase):
 """2Embed.cc - Multi-source embedder"""
 NAME = '2Embed'
 BASE_URL = 'https://2embed.cc'
 
 def is_enabled(self):
 return ADDON.getSetting('2embed_enabled') != 'false'
 
 def get_movie_sources(self, title, year=''):
 imdb_id, tmdb_id = self._get_imdb_id(title, year, 'movie')
 sources = []
 
 if tmdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/embed/movie/{tmdb_id}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': f'{self.NAME}'
 })
 if imdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/embed/{imdb_id}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': f'{self.NAME} IMDB'
 })
 
 return sources
 
 def get_episode_sources(self, title, year, season, episode):
 imdb_id, tmdb_id = self._get_imdb_id(title, year, 'tvshow')
 sources = []
 
 if tmdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/embed/tv/{tmdb_id}/{season}/{episode}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': f'{self.NAME}'
 })
 
 return sources


class TwoEmbedOrgScraper(TwoEmbedScraper):
 """2Embed.org - Backup"""
 NAME = '2Embed.org'
 BASE_URL = 'https://2embed.org'
 
 def is_enabled(self):
 return ADDON.getSetting('2embed_org_enabled') != 'false'


# ==================== EMBED.SU & SIMILAR ====================

class EmbedSuScraper(FreeStreamBase):
 """Embed.su - Quality embedder"""
 NAME = 'Embed.su'
 BASE_URL = 'https://embed.su'
 
 def is_enabled(self):
 return ADDON.getSetting('embedsu_enabled') != 'false'
 
 def get_movie_sources(self, title, year=''):
 imdb_id, tmdb_id = self._get_imdb_id(title, year, 'movie')
 sources = []
 
 if tmdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/embed/movie/{tmdb_id}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': self.NAME
 })
 
 return sources
 
 def get_episode_sources(self, title, year, season, episode):
 _, tmdb_id = self._get_imdb_id(title, year, 'tvshow')
 sources = []
 
 if tmdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/embed/tv/{tmdb_id}/{season}/{episode}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': self.NAME
 })
 
 return sources


class AutoEmbedScraper(EmbedSuScraper):
 """AutoEmbed - Auto source selection"""
 NAME = 'AutoEmbed'
 BASE_URL = 'https://autoembed.cc'
 
 def is_enabled(self):
 return ADDON.getSetting('autoembed_enabled') != 'false'


class MultiEmbedScraper(EmbedSuScraper):
 """MultiEmbed - Multiple source embedder"""
 NAME = 'MultiEmbed'
 BASE_URL = 'https://multiembed.mov'
 
 def is_enabled(self):
 return ADDON.getSetting('multiembed_enabled') != 'false'
 
 def get_movie_sources(self, title, year=''):
 imdb_id, tmdb_id = self._get_imdb_id(title, year, 'movie')
 sources = []
 
 if imdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/video/{imdb_id}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': self.NAME
 })
 if tmdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/video/tmdb/movie/{tmdb_id}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': f'{self.NAME} TMDB'
 })
 
 return sources
 
 def get_episode_sources(self, title, year, season, episode):
 imdb_id, tmdb_id = self._get_imdb_id(title, year, 'tvshow')
 sources = []
 
 if imdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/video/{imdb_id}/{season}/{episode}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': self.NAME
 })
 if tmdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/video/tmdb/tv/{tmdb_id}/{season}/{episode}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': f'{self.NAME} TMDB'
 })
 
 return sources


class VidLinkScraper(EmbedSuScraper):
 """VidLink - Fast streaming"""
 NAME = 'VidLink'
 BASE_URL = 'https://vidlink.pro'
 
 def is_enabled(self):
 return ADDON.getSetting('vidlink_enabled') != 'false'


class VidPlayScraper(EmbedSuScraper):
 """VidPlay - Video player embed"""
 NAME = 'VidPlay'
 BASE_URL = 'https://vidplay.online'
 
 def is_enabled(self):
 return ADDON.getSetting('vidplay_enabled') != 'false'


class MoviesAPIScraper(EmbedSuScraper):
 """MoviesAPI - Movie API service"""
 NAME = 'MoviesAPI'
 BASE_URL = 'https://moviesapi.club'
 
 def is_enabled(self):
 return ADDON.getSetting('moviesapi_enabled') != 'false'


class NontonGoScraper(EmbedSuScraper):
 """NontonGo - Indonesian streaming"""
 NAME = 'NontonGo'
 BASE_URL = 'https://nontongo.win'
 
 def is_enabled(self):
 return ADDON.getSetting('nontongo_enabled') != 'false'


class SmashyStreamScraper(EmbedSuScraper):
 """SmashyStream - Multiple sources"""
 NAME = 'SmashyStream'
 BASE_URL = 'https://player.smashy.stream'
 
 def is_enabled(self):
 return ADDON.getSetting('smashystream_enabled') != 'false'
 
 def get_movie_sources(self, title, year=''):
 imdb_id, tmdb_id = self._get_imdb_id(title, year, 'movie')
 sources = []
 
 if imdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/movie/{imdb_id}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': self.NAME
 })
 if tmdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/movie/{tmdb_id}?tmdb=1',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': f'{self.NAME} TMDB'
 })
 
 return sources
 
 def get_episode_sources(self, title, year, season, episode):
 imdb_id, tmdb_id = self._get_imdb_id(title, year, 'tvshow')
 sources = []
 
 if imdb_id:
 sources.append({
 'url': f'{self.BASE_URL}/tv/{imdb_id}/{season}/{episode}',
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': self.NAME
 })
 
 return sources


class RgShortsScraper(EmbedSuScraper):
 """RgShorts - Quick embeds"""
 NAME = 'RgShorts'
 BASE_URL = 'https://rivestream.live'
 
 def is_enabled(self):
 return ADDON.getSetting('rgshorts_enabled') != 'false'


# ==================== FLIXHQ & SIMILAR ====================

class FlixHQScraper(FreeStreamBase):
 """FlixHQ - High quality free streaming"""
 NAME = 'FlixHQ'
 BASE_URL = 'https://flixhq.to'
 
 def is_enabled(self):
 return ADDON.getSetting('flixhq_enabled') != 'false'
 
 def get_movie_sources(self, title, year=''):
 sources = []
 try:
 # Search for the movie
 search_url = f'{self.BASE_URL}/search/{quote_plus(title)}'
 html = self._http_get(search_url)
 if html:
 soup = BeautifulSoup(html, 'html.parser')
 # Find movie links
 items = soup.select('.film_list-wrap .flw-item')
 for item in items[:3]:
 link = item.select_one('a.film-poster-ahref')
 if link and link.get('href'):
 movie_url = self.BASE_URL + link['href']
 sources.append({
 'url': movie_url,
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': self.NAME
 })
 except Exception as e:
 log_utils.log_error(f'{self.NAME}: Error: {e}')
 return sources
 
 def get_episode_sources(self, title, year, season, episode):
 return self.get_movie_sources(f'{title} S{season:02d}E{episode:02d}')


class BFlixTVScraper(FlixHQScraper):
 """BFlix.tv - Free movies & TV"""
 NAME = 'BFlix'
 BASE_URL = 'https://bflix.gs'
 
 def is_enabled(self):
 return ADDON.getSetting('bflix_enabled') != 'false'


class HDTodayScraper(FlixHQScraper):
 """HDToday - HD streaming"""
 NAME = 'HDToday'
 BASE_URL = 'https://hdtoday.tv'
 
 def is_enabled(self):
 return ADDON.getSetting('hdtoday_enabled') != 'false'


class Soap2DayScraper(FlixHQScraper):
 """Soap2Day - Popular free streaming"""
 NAME = 'Soap2Day'
 BASE_URL = 'https://soap2day.to'
 
 def is_enabled(self):
 return ADDON.getSetting('soap2day_enabled') != 'false'


class LookMovieScraper(FlixHQScraper):
 """LookMovie - Quality streams"""
 NAME = 'LookMovie'
 BASE_URL = 'https://lookmovie2.to'
 
 def is_enabled(self):
 return ADDON.getSetting('lookmovie_enabled') != 'false'


class AZMoviesScraper(FlixHQScraper):
 """AZMovies - A-Z Movies"""
 NAME = 'AZMovies'
 BASE_URL = 'https://azmovies.net'
 
 def is_enabled(self):
 return ADDON.getSetting('azmovies_enabled') != 'false'


class YesMoviesScraper(FlixHQScraper):
 """YesMovies - Yes to movies"""
 NAME = 'YesMovies'
 BASE_URL = 'https://yesmovies.ag'
 
 def is_enabled(self):
 return ADDON.getSetting('yesmovies_enabled') != 'false'


class FMoviesScraper(FlixHQScraper):
 """FMovies - Classic free streaming"""
 NAME = 'FMovies'
 BASE_URL = 'https://fmovies.wtf'
 
 def is_enabled(self):
 return ADDON.getSetting('fmovies_enabled') != 'false'


class GoMoviesScraper(FlixHQScraper):
 """GoMovies - Go stream movies"""
 NAME = 'GoMovies'
 BASE_URL = 'https://gomovies.sx'
 
 def is_enabled(self):
 return ADDON.getSetting('gomovies_enabled') != 'false'


class Movies123Scraper(FlixHQScraper):
 """123Movies - Classic streaming"""
 NAME = '123Movies'
 BASE_URL = 'https://ww1.123moviesfree.net'
 
 def is_enabled(self):
 return ADDON.getSetting('123movies_enabled') != 'false'


class StreamLordScraper(FlixHQScraper):
 """StreamLord - Stream everything"""
 NAME = 'StreamLord'
 BASE_URL = 'https://streamlord.to'
 
 def is_enabled(self):
 return ADDON.getSetting('streamlord_enabled') != 'false'


class MoviesJoyScraper(FlixHQScraper):
 """MoviesJoy - Joy of movies"""
 NAME = 'MoviesJoy'
 BASE_URL = 'https://moviesjoy.is'
 
 def is_enabled(self):
 return ADDON.getSetting('moviesjoy_enabled') != 'false'


class SFlix2Scraper(FlixHQScraper):
 """SFlix - S Flix streaming"""
 NAME = 'SFlix'
 BASE_URL = 'https://sflix.to'
 
 def is_enabled(self):
 return ADDON.getSetting('sflix_enabled') != 'false'


class PutlockerScraper(FlixHQScraper):
 """Putlocker - Classic streaming"""
 NAME = 'Putlocker'
 BASE_URL = 'https://putlocker.pe'
 
 def is_enabled(self):
 return ADDON.getSetting('putlocker_enabled') != 'false'


class WatchSeriesHDScraper(FlixHQScraper):
 """WatchSeriesHD - HD TV shows"""
 NAME = 'WatchSeriesHD'
 BASE_URL = 'https://watchserieshd.tv'
 
 def is_enabled(self):
 return ADDON.getSetting('watchserieshd_enabled') != 'false'


class M4UFreesScraper(FlixHQScraper):
 """M4UFree - Movies 4 U"""
 NAME = 'M4UFree'
 BASE_URL = 'https://m4ufree.tv'
 
 def is_enabled(self):
 return ADDON.getSetting('m4ufree_enabled') != 'false'


class YifyMoviesScraper(FlixHQScraper):
 """YifyMovies - YIFY quality streams"""
 NAME = 'YifyMovies'
 BASE_URL = 'https://yifymovies.tv'
 
 def is_enabled(self):
 return ADDON.getSetting('yifymovies_enabled') != 'false'


class SolarMovieScraper2(FlixHQScraper):
 """SolarMovie - Solar streams"""
 NAME = 'SolarMovie2'
 BASE_URL = 'https://solarmovie.pe'
 
 def is_enabled(self):
 return ADDON.getSetting('solarmovie2_enabled') != 'false'


class XMovies8Scraper(FlixHQScraper):
 """XMovies8 - X Movies"""
 NAME = 'XMovies8'
 BASE_URL = 'https://xmovies8.fun'
 
 def is_enabled(self):
 return ADDON.getSetting('xmovies8_enabled') != 'false'


class IOMoviesScraper(FlixHQScraper):
 """IOMovies - IO Streaming"""
 NAME = 'IOMovies'
 BASE_URL = 'https://iomovies.top'
 
 def is_enabled(self):
 return ADDON.getSetting('iomovies_enabled') != 'false'


class CMoviesHDScraper(FlixHQScraper):
 """CMoviesHD - HD streaming"""
 NAME = 'CMoviesHD'
 BASE_URL = 'https://cmovies.so'
 
 def is_enabled(self):
 return ADDON.getSetting('cmovieshd_enabled') != 'false'


# ==================== ASIAN DRAMA ====================

class WatchAsianScraper(FreeStreamBase):
 """WatchAsian - Asian dramas"""
 NAME = 'WatchAsian'
 BASE_URL = 'https://watchasian.sk'
 
 def is_enabled(self):
 return ADDON.getSetting('watchasian_enabled') != 'false'
 
 def get_movie_sources(self, title, year=''):
 return [] # Drama-focused
 
 def get_episode_sources(self, title, year, season, episode):
 sources = []
 try:
 search_url = f'{self.BASE_URL}/search?keyword={quote_plus(title)}'
 html = self._http_get(search_url)
 if html:
 soup = BeautifulSoup(html, 'html.parser')
 items = soup.select('.film_list .item')
 for item in items[:3]:
 link = item.select_one('a')
 if link and link.get('href'):
 sources.append({
 'url': link['href'],
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': self.NAME
 })
 except Exception:
 pass
 return sources


class KissAsianScraper(WatchAsianScraper):
 """KissAsian - Asian content"""
 NAME = 'KissAsian'
 BASE_URL = 'https://kissasian.lu'
 
 def is_enabled(self):
 return ADDON.getSetting('kissasian_enabled') != 'false'


class DramaCoolScraper(WatchAsianScraper):
 """DramaCool - Asian dramas"""
 NAME = 'DramaCool'
 BASE_URL = 'https://dramacool.pa'
 
 def is_enabled(self):
 return ADDON.getSetting('dramacool_enabled') != 'false'


class ViewAsianScraper(WatchAsianScraper):
 """ViewAsian - Asian viewing"""
 NAME = 'ViewAsian'
 BASE_URL = 'https://viewasian.co'
 
 def is_enabled(self):
 return ADDON.getSetting('viewasian_enabled') != 'false'


class AsianLoadScraper(WatchAsianScraper):
 """AsianLoad - Asian content loader"""
 NAME = 'AsianLoad'
 BASE_URL = 'https://asianload.io'
 
 def is_enabled(self):
 return ADDON.getSetting('asianload_enabled') != 'false'


# ==================== ANIME ====================

class ZoroScraper(FreeStreamBase):
 """Zoro.to - Quality anime streaming"""
 NAME = 'Zoro'
 BASE_URL = 'https://zoro.to'
 
 def is_enabled(self):
 return ADDON.getSetting('zoro_enabled') != 'false'
 
 def get_movie_sources(self, title, year=''):
 sources = []
 try:
 search_url = f'{self.BASE_URL}/search?keyword={quote_plus(title)}'
 html = self._http_get(search_url)
 if html:
 soup = BeautifulSoup(html, 'html.parser')
 items = soup.select('.film_list-wrap .flw-item')
 for item in items[:3]:
 link = item.select_one('a.film-poster-ahref')
 if link and link.get('href'):
 sources.append({
 'url': self.BASE_URL + link['href'],
 'quality': 'HD',
 'scraper': self.NAME,
 'type': 'embed',
 'name': self.NAME
 })
 except Exception:
 pass
 return sources
 
 def get_episode_sources(self, title, year, season, episode):
 return self.get_movie_sources(title)


class NineAnimeScraper(ZoroScraper):
 """9Anime - Popular anime site"""
 NAME = '9Anime'
 BASE_URL = 'https://9anime.to'
 
 def is_enabled(self):
 return ADDON.getSetting('9anime_enabled') != 'false'


class GogoAnimeScraper(ZoroScraper):
 """GogoAnime - Classic anime streaming"""
 NAME = 'GogoAnime'
 BASE_URL = 'https://gogoanime.sk'
 
 def is_enabled(self):
 return ADDON.getSetting('gogoanime_enabled') != 'false'


class AniWaveScraper(ZoroScraper):
 """AniWave - Anime waves"""
 NAME = 'AniWave'
 BASE_URL = 'https://aniwave.to'
 
 def is_enabled(self):
 return ADDON.getSetting('aniwave_enabled') != 'false'


class HiAnimeScraper(ZoroScraper):
 """HiAnime - High quality anime"""
 NAME = 'HiAnime'
 BASE_URL = 'https://hianime.to'
 
 def is_enabled(self):
 return ADDON.getSetting('hianime_enabled') != 'false'


class AnimePaheScraper(ZoroScraper):
 """AnimePahe - Pahe anime"""
 NAME = 'AnimePahe'
 BASE_URL = 'https://animepahe.ru'
 
 def is_enabled(self):
 return ADDON.getSetting('animepahe_enabled') != 'false'


class AnimeFlixScraper(ZoroScraper):
 """AnimeFlix - Flix anime"""
 NAME = 'AnimeFlix'
 BASE_URL = 'https://animeflix.live'
 
 def is_enabled(self):
 return ADDON.getSetting('animeflix_enabled') != 'false'


class KickAssAnimeScraper(ZoroScraper):
 """KickAssAnime - KA anime"""
 NAME = 'KickAssAnime'
 BASE_URL = 'https://kickassanime.am'
 
 def is_enabled(self):
 return ADDON.getSetting('kickassanime_enabled') != 'false'


class YugenAnimeScraper(ZoroScraper):
 """YugenAnime - Yugen anime"""
 NAME = 'YugenAnime'
 BASE_URL = 'https://yugenanime.tv'
 
 def is_enabled(self):
 return ADDON.getSetting('yugenanime_enabled') != 'false'


class AllAnimeScraper(ZoroScraper):
 """AllAnime - All anime"""
 NAME = 'AllAnime'
 BASE_URL = 'https://allanime.to'
 
 def is_enabled(self):
 return ADDON.getSetting('allanime_enabled') != 'false'


class AnimeSugeScraper(ZoroScraper):
 """AnimeSuge - Suge anime"""
 NAME = 'AnimeSuge'
 BASE_URL = 'https://animesuge.to'
 
 def is_enabled(self):
 return ADDON.getSetting('animesuge_enabled') != 'false'


class AniwatchScraper(ZoroScraper):
 """Aniwatch - Watch anime"""
 NAME = 'Aniwatch'
 BASE_URL = 'https://aniwatch.to'
 
 def is_enabled(self):
 return ADDON.getSetting('aniwatch_enabled') != 'false'


# ==================== ALL EXTENDED FREE SCRAPERS ====================

EXTENDED_FREE_SCRAPERS = [
 # VidSrc Variants
 VidSrcXYZScraper,
 VidSrcCCScraper,
 VidSrcInScraper,
 VidSrcPMScraper,
 VidSrcNLScraper,
 VidSrcProScraper,
 
 # 2Embed Variants
 TwoEmbedScraper,
 TwoEmbedOrgScraper,
 
 # Embed Services
 EmbedSuScraper,
 AutoEmbedScraper,
 MultiEmbedScraper,
 VidLinkScraper,
 VidPlayScraper,
 MoviesAPIScraper,
 NontonGoScraper,
 SmashyStreamScraper,
 RgShortsScraper,
 
 # FlixHQ & Similar Sites
 FlixHQScraper,
 BFlixTVScraper,
 HDTodayScraper,
 Soap2DayScraper,
 LookMovieScraper,
 AZMoviesScraper,
 YesMoviesScraper,
 FMoviesScraper,
 GoMoviesScraper,
 Movies123Scraper,
 StreamLordScraper,
 MoviesJoyScraper,
 SFlix2Scraper,
 PutlockerScraper,
 WatchSeriesHDScraper,
 M4UFreesScraper,
 YifyMoviesScraper,
 SolarMovieScraper2,
 XMovies8Scraper,
 IOMoviesScraper,
 CMoviesHDScraper,
 
 # Asian Drama
 WatchAsianScraper,
 KissAsianScraper,
 DramaCoolScraper,
 ViewAsianScraper,
 AsianLoadScraper,
 
 # Anime
 ZoroScraper,
 NineAnimeScraper,
 GogoAnimeScraper,
 AniWaveScraper,
 HiAnimeScraper,
 AnimePaheScraper,
 AnimeFlixScraper,
 KickAssAnimeScraper,
 YugenAnimeScraper,
 AllAnimeScraper,
 AnimeSugeScraper,
 AniwatchScraper,
]
