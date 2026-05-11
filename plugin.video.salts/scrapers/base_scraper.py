"""
SALTS Scrapers - Base Scraper Class
Revived by zeus768 for Kodi 21+
Uses native urllib (no external requests module)

v2.9.16 hardening:
 - Tolerant SSL context (fixes "CERTIFICATE_VERIFY_FAILED" on Windows builds
   that ship an outdated CA bundle -> PrimeWire, some mirror sites).
 - Transparent gzip / deflate decoding so sites that always send gzipped
   bodies (1337x, torrentgalaxy mirrors, ...) don't return garbage HTML.
 - Modern desktop Chrome User-Agent + full browser header set so
   Cloudflare / DDoS-Guard edge nodes stop returning 403 on simple
   GETs (1337x, rargb, torrentfunk).
 - Short connect + read timeout per site so one dead mirror cannot
   burn the whole 60 s Stream-All-The-Sources budget.
"""
import abc
import re
import json
import ssl
import gzip
import zlib
import io
import socket

import xbmc
import xbmcaddon

from urllib.request import urlopen, Request, build_opener, HTTPSHandler, HTTPHandler
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin, urlparse, quote_plus

from salts_lib import log_utils
from salts_lib.db_utils import DB_Connection
from salts_lib.constants import USER_AGENT, DEFAULT_TIMEOUT, QUALITY_PATTERNS

ADDON = xbmcaddon.Addon()

# ---------------------------------------------------------------------------
# Shared HTTPS context - disables cert verification so outdated CA bundles
# (common on Windows / FireStick builds) don't brick entire scrapers.
# Scrapers only fetch public HTML search pages, no auth tokens are sent,
# so this is safe for this use case.
# ---------------------------------------------------------------------------
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# Modern Chrome on Windows 10 - matches what Cloudflare fingerprints expect.
_DEFAULT_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36'
)


def _decode_body(resp):
    """Read a urllib response, transparently decoding gzip/deflate."""
    raw = resp.read()
    enc = (resp.headers.get('Content-Encoding') or '').lower()
    try:
        if enc == 'gzip':
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        elif enc == 'deflate':
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    except Exception:
        # If decoding fails just fall back to the raw bytes - callers use
        # errors='replace' so they'll still get *something* to parse.
        pass
    return raw.decode('utf-8', errors='replace')


class _SessionResponse:
    """Minimal `requests.Response`-like object returned by the session shim.
    Only the attributes actually used by legacy SALTS scrapers are provided:
        .status_code, .text, .content, .ok, .url, .headers, .json()
    """
    __slots__ = ('status_code', 'text', 'content', 'url', 'headers')

    def __init__(self, status_code=0, text='', content=b'', url='', headers=None):
        self.status_code = status_code
        self.text = text
        self.content = content
        self.url = url
        self.headers = headers or {}

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def json(self):
        return json.loads(self.text) if self.text else None


