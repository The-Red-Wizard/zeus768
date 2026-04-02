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
import random
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

# TMDB API config
TMDB_BASE = 'https://api.themoviedb.org/3'
TMDB_KEY = '8265bd1679663a7ea12ac168da84d2e8'
TMDB_IMG = 'https://image.tmdb.org/t/p'

def _tmdb_get(path, params=None):
    """Helper: GET from TMDB API, returns parsed JSON or None"""
    url = f'{TMDB_BASE}{path}'
    p = {'api_key': TMDB_KEY}
    if params:
        p.update(params)
    query = '&'.join(f'{k}={quote_plus(str(v))}' for k, v in p.items())
    full_url = f'{url}?{query}'
    try:
        req = Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urlopen(req, timeout=15)
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        log_utils.log(f'TMDB API error: {e}', xbmc.LOGERROR)
        return None

def build_url(query):
    return sys.argv[0] + '?' + urlencode(query)

def show_kofi_qr():
    """Show Ko-fi QR code dialog for donations"""
    import ssl
    kofi_url = 'https://ko-fi.com/zeus768'
    qr_api = f'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={quote_plus(kofi_url)}'
    temp_path = xbmcvfs.translatePath('special://temp/')
    qr_file = os.path.join(temp_path, 'kofi_qr.png')
    
    try:
        ctx = ssl._create_unverified_context()
        req = Request(qr_api, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, context=ctx, timeout=15) as resp:
            with open(qr_file, 'wb') as f:
                f.write(resp.read())
    except Exception:
        xbmcgui.Dialog().ok(
            'Buy Me a Beer',
            '[COLOR orange]Thanks for the support![/COLOR]\n\n'
            'Visit: [COLOR cyan]https://ko-fi.com/zeus768[/COLOR]\n\n'
            'Every beer keeps the addons alive!'
        )
        return
    
    if os.path.exists(qr_file):
        # Use WindowDialog to show QR image
        dialog = KofiQRDialog(qr_file, kofi_url)
        dialog.doModal()
        del dialog
    else:
        xbmcgui.Dialog().ok(
            'Buy Me a Beer',
            '[COLOR orange]Thanks for the support![/COLOR]\n\n'
            'Visit: [COLOR cyan]https://ko-fi.com/zeus768[/COLOR]'
        )

