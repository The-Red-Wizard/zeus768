"""
SALTS Scrapers - butterbeansrstop (srstop.link) Scraper

Scrapes TV episode streaming sources from srstop.link. The site is
Cloudflare-fronted and some content is gated behind login; this scraper
supports three escalating tiers:

1. Plain urllib GET (fastest, no deps).
2. Optional cloudscraper fallback when Cloudflare returns 403/503
   (guarded by the butterbeansrstop_cloudscraper setting).
3. Optional session login using srstop.link credentials stored in
   butterbeansrstop_username / butterbeansrstop_password settings -
   when present, a logged-in cookie jar is reused across requests
   which also exposes the embed-selector hrefs that normally render
   empty on anonymous requests.

Episode page parser reads each <a class="embed-selector"> entry and
extracts the hoster from the favicon background-image (or the href if
a logged-in session exposes one) plus quality from the sibling span
class markers (vris1080 / vris720 / vris480 / vrislow).
"""
import re
import json
import os
from http.cookiejar import LWPCookieJar
from urllib.parse import urljoin, quote_plus, urlencode, urlparse
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup

try:
    import xbmc
    import xbmcaddon
    import xbmcvfs
    ADDON = xbmcaddon.Addon()
    _PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
except Exception:
    ADDON = None
    _PROFILE = '/tmp'

from .base_scraper import BaseScraper
from salts_lib import log_utils


QUALITY_CLASS_MAP = {
    'vris1080': '1080p',
    'vris720': '720p',
    'vris480': 'SD',
    'vrislow': 'SD',
}


def _slugify(title):
    """Convert a show title to srstop.link slug format."""
    t = title.lower()
    t = re.sub(r"[\'\.]", '', t)
    t = re.sub(r"[^a-z0-9]+", '-', t)
    return t.strip('-')


def _setting(key, default=''):
    if ADDON is None:
        return default
    try:
        val = ADDON.getSetting(key)
        return val if val is not None else default
    except Exception:
        return default


