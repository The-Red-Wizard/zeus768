"""
Streamtape & LuluVdo Scrapers — External Sites Only
===================================================
Adds NEW scrapers that visit independent movie/TV sites (NOT thechains24.com)
and extract any iframe / link pointing at a Streamtape or LuluVdo host.
Whatever URL is returned is automatically converted to a direct mp4/m3u8 by
the existing bones_resolver, so it plays in Kodi without ResolveURL.

Author: zeus768 (2026-02)
"""
import re
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.parse import quote_plus, urljoin, urlencode

from .base_scraper import BaseScraper

ADDON = xbmcaddon.Addon()
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)

# Hosts treated as directly playable (resolved by bones_resolver, no debrid)
ACCEPT_HOSTS = (
    'streamtape.com', 'streamtape.to', 'streamtape.net', 'streamtape.cc',
    'streamta.pe', 'streamtape.xyz', 'streamtape.site', 'streamtape.online',
    'streamadblocker.xyz', 'stape.fun', 'shavetape.cash',
    'luluvid.com', 'luluvdo.com',
)


def _quality(url):
    u = (url or '').lower()
    if '2160' in u or '4k' in u or 'uhd' in u:
        return '4K'
    if '1080' in u:
        return '1080p'
    if '720' in u:
        return '720p'
    if '480' in u:
        return '480p'
    return '720p'


def _host_label(url):
    u = (url or '').lower()
    if any(h in u for h in (
        'streamtape', 'streamta.pe', 'stape.fun', 'shavetape', 'streamadblocker',
    )):
        return 'Streamtape'
    if 'luluvdo' in u or 'luluvid' in u:
        return 'LuluVdo'
    return 'Direct'


def _is_accept(url):
    u = (url or '').lower()
    return any(h in u for h in ACCEPT_HOSTS)


def _http_get(url, referer=None, timeout=15):
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    if referer:
        headers['Referer'] = referer
    try:
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        xbmc.log(f'[ST/Lulu] fetch error {url[:120]}: {e}', xbmc.LOGDEBUG)
        return ''


def _extract_host_links(html):
    """Find all streamtape/luluvdo URLs in arbitrary HTML/JSON."""
    out = set()
    # iframes
    for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE):
        u = m.group(1).strip()
        if u.startswith('//'):
            u = 'https:' + u
        if _is_accept(u):
            out.add(u)
    # generic urls anywhere in the markup / JSON
    for m in re.finditer(
        r'(https?://(?:streamtape\.[a-z]+|streamta\.pe|stape\.fun|shavetape\.[a-z]+|'
        r'streamadblocker\.[a-z]+|luluvdo\.com|luluvid\.com)/[A-Za-z0-9._/?=&%-]+)',
        html, re.IGNORECASE,
    ):
        out.add(m.group(1))
    return list(out)


# ===========================================================================
# SITE-SCRAPE BASE
# ===========================================================================
class _HostSiteScraper(BaseScraper):
    """Search a movie/TV site and extract iframes pointing at streamtape/luluvdo."""
    NAME = 'HostSite'
    BASE_URL = ''
    SEARCH_PATH = ''            # may include {q} placeholder
    SETTING_ID = ''
    SUPPORTED_TYPES = ('movie', 'movies', 'tvshow', 'tv', 'episode')
    is_free = True

    def is_enabled(self):
        if not self.SETTING_ID:
            return True
        return ADDON.getSetting(self.SETTING_ID) != 'false'

    def _build_search_url(self, query):
        path = self.SEARCH_PATH.format(q=quote_plus(query))
        return urljoin(self.BASE_URL, path)

    # subclasses override to find the watch-page links from search results html
    def _parse_search_results(self, html):
        return re.findall(
            r'href=["\'](/(?:movie|tv|watch|play|series|film)/[^"\']+)["\']',
            html,
        )

    def _fetch_watch_page(self, url):
        return _http_get(url, referer=self.BASE_URL, timeout=15)

    def search(self, query, media_type='movie', **kwargs):
        if media_type not in self.SUPPORTED_TYPES:
            return []
        title = (kwargs.get('title') or query or '').strip()
        year = str(kwargs.get('year') or '').strip()
        season = str(kwargs.get('season') or '').strip()
        episode = str(kwargs.get('episode') or '').strip()

        if season and episode:
            q = f'{title} S{int(season):02d}E{int(episode):02d}'
        elif year:
            q = f'{title} {year}'
        else:
            q = title

        try:
            search_url = self._build_search_url(q)
        except Exception:
            return []

        html = _http_get(search_url, referer=self.BASE_URL, timeout=12)
        if not html:
            return []

        watch_paths = self._parse_search_results(html)
        if not watch_paths:
            return []

        results = []
        for p in watch_paths[:5]:
            watch_url = urljoin(self.BASE_URL, p)
            page_html = self._fetch_watch_page(watch_url)
            if not page_html:
                continue
            for url in _extract_host_links(page_html):
                results.append({
                    'multi-part': False,
                    'host': _host_label(url),
                    'quality': _quality(url),
                    'label': f"[{self.NAME}] {title}",
                    'title': f"[{self.NAME}] {title}",
                    'rating': None,
                    'views': None,
                    'direct': True,
                    'url': url,
                    'magnet': '',
                    'seeds': 9000,
                    'size': '',
                    'is_free_link': True,
                    'source': self.NAME,
                })
            if results:
                break  # stop after first page that yielded
        xbmc.log(
            f'[ST/Lulu] {self.NAME}: {len(results)} sources for "{q}"',
            xbmc.LOGINFO,
        )
        return results


