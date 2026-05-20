# -*- coding: utf-8 -*-
"""
Enhanced Click-and-Play engine for Genesis
Features:
- Manual source selection via enhanced source picker
- Free links integration via ResolveURL
- No auto-play (user chooses source)
- Full quality/codec/HDR information display
"""
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from . import scrapers
from . import debrid
from . import source_picker
from . import free_links_scraper
from . import torbox_advanced
from . import bento_search

ADDON = xbmcaddon.Addon()

QUALITY_MAP = {'0': '2160p', '1': '1080p', '2': '720p', '3': '480p'}


def _handle():
    try:
        return int(sys.argv[1])
    except (IndexError, ValueError):
        return -1


def _max_quality():
    return QUALITY_MAP.get(ADDON.getSetting('preferred_quality'), '1080p')


def _confirm_uncached(selected):
    """Show the "not cached" confirmation dialog before consuming the source.

    Returns one of: 'play', 'queue_tb', 'cancel'.
    """
    # Allow users to disable via settings
    try:
        if ADDON.getSetting('confirm_uncached') == 'false':
            return 'play'
    except Exception:
        pass

    tb = torbox_advanced.TorboxAdvanced()
    has_tb = tb.is_authorized()

    title = selected.get('title', '')[:80]
    seeds = selected.get('seeds', 0)
    seed_color = 'lime' if seeds > 50 else ('yellow' if seeds > 10 else 'red')
    body = (
        f"[B]This source is NOT cached on any debrid service.[/B]\n\n"
        f"[COLOR yellow]{title}[/COLOR]\n"
        f"Seeders: [COLOR {seed_color}]{seeds}[/COLOR]\n\n"
        f"Streaming may fail or take a long time.\n"
        f"What would you like to do?"
    )

    dialog = xbmcgui.Dialog()
    if has_tb:
        choice = dialog.select(
            'Source Not Cached',
            [
                '[COLOR yellow]Try to stream now[/COLOR]  (may fail if download is slow)',
                '[COLOR lime]Queue to TorBox Cloud[/COLOR]  (download in background)',
                '[COLOR red]Cancel[/COLOR]',
            ],
        )
        if choice == 0:
            return 'play'
        if choice == 1:
            return 'queue_tb'
        return 'cancel'

    # No TorBox - just yes/no warning
    ok = dialog.yesno(
        'Source Not Cached',
        body,
        nolabel='Cancel',
        yeslabel='Try anyway',
    )
    return 'play' if ok else 'cancel'


def _queue_to_torbox(magnet, title):
    """Submit the magnet to TorBox cloud and tell the user where to look."""
    tb = torbox_advanced.TorboxAdvanced()
    if not tb.is_authorized():
        xbmcgui.Dialog().notification(
            'TorBox', 'Link your TorBox account first',
            xbmcgui.NOTIFICATION_ERROR, 4000,
        )
        return False
    res = tb.queue_torrent(magnet, as_queued=True)
    if not res or not res.get('success'):
        err = (res or {}).get('detail') or (res or {}).get('error') or 'Unknown error'
        xbmcgui.Dialog().notification(
            'TorBox', f'Queue failed: {err}',
            xbmcgui.NOTIFICATION_ERROR, 5000,
        )
        return False
    xbmcgui.Dialog().notification(
        'TorBox Cloud',
        f'Queued "{title[:40]}". Check Cloud > TorBox later.',
        xbmcgui.NOTIFICATION_INFO, 5000,
    )
    return True


def _set_scrobble_props(media_type, title, imdb_id='', season=0, episode=0, show_title='', tmdb_id=''):
    """Set window properties so the scrobble service knows what's playing."""
    win = xbmcgui.Window(10000)
    win.setProperty('Genesis.type', media_type)
    win.setProperty('Genesis.title', title)
    win.setProperty('Genesis.imdb', imdb_id)
    win.setProperty('Genesis.season', str(season))
    win.setProperty('Genesis.episode', str(episode))
    win.setProperty('Genesis.show_title', show_title)
    win.setProperty('Genesis.tmdb_id', str(tmdb_id) if tmdb_id else '')


