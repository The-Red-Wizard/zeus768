# -*- coding: utf-8 -*-
"""Thin wrapper around ``script.module.zeusresolvers``.

This module is kept tiny on purpose: the real logic lives in the
``script.module.zeusresolvers`` Kodi Python module. Each video addon
vendors a copy of this helper so it can call Zeus first and fall back
to ResolveURL cleanly without reimplementing the try/except dance.

Usage:
    from zeus_hook import try_zeus
    stream = try_zeus(url)                    # None if unsupported / failed
    if not stream:
        stream = resolveurl.resolve(url)
"""
try:
    import xbmc  # type: ignore
except Exception:  # pragma: no cover - non-Kodi test imports
    xbmc = None


def _log(msg, level=1):
    if xbmc is None:
        return
    try:
        xbmc.log(f"[zeus_hook] {msg}", level)
    except Exception:
        pass


def try_zeus(url):
    """Attempt resolution via Zeus Resolvers.

    Returns the resolved stream URL on success, ``None`` on any failure
    (module missing, host unsupported, parse error, network error).
    Callers are expected to fall back to ResolveURL / Debrid on ``None``.
    """
    if not url or not isinstance(url, str):
        return None
    try:
        import zeusresolvers  # type: ignore
    except Exception:
        _log("zeusresolvers module not installed")
        return None

    try:
        if not zeusresolvers.can_resolve(url):
            return None
        resolved = zeusresolvers.resolve(url)
        if resolved:
            _log(f"resolved {url[:60]} -> {resolved[:60]}...")
            return resolved
        _log(f"zeus could not resolve {url[:60]}")
    except Exception as e:  # defensive
        _log(f"zeus error: {e}", 2)
    return None


def zeus_supports(url):
    try:
        import zeusresolvers  # type: ignore
        return bool(url) and zeusresolvers.can_resolve(url)
    except Exception:
        return False
