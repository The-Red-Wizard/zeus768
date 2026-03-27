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
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
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

HANDLE = int(sys.argv[1])

def build_url(query):
    return sys.argv[0] + '?' + urlencode(query)

def get_params():
    return dict(parse_qsl(sys.argv[2][1:]))

def main_menu():
    """Main menu of the addon"""
    items = [
        {'title': '[B]Movies[/B]', 'mode': 'movies_menu'},
        {'title': '[B]TV Shows[/B]', 'mode': 'tvshows_menu'},
        {'title': '[B]Search[/B]', 'mode': 'search_menu'},
        {'title': '[B]Trakt[/B]', 'mode': 'trakt_menu'},
        {'title': 'Scrapers', 'mode': 'scrapers_menu'},
        {'title': 'Debrid Services', 'mode': 'debrid_menu'},
        {'title': 'Tools', 'mode': 'tools_menu'},
        {'title': 'Settings', 'mode': 'addon_settings'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART, 'thumb': ADDON_ICON})
        url = build_url({'mode': item['mode']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def movies_menu():
    """Movies sub-menu"""
    items = [
        {'title': '[B]Search Movies[/B]', 'mode': 'search', 'media_type': 'movie'},
        {'title': 'Popular Movies', 'mode': 'tmdb_list', 'list_type': 'popular', 'media_type': 'movie'},
        {'title': 'Trending Movies', 'mode': 'tmdb_list', 'list_type': 'trending', 'media_type': 'movie'},
        {'title': 'Top Rated Movies', 'mode': 'tmdb_list', 'list_type': 'top_rated', 'media_type': 'movie'},
        {'title': 'Now Playing', 'mode': 'tmdb_list', 'list_type': 'now_playing', 'media_type': 'movie'},
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
        {'title': '[B]Search TV Shows[/B]', 'mode': 'search', 'media_type': 'tvshow'},
        {'title': 'Popular TV Shows', 'mode': 'tmdb_list', 'list_type': 'popular', 'media_type': 'tvshow'},
        {'title': 'Trending TV Shows', 'mode': 'tmdb_list', 'list_type': 'trending', 'media_type': 'tvshow'},
        {'title': 'Top Rated TV Shows', 'mode': 'tmdb_list', 'list_type': 'top_rated', 'media_type': 'tvshow'},
        {'title': 'Airing Today', 'mode': 'tmdb_list', 'list_type': 'airing_today', 'media_type': 'tvshow'},
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
        {'title': '[B]Search Movies[/B]', 'mode': 'search', 'media_type': 'movie'},
        {'title': '[B]Search TV Shows[/B]', 'mode': 'search', 'media_type': 'tvshow'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def tmdb_list(list_type, media_type='movie', page=1):
    """Get list from TMDB API (free, no key needed for basic lists)"""
    import requests
    
    # TMDB API (v3) - using discover endpoint which works without auth for basic queries
    base_url = 'https://api.themoviedb.org/3'
    
    # Free API key for demo purposes (limited, users should get their own)
    api_key = '8265bd1679663a7ea12ac168da84d2e8'
    
    try:
        if media_type == 'movie':
            if list_type == 'popular':
                url = f'{base_url}/movie/popular?api_key={api_key}&page={page}'
            elif list_type == 'trending':
                url = f'{base_url}/trending/movie/week?api_key={api_key}&page={page}'
            elif list_type == 'top_rated':
                url = f'{base_url}/movie/top_rated?api_key={api_key}&page={page}'
            elif list_type == 'now_playing':
                url = f'{base_url}/movie/now_playing?api_key={api_key}&page={page}'
            else:
                url = f'{base_url}/movie/popular?api_key={api_key}&page={page}'
        else:  # tvshow
            if list_type == 'popular':
                url = f'{base_url}/tv/popular?api_key={api_key}&page={page}'
            elif list_type == 'trending':
                url = f'{base_url}/trending/tv/week?api_key={api_key}&page={page}'
            elif list_type == 'top_rated':
                url = f'{base_url}/tv/top_rated?api_key={api_key}&page={page}'
            elif list_type == 'airing_today':
                url = f'{base_url}/tv/airing_today?api_key={api_key}&page={page}'
            else:
                url = f'{base_url}/tv/popular?api_key={api_key}&page={page}'
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        results = data.get('results', [])
        
        if not results:
            xbmcgui.Dialog().notification(ADDON_NAME, 'No results found', ADDON_ICON)
            return
        
        for item in results:
            if media_type == 'movie':
                title = item.get('title', 'Unknown')
                year = item.get('release_date', '')[:4]
            else:
                title = item.get('name', item.get('original_name', 'Unknown'))
                year = item.get('first_air_date', '')[:4]
            
            poster = item.get('poster_path', '')
            backdrop = item.get('backdrop_path', '')
            overview = item.get('overview', '')
            rating = item.get('vote_average', 0)
            
            poster_url = f'https://image.tmdb.org/t/p/w500{poster}' if poster else ADDON_ICON
            backdrop_url = f'https://image.tmdb.org/t/p/original{backdrop}' if backdrop else ADDON_FANART
            
            label = f'{title} ({year})' if year else title
            
            li = xbmcgui.ListItem(label)
            li.setArt({
                'icon': poster_url,
                'thumb': poster_url,
                'poster': poster_url,
                'fanart': backdrop_url
            })
            
            # Set video info
            info_tag = li.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setYear(int(year) if year else 0)
            info_tag.setPlot(overview)
            info_tag.setRating(rating)
            info_tag.setMediaType('movie' if media_type == 'movie' else 'tvshow')
            
            if media_type == 'movie':
                url = build_url({
                    'mode': 'get_sources',
                    'title': title,
                    'year': year,
                    'media_type': 'movie'
                })
            else:
                url = build_url({
                    'mode': 'tv_seasons',
                    'title': title,
                    'year': year,
                    'tmdb_id': item.get('id', '')
                })
            
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        
        # Add next page
        if data.get('page', 1) < data.get('total_pages', 1):
            li = xbmcgui.ListItem('[B]>> Next Page[/B]')
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            url = build_url({
                'mode': 'tmdb_list',
                'list_type': list_type,
                'media_type': media_type,
                'page': page + 1
            })
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        
        xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movie' else 'tvshows')
        xbmcplugin.endOfDirectory(HANDLE)
        
    except Exception as e:
        log_utils.log(f'TMDB list error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, f'Error: {e}', ADDON_ICON)

def search(media_type='movie'):
    """Perform search - show results as movies/shows first"""
    keyboard = xbmc.Keyboard('', f'Search {"Movies" if media_type == "movie" else "TV Shows"}')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            search_tmdb(query, media_type)

def search_tmdb(query, media_type='movie'):
    """Search TMDB and show results"""
    import requests
    
    base_url = 'https://api.themoviedb.org/3'
    api_key = '8265bd1679663a7ea12ac168da84d2e8'
    
    try:
        if media_type == 'movie':
            url = f'{base_url}/search/movie?api_key={api_key}&query={quote_plus(query)}'
        else:
            url = f'{base_url}/search/tv?api_key={api_key}&query={quote_plus(query)}'
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        results = data.get('results', [])
        
        if not results:
            xbmcgui.Dialog().notification(ADDON_NAME, 'No results found', ADDON_ICON)
            return
        
        for item in results:
            if media_type == 'movie':
                title = item.get('title', 'Unknown')
                year = item.get('release_date', '')[:4]
            else:
                title = item.get('name', item.get('original_name', 'Unknown'))
                year = item.get('first_air_date', '')[:4]
            
            poster = item.get('poster_path', '')
            backdrop = item.get('backdrop_path', '')
            overview = item.get('overview', '')
            rating = item.get('vote_average', 0)
            
            poster_url = f'https://image.tmdb.org/t/p/w500{poster}' if poster else ADDON_ICON
            backdrop_url = f'https://image.tmdb.org/t/p/original{backdrop}' if backdrop else ADDON_FANART
            
            label = f'{title} ({year})' if year else title
            
            li = xbmcgui.ListItem(label)
            li.setArt({
                'icon': poster_url,
                'thumb': poster_url,
                'poster': poster_url,
                'fanart': backdrop_url
            })
            
            # Set video info
            info_tag = li.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setYear(int(year) if year else 0)
            info_tag.setPlot(overview)
            info_tag.setRating(rating)
            info_tag.setMediaType('movie' if media_type == 'movie' else 'tvshow')
            
            if media_type == 'movie':
                url = build_url({
                    'mode': 'get_sources',
                    'title': title,
                    'year': year,
                    'media_type': 'movie'
                })
            else:
                url = build_url({
                    'mode': 'tv_seasons',
                    'title': title,
                    'year': year,
                    'tmdb_id': item.get('id', '')
                })
            
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        
        xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movie' else 'tvshows')
        xbmcplugin.endOfDirectory(HANDLE)
        
    except Exception as e:
        log_utils.log(f'Search error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, f'Error: {e}', ADDON_ICON)

def tv_seasons(title, year='', tmdb_id=''):
    """Show seasons for a TV show"""
    import requests
    
    base_url = 'https://api.themoviedb.org/3'
    api_key = '8265bd1679663a7ea12ac168da84d2e8'
    
    try:
        if tmdb_id:
            url = f'{base_url}/tv/{tmdb_id}?api_key={api_key}'
            response = requests.get(url, timeout=10)
            data = response.json()
            
            seasons = data.get('seasons', [])
            backdrop = data.get('backdrop_path', '')
            backdrop_url = f'https://image.tmdb.org/t/p/original{backdrop}' if backdrop else ADDON_FANART
            
            for season in seasons:
                season_num = season.get('season_number', 0)
                if season_num == 0:  # Skip specials
                    continue
                    
                name = season.get('name', f'Season {season_num}')
                poster = season.get('poster_path', '')
                poster_url = f'https://image.tmdb.org/t/p/w500{poster}' if poster else ADDON_ICON
                episode_count = season.get('episode_count', 0)
                
                label = f'{name} ({episode_count} episodes)'
                
                li = xbmcgui.ListItem(label)
                li.setArt({
                    'icon': poster_url,
                    'thumb': poster_url,
                    'poster': poster_url,
                    'fanart': backdrop_url
                })
                
                url = build_url({
                    'mode': 'tv_episodes',
                    'title': title,
                    'year': year,
                    'tmdb_id': tmdb_id,
                    'season': season_num
                })
                
                xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
            
            xbmcplugin.setContent(HANDLE, 'seasons')
            xbmcplugin.endOfDirectory(HANDLE)
        else:
            # No TMDB ID, show generic seasons 1-10
            for i in range(1, 11):
                li = xbmcgui.ListItem(f'Season {i}')
                li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
                url = build_url({
                    'mode': 'tv_episodes',
                    'title': title,
                    'year': year,
                    'season': i
                })
                xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
            
            xbmcplugin.setContent(HANDLE, 'seasons')
            xbmcplugin.endOfDirectory(HANDLE)
            
    except Exception as e:
        log_utils.log(f'TV seasons error: {e}', xbmc.LOGERROR)
        # Fallback to generic seasons
        for i in range(1, 11):
            li = xbmcgui.ListItem(f'Season {i}')
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            url = build_url({
                'mode': 'tv_episodes',
                'title': title,
                'year': year,
                'season': i
            })
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        
        xbmcplugin.setContent(HANDLE, 'seasons')
        xbmcplugin.endOfDirectory(HANDLE)

def tv_episodes(title, year='', tmdb_id='', season=1):
    """Show episodes for a season"""
    import requests
    
    base_url = 'https://api.themoviedb.org/3'
    api_key = '8265bd1679663a7ea12ac168da84d2e8'
    
    try:
        if tmdb_id:
            url = f'{base_url}/tv/{tmdb_id}/season/{season}?api_key={api_key}'
            response = requests.get(url, timeout=10)
            data = response.json()
            
            episodes = data.get('episodes', [])
            
            for ep in episodes:
                ep_num = ep.get('episode_number', 0)
                ep_name = ep.get('name', f'Episode {ep_num}')
                overview = ep.get('overview', '')
                still = ep.get('still_path', '')
                still_url = f'https://image.tmdb.org/t/p/w500{still}' if still else ADDON_FANART
                rating = ep.get('vote_average', 0)
                
                label = f'{ep_num}. {ep_name}'
                
                li = xbmcgui.ListItem(label)
                li.setArt({
                    'icon': still_url,
                    'thumb': still_url,
                    'fanart': still_url
                })
                
                info_tag = li.getVideoInfoTag()
                info_tag.setTitle(ep_name)
                info_tag.setPlot(overview)
                info_tag.setRating(rating)
                info_tag.setSeason(int(season))
                info_tag.setEpisode(ep_num)
                info_tag.setMediaType('episode')
                
                url = build_url({
                    'mode': 'get_sources',
                    'title': title,
                    'year': year,
                    'season': season,
                    'episode': ep_num,
                    'media_type': 'tvshow'
                })
                
                xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
            
            xbmcplugin.setContent(HANDLE, 'episodes')
            xbmcplugin.endOfDirectory(HANDLE)
        else:
            # No TMDB ID, show generic episodes 1-20
            for i in range(1, 21):
                li = xbmcgui.ListItem(f'Episode {i}')
                li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
                url = build_url({
                    'mode': 'get_sources',
                    'title': title,
                    'year': year,
                    'season': season,
                    'episode': i,
                    'media_type': 'tvshow'
                })
                xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
            
            xbmcplugin.setContent(HANDLE, 'episodes')
            xbmcplugin.endOfDirectory(HANDLE)
            
    except Exception as e:
        log_utils.log(f'TV episodes error: {e}', xbmc.LOGERROR)
        # Fallback to generic episodes
        for i in range(1, 21):
            li = xbmcgui.ListItem(f'Episode {i}')
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            url = build_url({
                'mode': 'get_sources',
                'title': title,
                'year': year,
                'season': season,
                'episode': i,
                'media_type': 'tvshow'
            })
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        
        xbmcplugin.setContent(HANDLE, 'episodes')
        xbmcplugin.endOfDirectory(HANDLE)

def get_sources(title, year='', season='', episode='', media_type='movie'):
    """Get all available sources for a title with progress dialog"""
    from scrapers import get_all_scrapers
    
    # Build search query
    if media_type == 'movie':
        query = f'{title} {year}' if year else title
        search_title = f'{title} ({year})' if year else title
    else:
        query = f'{title} S{int(season):02d}E{int(episode):02d}'
        search_title = f'{title} S{int(season):02d}E{int(episode):02d}'
    
    progress = xbmcgui.DialogProgress()
    progress.create('SALTS', f'Searching for: {search_title}')
    
    all_sources = []
    scrapers = get_all_scrapers()
    total = len(scrapers)
    sources_found = 0
    
    for i, scraper_cls in enumerate(scrapers):
        if progress.iscanceled():
            break
        
        try:
            scraper = scraper_cls()
            scraper_name = scraper.get_name()
            
            if not scraper.is_enabled():
                continue
            
            percent = int((i / total) * 100)
            progress.update(percent, f'Searching: {scraper_name}...\nSources found: {sources_found}')
            
            try:
                results = scraper.search(query, media_type)
                
                for result in results:
                    result['scraper'] = scraper_name
                    all_sources.append(result)
                    sources_found += 1
                
            except Exception as e:
                log_utils.log(f'{scraper_name}: Error - {e}', xbmc.LOGERROR)
                
        except Exception as e:
            log_utils.log(f'Error loading scraper: {e}', xbmc.LOGERROR)
    
    progress.update(100, f'Found {sources_found} sources')
    time.sleep(0.5)
    progress.close()
    
    if not all_sources:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No sources found', ADDON_ICON)
        return
    
    # Sort by seeds (if available) and quality
    all_sources.sort(key=lambda x: (QUALITY_ORDER.get(x.get('quality', 'SD'), 0), x.get('seeds', 0)), reverse=True)
    
    # Display sources
    for source in all_sources:
        scraper_name = source.get('scraper', 'Unknown')
        source_title = source.get('title', 'Unknown')
        quality = source.get('quality', 'SD')
        seeds = source.get('seeds', 0)
        size = source.get('size', '')
        host = source.get('host', scraper_name)
        
        # Build label
        label_parts = [f'[{quality}]', f'[{scraper_name}]']
        if seeds:
            label_parts.append(f'Seeds: {seeds}')
        if size:
            label_parts.append(size)
        label_parts.append(source_title[:60])
        
        label = ' | '.join(label_parts)
        
        # Color coding based on quality
        if quality in ['4K', '2160p']:
            label = f'[COLOR gold]{label}[/COLOR]'
        elif quality in ['1080p', 'HD']:
            label = f'[COLOR lime]{label}[/COLOR]'
        elif quality in ['720p']:
            label = f'[COLOR cyan]{label}[/COLOR]'
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({
            'mode': 'play',
            'url': source.get('url', ''),
            'magnet': source.get('magnet', ''),
            'title': search_title,
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
                progress = xbmcgui.DialogProgress()
                progress.create('SALTS', 'Resolving with Real-Debrid...')
                stream_url = rd.resolve_magnet(magnet)
                progress.close()
                if stream_url:
                    log_utils.log(f'Resolved via Real-Debrid: {stream_url}', xbmc.LOGINFO)
        
        # Check Premiumize
        if not stream_url and ADDON.getSetting('premiumize_enabled') == 'true':
            pm = debrid.Premiumize()
            if pm.is_authorized():
                progress = xbmcgui.DialogProgress()
                progress.create('SALTS', 'Resolving with Premiumize...')
                stream_url = pm.resolve_magnet(magnet)
                progress.close()
                if stream_url:
                    log_utils.log(f'Resolved via Premiumize: {stream_url}', xbmc.LOGINFO)
        
        # Check AllDebrid
        if not stream_url and ADDON.getSetting('alldebrid_enabled') == 'true':
            ad = debrid.AllDebrid()
            if ad.is_authorized():
                progress = xbmcgui.DialogProgress()
                progress.create('SALTS', 'Resolving with AllDebrid...')
                stream_url = ad.resolve_magnet(magnet)
                progress.close()
                if stream_url:
                    log_utils.log(f'Resolved via AllDebrid: {stream_url}', xbmc.LOGINFO)
        
        # No debrid - show message
        if not stream_url:
            xbmcgui.Dialog().ok(ADDON_NAME, 'Torrent sources require a debrid service.\n\nPlease configure Real-Debrid, Premiumize, or AllDebrid in settings.')
            return
    
    # Try ResolveURL for direct links
    if not stream_url and url:
        try:
            import resolveurl
            progress = xbmcgui.DialogProgress()
            progress.create('SALTS', 'Resolving link...')
            stream_url = resolveurl.resolve(url)
            progress.close()
            if stream_url:
                log_utils.log(f'Resolved via ResolveURL: {stream_url}', xbmc.LOGINFO)
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
            
            status = '[COLOR lime]ON[/COLOR]' if enabled else '[COLOR red]OFF[/COLOR]'
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
    setting_id = f'{scraper_name.lower().replace(" ", "_")}_enabled'
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
        
        if enabled and authorized:
            status = '[COLOR lime]Authorized[/COLOR]'
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
            status = f'OK ({len(test_results)} results)' if test_results else 'No Results'
            results.append(f'{name}: {status}')
        except Exception as e:
            results.append(f'{scraper_cls.__name__}: Error - {str(e)[:50]}')
    
    progress.close()
    
    xbmcgui.Dialog().textviewer('Scraper Test Results', '\n'.join(results))

def addon_settings():
    """Open addon settings"""
    ADDON.openSettings()

# ==================== Trakt Functions ====================

def trakt_menu():
    """Trakt.tv menu"""
    from salts_lib.trakt_api import TraktAPI
    trakt = TraktAPI()
    
    if trakt.is_authorized():
        auth_status = '[COLOR lime]Authorized[/COLOR]'
    else:
        auth_status = '[COLOR red]Not Authorized[/COLOR]'
    
    items = [
        {'title': f'Authorization: {auth_status}', 'mode': 'trakt_auth'},
        {'title': 'My Watchlist (Movies)', 'mode': 'trakt_watchlist', 'media_type': 'movies'},
        {'title': 'My Watchlist (TV Shows)', 'mode': 'trakt_watchlist', 'media_type': 'shows'},
        {'title': 'My Collection (Movies)', 'mode': 'trakt_collection', 'media_type': 'movies'},
        {'title': 'My Collection (TV Shows)', 'mode': 'trakt_collection', 'media_type': 'shows'},
        {'title': 'Trending Movies', 'mode': 'trakt_trending', 'media_type': 'movies'},
        {'title': 'Trending TV Shows', 'mode': 'trakt_trending', 'media_type': 'shows'},
        {'title': 'Popular Movies', 'mode': 'trakt_popular', 'media_type': 'movies'},
        {'title': 'Popular TV Shows', 'mode': 'trakt_popular', 'media_type': 'shows'},
        {'title': 'My Lists', 'mode': 'trakt_lists'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_auth():
    """Authorize Trakt"""
    from salts_lib.trakt_api import TraktAPI
    trakt = TraktAPI()
    trakt.authorize()
    xbmc.executebuiltin('Container.Refresh')

def trakt_watchlist(media_type='movies'):
    """Show Trakt watchlist"""
    from salts_lib.trakt_api import TraktAPI
    trakt = TraktAPI()
    
    if not trakt.is_authorized():
        xbmcgui.Dialog().notification(ADDON_NAME, 'Please authorize Trakt first', ADDON_ICON)
        return
    
    items = trakt.get_watchlist(media_type)
    _show_trakt_items(items, media_type)

def trakt_collection(media_type='movies'):
    """Show Trakt collection"""
    from salts_lib.trakt_api import TraktAPI
    trakt = TraktAPI()
    
    if not trakt.is_authorized():
        xbmcgui.Dialog().notification(ADDON_NAME, 'Please authorize Trakt first', ADDON_ICON)
        return
    
    items = trakt.get_collection(media_type)
    _show_trakt_items(items, media_type)

def trakt_trending(media_type='movies'):
    """Show trending on Trakt"""
    from salts_lib.trakt_api import TraktAPI
    trakt = TraktAPI()
    
    items = trakt.get_trending(media_type)
    _show_trakt_items(items, media_type, key='movie' if media_type == 'movies' else 'show')

def trakt_popular(media_type='movies'):
    """Show popular on Trakt"""
    from salts_lib.trakt_api import TraktAPI
    trakt = TraktAPI()
    
    items = trakt.get_popular(media_type)
    _show_trakt_items(items, media_type)

def trakt_lists():
    """Show user's Trakt lists"""
    from salts_lib.trakt_api import TraktAPI
    trakt = TraktAPI()
    
    if not trakt.is_authorized():
        xbmcgui.Dialog().notification(ADDON_NAME, 'Please authorize Trakt first', ADDON_ICON)
        return
    
    lists = trakt.get_lists()
    
    if not lists:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No lists found', ADDON_ICON)
        return
    
    for lst in lists:
        name = lst.get('name', 'Unknown')
        list_id = lst.get('ids', {}).get('slug', '')
        item_count = lst.get('item_count', 0)
        
        label = f'{name} ({item_count} items)'
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': 'trakt_list', 'list_id': list_id})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_list(list_id):
    """Show items in a Trakt list"""
    from salts_lib.trakt_api import TraktAPI
    trakt = TraktAPI()
    
    items = trakt.get_list(list_id)
    
    if not items:
        xbmcgui.Dialog().notification(ADDON_NAME, 'List is empty', ADDON_ICON)
        return
    
    for item in items:
        item_type = item.get('type', 'movie')
        data = item.get(item_type, {})
        
        title = data.get('title', 'Unknown')
        year = data.get('year', '')
        
        label = f'{title} ({year})' if year else title
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        if item_type == 'movie':
            url = build_url({
                'mode': 'get_sources',
                'title': title,
                'year': str(year),
                'media_type': 'movie'
            })
        else:
            url = build_url({
                'mode': 'tv_seasons',
                'title': title,
                'year': str(year),
                'tmdb_id': ''
            })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def _show_trakt_items(items, media_type, key=None):
    """Helper to display Trakt items"""
    if not items:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No items found', ADDON_ICON)
        return
    
    for item in items:
        if key:
            data = item.get(key, item)
        else:
            if 'movie' in item:
                data = item['movie']
            elif 'show' in item:
                data = item['show']
            else:
                data = item
        
        title = data.get('title', 'Unknown')
        year = data.get('year', '')
        
        label = f'{title} ({year})' if year else title
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setYear(int(year) if year else 0)
        info_tag.setPlot(data.get('overview', ''))
        
        if media_type == 'movies':
            url = build_url({
                'mode': 'get_sources',
                'title': title,
                'year': str(year),
                'media_type': 'movie'
            })
        else:
            url = build_url({
                'mode': 'tv_seasons',
                'title': title,
                'year': str(year),
                'tmdb_id': ''
            })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movies' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def router(params):
    """Route to appropriate function based on mode"""
    mode = params.get('mode', '')
    
    log_utils.log(f'SALTS called with mode: {mode}, params: {params}', xbmc.LOGDEBUG)
    
    if not mode:
        main_menu()
    elif mode == 'movies_menu':
        movies_menu()
    elif mode == 'tvshows_menu':
        tvshows_menu()
    elif mode == 'search_menu':
        search_menu()
    elif mode == 'tmdb_list':
        tmdb_list(params.get('list_type', 'popular'), params.get('media_type', 'movie'), int(params.get('page', 1)))
    elif mode == 'search':
        search(params.get('media_type', 'movie'))
    elif mode == 'tv_seasons':
        tv_seasons(params.get('title', ''), params.get('year', ''), params.get('tmdb_id', ''))
    elif mode == 'tv_episodes':
        tv_episodes(params.get('title', ''), params.get('year', ''), params.get('tmdb_id', ''), int(params.get('season', 1)))
    elif mode == 'get_sources':
        get_sources(
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
    elif mode == 'addon_settings':
        addon_settings()
    # Trakt modes
    elif mode == 'trakt_menu':
        trakt_menu()
    elif mode == 'trakt_auth':
        trakt_auth()
    elif mode == 'trakt_watchlist':
        trakt_watchlist(params.get('media_type', 'movies'))
    elif mode == 'trakt_collection':
        trakt_collection(params.get('media_type', 'movies'))
    elif mode == 'trakt_trending':
        trakt_trending(params.get('media_type', 'movies'))
    elif mode == 'trakt_popular':
        trakt_popular(params.get('media_type', 'movies'))
    elif mode == 'trakt_lists':
        trakt_lists()
    elif mode == 'trakt_list':
        trakt_list(params.get('list_id', ''))
    else:
        log_utils.log(f'Unknown mode: {mode}', xbmc.LOGWARNING)
        main_menu()

if __name__ == '__main__':
    params = get_params()
    router(params)
