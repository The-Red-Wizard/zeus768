# -*- coding: utf-8 -*-
"""
Minimal urllib-based HTTP client used by the resolver plugins.

Kept intentionally dependency-free so this module stays safely importable
inside any Kodi addon regardless of what libs are present.
"""
import gzip
import io
import zlib
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)
from http.cookiejar import CookieJar

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 15


class _NoRedirect(HTTPRedirectHandler):
    """Redirect handler that captures 30x Location instead of following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        return None


def _decode_body(resp):
    data = resp.read()
    enc = (resp.headers.get("Content-Encoding") or "").lower()
    try:
        if enc == "gzip":
            data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
        elif enc == "deflate":
            try:
                data = zlib.decompress(data)
            except zlib.error:
                data = zlib.decompress(data, -zlib.MAX_WBITS)
    except Exception:
        pass
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return data.decode("latin-1", errors="replace")


class HttpSession:
    """Lightweight urllib session with cookie jar + optional redirect control."""

    def __init__(self, follow_redirects=True, timeout=DEFAULT_TIMEOUT):
        self.cookies = CookieJar()
        handlers = [HTTPCookieProcessor(self.cookies)]
        if not follow_redirects:
            handlers.append(_NoRedirect())
        self._opener = build_opener(*handlers)
        self.timeout = timeout
        self.default_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }

    def _merge_headers(self, headers):
        h = dict(self.default_headers)
        if headers:
            h.update(headers)
        return h

    def get(self, url, headers=None, timeout=None, allow_redirect_capture=False):
        req = Request(url, headers=self._merge_headers(headers), method="GET")
        try:
            resp = self._opener.open(req, timeout=timeout or self.timeout)
            return {
                "status": resp.getcode(),
                "url": resp.geturl(),
                "headers": dict(resp.headers),
                "text": _decode_body(resp),
            }
        except HTTPError as e:
            # When not following redirects, 30x raises HTTPError carrying Location.
            if allow_redirect_capture and 300 <= e.code < 400:
                loc = e.headers.get("Location") if e.headers else None
                return {
                    "status": e.code,
                    "url": url,
                    "headers": dict(e.headers) if e.headers else {},
                    "location": loc,
                    "text": "",
                }
            return {"status": e.code, "url": url, "headers": {}, "text": "", "error": str(e)}
        except URLError as e:
            return {"status": 0, "url": url, "headers": {}, "text": "", "error": str(e)}

    def post(self, url, data=None, headers=None, timeout=None, allow_redirect_capture=False):
        body = urlencode(data or {}).encode("utf-8")
        h = self._merge_headers(headers)
        h.setdefault("Content-Type", "application/x-www-form-urlencoded")
        req = Request(url, data=body, headers=h, method="POST")
        try:
            resp = self._opener.open(req, timeout=timeout or self.timeout)
            return {
                "status": resp.getcode(),
                "url": resp.geturl(),
                "headers": dict(resp.headers),
                "text": _decode_body(resp),
            }
        except HTTPError as e:
            if allow_redirect_capture and 300 <= e.code < 400:
                loc = e.headers.get("Location") if e.headers else None
                return {
                    "status": e.code,
                    "url": url,
                    "headers": dict(e.headers) if e.headers else {},
                    "location": loc,
                    "text": "",
                }
            return {"status": e.code, "url": url, "headers": {}, "text": "", "error": str(e)}
        except URLError as e:
            return {"status": 0, "url": url, "headers": {}, "text": "", "error": str(e)}


def host_of(url):
    try:
        return (urlparse(url).netloc or "").lower().lstrip("www.")
    except Exception:
        return ""
