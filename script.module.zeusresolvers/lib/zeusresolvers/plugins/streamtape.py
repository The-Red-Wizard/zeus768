# -*- coding: utf-8 -*-
"""Streamtape resolver.

Strategy (matches ResolveURL/Lambda-class scrapers):

    1. Normalise /e/<id> embed URLs to /v/<id> video pages.
    2. Fetch the page HTML.
    3. Locate every ``getElementById('XXXlink').innerHTML = <JS expression>;``
       where XXX ends in ``link`` (robotlink / norobotlink / ideoooolink ...).
    4. Evaluate the JS expression using a tiny string-only evaluator that
       handles ``'a' + 'b'`` and ``('xyz').substring(N[,M])`` slicing -- this
       is the obfuscation Streamtape uses to hide the real token.
    5. Pick the result that contains ``token=`` and the most data, build the
       final ``https://streamtape.com/get_video?...&token=...&dl=1`` URL,
       and append ``|User-Agent=...&Referer=https://streamtape.com/`` so
       Kodi's curl sends the headers the CDN expects (otherwise -> 403).
"""
import re

from .._http import USER_AGENT, HttpSession, host_of

HOSTS = [
    "streamtape.com",
    "streamtape.to",
    "streamtape.net",
    "streamtape.cc",
    "streamta.pe",
    "streamadblocker.com",
    "streamtapeadblock.art",
    "streamtapeadblocker.com",
    "strtape.cloud",
    "strtape.tech",
    "strtape.site",
    "strtapeadblock.art",
    "strtpe.link",
    "stape.fun",
    "tapeadvertisement.com",
    "watchadsontape.com",
    "shavetape.cash",
    "adblockeronstape.com",
    "adblockstreamtape.com",
    "antiadblockeronstape.com",
    "tubelessceliresolver.com",
]

REFERER = "https://streamtape.com/"

_ID_PAT = re.compile(r"streamtape[^/]*/[ev]/([A-Za-z0-9_-]+)", re.I)

# Capture every  document.getElementById('XXXlink').innerHTML = <expr>;  block.
_INNER_PAT = re.compile(
    r"getElementById\(\s*['\"]([A-Za-z0-9_]*link)['\"]\s*\)"
    r"\s*\.innerHTML\s*=\s*([^;]+);",
    re.S,
)

# JS string expression token: optional opening paren, quoted literal, optional
# closing paren, optional .substring(a) or .substring(a, b).
_JS_LITERAL_PAT = re.compile(
    r"""(?:\(\s*)?(['"])([^'"]*)\1(?:\s*\))?"""
    r"""(?:\s*\.\s*substring\(\s*(\d+)\s*(?:,\s*(\d+)\s*)?\))?""",
    re.S,
)


def matches(url):
    h = host_of(url)
    if not h:
        return False
    return any(h == d or h.endswith("." + d) for d in HOSTS)


def _eval_js_string(expr):
    """Concatenate every JS string literal in ``expr``, applying any
    trailing ``.substring(a[, b])`` slice. Anything that isn't a literal
    (operators, whitespace, parens) is ignored.
    """
    parts = []
    for m in _JS_LITERAL_PAT.finditer(expr):
        s = m.group(2)
        a = m.group(3)
        b = m.group(4)
        if a is not None:
            ai = int(a)
            if b is not None:
                s = s[ai:int(b)]
            else:
                s = s[ai:]
        parts.append(s)
    return "".join(parts)


def _build_headers_suffix():
    """Kodi pipe-suffix HTTP headers for the resolved URL."""
    return f"|User-Agent={USER_AGENT}&Referer={REFERER}"


def resolve(url):
    # 1. Normalise embed -> video page
    m = _ID_PAT.search(url)
    if not m:
        return None
    video_id = m.group(1)
    page_url = f"https://streamtape.com/v/{video_id}"

    session = HttpSession()
    resp = session.get(page_url, headers={"Referer": REFERER})
    if resp.get("status") != 200:
        return None
    html = resp.get("text", "") or ""

    # 2. Evaluate every getElementById('*link').innerHTML = ...; assignment.
    candidates = []
    for inner in _INNER_PAT.finditer(html):
        decoded = _eval_js_string(inner.group(2))
        if decoded and "token=" in decoded:
            candidates.append(decoded)

    if not candidates:
        return None

    # Pick the longest decoded candidate -- the obfuscated full URL is
    # always longer than any partial decoy on the page.
    partial = max(candidates, key=len).strip()

    # 3. Normalise to absolute https URL
    if partial.startswith("//"):
        direct = "https:" + partial
    elif partial.startswith("http"):
        direct = partial
    elif partial.startswith("/"):
        # Path-only result -> bolt onto streamtape.com
        direct = "https://streamtape.com" + partial
    else:
        direct = "https://" + partial.lstrip("/")

    # 4. Force download flag (forces mp4 stream)
    if "dl=1" not in direct:
        direct += ("&" if "?" in direct else "?") + "dl=1"

    # 5. Append Kodi-style headers so the player sends Referer + UA.
    return direct + _build_headers_suffix()
