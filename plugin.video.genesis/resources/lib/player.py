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

ADDON = xbmcaddon.Addon()

QUALITY_MAP = {'0': '2160p', '1': '1080p', '2': '720p', '3': '480p'}


def _handle():
    try:
        return int(sys.argv[1])
    except (IndexError, ValueError):
        return -1


def _max_quality():
    return QUALITY_MAP.get(ADDON.getSetting('preferred_quality'), '1080p')


def _set_scrobble_props(media_type, title, imdb_id='', season=0, episode=0, show_title='', tmdb_id=''):
    """Set window properties so the scrobble service knows what's playing."""
    win = xbmcgui.Window(10000)
    win.setProperty('Test1.type', media_type)
    win.setProperty('Test1.title', title)
    win.setProperty('Test1.imdb', imdb_id)
    win.setProperty('Test1.season', str(season))
    win.setProperty('Test1.episode', str(episode))
    win.setProperty('Test1.show_title', show_title)
    win.setProperty('Test1.tmdb_id', str(tmdb_id) if tmdb_id else '')


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

    progress = xbmcgui.DialogProgress()
    progress.create('Test1', 'Searching 10 torrent sites for %s...' % title)

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

    progress = xbmcgui.DialogProgress()
    progress.create('Test1', 'Resolving source via debrid...')

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
        xbmcgui.Dialog().notification('Failed', 'Could not resolve selected source', xbmcgui.NOTIFICATION_ERROR, 5000)
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

    progress = xbmcgui.DialogProgress()
    progress.create('Test1', 'Searching for %s...' % search_title)

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

    progress = xbmcgui.DialogProgress()
    progress.create('Test1', 'Resolving source via debrid...')

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
        xbmcgui.Dialog().notification('Failed', 'Could not resolve any source', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
