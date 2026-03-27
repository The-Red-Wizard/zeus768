"""
SALTS XBMC Addon - Modernized for Kodi 21+
Copyright (C) 2014 tknorris
Revived and Modernized by zeus768 (2026)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""
import sys
import os
import re
import datetime
import time
import json
import xbmcplugin
import xbmcgui
import xbmc
import xbmcaddon
import xbmcvfs

from urllib.parse import parse_qsl, urlencode, quote_plus

# Add addon lib to path
ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_ICON = os.path.join(ADDON_PATH, 'icon.png')
ADDON_FANART = os.path.join(ADDON_PATH, 'fanart.jpg')
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

sys.path.insert(0, os.path.join(ADDON_PATH, 'salts_lib'))

from salts_lib import log_utils
from salts_lib import utils
from salts_lib.constants import *
from salts_lib import db_utils
from salts_lib import debrid

# Import all scrapers
from scrapers import *

HANDLE = int(sys.argv[1])

def build_url(query):
    return sys.argv[0] + '?' + urlencode(query)

def get_params():
    return dict(parse_qsl(sys.argv[2][1:]))

def main_menu():
    """Main menu of the addon"""
    items = [
        {'title': 'Movies', 'mode': 'movies_menu', 'icon': 'movies.png'},
        {'title': 'TV Shows', 'mode': 'tvshows_menu', 'icon': 'television.png'},
        {'title': 'Search', 'mode': 'search_menu', 'icon': 'search.png'},
        {'title': 'Scrapers', 'mode': 'scrapers_menu', 'icon': 'scraper.png'},
        {'title': 'Debrid Services', 'mode': 'debrid_menu', 'icon': 'debrid.png'},
        {'title': 'Tools', 'mode': 'tools_menu', 'icon': 'settings.png'},
        {'title': 'Settings', 'mode': 'settings', 'icon': 'settings.png'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': item['mode']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def movies_menu():
    """Movies sub-menu"""
    items = [
        {'title': 'Search Movies', 'mode': 'search', 'media_type': 'movie'},
        {'title': 'Popular Movies', 'mode': 'popular', 'media_type': 'movie'},
        {'title': 'Trending Movies', 'mode': 'trending', 'media_type': 'movie'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def tvshows_menu():
    """TV Shows sub-menu"""
    items = [
        {'title': 'Search TV Shows', 'mode': 'search', 'media_type': 'tvshow'},
        {'title': 'Popular TV Shows', 'mode': 'popular', 'media_type': 'tvshow'},
        {'title': 'Trending TV Shows', 'mode': 'trending', 'media_type': 'tvshow'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def search_menu():
    """Search menu"""
    items = [
        {'title': 'Search Movies', 'mode': 'search', 'media_type': 'movie'},
        {'title': 'Search TV Shows', 'mode': 'search', 'media_type': 'tvshow'},
        {'title': 'Search All', 'mode': 'search', 'media_type': 'all'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def search(media_type='all'):
    """Perform search"""
    keyboard = xbmc.Keyboard('', 'Search')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            search_results(query, media_type)

def search_results(query, media_type='all'):
    """Display search results from all scrapers"""
    from scrapers import get_all_scrapers
    
    progress = xbmcgui.DialogProgress()
    progress.create('SALTS', 'Searching sources...')
    
    all_results = []
    scrapers = get_all_scrapers()
    total = len(scrapers)
    
    for i, scraper_cls in enumerate(scrapers):
        if progress.iscanceled():
            break
            
        try:
            scraper = scraper_cls()
            if not scraper.is_enabled():
                continue
                
            progress.update(int((i / total) * 100), f'Searching {scraper.get_name()}...')
            
            results = scraper.search(query, media_type)
            for result in results:
                result['scraper'] = scraper.get_name()
                all_results.append(result)
        except Exception as e:
            log_utils.log(f'Error searching {scraper_cls}: {e}', xbmc.LOGERROR)
    
    progress.close()
    
    if not all_results:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No results found', ADDON_ICON)
        return
    
    # Sort by seeds if available
    all_results.sort(key=lambda x: x.get('seeds', 0), reverse=True)
    
    for result in all_results:
        title = result.get('title', 'Unknown')
        quality = result.get('quality', 'Unknown')
        seeds = result.get('seeds', 0)
        size = result.get('size', 'Unknown')
        scraper_name = result.get('scraper', 'Unknown')
        
        label = f"[{scraper_name}] {title} | {quality} | Seeds: {seeds} | {size}"
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        li.setProperty('IsPlayable', 'true')
        
        # Store result data for playback
        url = build_url({
            'mode': 'play',
            'url': result.get('url', ''),
            'magnet': result.get('magnet', ''),
            'title': title,
            'scraper': scraper_name
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def get_sources(title, year='', season='', episode='', media_type='movie'):
    """Get all available sources for a title"""
    from scrapers import get_all_scrapers
    
    progress = xbmcgui.DialogProgress()
    progress.create('SALTS', 'Gathering sources...')
    
    all_sources = []
    scrapers = get_all_scrapers()
    total = len(scrapers)
    
    for i, scraper_cls in enumerate(scrapers):
        if progress.iscanceled():
            break
            
        try:
            scraper = scraper_cls()
            if not scraper.is_enabled():
                continue
                
            progress.update(int((i / total) * 100), f'Checking {scraper.get_name()}...')
            
            if media_type == 'movie':
                sources = scraper.get_movie_sources(title, year)
            else:
                sources = scraper.get_episode_sources(title, year, season, episode)
                
            for source in sources:
                source['scraper'] = scraper.get_name()
                all_sources.append(source)
        except Exception as e:
            log_utils.log(f'Error getting sources from {scraper_cls}: {e}', xbmc.LOGERROR)
    
    progress.close()
    
    return all_sources

def show_sources(title, year='', season='', episode='', media_type='movie'):
    """Display all sources for selection"""
    sources = get_sources(title, year, season, episode, media_type)
    
    if not sources:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No sources found', ADDON_ICON)
        return
    
    # Sort by quality and seeds
    sources.sort(key=lambda x: (QUALITY_ORDER.get(x.get('quality', 'SD'), 0), x.get('seeds', 0)), reverse=True)
    
    for source in sources:
        scraper_name = source.get('scraper', 'Unknown')
        host = source.get('host', 'Unknown')
        quality = source.get('quality', 'Unknown')
        seeds = source.get('seeds', 0)
        size = source.get('size', 'Unknown')
        
        label = f"[{scraper_name}] [{quality}] {host}"
        if seeds:
            label += f" | Seeds: {seeds}"
        if size:
            label += f" | {size}"
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({
            'mode': 'play',
            'url': source.get('url', ''),
            'magnet': source.get('magnet', ''),
            'title': title,
            'scraper': scraper_name
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def play(url='', magnet='', title='', scraper=''):
    """Play a source"""
    log_utils.log(f'Playing: url={url}, magnet={magnet}, title={title}', xbmc.LOGINFO)
    
    stream_url = None
    
    # Try debrid services first for torrents
    if magnet:
        # Check Real-Debrid
        if ADDON.getSetting('realdebrid_enabled') == 'true':
            rd = debrid.RealDebrid()
            if rd.is_authorized():
                stream_url = rd.resolve_magnet(magnet)
                if stream_url:
                    log_utils.log(f'Resolved via Real-Debrid: {stream_url}', xbmc.LOGINFO)
        
        # Check Premiumize
        if not stream_url and ADDON.getSetting('premiumize_enabled') == 'true':
            pm = debrid.Premiumize()
            if pm.is_authorized():
                stream_url = pm.resolve_magnet(magnet)
                if stream_url:
                    log_utils.log(f'Resolved via Premiumize: {stream_url}', xbmc.LOGINFO)
        
        # Check AllDebrid
        if not stream_url and ADDON.getSetting('alldebrid_enabled') == 'true':
            ad = debrid.AllDebrid()
            if ad.is_authorized():
                stream_url = ad.resolve_magnet(magnet)
                if stream_url:
                    log_utils.log(f'Resolved via AllDebrid: {stream_url}', xbmc.LOGINFO)
    
    # Try URL resolver for direct links
    if not stream_url and url:
        try:
            import resolveurl
            stream_url = resolveurl.resolve(url)
        except Exception as e:
            log_utils.log(f'ResolveURL error: {e}', xbmc.LOGERROR)
            stream_url = url
    
    if not stream_url:
        xbmcgui.Dialog().notification(ADDON_NAME, 'Could not resolve source', ADDON_ICON)
        return
    
    # Play the stream
    li = xbmcgui.ListItem(title, path=stream_url)
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.setResolvedUrl(HANDLE, True, li)

def scrapers_menu():
    """Scrapers management menu"""
    from scrapers import get_all_scrapers
    
    scrapers = get_all_scrapers()
    
    for scraper_cls in scrapers:
        try:
            scraper = scraper_cls()
            name = scraper.get_name()
            enabled = scraper.is_enabled()
            
            status = '[COLOR green]Enabled[/COLOR]' if enabled else '[COLOR red]Disabled[/COLOR]'
            label = f'{name} - {status}'
            
            li = xbmcgui.ListItem(label)
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            
            url = build_url({'mode': 'toggle_scraper', 'scraper': name})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
        except Exception as e:
            log_utils.log(f'Error loading scraper: {e}', xbmc.LOGERROR)
    
    xbmcplugin.endOfDirectory(HANDLE)

def toggle_scraper(scraper_name):
    """Toggle scraper enabled/disabled"""
    setting_id = f'{scraper_name.lower()}_enabled'
    current = ADDON.getSetting(setting_id)
    new_value = 'false' if current == 'true' else 'true'
    ADDON.setSetting(setting_id, new_value)
    
    status = 'enabled' if new_value == 'true' else 'disabled'
    xbmcgui.Dialog().notification(ADDON_NAME, f'{scraper_name} {status}', ADDON_ICON)
    xbmc.executebuiltin('Container.Refresh')

def debrid_menu():
    """Debrid services menu"""
    items = [
        {'title': 'Real-Debrid', 'mode': 'debrid_auth', 'service': 'realdebrid'},
        {'title': 'Premiumize', 'mode': 'debrid_auth', 'service': 'premiumize'},
        {'title': 'AllDebrid', 'mode': 'debrid_auth', 'service': 'alldebrid'},
    ]
    
    for item in items:
        service = item['service']
        enabled = ADDON.getSetting(f'{service}_enabled') == 'true'
        authorized = ADDON.getSetting(f'{service}_token') != ''
        
        status = ''
        if enabled and authorized:
            status = '[COLOR green]Authorized[/COLOR]'
        elif enabled:
            status = '[COLOR yellow]Not Authorized[/COLOR]'
        else:
            status = '[COLOR red]Disabled[/COLOR]'
        
        label = f"{item['title']} - {status}"
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)

def debrid_auth(service):
    """Authorize debrid service"""
    if service == 'realdebrid':
        rd = debrid.RealDebrid()
        rd.authorize()
    elif service == 'premiumize':
        pm = debrid.Premiumize()
        pm.authorize()
    elif service == 'alldebrid':
        ad = debrid.AllDebrid()
        ad.authorize()

def tools_menu():
    """Tools menu"""
    items = [
        {'title': 'Clear Cache', 'mode': 'clear_cache'},
        {'title': 'Test Scrapers', 'mode': 'test_scrapers'},
        {'title': 'View Log', 'mode': 'view_log'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)

def clear_cache():
    """Clear addon cache"""
    db = db_utils.DB_Connection()
    db.flush_cache()
    xbmcgui.Dialog().notification(ADDON_NAME, 'Cache cleared', ADDON_ICON)

def test_scrapers():
    """Test all scrapers"""
    from scrapers import get_all_scrapers
    
    results = []
    scrapers = get_all_scrapers()
    
    progress = xbmcgui.DialogProgress()
    progress.create('SALTS', 'Testing scrapers...')
    
    for i, scraper_cls in enumerate(scrapers):
        if progress.iscanceled():
            break
            
        try:
            scraper = scraper_cls()
            name = scraper.get_name()
            
            progress.update(int((i / len(scrapers)) * 100), f'Testing {name}...')
            
            # Test with a known movie
            test_results = scraper.search('The Matrix', 'movie')
            status = 'OK' if test_results else 'No Results'
            results.append(f'{name}: {status}')
        except Exception as e:
            results.append(f'{scraper_cls}: Error - {e}')
    
    progress.close()
    
    xbmcgui.Dialog().textviewer('Scraper Test Results', '\n'.join(results))

def settings():
    """Open addon settings"""
    ADDON.openSettings()

def router(params):
    """Route to appropriate function based on mode"""
    mode = params.get('mode', '')
    
    if not mode:
        main_menu()
    elif mode == 'movies_menu':
        movies_menu()
    elif mode == 'tvshows_menu':
        tvshows_menu()
    elif mode == 'search_menu':
        search_menu()
    elif mode == 'search':
        search(params.get('media_type', 'all'))
    elif mode == 'search_results':
        search_results(params.get('query', ''), params.get('media_type', 'all'))
    elif mode == 'show_sources':
        show_sources(
            params.get('title', ''),
            params.get('year', ''),
            params.get('season', ''),
            params.get('episode', ''),
            params.get('media_type', 'movie')
        )
    elif mode == 'play':
        play(
            params.get('url', ''),
            params.get('magnet', ''),
            params.get('title', ''),
            params.get('scraper', '')
        )
    elif mode == 'scrapers_menu':
        scrapers_menu()
    elif mode == 'toggle_scraper':
        toggle_scraper(params.get('scraper', ''))
    elif mode == 'debrid_menu':
        debrid_menu()
    elif mode == 'debrid_auth':
        debrid_auth(params.get('service', ''))
    elif mode == 'tools_menu':
        tools_menu()
    elif mode == 'clear_cache':
        clear_cache()
    elif mode == 'test_scrapers':
        test_scrapers()
    elif mode == 'settings':
        settings()
    else:
        log_utils.log(f'Unknown mode: {mode}', xbmc.LOGWARNING)
        main_menu()

if __name__ == '__main__':
    params = get_params()
    log_utils.log(f'SALTS called with params: {params}', xbmc.LOGDEBUG)
    router(params)
