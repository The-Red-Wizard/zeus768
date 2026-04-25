# -*- coding: utf-8 -*-
"""Streamtape resolver.

Strategy (matches ResolveURL/Lambda-class scrapers):

    1. Normalise /e/<id> embed URLs to /v/<id> video pages.
    2. Fetch the page HTML.
    3. Locate every ``getElementById('XXXlink').innerHTML = <JS expression>;``
       where XXX ends in ``link`` (robotlink / norobotlink / ideoooolink ...).
    4. Evaluate the JS expression using a tiny string-only evaluator that
       handles literal concat plus common String prototype methods
       (``substring``, ``slice``, ``replace``, ``split().join()``). This is
       the obfuscation Streamtape uses to hide both the token AND the host
       (e.g. ``'streamtape.cddcom'.replace('cdd', '')`` -> ``streamtape.com``).
    5. Pick the longest decoded result that contains ``token=``, build the
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

# A JS string operand:
#   - optional opening '('
#   - quoted string literal
#   - optional closing ')'
#   - any number of  .method(args)  chained on the end
# The method-args group is non-greedy, supports nested quoted strings only.
_OPERAND_PAT = re.compile(
    r"""(?:\(\s*)?                       # optional (
        (['"])([^'"]*)\1                 # quoted literal
        (?:\s*\))?                       # optional )
        ((?:\s*\.\s*[A-Za-z_][\w]*       # method chain: .name(args)
          \s*\(
              (?:[^()'"]|'[^']*'|"[^"]*")*?
          \)
        )*)
    """,
    re.VERBOSE | re.S,
)

# Individual method call inside a chain.
_METHOD_PAT = re.compile(
    r"""\.\s*([A-Za-z_][\w]*)\s*\(
            ((?:[^()'"]|'[^']*'|"[^"]*")*?)
        \)""",
    re.VERBOSE | re.S,
)

# Quoted string literal (used for parsing replace/split args).
_LITERAL_PAT = re.compile(r"""(['"])([^'"]*)\1""", re.S)


def matches(url):
    h = host_of(url)
    if not h:
        return False
    return any(h == d or h.endswith("." + d) for d in HOSTS)


def _str_args(args_src):
    """Return a list of bare string values from quoted method-call args."""
    return [m.group(2) for m in _LITERAL_PAT.finditer(args_src)]


def _int_args(args_src):
    """Return a list of integer arguments from a method-call args string."""
    return [int(x) for x in re.findall(r"-?\d+", args_src)]


def _apply_methods(value, chain_src):
    """Apply a sequence of ``.method(args)`` calls to ``value`` in order.

    Supported (only the ones Streamtape actually uses):
        - substring(a) / substring(a, b)
        - slice(a) / slice(a, b)
        - replace('a', 'b')               -- first occurrence (JS str semantics)
        - split('a').join('b')            -- chained, treated as global replace
        - trim()
    Unknown methods are ignored (best-effort decoder).
    """
    pending_split = None  # remember last split('x') so a chained join consumes it
    for m in _METHOD_PAT.finditer(chain_src):
        name = m.group(1)
        args_src = m.group(2) or ""

        if name == "substring":
            nums = _int_args(args_src)
            if len(nums) >= 2:
                a, b = sorted([max(0, nums[0]), max(0, nums[1])])
                value = value[a:b]
            elif nums:
                value = value[max(0, nums[0]):]
        elif name == "slice":
            nums = _int_args(args_src)
            if len(nums) >= 2:
                value = value[nums[0]:nums[1]]
            elif nums:
                value = value[nums[0]:]
        elif name == "replace":
            strs = _str_args(args_src)
            if len(strs) >= 2:
                value = value.replace(strs[0], strs[1], 1)  # JS replace = first only
            elif len(strs) == 1:
                value = value.replace(strs[0], "", 1)
        elif name == "replaceAll":
            strs = _str_args(args_src)
            if len(strs) >= 2:
                value = value.replace(strs[0], strs[1])
            elif len(strs) == 1:
                value = value.replace(strs[0], "")
        elif name == "split":
            strs = _str_args(args_src)
            pending_split = strs[0] if strs else None
            # value becomes the array conceptually; we only realise it on join().
        elif name == "join":
            strs = _str_args(args_src)
            joiner = strs[0] if strs else ""
            if pending_split is not None:
                # ``s.split(x).join(y)`` is an idiomatic global replace
                value = value.replace(pending_split, joiner)
                pending_split = None
        elif name == "trim":
            value = value.strip()
        # else: silently ignore unrecognised methods
    return value


def _eval_js_string(expr):
    """Concatenate every JS string operand in ``expr`` after applying its
    method chain. Anything that isn't an operand (operators, whitespace,
    comments) is ignored.
    """
    out = []
    for m in _OPERAND_PAT.finditer(expr):
        s = m.group(2)
        chain = m.group(3) or ""
        if chain.strip():
            s = _apply_methods(s, chain)
        out.append(s)
    return "".join(out)


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
