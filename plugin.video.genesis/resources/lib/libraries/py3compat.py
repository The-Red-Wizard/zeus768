# -*- coding: utf-8 -*-
"""
Python 2 → 3 compatibility shim for Genesis.
Import this FIRST in default.py and service.py to make all
legacy Python 2 imports work transparently in Python 3 / Kodi 21+.
"""
import sys

if sys.version_info[0] >= 3:
    import types
    import builtins
    import urllib.parse
    import urllib.request
    import urllib.error
    import http.cookiejar
    import http.client
    import html.parser
    import io
    import queue

    # ── Register old module names in sys.modules ──────────────────
    sys.modules['urlparse'] = urllib.parse
    sys.modules['cookielib'] = http.cookiejar
    sys.modules['httplib'] = http.client
    sys.modules['Queue'] = queue

    # ── Fake urllib2 module ───────────────────────────────────────
    _u2 = types.ModuleType('urllib2')
    for _attr in ('Request', 'urlopen', 'build_opener', 'install_opener',
                  'ProxyHandler', 'HTTPHandler', 'HTTPSHandler',
                  'HTTPCookieProcessor', 'HTTPErrorProcessor',
                  'AbstractHTTPHandler'):
        try:
            setattr(_u2, _attr, getattr(urllib.request, _attr))
        except AttributeError:
            pass
    _u2.HTTPError = urllib.error.HTTPError
    _u2.URLError = urllib.error.URLError
    sys.modules['urllib2'] = _u2

    # ── Fake HTMLParser module ────────────────────────────────────
    _hp = types.ModuleType('HTMLParser')
    _hp.HTMLParser = html.parser.HTMLParser
    sys.modules['HTMLParser'] = _hp

    # ── Fake StringIO module (binary compat) ──────────────────────
    _sio = types.ModuleType('StringIO')
    _sio.StringIO = io.BytesIO
    sys.modules['StringIO'] = _sio

    # ── Patch urllib for Py2-style attribute access ───────────────
    import urllib as _ulib
    _ulib.quote_plus = urllib.parse.quote_plus
    _ulib.urlencode = urllib.parse.urlencode
    _ulib.quote = urllib.parse.quote
    _ulib.unquote = urllib.parse.unquote
    _ulib.unquote_plus = urllib.parse.unquote_plus

    # ── Python 2 builtins ─────────────────────────────────────────
    builtins.unicode = str
    builtins.basestring = str
    builtins.xrange = range
    builtins.long = int
    builtins.raw_input = input
