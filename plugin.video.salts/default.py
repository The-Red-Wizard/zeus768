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
    """Show compact Ko-fi QR code and link"""
    import ssl
    kofi_url = 'https://ko-fi.com/zeus768'
    qr_file = os.path.join(xbmcvfs.translatePath('special://temp/'), 'kofi_qr.png')
    try:
        ctx = ssl._create_unverified_context()
        req = Request(
            f'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={quote_plus(kofi_url)}&bgcolor=0-0-0&color=255-255-255',
            headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, context=ctx, timeout=10) as resp:
            with open(qr_file, 'wb') as f:
                f.write(resp.read())
        xbmc.executebuiltin(f'ShowPicture({qr_file})')
        xbmc.sleep(300)
    except:
        pass
    xbmcgui.Dialog().ok('Support zeus768', 'Scan QR or visit:\nhttps://ko-fi.com/zeus768')
    try:
        xbmc.executebuiltin('Action(Back)')
    except:
        pass

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
        {'title': '[B]AI Search[/B]', 'mode': 'ai_search_menu'},
        {'title': '[B]Trakt[/B]', 'mode': 'trakt_menu'},
        {'title': '[B]PunchPlay[/B] [COLOR grey][BETA][/COLOR]', 'mode': 'punchplay_menu'},
        {'title': 'Scrapers', 'mode': 'scrapers_menu'},
        {'title': 'Debrid Services', 'mode': 'debrid_menu'},
        {'title': 'Tools', 'mode': 'tools_menu'},
        {'title': 'Settings', 'mode': 'addon_settings'},
        {'title': 'Buy Me a Beer', 'mode': 'buy_beer'},
    ]

    # Continue Watching (PunchPlay /api/playback) - only shown when the endpoint
    # responds 200. Probe is cached for 60s so this does not slow the menu.
    try:
        if _punchplay_playback_available():
            items.insert(0, {'title': '[B][COLOR orange]Continue Watching[/COLOR][/B] [COLOR grey][BETA][/COLOR]',
                             'mode': 'continue_watching'})
    except Exception:
        pass

    # One-shot beta notice the first time a user lands on the main menu after
    # enabling PunchPlay. Gated behind punchplay_enabled so non-users never see it.
    try:
        if xbmcaddon.Addon().getSetting('punchplay_enabled') == 'true':
            _punchplay_beta_notice()
    except Exception:
        pass
    
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
        {'title': 'Live Movie Channels', 'mode': 'movie_channels_menu'},
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
        {'title': 'New Episodes Today', 'mode': 'new_episodes_calendar', 'days_back': '0'},
        {'title': 'Latest Show Premieres', 'mode': 'latest_premieres', 'page': '1'},
        {'title': ' Returning Shows (New Seasons)', 'mode': 'returning_shows'},
        {'title': ' Browse by Network', 'mode': 'network_browser'},
        {'title': ' My Episode Countdown', 'mode': 'episode_countdown'},
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


# ==================== NEW EPISODES & PREMIERES ====================

def new_episodes_calendar(days_back=0):
    """Show new episodes that aired on a specific day (0=today, up to 7 days back)"""
    days_back = int(days_back)
    target_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
    date_str = target_date.strftime('%Y-%m-%d')
    display_date = target_date.strftime('%A, %B %d')
    
    # Add navigation for previous/next days
    if days_back < 7:
        li = xbmcgui.ListItem(f'[B]<< Previous Day ({(target_date - datetime.timedelta(days=1)).strftime("%b %d")})[/B]')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': 'new_episodes_calendar', 'days_back': str(days_back + 1)})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    if days_back > 0:
        li = xbmcgui.ListItem(f'[B]>> Next Day ({(target_date + datetime.timedelta(days=1)).strftime("%b %d")})[/B]')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': 'new_episodes_calendar', 'days_back': str(days_back - 1)})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Add day header
    li = xbmcgui.ListItem(f'━━━ {display_date} ━━━')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
    
    # Fetch episodes airing on that date using discover/tv with air_date filter
    data = _tmdb_get('/discover/tv', {
        'air_date.gte': date_str,
        'air_date.lte': date_str,
        'sort_by': 'popularity.desc',
        'page': 1
    })
    
    if not data or not data.get('results'):
        li = xbmcgui.ListItem('No episodes found for this day')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    shows = data.get('results', [])
    
    # For each show, get the specific episode that aired
    for show in shows[:50]:  # Limit to 50 for performance
        show_id = show.get('id')
        show_name = show.get('name', 'Unknown')
        poster = show.get('poster_path', '')
        backdrop = show.get('backdrop_path', '')
        overview = show.get('overview', '')
        
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        # Get the show's latest episode info
        show_details = _tmdb_get(f'/tv/{show_id}')
        if show_details:
            last_ep = show_details.get('last_episode_to_air', {})
            if last_ep:
                season_num = last_ep.get('season_number', 1)
                ep_num = last_ep.get('episode_number', 1)
                ep_name = last_ep.get('name', '')
                ep_air = last_ep.get('air_date', '')
                
                # Only show if this episode actually aired on target date
                if ep_air == date_str:
                    label = f'[B]{show_name}[/B] - S{season_num:02d}E{ep_num:02d}'
                    if ep_name:
                        label += f' - {ep_name}'
                    
                    li = xbmcgui.ListItem(label)
                    li.setArt({
                        'icon': poster_url,
                        'thumb': poster_url,
                        'poster': poster_url,
                        'fanart': backdrop_url
                    })
                    
                    info_tag = li.getVideoInfoTag()
                    info_tag.setTitle(f'{show_name} S{season_num:02d}E{ep_num:02d}')
                    info_tag.setPlot(overview)
                    info_tag.setSeason(season_num)
                    info_tag.setEpisode(ep_num)
                    info_tag.setMediaType('episode')
                    
                    item_url = build_url({
                        'mode': 'get_sources',
                        'title': show_name,
                        'year': str(show_details.get('first_air_date', ''))[:4],
                        'season': season_num,
                        'episode': ep_num,
                        'media_type': 'tvshow',
                        'tmdb_id': show_id
                    })
                    
                    xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)


