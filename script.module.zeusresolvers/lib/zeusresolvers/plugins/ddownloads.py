# -*- coding: utf-8 -*-
"""DDownloads (ddownloads.org / ddownload.com) resolver.

DDownloads uses a two-step XFileSharing-style flow:

    1. GET the file landing page. Parse the hidden ``<form>`` on page for
       op/id/rand/referer/usr_login/method_free/method_premium/down_direct.
    2. POST the same form back to the file URL. The server responds with a
       30x whose ``Location`` header (or an ``<a href=... class="btn-free">``)
       is the direct stream/download link.

The final URL is suffixed with ``|User-Agent=...&Referer=https://ddownload.com/``
so Kodi's player passes the headers the CDN expects.

Only free-download flow is supported -- premium accounts are not required.
"""
import re
import time

from .._http import USER_AGENT, HttpSession, host_of

REFERER = "https://ddownload.com/"

HOSTS = [
    "ddownload.com",
    "ddownloads.org",
    "ddl.to",
]

_ID_PAT = re.compile(r"(?:ddownloads?\.org|ddownload\.com|ddl\.to)/([A-Za-z0-9]+)", re.I)
_FORM_INPUT_PAT = re.compile(
    r"<input[^>]*name\s*=\s*['\"]([^'\"]+)['\"][^>]*value\s*=\s*['\"]([^'\"]*)['\"][^>]*>",
    re.I,
)
_FORM_INPUT_PAT_REV = re.compile(
    r"<input[^>]*value\s*=\s*['\"]([^'\"]*)['\"][^>]*name\s*=\s*['\"]([^'\"]+)['\"][^>]*>",
    re.I,
)
_DIRECT_LINK_PAT = re.compile(
    r'href\s*=\s*["\'](https?://[^"\']+?\.(?:mp4|mkv|avi|mov|m4v|webm)(?:\?[^"\']*)?)["\']',
    re.I,
)
_BTN_FREE_PAT = re.compile(
    r'<a[^>]*class=["\'][^"\']*btn[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
    re.I,
)

# Final URL must look like a real download link, not a landing page.
_FINAL_URL_OK = re.compile(
    r"^https?://[A-Za-z0-9.-]+/[^|]*"
    r"\.(?:mp4|mkv|avi|mov|m4v|webm|ts|flv)(?:\?[^|]*)?$",
    re.I,
)


def _validate(direct):
    if not direct or not isinstance(direct, str):
        return False
    # Strip Kodi pipe-suffix headers before validating.
    base = direct.split("|", 1)[0]
    return bool(_FINAL_URL_OK.match(base))


def matches(url):
    h = host_of(url)
    if not h:
        return False
    return any(h == d or h.endswith("." + d) for d in HOSTS)


def _parse_form_fields(html):
    fields = {}
    for name, value in _FORM_INPUT_PAT.findall(html):
        fields[name] = value
    # Second pass: some inputs have attrs in reverse order
    for value, name in _FORM_INPUT_PAT_REV.findall(html):
        fields.setdefault(name, value)
    return fields


def _with_headers(direct):
    if not direct:
        return None
    if not _validate(direct):
        return None
    if "|" in direct:
        return direct
    return f"{direct}|User-Agent={USER_AGENT}&Referer={REFERER}"


def resolve(url):
    m = _ID_PAT.search(url)
    if not m:
        return None
    file_id = m.group(1)

    # Canonicalise to ddownload.com (current active domain) but keep original
    # as fallback if they diverge in the future.
    page_urls = [url, f"https://ddownload.com/{file_id}", f"https://ddownloads.org/{file_id}"]
    # De-duplicate while preserving order
    seen = set()
    page_urls = [u for u in page_urls if not (u in seen or seen.add(u))]

    session = HttpSession()

    for page_url in page_urls:
        r1 = session.get(page_url, headers={"Referer": REFERER})
        if r1.get("status") != 200 or not r1.get("text"):
            continue
        html = r1["text"]

        # If the page already exposes a direct media link, take it.
        direct = _DIRECT_LINK_PAT.search(html)
        if direct:
            return _with_headers(direct.group(1))

        fields = _parse_form_fields(html)
        if not fields.get("op") and not fields.get("id"):
            continue

        # Ensure sane defaults for XFileSharing free download
        fields.setdefault("id", file_id)
        fields["op"] = "download2"
        fields.setdefault("method_free", "Free Download")
        fields.setdefault("method_premium", "")
        fields.setdefault("down_direct", "1")

        # Honour countdown timer (most free hosts use 5-10s).
        time.sleep(6)

        post_url = page_url
        # First try: do not follow redirects so we can capture the direct Location.
        nr_session = HttpSession(follow_redirects=False)
        # Copy cookies from the landing session into the no-redirect session.
        nr_session.cookies = session.cookies
        r2 = nr_session.post(
            post_url,
            data=fields,
            headers={"Referer": post_url},
            allow_redirect_capture=True,
        )

        loc = r2.get("location")
        if loc and loc.startswith("http"):
            return _with_headers(loc)

        # Fallback: follow-through POST and scrape body for direct link / anchor.
        r3 = session.post(post_url, data=fields, headers={"Referer": post_url})
        body = r3.get("text", "") or ""
        direct = _DIRECT_LINK_PAT.search(body)
        if direct:
            return _with_headers(direct.group(1))
        btn = _BTN_FREE_PAT.search(body)
        if btn and btn.group(1).startswith("http"):
            return _with_headers(btn.group(1))

    return None
