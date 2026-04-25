# -*- coding: utf-8 -*-
"""Streamtape resolver -- conservative, yt-dlp / ResolveURL style.

We deliberately do NOT generally evaluate JS. The Streamtape page is
covered in honeypots: `botlink` and `robotlink` divs and scripts that
intentionally produce *wrong* URLs to defeat naive scrapers (this is the
``get_videod?id=...`` / ``streamtape.cddcom`` pattern observed in user
logs).

The only authoritative source is the ``ideoooolink`` / ``norobotlink``
element. We look for the exact form

    document.getElementById('ideoooolink').innerHTML = "PART1" + ('PART2').substring(N);

and compute ``PART1 + PART2[N:]``. The result is then validated against a
strict pattern -- anything that doesn't match is rejected as garbage and
``None`` is returned, so the calling addon falls through to ResolveURL.
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

# Authoritative elements only. Anything else on the page is a honeypot.
_AUTHORITATIVE_ELEMENTS = ("ideoooolink", "norobotlink")

# Strict canonical pattern (yt-dlp form):
#   getElementById('ideoooolink').innerHTML = "PART1" + ('PART2').substring(N);
# PART1 is the path stub (with token prefix), PART2[N:] is the token suffix.
_INNERHTML_PAT = re.compile(
    r"""getElementById\(\s*['"]({elem})['"]\s*\)\s*\.innerHTML\s*=\s*
        ['"]([^'"]+)['"]                       # PART1
        \s*\+\s*
        \(\s*['"]([^'"]+)['"]\s*\)             # ('PART2')
        \s*\.\s*substring\(\s*(\d+)\s*\)       # .substring(N)
    """.format(elem="|".join(_AUTHORITATIVE_ELEMENTS)),
    re.VERBOSE | re.S,
)

# Final URL must look like a real Streamtape /get_video URL.
_FINAL_URL_OK = re.compile(
    r"^https://[A-Za-z0-9.-]*streamtape\.com/get_video\?"
    r"id=[A-Za-z0-9_-]+&"
    r"expires=\d+&"
    r"ip=[A-Za-z0-9_.\-]+&"
    r"token=[A-Za-z0-9_-]+"
    r"(?:&[A-Za-z0-9_=&-]*)?$",
    re.I,
)


def matches(url):
    h = host_of(url)
    if not h:
        return False
    return any(h == d or h.endswith("." + d) for d in HOSTS)


def _build_headers_suffix():
    return f"|User-Agent={USER_AGENT}&Referer={REFERER}"


def _validate(direct):
    """Return ``True`` iff ``direct`` looks like a legit Streamtape URL.

    Anything failing this check is almost certainly a honeypot / trap and
    should be discarded so the calling addon can fall back to ResolveURL.
    """
    if not direct or not isinstance(direct, str):
        return False
    return bool(_FINAL_URL_OK.match(direct))


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

    # 2. Conservative pattern match on authoritative elements only.
    #    Pick the FIRST match -- the page may also contain honeypot variants
    #    inside ``botlink`` / ``robotlink`` which we deliberately ignore.
    match = _INNERHTML_PAT.search(html)
    if not match:
        return None

    part1, part2, idx_str = match.group(2), match.group(3), match.group(4)
    try:
        idx = int(idx_str)
    except ValueError:
        return None
    suffix = part2[idx:] if 0 <= idx <= len(part2) else ""
    partial = (part1 + suffix).strip()

    # 3. Normalise to absolute https URL
    if partial.startswith("//"):
        direct = "https:" + partial
    elif partial.startswith("http"):
        direct = partial
    elif partial.startswith("/"):
        direct = "https://streamtape.com" + partial
    else:
        direct = "https://streamtape.com/" + partial.lstrip("/")

    # 4. Validate before returning -- garbage gets rejected so the caller
    #    can fall through to ResolveURL.
    if not _validate(direct):
        return None

    # 5. Force download flag + Kodi-style headers
    if "dl=1" not in direct:
        direct += ("&" if "?" in direct else "?") + "dl=1"
    return direct + _build_headers_suffix()