class KofiQRDialog(xbmcgui.WindowDialog):
    def __init__(self, qr_path, url):
        super().__init__()
        w, h = 1280, 720
        dw, dh = 600, 520
        dx, dy = (w - dw) // 2, (h - dh) // 2
        
        self.addControl(xbmcgui.ControlImage(dx, dy, dw, dh, 'special://xbmc/addons/skin.estuary/media/dialogs/dialog-bg.png'))
        self.addControl(xbmcgui.ControlLabel(dx, dy + 20, dw, 40, '[B][COLOR orange]Buy Me a Beer![/COLOR][/B]', alignment=2))
        qr_sz = 280
        self.addControl(xbmcgui.ControlImage(dx + (dw - qr_sz) // 2, dy + 70, qr_sz, qr_sz, qr_path))
        self.addControl(xbmcgui.ControlLabel(dx + 20, dy + 365, dw - 40, 30, f'[COLOR cyan]{url}[/COLOR]', alignment=2))
        self.addControl(xbmcgui.ControlLabel(dx + 20, dy + 400, dw - 40, 30, 'Scan QR code or visit the link above', alignment=2))
        self.addControl(xbmcgui.ControlLabel(dx + 20, dy + 435, dw - 40, 30, '[COLOR orange]Every beer keeps the addons alive![/COLOR]', alignment=2))
        self.addControl(xbmcgui.ControlLabel(dx + 20, dy + dh - 40, dw - 40, 30, '[COLOR gray]Press BACK to close[/COLOR]', alignment=2))
    
    def onAction(self, action):
        if action.getId() in [9, 10, 92, 7]:
            self.close()

def get_params():
    return dict(parse_qsl(sys.argv[2][1:]))

def main_menu():
    """Main menu of the addon"""
    items = [
        {'title': '[B]Movies[/B]', 'mode': 'movies_menu'},
        {'title': '[B]TV Shows[/B]', 'mode': 'tvshows_menu'},
        {'title': '[B]24/7 Channels[/B]', 'mode': 'channel_menu'},
        {'title': '[B]Favorites[/B]', 'mode': 'favorites_menu'},
        {'title': '[B]Search[/B]', 'mode': 'search_menu'},
        {'title': '[COLOR magenta][B]AI Search[/B][/COLOR]', 'mode': 'ai_search_menu'},
        {'title': '[B]Trakt[/B]', 'mode': 'trakt_menu'},
        {'title': 'Scrapers', 'mode': 'scrapers_menu'},
        {'title': 'Debrid Services', 'mode': 'debrid_menu'},
        {'title': 'Tools', 'mode': 'tools_menu'},
        {'title': 'Settings', 'mode': 'addon_settings'},
        {'title': '[COLOR orange]Buy Me a Beer[/COLOR]', 'mode': 'buy_beer'},
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
        {'title': '[B]Franchises[/B]', 'mode': 'franchises_menu'},
        {'title': '[B]Actors[/B]', 'mode': 'actors_menu'},
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

def ai_search_menu():
    """AI Search sub-menu"""
    items = [
        {'title': '[COLOR magenta][B]AI Search Movies[/B][/COLOR]', 'mode': 'ai_search', 'media_filter': 'movie'},
        {'title': '[COLOR magenta][B]AI Search TV Shows[/B][/COLOR]', 'mode': 'ai_search', 'media_filter': 'tv'},
        {'title': '[COLOR magenta][B]AI Search All[/B][/COLOR]', 'mode': 'ai_search', 'media_filter': 'all'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def ai_search(media_filter='all'):
    """AI-powered natural language search"""
    from salts_lib import ai_search as ai_mod
    
    if ADDON.getSetting('ai_search_enabled') != 'true':
        xbmcgui.Dialog().ok('AI Search', 'AI Search is disabled.\n\nEnable it in Settings > AI Search.')
        return
    
    if not ADDON.getSetting('ai_api_key'):
        xbmcgui.Dialog().ok('AI Search', 'No API key configured.\n\nGo to Settings > AI Search to add your OpenAI key.')
        return
    
    keyboard = xbmc.Keyboard('', 'Describe what you want to watch...')
    keyboard.doModal()
    
    if not keyboard.isConfirmed():
        return
    
    query = keyboard.getText().strip()
    if not query:
        return
    
    # Show progress
    progress = xbmcgui.DialogProgress()
    progress.create('AI Search', f'Asking AI about: {query[:50]}...')
    progress.update(20, f'Searching with AI...')
    
    results = ai_mod.ai_search(query, media_filter)
    
    if progress.iscanceled():
        progress.close()
        return
    
    if not results:
        progress.close()
        xbmcgui.Dialog().notification('AI Search', 'No results. Try a different description.', ADDON_ICON)
        return
    
    progress.update(60, f'Found {len(results)} recommendations. Looking up on TMDB...')
    
    # Look up each result on TMDB to get posters and metadata
    tmdb_results = []
    for i, rec in enumerate(results):
        if progress.iscanceled():
            progress.close()
            return
        
        progress.update(60 + int(30 * i / len(results)), f'Looking up: {rec.get("title", "")}')
        
        title = rec.get('title', '')
        year = rec.get('year', '')
        rec_type = rec.get('type', 'movie')
        reason = rec.get('reason', '')
        
        # Search TMDB
        search_type = 'movie' if rec_type == 'movie' else 'tv'
        tmdb_data = _tmdb_get(f'/search/{search_type}', {
            'query': title,
            'year': str(year) if year and search_type == 'movie' else '',
            'first_air_date_year': str(year) if year and search_type == 'tv' else ''
        })
        
        if tmdb_data and tmdb_data.get('results'):
            tmdb_item = tmdb_data['results'][0]
            tmdb_results.append({
                'tmdb': tmdb_item,
                'type': rec_type,
                'reason': reason,
                'ai_title': title,
                'ai_year': year
            })
        else:
            # No TMDB match — still show it without poster
            tmdb_results.append({
                'tmdb': {'title': title, 'name': title, 'id': None, 'overview': reason,
                         'vote_average': 0, 'poster_path': '', 'backdrop_path': ''},
                'type': rec_type,
                'reason': reason,
                'ai_title': title,
                'ai_year': year
            })
    
    progress.close()
    
    # Display results
    for item in tmdb_results:
        tmdb = item['tmdb']
        rec_type = item['type']
        reason = item['reason']
        
        if rec_type == 'movie':
            title = tmdb.get('title', item['ai_title'])
            yr = str(tmdb.get('release_date', ''))[:4] or str(item['ai_year'])
        else:
            title = tmdb.get('name', item['ai_title'])
            yr = str(tmdb.get('first_air_date', ''))[:4] or str(item['ai_year'])
        
        poster = tmdb.get('poster_path', '')
        backdrop = tmdb.get('backdrop_path', '')
        overview = tmdb.get('overview', reason)
        rating = tmdb.get('vote_average', 0)
        tmdb_id = tmdb.get('id')
        
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        # Label with AI reason
        label = f'{title} ({yr})'
        if reason:
            label += f'  [COLOR FF9966CC]{reason}[/COLOR]'
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url, 'fanart': backdrop_url})
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setYear(int(yr) if yr else 0)
        info_tag.setPlot(f'{reason}\n\n{overview}' if reason else overview)
        info_tag.setRating(float(rating) if rating else 0)
        info_tag.setMediaType('movie' if rec_type == 'movie' else 'tvshow')
        
        if tmdb_id:
            if rec_type == 'movie':
                item_url = build_url({
                    'mode': 'get_sources', 'title': title, 'year': yr,
                    'media_type': 'movie', 'tmdb_id': tmdb_id
                })
                is_folder = False
            else:
                item_url = build_url({
                    'mode': 'tv_seasons', 'title': title, 'year': yr,
                    'tmdb_id': tmdb_id
                })
                is_folder = True
        else:
            item_url = build_url({
                'mode': 'get_sources', 'title': title, 'year': yr,
                'media_type': 'movie', 'tmdb_id': ''
            })
            is_folder = False
        
        xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=is_folder)
    
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE)

def tmdb_list(list_type, media_type='movie', page=1):
    """Get list from TMDB API (free, no key needed for basic lists)"""
    
    # TMDB API (v3)
    base_url = 'https://api.themoviedb.org/3'
    
    # Free API key for demo purposes
    api_key = '8265bd1679663a7ea12ac168da84d2e8'
    
    try:
        if media_type == 'movie':
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
        
        # Fetch Trakt ratings for browse page (cached 24hr)
        trakt_ratings = {}
        try:
            from salts_lib.trakt_api import TraktAPI
            trakt = TraktAPI()
            mt = 'movie' if media_type == 'movie' else 'show'
            tmdb_ids = [str(i.get('id', '')) for i in results if i.get('id')]
            trakt_ratings = trakt.get_batch_ratings(mt, tmdb_ids)
        except Exception:
            pass
        
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
            trakt_r = trakt_ratings.get(str(item.get('id', '')))
            if trakt_r:
                label += f'  [COLOR FFE8B800]Trakt: {trakt_r[0]}[/COLOR]'
            
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
            _fav_url = build_url({
                'mode': 'add_favorite', 'media_type': media_type if media_type == 'movie' else 'tvshow',
                'title': title, 'year': year, 'tmdb_id': str(item.get('id', '')),
                'poster': poster_url, 'overview': overview[:200], 'rating': str(rating)
            })
            li.addContextMenuItems([('Add to Favorites', f'RunPlugin({_fav_url})')])
            
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
            
            is_folder = media_type != 'movie' # isFolder is False for movies
            xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=is_folder)
        
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
        
        # Fetch Trakt ratings for search results (cached 24hr)
        trakt_ratings_s = {}
        try:
            from salts_lib.trakt_api import TraktAPI
            trakt_s = TraktAPI()
            mt_s = 'movie' if media_type == 'movie' else 'show'
            tmdb_ids_s = [str(i.get('id', '')) for i in results if i.get('id')]
            trakt_ratings_s = trakt_s.get_batch_ratings(mt_s, tmdb_ids_s)
        except Exception:
            pass
        
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
            trakt_r_s = trakt_ratings_s.get(str(item.get('id', '')))
            if trakt_r_s:
                label += f'  [COLOR FFE8B800]Trakt: {trakt_r_s[0]}[/COLOR]'
            
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
                
                xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=False) # isFolder set to False for select dialog use
            
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
    
    # Check if at least one Debrid service is enabled
    debrid_enabled = (
        ADDON.getSetting('realdebrid_enabled') == 'true' or
        ADDON.getSetting('premiumize_enabled') == 'true' or
        ADDON.getSetting('alldebrid_enabled') == 'true' or
        ADDON.getSetting('torbox_enabled') == 'true'
    )
    
    if not debrid_enabled:
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            'No Debrid service enabled - Free streams only',
            ADDON_ICON,
            5000
        )
    
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
    
    # Check hover/pre-scrape cache (24hr TTL, no prompt)
    hover_key = f'hover|{cache_key}'
    hover_sources = db.get_hover_cache(hover_key)
    if hover_sources:
        log_utils.log(f'Hover cache hit for {cache_key}: {len(hover_sources)} pre-scraped sources', xbmc.LOGINFO)
        xbmcgui.Dialog().notification(ADDON_NAME, f'Instant! {len(hover_sources)} pre-scraped sources', ADDON_ICON, 2000)
        all_sources = hover_sources
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
            
            # Skip torrent scrapers if no Debrid service is enabled
            is_free_scraper = isinstance(scraper, FreeStreamScraper)
            if not debrid_enabled and not is_free_scraper:
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
    
    # Batch cache check: mark torrent sources as cached/uncached
    if debrid_enabled:
        torrent_sources = [s for s in all_sources if s.get('magnet') and not s.get('direct')]
        hashes = {}
        for s in torrent_sources:
            magnet = s.get('magnet', '')
            h = None
            import re as _re
            m = _re.search(r'btih:([a-fA-F0-9]{40})', magnet)
            if m:
                h = m.group(1).lower()
            else:
                m = _re.search(r'btih:([a-zA-Z2-7]{32})', magnet)
                if m:
                    h = m.group(1).lower()
            if h:
                hashes[id(s)] = h
        
        if hashes:
            unique_hashes = list(set(hashes.values()))
            try:
                from salts_lib.debrid import check_cache_batch
                cache_results = check_cache_batch(unique_hashes)
                
                for s in torrent_sources:
                    h = hashes.get(id(s))
                    if h and cache_results.get(h, False):
                        s['cached'] = True
            except Exception as e:
                log_utils.log(f'Batch cache check error: {e}', xbmc.LOGDEBUG)
    
    # Cache the results
    if use_cache:
        db.cache_sources(cache_key, all_sources)
    
    _display_or_autoplay_sources(all_sources, search_title, media_type,
                                 title, year, season, episode, tmdb_id)