class _SessionShim:
    """requests.Session() compatibility shim on top of urllib.

    Several scrapers (yts, eztv, tpb, torrentgalaxy, limetorrents, rarbg,
    torrentz2, solarmovie, movie4k, primewire, watchseries, extra,
    torrentapi, jackett, prowlarr) were ported from the `requests` library
    and still call `self.session.get(url, params=, headers=, timeout=)`.
    Without this shim they raised AttributeError on every call, which is
    why users only ever saw results from a handful of scrapers.
    """

    def __init__(self, scraper):
        self._scraper = scraper

    def get(self, url, params=None, headers=None, timeout=None, allow_redirects=True, **_):
        return self._request('GET', url, params=params, headers=headers, timeout=timeout)

    def post(self, url, params=None, data=None, json=None, headers=None, timeout=None, **_):
        return self._request('POST', url, params=params, data=data or json, headers=headers, timeout=timeout)

    def _request(self, method, url, params=None, data=None, headers=None, timeout=None):
        # Build URL + params
        if params:
            qs = '&'.join(f'{k}={quote_plus(str(v))}' for k, v in params.items())
            sep = '&' if '?' in url else '?'
            url = f'{url}{sep}{qs}'
        hdrs = dict(self._scraper._headers)
        try:
            p = urlparse(url)
            if p.scheme and p.netloc:
                hdrs.setdefault('Referer', f'{p.scheme}://{p.netloc}/')
        except Exception:
            pass
        if headers:
            hdrs.update(headers)
        post_data = None
        if data is not None:
            if isinstance(data, dict):
                post_data = '&'.join(f'{k}={quote_plus(str(v))}' for k, v in data.items()).encode('utf-8')
                hdrs.setdefault('Content-Type', 'application/x-www-form-urlencoded')
            elif isinstance(data, str):
                post_data = data.encode('utf-8')
            elif isinstance(data, bytes):
                post_data = data
        t = timeout if timeout is not None else self._scraper.timeout
        try:
            t = float(t)
        except Exception:
            t = self._scraper.timeout
        t = min(max(t, 3), 15)
        try:
            req = Request(url, data=post_data, headers=hdrs, method=method)
            resp = urlopen(req, timeout=t, context=_SSL_CTX)
            text = _decode_body(resp)
            return _SessionResponse(
                status_code=getattr(resp, 'status', 200) or 200,
                text=text,
                content=text.encode('utf-8', errors='replace'),
                url=getattr(resp, 'url', url),
                headers=dict(resp.headers),
            )
        except HTTPError as e:
            try:
                body = _decode_body(e)
            except Exception:
                body = ''
            return _SessionResponse(status_code=e.code, text=body, url=url, headers=dict(getattr(e, 'headers', {}) or {}))
        except Exception as e:
            log_utils.log_error(f'{self._scraper.NAME}: session.{method} error for {url}: {e}')
            return _SessionResponse(status_code=0, text='', url=url)