def latest_premieres(page=1):
    """Show latest TV show premieres from the last 7 days with infinite scroll.
    By default shows English/American shows only. International shows can be enabled in settings."""
    page = int(page)
    
    # Check setting for international content
    show_international = ADDON.getSetting('premiere_international') == 'true'
    
    # Calculate date range for last 7 days
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Build request params - filter to English/American by default
    params = {
        'first_air_date.gte': start_str,
        'first_air_date.lte': end_str,
        'sort_by': 'first_air_date.desc',
        'page': page
    }
    
    # If NOT showing international, filter to English language and US/UK/CA/AU origin
    if not show_international:
        params['with_original_language'] = 'en'
        params['with_origin_country'] = 'US|GB|CA|AU'
    
    # Fetch new shows that premiered in last 7 days
    data = _tmdb_get('/discover/tv', params)
    
    if not data or not data.get('results'):
        if page == 1:
            xbmcgui.Dialog().notification(ADDON_NAME, 'No new premieres found', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    results = data.get('results', [])
    total_pages = data.get('total_pages', 1)
    total_results = data.get('total_results', 0)
    
    # Add header with filter indicator
    filter_text = 'All Countries' if show_international else 'English/American Only'
    li = xbmcgui.ListItem(f'━━━ New Premieres (Last 7 Days) - {filter_text} - Page {page}/{total_pages} ({total_results} shows) ━━━')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
    
    for show in results:
        title = show.get('name', show.get('original_name', 'Unknown'))
        year = (show.get('first_air_date') or '')[:4]
        premiere_date = show.get('first_air_date', 'TBA')
        tmdb_id = show.get('id', '')
        origin_country = ', '.join(show.get('origin_country', []))
        original_language = show.get('original_language', '')
        
        poster = show.get('poster_path', '')
        backdrop = show.get('backdrop_path', '')
        overview = show.get('overview', '')
        rating = show.get('vote_average', 0)
        
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        # Format premiere date nicely
        try:
            premiere_dt = datetime.datetime.strptime(premiere_date, '%Y-%m-%d')
            premiere_display = premiere_dt.strftime('%b %d')
        except:
            premiere_display = premiere_date
        
        # Add country indicator for international content
        country_indicator = ''
        if show_international and origin_country and origin_country not in ['US', 'GB', 'CA', 'AU']:
            country_indicator = f' [{origin_country}]'
        
        label = f'NEW {title} ({year}){country_indicator} - Premiered: {premiere_display}'
        
        li = xbmcgui.ListItem(label)
        li.setArt({
            'icon': poster_url,
            'thumb': poster_url,
            'poster': poster_url,
            'fanart': backdrop_url
        })
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setYear(int(year) if year else 0)
        info_tag.setPlot(overview)
        info_tag.setRating(rating)
        info_tag.setMediaType('tvshow')
        
        item_url = build_url({
            'mode': 'tv_seasons',
            'title': title,
            'year': year,
            'tmdb_id': tmdb_id
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
    
    # Add infinite scroll - next page
    if page < total_pages:
        li = xbmcgui.ListItem(f'[B]>> Load More (Page {page + 1})[/B]')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': 'latest_premieres', 'page': str(page + 1)})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)


# ==================== TV SHOW ENHANCEMENTS ====================

# TV Networks for browser
TV_NETWORKS = [
    {'name': 'Netflix', 'id': 213, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Netflix_2015_logo.svg/200px-Netflix_2015_logo.svg.png'},
    {'name': 'HBO', 'id': 49, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/HBO_logo.svg/200px-HBO_logo.svg.png'},
    {'name': 'Amazon Prime Video', 'id': 1024, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Amazon_Prime_Video_logo.svg/200px-Amazon_Prime_Video_logo.svg.png'},
    {'name': 'Apple TV+', 'id': 2552, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/Apple_TV_Plus_Logo.svg/200px-Apple_TV_Plus_Logo.svg.png'},
    {'name': 'Disney+', 'id': 2739, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Disney%2B_logo.svg/200px-Disney%2B_logo.svg.png'},
    {'name': 'Hulu', 'id': 453, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Hulu_Logo.svg/200px-Hulu_Logo.svg.png'},
    {'name': 'Paramount+', 'id': 4330, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Paramount_Plus.svg/200px-Paramount_Plus.svg.png'},
    {'name': 'Peacock', 'id': 3353, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/NBCUniversal_Peacock_Logo.svg/200px-NBCUniversal_Peacock_Logo.svg.png'},
    {'name': 'BBC One', 'id': 4, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/BBC_One_logo.svg/200px-BBC_One_logo.svg.png'},
    {'name': 'BBC Two', 'id': 332, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/BBC_Two_logo.svg/200px-BBC_Two_logo.svg.png'},
    {'name': 'ITV', 'id': 9, 'logo': 'https://upload.wikimedia.org/wikipedia/en/thumb/a/aa/ITV_logo_2022.svg/200px-ITV_logo_2022.svg.png'},
    {'name': 'Channel 4', 'id': 26, 'logo': 'https://upload.wikimedia.org/wikipedia/en/thumb/9/9e/Channel_4_logo_2015.svg/200px-Channel_4_logo_2015.svg.png'},
    {'name': 'Sky Atlantic', 'id': 1063, 'logo': 'https://upload.wikimedia.org/wikipedia/en/thumb/a/a8/Sky_Atlantic_logo.svg/200px-Sky_Atlantic_logo.svg.png'},
    {'name': 'AMC', 'id': 174, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/AMC_logo_2019.svg/200px-AMC_logo_2019.svg.png'},
    {'name': 'FX', 'id': 88, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/FX_logo.svg/200px-FX_logo.svg.png'},
    {'name': 'NBC', 'id': 6, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/NBC_logo_%282022%29.svg/200px-NBC_logo_%282022%29.svg.png'},
    {'name': 'CBS', 'id': 16, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ee/CBS_logo_%282020%29.svg/200px-CBS_logo_%282020%29.svg.png'},
    {'name': 'ABC', 'id': 2, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/ABC-2021-LOGO.svg/200px-ABC-2021-LOGO.svg.png'},
    {'name': 'FOX', 'id': 19, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Fox_Broadcasting_Company_logo_%282019%29.svg/200px-Fox_Broadcasting_Company_logo_%282019%29.svg.png'},
    {'name': 'The CW', 'id': 71, 'logo': 'https://upload.wikimedia.org/wikipedia/en/thumb/c/c0/The_CW_logo_2022.svg/200px-The_CW_logo_2022.svg.png'},
    {'name': 'Showtime', 'id': 67, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Showtime.svg/200px-Showtime.svg.png'},
    {'name': 'Starz', 'id': 318, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Starz_2022.svg/200px-Starz_2022.svg.png'},
    {'name': 'Max (HBO Max)', 'id': 3186, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Max_logo.svg/200px-Max_logo.svg.png'},
    {'name': 'Crunchyroll', 'id': 1112, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Crunchyroll_logo_2024.svg/200px-Crunchyroll_logo_2024.svg.png'},
]

# Episode countdown tracking (stored in addon data)
_COUNTDOWN_SHOWS = None


def returning_shows(page=1):
    """Show TV shows with new seasons starting soon (next 30 days)"""
    page = int(page)
    
    # Get shows airing in next 30 days that have multiple seasons
    end_date = datetime.datetime.now() + datetime.timedelta(days=30)
    start_date = datetime.datetime.now()
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Fetch shows with new episodes coming
    data = _tmdb_get('/discover/tv', {
        'air_date.gte': start_str,
        'air_date.lte': end_str,
        'sort_by': 'popularity.desc',
        'with_original_language': 'en',
        'page': page
    })
    
    if not data or not data.get('results'):
        if page == 1:
            xbmcgui.Dialog().notification(ADDON_NAME, 'No returning shows found', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    results = data.get('results', [])
    total_pages = min(data.get('total_pages', 1), 10)  # Limit to 10 pages
    
    # Add header
    li = xbmcgui.ListItem(f'━━━ Returning Shows (New Seasons) - Page {page}/{total_pages} ━━━')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
    
    # Filter and display shows with multiple seasons (returning shows)
    for show in results:
        tmdb_id = show.get('id', '')
        
        # Get detailed info to check season count
        details = _tmdb_get(f'/tv/{tmdb_id}')
        if not details:
            continue
        
        num_seasons = details.get('number_of_seasons', 1)
        if num_seasons < 2:  # Skip shows with only 1 season (new shows, not returning)
            continue
        
        title = show.get('name', show.get('original_name', 'Unknown'))
        year = (show.get('first_air_date') or '')[:4]
        
        poster = show.get('poster_path', '')
        backdrop = show.get('backdrop_path', '')
        overview = show.get('overview', '')
        rating = show.get('vote_average', 0)
        
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        # Get next episode info
        next_ep = details.get('next_episode_to_air', {})
        next_ep_date = next_ep.get('air_date', '') if next_ep else ''
        next_ep_name = next_ep.get('name', '') if next_ep else ''
        season_num = next_ep.get('season_number', '') if next_ep else ''
        ep_num = next_ep.get('episode_number', '') if next_ep else ''
        
        # Calculate days until
        days_until = ''
        if next_ep_date:
            try:
                ep_date = datetime.datetime.strptime(next_ep_date, '%Y-%m-%d')
                delta = (ep_date - datetime.datetime.now()).days
                if delta == 0:
                    days_until = 'TODAY'
                elif delta == 1:
                    days_until = 'TOMORROW'
                elif delta > 0:
                    days_until = f'in {delta} days'
            except:
                pass
        
        label = f'[B]{title}[/B] (Season {num_seasons})'
        if season_num and ep_num:
            label += f' - S{season_num:02d}E{ep_num:02d}'
        if days_until:
            label += f' {days_until}'
        
        li = xbmcgui.ListItem(label)
        li.setArt({
            'icon': poster_url,
            'thumb': poster_url,
            'poster': poster_url,
            'fanart': backdrop_url
        })
        
        plot = f'Season {num_seasons} returning\n\n{overview}'
        if next_ep_name:
            plot = f'Next: S{season_num}E{ep_num} - {next_ep_name}\nAirs: {next_ep_date}\n\n{overview}'
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setYear(int(year) if year else 0)
        info_tag.setPlot(plot)
        info_tag.setRating(rating)
        info_tag.setMediaType('tvshow')
        
        # Add context menu for countdown tracking
        countdown_url = build_url({
            'mode': 'add_to_countdown',
            'tmdb_id': str(tmdb_id),
            'title': title
        })
        li.addContextMenuItems([('Track Episode Countdown', f'RunPlugin({countdown_url})')])
        
        item_url = build_url({
            'mode': 'tv_seasons',
            'title': title,
            'year': year,
            'tmdb_id': tmdb_id
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
    
    # Add next page
    if page < total_pages:
        li = xbmcgui.ListItem(f'[B]>> Load More (Page {page + 1})[/B]')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': 'returning_shows', 'page': str(page + 1)})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)


def network_browser():
    """Browse TV shows by network"""
    # Add header
    li = xbmcgui.ListItem('━━━ Browse by Network ━━━')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
    
    for network in TV_NETWORKS:
        name = network['name']
        network_id = network['id']
        logo = network.get('logo', ADDON_ICON)
        
        li = xbmcgui.ListItem(f'[B]{name}[/B]')
        li.setArt({
            'icon': logo,
            'thumb': logo,
            'poster': logo,
            'fanart': ADDON_FANART
        })
        
        url = build_url({'mode': 'network_shows', 'network_id': str(network_id), 'network_name': name})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def network_shows(network_id, network_name, page=1):
    """Show TV shows from a specific network"""
    network_id = int(network_id)
    page = int(page)
    
    # Fetch shows from this network
    data = _tmdb_get('/discover/tv', {
        'with_networks': network_id,
        'sort_by': 'popularity.desc',
        'page': page
    })
    
    if not data or not data.get('results'):
        if page == 1:
            xbmcgui.Dialog().notification(ADDON_NAME, f'No shows found for {network_name}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    results = data.get('results', [])
    total_pages = min(data.get('total_pages', 1), 20)
    total_results = data.get('total_results', 0)
    
    # Add header
    li = xbmcgui.ListItem(f'━━━ {network_name} Shows - Page {page}/{total_pages} ({total_results} total) ━━━')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
    
    for show in results:
        title = show.get('name', show.get('original_name', 'Unknown'))
        year = (show.get('first_air_date') or '')[:4]
        tmdb_id = show.get('id', '')
        
        poster = show.get('poster_path', '')
        backdrop = show.get('backdrop_path', '')
        overview = show.get('overview', '')
        rating = show.get('vote_average', 0)
        
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        label = f'{title} ({year})' if year else title
        
        li = xbmcgui.ListItem(label)
        li.setArt({
            'icon': poster_url,
            'thumb': poster_url,
            'poster': poster_url,
            'fanart': backdrop_url
        })
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setYear(int(year) if year else 0)
        info_tag.setPlot(overview)
        info_tag.setRating(rating)
        info_tag.setMediaType('tvshow')
        
        item_url = build_url({
            'mode': 'tv_seasons',
            'title': title,
            'year': year,
            'tmdb_id': tmdb_id
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
    
    # Add next page
    if page < total_pages:
        li = xbmcgui.ListItem(f'[B]>> Load More (Page {page + 1})[/B]')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': 'network_shows', 'network_id': str(network_id), 'network_name': network_name, 'page': str(page + 1)})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)


def episode_countdown():
    """Show tracked shows with countdown to next episode"""
    from salts_lib import db_utils
    db = db_utils.DB_Connection()
    
    # Get tracked shows from database
    tracked_shows = db.get_countdown_shows()
    
    if not tracked_shows:
        # Add instruction
        li = xbmcgui.ListItem('No shows tracked yet.')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
        
        li = xbmcgui.ListItem('To track a show: Browse to any show, open context menu, select "Track Episode Countdown"')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
        
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    # Add header
    li = xbmcgui.ListItem('━━━ My Episode Countdown ━━━')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
    
    # Fetch details for each tracked show
    countdown_list = []
    for show_data in tracked_shows:
        tmdb_id = show_data.get('tmdb_id')
        if not tmdb_id:
            continue
        
        details = _tmdb_get(f'/tv/{tmdb_id}')
        if not details:
            continue
        
        title = details.get('name', 'Unknown')
        poster = details.get('poster_path', '')
        backdrop = details.get('backdrop_path', '')
        
        poster_url = f'{TMDB_IMG}/w500{poster}' if poster else ADDON_ICON
        backdrop_url = f'{TMDB_IMG}/original{backdrop}' if backdrop else ADDON_FANART
        
        next_ep = details.get('next_episode_to_air', {})
        if next_ep:
            next_ep_date = next_ep.get('air_date', '')
            next_ep_name = next_ep.get('name', '')
            season_num = next_ep.get('season_number', 1)
            ep_num = next_ep.get('episode_number', 1)
            
            # Calculate days until
            days_until = 999
            days_text = 'TBA'
            if next_ep_date:
                try:
                    ep_date = datetime.datetime.strptime(next_ep_date, '%Y-%m-%d')
                    days_until = (ep_date - datetime.datetime.now()).days
                    if days_until < 0:
                        days_text = 'AIRED'
                    elif days_until == 0:
                        days_text = 'TODAY!'
                    elif days_until == 1:
                        days_text = 'TOMORROW'
                    elif days_until <= 7:
                        days_text = f'{days_until} days'
                    else:
                        days_text = f'{days_until} days'
                except:
                    pass
            
            countdown_list.append({
                'title': title,
                'tmdb_id': tmdb_id,
                'poster': poster_url,
                'fanart': backdrop_url,
                'season': season_num,
                'episode': ep_num,
                'ep_name': next_ep_name,
                'air_date': next_ep_date,
                'days_until': days_until,
                'days_text': days_text
            })
        else:
            # Show ended or no next episode
            countdown_list.append({
                'title': title,
                'tmdb_id': tmdb_id,
                'poster': poster_url,
                'fanart': backdrop_url,
                'season': 0,
                'episode': 0,
                'ep_name': '',
                'air_date': '',
                'days_until': 999,
                'days_text': 'No upcoming episodes'
            })
    
    # Sort by days until (soonest first)
    countdown_list.sort(key=lambda x: x['days_until'])
    
    for item in countdown_list:
        title = item['title']
        season = item['season']
        episode = item['episode']
        ep_name = item['ep_name']
        days_text = item['days_text']
        air_date = item['air_date']
        
        if season and episode:
            label = f'[B]{title}[/B] - S{season:02d}E{episode:02d} - {days_text}'
        else:
            label = f'[B]{title}[/B] - {days_text}'
        
        li = xbmcgui.ListItem(label)
        li.setArt({
            'icon': item['poster'],
            'thumb': item['poster'],
            'poster': item['poster'],
            'fanart': item['fanart']
        })
        
        plot = f'Next Episode: S{season:02d}E{episode:02d}'
        if ep_name:
            plot += f' - {ep_name}'
        if air_date:
            plot += f'\nAirs: {air_date}'
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setPlot(plot)
        info_tag.setMediaType('tvshow')
        
        # Context menu to remove from countdown
        remove_url = build_url({
            'mode': 'remove_from_countdown',
            'tmdb_id': str(item['tmdb_id']),
            'title': title
        })
        li.addContextMenuItems([('Remove from Countdown', f'RunPlugin({remove_url})')])
        
        item_url = build_url({
            'mode': 'tv_seasons',
            'title': title,
            'year': '',
            'tmdb_id': item['tmdb_id']
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, item_url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)


def add_to_countdown(tmdb_id, title):
    """Add a show to the episode countdown tracker"""
    from salts_lib import db_utils
    db = db_utils.DB_Connection()
    
    if db.add_countdown_show(tmdb_id, title):
        xbmcgui.Dialog().notification(ADDON_NAME, f'Added "{title}" to Episode Countdown', ADDON_ICON, 2000)
    else:
        xbmcgui.Dialog().notification(ADDON_NAME, f'"{title}" already tracked', ADDON_ICON, 2000)


def remove_from_countdown(tmdb_id, title):
    """Remove a show from the episode countdown tracker"""
    from salts_lib import db_utils
    db = db_utils.DB_Connection()
    
    db.remove_countdown_show(tmdb_id)
    xbmcgui.Dialog().notification(ADDON_NAME, f'Removed "{title}" from Episode Countdown', ADDON_ICON, 2000)
    xbmc.executebuiltin('Container.Refresh')


# ==================== LIVE MOVIE CHANNELS WITH EPG ====================

# Movie channel definitions with EPG sources and genre IDs for TMDB
# Genre IDs from TMDB: 28=Action, 35=Comedy, 10751=Family, 53=Thriller, 18=Drama, 878=Sci-Fi, 27=Horror, 16=Animation, 10749=Romance
MOVIE_CHANNELS = [
    # Sky Cinema UK - each channel has unique genre for EPG
    {'name': 'Sky Cinema Premiere', 'id': 'sky_premiere', 'epg_id': '1402', 'country': 'UK', 'category': 'Sky Cinema', 'genre_id': None, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/sky-cinema-premiere-uk.png'},
    {'name': 'Sky Cinema Action', 'id': 'sky_action', 'epg_id': '1807', 'country': 'UK', 'category': 'Sky Cinema', 'genre_id': 28, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/sky-cinema-action-uk.png'},
    {'name': 'Sky Cinema Family', 'id': 'sky_family', 'epg_id': '1811', 'country': 'UK', 'category': 'Sky Cinema', 'genre_id': 10751, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/sky-cinema-family-uk.png'},
    {'name': 'Sky Cinema Comedy', 'id': 'sky_comedy', 'epg_id': '1813', 'country': 'UK', 'category': 'Sky Cinema', 'genre_id': 35, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/sky-cinema-comedy-uk.png'},
    {'name': 'Sky Cinema Thriller', 'id': 'sky_thriller', 'epg_id': '1814', 'country': 'UK', 'category': 'Sky Cinema', 'genre_id': 53, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/sky-cinema-thriller-uk.png'},
    {'name': 'Sky Cinema Drama', 'id': 'sky_drama', 'epg_id': '1815', 'country': 'UK', 'category': 'Sky Cinema', 'genre_id': 18, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/sky-cinema-drama-uk.png'},
    {'name': 'Sky Cinema Sci-Fi & Horror', 'id': 'sky_scifi', 'epg_id': '1816', 'country': 'UK', 'category': 'Sky Cinema', 'genre_id': 878, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/sky-cinema-sci-fi-horror-uk.png'},
    {'name': 'Sky Cinema Greats', 'id': 'sky_greats', 'epg_id': '1808', 'country': 'UK', 'category': 'Sky Cinema', 'genre_id': None, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/sky-cinema-greats-uk.png'},
    {'name': 'Sky Cinema Animation', 'id': 'sky_animation', 'epg_id': '5300', 'country': 'UK', 'category': 'Sky Cinema', 'genre_id': 16, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/sky-cinema-animation-uk.png'},
    
    # Film4 and Free UK - each with unique offset for variety
    {'name': 'Film4', 'id': 'film4', 'epg_id': '1627', 'country': 'UK', 'category': 'Free UK', 'genre_id': None, 'offset': 0, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/film4-uk.png'},
    {'name': 'Film4 +1', 'id': 'film4_plus1', 'epg_id': '1806', 'country': 'UK', 'category': 'Free UK', 'genre_id': None, 'offset': 1, 'logo': 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/united-kingdom/film4-plus1-uk.png'},
    {'name': 'Movies 24', 'id': 'movies24', 'epg_id': '1843', 'country': 'UK', 'category': 'Free UK', 'genre_id': 28, 'offset': 2, 'logo': 'https://upload.wikimedia.org/wikipedia/en/d/d3/Movies_24_logo.png'},
    {'name': 'Movies 24+', 'id': 'movies24_plus', 'epg_id': '5605', 'country': 'UK', 'category': 'Free UK', 'genre_id': 28, 'offset': 3, 'logo': 'https://upload.wikimedia.org/wikipedia/en/d/d3/Movies_24_logo.png'},
    {'name': 'Great! Movies', 'id': 'great_movies', 'epg_id': '1870', 'country': 'UK', 'category': 'Free UK', 'genre_id': None, 'offset': 4, 'logo': 'https://upload.wikimedia.org/wikipedia/en/4/46/Great%21_Movies_logo.png'},
    {'name': 'Great! Action', 'id': 'great_action', 'epg_id': '5277', 'country': 'UK', 'category': 'Free UK', 'genre_id': 28, 'offset': 5, 'logo': 'https://upload.wikimedia.org/wikipedia/en/a/a7/Great%21_Action_logo.png'},
    {'name': 'Great! Romance', 'id': 'great_romance', 'epg_id': '5296', 'country': 'UK', 'category': 'Free UK', 'genre_id': 10749, 'offset': 6, 'logo': 'https://upload.wikimedia.org/wikipedia/en/thumb/3/35/Great%21_Romance_logo.png/220px-Great%21_Romance_logo.png'},
    {'name': 'Legend', 'id': 'legend', 'epg_id': '4075', 'country': 'UK', 'category': 'Free UK', 'genre_id': None, 'offset': 7, 'logo': 'https://upload.wikimedia.org/wikipedia/en/6/63/Legend_TV_logo.png'},
    {'name': 'Talking Pictures TV', 'id': 'tptv', 'epg_id': '4074', 'country': 'UK', 'category': 'Free UK', 'genre_id': None, 'offset': 8, 'logo': 'https://upload.wikimedia.org/wikipedia/en/6/68/Talking_Pictures_TV_logo.png'},
    
    # Sony Movies
    {'name': 'Sony Movies', 'id': 'sony_movies', 'epg_id': '3507', 'country': 'UK', 'category': 'Sony', 'genre_id': None, 'offset': 9, 'logo': 'https://upload.wikimedia.org/wikipedia/en/6/61/Sony_Movies_logo.png'},
    {'name': 'Sony Movies Action', 'id': 'sony_action', 'epg_id': '3508', 'country': 'UK', 'category': 'Sony', 'genre_id': 28, 'offset': 10, 'logo': 'https://upload.wikimedia.org/wikipedia/en/2/2f/Sony_Movies_Action_logo.png'},
    {'name': 'Sony Movies Classic', 'id': 'sony_classic', 'epg_id': '3509', 'country': 'UK', 'category': 'Sony', 'genre_id': None, 'offset': 11, 'logo': 'https://upload.wikimedia.org/wikipedia/en/5/56/Sony_Movies_Classic_logo.png'},
    
    # US Movie Channels
    {'name': 'AMC', 'id': 'amc_us', 'epg_id': 'amc.us', 'country': 'US', 'category': 'US Movies', 'genre_id': None, 'offset': 12, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/AMC_logo_2019.svg/200px-AMC_logo_2019.svg.png'},
    {'name': 'TCM (Turner Classic Movies)', 'id': 'tcm_us', 'epg_id': 'tcm.us', 'country': 'US', 'category': 'US Movies', 'genre_id': None, 'offset': 13, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Turner_Classic_Movies_Logo.svg/200px-Turner_Classic_Movies_Logo.svg.png'},
    {'name': 'FX Movies', 'id': 'fxm', 'epg_id': 'fxm.us', 'country': 'US', 'category': 'US Movies', 'genre_id': None, 'offset': 14, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/FXM_logo.svg/200px-FXM_logo.svg.png'},
    {'name': 'Paramount Network', 'id': 'paramount', 'epg_id': 'paramountnetwork.us', 'country': 'US', 'category': 'US Movies', 'genre_id': None, 'offset': 15, 'logo': 'https://upload.wikimedia.org/wikipedia/en/thumb/a/a0/Paramount_Network.svg/200px-Paramount_Network.svg.png'},
    
    # European Movie Channels
    {'name': 'Cine+ Premier (France)', 'id': 'cine_premier', 'epg_id': 'cinepluspremier.fr', 'country': 'FR', 'category': 'European', 'genre_id': None, 'offset': 16, 'logo': 'https://upload.wikimedia.org/wikipedia/fr/e/e3/Cin%C3%A9%2B_Premier_2022.svg'},
    {'name': 'Canal+ Cinema (France)', 'id': 'canal_cinema', 'epg_id': 'canalpluscinema.fr', 'country': 'FR', 'category': 'European', 'genre_id': None, 'offset': 17, 'logo': 'https://upload.wikimedia.org/wikipedia/fr/5/5a/Canal%2B_Cin%C3%A9ma_2023.svg'},
    {'name': 'RTL Kino (Germany)', 'id': 'rtl_kino', 'epg_id': 'rtl.de', 'country': 'DE', 'category': 'European', 'genre_id': None, 'offset': 18, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/RTL_Logo_ab_2021.svg/200px-RTL_Logo_ab_2021.svg.png'},
    {'name': 'Sky Cinema (Germany)', 'id': 'sky_de', 'epg_id': 'skycinema.de', 'country': 'DE', 'category': 'European', 'genre_id': None, 'offset': 19, 'logo': 'https://upload.wikimedia.org/wikipedia/de/thumb/e/ee/Sky_Deutschland.svg/200px-Sky_Deutschland.svg.png'},
    {'name': 'Sky Cinema (Italy)', 'id': 'sky_it', 'epg_id': 'skycinema.it', 'country': 'IT', 'category': 'European', 'genre_id': None, 'offset': 20, 'logo': 'https://upload.wikimedia.org/wikipedia/it/thumb/c/ce/Sky_Cinema_-_Logo_2020.svg/200px-Sky_Cinema_-_Logo_2020.svg.png'},
    
    # FAST Channels (Free Ad-Supported)
    {'name': 'Pluto TV Movies', 'id': 'pluto_movies', 'epg_id': 'plutotv.movies', 'country': 'US', 'category': 'FAST', 'genre_id': None, 'offset': 21, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Pluto_TV_2020_logo.svg/200px-Pluto_TV_2020_logo.svg.png'},
    {'name': 'Pluto TV Action', 'id': 'pluto_action', 'epg_id': 'plutotv.action', 'country': 'US', 'category': 'FAST', 'genre_id': 28, 'offset': 22, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Pluto_TV_2020_logo.svg/200px-Pluto_TV_2020_logo.svg.png'},
    {'name': 'Pluto TV Comedy', 'id': 'pluto_comedy', 'epg_id': 'plutotv.comedy', 'country': 'US', 'category': 'FAST', 'genre_id': 35, 'offset': 23, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Pluto_TV_2020_logo.svg/200px-Pluto_TV_2020_logo.svg.png'},
    {'name': 'Tubi Originals', 'id': 'tubi', 'epg_id': 'tubi.originals', 'country': 'US', 'category': 'FAST', 'genre_id': None, 'offset': 24, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Tubi_logo.svg/200px-Tubi_logo.svg.png'},
    {'name': 'Plex Movies', 'id': 'plex_movies', 'epg_id': 'plex.movies', 'country': 'US', 'category': 'FAST', 'genre_id': None, 'offset': 25, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Plex_logo_2022.svg/200px-Plex_logo_2022.svg.png'},
    {'name': 'Samsung TV Plus Movies', 'id': 'samsung_movies', 'epg_id': 'samsung.movies', 'country': 'US', 'category': 'FAST', 'genre_id': None, 'offset': 26, 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Samsung_TV_Plus_Logo.svg/200px-Samsung_TV_Plus_Logo.svg.png'},
]

# Cache for EPG data
_EPG_CACHE = {}
_EPG_CACHE_TIME = 0
_TMDB_MOVIES_CACHE = {}

def movie_channels_menu():
    """Movie Channels main menu - browse by category"""
    categories = {}
    for ch in MOVIE_CHANNELS:
        cat = ch.get('category', 'Other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(ch)
    
    # Add Force Refresh EPG option at top
    li = xbmcgui.ListItem('⟳ Force Refresh EPG')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({'mode': 'force_refresh_epg'})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    # Add Movie Schedules option
    li = xbmcgui.ListItem(' Movie Schedules (Next 12 Hours)')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({'mode': 'movie_schedules'})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Add category folders
    for cat_name in ['Sky Cinema', 'Free UK', 'Sony', 'US Movies', 'European', 'FAST']:
        if cat_name in categories:
            count = len(categories[cat_name])
            li = xbmcgui.ListItem(f'[B]{cat_name}[/B] ({count} channels)')
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            url = build_url({'mode': 'movie_channels_category', 'category': cat_name})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Add "All Channels" option
    li = xbmcgui.ListItem(f'All Movie Channels ({len(MOVIE_CHANNELS)})')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({'mode': 'movie_channels_category', 'category': 'all'})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def force_refresh_epg():
    """Force refresh the EPG cache"""
    global _EPG_CACHE, _EPG_CACHE_TIME, _TMDB_MOVIES_CACHE
    _EPG_CACHE = {}
    _EPG_CACHE_TIME = 0
    _TMDB_MOVIES_CACHE = {}
    xbmcgui.Dialog().notification(ADDON_NAME, 'EPG cache cleared! Refreshing...', ADDON_ICON, 2000)
    # Fetch fresh data
    _fetch_epg_data()
    xbmcgui.Dialog().notification(ADDON_NAME, 'EPG refreshed successfully!', ADDON_ICON, 2000)
    xbmc.executebuiltin('Container.Refresh')


def movie_schedules():
    """Show movie schedules for all channels - next 12 hours"""
    epg_data = _fetch_epg_data()
    now = datetime.datetime.now()
    
    # Group by time slots (2-hour blocks for next 12 hours)
    time_slots = []
    for hours_ahead in range(0, 12, 2):
        slot_time = now + datetime.timedelta(hours=hours_ahead)
        slot_hour = (slot_time.hour // 2) * 2
        slot_display = f'{slot_hour:02d}:00 - {(slot_hour + 2) % 24:02d}:00'
        if hours_ahead == 0:
            slot_display = f'NOW {slot_display}'
        time_slots.append({
            'display': slot_display,
            'hours_ahead': hours_ahead,
            'slot_hour': slot_hour
        })
    
    # Add time slot folders
    for slot in time_slots:
        li = xbmcgui.ListItem(f'[B]{slot["display"]}[/B]')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': 'movie_schedule_slot', 'hours_ahead': str(slot['hours_ahead'])})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def movie_schedule_slot(hours_ahead=0):
    """Show what's playing on all channels at a specific time slot"""
    hours_ahead = int(hours_ahead)
    now = datetime.datetime.now()
    target_time = now + datetime.timedelta(hours=hours_ahead)
    
    # Get movies for this time slot
    slot_hour = (target_time.hour // 2) * 2
    slot_display = f'{slot_hour:02d}:00 - {(slot_hour + 2) % 24:02d}:00'
    
    # Add header
    header_text = 'NOW PLAYING' if hours_ahead == 0 else f'Playing at {slot_display}'
    li = xbmcgui.ListItem(f'━━━ {header_text} ━━━')
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
    
    # Calculate movies for each channel at this time
    for channel in MOVIE_CHANNELS:
        ch_id = channel['id']
        ch_name = channel['name']
        ch_logo = channel.get('logo', ADDON_ICON)
        genre_id = channel.get('genre_id')
        offset = channel.get('offset', 0)
        country = channel.get('country', '')
        
        # Get movie for this slot
        movie_info = _get_movie_for_slot(genre_id, offset, hours_ahead)
        if not movie_info:
            continue
        
        movie_title = movie_info.get('title', 'Unknown')
        movie_poster = movie_info.get('poster', '')
        movie_year = movie_info.get('year', '')
        tmdb_id = movie_info.get('tmdb_id', '')
        
        label = f'[B]{ch_name}[/B] [{country}] - {movie_title}'
        if movie_year:
            label += f' ({movie_year})'
        
        li = xbmcgui.ListItem(label)
        li.setArt({
            'icon': ch_logo,
            'thumb': movie_poster if movie_poster else ch_logo,
            'poster': movie_poster if movie_poster else ch_logo,
            'fanart': movie_poster if movie_poster else ADDON_FANART
        })
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(movie_title)
        info_tag.setPlot(f'Playing on {ch_name} at {slot_display}')
        info_tag.setMediaType('movie')
        
        url = build_url({
            'mode': 'get_sources',
            'title': movie_title,
            'year': movie_year,
            'media_type': 'movie',
            'tmdb_id': tmdb_id
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE)


def _get_movie_for_slot(genre_id, offset, hours_ahead):
    """Get the movie playing at a specific time slot for a channel"""
    global _TMDB_MOVIES_CACHE
    
    now = datetime.datetime.now()
    target_time = now + datetime.timedelta(hours=hours_ahead)
    hour_block = target_time.hour // 2
    
    # Get movie list based on genre
    cache_key = f'genre_{genre_id}' if genre_id else 'all'
    
    if cache_key not in _TMDB_MOVIES_CACHE:
        params = {'page': 1, 'sort_by': 'popularity.desc'}
        if genre_id:
            params['with_genres'] = genre_id
        
        data = _tmdb_get('/discover/movie', params)
        movies = []
        if data and data.get('results'):
            for m in data['results'][:20]:
                movies.append({
                    'title': m.get('title', 'Unknown'),
                    'poster': f"{TMDB_IMG}/w500{m.get('poster_path', '')}" if m.get('poster_path') else '',
                    'year': (m.get('release_date') or '')[:4],
                    'tmdb_id': m.get('id', '')
                })
        _TMDB_MOVIES_CACHE[cache_key] = movies
    
    movies = _TMDB_MOVIES_CACHE.get(cache_key, [])
    if not movies:
        return None
    
    # Calculate index based on time and offset
    idx = (hour_block + offset) % len(movies)
    return movies[idx]


def movie_channels_category(category):
    """Show channels in a category with EPG info and channel logos"""
    if category == 'all':
        channels = MOVIE_CHANNELS
    else:
        channels = [ch for ch in MOVIE_CHANNELS if ch.get('category') == category]
    
    if not channels:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No channels found', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    # Fetch EPG data with unique movies per channel
    epg_data = _fetch_epg_data()
    
    for channel in channels:
        ch_name = channel['name']
        ch_id = channel['id']
        epg_id = channel.get('epg_id', '')
        country = channel.get('country', '')
        ch_logo = channel.get('logo', ADDON_ICON)
        
        # Get current/next program from EPG
        current_program = ''
        next_program = ''
        current_poster = ''
        
        if epg_data and ch_id in epg_data:
            prog = epg_data[ch_id]
            current_program = prog.get('current', {}).get('title', '')
            current_time = prog.get('current', {}).get('time', '')
            next_program = prog.get('next', {}).get('title', '')
            current_poster = prog.get('current', {}).get('poster', '')
        
        label = f'[B]{ch_name}[/B] [{country}]'
        if current_program:
            label += f' - {current_program}'
        
        li = xbmcgui.ListItem(label)
        
        # Use channel logo, with movie poster as fanart if available
        icon_url = ch_logo if ch_logo else ADDON_ICON
        fanart_url = current_poster if current_poster else ADDON_FANART
        
        li.setArt({
            'icon': icon_url,
            'thumb': icon_url,
            'poster': icon_url,
            'fanart': fanart_url
        })
        
        # Add info
        plot = f'Live Movie Channel: {ch_name}\nCountry: {country}'
        if current_program:
            plot += f'\n\nNow Playing: {current_program}'
        if next_program:
            plot += f'\nUp Next: {next_program}'
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(ch_name)
        info_tag.setPlot(plot)
        info_tag.setMediaType('video')
        
        url = build_url({
            'mode': 'play_movie_channel',
            'channel_id': ch_id,
            'channel_name': ch_name,
            'current_program': current_program
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def _fetch_epg_data():
    """Fetch EPG data with unique movies for each channel from TMDB"""
    global _EPG_CACHE, _EPG_CACHE_TIME, _TMDB_MOVIES_CACHE
    
    # Return cached data if fresh (30 minutes)
    if _EPG_CACHE and (time.time() - _EPG_CACHE_TIME) < 1800:
        return _EPG_CACHE
    
    epg_data = {}
    now = datetime.datetime.now()
    
    # Fetch movies from TMDB for EPG - one request per genre to get variety
    def _get_tmdb_movies_by_genre(genre_id=None):
        """Get movies from TMDB, optionally filtered by genre"""
        cache_key = f'genre_{genre_id}' if genre_id else 'all'
        if cache_key in _TMDB_MOVIES_CACHE:
            return _TMDB_MOVIES_CACHE[cache_key]
        
        params = {'page': 1, 'sort_by': 'popularity.desc'}
        if genre_id:
            params['with_genres'] = genre_id
        
        data = _tmdb_get('/discover/movie', params)
        movies = []
        if data and data.get('results'):
            for m in data['results'][:20]:  # Get top 20
                movies.append({
                    'title': m.get('title', 'Unknown'),
                    'poster': f"{TMDB_IMG}/w500{m.get('poster_path', '')}" if m.get('poster_path') else '',
                    'year': (m.get('release_date') or '')[:4],
                    'tmdb_id': m.get('id', '')
                })
        
        _TMDB_MOVIES_CACHE[cache_key] = movies
        return movies
    
    # Also get "Now Playing" movies for premium channels
    now_playing = _tmdb_get('/movie/now_playing', {'page': 1})
    now_playing_movies = []
    if now_playing and now_playing.get('results'):
        for m in now_playing['results'][:20]:
            now_playing_movies.append({
                'title': m.get('title', 'Unknown'),
                'poster': f"{TMDB_IMG}/w500{m.get('poster_path', '')}" if m.get('poster_path') else '',
                'year': (m.get('release_date') or '')[:4],
                'tmdb_id': m.get('id', '')
            })
    
    # Process each channel with unique movie selection
    for i, channel in enumerate(MOVIE_CHANNELS):
        ch_id = channel['id']
        ch_name = channel['name']
        genre_id = channel.get('genre_id')
        offset = channel.get('offset', i)  # Use offset or index for variety
        
        # Get appropriate movie list
        if genre_id:
            movies = _get_tmdb_movies_by_genre(genre_id)
        elif 'Premiere' in ch_name or 'Premier' in ch_name:
            movies = now_playing_movies
        else:
            movies = _get_tmdb_movies_by_genre(None)  # All popular
        
        if not movies:
            continue
        
        # Calculate unique index for this channel based on time and offset
        # Each channel gets different movies by using offset
        hour_block = now.hour // 2  # 2-hour movie blocks
        base_idx = (hour_block + offset) % len(movies)
        next_idx = (base_idx + 1) % len(movies)
        
        current_movie = movies[base_idx]
        next_movie = movies[next_idx]
        
        # Calculate approximate times
        block_start_hour = (now.hour // 2) * 2
        
        epg_data[ch_id] = {
            'current': {
                'title': current_movie['title'],
                'time': f'{block_start_hour:02d}:00',
                'poster': current_movie['poster'],
                'year': current_movie['year'],
                'tmdb_id': current_movie['tmdb_id']
            },
            'next': {
                'title': next_movie['title'],
                'time': f'{(block_start_hour + 2) % 24:02d}:00',
                'poster': next_movie['poster']
            }
        }
    
    _EPG_CACHE = epg_data
    _EPG_CACHE_TIME = time.time()
    return epg_data


def _get_channel_movies(category):
    """Get sample movie titles for a channel category (fallback)"""
    movies = {
        'Sky Cinema': [
            'Oppenheimer', 'Barbie', 'Killers of the Flower Moon', 'Napoleon',
            'The Holdovers', 'Poor Things', 'Maestro', 'Ferrari',
            'Wonka', 'Aquaman 2', 'Migration', 'Anyone But You'
        ],
        'Free UK': [
            'Gladiator', 'The Dark Knight', 'Inception', 'The Matrix',
            'Forrest Gump', 'The Shawshank Redemption', 'Pulp Fiction',
            'Fight Club', 'The Godfather', 'Goodfellas', 'Scarface'
        ],
        'Sony': [
            'Spider-Man: No Way Home', 'Ghostbusters: Afterlife', 'Venom',
            'Bad Boys for Life', 'Jumanji: The Next Level', 'Men in Black',
            'Hotel Transylvania', 'Peter Rabbit', 'Uncharted'
        ],
        'US Movies': [
            'The Godfather Part II', 'Casablanca', 'Citizen Kane',
            'Gone with the Wind', 'Singin in the Rain', 'Its a Wonderful Life',
            'The Wizard of Oz', 'Psycho', 'Vertigo', 'Rear Window'
        ],
        'European': [
            'Amelie', 'The Intouchables', 'Cinema Paradiso', 'La Vita e Bella',
            'Das Boot', 'Run Lola Run', 'Oldboy', 'City of God'
        ],
        'FAST': [
            'Die Hard', 'Lethal Weapon', 'Terminator 2', 'Aliens',
            'Predator', 'RoboCop', 'Total Recall', 'The Running Man',
            'Commando', 'Rambo', 'Rocky', 'First Blood'
        ]
    }
    return movies.get(category, movies['Free UK'])


def play_movie_channel(channel_id, channel_name, current_program=''):
    """Play a movie channel - let user choose Live or From Beginning"""
    # Find channel info
    channel = None
    for ch in MOVIE_CHANNELS:
        if ch['id'] == channel_id:
            channel = ch
            break
    
    if not channel:
        xbmcgui.Dialog().notification(ADDON_NAME, 'Channel not found', ADDON_ICON)
        return
    
    # Ask user: Watch Live or Start from Beginning
    choices = ['Watch Live (Current Broadcast)', 'Start from Beginning of Current Movie']
    if current_program:
        choices[0] = f'Watch Live: {current_program}'
        choices[1] = f'Start from Beginning: {current_program}'
    
    selection = xbmcgui.Dialog().select(f'{channel_name}', choices)
    
    if selection < 0:
        return
    
    from_beginning = (selection == 1)
    
    # Progress dialog
    progress = xbmcgui.DialogProgress()
    progress.create('SALTS', f'Finding stream for {channel_name}...')
    
    # Try to find a stream for the current movie
    if current_program:
        progress.update(30, f'Searching for: {current_program}')
        
        # Search TMDB for the movie
        search_data = _tmdb_get('/search/movie', {'query': current_program})
        
        if search_data and search_data.get('results'):
            movie = search_data['results'][0]
            title = movie.get('title', current_program)
            year = (movie.get('release_date') or '')[:4]
            tmdb_id = movie.get('id', '')
            
            progress.update(60, f'Found: {title} ({year})')
            progress.close()
            
            # Get sources and play
            get_sources(title, year, '', '', 'movie', tmdb_id)
            return
    
    progress.close()
    
    # Fallback: Search for channel name or generic movie stream
    xbmcgui.Dialog().notification(
        ADDON_NAME,
        'Live stream not available. Searching for movie...',
        ADDON_ICON,
        3000
    )
    
    # Get a random movie from the channel category
    movies = _get_channel_movies(channel.get('category', 'Free UK'))
    if movies:
        random_movie = random.choice(movies)
        search_data = _tmdb_get('/search/movie', {'query': random_movie})
        if search_data and search_data.get('results'):
            movie = search_data['results'][0]
            get_sources(movie.get('title', random_movie), 
                       (movie.get('release_date') or '')[:4],
                       '', '', 'movie', movie.get('id', ''))


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
        {'title': '[B]AI Search Movies[/B]', 'mode': 'ai_search', 'media_filter': 'movie'},
        {'title': '[B]AI Search TV Shows[/B]', 'mode': 'ai_search', 'media_filter': 'tv'},
        {'title': '[B]AI Search All[/B]', 'mode': 'ai_search', 'media_filter': 'all'},
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
            label += f'  {reason}'
        
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
                label += f'  Trakt: {trakt_r[0]}'
            
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
                label += f'  Trakt: {trakt_r_s[0]}'
            
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
    
    # ── CONCURRENT SCRAPING ("superfast") ─────────────────────────────
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def _run_scraper(scraper_cls):
        """Execute a single scraper. Returns (name, results, was_active)."""
        try:
            scraper = scraper_cls()
            scraper_name = scraper.get_name()
            if not scraper.is_enabled():
                return scraper_name, [], False
            is_free_scraper = isinstance(scraper, FreeStreamScraper)

            # Check for Stremio-based scrapers
            is_stremio = False
            try:
                from scrapers.stremio_scrapers import StremioBaseScraper
                is_stremio = isinstance(scraper, StremioBaseScraper)
            except ImportError:
                pass

            # Any scraper that exposes `is_free = True` (e.g. Bones direct-stream
            # provider) is allowed to run without a configured debrid service.
            scraper_is_free = bool(getattr(scraper, 'is_free', False))

            if (not debrid_enabled
                    and not is_free_scraper
                    and not scraper_is_free
                    and not (is_stremio and getattr(scraper, 'is_free', False))):
                return scraper_name, [], False

            if is_free_scraper or is_stremio:
                results = scraper.search(
                    query, media_type,
                    tmdb_id=tmdb_id,
                    title=title, year=year,
                    season=season, episode=episode
                )
            else:
                # Try the rich signature first (Bones + any future kwarg-aware
                # scrapers), fall back to minimal signature for legacy scrapers.
                try:
                    results = scraper.search(
                        query, media_type,
                        tmdb_id=tmdb_id,
                        title=title, year=year,
                        season=season, episode=episode,
                    )
                except TypeError:
                    results = scraper.search(query, media_type)

            results = results or []
            for r in results:
                r['scraper'] = scraper_name
            return scraper_name, results, True
        except Exception as e:
            # Elevate to WARNING so scraper failures are diagnosable from kodi.log
            log_utils.log(f'Scraper {getattr(scraper_cls, "NAME", scraper_cls)} error: {e}', xbmc.LOGWARNING)
            return getattr(scraper_cls, 'NAME', str(scraper_cls)), [], False
    
    SCRAPER_TIMEOUT = 30  # seconds - abandon any scraper slower than this
    futures = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        for scraper_cls in scrapers:
            futures[executor.submit(_run_scraper, scraper_cls)] = scraper_cls
        
        completed = 0
        try:
            for future in as_completed(futures, timeout=SCRAPER_TIMEOUT):
                if progress.iscanceled():
                    break
                try:
                    name, results, was_active = future.result(timeout=2)
                except Exception:
                    completed += 1
                    continue
                if was_active:
                    scraper_count += 1
                for r in results:
                    all_sources.append(r)
                    sources_found += 1
                    if r.get('direct'):
                        free_count += 1
                completed += 1
                percent = int((completed / total) * 100)
                progress.update(percent, f'Scraped: {name}\nScrapers: {scraper_count}/{total} | Sources: {sources_found} | Free: {free_count}')
        except Exception:
            log_utils.log(f'Scraper timeout hit after {SCRAPER_TIMEOUT}s - {completed}/{total} completed', xbmc.LOGINFO)
    
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
            parts.append('[B]CACHED[/B]')
        elif is_free:
            parts.append('[B]FREE[/B]')
        
        parts.append(f'{scraper}')
        
        if seeds and not is_free:
            sc = 'FF00EE00' if seeds >= 100 else ('FFCCCC00' if seeds >= 10 else 'FFEE6600')
            parts.append(f'[COLOR {sc}]S:{seeds}[/COLOR]')
        
        if size:
            parts.append(f'{size}')
        
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
            # Try Bones custom resolver first (Streamtape mirrors, LuluVid)
            _bones_hosts = (
                'streamtape.com', 'streamtape.to', 'streamtape.net',
                'streamtape.cc', 'streamta.pe', 'streamtape.xyz',
                'streamtape.site', 'streamtape.online',
                'streamadblocker.xyz', 'stape.fun', 'shavetape.cash',
                'luluvid.com', 'luluvdo.com',
            )
            if any(host in url.lower() for host in _bones_hosts):
                try:
                    from scrapers.bones_resolver import resolve as bones_resolve
                    progress = xbmcgui.DialogProgress()
                    progress.create('SALTS', 'Resolving Bones link...')
                    stream_url = bones_resolve(url)
                    progress.close()
                    if stream_url:
                        log_utils.log(f'Resolved via Bones resolver: {stream_url}', xbmc.LOGINFO)
                except Exception as e:
                    log_utils.log(f'Bones resolver error: {e}', xbmc.LOGWARNING)
                # Zeus Resolvers fallback - SCOPED to Bones scraper hosts only
                # (debrid-free resolver for Streamtape / DDownloads; ddownloads
                # entries are still gated by the _bones_hosts tuple above)
                if not stream_url:
                    try:
                        from salts_lib.zeus_hook import try_zeus
                        zeus_url = try_zeus(url)
                        if zeus_url:
                            stream_url = zeus_url
                            log_utils.log(f'Resolved via Zeus Resolvers: {stream_url}', xbmc.LOGINFO)
                    except Exception as e:
                        log_utils.log(f'Zeus hook error: {e}', xbmc.LOGWARNING)
            # Fallback to ResolveURL
            if not stream_url:
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
    _monitor_playback(player, media_type, show_title, year, season, episode, tmdb_id, title=title)


def _monitor_playback(player, media_type, show_title, year, season, episode, tmdb_id='', title=''):
    """Monitor playback for skip intro, next episode, Trakt scrobbling, and pre-emptive scraping"""
    skip_intro_shown = False
    next_ep_shown = False
    preemptive_done = False
    skip_intro_seconds = int(ADDON.getSetting('skip_intro_duration') or 90)
    next_ep_enabled = ADDON.getSetting('next_episode_enabled') == 'true'
    skip_intro_enabled = ADDON.getSetting('skip_intro_enabled') == 'true'
    preemptive_enabled = ADDON.getSetting('preemptive_scrape') == 'true'
    
    # Trakt scrobbling setup
    trakt_enabled = xbmcaddon.Addon().getSetting('trakt_enabled') == 'true'
    trakt_scrobble_started = False
    trakt_obj = None
    trakt_item_id = None
    trakt_item_type = None
    imdb_id = ''
    
    if trakt_enabled:
        try:
            from salts_lib.trakt_api import TraktAPI
            trakt_obj = TraktAPI()
            if trakt_obj.is_authorized() and tmdb_id:
                mt = 'movie' if media_type == 'movie' else 'show'
                results = trakt_obj._call_api(f'/search/tmdb/{tmdb_id}?type={mt}', cache_limit=24)
                if results and isinstance(results, list) and len(results) > 0:
                    trakt_item_id = results[0].get(mt, {}).get('ids', {}).get('trakt')
                    imdb_id = results[0].get(mt, {}).get('ids', {}).get('imdb') or ''
                    trakt_item_type = 'movies' if media_type == 'movie' else 'episodes'
                    
                    if trakt_item_type == 'episodes' and season and episode:
                        show_trakt = results[0].get('show', {}).get('ids', {}).get('trakt')
                        if not show_trakt:
                            show_trakt = trakt_item_id
                        if show_trakt:
                            ep_data = trakt_obj._call_api(
                                f'/shows/{show_trakt}/seasons/{int(season)}/episodes/{int(episode)}',
                                cache_limit=24
                            )
                            if ep_data and isinstance(ep_data, dict):
                                trakt_item_id = ep_data.get('ids', {}).get('trakt', trakt_item_id)
                                imdb_id = ep_data.get('ids', {}).get('imdb') or imdb_id
        except Exception as e:
            log_utils.log(f'Trakt scrobble init error: {e}', xbmc.LOGDEBUG)
    
    # PunchPlay scrobbling setup (parallel to Trakt)
    pp_enabled = xbmcaddon.Addon().getSetting('punchplay_enabled') == 'true'
    pp_obj = None
    pp_started = False
    pp_media_type = 'episode' if media_type == 'tvshow' else 'movie'
    pp_title = show_title or title or ''
    if pp_enabled:
        try:
            from salts_lib.punchplay_api import PunchPlayAPI
            pp_obj = PunchPlayAPI()
            if not pp_obj.is_authorized():
                pp_obj = None
        except Exception as e:
            log_utils.log(f'PunchPlay init error: {e}', xbmc.LOGDEBUG)
            pp_obj = None
    
    total_time = 0
    
    while player.isPlaying():
        try:
            current_time = player.getTime()
            if total_time == 0:
                try:
                    total_time = player.getTotalTime()
                except Exception:
                    pass
            
            progress_pct = (current_time / total_time * 100) if total_time > 0 else 0
            
            # Trakt: start scrobble after 2% of playback
            if (trakt_obj and trakt_item_id and not trakt_scrobble_started
                    and progress_pct > 2):
                trakt_scrobble_started = True
                try:
                    trakt_obj.scrobble_start(trakt_item_type, trakt_item_id, progress_pct)
                    log_utils.log(f'Trakt scrobble started: {trakt_item_type}/{trakt_item_id}', xbmc.LOGINFO)
                except Exception as e:
                    log_utils.log(f'Trakt scrobble start error: {e}', xbmc.LOGDEBUG)
            
            # PunchPlay: start scrobble after 2% of playback (parallel to Trakt)
            if pp_obj and not pp_started and progress_pct > 2:
                pp_started = True
                try:
                    pp_obj.scrobble_start(
                        pp_media_type, pp_title, year, tmdb_id, imdb_id,
                        progress=progress_pct / 100.0,
                        duration_seconds=total_time,
                        position_seconds=current_time,
                        season=season if pp_media_type == 'episode' else None,
                        episode=episode if pp_media_type == 'episode' else None,
                    )
                    log_utils.log(f'PunchPlay scrobble started: {pp_media_type}/{pp_title}', xbmc.LOGINFO)
                except Exception as e:
                    log_utils.log(f'PunchPlay scrobble start error: {e}', xbmc.LOGDEBUG)
            
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
                if progress_pct > 75:
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
                        # Scrobble stop before switching
                        if trakt_obj and trakt_item_id and trakt_scrobble_started:
                            try:
                                trakt_obj.scrobble_stop(trakt_item_type, trakt_item_id, progress_pct)
                            except Exception:
                                pass
                        if pp_obj and pp_started:
                            try:
                                pp_obj.scrobble_stop(
                                    pp_media_type, pp_title, year, tmdb_id, imdb_id,
                                    progress=progress_pct / 100.0,
                                    duration_seconds=total_time,
                                    position_seconds=current_time,
                                    season=season if pp_media_type == 'episode' else None,
                                    episode=episode if pp_media_type == 'episode' else None,
                                    watched=(progress_pct > 80),
                                )
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
    
    # Playback ended - Trakt scrobble stop + mark watched
    if trakt_obj and trakt_item_id and trakt_scrobble_started:
        try:
            final_pct = progress_pct if progress_pct > 0 else 100
            trakt_obj.scrobble_stop(trakt_item_type, trakt_item_id, final_pct)
            log_utils.log(f'Trakt scrobble stopped at {final_pct:.0f}%', xbmc.LOGINFO)
            
            # If watched > 80%, explicitly mark as watched
            if final_pct > 80:
                try:
                    if trakt_item_type == 'movies':
                        trakt_obj.mark_watched('movies', [{'ids': {'trakt': trakt_item_id}}])
                    else:
                        trakt_obj.mark_watched('episodes', [{'ids': {'trakt': trakt_item_id}}])
                    log_utils.log(f'Trakt: marked as watched ({trakt_item_type}/{trakt_item_id})', xbmc.LOGINFO)
                except Exception as e:
                    log_utils.log(f'Trakt mark watched error: {e}', xbmc.LOGDEBUG)
        except Exception as e:
            log_utils.log(f'Trakt scrobble stop error: {e}', xbmc.LOGDEBUG)

    # Playback ended - PunchPlay scrobble stop + mark watched (parallel to Trakt)
    if pp_obj and pp_started:
        try:
            final_pct = progress_pct if progress_pct > 0 else 100
            pp_watched_thresh = xbmcaddon.Addon().getSetting('punchplay_mark_watched') == 'true'
            pp_obj.scrobble_stop(
                pp_media_type, pp_title, year, tmdb_id, imdb_id,
                progress=final_pct / 100.0,
                duration_seconds=total_time,
                position_seconds=int((final_pct / 100.0) * (total_time or 0)),
                season=season if pp_media_type == 'episode' else None,
                episode=episode if pp_media_type == 'episode' else None,
                watched=(pp_watched_thresh and final_pct > 80),
            )
            log_utils.log(f'PunchPlay scrobble stopped at {final_pct:.0f}%', xbmc.LOGINFO)
        except Exception as e:
            log_utils.log(f'PunchPlay scrobble stop error: {e}', xbmc.LOGDEBUG)


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
            
            status = 'ON' if enabled else 'OFF'
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
            status = 'Authorized'
        elif enabled:
            status = 'Not Authorized'
        else:
            status = 'Disabled'
        
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
        
        label = f'{name} - {quality} / {autoplay}'
        
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
        status = 'ON' if enabled else 'OFF'
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
    
    is_auth = trakt.is_authorized()
    
    if is_auth:
        auth_status = 'Authorized'
        auth_action = 'Re-Authorize Trakt'
    else:
        auth_status = 'Not Authorized'
        auth_action = 'Authorize Trakt'
    
    items = [
        {'title': f'Status: {auth_status}', 'mode': 'trakt_status'},
        {'title': auth_action, 'mode': 'trakt_auth'},
    ]
    
    # Add revoke option if authorized
    if is_auth:
        items.append({'title': 'Revoke Authorization', 'mode': 'trakt_revoke'})
    
    items.extend([
        {'title': 'My Watchlist (Movies)', 'mode': 'trakt_watchlist', 'media_type': 'movies'},
        {'title': 'My Watchlist (TV Shows)', 'mode': 'trakt_watchlist', 'media_type': 'shows'},
        {'title': 'My Collection (Movies)', 'mode': 'trakt_collection', 'media_type': 'movies'},
        {'title': 'My Collection (TV Shows)', 'mode': 'trakt_collection', 'media_type': 'shows'},
        {'title': 'Trending Movies', 'mode': 'trakt_trending', 'media_type': 'movies'},
        {'title': 'Trending TV Shows', 'mode': 'trakt_trending', 'media_type': 'shows'},
        {'title': 'Popular Movies', 'mode': 'trakt_popular', 'media_type': 'movies'},
        {'title': 'Popular TV Shows', 'mode': 'trakt_popular', 'media_type': 'shows'},
        {'title': 'My Lists', 'mode': 'trakt_lists'},
    ])
    
    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url(item)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_status():
    """Show Trakt authorization status"""
    from salts_lib.trakt_api import TraktAPI
    trakt = TraktAPI()
    
    if trakt.is_authorized():
        try:
            user_info = trakt.get_user_settings()
            username = user_info.get('user', {}).get('username', 'Unknown')
            xbmcgui.Dialog().ok('Trakt Status', f'Authorized as: {username}')
        except Exception:
            xbmcgui.Dialog().ok('Trakt Status', 'Authorized (unable to fetch username)')
    else:
        xbmcgui.Dialog().ok('Trakt Status', 'Not Authorized\n\nSelect "Authorize Trakt" to connect your account.')

def trakt_auth():
    """Authorize Trakt"""
    from salts_lib.trakt_api import TraktAPI
    trakt = TraktAPI()
    trakt.authorize()
    xbmc.executebuiltin('Container.Refresh')

def trakt_revoke():
    """Revoke Trakt authorization"""
    from salts_lib.trakt_api import TraktAPI
    
    confirm = xbmcgui.Dialog().yesno(
        'Revoke Trakt',
        'Are you sure you want to revoke Trakt authorization?\n\nYou will need to re-authorize to use Trakt features.'
    )
    
    if confirm:
        trakt = TraktAPI()
        trakt.clear_authorization()
        xbmcgui.Dialog().notification('Trakt', 'Authorization revoked', xbmcgui.NOTIFICATION_INFO)
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
    """Helper to display Trakt items with TMDB posters and watched overlay.
    
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
    
    # Fetch watched list from Trakt for overlay
    watched_set = set()
    try:
        from salts_lib.trakt_api import TraktAPI
        trakt_w = TraktAPI()
        if trakt_w.is_authorized():
            wt = media_type if media_type in ('movies', 'shows') else 'movies'
            watched_items = trakt_w.get_watched(wt)
            if watched_items and isinstance(watched_items, list):
                for wi in watched_items:
                    w_key = 'movie' if wt == 'movies' else 'show'
                    w_data = wi.get(w_key, {})
                    w_ids = w_data.get('ids', {})
                    if w_ids.get('trakt'):
                        watched_set.add(w_ids['trakt'])
    except Exception as e:
        log_utils.log(f'Trakt watched fetch error: {e}', xbmc.LOGDEBUG)
    
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
            
            ids = data.get('ids', {})
            tmdb_id = str(ids.get('tmdb', '')) if ids else ''
            trakt_id = ids.get('trakt', 0) if ids else 0
            
            # Watched indicator
            is_watched = trakt_id in watched_set
            watched_tag = 'W ' if is_watched else ''
            label = f'{watched_tag}{title} ({year})' if year else f'{watched_tag}{title}'
            
            # Fetch TMDB poster/fanart
            poster_url = ADDON_ICON
            backdrop_url = ADDON_FANART
            overview = data.get('overview', '')
            rating = 0
            
            if tmdb_id:
                try:
                    search_type = 'movie' if media_type == 'movies' else 'tv'
                    tmdb_data = _tmdb_get(f'/{search_type}/{tmdb_id}')
                    if tmdb_data:
                        poster = tmdb_data.get('poster_path', '')
                        backdrop = tmdb_data.get('backdrop_path', '')
                        if poster:
                            poster_url = f'{TMDB_IMG}/w500{poster}'
                        if backdrop:
                            backdrop_url = f'{TMDB_IMG}/original{backdrop}'
                        overview = tmdb_data.get('overview', overview)
                        rating = tmdb_data.get('vote_average', 0)
                except Exception:
                    pass
            
            li = xbmcgui.ListItem(label)
            li.setArt({
                'icon': poster_url, 'thumb': poster_url,
                'poster': poster_url, 'fanart': backdrop_url
            })
            
            info_tag = li.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setYear(int(year) if year else 0)
            info_tag.setPlot(overview)
            if rating:
                info_tag.setRating(float(rating))
            info_tag.setMediaType('movie' if media_type == 'movies' else 'tvshow')
            if is_watched:
                info_tag.setPlaycount(1)
            
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



# ==================== PunchPlay Functions ====================

def punchplay_menu():
    """PunchPlay.tv menu (Trakt alternative - scrobbling only)"""
    from salts_lib.punchplay_api import PunchPlayAPI
    pp = PunchPlayAPI()
    is_auth = pp.is_authorized()
    enabled = xbmcaddon.Addon().getSetting('punchplay_enabled') == 'true'

    status = 'Authorized' if is_auth else 'Not Authorized'
    action_label = 'Re-Authorize PunchPlay' if is_auth else 'Authorize PunchPlay'
    toggle_label = 'Disable PunchPlay Scrobbling' if enabled else 'Enable PunchPlay Scrobbling'

    items = [
        {'title': '[COLOR grey][BETA] PunchPlay is in beta - rough edges expected[/COLOR]', 'mode': 'punchplay_menu'},
        {'title': f'Status: {status}', 'mode': 'punchplay_status'},
        {'title': f'Scrobbling: {"ON" if enabled else "OFF"} (toggle)', 'mode': 'punchplay_toggle'},
        {'title': action_label, 'mode': 'punchplay_auth'},
    ]
    if is_auth:
        items.append({'title': 'Revoke Authorization', 'mode': 'punchplay_revoke'})
    items.append({'title': 'Open PunchPlay website', 'mode': 'punchplay_open_site'})

    # Fire the one-shot beta toast the first time a user opens the menu directly
    # (covers people who land here before flipping the Enable toggle).
    try:
        _punchplay_beta_notice()
    except Exception:
        pass

    for item in items:
        li = xbmcgui.ListItem(item['title'])
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        url = build_url({'mode': item['mode']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE)


def punchplay_status():
    """Show PunchPlay authorization status"""
    from salts_lib.punchplay_api import PunchPlayAPI
    pp = PunchPlayAPI()
    if pp.is_authorized():
        me = None
        try:
            me = pp.get_me()
        except Exception:
            pass
        username = ''
        if isinstance(me, dict):
            username = me.get('username') or me.get('name') or ''
        if username:
            xbmcgui.Dialog().ok('PunchPlay Status', f'Authorized as: {username}')
        else:
            xbmcgui.Dialog().ok('PunchPlay Status', 'Authorized.')
    else:
        xbmcgui.Dialog().ok(
            'PunchPlay Status',
            'Not Authorized.\n\nOpen the PunchPlay menu and select "Authorize PunchPlay".'
        )


def punchplay_auth():
    """Start PunchPlay device-code authorization"""
    from salts_lib.punchplay_api import PunchPlayAPI
    pp = PunchPlayAPI()
    pp.authorize()
    xbmc.executebuiltin('Container.Refresh')


def punchplay_revoke():
    """Revoke PunchPlay authorization"""
    from salts_lib.punchplay_api import PunchPlayAPI
    confirm = xbmcgui.Dialog().yesno(
        'Revoke PunchPlay',
        'Are you sure you want to revoke PunchPlay authorization?'
    )
    if confirm:
        pp = PunchPlayAPI()
        pp.clear_authorization()
        xbmcgui.Dialog().notification('PunchPlay', 'Authorization revoked', xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')


def punchplay_toggle():
    """Flip the punchplay_enabled setting"""
    addon = xbmcaddon.Addon()
    current = addon.getSetting('punchplay_enabled') == 'true'
    addon.setSetting('punchplay_enabled', 'false' if current else 'true')
    new_state = 'disabled' if current else 'enabled'
    xbmcgui.Dialog().notification('PunchPlay', f'Scrobbling {new_state}', ADDON_ICON)
    xbmc.executebuiltin('Container.Refresh')


def punchplay_open_site():
    """Show the PunchPlay web URL"""
    xbmcgui.Dialog().ok(
        'PunchPlay',
        'Visit https://punchplay.tv on any browser to manage your profile,\n'
        'lists, and watch history.'
    )


def _punchplay_mark_watched(media_type, tmdb_id, imdb_id='', title='', year='',
                             season=None, episode=None):
    """Helper: mirror a Trakt mark_watched action onto PunchPlay.

    Called from places in default.py where SALTS explicitly marks an item
    watched on Trakt. Honors the 'punchplay_mirror_trakt' setting.
    """
    try:
        addon = xbmcaddon.Addon()
        if addon.getSetting('punchplay_enabled') != 'true':
            return
        if addon.getSetting('punchplay_mirror_trakt') != 'true':
            return
        from salts_lib.punchplay_api import PunchPlayAPI
        pp = PunchPlayAPI()
        if not pp.is_authorized():
            return
        pp.mark_watched(
            'episode' if media_type in ('tvshow', 'episode', 'episodes', 'shows') else 'movie',
            title, year, tmdb_id, imdb_id,
            season=season, episode=episode,
        )
    except Exception as e:
        log_utils.log(f'PunchPlay mirror mark_watched error: {e}', xbmc.LOGDEBUG)



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
        {'title': '[B]24/7 AI Vibe[/B] - Describe a mood, AI builds your marathon', 'mode': 'channel_ai_vibe'},
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
        
        result = _channel_play_item(player, stream_url, f'{title} ({year})')
        if result == 'stop' or result == 'abort':
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
        
        result = _channel_play_item(player, stream_url, f'{name} - S{s_num:02d}E{ep_num:02d}')
        if result == 'stop' or result == 'abort':
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
        result = _channel_play_item(player, stream_url, f'{title} ({year})',
                                     art={'icon': poster_url, 'thumb': poster_url, 'fanart': ADDON_FANART})
        if result == 'stop' or result == 'abort':
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
        result = _channel_play_item(player, stream_url, f'{title} ({year})',
                                     art={'icon': poster_url, 'thumb': poster_url, 'fanart': ADDON_FANART})
        if result == 'stop' or result == 'abort':
            break
    
    xbmcgui.Dialog().notification(ADDON_NAME, 'AI Vibe: Marathon complete!', ADDON_ICON)


def _channel_wait_for_playback(player):
    """Wait for playback to end. Returns True if user stopped manually, False if ended naturally."""
    total_time = 0
    try:
        total_time = player.getTotalTime()
    except Exception:
        pass
    
    while player.isPlaying():
        xbmc.sleep(2000)
        if xbmc.Monitor().abortRequested():
            return True
    
    # Check if it ended naturally (reached near the end) or user stopped
    if total_time > 0:
        try:
            last_pos = player.getTime()
        except Exception:
            last_pos = 0
        # If we got past 85% of the total time, it ended naturally
        if last_pos >= total_time * 0.85:
            return False
    
    # If total_time was 0, we can't tell — but if the stream was playing
    # and stopped, likely user quit. Use a heuristic: was it playing > 60s?
    # For safety, assume user stopped unless we know it ended naturally.
    return True


def _channel_play_item(player, stream_url, label, art=None):
    """Play a single item in 24/7 channel. Returns 'next', 'stop', or 'abort'."""
    if art is None:
        art = {'icon': ADDON_ICON, 'fanart': ADDON_FANART}
    
    li = xbmcgui.ListItem(label, path=stream_url)
    li.setArt(art)
    player.play(stream_url, li)
    
    timeout = 30
    while not player.isPlaying() and timeout > 0:
        xbmc.sleep(500)
        timeout -= 1
    
    if not player.isPlaying():
        return 'next'  # Failed to start, skip to next
    
    user_stopped = _channel_wait_for_playback(player)
    xbmc.sleep(500)
    
    if xbmc.Monitor().abortRequested():
        return 'abort'
    
    if user_stopped:
        return 'stop'
    
    return 'next'


def _channel_get_stream(title, year='', tmdb_id='', season='', episode='', media_type='movie', max_quality='1080p'):
    """Get a stream URL for 24/7 channel playback. Returns URL or None."""
    from scrapers import get_all_scrapers
    from scrapers.freestream_scraper import FreeStreamScraper
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    debrid_enabled = (
        ADDON.getSetting('realdebrid_enabled') == 'true' or
        ADDON.getSetting('premiumize_enabled') == 'true' or
        ADDON.getSetting('alldebrid_enabled') == 'true' or
        ADDON.getSetting('torbox_enabled') == 'true'
    )
    
    quality_cap = {'4K': 4, '2160p': 4, '1080p': 3, 'HD': 3, '720p': 2, '480p': 1, 'SD': 0}
    max_val = quality_cap.get(max_quality, 3)
    
    # Build search query
    if media_type == 'movie':
        query = f'{title} {year}' if year else title
    else:
        query = f'{title} S{int(season):02d}E{int(episode):02d}' if season and episode else title
    
    all_sources = []
    scraper_classes = get_all_scrapers()
    
    def _run_scraper(scraper_cls):
        try:
            scraper = scraper_cls()
            if not scraper.is_enabled():
                return []
            is_free = issubclass(scraper_cls, FreeStreamScraper)
            is_stremio = False
            try:
                from scrapers.stremio_scrapers import StremioBaseScraper
                is_stremio = isinstance(scraper, StremioBaseScraper)
            except ImportError:
                pass
            if not debrid_enabled and not is_free and not (is_stremio and scraper.is_free):
                return []
            if is_free:
                results = scraper.search(
                    query, media_type,
                    tmdb_id=tmdb_id, title=title, year=year,
                    season=season, episode=episode
                )
            elif is_stremio:
                results = scraper.search(
                    query, media_type,
                    tmdb_id=tmdb_id, title=title, year=year,
                    season=season, episode=episode
                )
            else:
                results = scraper.search(query, media_type)
            for r in results:
                r['scraper'] = scraper.get_name()
            return results
        except Exception:
            return []
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(_run_scraper, cls) for cls in scraper_classes]
        try:
            for future in as_completed(futures, timeout=20):
                try:
                    results = future.result(timeout=2)
                    for r in results:
                        q_val = quality_cap.get(r.get('quality', 'SD'), 0)
                        if q_val <= max_val:
                            all_sources.append(r)
                except Exception:
                    continue
        except Exception:
            pass
    
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


def _punchplay_beta_notice():
    """One-shot toast informing the user that PunchPlay is still in beta.

    Fires at most once per install (flag stored in addon_data). Silent no-op
    on any failure so it never blocks menu rendering.
    """
    try:
        flag_file = os.path.join(ADDON_DATA, 'punchplay_beta_seen.json')
        if os.path.exists(flag_file):
            return
        if not os.path.isdir(ADDON_DATA):
            os.makedirs(ADDON_DATA, exist_ok=True)
        xbmcgui.Dialog().notification(
            'PunchPlay (Beta)',
            'PunchPlay integration is in beta - expect rough edges. Continue Watching lights up when the API goes live.',
            ADDON_ICON,
            7000,
            False,
        )
        with open(flag_file, 'w') as f:
            json.dump({'shown_at': time.time(), 'version': ADDON_VERSION}, f)
    except Exception as e:
        log_utils.log(f'PunchPlay beta notice failed: {e}', xbmc.LOGDEBUG)


def _punchplay_playback_available():
    """Cached probe for /api/playback availability.

    Returns True if:
      * PunchPlay is enabled AND authorized, AND
      * The Continue Watching UI is toggled on (default: true), AND
      * GET /api/playback returned HTTP 200 within the last PROBE_TTL seconds.

    Result is cached in addon_data/punchplay_probe.json (60s TTL) so the main
    menu does not issue a network call on every render. Any failure => False,
    which makes the row disappear silently (matches the "hide entirely until
    endpoint responds 200" product decision).
    """
    PROBE_TTL = 60  # seconds
    try:
        addon = xbmcaddon.Addon()
        if addon.getSetting('punchplay_enabled') != 'true':
            return False
        if addon.getSetting('punchplay_continue_watching') == 'false':
            return False
    except Exception:
        return False

    probe_file = os.path.join(ADDON_DATA, 'punchplay_probe.json')
    now = time.time()
    try:
        if os.path.exists(probe_file):
            with open(probe_file, 'r') as f:
                cached = json.load(f)
            if now - float(cached.get('checked_at', 0)) < PROBE_TTL:
                return bool(cached.get('available', False))
    except Exception:
        pass

    available = False
    try:
        from salts_lib.punchplay_api import PunchPlayAPI
        pp = PunchPlayAPI()
        if pp.is_authorized():
            available = pp.is_playback_api_available()
    except Exception as e:
        log_utils.log(f'PunchPlay probe error: {e}', xbmc.LOGDEBUG)

    try:
        if not os.path.isdir(ADDON_DATA):
            os.makedirs(ADDON_DATA, exist_ok=True)
        with open(probe_file, 'w') as f:
            json.dump({'available': available, 'checked_at': now}, f)
    except Exception:
        pass

    return available


def continue_watching_menu():
    """List in-progress items pulled from PunchPlay /api/playback.

    Clicking a movie routes to get_sources (same as search results). Clicking
    an episode routes to get_sources with season/episode params. Position /
    duration are surfaced as ResumeTime / TotalTime so Kodi shows a progress
    bar in the default skin. Actual seek-on-play requires threading position
    through play() - tracked as a follow-up.
    """
    try:
        from salts_lib.punchplay_api import PunchPlayAPI
        pp = PunchPlayAPI()
        items = pp.get_continue_watching(limit=30)
    except Exception as e:
        log_utils.log(f'Continue Watching fetch failed: {e}', xbmc.LOGWARNING)
        items = []

    if not items:
        li = xbmcgui.ListItem('Nothing in progress on PunchPlay')
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'mode': 'punchplay_menu'}), li, isFolder=True)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    for it in items:
        media_type = it.get('type') or 'movie'
        title = it.get('title') or 'Unknown'
        year = str(it.get('year') or '')
        tmdb_id = str(it.get('tmdb_id') or '')
        position = float(it.get('position') or 0)
        duration = float(it.get('duration') or 0)
        pct = int((position / duration) * 100) if duration > 0 else 0

        poster = it.get('poster') or ''
        if poster and not poster.startswith('http'):
            poster = f'{TMDB_IMG}/w500{poster}'
        fanart = it.get('fanart') or ''
        if fanart and not fanart.startswith('http'):
            fanart = f'{TMDB_IMG}/original{fanart}'

        if media_type == 'episode':
            season = it.get('season') or 0
            episode = it.get('episode') or 0
            label = f'{title} - S{int(season):02d}E{int(episode):02d}  [{pct}%]'
            query = {
                'mode': 'get_sources',
                'title': title,
                'year': year,
                'tmdb_id': tmdb_id,
                'season': str(season),
                'episode': str(episode),
                'media_type': 'tv',
            }
        else:
            label = f'{title} ({year})  [{pct}%]' if year else f'{title}  [{pct}%]'
            query = {
                'mode': 'get_sources',
                'title': title,
                'year': year,
                'tmdb_id': tmdb_id,
                'media_type': 'movie',
            }

        li = xbmcgui.ListItem(label)
        art = {'icon': poster or ADDON_ICON, 'thumb': poster or ADDON_ICON,
               'poster': poster or ADDON_ICON, 'fanart': fanart or ADDON_FANART}
        li.setArt(art)

        info = {'title': title, 'plot': it.get('overview') or ''}
        try:
            if year:
                info['year'] = int(year)
        except Exception:
            pass
        if media_type == 'episode':
            info['mediatype'] = 'episode'
            try:
                info['season'] = int(it.get('season') or 0)
                info['episode'] = int(it.get('episode') or 0)
                info['tvshowtitle'] = title
            except Exception:
                pass
        else:
            info['mediatype'] = 'movie'
        try:
            li.setInfo('video', info)
        except Exception:
            pass

        if duration > 0:
            try:
                li.setProperty('TotalTime', str(int(duration)))
                li.setProperty('ResumeTime', str(int(position)))
            except Exception:
                pass

        li.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(HANDLE, build_url(query), li, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
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
    elif mode == 'trakt_status':
        trakt_status()
    elif mode == 'trakt_revoke':
        trakt_revoke()
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
    # PunchPlay modes
    elif mode == 'punchplay_menu':
        punchplay_menu()
    elif mode == 'punchplay_auth':
        punchplay_auth()
    elif mode == 'punchplay_status':
        punchplay_status()
    elif mode == 'punchplay_revoke':
        punchplay_revoke()
    elif mode == 'punchplay_toggle':
        punchplay_toggle()
    elif mode == 'punchplay_open_site':
        punchplay_open_site()
    elif mode == 'continue_watching':
        continue_watching_menu()
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
    # New Episodes & Premieres modes
    elif mode == 'new_episodes_calendar':
        new_episodes_calendar(int(params.get('days_back', 0)))
    elif mode == 'latest_premieres':
        latest_premieres(int(params.get('page', 1)))
    # Movie Channels modes
    elif mode == 'movie_channels_menu':
        movie_channels_menu()
    elif mode == 'movie_channels_category':
        movie_channels_category(params.get('category', 'all'))
    elif mode == 'play_movie_channel':
        play_movie_channel(
            params.get('channel_id', ''),
            params.get('channel_name', ''),
            params.get('current_program', '')
        )
    elif mode == 'force_refresh_epg':
        force_refresh_epg()
    elif mode == 'movie_schedules':
        movie_schedules()
    elif mode == 'movie_schedule_slot':
        movie_schedule_slot(int(params.get('hours_ahead', 0)))
    elif mode == 'returning_shows':
        returning_shows(int(params.get('page', 1)))
    elif mode == 'network_browser':
        network_browser()
    elif mode == 'network_shows':
        network_shows(
            params.get('network_id', ''),
            params.get('network_name', ''),
            int(params.get('page', 1))
        )
    elif mode == 'episode_countdown':
        episode_countdown()
    elif mode == 'add_to_countdown':
        add_to_countdown(
            params.get('tmdb_id', ''),
            params.get('title', '')
        )
    elif mode == 'remove_from_countdown':
        remove_from_countdown(
            params.get('tmdb_id', ''),
            params.get('title', '')
        )
    elif mode == 'buy_beer':
        show_kofi_qr()
    else:
        log_utils.log(f'Unknown mode: {mode}', xbmc.LOGWARNING)
        main_menu()

if __name__ == '__main__':
    params = get_params()
    router(params)