# ===========================================================================
# SITE-SCRAPE CONCRETE SCRAPERS (independent sites, NOT thechains24.com)
# ===========================================================================
class GokuStreamtapeScraper(_HostSiteScraper):
    """goku.sx — many movies & TV with streamtape mirrors."""
    NAME = 'Goku-ST'
    BASE_URL = 'https://goku.sx/'
    SEARCH_PATH = 'search/{q}'
    SETTING_ID = 'site_goku_st_enabled'

    def _parse_search_results(self, html):
        return re.findall(r'href=["\'](/(?:movie|tv|watch)/[^"\']+)["\']', html)


class GokuTVStreamtapeScraper(_HostSiteScraper):
    """gokutv.net mirror — same network as goku.sx."""
    NAME = 'GokuTV-ST'
    BASE_URL = 'https://gokutv.net/'
    SEARCH_PATH = 'search/{q}'
    SETTING_ID = 'site_gokutv_st_enabled'

    def _parse_search_results(self, html):
        return re.findall(r'href=["\'](/(?:watch|movie|tv-series|film)/[^"\']+)["\']', html)


class FrenchStreamScraper(_HostSiteScraper):
    """french-stream.lol — French streaming aggregator using streamtape mirrors."""
    NAME = 'FrenchStream-ST'
    BASE_URL = 'https://french-stream.lol/'
    SEARCH_PATH = '?s={q}'
    SETTING_ID = 'site_frstream_st_enabled'

    def _parse_search_results(self, html):
        return re.findall(r'href=["\'](https?://french-stream\.lol/[^"\']+)["\']', html)

    def _build_search_url(self, query):
        return f'{self.BASE_URL}?s={quote_plus(query)}'


class PutlockerFmScraper(_HostSiteScraper):
    """putlockers.fm — uses streamtape/luluvdo as mirror servers."""
    NAME = 'PutlockerFM-ST'
    BASE_URL = 'https://putlockers.fm/'
    SEARCH_PATH = 'search/{q}'
    SETTING_ID = 'site_putlocker_st_enabled'


class MyFlixerHostScraper(_HostSiteScraper):
    """myflixerz.to — popular streamer with streamtape/luluvdo servers."""
    NAME = 'MyFlixerz-ST'
    BASE_URL = 'https://myflixerz.to/'
    SEARCH_PATH = 'search/{q}'
    SETTING_ID = 'site_myflixerz_st_enabled'

    def _parse_search_results(self, html):
        return re.findall(r'href=["\'](/(?:movie|tv)/[^"\']+)["\']', html)


class FmoviesHostScraper(_HostSiteScraper):
    """fmovies24.to — multi-server with streamtape/luluvdo embeds."""
    NAME = 'FMovies-ST'
    BASE_URL = 'https://fmovies24.to/'
    SEARCH_PATH = 'search/{q}'
    SETTING_ID = 'site_fmovies_st_enabled'

    def _parse_search_results(self, html):
        return re.findall(r'href=["\'](/(?:movie|tv|watch)/[^"\']+)["\']', html)


