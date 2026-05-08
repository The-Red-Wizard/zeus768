"""
Trakt Player - Quality Badge Cache

Persistent map of imdb_id -> {max_q, ts} populated every time scrapers run.
Consumed by the list renderer to prefix labels with a [4K]/[1080p]/[720p]
badge so the user sees at a glance which titles actually have high-quality
sources available.

- Zero network cost at render time.
- Cache grows as the user plays titles; stale entries (older than 14 days)
  are ignored so refreshes still happen periodically.
- Kept deliberately small (capped at 2000 entries, LRU evicts the rest).
"""
import os
import json
import time

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
CACHE_FILE = os.path.join(PROFILE, 'quality_cache.json')

MAX_ENTRIES = 2000
STALE_SECONDS = 14 * 24 * 60 * 60   # 14 days

QUALITY_RANK = {'2160p': 4, '1080p': 3, '720p': 2, '480p': 1}
LABEL = {'2160p': '[4K]', '1080p': '[1080p]', '720p': '[720p]', '480p': '[SD]'}
COLOUR = {
    '2160p': 'gold',
    '1080p': 'lime',
    '720p':  'cyan',
    '480p':  'grey',
}


def _load():
    try:
        if os.path.isfile(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception as e:
        xbmc.log(f'[TraktPlayer] quality cache load failed: {e}', xbmc.LOGWARNING)
    return {}


def _save(data):
    try:
        os.makedirs(PROFILE, exist_ok=True)
        # LRU trim
        if len(data) > MAX_ENTRIES:
            items = sorted(data.items(), key=lambda kv: kv[1].get('ts', 0),
                           reverse=True)
            data = dict(items[:MAX_ENTRIES])
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'))
    except Exception as e:
        xbmc.log(f'[TraktPlayer] quality cache save failed: {e}', xbmc.LOGWARNING)


def record_results(imdb_id, results):
    """Scan scraper results for the highest quality found, persist it."""
    if not imdb_id or not results:
        return
    best = None
    best_rank = 0
    for r in results:
        q = r.get('quality', '')
        rank = QUALITY_RANK.get(q, 0)
        if rank > best_rank:
            best_rank = rank
            best = q
            if rank == 4:   # 4K already - stop early
                break
    if not best:
        return
    data = _load()
    data[str(imdb_id)] = {'max_q': best, 'ts': int(time.time())}
    _save(data)


def lookup(imdb_id):
    """Return the cached quality label (e.g. '[4K]') or empty string."""
    if not imdb_id:
        return ''
    if not _badges_enabled():
        return ''
    data = _load()
    entry = data.get(str(imdb_id))
    if not entry:
        return ''
    if (time.time() - entry.get('ts', 0)) > STALE_SECONDS:
        return ''
    q = entry.get('max_q', '')
    tag = LABEL.get(q, '')
    col = COLOUR.get(q, 'white')
    return f'[COLOR {col}]{tag}[/COLOR] ' if tag else ''


def _badges_enabled():
    return (ADDON.getSetting('quality_badges') or 'true').lower() != 'false'


def clear():
    try:
        if os.path.isfile(CACHE_FILE):
            os.remove(CACHE_FILE)
        return True
    except Exception:
        return False


def size():
    return len(_load())
