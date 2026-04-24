# -*- coding: utf-8 -*-
"""
Zeus Resolvers - Debrid-free URL resolver for Kodi.

Public API:
    can_resolve(url) -> bool
    resolve(url)     -> str | None
    supported_hosts() -> list[str]

Design goals:
    - Zero third-party runtime deps (stdlib-only).
    - Safe to import from any Kodi addon (no xbmc imports at module level
      so it can also be unit tested on a plain Python interpreter).
    - Pluggable: each supported host lives in ``zeusresolvers.plugins``.
"""
from ._registry import (
    can_resolve,
    resolve,
    supported_hosts,
    register,
)

__version__ = "1.0.0"

__all__ = [
    "can_resolve",
    "resolve",
    "supported_hosts",
    "register",
    "__version__",
]
