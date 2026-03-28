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
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

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
        {'title': '[B]Favorites[/B]', 'mode': 'favorites_menu'},
        {'title': '[B]Watch History[/B]', 'mode': 'watch_history_menu'},
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
        {'title': '[COLOR cyan]Browse by Genre[/COLOR]', 'mode': 'genre_list', 'media_type': 'movie'},
        {'title': '[COLOR cyan]Browse by Year[/COLOR]', 'mode': 'year_list', 'media_type': 'movie'},
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
        {'title': '[COLOR cyan]Browse by Genre[/COLOR]', 'mode': 'genre_list', 'media_type': 'tvshow'},
        {'title': '[COLOR cyan]Browse by Year[/COLOR]', 'mode': 'year_list', 'media_type': 'tvshow'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


# TMDB Genre IDs
MOVIE_GENRES = {
    28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime',
    99: 'Documentary', 18: 'Drama', 10751: 'Family', 14: 'Fantasy', 36: 'History',
    27: 'Horror', 10402: 'Music', 9648: 'Mystery', 10749: 'Romance',
    878: 'Science Fiction', 10770: 'TV Movie', 53: 'Thriller', 10752: 'War', 37: 'Western'
}
TV_GENRES = {
    10759: 'Action & Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime',
    99: 'Documentary', 18: 'Drama', 10751: 'Family', 10762: 'Kids', 9648: 'Mystery',
    10763: 'News', 10764: 'Reality', 10765: 'Sci-Fi & Fantasy', 10766: 'Soap',
    10767: 'Talk', 10768: 'War & Politics', 37: 'Western'
}


def genre_list(media_type='movie'):
    """Show list of genres to browse"""
    genres = MOVIE_GENRES if media_type == 'movie' else TV_GENRES
    
    for genre_id, genre_name in sorted(genres.items(), key=lambda x: x[1]):
        li = xbmcgui.ListItem(genre_name)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({
            'mode': 'tmdb_list',
            'list_type': 'discover',
            'media_type': media_type,
            'genre_id': str(genre_id)
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def year_list(media_type='movie'):
    """Show list of years to browse"""
    current_year = datetime.datetime.now().year
    
    for year in range(current_year, 1969, -1):
        li = xbmcgui.ListItem(str(year))
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({
            'mode': 'tmdb_list',
            'list_type': 'discover',
            'media_type': media_type,
            'year': str(year)
        })
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

def tmdb_list(list_type, media_type='movie', page=1, genre_id='', year=''):
    """Get list from TMDB API (free, no key needed for basic lists)"""
    
    # TMDB API (v3)
    base_url = 'https://api.themoviedb.org/3'
    
    # Free API key for demo purposes
    api_key = '8265bd1679663a7ea12ac168da84d2e8'
    
    try:
        if list_type == 'discover':
            # Genre/Year filtered discovery
            tmdb_type = 'movie' if media_type == 'movie' else 'tv'
            api_url = f'{base_url}/discover/{tmdb_type}?api_key={api_key}&page={page}&sort_by=popularity.desc'
            if genre_id:
                api_url += f'&with_genres={genre_id}'
            if year:
                if media_type == 'movie':
                    api_url += f'&primary_release_year={year}'
                else:
                    api_url += f'&first_air_date_year={year}'
        elif media_type == 'movie':
            if list_type == 'popular':
                api_url = f'{base_url}/movie/popular?api_key={api_key}&page={page}'
            elif list_type == 'trending':
                api_url = f'{base_url}/trending/movie/week?api_key={api_key}&page={page}'
            elif list_type == 'top_rated':
                api_url = f'{base_url}/movie/top_rated?api_key={api_key}&page={page}'
            elif list_type == 'now_playing':
                api_url = f'{base_url}/movie/now_playing?api_key={api_key}&page={page}'
            else:
                api_url = f'{base_url}/movie/popular?api_key={api_key}&page={page}'
        else:  # tvshow
            if list_type == 'popular':
                api_url = f'{base_url}/tv/popular?api_key={api_key}&page={page}'
            elif list_type == 'trending':
                api_url = f'{base_url}/trending/tv/week?api_key={api_key}&page={page}'
            elif list_type == 'top_rated':
                api_url = f'{base_url}/tv/top_rated?api_key={api_key}&page={page}'
            elif list_type == 'airing_today':
                api_url = f'{base_url}/tv/airing_today?api_key={api_key}&page={page}'
            else:
                api_url = f'{base_url}/tv/popular?api_key={api_key}&page={page}'
        
        log_utils.log(f'TMDB URL: {api_url}', xbmc.LOGDEBUG)
        
        # Use urllib instead of requests
        req = Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req, timeout=15)
        data = json.loads(response.read().decode('utf-8'))
        
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
            
            # Watch history overlay
            tmdb_id_str = str(item.get('id', ''))
            watched_db = db_utils.DB_Connection()
            if watched_db.is_watched_by_tmdb(tmdb_id_str, media_type if media_type == 'movie' else 'tvshow'):
                info_tag.setPlaycount(1)  # Shows watched overlay in Kodi
            
            # Context menu - Add to Favorites
            _fav_url = build_url({
                'mode': 'add_favorite', 'media_type': media_type if media_type == 'movie' else 'tvshow',
                'title': title, 'year': year, 'tmdb_id': tmdb_id_str,
                'poster': poster_url, 'overview': overview[:200], 'rating': str(rating)
            })
            li.addContextMenuItems([('Add to Favorites', f'RunPlugin({_fav_url})')])
            
            if media_type == 'movie':
                item_url = build_url({
                    'mode': 'get_sources',
                    'title': title,
                    'year': year,
                    'media_type': 'movie',
                    'tmdb_id': tmdb_id_str
                })
            else:
                item_url = build_url({
                    'mode': 'tv_seasons',
                    'title': title,
                    'year': year,
                    'tmdb_id': item.get('id', '')
                })
            
            xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
        
        # Add next page
        if data.get('page', 1) < data.get('total_pages', 1):
            li = xbmcgui.ListItem('[B]>> Next Page[/B]')
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            next_url = build_url({
                'mode': 'tmdb_list',
                'list_type': list_type,
                'media_type': media_type,
                'page': page + 1
            })
            xbmcplugin.addDirectoryItem(HANDLE, next_url, li, isFolder=True)
        
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
    
    base_url = 'https://api.themoviedb.org/3'
    api_key = '8265bd1679663a7ea12ac168da84d2e8'
    
    try:
        if media_type == 'movie':
            api_url = f'{base_url}/search/movie?api_key={api_key}&query={quote_plus(query)}'
        else:
            api_url = f'{base_url}/search/tv?api_key={api_key}&query={quote_plus(query)}'
        
        log_utils.log(f'Search URL: {api_url}', xbmc.LOGDEBUG)
        
        # Use urllib instead of requests
        req = Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req, timeout=15)
        data = json.loads(response.read().decode('utf-8'))
        
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
            
            # Context menu - Add to Favorites
            _fav_url2 = build_url({
                'mode': 'add_favorite', 'media_type': media_type if media_type == 'movie' else 'tvshow',
                'title': title, 'year': year, 'tmdb_id': str(item.get('id', '')),
                'poster': poster_url, 'overview': overview[:200], 'rating': str(rating)
            })
            li.addContextMenuItems([('Add to Favorites', f'RunPlugin({_fav_url2})')])
            
            if media_type == 'movie':
                item_url = build_url({
                    'mode': 'get_sources',
                    'title': title,
                    'year': year,
                    'media_type': 'movie',
                    'tmdb_id': item.get('id', '')
                })
            else:
                item_url = build_url({
                    'mode': 'tv_seasons',
                    'title': title,
                    'year': year,
                    'tmdb_id': item.get('id', '')
                })
            
            xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
        
        xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movie' else 'tvshows')
        xbmcplugin.endOfDirectory(HANDLE)
        
    except Exception as e:
        log_utils.log(f'Search error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, f'Error: {e}', ADDON_ICON)

def tv_seasons(title, year='', tmdb_id=''):
    """Show seasons for a TV show"""
    
    base_url = 'https://api.themoviedb.org/3'
    api_key = '8265bd1679663a7ea12ac168da84d2e8'
    
    try:
        if tmdb_id:
            api_url = f'{base_url}/tv/{tmdb_id}?api_key={api_key}'
            req = Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urlopen(req, timeout=15)
            data = json.loads(response.read().decode('utf-8'))
            
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
                
                item_url = build_url({
                    'mode': 'tv_episodes',
                    'title': title,
                    'year': year,
                    'tmdb_id': tmdb_id,
                    'season': season_num
                })
                
                xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
            
            xbmcplugin.setContent(HANDLE, 'seasons')
            xbmcplugin.endOfDirectory(HANDLE)
        else:
            # No TMDB ID, show generic seasons 1-10
            for i in range(1, 11):
                li = xbmcgui.ListItem(f'Season {i}')
                li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
                item_url = build_url({
                    'mode': 'tv_episodes',
                    'title': title,
                    'year': year,
                    'season': i
                })
                xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
            
            xbmcplugin.setContent(HANDLE, 'seasons')
            xbmcplugin.endOfDirectory(HANDLE)
            
    except Exception as e:
        log_utils.log(f'TV seasons error: {e}', xbmc.LOGERROR)
        # Fallback to generic seasons
        for i in range(1, 11):
            li = xbmcgui.ListItem(f'Season {i}')
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            item_url = build_url({
                'mode': 'tv_episodes',
                'title': title,
                'year': year,
                'season': i
            })
            xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
        
        xbmcplugin.setContent(HANDLE, 'seasons')
        xbmcplugin.endOfDirectory(HANDLE)

def tv_episodes(title, year='', tmdb_id='', season=1):
    """Show episodes for a season"""
    
    base_url = 'https://api.themoviedb.org/3'
    api_key = '8265bd1679663a7ea12ac168da84d2e8'
    
    try:
        if tmdb_id:
            api_url = f'{base_url}/tv/{tmdb_id}/season/{season}?api_key={api_key}'
            req = Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urlopen(req, timeout=15)
            data = json.loads(response.read().decode('utf-8'))
            
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
                
                item_url = build_url({
                    'mode': 'get_sources',
                    'title': title,
                    'year': year,
                    'season': season,
                    'episode': ep_num,
                    'media_type': 'tvshow',
                    'tmdb_id': tmdb_id
                })
                
                xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
            
            xbmcplugin.setContent(HANDLE, 'episodes')
            xbmcplugin.endOfDirectory(HANDLE)
        else:
            # No TMDB ID, show generic episodes 1-20
            for i in range(1, 21):
                li = xbmcgui.ListItem(f'Episode {i}')
                li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
                item_url = build_url({
                    'mode': 'get_sources',
                    'title': title,
                    'year': year,
                    'season': season,
                    'episode': i,
                    'media_type': 'tvshow'
                })
                xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
            
            xbmcplugin.setContent(HANDLE, 'episodes')
            xbmcplugin.endOfDirectory(HANDLE)
            
    except Exception as e:
        log_utils.log(f'TV episodes error: {e}', xbmc.LOGERROR)
        # Fallback to generic episodes
        for i in range(1, 21):
            li = xbmcgui.ListItem(f'Episode {i}')
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            item_url = build_url({
                'mode': 'get_sources',
                'title': title,
                'year': year,
                'season': season,
                'episode': i,
                'media_type': 'tvshow'
            })
            xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
        
        xbmcplugin.setContent(HANDLE, 'episodes')
        xbmcplugin.endOfDirectory(HANDLE)

def get_sources(title, year='', season='', episode='', media_type='movie', tmdb_id=''):
    """Get all available sources for a title with caching, custom dialog, and autoplay"""
    from scrapers import get_all_scrapers
    from scrapers.freestream_scraper import FreeStreamScraper
    
    # Build search query
    if media_type == 'movie':
        query = f'{title} {year}' if year else title
        search_title = f'{title} ({year})' if year else title
    else:
        query = f'{title} S{int(season):02d}E{int(episode):02d}'
        search_title = f'{title} S{int(season):02d}E{int(episode):02d}'
    
    # Check source cache first
    cache_key = f'{media_type}|{title}|{year}|{season}|{episode}'
    db = db_utils.DB_Connection()
    use_cache = ADDON.getSetting('source_cache_enabled') != 'false'
    
    if use_cache:
        cache_hours = float(ADDON.getSetting('source_cache_hours') or 2)
        cached_sources, cache_time = db.get_cached_sources(cache_key, cache_hours)
        if cached_sources:
            import datetime as dt
            cache_age = int((time.time() - cache_time) / 60)
            log_utils.log(f'Source cache hit for {cache_key}: {len(cached_sources)} sources ({cache_age}m old)', xbmc.LOGINFO)
            
            # Ask user: use cache or re-scrape?
            use_cached = xbmcgui.Dialog().yesno(
                'SALTS - Cached Sources',
                f'{len(cached_sources)} cached sources found ({cache_age} min old)\n\nUse cached or re-scrape?',
                yeslabel='Use Cached',
                nolabel='Re-Scrape',
                autoclose=10000
            )
            
            if use_cached:
                all_sources = cached_sources
                # Jump straight to display/autoplay
                return _display_or_autoplay_sources(all_sources, search_title, media_type,
                                                     title, year, season, episode, tmdb_id)
    
    progress = xbmcgui.DialogProgress()
    progress.create('SALTS', f'Searching for: {search_title}')
    
    all_sources = []
    scrapers = get_all_scrapers()
    
    # Apply scraper priority ordering
    priorities = db.get_all_scraper_priorities()
    if priorities:
        def scraper_sort_key(cls):
            try:
                s = cls()
                return priorities.get(s.get_name(), 100)
            except Exception:
                return 100
        scrapers.sort(key=scraper_sort_key)
    
    total = len(scrapers)
    sources_found = 0
    scraper_count = 0
    free_count = 0
    
    for i, scraper_cls in enumerate(scrapers):
        if progress.iscanceled():
            break
        
        try:
            scraper = scraper_cls()
            scraper_name = scraper.get_name()
            
            if not scraper.is_enabled():
                continue
            
            scraper_count += 1
            percent = int((i / total) * 100)
            progress.update(percent, f'Searching: {scraper_name}...\nScrapers: {scraper_count} | Sources: {sources_found} | Free: {free_count}')
            
            try:
                if isinstance(scraper, FreeStreamScraper):
                    results = scraper.search(
                        query, media_type,
                        tmdb_id=tmdb_id,
                        title=title, year=year,
                        season=season, episode=episode
                    )
                else:
                    results = scraper.search(query, media_type)
                
                for result in results:
                    result['scraper'] = scraper_name
                    all_sources.append(result)
                    sources_found += 1
                    if result.get('direct'):
                        free_count += 1
                
            except Exception as e:
                log_utils.log(f'{scraper_name}: Error - {e}', xbmc.LOGERROR)
                
        except Exception as e:
            log_utils.log(f'Error loading scraper: {e}', xbmc.LOGERROR)
    
    progress.update(100, f'Found {sources_found} sources ({free_count} free) from {scraper_count} scrapers')
    time.sleep(0.5)
    progress.close()
    
    if not all_sources:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No sources found', ADDON_ICON)
        return
    
    # Cache the results
    if use_cache:
        db.cache_sources(cache_key, all_sources)
    
    _display_or_autoplay_sources(all_sources, search_title, media_type,
                                 title, year, season, episode, tmdb_id)


def _display_or_autoplay_sources(all_sources, search_title, media_type,
                                  title, year, season, episode, tmdb_id):
    """Sort, display source dialog or autoplay"""
    # Sort: free direct streams first, then by quality and seeds
    def sort_key(x):
        is_free = 1 if x.get('direct') else 0
        quality = QUALITY_ORDER.get(x.get('quality', 'SD'), 0)
        seeds = x.get('seeds', 0)
        return (is_free, quality, seeds)
    
    all_sources.sort(key=sort_key, reverse=True)
    
    # Autoplay: if enabled, pick the best source and play immediately
    autoplay = ADDON.getSetting('auto_play') == 'true'
    if autoplay and all_sources:
        chosen = all_sources[0]
        log_utils.log(f'Autoplay: picking {chosen.get("scraper")} - {chosen.get("quality")}', xbmc.LOGINFO)
        _play_source(
            url=chosen.get('url', ''),
            magnet=chosen.get('magnet', ''),
            title=search_title,
            scraper=chosen.get('scraper', ''),
            media_type=media_type,
            show_title=title,
            year=year,
            season=season,
            episode=episode,
            tmdb_id=tmdb_id
        )
        return
    
    # Count totals
    free_count = sum(1 for s in all_sources if s.get('direct'))
    sources_found = len(all_sources)
    
    # Count quality breakdown
    quality_counts = {}
    for s in all_sources:
        q = s.get('quality', 'SD')
        quality_counts[q] = quality_counts.get(q, 0) + 1
    
    q_parts = []
    for q in ['4K', '2160p', '1080p', 'HD', '720p', '480p', 'SD']:
        if q in quality_counts:
            q_parts.append(f'{q}: {quality_counts[q]}')
    quality_summary = ' | '.join(q_parts) if q_parts else 'Mixed'
    
    # Build display list
    display_list = []
    for source in all_sources:
        scraper_name = source.get('scraper', 'Unknown')
        source_title = source.get('title', 'Unknown')
        quality = source.get('quality', 'SD')
        seeds = source.get('seeds', 0)
        size = source.get('size', '')
        is_free = source.get('direct', False)
        
        label_parts = [f'[{quality}]']
        if is_free:
            label_parts.append('[FREE]')
        label_parts.append(f'[{scraper_name}]')
        if seeds and not is_free:
            label_parts.append(f'Seeds: {seeds}')
        if size:
            label_parts.append(size)
        label_parts.append(source_title[:80])
        
        label = ' | '.join(label_parts)
        
        if is_free:
            label = f'[COLOR orange]{label}[/COLOR]'
        elif quality in ['4K', '2160p']:
            label = f'[COLOR gold]{label}[/COLOR]'
        elif quality in ['1080p', 'HD']:
            label = f'[COLOR lime]{label}[/COLOR]'
        elif quality in ['720p']:
            label = f'[COLOR cyan]{label}[/COLOR]'
        else:
            label = f'[COLOR white]{label}[/COLOR]'
        
        display_list.append(label)
    
    header = f'SALTS: {sources_found} sources ({free_count} free)  [{quality_summary}]'
    selected = xbmcgui.Dialog().select(header, display_list, useDetails=False)
    
    if selected < 0:
        return
    
    chosen = all_sources[selected]
    
    _play_source(
        url=chosen.get('url', ''),
        magnet=chosen.get('magnet', ''),
        title=search_title,
        scraper=chosen.get('scraper', ''),
        media_type=media_type,
        show_title=title,
        year=year,
        season=season,
        episode=episode,
        tmdb_id=tmdb_id
    )

def _play_source(url='', magnet='', title='', scraper='', media_type='movie',
                  show_title='', year='', season='', episode='', tmdb_id=''):
    """Resolve and play a source using xbmc.Player().play() to avoid rescrape loop"""
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
        # Check if URL is already a direct stream (m3u8, mp4) from free providers
        if any(ext in url.lower() for ext in ['.m3u8', '.mp4', '.mkv', '.avi']):
            stream_url = url
            log_utils.log(f'Direct stream URL: {stream_url}', xbmc.LOGINFO)
        else:
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
                stream_url = url  # Fallback to raw URL
    
    if not stream_url:
        xbmcgui.Dialog().notification(ADDON_NAME, 'Could not resolve source', ADDON_ICON)
        return
    
    # Build ListItem and play with xbmc.Player() to avoid container refresh / rescrape
    li = xbmcgui.ListItem(title, path=stream_url)
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    
    # Set inputstream.adaptive for HLS/m3u8 streams
    if '.m3u8' in stream_url.lower():
        try:
            li.setProperty('inputstream', 'inputstream.adaptive')
            li.setProperty('inputstream.adaptive.manifest_type', 'hls')
            li.setMimeType('application/vnd.apple.mpegurl')
            li.setContentLookup(False)
            log_utils.log(f'Set inputstream.adaptive for HLS: {stream_url}', xbmc.LOGINFO)
        except Exception as e:
            log_utils.log(f'inputstream.adaptive setup error (will try direct): {e}', xbmc.LOGDEBUG)
    elif '.mpd' in stream_url.lower():
        try:
            li.setProperty('inputstream', 'inputstream.adaptive')
            li.setProperty('inputstream.adaptive.manifest_type', 'mpd')
            li.setMimeType('application/dash+xml')
            li.setContentLookup(False)
        except Exception:
            pass
    
    player = xbmc.Player()
    player.play(stream_url, li)
    
    # Wait for playback to start
    timeout = 30
    while not player.isPlaying() and timeout > 0:
        xbmc.sleep(500)
        timeout -= 1
    
    if not player.isPlaying():
        log_utils.log('Playback failed to start', xbmc.LOGWARNING)
        return
    
    # Auto-load subtitles
    if ADDON.getSetting('auto_subtitles') == 'true':
        try:
            from salts_lib.opensubtitles import auto_download_subtitle
            sub_path = auto_download_subtitle(
                title=show_title or title, year=year, season=season,
                episode=episode, tmdb_id=tmdb_id, media_type=media_type
            )
            if sub_path:
                player.setSubtitles(sub_path)
                log_utils.log(f'Subtitle loaded: {sub_path}', xbmc.LOGINFO)
        except Exception as e:
            log_utils.log(f'Auto-subtitle error: {e}', xbmc.LOGDEBUG)
    
    # Track in watch history
    db = db_utils.DB_Connection()
    db.add_to_watch_history(media_type, show_title or title, year, tmdb_id, season, episode)
    
    # Monitor playback for skip intro, next episode, and Trakt scrobble
    _monitor_playback(player, media_type, show_title, year, season, episode, tmdb_id)


def _monitor_playback(player, media_type, show_title, year, season, episode, tmdb_id=''):
    """Monitor playback for skip intro, next episode, pre-emptive scraping, and Trakt scrobble"""
    skip_intro_shown = False
    next_ep_shown = False
    preemptive_done = False
    scrobble_started = False
    scrobble_stopped = False
    skip_intro_seconds = int(ADDON.getSetting('skip_intro_duration') or 90)
    next_ep_enabled = ADDON.getSetting('next_episode_enabled') == 'true'
    skip_intro_enabled = ADDON.getSetting('skip_intro_enabled') == 'true'
    preemptive_enabled = ADDON.getSetting('preemptive_scrape') == 'true'
    trakt_scrobble = ADDON.getSetting('trakt_scrobble') == 'true'
    
    total_time = 0
    trakt_api = None
    
    # Init Trakt scrobble if enabled
    if trakt_scrobble:
        try:
            from salts_lib.trakt_api import TraktAPI
            trakt_api = TraktAPI()
            if not trakt_api.is_authorized():
                trakt_api = None
        except Exception as e:
            log_utils.log(f'Trakt scrobble init error: {e}', xbmc.LOGDEBUG)
            trakt_api = None
    
    while player.isPlaying():
        try:
            current_time = player.getTime()
            if total_time == 0:
                try:
                    total_time = player.getTotalTime()
                except Exception:
                    pass
            
            progress = (current_time / total_time * 100) if total_time > 0 else 0
            
            # Trakt: Start scrobble at beginning
            if trakt_api and not scrobble_started and current_time > 5:
                scrobble_started = True
                try:
                    trakt_media = 'movies' if media_type == 'movie' else 'shows'
                    trakt_api.scrobble_start(trakt_media, tmdb_id or show_title, progress)
                    log_utils.log(f'Trakt scrobble started: {show_title}', xbmc.LOGINFO)
                except Exception as e:
                    log_utils.log(f'Trakt scrobble start error: {e}', xbmc.LOGDEBUG)
            
            # Skip Intro: show during first N seconds of TV episodes
            if (skip_intro_enabled and media_type == 'tvshow' and not skip_intro_shown
                    and 5 < current_time < skip_intro_seconds):
                skip_intro_shown = True
                if xbmcgui.Dialog().yesno('SALTS', 'Skip Intro?', 
                                           yeslabel='Skip', nolabel='Watch',
                                           autoclose=8000):
                    skip_to = float(skip_intro_seconds)
                    player.seekTime(skip_to)
                    log_utils.log(f'Skipped intro to {skip_to}s', xbmc.LOGINFO)
            
            # Pre-emptive scraping: start scraping next episode at 75% through
            if (preemptive_enabled and media_type == 'tvshow' and not preemptive_done
                    and total_time > 0 and season and episode):
                if progress > 75:
                    preemptive_done = True
                    next_ep = int(episode) + 1
                    log_utils.log(f'Pre-emptive scrape: {show_title} S{int(season):02d}E{next_ep:02d}', xbmc.LOGINFO)
                    try:
                        _preemptive_scrape(show_title, year, season, str(next_ep))
                    except Exception as e:
                        log_utils.log(f'Pre-emptive scrape error: {e}', xbmc.LOGDEBUG)
            
            # Next Episode: prompt when last 120 seconds
            if (next_ep_enabled and media_type == 'tvshow' and not next_ep_shown
                    and total_time > 0 and season and episode):
                remaining = total_time - current_time
                if remaining < 120 and remaining > 0:
                    next_ep_shown = True
                    next_ep = int(episode) + 1
                    if xbmcgui.Dialog().yesno(
                        'SALTS - Up Next',
                        f'Play next episode?\n{show_title} S{int(season):02d}E{next_ep:02d}',
                        yeslabel='Play Next',
                        nolabel='Stop',
                        autoclose=30000
                    ):
                        # Trakt: stop scrobble before switching
                        if trakt_api and scrobble_started:
                            try:
                                trakt_media = 'movies' if media_type == 'movie' else 'shows'
                                trakt_api.scrobble_stop(trakt_media, tmdb_id or show_title, progress)
                            except Exception:
                                pass
                        player.stop()
                        xbmc.sleep(500)
                        get_sources(show_title, year, season, str(next_ep), 'tvshow')
                        return
            
        except Exception as e:
            log_utils.log(f'Playback monitor: {e}', xbmc.LOGDEBUG)
            break
        
        xbmc.sleep(2000)
    
    # Playback ended - Trakt: stop scrobble
    if trakt_api and scrobble_started and not scrobble_stopped:
        scrobble_stopped = True
        try:
            final_progress = progress if total_time > 0 else 100
            trakt_media = 'movies' if media_type == 'movie' else 'shows'
            trakt_api.scrobble_stop(trakt_media, tmdb_id or show_title, final_progress)
            log_utils.log(f'Trakt scrobble stopped at {final_progress:.0f}%', xbmc.LOGINFO)
        except Exception as e:
            log_utils.log(f'Trakt scrobble stop error: {e}', xbmc.LOGDEBUG)


def _preemptive_scrape(title, year, season, episode):
    """Pre-emptively scrape next episode and cache results (no UI)"""
    from scrapers import get_all_scrapers
    from scrapers.freestream_scraper import FreeStreamScraper
    
    cache_key = f'tvshow|{title}|{year}|{season}|{episode}'
    db = db_utils.DB_Connection()
    
    # Skip if already cached
    cached, _ = db.get_cached_sources(cache_key, 2)
    if cached:
        return
    
    query = f'{title} S{int(season):02d}E{int(episode):02d}'
    all_sources = []
    
    for scraper_cls in get_all_scrapers():
        try:
            scraper = scraper_cls()
            if not scraper.is_enabled():
                continue
            
            if isinstance(scraper, FreeStreamScraper):
                results = scraper.search(query, 'tvshow', title=title, year=year,
                                         season=season, episode=episode)
            else:
                results = scraper.search(query, 'tvshow')
            
            for r in results:
                r['scraper'] = scraper.get_name()
                all_sources.append(r)
                
        except Exception:
            continue
    
    if all_sources:
        db.cache_sources(cache_key, all_sources)
        log_utils.log(f'Pre-emptive cache: {len(all_sources)} sources for {cache_key}', xbmc.LOGINFO)


def play(url='', magnet='', title='', scraper=''):
    """Legacy play route - redirects to _play_source"""
    _play_source(url=url, magnet=magnet, title=title, scraper=scraper)

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
        {'title': 'Clear Source Cache', 'mode': 'clear_source_cache'},
        {'title': 'Search Subtitles', 'mode': 'subtitle_search_dialog'},
        {'title': 'Test Scrapers', 'mode': 'test_scrapers'},
        {'title': 'Quality Presets', 'mode': 'quality_presets_menu'},
        {'title': 'Scraper Priority', 'mode': 'scraper_priority_menu'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True if item['mode'] in ['quality_presets_menu', 'scraper_priority_menu'] else False)
    
    xbmcplugin.endOfDirectory(HANDLE)

def clear_cache():
    """Clear addon cache"""
    db = db_utils.DB_Connection()
    db.flush_cache()
    xbmcgui.Dialog().notification(ADDON_NAME, 'Cache cleared', ADDON_ICON)

def clear_source_cache():
    """Clear source cache only"""
    db = db_utils.DB_Connection()
    db.clear_source_cache()
    xbmcgui.Dialog().notification(ADDON_NAME, 'Source cache cleared', ADDON_ICON)

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



# ==================== Watch History ====================

def watch_history_menu():
    """Watch history menu"""
    items = [
        {'title': '[B]Recently Watched Movies[/B]', 'mode': 'watch_history_list', 'media_type': 'movie'},
        {'title': '[B]Recently Watched TV Shows[/B]', 'mode': 'watch_history_list', 'media_type': 'tvshow'},
        {'title': '[COLOR red]Clear Watch History[/COLOR]', 'mode': 'clear_watch_history'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        is_folder = item['mode'] != 'clear_watch_history'
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    
    xbmcplugin.endOfDirectory(HANDLE)


def watch_history_list(media_type='movie'):
    """Show watch history"""
    db = db_utils.DB_Connection()
    history = db.get_watch_history(media_type)
    
    if not history:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No watch history', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for item in history:
        title = item.get('title', 'Unknown')
        year = item.get('year', '')
        tmdb_id = item.get('tmdb_id', '')
        season = item.get('season', '')
        episode = item.get('episode', '')
        
        if season and episode:
            label = f'{title} S{int(season):02d}E{int(episode):02d}'
        else:
            label = f'{title} ({year})' if year else title
        
        # Add watched indicator
        label = f'[COLOR lime]*[/COLOR] {label}'
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setPlaycount(1)
        
        if media_type == 'movie':
            item_url = build_url({
                'mode': 'get_sources', 'title': title, 'year': year,
                'media_type': 'movie', 'tmdb_id': tmdb_id
            })
        else:
            if season and episode:
                item_url = build_url({
                    'mode': 'get_sources', 'title': title, 'year': year,
                    'season': season, 'episode': episode,
                    'media_type': 'tvshow', 'tmdb_id': tmdb_id
                })
            else:
                item_url = build_url({
                    'mode': 'tv_seasons', 'title': title, 'year': year, 'tmdb_id': tmdb_id
                })
        
        xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=(media_type != 'movie' and not (season and episode)))
    
    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movie' else 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)


def clear_watch_history():
    """Clear all watch history"""
    if xbmcgui.Dialog().yesno('SALTS', 'Clear all watch history?'):
        db = db_utils.DB_Connection()
        db.clear_watch_history()
        xbmcgui.Dialog().notification(ADDON_NAME, 'Watch history cleared', ADDON_ICON)


# ==================== Subtitles ====================

def subtitle_search(title='', year='', season='', episode='',
                     tmdb_id='', media_type='movie'):
    """Search and download subtitles via dialog"""
    from salts_lib.opensubtitles import show_subtitle_dialog
    
    sub_path = show_subtitle_dialog(title, year, season, episode,
                                     tmdb_id, '', media_type)
    if sub_path:
        player = xbmc.Player()
        if player.isPlaying():
            player.setSubtitles(sub_path)
            xbmcgui.Dialog().notification(ADDON_NAME, 'Subtitle loaded', ADDON_ICON)


# ==================== Favorites ====================

def favorites_menu():
    """Favorites main menu"""
    items = [
        {'title': '[B]Favorite Movies[/B]', 'mode': 'favorites_list', 'media_type': 'movie'},
        {'title': '[B]Favorite TV Shows[/B]', 'mode': 'favorites_list', 'media_type': 'tvshow'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def favorites_list(media_type='movie'):
    """Show favorites list"""
    db = db_utils.DB_Connection()
    favs = db.get_favorites(media_type)
    
    if not favs:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No favorites yet', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for fav in favs:
        title = fav.get('title', 'Unknown')
        year = fav.get('year', '')
        tmdb_id = fav.get('tmdb_id', '')
        poster = fav.get('poster', '')
        fanart_img = fav.get('fanart', '')
        overview = fav.get('overview', '')
        rating = fav.get('rating', 0)
        
        label = f'{title} ({year})' if year else title
        
        li = xbmcgui.ListItem(label)
        li.setArt({
            'icon': poster or ADDON_ICON,
            'poster': poster,
            'fanart': fanart_img or ADDON_FANART,
            'thumb': poster
        })
        
        info = {'title': title, 'year': int(year) if year else 0, 'plot': overview, 'rating': rating}
        li.setInfo('video', info)
        
        # Context menu to remove from favorites
        ctx_menu = [
            ('Remove from Favorites', f'RunPlugin({build_url({"mode": "remove_favorite", "media_type": media_type, "title": title, "year": year})})'),
        ]
        li.addContextMenuItems(ctx_menu)
        
        if media_type == 'movie':
            item_url = build_url({
                'mode': 'get_sources', 'title': title, 'year': year,
                'media_type': 'movie', 'tmdb_id': tmdb_id
            })
        else:
            item_url = build_url({
                'mode': 'tv_seasons', 'title': title, 'year': year, 'tmdb_id': tmdb_id
            })
        
        xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=(media_type != 'movie'))
    
    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movie' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)


def add_favorite(media_type, title, year='', tmdb_id='', poster='', fanart='', overview='', rating=0):
    """Add item to favorites"""
    db = db_utils.DB_Connection()
    db.add_favorite(media_type, title, year, tmdb_id, poster, fanart, overview, rating)
    xbmcgui.Dialog().notification(ADDON_NAME, f'Added to Favorites: {title}', ADDON_ICON)


def remove_favorite(media_type, title, year=''):
    """Remove item from favorites"""
    db = db_utils.DB_Connection()
    db.remove_favorite(media_type, title, year)
    xbmcgui.Dialog().notification(ADDON_NAME, f'Removed from Favorites: {title}', ADDON_ICON)
    xbmc.executebuiltin('Container.Refresh')


# ==================== Quality Presets ====================

def quality_presets_menu():
    """Quality presets menu"""
    db = db_utils.DB_Connection()
    presets = db.get_all_quality_presets()
    
    # Add "Create New Preset" option
    li = xbmcgui.ListItem('[B]+ Create New Preset[/B]')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({'mode': 'create_quality_preset'})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    # Built-in presets
    builtin = {
        'Best Quality (WiFi)': {'min_quality': '1080p', 'filter_cam': 'true', 'auto_play': 'false'},
        'Fast Play (Mobile)': {'min_quality': 'Any', 'filter_cam': 'true', 'auto_play': 'true'},
        'Data Saver': {'min_quality': '480p', 'filter_cam': 'true', 'auto_play': 'true'},
        '4K Only': {'min_quality': '4K', 'filter_cam': 'true', 'auto_play': 'false'},
    }
    
    for name in builtin:
        if name not in presets:
            presets[name] = builtin[name]
    
    for name, settings in presets.items():
        quality = settings.get('min_quality', 'Any')
        autoplay = 'Autoplay' if settings.get('auto_play') == 'true' else 'Manual'
        
        label = f'{name} - [COLOR cyan]{quality}[/COLOR] / [COLOR yellow]{autoplay}[/COLOR]'
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        ctx_menu = [
            ('Delete Preset', f'RunPlugin({build_url({"mode": "delete_quality_preset", "name": name})})'),
        ]
        li.addContextMenuItems(ctx_menu)
        
        url = build_url({'mode': 'apply_quality_preset', 'name': name})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def create_quality_preset():
    """Create a new quality preset from current settings"""
    name = xbmcgui.Dialog().input('Preset Name')
    if not name:
        return
    
    settings = {
        'min_quality': ADDON.getSetting('min_quality'),
        'filter_cam': ADDON.getSetting('filter_cam'),
        'auto_play': ADDON.getSetting('auto_play'),
        'sort_by': ADDON.getSetting('sort_by'),
        'source_timeout': ADDON.getSetting('source_timeout'),
    }
    
    db = db_utils.DB_Connection()
    db.save_quality_preset(name, settings)
    xbmcgui.Dialog().notification(ADDON_NAME, f'Preset saved: {name}', ADDON_ICON)


def apply_quality_preset(name):
    """Apply a quality preset"""
    db = db_utils.DB_Connection()
    settings = db.get_quality_preset(name)
    
    if not settings:
        # Check built-in presets
        builtin = {
            'Best Quality (WiFi)': {'min_quality': '1080p', 'filter_cam': 'true', 'auto_play': 'false'},
            'Fast Play (Mobile)': {'min_quality': 'Any', 'filter_cam': 'true', 'auto_play': 'true'},
            'Data Saver': {'min_quality': '480p', 'filter_cam': 'true', 'auto_play': 'true'},
            '4K Only': {'min_quality': '4K', 'filter_cam': 'true', 'auto_play': 'false'},
        }
        settings = builtin.get(name)
    
    if settings:
        for key, value in settings.items():
            ADDON.setSetting(key, str(value))
        xbmcgui.Dialog().notification(ADDON_NAME, f'Applied preset: {name}', ADDON_ICON)
    else:
        xbmcgui.Dialog().notification(ADDON_NAME, f'Preset not found: {name}', ADDON_ICON)


def delete_quality_preset(name):
    """Delete a quality preset"""
    db = db_utils.DB_Connection()
    db.delete_quality_preset(name)
    xbmcgui.Dialog().notification(ADDON_NAME, f'Deleted preset: {name}', ADDON_ICON)
    xbmc.executebuiltin('Container.Refresh')


# ==================== Scraper Priority ====================

def scraper_priority_menu():
    """Scraper priority ordering menu"""
    from scrapers import get_all_scrapers
    
    db = db_utils.DB_Connection()
    priorities = db.get_all_scraper_priorities()
    
    scrapers = get_all_scrapers()
    scraper_list = []
    
    for cls in scrapers:
        try:
            s = cls()
            name = s.get_name()
            enabled = s.is_enabled()
            priority = priorities.get(name, 100)
            scraper_list.append((name, priority, enabled))
        except Exception:
            continue
    
    # Sort by priority
    scraper_list.sort(key=lambda x: x[1])
    
    for i, (name, priority, enabled) in enumerate(scraper_list):
        status = '[COLOR lime]ON[/COLOR]' if enabled else '[COLOR red]OFF[/COLOR]'
        label = f'{i+1}. {name} - {status} (Priority: {priority})'
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        ctx_menu = [
            ('Move Up', f'RunPlugin({build_url({"mode": "set_scraper_priority", "scraper": name, "priority": max(1, priority - 10)})})'),
            ('Move Down', f'RunPlugin({build_url({"mode": "set_scraper_priority", "scraper": name, "priority": priority + 10})})'),
            ('Set Priority', f'RunPlugin({build_url({"mode": "set_scraper_priority_manual", "scraper": name})})'),
            ('Toggle Enable', f'RunPlugin({build_url({"mode": "toggle_scraper", "scraper": name})})'),
        ]
        li.addContextMenuItems(ctx_menu)
        
        url = build_url({'mode': 'set_scraper_priority_manual', 'scraper': name})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def set_scraper_priority(scraper_name, priority):
    """Set scraper priority"""
    db = db_utils.DB_Connection()
    db.set_scraper_priority(scraper_name, int(priority))
    xbmcgui.Dialog().notification(ADDON_NAME, f'{scraper_name} priority: {priority}', ADDON_ICON)
    xbmc.executebuiltin('Container.Refresh')


def set_scraper_priority_manual(scraper_name):
    """Manually set scraper priority via dialog"""
    db = db_utils.DB_Connection()
    current = db.get_scraper_priority(scraper_name)
    
    new_priority = xbmcgui.Dialog().numeric(0, f'Priority for {scraper_name} (1=highest)', str(current))
    if new_priority:
        db.set_scraper_priority(scraper_name, int(new_priority))
        xbmcgui.Dialog().notification(ADDON_NAME, f'{scraper_name} priority: {new_priority}', ADDON_ICON)
        xbmc.executebuiltin('Container.Refresh')


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
        tmdb_list(params.get('list_type', 'popular'), params.get('media_type', 'movie'),
                  int(params.get('page', 1)), params.get('genre_id', ''), params.get('year', ''))
    elif mode == 'genre_list':
        genre_list(params.get('media_type', 'movie'))
    elif mode == 'year_list':
        year_list(params.get('media_type', 'movie'))
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
            params.get('media_type', 'movie'),
            params.get('tmdb_id', '')
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
    elif mode == 'clear_source_cache':
        clear_source_cache()
    elif mode == 'test_scrapers':
        test_scrapers()
    elif mode == 'addon_settings':
        addon_settings()
    # Favorites modes
    elif mode == 'favorites_menu':
        favorites_menu()
    elif mode == 'favorites_list':
        favorites_list(params.get('media_type', 'movie'))
    elif mode == 'add_favorite':
        add_favorite(
            params.get('media_type', 'movie'),
            params.get('title', ''),
            params.get('year', ''),
            params.get('tmdb_id', ''),
            params.get('poster', ''),
            params.get('fanart', ''),
            params.get('overview', ''),
            float(params.get('rating', 0))
        )
    elif mode == 'remove_favorite':
        remove_favorite(params.get('media_type', 'movie'), params.get('title', ''), params.get('year', ''))
    # Quality Presets
    elif mode == 'quality_presets_menu':
        quality_presets_menu()
    elif mode == 'create_quality_preset':
        create_quality_preset()
    elif mode == 'apply_quality_preset':
        apply_quality_preset(params.get('name', ''))
    elif mode == 'delete_quality_preset':
        delete_quality_preset(params.get('name', ''))
    # Scraper Priority
    elif mode == 'scraper_priority_menu':
        scraper_priority_menu()
    elif mode == 'set_scraper_priority':
        set_scraper_priority(params.get('scraper', ''), int(params.get('priority', 100)))
    elif mode == 'set_scraper_priority_manual':
        set_scraper_priority_manual(params.get('scraper', ''))
    # Watch History
    elif mode == 'watch_history_menu':
        watch_history_menu()
    elif mode == 'watch_history_list':
        watch_history_list(params.get('media_type', 'movie'))
    elif mode == 'clear_watch_history':
        clear_watch_history()
    # Subtitles
    elif mode == 'subtitle_search_dialog':
        title = xbmcgui.Dialog().input('Movie/Show title')
        if title:
            subtitle_search(title=title)
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