def _display_or_autoplay_sources(all_sources, search_title, media_type,
                                  title, year, season, episode, tmdb_id):
    """Sort, display source dialog or autoplay"""
    # Sort: cached first, then free streams, then by quality and seeds
    def sort_key(x):
        is_cached = 1 if x.get('cached') else 0
        is_free = 1 if x.get('direct') else 0
        quality = QUALITY_ORDER.get(x.get('quality', 'SD'), 0)
        seeds = x.get('seeds', 0)
        return (is_cached, is_free, quality, seeds)
    
    all_sources.sort(key=sort_key, reverse=True)
    
    # Fetch Trakt rating for the item
    trakt_rating_str = ''
    try:
        from salts_lib.trakt_api import TraktAPI
        trakt = TraktAPI()
        mt = 'movie' if media_type == 'movie' else 'show'
        rating, votes = trakt.get_item_rating(mt, tmdb_id)
        if rating is not None:
            trakt_rating_str = f'  Trakt: {rating}/10 ({votes})'
    except Exception:
        pass
    
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
    cached_count = sum(1 for s in all_sources if s.get('cached'))
    
    # Quality color map
    _QCOLORS = {
        '4K': 'FFD4AF37', '2160p': 'FFD4AF37', '1080p': 'FF00CC66',
        'HD': 'FF00CC66', '720p': 'FF4499DD', '480p': 'FF9977CC', 'SD': 'FF999999'
    }
    
    # Quality summary for header
    _qcounts = {}
    for _s in all_sources:
        _q = _s.get('quality', 'SD')
        _qcounts[_q] = _qcounts.get(_q, 0) + 1
    _qstr = '  '.join(f'{q}:{c}' for q in ['4K','2160p','1080p','HD','720p','480p','SD'] if (c := _qcounts.get(q)))
    
    header = f'SALTS: {sources_found} sources | {cached_count} cached | {free_count} free  [{_qstr}]{trakt_rating_str}'
    
    # Build display list with color-coded formatting
    display_list = []
    for source in all_sources:
        quality = source.get('quality', 'SD')
        scraper = source.get('scraper', '?')
        seeds = source.get('seeds', 0)
        size = source.get('size', '')
        is_cached = source.get('cached', False)
        is_free = source.get('direct', False)
        
        qc = _QCOLORS.get(quality, 'FF999999')
        parts = [f'[COLOR {qc}][B]{quality}[/B][/COLOR]']
        
        if is_cached:
            parts.append('[COLOR FF00FF7F][B]CACHED[/B][/COLOR]')
        elif is_free:
            parts.append('[COLOR FFFFA500][B]FREE[/B][/COLOR]')
        
        parts.append(f'[COLOR FFCCDDEE]{scraper}[/COLOR]')
        
        if seeds and not is_free:
            sc = 'FF00EE00' if seeds >= 100 else ('FFCCCC00' if seeds >= 10 else 'FFEE6600')
            parts.append(f'[COLOR {sc}]S:{seeds}[/COLOR]')
        
        if size:
            parts.append(f'[COLOR FF8899BB]{size}[/COLOR]')
        
        display_list.append('  |  '.join(parts))
    
    selected = xbmcgui.Dialog().select(header, display_list)
    
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
        
        # Check TorBox
        if not stream_url and ADDON.getSetting('torbox_enabled') == 'true':
            tb = debrid.TorBox()
            if tb.is_authorized():
                progress = xbmcgui.DialogProgress()
                progress.create('SALTS', 'Resolving with TorBox...')
                stream_url = tb.resolve_magnet(magnet)
                progress.close()
                if stream_url:
                    log_utils.log(f'Resolved via TorBox: {stream_url}', xbmc.LOGINFO)
        
        # No debrid - show message
        if not stream_url:
            xbmcgui.Dialog().ok(ADDON_NAME, 'Torrent sources require a debrid service.\n\nPlease configure Real-Debrid, Premiumize, AllDebrid, or TorBox in settings.')
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
    
    # Monitor playback for skip intro and next episode
    _monitor_playback(player, media_type, show_title, year, season, episode)


def _monitor_playback(player, media_type, show_title, year, season, episode):
    """Monitor playback for skip intro, next episode, and pre-emptive scraping"""
    skip_intro_shown = False
    next_ep_shown = False
    preemptive_done = False
    skip_intro_seconds = int(ADDON.getSetting('skip_intro_duration') or 90)
    next_ep_enabled = ADDON.getSetting('next_episode_enabled') == 'true'
    skip_intro_enabled = ADDON.getSetting('skip_intro_enabled') == 'true'
    preemptive_enabled = ADDON.getSetting('preemptive_scrape') == 'true'
    
    total_time = 0
    preemptive_sources = None
    
    while player.isPlaying():
        try:
            current_time = player.getTime()
            if total_time == 0:
                try:
                    total_time = player.getTotalTime()
                except Exception:
                    pass
            
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
                progress_pct = (current_time / total_time) * 100
                if progress_pct > 75:
                    preemptive_done = True
                    next_ep = int(episode) + 1
                    log_utils.log(f'Pre-emptive scrape: {show_title} S{int(season):02d}E{next_ep:02d}', xbmc.LOGINFO)
                    # Pre-scrape next episode sources in background (cache only)
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
                        player.stop()
                        xbmc.sleep(500)
                        get_sources(show_title, year, season, str(next_ep), 'tvshow')
                        return
            
        except Exception as e:
            log_utils.log(f'Playback monitor: {e}', xbmc.LOGDEBUG)
            break
        
        xbmc.sleep(2000)


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
        {'title': 'TorBox', 'mode': 'debrid_auth', 'service': 'torbox'},
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
    elif service == 'torbox':
        tb = debrid.TorBox()
        tb.authorize()
    xbmc.executebuiltin('Container.Refresh')

