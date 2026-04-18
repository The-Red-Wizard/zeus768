"""
Bones Scraper - Direct stream links provider
"""
import re
import xbmc
import xbmcaddon
import time

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
        return True

    def _fetch_catalog(self):
        global _bones_cache, _bones_cache_time

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

        # Parse XML-style items: <item>...<title>...<sublink>...<summary>...<thumbnail>...<fanart>...</item>
        items = re.findall(r'<item>(.*?)</item>', raw, re.DOTALL)
        if not items:
            # Fallback: split by <title> tags if no <item> wrappers
            items = re.split(r'(?=<title>)', raw)

        for item_text in items:
            title_match = re.search(r'<title>(.*?)</title>', item_text)
            if not title_match:
                continue
            title = title_match.group(1).strip()
            if not title:
                continue

            # Get all stream URLs (sublink tags)
            sublinks = re.findall(r'<sublink>(.*?)</sublink>', item_text)
            # Also catch bare streamtape/luluvid URLs not in sublink tags
            if not sublinks:
                sublinks = re.findall(r'(https?://(?:streamtape\.com|luluvid\.com)/[^\s<]+)', item_text)

            stream_url = sublinks[0].strip() if sublinks else ''
            stream_url_2 = sublinks[1].strip() if len(sublinks) > 1 else ''

            if not stream_url:
                continue

            # Clean URLs (remove trailing </sublink> etc)
            stream_url = re.sub(r'<.*', '', stream_url).strip()
            stream_url_2 = re.sub(r'<.*', '', stream_url_2).strip() if stream_url_2 else ''

            # Summary
            summary_match = re.search(r'<summary>(.*?)</summary>', item_text, re.DOTALL)
            description = summary_match.group(1).strip() if summary_match else ''

            # Thumbnail (poster)
            thumb_match = re.search(r'<thumbnail>(.*?)</thumbnail>', item_text)
            poster = thumb_match.group(1).strip() if thumb_match else ''

            # Fanart (backdrop)
            fanart_match = re.search(r'<fanart>(.*?)</fanart>', item_text)
            backdrop = fanart_match.group(1).strip() if fanart_match else poster

            # IMDB ID
            imdb_match = re.search(r'(tt\d{7,})', item_text)
            imdb_id = imdb_match.group(1) if imdb_match else ''

            movies.append({
                'title': title,
                'stream_url': stream_url,
                'stream_url_2': stream_url_2,
                'description': description,
                'poster': poster,
                'backdrop': backdrop,
                'imdb_id': imdb_id,
            })

        xbmc.log(f'Bones: Parsed {len(movies)} movies from catalog', xbmc.LOGINFO)
        _bones_cache = movies
        _bones_cache_time = time.time()
        return movies

    def search(self, query, media_type='movie', **kwargs):
        """Search Bones catalog. Called by framework as search(query, media_type, tmdb_id=, title=, year=, season=, episode=)"""
        if media_type not in ('movie', 'movies'):
            return []

        title = kwargs.get('title', query)
        year = kwargs.get('year', '')

        catalog = self._fetch_catalog()
        search_term = title.lower().strip() if title else query.lower().strip()
        search_term = re.sub(r'\s*\(?\d{4}\)?\s*$', '', search_term).strip()

        results = []
        for movie in catalog:
            mtitle = movie['title'].lower()
            if search_term in mtitle or mtitle in search_term:
                quality = '720p'
                url_lower = movie['stream_url'].lower()
                if '1080p' in url_lower:
                    quality = '1080p'
                elif '4k' in url_lower or '2160' in url_lower:
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
        return self._fetch_catalog()
