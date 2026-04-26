"""Persistent channel favourites for Poseidon Guide.

Stored per-profile as ``<addon_profile>/favourites.json``:

    {"ids": ["1234", "5678", ...]}

Keyed by stream_id (string) so it survives credential changes / channel
re-numbering. All API calls swallow IO errors -- favourites are a UX
nice-to-have, never block the guide.
"""
import json
import os
import threading

import xbmcaddon
import xbmcvfs

_ADDON = xbmcaddon.Addon('program.poseidonguide')
_PROFILE = xbmcvfs.translatePath(_ADDON.getAddonInfo('profile'))
_FAV_FILE = os.path.join(_PROFILE, 'favourites.json')

_LOCK = threading.Lock()


def _ensure_dir():
    if not xbmcvfs.exists(_PROFILE):
        xbmcvfs.mkdirs(_PROFILE)


def load():
    """Return the set of stream_ids (strings) currently favourited."""
    try:
        with open(_FAV_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {str(x) for x in data.get('ids', []) if x}
    except Exception:
        return set()


def save(ids):
    """Persist a set/iterable of stream_ids."""
    _ensure_dir()
    try:
        with open(_FAV_FILE, 'w', encoding='utf-8') as f:
            json.dump({'ids': sorted({str(x) for x in ids if x})}, f)
    except Exception:
        pass


def toggle(stream_id):
    """Add or remove ``stream_id``. Returns True if it is now a favourite."""
    sid = str(stream_id)
    with _LOCK:
        ids = load()
        if sid in ids:
            ids.discard(sid)
            added = False
        else:
            ids.add(sid)
            added = True
        save(ids)
    return added


def is_favourite(stream_id):
    return str(stream_id) in load()


def filter_channels(channels):
    """Return only the channels whose stream_id is currently favourited.

    Preserves the original ordering of ``channels`` (favourites picker
    inherits whatever sort the caller already applied -- usually UK first,
    then by channel number).
    """
    ids = load()
    if not ids:
        return []
    return [c for c in channels if str(c.get('stream_id')) in ids]


def count():
    return len(load())