def tools_menu():
    """Tools menu"""
    items = [
        {'title': 'Clear Cache', 'mode': 'clear_cache'},
        {'title': 'Clear Source Cache', 'mode': 'clear_source_cache'},
        {'title': 'Clear Pre-Scrape Cache', 'mode': 'clear_hover_cache'},
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

def clear_hover_cache():
    """Clear pre-scrape / hover cache"""
    db = db_utils.DB_Connection()
    db.clear_hover_cache()
    xbmcgui.Dialog().notification(ADDON_NAME, 'Pre-scrape cache cleared', ADDON_ICON)

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
    from salts_lib.trakt_api import TraktAPI, TraktError, TransientTraktError
    trakt = TraktAPI()
    
    if not trakt.is_authorized():
        xbmcgui.Dialog().notification(ADDON_NAME, 'Please authorize Trakt first', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    try:
        items = trakt.get_watchlist(media_type)
        _show_trakt_items(items, media_type)
    except (TraktError, TransientTraktError) as e:
        log_utils.log(f'Trakt watchlist error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, f'Trakt error: {e}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)

def trakt_collection(media_type='movies'):
    """Show Trakt collection"""
    from salts_lib.trakt_api import TraktAPI, TraktError, TransientTraktError
    trakt = TraktAPI()
    
    if not trakt.is_authorized():
        xbmcgui.Dialog().notification(ADDON_NAME, 'Please authorize Trakt first', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    try:
        items = trakt.get_collection(media_type)
        _show_trakt_items(items, media_type)
    except (TraktError, TransientTraktError) as e:
        log_utils.log(f'Trakt collection error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, f'Trakt error: {e}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)

def trakt_trending(media_type='movies'):
    """Show trending on Trakt"""
    from salts_lib.trakt_api import TraktAPI, TraktError, TransientTraktError
    trakt = TraktAPI()
    
    try:
        items = trakt.get_trending(media_type)
        _show_trakt_items(items, media_type, key='movie' if media_type == 'movies' else 'show')
    except (TraktError, TransientTraktError) as e:
        log_utils.log(f'Trakt trending error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, f'Trakt error: {e}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)

def trakt_popular(media_type='movies'):
    """Show popular on Trakt"""
    from salts_lib.trakt_api import TraktAPI, TraktError, TransientTraktError
    trakt = TraktAPI()
    
    try:
        items = trakt.get_popular(media_type)
        _show_trakt_items(items, media_type)
    except (TraktError, TransientTraktError) as e:
        log_utils.log(f'Trakt popular error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, f'Trakt error: {e}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)

def trakt_lists():
    """Show user's Trakt lists"""
    from salts_lib.trakt_api import TraktAPI, TraktError, TransientTraktError
    trakt = TraktAPI()
    
    if not trakt.is_authorized():
        xbmcgui.Dialog().notification(ADDON_NAME, 'Please authorize Trakt first', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    try:
        lists = trakt.get_lists()
    except (TraktError, TransientTraktError) as e:
        log_utils.log(f'Trakt lists error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, f'Trakt error: {e}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
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
    from salts_lib.trakt_api import TraktAPI, TraktError, TransientTraktError
    trakt = TraktAPI()
    
    try:
        items = trakt.get_list(list_id)
    except (TraktError, TransientTraktError) as e:
        log_utils.log(f'Trakt list error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, f'Trakt error: {e}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    if not items:
        xbmcgui.Dialog().notification(ADDON_NAME, 'List is empty', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for item in items:
        item_type = item.get('type', 'movie')
        data = item.get(item_type, {})
        
        title = data.get('title', 'Unknown')
        year = data.get('year', '')
        ids = data.get('ids', {})
        tmdb_id = str(ids.get('tmdb', '')) if ids else ''
        
        label = f'{title} ({year})' if year else title
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        if item_type == 'movie':
            url = build_url({
                'mode': 'get_sources',
                'title': title,
                'year': str(year),
                'media_type': 'movie',
                'tmdb_id': tmdb_id
            })
        else:
            url = build_url({
                'mode': 'tv_seasons',
                'title': title,
                'year': str(year),
                'tmdb_id': tmdb_id
            })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def _show_trakt_items(items, media_type, key=None):
    """Helper to display Trakt items.
    
    Handles all Trakt response formats:
    - Trending: [{movie: {...}, watchers: N}, ...]
    - Popular: [{title, year, ids, ...}, ...]  (flat movie/show objects)
    - Watchlist/Collection: [{movie: {...}, listed_at: ...}, ...]
    - Lists: [{type: 'movie', movie: {...}}, ...]
    """
    if not items:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No items found', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    if not isinstance(items, list):
        log_utils.log(f'Trakt: unexpected response type: {type(items)}', xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(ADDON_NAME, 'Unexpected Trakt response', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    count = 0
    for item in items:
        try:
            if not isinstance(item, dict):
                continue
            
            # Extract the media data object from various response formats
            data = None
            if key and key in item:
                data = item[key]
            elif 'movie' in item:
                data = item['movie']
            elif 'show' in item:
                data = item['show']
            elif 'title' in item:
                data = item
            else:
                continue
            
            if not data or not isinstance(data, dict):
                continue
            
            title = data.get('title', 'Unknown')
            year = data.get('year', '')
            
            label = f'{title} ({year})' if year else title
            
            li = xbmcgui.ListItem(label)
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            
            info_tag = li.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setYear(int(year) if year else 0)
            info_tag.setPlot(data.get('overview', ''))
            
            ids = data.get('ids', {})
            tmdb_id = str(ids.get('tmdb', '')) if ids else ''
            
            if media_type == 'movies':
                url = build_url({
                    'mode': 'get_sources',
                    'title': title,
                    'year': str(year),
                    'media_type': 'movie',
                    'tmdb_id': tmdb_id
                })
            else:
                url = build_url({
                    'mode': 'tv_seasons',
                    'title': title,
                    'year': str(year),
                    'tmdb_id': tmdb_id
                })
            
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
            count += 1
        except Exception as e:
            log_utils.log(f'Trakt item parse error: {e}', xbmc.LOGDEBUG)
            continue
    
    if count == 0:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No valid items found', ADDON_ICON)
    
    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movies' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)


# ==================== FRANCHISES ====================

def franchises_menu():
    """Browse popular movie franchises/collections"""
    franchises = [
        {'name': 'Marvel Cinematic Universe', 'id': 529892},
        {'name': 'Star Wars', 'id': 10},
        {'name': 'Harry Potter', 'id': 1241},
        {'name': 'The Lord of the Rings', 'id': 119},
        {'name': 'Fast & Furious', 'id': 9485},
        {'name': 'James Bond', 'id': 645},
        {'name': 'Batman', 'id': 263},
        {'name': 'Spider-Man', 'id': 531241},
        {'name': 'X-Men', 'id': 748},
        {'name': 'Jurassic Park', 'id': 328},
        {'name': 'Pirates of the Caribbean', 'id': 295},
        {'name': 'Transformers', 'id': 8650},
        {'name': 'Mission: Impossible', 'id': 87359},
        {'name': 'John Wick', 'id': 404609},
        {'name': 'The Hunger Games', 'id': 131635},
        {'name': 'Toy Story', 'id': 10194},
        {'name': 'Shrek', 'id': 2150},
        {'name': 'Indiana Jones', 'id': 84},
        {'name': 'The Matrix', 'id': 2344},
        {'name': 'Despicable Me', 'id': 86066},
        {'name': 'Planet of the Apes', 'id': 173710},
        {'name': 'Alien', 'id': 8091},
        {'name': 'Rocky / Creed', 'id': 1575},
        {'name': 'The Conjuring Universe', 'id': 313086},
        {'name': 'Twilight', 'id': 33514},
        {'name': 'The Godfather', 'id': 230},
        {'name': 'Back to the Future', 'id': 264},
        {'name': 'Die Hard', 'id': 1570},
        {'name': 'Mad Max', 'id': 8945},
        {'name': 'Terminator', 'id': 528},
        {'name': 'DC Extended Universe', 'id': 209131},
        {'name': 'The Avengers', 'id': 86311},
        {'name': 'Iron Man', 'id': 131292},
        {'name': 'Captain America', 'id': 131295},
        {'name': 'Thor', 'id': 131296},
        {'name': 'Guardians of the Galaxy', 'id': 284433},
        {'name': 'The Hobbit', 'id': 121938},
        {'name': 'Predator', 'id': 399},
        {'name': 'The Mummy', 'id': 1733},
        {'name': 'Men in Black', 'id': 86055},
        {'name': 'Rush Hour', 'id': 90863},
        {'name': 'Lethal Weapon', 'id': 945},
        {'name': 'Beverly Hills Cop', 'id': 85943},
        {'name': 'The Expendables', 'id': 126125},
        {'name': 'Ocean\'s', 'id': 304},
        {'name': 'The Hangover', 'id': 86119},
        {'name': 'The Maze Runner', 'id': 295130},
        {'name': 'Divergent', 'id': 283579},
        {'name': 'Ghostbusters', 'id': 2980},
        {'name': 'Scream', 'id': 2602},
        {'name': 'Halloween', 'id': 91361},
        {'name': 'A Nightmare on Elm Street', 'id': 8581},
        {'name': 'Friday the 13th', 'id': 9735},
        {'name': 'Saw', 'id': 656},
        {'name': 'The Purge', 'id': 256322},
        {'name': 'Insidious', 'id': 228446},
        {'name': 'Kung Fu Panda', 'id': 77816},
        {'name': 'How to Train Your Dragon', 'id': 89137},
        {'name': 'Cars', 'id': 87118},
        {'name': 'Ice Age', 'id': 8354},
    ]
    
    li = xbmcgui.ListItem('[B]Search Franchises[/B]')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({'mode': 'search_franchise'})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    for f in franchises:
        # Fetch TMDB collection poster
        coll_data = _tmdb_get(f'/collection/{f["id"]}')
        poster = ''
        backdrop = ''
        if coll_data:
            poster = coll_data.get('poster_path', '')
            backdrop = coll_data.get('backdrop_path', '')
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        li = xbmcgui.ListItem(f['name'])
        li.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url, 'fanart': backdrop_url})
        url = build_url({'mode': 'franchise_movies', 'collection_id': f['id'], 'name': f['name']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def search_franchise():
    """Search for a movie franchise/collection"""
    keyboard = xbmc.Keyboard('', 'Search Franchise')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            _search_franchise_results(query, 1)


def _search_franchise_results(query, page=1):
    """Display franchise search results with pagination"""
    data = _tmdb_get('/search/collection', {'query': query, 'page': page})
    if not data or not data.get('results'):
        xbmcgui.Dialog().notification(ADDON_NAME, 'No franchises found', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for item in data['results']:
        name = item.get('name', 'Unknown')
        coll_id = item.get('id')
        poster = item.get('poster_path', '')
        backdrop = item.get('backdrop_path', '')
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        li = xbmcgui.ListItem(name)
        li.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url, 'fanart': backdrop_url})
        url = build_url({'mode': 'franchise_movies', 'collection_id': coll_id, 'name': name})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    if data.get('page', 1) < data.get('total_pages', 1):
        li = xbmcgui.ListItem('[B]>> Next Page[/B]')
        li.setArt({'icon': ADDON_ICON})
        url = build_url({'mode': 'search_franchise_page', 'query': query, 'page': page + 1})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def franchise_movies(collection_id, name=''):
    """Show all movies in a franchise/collection"""
    data = _tmdb_get(f'/collection/{collection_id}')
    if not data:
        xbmcgui.Dialog().notification(ADDON_NAME, 'Failed to load franchise', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    parts = data.get('parts', [])
    parts.sort(key=lambda x: x.get('release_date', '') or '9999')
    
    for movie in parts:
        title = movie.get('title', 'Unknown')
        year = (movie.get('release_date') or '')[:4]
        tmdb_id = movie.get('id', '')
        poster = movie.get('poster_path', '')
        backdrop = movie.get('backdrop_path', '')
        overview = movie.get('overview', '')
        rating = movie.get('vote_average', 0)
        
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        label = f'{title} ({year})' if year else title
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url, 'fanart': backdrop_url})
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setYear(int(year) if year else 0)
        info_tag.setPlot(overview)
        info_tag.setRating(rating)
        info_tag.setMediaType('movie')
        
        url = build_url({
            'mode': 'get_sources', 'title': title, 'year': year,
            'media_type': 'movie', 'tmdb_id': tmdb_id
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE)


# ==================== ACTORS ====================

def actors_menu():
    """Browse popular actors"""
    items = [
        {'title': '[B]Search Actors[/B]', 'mode': 'search_actor'},
        {'title': 'Popular Actors', 'mode': 'popular_actors', 'page': '1'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def popular_actors(page=1):
    """Show popular actors with unlimited pagination"""
    data = _tmdb_get('/person/popular', {'page': page})
    if not data or not data.get('results'):
        xbmcgui.Dialog().notification(ADDON_NAME, 'No actors found', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for person in data['results']:
        name = person.get('name', 'Unknown')
        person_id = person.get('id')
        profile = person.get('profile_path', '')
        
        profile_url = f'{TMDB_IMG}/w500{profile}' if profile else ADDON_ICON
        
        kf_titles = []
        for kf in person.get('known_for', [])[:3]:
            kf_titles.append(kf.get('title') or kf.get('name', ''))
        kf_str = ', '.join(t for t in kf_titles if t)
        
        label = f'{name} - {kf_str}' if kf_str else name
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': profile_url, 'thumb': profile_url, 'poster': profile_url, 'fanart': ADDON_FANART})
        
        url = build_url({'mode': 'actor_movies', 'person_id': person_id, 'name': name})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    if data.get('page', 1) < data.get('total_pages', 1):
        li = xbmcgui.ListItem('[B]>> Next Page[/B]')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': 'popular_actors', 'page': page + 1})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def search_actor():
    """Search for an actor"""
    keyboard = xbmc.Keyboard('', 'Search Actor')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            data = _tmdb_get('/search/person', {'query': query})
            if not data or not data.get('results'):
                xbmcgui.Dialog().notification(ADDON_NAME, 'No actors found', ADDON_ICON)
                xbmcplugin.endOfDirectory(HANDLE)
                return
            
            for person in data['results']:
                name = person.get('name', 'Unknown')
                person_id = person.get('id')
                profile = person.get('profile_path', '')
                profile_url = f'{TMDB_IMG}/w500{profile}' if profile else ADDON_ICON
                
                li = xbmcgui.ListItem(name)
                li.setArt({'icon': profile_url, 'thumb': profile_url, 'poster': profile_url})
                url = build_url({'mode': 'actor_movies', 'person_id': person_id, 'name': name})
                xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
            
            xbmcplugin.endOfDirectory(HANDLE)


def actor_movies(person_id, name='', page=1):
    """Show an actor's filmography with pagination"""
    data = _tmdb_get(f'/person/{person_id}/movie_credits')
    if not data:
        xbmcgui.Dialog().notification(ADDON_NAME, 'Failed to load filmography', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    cast = data.get('cast', [])
    cast.sort(key=lambda x: x.get('popularity', 0), reverse=True)
    
    per_page = 20
    start = (page - 1) * per_page
    end = start + per_page
    page_items = cast[start:end]
    
    if not page_items:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No more movies', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for movie in page_items:
        title = movie.get('title', 'Unknown')
        year = (movie.get('release_date') or '')[:4]
        tmdb_id = movie.get('id', '')
        poster = movie.get('poster_path', '')
        character = movie.get('character', '')
        overview = movie.get('overview', '')
        rating = movie.get('vote_average', 0)
        
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        
        label = f'{title} ({year})' if year else title
        if character:
            label = f'{label} - as {character}'
        
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url, 'fanart': ADDON_FANART})
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setYear(int(year) if year else 0)
        info_tag.setPlot(overview)
        info_tag.setRating(rating)
        info_tag.setMediaType('movie')
        
        url = build_url({
            'mode': 'get_sources', 'title': title, 'year': year,
            'media_type': 'movie', 'tmdb_id': tmdb_id
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    if end < len(cast):
        li = xbmcgui.ListItem(f'[B]>> Next Page ({page + 1})[/B]')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': 'actor_movies', 'person_id': person_id, 'name': name, 'page': page + 1})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE)


# ==================== 24/7 CHANNELS ====================

def channel_menu():
    """24/7 Channels menu"""
    items = [
        {'title': '[B]24/7 Movies[/B] - Pick an actor, random marathon', 'mode': 'channel_movies_menu'},
        {'title': '[B]24/7 TV Shows[/B] - Pick a show, random start', 'mode': 'channel_shows_menu'},
        {'title': '[B]24/7 Genre[/B] - Pick a genre, endless movies', 'mode': 'channel_genre_menu'},
        {'title': '[COLOR magenta][B]24/7 AI Vibe[/B][/COLOR] - Describe a mood, AI builds your marathon', 'mode': 'channel_ai_vibe'},
    ]
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': item['mode']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def channel_movies_menu():
    """24/7 Movies: pick an actor for random movie marathon"""
    actors = [
        {'name': 'Adam Sandler', 'id': 19292},
        {'name': 'Tom Hanks', 'id': 31},
        {'name': 'Leonardo DiCaprio', 'id': 6193},
        {'name': 'Denzel Washington', 'id': 5292},
        {'name': 'Morgan Freeman', 'id': 192},
        {'name': 'Keanu Reeves', 'id': 6384},
        {'name': 'Dwayne Johnson', 'id': 18918},
        {'name': 'Will Smith', 'id': 2888},
        {'name': 'Robert Downey Jr.', 'id': 3223},
        {'name': 'Scarlett Johansson', 'id': 1245},
        {'name': 'Brad Pitt', 'id': 287},
        {'name': 'Margot Robbie', 'id': 234352},
        {'name': 'Samuel L. Jackson', 'id': 2231},
        {'name': 'Jason Statham', 'id': 976},
        {'name': 'Liam Neeson', 'id': 3896},
        {'name': 'Nicolas Cage', 'id': 2963},
        {'name': 'Ryan Reynolds', 'id': 10859},
        {'name': 'Matt Damon', 'id': 1892},
        {'name': 'Chris Pratt', 'id': 73457},
        {'name': 'Eddie Murphy', 'id': 776},
        {'name': 'Tom Cruise', 'id': 500},
        {'name': 'Angelina Jolie', 'id': 11701},
        {'name': 'Jennifer Lawrence', 'id': 72129},
        {'name': 'Chris Hemsworth', 'id': 74568},
        {'name': 'Vin Diesel', 'id': 12835},
        {'name': 'Harrison Ford', 'id': 3},
        {'name': 'Al Pacino', 'id': 1158},
        {'name': 'Robert De Niro', 'id': 380},
        {'name': 'Mark Wahlberg', 'id': 13240},
        {'name': 'Bruce Willis', 'id': 62},
        {'name': 'Arnold Schwarzenegger', 'id': 1100},
        {'name': 'Sylvester Stallone', 'id': 16483},
        {'name': 'Jackie Chan', 'id': 18897},
        {'name': 'Jason Momoa', 'id': 117642},
        {'name': 'Idris Elba', 'id': 17605},
        {'name': 'Sandra Bullock', 'id': 18277},
        {'name': 'Melissa McCarthy', 'id': 59410},
        {'name': 'Kevin Hart', 'id': 55638},
        {'name': 'Zendaya', 'id': 505710},
        {'name': 'Timothee Chalamet', 'id': 1190668},
    ]
    
    li = xbmcgui.ListItem('[B]Search Actor for 24/7[/B]')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({'mode': 'channel_search_actor'})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    for actor in actors:
        # Fetch TMDB profile photo
        person_data = _tmdb_get(f'/person/{actor["id"]}')
        profile = ''
        if person_data:
            profile = person_data.get('profile_path', '')
        profile_url = f'{TMDB_IMG}/w500{profile}' if profile else ADDON_ICON
        
        li = xbmcgui.ListItem(f'24/7 {actor["name"]}')
        li.setArt({'icon': profile_url, 'thumb': profile_url, 'poster': profile_url, 'fanart': ADDON_FANART})
        url = build_url({'mode': 'channel_play_actor', 'person_id': actor['id'], 'name': actor['name']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def channel_search_actor():
    """Search for an actor to start 24/7 channel"""
    keyboard = xbmc.Keyboard('', 'Search Actor for 24/7 Channel')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            data = _tmdb_get('/search/person', {'query': query})
            if not data or not data.get('results'):
                xbmcgui.Dialog().notification(ADDON_NAME, 'No actors found', ADDON_ICON)
                xbmcplugin.endOfDirectory(HANDLE)
                return
            
            for person in data['results']:
                name = person.get('name', 'Unknown')
                person_id = person.get('id')
                profile = person.get('profile_path', '')
                profile_url = f'{TMDB_IMG}/w500{profile}' if profile else ADDON_ICON
                
                li = xbmcgui.ListItem(f'24/7 {name}')
                li.setArt({'icon': profile_url, 'thumb': profile_url, 'poster': profile_url})
                url = build_url({'mode': 'channel_play_actor', 'person_id': person_id, 'name': name})
                xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
            
            xbmcplugin.endOfDirectory(HANDLE)


def channel_play_actor(person_id, name=''):
    """Start 24/7 actor channel: random movies back to back, max 1080p"""
    data = _tmdb_get(f'/person/{person_id}/movie_credits')
    if not data or not data.get('cast'):
        xbmcgui.Dialog().notification(ADDON_NAME, f'No movies found for {name}', ADDON_ICON)
        return
    
    movies = [m for m in data.get('cast', []) if m.get('release_date')]
    
    if not movies:
        xbmcgui.Dialog().notification(ADDON_NAME, f'No movies found for {name}', ADDON_ICON)
        return
    
    random.shuffle(movies)
    
    xbmcgui.Dialog().notification(ADDON_NAME, f'24/7 {name}: {len(movies)} movies shuffled', ADDON_ICON, 3000)
    
    player = xbmc.Player()
    
    for movie in movies:
        title = movie.get('title', 'Unknown')
        year = (movie.get('release_date') or '')[:4]
        tmdb_id = movie.get('id', '')
        
        log_utils.log(f'24/7 Channel: Playing {title} ({year})', xbmc.LOGINFO)
        
        stream_url = _channel_get_stream(title, year, tmdb_id, max_quality='1080p')
        
        if not stream_url:
            log_utils.log(f'24/7 Channel: No source for {title}, skipping', xbmc.LOGINFO)
            continue
        
        li = xbmcgui.ListItem(f'{title} ({year})', path=stream_url)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        player.play(stream_url, li)
        
        timeout = 30
        while not player.isPlaying() and timeout > 0:
            xbmc.sleep(500)
            timeout -= 1
        
        if not player.isPlaying():
            continue
        
        while player.isPlaying():
            xbmc.sleep(2000)
        
        xbmc.sleep(1000)
        
        if xbmc.Monitor().abortRequested():
            break
    
    xbmcgui.Dialog().notification(ADDON_NAME, f'24/7 {name}: Marathon complete!', ADDON_ICON)


def channel_shows_menu():
    """24/7 TV Shows: browse popular shows to start random marathon"""
    shows = [
        {'name': 'The Simpsons', 'id': 456},
        {'name': 'Breaking Bad', 'id': 1396},
        {'name': 'The Office (US)', 'id': 2316},
        {'name': 'Friends', 'id': 1668},
        {'name': 'Game of Thrones', 'id': 1399},
        {'name': 'Stranger Things', 'id': 66732},
        {'name': 'South Park', 'id': 2190},
        {'name': 'Family Guy', 'id': 1434},
        {'name': 'The Walking Dead', 'id': 1402},
        {'name': 'Seinfeld', 'id': 1400},
        {'name': 'Rick and Morty', 'id': 60625},
        {'name': 'House of the Dragon', 'id': 94997},
        {'name': 'The Sopranos', 'id': 1398},
        {'name': 'The Wire', 'id': 1438},
        {'name': 'How I Met Your Mother', 'id': 1100},
        {'name': 'Peaky Blinders', 'id': 60574},
        {'name': 'Brooklyn Nine-Nine', 'id': 48891},
        {'name': 'The Big Bang Theory', 'id': 1418},
        {'name': 'Better Call Saul', 'id': 60059},
        {'name': 'Arrested Development', 'id': 4589},
        {'name': 'Lost', 'id': 4607},
        {'name': 'Dexter', 'id': 1405},
        {'name': 'The Mandalorian', 'id': 82856},
        {'name': 'Narcos', 'id': 63351},
        {'name': 'Ozark', 'id': 69740},
        {'name': 'The Boys', 'id': 76479},
        {'name': 'Succession', 'id': 76331},
        {'name': 'Ted Lasso', 'id': 97546},
        {'name': 'Yellowstone', 'id': 73586},
        {'name': 'The Last of Us', 'id': 100088},
        {'name': 'Wednesday', 'id': 119051},
        {'name': 'Squid Game', 'id': 93405},
        {'name': 'Cobra Kai', 'id': 77169},
        {'name': 'The Witcher', 'id': 71912},
        {'name': 'Reacher', 'id': 108978},
        {'name': 'True Detective', 'id': 46648},
        {'name': 'Fargo', 'id': 60622},
        {'name': 'Black Mirror', 'id': 42009},
        {'name': 'Suits', 'id': 37680},
        {'name': 'Prison Break', 'id': 2288},
    ]
    
    li = xbmcgui.ListItem('[B]Search Show for 24/7[/B]')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({'mode': 'channel_search_show'})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    for show in shows:
        # Fetch TMDB show poster
        show_data = _tmdb_get(f'/tv/{show["id"]}')
        poster = ''
        backdrop = ''
        if show_data:
            poster = show_data.get('poster_path', '')
            backdrop = show_data.get('backdrop_path', '')
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        li = xbmcgui.ListItem(f'24/7 {show["name"]}')
        li.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url, 'fanart': backdrop_url})
        url = build_url({'mode': 'channel_play_show', 'tmdb_id': show['id'], 'name': show['name']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def channel_search_show():
    """Search for a show to start 24/7 channel"""
    keyboard = xbmc.Keyboard('', 'Search Show for 24/7 Channel')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            data = _tmdb_get('/search/tv', {'query': query})
            if not data or not data.get('results'):
                xbmcgui.Dialog().notification(ADDON_NAME, 'No shows found', ADDON_ICON)
                xbmcplugin.endOfDirectory(HANDLE)
                return
            
            for show in data['results']:
                name = show.get('name', 'Unknown')
                tmdb_id = show.get('id')
                poster = show.get('poster_path', '')
                poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
                
                li = xbmcgui.ListItem(f'24/7 {name}')
                li.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url})
                url = build_url({'mode': 'channel_play_show', 'tmdb_id': tmdb_id, 'name': name})
                xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
            
            xbmcplugin.endOfDirectory(HANDLE)


def channel_play_show(tmdb_id, name=''):
    """Start 24/7 TV channel: random start, then sequential, back out re-randomizes"""
    show_data = _tmdb_get(f'/tv/{tmdb_id}')
    if not show_data:
        xbmcgui.Dialog().notification(ADDON_NAME, f'Failed to load {name}', ADDON_ICON)
        return
    
    seasons = show_data.get('seasons', [])
    seasons = [s for s in seasons if s.get('season_number', 0) > 0 and s.get('episode_count', 0) > 0]
    
    if not seasons:
        xbmcgui.Dialog().notification(ADDON_NAME, f'No seasons found for {name}', ADDON_ICON)
        return
    
    rand_season = random.choice(seasons)
    season_num = rand_season['season_number']
    
    season_data = _tmdb_get(f'/tv/{tmdb_id}/season/{season_num}')
    if not season_data or not season_data.get('episodes'):
        xbmcgui.Dialog().notification(ADDON_NAME, f'Failed to load season {season_num}', ADDON_ICON)
        return
    
    episodes = season_data.get('episodes', [])
    start_idx = random.randint(0, len(episodes) - 1)
    start_ep = episodes[start_idx]
    
    xbmcgui.Dialog().notification(
        ADDON_NAME,
        f'24/7 {name}: Starting S{season_num:02d}E{start_ep["episode_number"]:02d}',
        ADDON_ICON, 3000
    )
    
    player = xbmc.Player()
    
    # Build episode queue: current position -> end of season -> next seasons in order
    episode_queue = []
    
    for ep in episodes[start_idx:]:
        episode_queue.append((season_num, ep['episode_number']))
    
    for s in seasons:
        sn = s['season_number']
        if sn <= season_num:
            continue
        s_data = _tmdb_get(f'/tv/{tmdb_id}/season/{sn}')
        if s_data and s_data.get('episodes'):
            for ep in s_data['episodes']:
                episode_queue.append((sn, ep['episode_number']))
    
    for (s_num, ep_num) in episode_queue:
        log_utils.log(f'24/7 Channel: Playing {name} S{s_num:02d}E{ep_num:02d}', xbmc.LOGINFO)
        
        stream_url = _channel_get_stream(name, '', tmdb_id, season=str(s_num), episode=str(ep_num), media_type='tvshow')
        
        if not stream_url:
            log_utils.log(f'24/7 Channel: No source for {name} S{s_num:02d}E{ep_num:02d}, skipping', xbmc.LOGINFO)
            continue
        
        li = xbmcgui.ListItem(f'{name} - S{s_num:02d}E{ep_num:02d}', path=stream_url)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        player.play(stream_url, li)
        
        timeout = 30
        while not player.isPlaying() and timeout > 0:
            xbmc.sleep(500)
            timeout -= 1
        
        if not player.isPlaying():
            continue
        
        while player.isPlaying():
            xbmc.sleep(2000)
        
        xbmc.sleep(1000)
        
        if xbmc.Monitor().abortRequested():
            break
    
    xbmcgui.Dialog().notification(ADDON_NAME, f'24/7 {name}: Channel complete!', ADDON_ICON)


def channel_genre_menu():
    """24/7 Genre Channels: pick a genre for random movie marathon"""
    genres = [
        {'name': 'Action', 'id': 28},
        {'name': 'Adventure', 'id': 12},
        {'name': 'Animation', 'id': 16},
        {'name': 'Comedy', 'id': 35},
        {'name': 'Crime', 'id': 80},
        {'name': 'Documentary', 'id': 99},
        {'name': 'Drama', 'id': 18},
        {'name': 'Family', 'id': 10751},
        {'name': 'Fantasy', 'id': 14},
        {'name': 'History', 'id': 36},
        {'name': 'Horror', 'id': 27},
        {'name': 'Music', 'id': 10402},
        {'name': 'Mystery', 'id': 9648},
        {'name': 'Romance', 'id': 10749},
        {'name': 'Science Fiction', 'id': 878},
        {'name': 'Thriller', 'id': 53},
        {'name': 'War', 'id': 10752},
        {'name': 'Western', 'id': 37},
    ]
    
    for genre in genres:
        # Fetch a sample movie poster for this genre
        sample = _tmdb_get('/discover/movie', {
            'with_genres': genre['id'], 'sort_by': 'popularity.desc', 'page': 1
        })
        poster = ''
        backdrop = ''
        if sample and sample.get('results'):
            top = sample['results'][0]
            poster = top.get('poster_path', '')
            backdrop = top.get('backdrop_path', '')
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        li = xbmcgui.ListItem(f'24/7 {genre["name"]}')
        li.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url, 'fanart': backdrop_url})
        url = build_url({'mode': 'channel_play_genre', 'genre_id': genre['id'], 'name': genre['name']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def channel_play_genre(genre_id, name=''):
    """Start 24/7 genre channel: random popular movies from genre, back to back"""
    # Fetch 3 pages of popular movies in this genre (60 movies)
    all_movies = []
    for pg in range(1, 4):
        data = _tmdb_get('/discover/movie', {
            'with_genres': genre_id,
            'sort_by': 'popularity.desc',
            'vote_count.gte': 100,
            'page': pg
        })
        if data and data.get('results'):
            all_movies.extend(data['results'])
    
    if not all_movies:
        xbmcgui.Dialog().notification(ADDON_NAME, f'No movies found for {name}', ADDON_ICON)
        return
    
    random.shuffle(all_movies)
    
    xbmcgui.Dialog().notification(
        ADDON_NAME, f'24/7 {name}: {len(all_movies)} movies shuffled', ADDON_ICON, 3000
    )
    
    player = xbmc.Player()
    
    for movie in all_movies:
        title = movie.get('title', 'Unknown')
        year = (movie.get('release_date') or '')[:4]
        tmdb_id = movie.get('id', '')
        poster = movie.get('poster_path', '')
        
        log_utils.log(f'24/7 {name}: Playing {title} ({year})', xbmc.LOGINFO)
        
        stream_url = _channel_get_stream(title, year, tmdb_id, max_quality='1080p')
        
        if not stream_url:
            log_utils.log(f'24/7 {name}: No source for {title}, skipping', xbmc.LOGINFO)
            continue
        
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        li = xbmcgui.ListItem(f'{title} ({year})', path=stream_url)
        li.setArt({'icon': poster_url, 'thumb': poster_url, 'fanart': ADDON_FANART})
        
        player.play(stream_url, li)
        
        timeout = 30
        while not player.isPlaying() and timeout > 0:
            xbmc.sleep(500)
            timeout -= 1
        
        if not player.isPlaying():
            continue
        
        while player.isPlaying():
            xbmc.sleep(2000)
        
        xbmc.sleep(1000)
        
        if xbmc.Monitor().abortRequested():
            break
    
    xbmcgui.Dialog().notification(ADDON_NAME, f'24/7 {name}: Marathon complete!', ADDON_ICON)


def channel_ai_vibe():
    """AI Vibe Channel: describe a mood/vibe, AI builds a custom movie marathon"""
    from salts_lib import ai_search as ai_mod
    
    if ADDON.getSetting('ai_search_enabled') != 'true':
        xbmcgui.Dialog().ok('AI Vibe', 'AI Search is disabled.\n\nEnable it in Settings > AI Search.')
        return
    
    if not ADDON.getSetting('ai_api_key'):
        xbmcgui.Dialog().ok('AI Vibe', 'No API key configured.\n\nGo to Settings > AI Search to add your OpenAI key.')
        return
    
    keyboard = xbmc.Keyboard('', 'Describe the vibe (e.g. "cozy rainy day movies")')
    keyboard.doModal()
    
    if not keyboard.isConfirmed():
        return
    
    query = keyboard.getText().strip()
    if not query:
        return
    
    progress = xbmcgui.DialogProgress()
    progress.create('AI Vibe Channel', f'Asking AI: {query[:50]}...')
    progress.update(15, 'AI is picking movies for your vibe...')
    
    # Get AI recommendations (movies only for 24/7 playback)
    results = ai_mod.ai_search(query, media_filter='movie')
    
    if progress.iscanceled():
        progress.close()
        return
    
    if not results:
        progress.close()
        xbmcgui.Dialog().notification(ADDON_NAME, 'AI returned no results. Try a different vibe.', ADDON_ICON)
        return
    
    progress.update(40, f'Found {len(results)} movies. Looking up on TMDB...')
    
    # Look up each on TMDB to get IDs and posters
    movies = []
    for i, rec in enumerate(results):
        if progress.iscanceled():
            progress.close()
            return
        
        progress.update(40 + int(30 * i / len(results)), f'Looking up: {rec.get("title", "")}')
        
        title = rec.get('title', '')
        year = rec.get('year', '')
        
        tmdb_data = _tmdb_get('/search/movie', {'query': title, 'year': str(year) if year else ''})
        
        if tmdb_data and tmdb_data.get('results'):
            tmdb_item = tmdb_data['results'][0]
            movies.append({
                'title': tmdb_item.get('title', title),
                'year': str(tmdb_item.get('release_date', ''))[:4] or str(year),
                'tmdb_id': tmdb_item.get('id', ''),
                'poster': tmdb_item.get('poster_path', ''),
                'reason': rec.get('reason', '')
            })
        else:
            movies.append({
                'title': title,
                'year': str(year),
                'tmdb_id': '',
                'poster': '',
                'reason': rec.get('reason', '')
            })
    
    progress.close()
    
    if not movies:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No movies found for this vibe', ADDON_ICON)
        return
    
    random.shuffle(movies)
    
    # Show what's coming
    movie_names = ', '.join(m['title'] for m in movies[:5])
    xbmcgui.Dialog().notification(
        ADDON_NAME, f'AI Vibe: {len(movies)} movies - {movie_names}...', ADDON_ICON, 5000
    )
    
    player = xbmc.Player()
    
    for movie in movies:
        title = movie['title']
        year = movie['year']
        tmdb_id = movie['tmdb_id']
        poster = movie['poster']
        
        log_utils.log(f'AI Vibe: Playing {title} ({year})', xbmc.LOGINFO)
        
        stream_url = _channel_get_stream(title, year, tmdb_id, max_quality='1080p')
        
        if not stream_url:
            log_utils.log(f'AI Vibe: No source for {title}, skipping', xbmc.LOGINFO)
            continue
        
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        li = xbmcgui.ListItem(f'{title} ({year})', path=stream_url)
        li.setArt({'icon': poster_url, 'thumb': poster_url, 'fanart': ADDON_FANART})
        
        player.play(stream_url, li)
        
        timeout = 30
        while not player.isPlaying() and timeout > 0:
            xbmc.sleep(500)
            timeout -= 1
        
        if not player.isPlaying():
            continue
        
        while player.isPlaying():
            xbmc.sleep(2000)
        
        xbmc.sleep(1000)
        
        if xbmc.Monitor().abortRequested():
            break
    
    xbmcgui.Dialog().notification(ADDON_NAME, 'AI Vibe: Marathon complete!', ADDON_ICON)


def _channel_get_stream(title, year='', tmdb_id='', season='', episode='', media_type='movie', max_quality='1080p'):
    """Get a stream URL for 24/7 channel playback. Returns URL or None."""
    from scrapers import get_all_scrapers
    from scrapers.freestream_scraper import FreeStreamScraper
    
    debrid_enabled = (
        ADDON.getSetting('realdebrid_enabled') == 'true' or
        ADDON.getSetting('premiumize_enabled') == 'true' or
        ADDON.getSetting('alldebrid_enabled') == 'true' or
        ADDON.getSetting('torbox_enabled') == 'true'
    )
    
    quality_cap = {'4K': 4, '2160p': 4, '1080p': 3, 'HD': 3, '720p': 2, '480p': 1, 'SD': 0}
    max_val = quality_cap.get(max_quality, 3)
    
    all_sources = []
    scrapers = get_all_scrapers()
    
    for scraper in scrapers:
        try:
            if not scraper.is_enabled():
                continue
            is_free = isinstance(scraper, FreeStreamScraper)
            if not debrid_enabled and not is_free:
                continue
            
            if media_type == 'movie':
                results = scraper.get_movie_sources(title, year)
            else:
                results = scraper.get_episode_sources(title, year or '', season, episode)
            
            if results:
                for r in results:
                    q_val = quality_cap.get(r.get('quality', 'SD'), 0)
                    if q_val <= max_val:
                        all_sources.append(r)
        except Exception:
            continue
    
    if not all_sources:
        return None
    
    all_sources.sort(key=lambda x: (
        1 if x.get('cached') else 0,
        1 if x.get('direct') else 0,
        quality_cap.get(x.get('quality', 'SD'), 0),
        x.get('seeds', 0)
    ), reverse=True)
    
    for source in all_sources[:5]:
        magnet = source.get('magnet', '')
        url = source.get('url', '')
        
        try:
            if magnet:
                for setting_key, svc_class in [
                    ('realdebrid_enabled', debrid.RealDebrid),
                    ('premiumize_enabled', debrid.Premiumize),
                    ('alldebrid_enabled', debrid.AllDebrid),
                    ('torbox_enabled', debrid.TorBox),
                ]:
                    if ADDON.getSetting(setting_key) == 'true':
                        svc = svc_class()
                        if svc.is_authorized():
                            stream = svc.resolve_magnet(magnet)
                            if stream:
                                return stream
            elif url:
                if any(ext in url.lower() for ext in ['.m3u8', '.mp4', '.mkv']):
                    return url
                try:
                    import resolveurl
                    stream = resolveurl.resolve(url)
                    if stream:
                        return stream
                except Exception:
                    pass
        except Exception:
            continue
    
    return None


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
    elif mode == 'ai_search_menu':
        ai_search_menu()
    elif mode == 'ai_search':
        ai_search(params.get('media_filter', 'all'))
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
    elif mode == 'clear_hover_cache':
        clear_hover_cache()
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
    # Franchise modes
    elif mode == 'franchises_menu':
        franchises_menu()
    elif mode == 'search_franchise':
        search_franchise()
    elif mode == 'search_franchise_page':
        _search_franchise_results(params.get('query', ''), int(params.get('page', 1)))
    elif mode == 'franchise_movies':
        franchise_movies(params.get('collection_id', ''), params.get('name', ''))
    # Actor modes
    elif mode == 'actors_menu':
        actors_menu()
    elif mode == 'popular_actors':
        popular_actors(int(params.get('page', 1)))
    elif mode == 'search_actor':
        search_actor()
    elif mode == 'actor_movies':
        actor_movies(params.get('person_id', ''), params.get('name', ''), int(params.get('page', 1)))
    # 24/7 Channel modes
    elif mode == 'channel_menu':
        channel_menu()
    elif mode == 'channel_movies_menu':
        channel_movies_menu()
    elif mode == 'channel_search_actor':
        channel_search_actor()
    elif mode == 'channel_play_actor':
        channel_play_actor(params.get('person_id', ''), params.get('name', ''))
    elif mode == 'channel_shows_menu':
        channel_shows_menu()
    elif mode == 'channel_search_show':
        channel_search_show()
    elif mode == 'channel_play_show':
        channel_play_show(params.get('tmdb_id', ''), params.get('name', ''))
    elif mode == 'channel_genre_menu':
        channel_genre_menu()
    elif mode == 'channel_play_genre':
        channel_play_genre(params.get('genre_id', ''), params.get('name', ''))
    elif mode == 'channel_ai_vibe':
        channel_ai_vibe()
    elif mode == 'buy_beer':
        choice = xbmcgui.Dialog().select(
            'Buy Me a Beer - Support zeus768',
            ['Show QR Code (scan to donate)', 'Show Ko-fi Link']
        )
        if choice == 0:
            show_kofi_qr()
        elif choice == 1:
            xbmcgui.Dialog().ok(
                'Buy Me a Beer',
                '[COLOR orange]Thanks for the support![/COLOR]\n\n'
                'Visit: [COLOR cyan]https://ko-fi.com/zeus768[/COLOR]\n\n'
                'Every beer keeps the addons alive!'
            )
    else:
        log_utils.log(f'Unknown mode: {mode}', xbmc.LOGWARNING)
        main_menu()

if __name__ == '__main__':
    params = get_params()
    router(params)
