# -*- coding: utf-8 -*-
"""Click-and-Play engine with scrobble context + Up Next support + Pre-cache."""
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from . import scrapers
from . import debrid
from . import precache

ADDON = xbmcaddon.Addon()

# v2.4.4: settings.xml has 4 options (4K/1080p/720p/480p indexed 0..3).
# Previous map only had 3 entries and silently collapsed 4K to 1080p.
QUALITY_MAP = {'0': '2160p', '1': '1080p', '2': '720p', '3': '480p'}
QUALITY_LABEL = {'2160p': '4K', '1080p': '1080p', '720p': '720p', '480p': '480p'}
QUALITY_ORDER = ['2160p', '1080p', '720p', '480p']


def _handle():
    try:
        return int(sys.argv[1])
    except (IndexError, ValueError):
        return -1


def _max_quality():
    return QUALITY_MAP.get(ADDON.getSetting('preferred_quality'), '1080p')


def _auto_play_enabled():
    """'Auto-Play Best Quality' setting. Default TRUE (matches settings.xml)."""
    val = ADDON.getSetting('auto_play')
    # Kodi returns 'true'/'false' strings; empty means unset -> default True.
    if not val:
        return True
    return val.lower() not in ('false', '0', 'no')


def _sort_key_factory(preferred, cached_set):
    """Return a sort key that puts cached+preferred-quality first, then other
    qualities by closeness to the user's preference, then by seed count."""
    pref_idx = QUALITY_ORDER.index(preferred) if preferred in QUALITY_ORDER else 1

    def _key(r):
        is_cached = 0 if r.get('hash', '').lower() in cached_set else 1
        q = r.get('quality', '720p')
        q_idx = QUALITY_ORDER.index(q) if q in QUALITY_ORDER else 9
        # Distance from user preference (preferred = 0; lower qualities grow).
        q_distance = q_idx - pref_idx if q_idx >= pref_idx else 10 - (pref_idx - q_idx)
        return (is_cached, q_distance, -r.get('seeds', 0))
    return _key


def _pick_source(results, cached_set):
    """Show a selectable list of sources. Returns picked source dict, or None."""
    labels = []
    for r in results[:40]:
        is_cached = r.get('hash', '').lower() in cached_set
        tag = '[CACHED] ' if is_cached else ''
        labels.append(
            '{tag}[{q}] {src} - {seeds} seeds - {title}'.format(
                tag=tag,
                q=QUALITY_LABEL.get(r.get('quality', ''), r.get('quality', '?')),
                src=r.get('source', '?'),
                seeds=r.get('seeds', 0),
                title=(r.get('title', '') or '')[:60]
            )
        )
    idx = xbmcgui.Dialog().select('Select Source', labels)
    if idx < 0:
        return None
    return results[idx]


def _set_scrobble_props(media_type, title, imdb_id='', season=0, episode=0, show_title='', tmdb_id=''):
    """Set window properties so the scrobble service knows what's playing."""
    win = xbmcgui.Window(10000)
    win.setProperty('TraktPlayer.type', media_type)
    win.setProperty('TraktPlayer.title', title)
    win.setProperty('TraktPlayer.imdb', imdb_id)
    win.setProperty('TraktPlayer.season', str(season))
    win.setProperty('TraktPlayer.episode', str(episode))
    win.setProperty('TraktPlayer.show_title', show_title)
    win.setProperty('TraktPlayer.tmdb_id', str(tmdb_id) if tmdb_id else '')


def play(title, year='', imdb_id=''):
    """Click-and-play: scrape -> cache check -> debrid resolve -> play. No dialog."""
    services = debrid.get_active_services()
    if not services:
        xbmcgui.Dialog().notification('No Debrid', 'Configure a Debrid service in Settings', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    max_q = _max_quality()
    search_query = '%s %s' % (title, year) if year else title

    progress = xbmcgui.DialogProgress()
    progress.create('Trakt Player', 'Searching torrents for %s...' % title)

    try:
        results = scrapers.search_all(search_query, max_q)
    except Exception as e:
        xbmc.log('Scraper error: %s' % str(e), xbmc.LOGERROR)
        results = []

    if not results:
        progress.close()
        xbmcgui.Dialog().notification('No Sources', 'No torrents found for %s' % title, xbmcgui.NOTIFICATION_WARNING, 4000)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    # Cache check: prioritize cached torrents for instant playback
    progress.update(40, 'Found %d sources. Checking debrid cache...' % len(results))
    hashes = []
    for r in results:
        h = scrapers.extract_hash(r.get('magnet', ''))
        if h:
            hashes.append(h)
            r['hash'] = h
    cached_set = set()
    if hashes:
        try:
            cached_set = debrid.check_cache_all(hashes)
            xbmc.log('Cache check: %d/%d cached' % (len(cached_set), len(hashes)), xbmc.LOGINFO)
        except Exception as e:
            xbmc.log('Cache check failed: %s' % str(e), xbmc.LOGWARNING)

    # Sort with new preference-aware key
    results.sort(key=_sort_key_factory(max_q, cached_set))
    cached_count = sum(1 for r in results if r.get('hash', '').lower() in cached_set)

    # If auto-play is OFF, let user pick a source manually.
    if not _auto_play_enabled():
        progress.close()
        picked = _pick_source(results, cached_set)
        if not picked:
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return
        results = [picked]
        progress = xbmcgui.DialogProgress()
        progress.create('Trakt Player', 'Resolving selected source...')

    progress.update(55, 'Found %d sources (%d cached). Resolving...' % (len(results), cached_count))

    for i, source in enumerate(results[:10]):
        if progress.iscanceled():
            progress.close()
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return

        magnet = source.get('magnet', '')
        if not magnet:
            continue

        pct = 50 + int((i / min(len(results), 10)) * 45)
        is_cached = source.get('hash', '').lower() in cached_set
        cache_tag = '[CACHED] ' if is_cached else ''
        progress.update(pct, 'Trying %s[%s] %s (%d seeds)...' % (
            cache_tag, source.get('quality', '?'), source.get('source', '?'), source.get('seeds', 0)))

        url, svc_name = debrid.resolve_magnet(magnet)
        if url:
            progress.close()
            xbmc.log('Playing via %s: %s [%s]' % (svc_name, source.get('title', ''), source.get('quality', '')), xbmc.LOGINFO)
            xbmcgui.Dialog().notification(svc_name, 'Playing %s [%s]' % (title, source.get('quality', '')),
                                          xbmcgui.NOTIFICATION_INFO, 3000)

            # Set scrobble context
            _set_scrobble_props('movie', title, imdb_id)

            li = xbmcgui.ListItem(path=url)
            if '|' in url:
                parts = url.split('|', 1)
                li = xbmcgui.ListItem(path=parts[0])
                li.setProperty('inputstream.adaptive.stream_headers', parts[1])
            xbmcplugin.setResolvedUrl(_handle(), True, li)
            return

    progress.close()
    xbmcgui.Dialog().notification('Failed', 'Could not resolve any source for %s' % title, xbmcgui.NOTIFICATION_ERROR, 5000)
    xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())


