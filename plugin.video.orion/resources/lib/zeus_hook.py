# -*- coding: utf-8 -*-
"""Thin wrapper around ``script.module.zeusresolvers``. Vendored per-addon."""
try:
    import xbmc  # type: ignore
except Exception:
    xbmc = None


def _log(msg, level=1):
    if xbmc is None:
        return
    try:
        xbmc.log(f"[zeus_hook] {msg}", level)
    except Exception:
        pass


def try_zeus(url):
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
    except Exception as e:
        _log(f"zeus error: {e}", 2)
    return None


def zeus_supports(url):
    try:
        import zeusresolvers  # type: ignore
        return bool(url) and zeusresolvers.can_resolve(url)
    except Exception:
        return False
