"""
SALTS Scrapers - Streamtape / Doodstream "Direct-Hoster" Sites
==============================================================
Sites that expose Streamtape AND/OR Doodstream URLs directly on their
movie/TV pages (as plain <a href> links or simple server buttons), NOT
hidden behind obfuscated iframes / JS-protected players.

Whatever Streamtape / Doodstream URL is extracted is converted to a direct
mp4/m3u8 by the existing zeus_resolvers (streamtape, d000d, dood, etc.) so
each link plays in Kodi without ResolveURL/Premium.

Scope per user request 2026-02:
  * Easy-to-scrape sites
  * Source hosters = Streamtape family + Doodstream family
  * No Mixdrop / Filemoon / Vidguard (not requested)
  * Movies + TV shows supported

Author: zeus768 (2026-02)
"""
import re
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.parse import quote_plus, urljoin

from .base_scraper import BaseScraper

ADDON = xbmcaddon.Addon()
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')


# --------------------------------------------------------------------------
# Hoster host-name patterns accepted (handled by zeus_resolvers)
# --------------------------------------------------------------------------
STREAMTAPE_HOSTS = (
    'streamtape.com', 'streamtape.to', 'streamtape.net', 'streamtape.cc',
    'streamtape.xyz', 'streamtape.site', 'streamtape.online',
    'streamta.pe', 'stape.fun', 'shavetape.cash', 'streamadblocker.xyz',
    'streamadblocker.com',
)
DOODSTREAM_HOSTS = (
    'doodstream.com', 'dood.to', 'dood.so', 'dood.la', 'dood.ws', 'dood.cx',
    'dood.sh', 'dood.pm', 'dood.watch', 'dood.wf', 'dood.re', 'dood.li',
    'd000d.com', 'd0000d.com', 'd0o0d.com', 'ds2play.com', 'ds2video.com',
    'dooood.com', 'vidply.com',
)
ACCEPT_HOSTS = STREAMTAPE_HOSTS + DOODSTREAM_HOSTS

_HOST_RX = re.compile(
    r'https?://(?:[a-z0-9\-]+\.)*(?:' +
    '|'.join(re.escape(h) for h in ACCEPT_HOSTS) +
    r')/[A-Za-z0-9._/\?=&%\-#]+',
    re.IGNORECASE,
)


def _host_label(url):
    u = (url or '').lower()
    if any(h in u for h in STREAMTAPE_HOSTS):
        return 'Streamtape'
    if any(h in u for h in DOODSTREAM_HOSTS):
        return 'Doodstream'
    return 'Direct'


def _quality(text, url=''):
    s = f'{text} {url}'.lower()
    if '2160' in s or '4k' in s or 'uhd' in s:
        return '4K'
    if '1080' in s:
        return '1080p'
    if '720' in s:
        return '720p'
    if '480' in s or 'sd' in s:
        return '480p'
    return '720p'