class ButterbeanSRStopScraper(BaseScraper):
    """butterbeansrstop - srstop.link TV streaming scraper."""

    BASE_URL = 'https://srstop.link'
    NAME = 'butterbeansrstop'

    MIRRORS = [
        'https://srstop.link',
    ]

    _COOKIE_FILE = os.path.join(_PROFILE, 'butterbeansrstop_cookies.lwp')

    def __init__(self, timeout=30):
        super().__init__(timeout)
        self._cookie_jar = LWPCookieJar(self._COOKIE_FILE)
        try:
            if os.path.exists(self._COOKIE_FILE):
                self._cookie_jar.load(ignore_discard=True)
        except Exception:
            pass
        self._opener = build_opener(HTTPCookieProcessor(self._cookie_jar))
        self._logged_in = False
        self._cf_client = None  # lazy cloudscraper instance

    # -----------------------------------------------------------------
    # Enabled / settings helpers
    # -----------------------------------------------------------------
    def is_enabled(self):
        return _setting('butterbeansrstop_enabled', 'true').lower() != 'false'

    def _use_cloudscraper(self):
        return _setting('butterbeansrstop_cloudscraper', 'true').lower() != 'false'

    def _credentials(self):
        return (
            _setting('butterbeansrstop_username', '').strip(),
            _setting('butterbeansrstop_password', '').strip(),
        )

    # -----------------------------------------------------------------
    # HTTP layer with CF + login fallbacks
    # -----------------------------------------------------------------
    def _fetch(self, url, params=None, data=None, allow_cf=True):
        """Fetch URL returning body text. Uses cookie jar + CF fallback."""
        full = url
        if params:
            sep = '&' if '?' in url else '?'
            full = f'{url}{sep}{urlencode(params)}'

        req = Request(full, headers=self._headers, method='POST' if data else 'GET')
        if data is not None:
            if isinstance(data, dict):
                body = urlencode(data).encode('utf-8')
                req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            elif isinstance(data, str):
                body = data.encode('utf-8')
            else:
                body = data
            req.data = body

        try:
            resp = self._opener.open(req, timeout=self.timeout)
            html = resp.read().decode('utf-8', errors='replace')
            try:
                self._cookie_jar.save(ignore_discard=True)
            except Exception:
                pass
            return html
        except HTTPError as e:
            if allow_cf and e.code in (403, 503) and self._use_cloudscraper():
                return self._fetch_via_cloudscraper(full, data=data)
            log_utils.log_error(f'{self.NAME}: HTTP {e.code} for {full}')
            return ''
        except (URLError, Exception) as e:
            log_utils.log_error(f'{self.NAME}: fetch error {full}: {e}')
            return ''

    def _fetch_via_cloudscraper(self, url, data=None):
        """Optional cloudscraper fallback. Silently no-op if not installed."""
        try:
            if self._cf_client is None:
                import cloudscraper  # noqa: WPS433
                self._cf_client = cloudscraper.create_scraper()
                # share cookies with our jar
                for c in self._cookie_jar:
                    self._cf_client.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
            r = (self._cf_client.post(url, data=data, timeout=self.timeout)
                 if data else self._cf_client.get(url, timeout=self.timeout))
            # mirror cookies back into our jar
            try:
                for c in self._cf_client.cookies:
                    self._cookie_jar.set_cookie(
                        __import__('http.cookiejar', fromlist=['Cookie']).Cookie(
                            version=0, name=c.name, value=c.value,
                            port=None, port_specified=False,
                            domain=c.domain or urlparse(url).netloc,
                            domain_specified=True, domain_initial_dot=False,
                            path=c.path or '/', path_specified=True,
                            secure=c.secure, expires=c.expires, discard=False,
                            comment=None, comment_url=None, rest={},
                        )
                    )
                self._cookie_jar.save(ignore_discard=True)
            except Exception:
                pass
            return r.text if r.status_code < 400 else ''
        except ImportError:
            log_utils.log_warning(f'{self.NAME}: cloudscraper unavailable (pip install cloudscraper)')
            return ''
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: cloudscraper error: {e}')
            return ''

    def _http_get(self, url, params=None, data=None, headers=None, cache_limit=8):
        """Override BaseScraper to use our cookie/CF-aware fetcher + cache."""
        cache_url = url + str(params or {}) + ('P' if data else '')
        _, cached = self.db.get_cached_url(cache_url, cache_limit)
        if cached:
            return cached
        html = self._fetch(url, params=params, data=data)
        if html:
            self.db.cache_url(cache_url, html)
        return html

    # -----------------------------------------------------------------
    # Login (optional)
    # -----------------------------------------------------------------
    def _ensure_login(self):
        if self._logged_in:
            return True
        user, pwd = self._credentials()
        if not user or not pwd:
            return False
        html = self._fetch(f'{self.BASE_URL}/index.php',
                           data={'username': user, 'password': pwd, 'login': 'Login'},
                           allow_cf=True)
        # Site returns a logout link when auth succeeds
        if html and ('logout' in html.lower() or 'welcome' in html.lower()):
            self._logged_in = True
            try:
                os.makedirs(_PROFILE, exist_ok=True)
                self._cookie_jar.save(ignore_discard=True)
            except Exception:
                pass
            return True
        return False

    # -----------------------------------------------------------------
    # Required BaseScraper entry point
    # -----------------------------------------------------------------
    def search(self, query, media_type='tvshow'):
        if media_type == 'movie':
            return []

        m = re.search(r'(.+?)\s+s(\d{1,2})e(\d{1,2})', query, re.IGNORECASE)
        if m:
            show_title = m.group(1).strip()
            season = int(m.group(2))
            episode = int(m.group(3))
            return self._get_episode_sources(show_title, season, episode)

        return self._search_shows(query)

    def get_movie_sources(self, title, year=''):
        return []

    def get_episode_sources(self, title, year, season, episode):
        try:
            return self._get_episode_sources(title, int(season), int(episode))
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: episode source error: {e}')
            return []

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _search_shows(self, query):
        results = []
        try:
            self._ensure_login()
            search_url = f'{self.BASE_URL}/index.php'
            params = {'menu': 'search', 'query': query}
            html = self._http_get(search_url, params=params, cache_limit=1)
            if not html:
                return results

            soup = BeautifulSoup(html, 'html.parser')
            seen = set()
            for a in soup.select('a[href*="/show/"]'):
                href = a.get('href', '')
                if not href or href in seen:
                    continue
                seen.add(href)

                title = (a.get('title') or a.get_text(strip=True) or '').strip()
                if not title:
                    continue

                results.append({
                    'title': title,
                    'year': '',
                    'url': urljoin(self.BASE_URL, href),
                    'quality': 'HD',
                    'host': 'srstop.link',
                    'direct': False,
                })
            return results
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: search error: {e}')
            return results

    def _candidate_slugs(self, title):
        base = _slugify(title)
        candidates = [base]
        if base.startswith('the-'):
            candidates.append(base[4:])
        return candidates

    def _episode_url(self, slug, season, episode):
        ss = f'{season:02d}'
        ee = f'{episode:02d}'
        return f'{self.BASE_URL}/show/{slug}-s{ss}e{ee}/season/{season}/episode/{episode}'

    def _get_episode_sources(self, title, season, episode):
        sources = []

        self._ensure_login()

        episode_url = None
        for slug in self._candidate_slugs(title):
            probe = self._episode_url(slug, season, episode)
            html = self._http_get(probe, cache_limit=1)
            if html and 'listlink' in html:
                episode_url = probe
                break

        if not episode_url:
            search_results = self._search_shows(f'{title} s{season:02d}e{episode:02d}')
            target = f's{season:02d}e{episode:02d}'
            for r in search_results:
                if target in r['url'].lower():
                    episode_url = r['url']
                    break
            if not episode_url:
                show_results = self._search_shows(title)
                for r in show_results:
                    m = re.search(r'/show/([^/]+?)(?:-s\d{2}e\d{2})?(?:/|$)', r['url'])
                    if not m:
                        continue
                    slug = m.group(1)
                    probe = self._episode_url(slug, season, episode)
                    html = self._http_get(probe, cache_limit=1)
                    if html and 'listlink' in html:
                        episode_url = probe
                        break

        if not episode_url:
            return sources

        html = self._http_get(episode_url, cache_limit=0.5)
        if not html:
            return sources

        soup = BeautifulSoup(html, 'html.parser')

        for link in soup.select('a.embed-selector'):
            try:
                host = self._extract_host(link)
                quality = self._extract_quality(link)
                if not host:
                    continue

                # When logged in the real iframe URL is exposed via href /
                # data-link / onclick - prefer it over the page URL.
                direct_url = (
                    link.get('href') or link.get('data-link')
                    or link.get('data-url') or ''
                ).strip()
                if direct_url.startswith('http'):
                    url = direct_url
                    direct = False  # still an embed, ResolveURL handles it
                else:
                    url = episode_url
                    direct = False

                sources.append({
                    'url': url,
                    'host': host,
                    'quality': quality,
                    'direct': direct,
                    'extra': 'srstop.link',
                })
            except Exception:
                continue

        return sources

    @staticmethod
    def _extract_host(link_tag):
        flag = link_tag.select_one('.embed-flag')
        if flag is not None:
            style = flag.get('style', '') or ''
            m = re.search(r'domain=([^&\'")\s]+)', style)
            if m:
                return m.group(1).lower().strip()
        strong = link_tag.select_one('.embed-type strong')
        if strong is not None:
            return strong.get_text(strip=True).lower()
        return ''

    @staticmethod
    def _extract_quality(link_tag):
        for span in link_tag.select('span'):
            classes = span.get('class') or []
            for cls in classes:
                if cls in QUALITY_CLASS_MAP:
                    return QUALITY_CLASS_MAP[cls]
        return 'HD'