class SoaperHostScraper(_HostSiteScraper):
    """soaper.live / .tv — TV-show focused, uses external embeds."""
    NAME = 'Soaper-ST'
    BASE_URL = 'https://soaper.live/'
    SEARCH_PATH = 'search.html?keyword={q}'
    SETTING_ID = 'site_soaper_st_enabled'

    def _parse_search_results(self, html):
        return re.findall(r'href=["\'](/(?:movie|tv)_[^"\']+\.html)["\']', html)


class HdtodayHostScraper(_HostSiteScraper):
    """hdtoday.cc — multi-server streaming, streamtape mirror common."""
    NAME = 'HDToday-ST'
    BASE_URL = 'https://hdtoday.cc/'
    SEARCH_PATH = 'search/{q}'
    SETTING_ID = 'site_hdtoday_st_enabled'

    def _parse_search_results(self, html):
        return re.findall(r'href=["\'](/(?:movie|tv|watch-movie|watch-tv)/[^"\']+)["\']', html)


class FlixtorHostScraper(_HostSiteScraper):
    """flixtor.video — has streamtape & luluvdo as alt-servers."""
    NAME = 'Flixtor-ST'
    BASE_URL = 'https://flixtor.video/'
    SEARCH_PATH = 'search/{q}'
    SETTING_ID = 'site_flixtor_st_enabled'

    def _parse_search_results(self, html):
        return re.findall(r'href=["\'](/(?:movie|tv|watch)/[^"\']+)["\']', html)


class MoviesJoyHostScraper(_HostSiteScraper):
    """moviesjoy.plus — has streamtape mirrors per title."""
    NAME = 'MoviesJoy-ST'
    BASE_URL = 'https://moviesjoy.plus/'
    SEARCH_PATH = 'search/{q}'
    SETTING_ID = 'site_moviesjoy_st_enabled'

    def _parse_search_results(self, html):
        return re.findall(r'href=["\'](/(?:movie|tv|watch)/[^"\']+)["\']', html)


# ===========================================================================
# DUCKDUCKGO MIRROR FALLBACK
# Last resort: query DuckDuckGo HTML for "<title> streamtape" and pluck embed
# pages directly. Useful when curated site scrapers don't cover the title.
# ===========================================================================
class DDGStreamtapeScraper(BaseScraper):
    NAME = 'DDG-Search'
    is_free = True

    def is_enabled(self):
        # opt-in (off by default — slower, can be noisy)
        return ADDON.getSetting('ddg_st_enabled') == 'true'

    def _ddg(self, query):
        url = 'https://html.duckduckgo.com/html/?' + urlencode({'q': query})
        html = _http_get(url, referer='https://duckduckgo.com/', timeout=15)
        if not html:
            return []
        urls = re.findall(
            r'(https?://(?:streamtape\.[a-z]+|streamta\.pe|luluvdo\.com|luluvid\.com)'
            r'/[A-Za-z0-9_/-]+)',
            html, re.IGNORECASE,
        )
        return list({u for u in urls if _is_accept(u)})

    def search(self, query, media_type='movie', **kwargs):
        title = (kwargs.get('title') or query or '').strip()
        year = str(kwargs.get('year') or '').strip()
        if not title:
            return []
        results = []
        for term in ('streamtape', 'luluvdo'):
            q = f'{title} {year} {term}' if year else f'{title} {term}'
            for url in self._ddg(q)[:6]:
                results.append({
                    'multi-part': False,
                    'host': _host_label(url),
                    'quality': _quality(url),
                    'label': f"[DDG] {title}",
                    'title': f"[DDG] {title}",
                    'rating': None,
                    'views': None,
                    'direct': True,
                    'url': url,
                    'magnet': '',
                    'seeds': 8000,
                    'size': '',
                    'is_free_link': True,
                    'source': self.NAME,
                })
        return results


# Convenience list (consumed by scrapers/__init__.py).
ST_LULU_SCRAPERS = [
    GokuStreamtapeScraper,
    GokuTVStreamtapeScraper,
    FrenchStreamScraper,
    PutlockerFmScraper,
    MyFlixerHostScraper,
    FmoviesHostScraper,
    SoaperHostScraper,
    HdtodayHostScraper,
    FlixtorHostScraper,
    MoviesJoyHostScraper,
    DDGStreamtapeScraper,
]