def _http_get(url, referer=None, timeout=15):
    hdrs = {
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    if referer:
        hdrs['Referer'] = referer
    try:
        req = Request(url, headers=hdrs)
        resp = urlopen(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        xbmc.log(f'[ST/Dood] fetch error {url[:120]}: {e}', xbmc.LOGDEBUG)
        return ''


def _extract_host_urls(html):
    """Pull every Streamtape/Doodstream URL present anywhere in the HTML."""
    urls = set()
    for m in _HOST_RX.finditer(html or ''):
        u = m.group(0).rstrip('"\'<>)')
        urls.add(u)
    # iframes with protocol-less src
    for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', html or '', re.I):
        u = m.group(1).strip()
        if u.startswith('//'):
            u = 'https:' + u
        if any(h in u.lower() for h in ACCEPT_HOSTS):
            urls.add(u)
    return list(urls)


def _clean_title(s):
    return re.sub(r'[^a-z0-9]+', '', (s or '').lower())


# --------------------------------------------------------------------------
# Base: search → page → extract hoster links
# --------------------------------------------------------------------------
class _STDoodSiteBase(BaseScraper):
    """Generic flow:
       1. _search(query) -> list of result-page urls (title -> page)
       2. _page(url) -> html
       3. _extract_host_urls(html) -> list of Streamtape/Doodstream URLs
    """
    NAME = 'ST/Dood Base'
    BASE_URL = ''
    SEARCH_PATH = '/?s={q}'           # default WordPress-style search
    RESULT_SEL = r'h2\.entry-title\s+a|h3\s+a|\.post-title\s+a'  # informative only
    SETTING_ID = ''

    def is_enabled(self):
        return ADDON.getSetting(self.SETTING_ID) != 'false'

    # -- overridable hooks --
    def _build_search_urls(self, query):
        """Return one or more absolute search URLs to try."""
        q = quote_plus(query)
        return [self.BASE_URL + self.SEARCH_PATH.format(q=q)]

    def _parse_results(self, html):
        """Return list of (title, absolute_url) result tuples."""
        out = []
        for m in re.finditer(
            r'<(?:h[1-4]|div)[^>]*class="[^"]*(?:entry-title|post-title|movie-title|title)[^"]*"[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
            html, re.I,
        ):
            url, title = m.group(1), m.group(2).strip()
            out.append((title, urljoin(self.BASE_URL, url)))
        if not out:
            # Fallback: any <a> that looks like a post permalink
            for m in re.finditer(
                r'<a[^>]+href="([^"]+/(?:movie|film|tv|show|series|download|watch)[^"]*)"[^>]*>([^<]{5,120})</a>',
                html, re.I,
            ):
                url, title = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
                out.append((title, urljoin(self.BASE_URL, url)))
        return out

    # -- main search --
    def _search(self, query, media_type='movie'):
        sources = []
        norm_q = _clean_title(query)
        seen = set()
        for search_url in self._build_search_urls(query):
            html = _http_get(search_url, referer=self.BASE_URL)
            if not html:
                continue
            for title, url in self._parse_results(html)[:8]:
                if url in seen:
                    continue
                seen.add(url)
                # Relevance filter (very lax)
                if norm_q and not any(
                    tok in _clean_title(title) for tok in norm_q.split() if tok
                ):
                    # still allow if strong overlap
                    if _clean_title(query)[:8] not in _clean_title(title):
                        pass  # keep; many sites mangle titles
                page_html = _http_get(url, referer=search_url)
                if not page_html:
                    continue
                for host_url in _extract_host_urls(page_html):
                    label = _host_label(host_url)
                    sources.append({
                        'url': host_url,
                        'host': label,
                        'quality': _quality(title, host_url),
                        'direct': False,
                        'scraper': self.NAME,
                        'type': 'stream',
                        'name': f'{self.NAME} | {label} | {title[:60]}',
                        'seeds': 8900,
                    })
                if len(sources) >= 8:
                    break
            if sources:
                break
        return sources

    # -- BaseScraper abstract --
    def search(self, query, media_type='movie'):
        return self._search(query, media_type)

    def get_movie_sources(self, title, year=''):
        q = f'{title} {year}'.strip()
        return self._search(q, 'movie')

    def get_episode_sources(self, title, year, season, episode):
        try:
            s, e = int(season), int(episode)
            q = f'{title} S{s:02d}E{e:02d}'
        except Exception:
            q = f'{title} season {season} episode {episode}'
        srcs = self._search(q, 'tvshow')
        if not srcs:
            # Fallback: search show name only, then filter pages
            srcs = self._search(title, 'tvshow')
        return srcs


# --------------------------------------------------------------------------
# Concrete sites (all serve Streamtape and/or Doodstream directly)
# --------------------------------------------------------------------------

class VegaMoviesScraper(_STDoodSiteBase):
    """VegaMovies — Bollywood + Hollywood, direct Streamtape/Doodstream mirror
    links exposed as plain <a> on the post page."""
    NAME = 'VegaMovies'
    BASE_URL = 'https://vegamovies.ph'
    SEARCH_PATH = '/?s={q}'
    SETTING_ID = 'vegamovies_st_enabled'

    def _build_search_urls(self, query):
        mirrors = (
            'https://vegamovies.ph', 'https://vegamovies.la',
            'https://vegamovies.rs', 'https://vegamovies.yt',
        )
        q = quote_plus(query)
        return [f'{m}/?s={q}' for m in mirrors]


class MoviesModScraper(_STDoodSiteBase):
    """MoviesMod — heavy Streamtape + Doodstream usage on post pages."""
    NAME = 'MoviesMod'
    BASE_URL = 'https://moviesmod.chat'
    SETTING_ID = 'moviesmod_st_enabled'

    def _build_search_urls(self, query):
        mirrors = (
            'https://moviesmod.chat', 'https://moviesmod.cm',
            'https://moviesmod.day', 'https://moviesmod.fans',
        )
        q = quote_plus(query)
        return [f'{m}/?s={q}' for m in mirrors]


class HDHub4UScraper(_STDoodSiteBase):
    """HDHub4u — Bollywood / Hollywood / web series, exposes Streamtape &
    Doodstream links directly."""
    NAME = 'HDHub4u'
    BASE_URL = 'https://hdhub4u.tv'
    SETTING_ID = 'hdhub4u_st_enabled'

    def _build_search_urls(self, query):
        mirrors = (
            'https://hdhub4u.tv', 'https://hdhub4u.haus',
            'https://hdhub4u.one', 'https://hdhub4u.ms',
        )
        q = quote_plus(query)
        return [f'{m}/?s={q}' for m in mirrors]


class SkyMoviesHDScraper(_STDoodSiteBase):
    """SkyMoviesHD — classic index-style site with direct Streamtape /
    Doodstream / DoodStream links."""
    NAME = 'SkyMoviesHD'
    BASE_URL = 'https://skymovieshd.video'
    SETTING_ID = 'skymovieshd_st_enabled'

    def _build_search_urls(self, query):
        mirrors = (
            'https://skymovieshd.video', 'https://skymovieshd.nl',
            'https://skymovieshd.cv', 'https://skymovieshd.cloud',
        )
        q = quote_plus(query)
        # SkyMoviesHD uses /search.php?search=
        urls = [f'{m}/search.php?search={q}' for m in mirrors]
        urls += [f'{m}/?s={q}' for m in mirrors]
        return urls

    def _parse_results(self, html):
        out = super()._parse_results(html)
        # SkyMovies specific: <a href="/Hollywood/...html">
        for m in re.finditer(
            r'<a[^>]+href="(/(?:Hollywood|Bollywood|Tv-Show|TV-Shows|South|Tamil)/[^"]+\.html)"[^>]*>([^<]{5,120})</a>',
            html, re.I,
        ):
            out.append((m.group(2).strip(), urljoin(self.BASE_URL, m.group(1))))
        return out


class FilmyZillaScraper(_STDoodSiteBase):
    """FilmyZilla — Bollywood + dubbed; direct Streamtape/Doodstream."""
    NAME = 'FilmyZilla'
    BASE_URL = 'https://filmyzilla13.com'
    SETTING_ID = 'filmyzilla_st_enabled'

    def _build_search_urls(self, query):
        mirrors = (
            'https://filmyzilla13.com', 'https://filmyzillas.com',
            'https://filmyzilla.beauty', 'https://filmyzilla.day',
        )
        q = quote_plus(query)
        return [f'{m}/?s={q}' for m in mirrors]


class MovieRulzScraper(_STDoodSiteBase):
    """5MovieRulz / Movierulz — South + Hollywood. Exposes Streamtape +
    Doodstream links."""
    NAME = 'MovieRulz'
    BASE_URL = 'https://www.5movierulz.chat'
    SETTING_ID = 'movierulz_st_enabled'

    def _build_search_urls(self, query):
        mirrors = (
            'https://www.5movierulz.chat', 'https://www.5movierulz.hair',
            'https://www.5movierulz.soccer', 'https://www.5movierulz.meme',
        )
        q = quote_plus(query)
        return [f'{m}/?s={q}' for m in mirrors]


class MKVCinemasScraper(_STDoodSiteBase):
    """MKVCinemas — post pages expose Streamtape and Doodstream mirrors."""
    NAME = 'MKVCinemas'
    BASE_URL = 'https://mkvcinemas.mx'
    SETTING_ID = 'mkvcinemas_st_enabled'

    def _build_search_urls(self, query):
        mirrors = (
            'https://mkvcinemas.mx', 'https://mkvcinemas.cloud',
            'https://mkvcinemas.shop', 'https://mkvcinemas.haus',
        )
        q = quote_plus(query)
        return [f'{m}/?s={q}' for m in mirrors]


class Bolly4UScraper(_STDoodSiteBase):
    """Bolly4U — Bollywood direct Streamtape links."""
    NAME = 'Bolly4U'
    BASE_URL = 'https://bolly4u.show'
    SETTING_ID = 'bolly4u_st_enabled'

    def _build_search_urls(self, query):
        mirrors = (
            'https://bolly4u.show', 'https://bolly4u.haus',
            'https://bolly4u.cam', 'https://bolly4u.soccer',
        )
        q = quote_plus(query)
        return [f'{m}/?s={q}' for m in mirrors]


class MoviesDaScraper(_STDoodSiteBase):
    """MoviesDa — Tamil / South content; exposes Streamtape & Doodstream
    mirrors directly."""
    NAME = 'MoviesDa'
    BASE_URL = 'https://moviesda.click'
    SETTING_ID = 'moviesda_st_enabled'

    def _build_search_urls(self, query):
        mirrors = (
            'https://moviesda.click', 'https://moviesda.fans',
            'https://moviesda.day', 'https://moviesda.haus',
        )
        q = quote_plus(query)
        return [f'{m}/?s={q}' for m in mirrors]


class KatMovieHDScraper(_STDoodSiteBase):
    """KatMovieHD — multi-audio releases with direct Streamtape + Doodstream
    hoster links listed on each post."""
    NAME = 'KatMovieHD'
    BASE_URL = 'https://katmoviehd.skin'
    SETTING_ID = 'katmoviehd_st_enabled'

    def _build_search_urls(self, query):
        mirrors = (
            'https://katmoviehd.skin', 'https://katmoviehd.so',
            'https://katmoviehd.is', 'https://katmoviehd.diy',
        )
        q = quote_plus(query)
        return [f'{m}/?s={q}' for m in mirrors]


# --------------------------------------------------------------------------
# Export list
# --------------------------------------------------------------------------
ST_DOOD_DIRECT_SCRAPERS = [
    VegaMoviesScraper,
    MoviesModScraper,
    HDHub4UScraper,
    SkyMoviesHDScraper,
    FilmyZillaScraper,
    MovieRulzScraper,
    MKVCinemasScraper,
    Bolly4UScraper,
    MoviesDaScraper,
    KatMovieHDScraper,
]