def play_episode(title, season, episode, imdb_id='', tmdb_id=''):
    """Click-and-play for TV episodes with Up Next context."""
    services = debrid.get_active_services()
    if not services:
        xbmcgui.Dialog().notification('No Debrid', 'Configure a Debrid service in Settings', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    max_q = _max_quality()
    search_title = '%s S%sE%s' % (title, str(season).zfill(2), str(episode).zfill(2))

    progress = xbmcgui.DialogProgress()
    progress.create('Trakt Player', 'Searching for %s...' % search_title)

    try:
        results = scrapers.search_all(search_title, max_q)
    except Exception as e:
        xbmc.log('Scraper error: %s' % str(e), xbmc.LOGERROR)
        results = []

    if not results:
        progress.close()
        xbmcgui.Dialog().notification('No Sources', 'No torrents found', xbmcgui.NOTIFICATION_WARNING, 4000)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    # Cache check for episodes
    progress.update(40, 'Found %d sources. Checking cache...' % len(results))
    hashes = []
    for r in results:
        h = scrapers.extract_hash(r.get('magnet', ''))
        if h:
            hashes.append(h)
            r['hash'] = h
    ep_cached_set = set()
    if hashes:
        try:
            ep_cached_set = debrid.check_cache_all(hashes)
        except Exception:
            pass

    results.sort(key=_sort_key_factory(max_q, ep_cached_set))
    ep_cached_count = sum(1 for r in results if r.get('hash', '').lower() in ep_cached_set)

    # If auto-play is OFF, let user pick.
    if not _auto_play_enabled():
        progress.close()
        picked = _pick_source(results, ep_cached_set)
        if not picked:
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return
        results = [picked]
        progress = xbmcgui.DialogProgress()
        progress.create('Trakt Player', 'Resolving selected source...')

    progress.update(55, 'Found %d sources (%d cached). Resolving...' % (len(results), ep_cached_count))

    for i, source in enumerate(results[:10]):
        if progress.iscanceled():
            progress.close()
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return

        magnet = source.get('magnet', '')
        if not magnet:
            continue

        pct = 55 + int((i / min(len(results), 10)) * 40)
        ep_is_cached = source.get('hash', '').lower() in ep_cached_set
        ep_cache_tag = '[CACHED] ' if ep_is_cached else ''
        progress.update(pct, 'Trying %s[%s] %s (%d seeds)...' % (
            ep_cache_tag, source.get('quality', '?'), source.get('source', '?'), source.get('seeds', 0)))

        url, svc_name = debrid.resolve_magnet(magnet)
        if url:
            progress.close()
            xbmc.log('Playing via %s: %s [%s]' % (svc_name, source.get('title', ''), source.get('quality', '')), xbmc.LOGINFO)
            xbmcgui.Dialog().notification(svc_name, 'Playing %s [%s]' % (search_title, source.get('quality', '')),
                                          xbmcgui.NOTIFICATION_INFO, 3000)

            # Set scrobble + Up Next context
            _set_scrobble_props('episode', search_title, imdb_id,
                                int(season), int(episode), title, tmdb_id)

            # Set up pre-cache monitor for next episode
            try:
                monitor = precache.get_monitor()
                monitor.set_episode_info(title, season, episode, tmdb_id)
            except Exception as e:
                xbmc.log(f'Pre-cache setup error: {e}', xbmc.LOGDEBUG)

            li = xbmcgui.ListItem(path=url)
            if '|' in url:
                parts = url.split('|', 1)
                li = xbmcgui.ListItem(path=parts[0])
                li.setProperty('inputstream.adaptive.stream_headers', parts[1])
            xbmcplugin.setResolvedUrl(_handle(), True, li)
            return

    progress.close()
    xbmcgui.Dialog().notification('Failed', 'Could not resolve any source', xbmcgui.NOTIFICATION_ERROR, 5000)
    xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