class BaseScraper(abc.ABC):
    """Abstract base class for all scrapers"""

    BASE_URL = ''
    NAME = 'Base'

    def __init__(self, timeout=DEFAULT_TIMEOUT):
        # Hard per-request ceiling - one scraper must never monopolise the
        # global 60s Stream-All-The-Sources budget.
        try:
            t = float(timeout)
        except Exception:
            t = 15
        self.timeout = min(max(t, 5), 15)
        self.db = DB_Connection()
        self._headers = {
            'User-Agent': _DEFAULT_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        # Legacy `requests.Session`-style shim.  Sixteen child scrapers were
        # ported from `requests` and still call `self.session.get(...)` during
        # mirror probing / search.  Without this shim they crashed with
        # `AttributeError: session` on every Stream-All-The-Sources run, which
        # is the single biggest reason the user only saw "a few" scrapers.
        self.session = _SessionShim(self)

    @classmethod
    def get_name(cls):
        """Get scraper name"""
        return cls.NAME

    def is_enabled(self):
        """Check if scraper is enabled"""
        setting_id = f'{self.NAME.lower().replace(" ", "_")}_enabled'
        return ADDON.getSetting(setting_id) != 'false'

    def _http_get(self, url, params=None, data=None, headers=None, cache_limit=8):
        """Make HTTP GET/POST request with caching using native urllib"""
        cache_url = url + str(params or {})

        # Check cache
        try:
            _, cached = self.db.get_cached_url(cache_url, cache_limit)
            if cached:
                return cached
        except Exception:
            pass

        try:
            # Build URL with params
            request_url = url
            if params:
                query_str = '&'.join(f'{k}={quote_plus(str(v))}' for k, v in params.items())
                separator = '&' if '?' in url else '?'
                request_url = f'{url}{separator}{query_str}'

            # Build headers (auto-fill Referer with origin for anti-hotlink sites)
            hdrs = self._headers.copy()
            try:
                p = urlparse(request_url)
                if p.scheme and p.netloc:
                    hdrs.setdefault('Referer', f'{p.scheme}://{p.netloc}/')
                    hdrs.setdefault('Origin', f'{p.scheme}://{p.netloc}')
                    hdrs.setdefault('Host', p.netloc)
            except Exception:
                pass
            if headers:
                hdrs.update(headers)

            # Build request
            post_data = None
            if data:
                if isinstance(data, dict):
                    post_data = '&'.join(f'{k}={quote_plus(str(v))}' for k, v in data.items()).encode('utf-8')
                    hdrs['Content-Type'] = 'application/x-www-form-urlencoded'
                elif isinstance(data, str):
                    post_data = data.encode('utf-8')
                elif isinstance(data, bytes):
                    post_data = data

            req = Request(request_url, data=post_data, headers=hdrs)
            resp = urlopen(req, timeout=self.timeout, context=_SSL_CTX)
            html = _decode_body(resp)

            # Cache the response
            try:
                self.db.cache_url(cache_url, html)
            except Exception:
                pass

            return html
        except (HTTPError,) as e:
            log_utils.log_error(f'{self.NAME}: HTTP error for {url}: {e}')
            return ''
        except (URLError, socket.timeout, ssl.SSLError) as e:
            log_utils.log_error(f'{self.NAME}: HTTP error for {url}: {e}')
            return ''
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: HTTP error for {url}: {e}')
            return ''

    def _http_get_json(self, url, params=None, headers=None, cache_limit=8):
        """Make HTTP GET and return parsed JSON"""
        # JSON endpoints prefer application/json Accept header
        hdrs = {'Accept': 'application/json, text/plain, */*'}
        if headers:
            hdrs.update(headers)
        html = self._http_get(url, params=params, headers=hdrs, cache_limit=cache_limit)
        if html:
            try:
                return json.loads(html)
            except Exception:
                pass
        return None

    def _parse_quality(self, text):
        """Parse quality from text"""
        text = text.lower()

        for quality, patterns in QUALITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return quality

        return 'SD'

    def _parse_size(self, size_str):
        """Parse size string to formatted size"""
        if not size_str:
            return 'Unknown'

        size_str = size_str.strip().upper()

        if re.match(r'[\d.]+\s*(B|KB|MB|GB|TB)', size_str):
            return size_str

        return size_str

    def _extract_hash(self, text):
        """Extract info hash from magnet or text"""
        match = re.search(r'btih:([a-fA-F0-9]{40})', text)
        if match:
            return match.group(1).lower()

        match = re.search(r'btih:([a-zA-Z2-7]{32})', text)
        if match:
            return match.group(1).lower()

        match = re.search(r'\b([a-fA-F0-9]{40})\b', text)
        if match:
            return match.group(1).lower()

        return None

    def _clean_title(self, title):
        """Clean title for comparison"""
        title = title.lower()
        title = re.sub(r'[^\w\s]', '', title)
        title = ' '.join(title.split())
        return title

    @abc.abstractmethod
    def search(self, query, media_type='movie'):
        """Search for content. Returns list of result dicts."""
        raise NotImplementedError

    def get_movie_sources(self, title, year=''):
        """Get sources for a movie"""
        query = title
        if year:
            query = f'{title} {year}'
        return self.search(query, 'movie')

    def get_episode_sources(self, title, year, season, episode):
        """Get sources for a TV episode"""
        query = f'{title} S{int(season):02d}E{int(episode):02d}'
        return self.search(query, 'tvshow')


class TorrentScraper(BaseScraper):
    """Base class for torrent site scrapers"""

    def _make_magnet(self, info_hash, name):
        """Create magnet link from hash and name"""
        trackers = [
            'udp://tracker.opentrackr.org:1337/announce',
            'udp://open.stealth.si:80/announce',
            'udp://tracker.torrent.eu.org:451/announce',
            'udp://tracker.bittor.pw:1337/announce',
            'udp://public.popcorn-tracker.org:6969/announce',
            'udp://tracker.dler.org:6969/announce',
            'udp://exodus.desync.com:6969',
            'udp://open.demonii.com:1337/announce'
        ]

        tracker_str = '&tr='.join([quote_plus(t) for t in trackers])
        return f'magnet:?xt=urn:btih:{info_hash}&dn={quote_plus(name)}&tr={tracker_str}'
