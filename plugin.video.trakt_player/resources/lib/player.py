# -*- coding: utf-8 -*-
"""Click-and-Play engine. Scrape torrents, filter <=1080p, resolve via Debrid, play instantly."""
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from . import scrapers
from . import debrid

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])

QUALITY_MAP = {'0': '1080p', '1': '720p', '2': '480p'}


def _max_quality():
    return QUALITY_MAP.get(ADDON.getSetting('preferred_quality'), '1080p')


def play(title, year='', imdb_id=''):
    """Click-and-play: scrape -> filter -> debrid resolve -> play. No dialog."""
    services = debrid.get_active_services()
    if not services:
        xbmcgui.Dialog().notification('No Debrid', 'Please configure a Debrid service in Settings', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
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
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    progress.update(50, 'Found %d sources. Resolving via Debrid...' % len(results))

    # Try each result until one resolves
    for i, source in enumerate(results[:10]):
        if progress.iscanceled():
            progress.close()
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            return

        magnet = source.get('magnet', '')
        if not magnet:
            continue

        pct = 50 + int((i / min(len(results), 10)) * 45)
        progress.update(pct, 'Trying [%s] %s (%d seeds)...' % (
            source.get('quality', '?'), source.get('source', '?'), source.get('seeds', 0)))

        url, svc_name = debrid.resolve_magnet(magnet)
        if url:
            progress.close()
            xbmc.log('Playing via %s: %s [%s]' % (svc_name, source.get('title', ''), source.get('quality', '')), xbmc.LOGINFO)
            xbmcgui.Dialog().notification(svc_name, 'Playing %s [%s]' % (title, source.get('quality', '')),
                                          xbmcgui.NOTIFICATION_INFO, 3000)

            li = xbmcgui.ListItem(path=url)
            if '|' in url:
                parts = url.split('|', 1)
                li = xbmcgui.ListItem(path=parts[0])
                li.setProperty('inputstream.adaptive.stream_headers', parts[1])
            xbmcplugin.setResolvedUrl(HANDLE, True, li)
            return

    progress.close()
    xbmcgui.Dialog().notification('Failed', 'Could not resolve any source for %s' % title, xbmcgui.NOTIFICATION_ERROR, 5000)
    xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def play_episode(title, season, episode, imdb_id=''):
    """Click-and-play for TV episodes."""
    search_title = '%s S%sE%s' % (title, str(season).zfill(2), str(episode).zfill(2))
    play(search_title, '', imdb_id)
