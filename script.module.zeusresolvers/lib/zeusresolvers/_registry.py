# -*- coding: utf-8 -*-
"""Plugin registry + public dispatch functions."""
from ._http import host_of
from .plugins import streamtape as _streamtape
from .plugins import ddownloads as _ddownloads

# Ordered list of (matcher, resolver) pairs.
# matcher(url) -> bool
# resolver(url) -> str | None
_PLUGINS = []


def register(matcher, resolver):
    """Register a custom host plugin at runtime."""
    _PLUGINS.append((matcher, resolver))


# --- Built-ins -------------------------------------------------------------
register(_streamtape.matches, _streamtape.resolve)
register(_ddownloads.matches, _ddownloads.resolve)


def _select(url):
    if not url or not isinstance(url, str):
        return None
    for matcher, resolver in _PLUGINS:
        try:
            if matcher(url):
                return resolver
        except Exception:
            continue
    return None


def can_resolve(url):
    return _select(url) is not None


def resolve(url):
    """Return a direct playable URL or None on failure."""
    plugin = _select(url)
    if plugin is None:
        return None
    try:
        return plugin(url)
    except Exception:
        return None


def supported_hosts():
    """Human-readable list of hoster domains covered by built-ins."""
    return sorted(set(_streamtape.HOSTS + _ddownloads.HOSTS))


__all__ = ["register", "can_resolve", "resolve", "supported_hosts", "host_of"]