def play(title, year='', imdb_id='', tmdb_id=''):
    """
    Enhanced play function with manual source selection.
    No auto-play - user selects from source picker dialog.
    """
    services = debrid.get_active_services()
    if not services:
        xbmcgui.Dialog().notification('No Debrid', 'Configure a Debrid service in Settings', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    max_q = _max_quality()
    search_query = '%s %s' % (title, year) if year else title

    use_bento = bento_search.is_enabled()
    bento = None
    if use_bento:
        try:
            bento = bento_search.BentoSearchDialog(query=search_query, subtitle='Movie')
            bento.show()
        except Exception as e:
            xbmc.log('Bento dialog failed to open: %s' % e, xbmc.LOGWARNING)
            bento = None

    progress = None
    if bento is None:
        progress = xbmcgui.DialogProgress()
        progress.create('Genesis', 'Searching torrent sites for %s...' % title)

    try:
        results = scrapers.search_all(
            search_query, max_q,
            imdb_id=imdb_id, media_type='movie',
            progress_cb=(bento.on_progress if bento else None),
        )
    except Exception as e:
        xbmc.log('Scraper error: %s' % str(e), xbmc.LOGERROR)
        results = []

    if bento is not None:
        bento.finish(len(results))
        # If user cancelled mid-search, abort
        if bento.cancelled:
            bento.close()
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return
        # Wait for user to click Continue (or auto-close in 4s if results found)
        cont = bento.wait_for_user(auto_close_seconds=4 if results else 0)
        bento.close()
        if not cont:
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return

    if not results:
        if progress:
            progress.close()
        xbmcgui.Dialog().notification('No Sources', 'No torrents found for %s' % title, xbmcgui.NOTIFICATION_WARNING, 4000)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    if progress:
        progress.update(40, 'Found %d sources. Checking debrid cache...' % len(results))
    
    # Extract hashes for cache check
    hashes = []
    for r in results:
        h = scrapers.extract_hash(r.get('magnet', ''))
        if h:
            hashes.append(h)
            r['hash'] = h
    
    # Check cache across all debrid services
    cached_set = set()
    if hashes:
        try:
            cached_set = debrid.check_cache_all(hashes)
            xbmc.log('Cache check: %d/%d cached' % (len(cached_set), len(hashes)), xbmc.LOGINFO)
        except Exception as e:
            xbmc.log('Cache check failed: %s' % str(e), xbmc.LOGWARNING)

    if progress:
        progress.close()

    # Show enhanced source picker dialog (includes free links)
    selected = source_picker.show_source_picker(results, cached_set, title, include_free_links=True)
    
    if not selected:
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    # Check if this is a free link
    if selected.get('is_free_link'):
        progress = xbmcgui.DialogProgress()
        progress.create('Genesis', 'Resolving free link...')
        
        url = free_links_scraper.resolve_free_link(selected.get('url', ''))
        progress.close()
        
        if url:
            quality_str = selected.get('quality', '')
            xbmcgui.Dialog().notification(
                'Free Link', 
                f'Playing {title} [{quality_str}]',
                xbmcgui.NOTIFICATION_INFO, 3000
            )
            _set_scrobble_props('movie', title, imdb_id, tmdb_id=tmdb_id)
            li = xbmcgui.ListItem(path=url)
            xbmcplugin.setResolvedUrl(_handle(), True, li)
        else:
            xbmcgui.Dialog().notification('Failed', 'Could not resolve free link', xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    # Resolve selected source (torrent/debrid)
    magnet = selected.get('magnet', '')
    if not magnet:
        xbmcgui.Dialog().notification('Error', 'No magnet link for selected source', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    # Uncached confirmation -> prompt user
    if not selected.get('is_cached'):
        choice = _confirm_uncached(selected)
        if choice == 'cancel':
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return
        if choice == 'queue_tb':
            _queue_to_torbox(magnet, selected.get('title', title))
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return

    progress = xbmcgui.DialogProgress()
    progress.create('Genesis', 'Resolving source via debrid...')

    url, svc_name = debrid.resolve_magnet(magnet)
    
    progress.close()

    if url:
        xbmc.log('Playing via %s: %s [%s]' % (svc_name, selected.get('title', ''), selected.get('quality', '')), xbmc.LOGINFO)
        
        # Build quality info for notification
        quality_info = []
        if selected.get('resolution'):
            quality_info.append(selected['resolution'])
        if selected.get('quality_type') and selected['quality_type'] != 'Unknown':
            quality_info.append(selected['quality_type'])
        if selected.get('hdr'):
            quality_info.append(selected['hdr'])
        
        quality_str = ' | '.join(quality_info) if quality_info else selected.get('quality', '')
        
        xbmcgui.Dialog().notification(
            svc_name, 
            f'Playing {title} [{quality_str}]',
            xbmcgui.NOTIFICATION_INFO, 3000
        )

        _set_scrobble_props('movie', title, imdb_id, tmdb_id=tmdb_id)

        li = xbmcgui.ListItem(path=url)
        if '|' in url:
            parts = url.split('|', 1)
            li = xbmcgui.ListItem(path=parts[0])
            li.setProperty('inputstream.adaptive.stream_headers', parts[1])
        xbmcplugin.setResolvedUrl(_handle(), True, li)
    else:
        # Friendlier failure message that hints at the likely reason
        cached_hint = '' if selected.get('is_cached') else \
            '\nThis source was not cached - it may need time to download.'
        xbmcgui.Dialog().ok(
            'Source Failed',
            f'Could not resolve "{selected.get("title", "")[:80]}".' + cached_hint,
        )
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())


def play_episode(title, season, episode, imdb_id='', tmdb_id=''):
    """
    Enhanced play function for TV episodes with manual source selection.
    """
    services = debrid.get_active_services()
    if not services:
        xbmcgui.Dialog().notification('No Debrid', 'Configure a Debrid service in Settings', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    max_q = _max_quality()
    search_title = '%s S%sE%s' % (title, str(season).zfill(2), str(episode).zfill(2))

    use_bento = bento_search.is_enabled()
    bento = None
    if use_bento:
        try:
            bento = bento_search.BentoSearchDialog(query=search_title, subtitle='Episode')
            bento.show()
        except Exception as e:
            xbmc.log('Bento dialog failed to open: %s' % e, xbmc.LOGWARNING)
            bento = None

    progress = None
    if bento is None:
        progress = xbmcgui.DialogProgress()
        progress.create('Genesis', 'Searching for %s...' % search_title)

    try:
        results = scrapers.search_all(
            search_title, max_q,
            imdb_id=imdb_id, media_type='series',
            season=int(season), episode=int(episode),
            progress_cb=(bento.on_progress if bento else None),
        )
    except Exception as e:
        xbmc.log('Scraper error: %s' % str(e), xbmc.LOGERROR)
        results = []

    # If no results with S01E01 format, try with season pack (free-text only, no Stremio repeat)
    if not results:
        try:
            season_query = '%s Season %s' % (title, str(season))
            if progress:
                progress.update(50, 'No episode results. Trying season pack...')
            results = scrapers.search_all(
                season_query, max_q,
                imdb_id='', media_type='movie',
                progress_cb=(bento.on_progress if bento else None),
            )
        except Exception as e:
            xbmc.log('Season pack search error: %s' % str(e), xbmc.LOGERROR)
            results = []

    if bento is not None:
        bento.finish(len(results))
        if bento.cancelled:
            bento.close()
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return
        cont = bento.wait_for_user(auto_close_seconds=4 if results else 0)
        bento.close()
        if not cont:
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return

    if not results:
        if progress:
            progress.close()
        xbmcgui.Dialog().notification('No Sources', 'No torrents found', xbmcgui.NOTIFICATION_WARNING, 4000)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    if progress:
        progress.update(40, 'Found %d sources. Checking cache...' % len(results))
    
    # Extract hashes
    hashes = []
    for r in results:
        h = scrapers.extract_hash(r.get('magnet', ''))
        if h:
            hashes.append(h)
            r['hash'] = h
    
    # Check cache
    ep_cached_set = set()
    if hashes:
        try:
            ep_cached_set = debrid.check_cache_all(hashes)
        except Exception:
            pass

    if progress:
        progress.close()

    # Show enhanced source picker
    selected = source_picker.show_source_picker(results, ep_cached_set, search_title)
    
    if not selected:
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    magnet = selected.get('magnet', '')
    if not magnet:
        xbmcgui.Dialog().notification('Error', 'No magnet link', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
        return

    # Uncached confirmation -> prompt user
    if not selected.get('is_cached'):
        choice = _confirm_uncached(selected)
        if choice == 'cancel':
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return
        if choice == 'queue_tb':
            _queue_to_torbox(magnet, selected.get('title', search_title))
            xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
            return

    progress = xbmcgui.DialogProgress()
    progress.create('Genesis', 'Resolving source via debrid...')

    url, svc_name = debrid.resolve_magnet(magnet)
    
    progress.close()

    if url:
        xbmc.log('Playing via %s: %s [%s]' % (svc_name, selected.get('title', ''), selected.get('quality', '')), xbmc.LOGINFO)
        
        quality_info = []
        if selected.get('resolution'):
            quality_info.append(selected['resolution'])
        if selected.get('quality_type') and selected['quality_type'] != 'Unknown':
            quality_info.append(selected['quality_type'])
        if selected.get('hdr'):
            quality_info.append(selected['hdr'])
        
        quality_str = ' | '.join(quality_info) if quality_info else selected.get('quality', '')
        
        xbmcgui.Dialog().notification(
            svc_name, 
            f'Playing {search_title} [{quality_str}]',
            xbmcgui.NOTIFICATION_INFO, 3000
        )

        _set_scrobble_props('episode', search_title, imdb_id,
                            int(season), int(episode), title, tmdb_id)

        li = xbmcgui.ListItem(path=url)
        if '|' in url:
            parts = url.split('|', 1)
            li = xbmcgui.ListItem(path=parts[0])
            li.setProperty('inputstream.adaptive.stream_headers', parts[1])
        xbmcplugin.setResolvedUrl(_handle(), True, li)
    else:
        cached_hint = '' if selected.get('is_cached') else \
            '\nThis source was not cached - it may need time to download.'
        xbmcgui.Dialog().ok(
            'Source Failed',
            f'Could not resolve "{selected.get("title", "")[:80]}".' + cached_hint,
        )
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
