"""
Bones Scraper - Direct stream links provider
Fixed 2026-01: marked as free scraper, tightened title matching, year-aware,
resilient to source-format variations.
"""
import re
import time
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from .base_scraper import BaseScraper

ADDON = xbmcaddon.Addon()
SOURCE_URL = 'https://thechains24.com/ABSOLUTION/MOVIES/newm.NEW.txt'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Module-level cache (shared across BonesScraper instances within the session)
_bones_cache = []
_bones_cache_time = 0


def _norm(text):
    """Normalize a title for comparison: lowercase, drop non-word chars, collapse spaces."""
    if not text:
        return ''
    text = text.lower()
    text = re.sub(r"[\u2018\u2019\u201c\u201d']", '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _extract_year(text):
    """Pull a 4-digit year (1900-2099) from arbitrary text. Returns str or ''."""
    if not text:
        return ''
    m = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    return m.group(1) if m else ''


def _parse_quality(url):
    """Very small quality hint from URL/filename."""
    u = (url or '').lower()
    if '2160' in u or '4k' in u or 'uhd' in u:
        return '4K'
    if '1080' in u:
        return '1080p'
    if '720' in u:
        return '720p'
    if '480' in u:
        return '480p'
    return '720p'  # sensible default for Bones (most are 720p WEB)


class BonesScraper(BaseScraper):
    NAME = 'Bones'
    BASE_URL = 'https://thechains24.com'
    # Flag consumed by default.py get_sources: allow to run without debrid.
    is_free = True

    def is_enabled(self):
        # Default enabled; user can disable via `bones_enabled=false`.
        return ADDON.getSetting('bones_enabled') != 'false'

    def _fetch_catalog(self):
        global _bones_cache, _bones_cache_time

        if _bones_cache and (time.time() - _bones_cache_time) < 3600:
            return _bones_cache

        try:
            req = Request(SOURCE_URL, headers={'User-Agent': USER_AGENT})
            response = urlopen(req, timeout=15)
            raw = response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            xbmc.log(f'Bones: Fetch failed: {e}', xbmc.LOGWARNING)
            return []

        movies = []

        # Parse XML-style <item>...</item> blocks
        items = re.findall(r'<item>(.*?)</item>', raw, re.DOTALL)
        if not items:
            # Fallback: split on <title> if no <item> wrappers
            items = re.split(r'(?=<title>)', raw)

        for item_text in items:
            title_match = re.search(r'<title>\s*(.*?)\s*</title>', item_text, re.DOTALL)
            if not title_match:
                continue
            title = re.sub(r'\s+', ' ', title_match.group(1)).strip()
            if not title:
                continue

            # Stream URLs (sublink tags). Tolerate whitespace/newlines inside.
            sublinks = re.findall(r'<sublink>\s*(\S+?)\s*</sublink>', item_text, re.DOTALL)
            if not sublinks:
                # Fallback: scrape any known host URL that appears raw
                sublinks = re.findall(
                    r'(https?://(?:streamtape\.com|streamtape\.to|streamtape\.net|'
                    r'luluvid\.com|luluvdo\.com)/[^\s<>\'"]+)',
                    item_text,
                )

            # Clean URLs (strip stray tag fragments/quotes)
            sublinks = [re.sub(r'[<>"\s].*$', '', s).strip() for s in sublinks if s]
            sublinks = [s for s in sublinks if s]

            if not sublinks:
                continue

            stream_url = sublinks[0]
            stream_url_2 = sublinks[1] if len(sublinks) > 1 else ''

            # Summary
            summary_match = re.search(r'<summary>(.*?)</summary>', item_text, re.DOTALL)
            description = summary_match.group(1).strip() if summary_match else ''

            # Thumbnail (poster)
            thumb_match = re.search(r'<thumbnail>(.*?)</thumbnail>', item_text, re.DOTALL)
            poster = thumb_match.group(1).strip() if thumb_match else ''

            # Fanart
            fanart_match = re.search(r'<fanart>(.*?)</fanart>', item_text, re.DOTALL)
            backdrop = fanart_match.group(1).strip() if fanart_match else poster

            # IMDB id (occasionally present)
            imdb_match = re.search(r'(tt\d{7,})', item_text)
            imdb_id = imdb_match.group(1) if imdb_match else ''

            # Year: prefer year in URL/filename, fallback to title
            year = _extract_year(stream_url) or _extract_year(stream_url_2) or _extract_year(title)

            movies.append({
                'title': title,
                'norm_title': _norm(title),
                'year': year,
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

    def _match(self, query_title, query_year, movie):
        """Strict title match with optional year preference."""
        qt = _norm(query_title)
        if not qt:
            return False

        mt = movie['norm_title']
        if not mt:
            return False

        # Exact normalized match
        if qt == mt:
            # If both have years and they mismatch by more than 1, reject
            if query_year and movie['year']:
                try:
                    if abs(int(query_year) - int(movie['year'])) > 1:
                        return False
                except ValueError:
                    pass
            return True

        # Word-set containment (all query words present in movie title) — for
        # cases like "Mission Impossible 7" vs "Mission Impossible Dead Reckoning".
        q_words = set(qt.split())
        m_words = set(mt.split())
        # Drop very short tokens that cause false matches (e.g. "a", "of")
        stop = {'a', 'an', 'the', 'of', 'and', 'or', 'to', 'in', 'on'}
        q_core = q_words - stop
        if q_core and q_core.issubset(m_words):
            if query_year and movie['year']:
                try:
                    if abs(int(query_year) - int(movie['year'])) > 1:
                        return False
                except ValueError:
                    pass
            return True

        return False

    def search(self, query, media_type='movie', **kwargs):
        """Search Bones catalog. Framework call signature:
           search(query, media_type, tmdb_id=, title=, year=, season=, episode=)
        """
        if media_type not in ('movie', 'movies'):
            return []

        title = (kwargs.get('title') or query or '').strip()
        year = str(kwargs.get('year') or '').strip()

        # Strip trailing (YEAR) from title if caller embedded it
        clean_title = re.sub(r'\s*\(?\d{4}\)?\s*$', '', title).strip()

        catalog = self._fetch_catalog()
        if not catalog:
            return []

        results = []
        for movie in catalog:
            if not self._match(clean_title, year, movie):
                continue

            quality = _parse_quality(movie['stream_url'])

            host_label = 'Streamtape' if 'streamtape' in movie['stream_url'].lower() else (
                'LuluVid' if 'luluv' in movie['stream_url'].lower() else 'Bones')

            results.append({
                'multi-part': False,
                'class': self,
                'host': host_label,
                'quality': quality,
                'label': f"[Bones] {movie['title']}",
                'title': f"[Bones] {movie['title']}",
                'rating': None,
                'views': None,
                'direct': True,
                'url': movie['stream_url'],
                'magnet': '',
                'seeds': 9999,
                'size': '',
                'is_free_link': True,
                'source': 'Bones',
            })

            if movie.get('stream_url_2'):
                q2 = _parse_quality(movie['stream_url_2'])
                host_label_2 = 'Streamtape' if 'streamtape' in movie['stream_url_2'].lower() else (
                    'LuluVid' if 'luluv' in movie['stream_url_2'].lower() else 'Bones')
                results.append({
                    'multi-part': False,
                    'class': self,
                    'host': f'{host_label_2} (Mirror)',
                    'quality': q2,
                    'label': f"[Bones Mirror] {movie['title']}",
                    'title': f"[Bones Mirror] {movie['title']}",
                    'rating': None,
                    'views': None,
                    'direct': True,
                    'url': movie['stream_url_2'],
                    'magnet': '',
                    'seeds': 9998,
                    'size': '',
                    'is_free_link': True,
                    'source': 'Bones',
                })

        xbmc.log(f'Bones: Found {len(results)} source(s) for "{clean_title}" ({year})', xbmc.LOGINFO)
        return results

    def get_catalog(self):
        return self._fetch_catalog()
