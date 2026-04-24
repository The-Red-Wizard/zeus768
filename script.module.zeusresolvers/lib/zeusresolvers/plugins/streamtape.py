# -*- coding: utf-8 -*-
"""Streamtape resolver.

Strategy:
    1. Normalise /e/<id> embed URLs to /v/<id> video pages.
    2. Fetch the page HTML.
    3. Locate the JS line that assigns ``norobotlink`` innerHTML and pull the
       ``token=...`` out of it.
    4. Read the hidden ``<div id="ideoooolink">...</div>`` content for the
       partial path.
    5. Concatenate into a https URL and append ``&token=<token>``.

Reference: public streamtape scrapers in Kodi/ResolveURL ecosystem.
"""
import re

from .._http import HttpSession, host_of

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

_ID_PAT = re.compile(r"streamtape[^/]*/[ev]/([A-Za-z0-9_-]+)", re.I)
# Match both styles: token=XXX  and  ('token','XXX')
_TOKEN_PAT = re.compile(r"token=([A-Za-z0-9_-]+)")
_IDEO_PAT = re.compile(
    r"getElementById\(\s*['\"]ideoooolink['\"]\s*\)\s*\.innerHTML\s*=\s*(.+?);",
    re.S,
)
_INNER_PAT = re.compile(
    r"getElementById\(\s*['\"](?:norobotlink|ideoooolink|robotlink)['\"]\s*\)"
    r"\s*\.innerHTML\s*=\s*(.+?);",
    re.S,
)
_HIDDEN_DIV_PAT = re.compile(
    r"<div[^>]*id\s*=\s*['\"]ideoooolink['\"][^>]*>([^<]+)</div>",
    re.I,
)


def matches(url):
    h = host_of(url)
    if not h:
        return False
    return any(h == d or h.endswith("." + d) for d in HOSTS)


def _extract_partial_link(js_expr):
    """Pull a URL-ish string out of a JS concatenation expression.

    Streamtape commonly encodes the link via ``'https://' + 'streamtape...'``
    or similar string concatenations. We strip quotes and join fragments.
    """
    parts = re.findall(r"'([^']*)'|\"([^\"]*)\"", js_expr)
    joined = "".join(a or b for a, b in parts)
    return joined.strip()


def resolve(url):
    # 1. Normalise embed -> video page
    m = _ID_PAT.search(url)
    if not m:
        return None
    video_id = m.group(1)
    page_url = f"https://streamtape.com/v/{video_id}"

    session = HttpSession()
    resp = session.get(page_url)
    if resp.get("status") != 200:
        return None
    html = resp.get("text", "") or ""

    # 2. Hidden div first (most reliable on current layout)
    partial = ""
    hidden = _HIDDEN_DIV_PAT.search(html)
    if hidden:
        partial = hidden.group(1).strip()
    if not partial:
        ideo = _IDEO_PAT.search(html)
        if ideo:
            partial = _extract_partial_link(ideo.group(1))

    # 3. Token: scan JS blobs for a token= fragment
    token = ""
    for inner in _INNER_PAT.finditer(html):
        tok = _TOKEN_PAT.search(inner.group(1))
        if tok:
            token = tok.group(1)
            break
    if not token:
        # Some variants keep token literal inside ideooo div content
        tok = _TOKEN_PAT.search(partial or "") or _TOKEN_PAT.search(html)
        if tok:
            token = tok.group(1)

    if not partial:
        return None

    # 4. Build final URL
    if partial.startswith("//"):
        direct = "https:" + partial
    elif partial.startswith("http"):
        direct = partial
    else:
        direct = "https://" + partial.lstrip("/")

    if token and "token=" not in direct:
        sep = "&" if "?" in direct else "?"
        direct = f"{direct}{sep}token={token}"

    # Force mp4 content-disposition download for Kodi Player
    if "dl=1" not in direct:
        direct += ("&" if "?" in direct else "?") + "dl=1"

    return direct
