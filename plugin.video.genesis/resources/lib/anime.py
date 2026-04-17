# -*- coding: utf-8 -*-
"""
Anime & Manga API Module for Test1
Uses Jikan API (unofficial MyAnimeList) + TMDB for metadata
"""
import json
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc
import xbmcvfs
import sys
import os
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus
from datetime import datetime, timedelta

ADDON_ID = 'plugin.video.genesis'
ADDON_PATH = xbmcvfs.translatePath(f'special://home/addons/{ADDON_ID}/')
USER_AGENT = 'Test1 Kodi Addon'

# Jikan API (free, no key required)
JIKAN_BASE = 'https://api.jikan.moe/v4'

# TMDB API for additional metadata
TMDB_BASE = 'https://api.themoviedb.org/3'


def get_addon():
    return xbmcaddon.Addon()


def get_addon_icon():
    icon_path = os.path.join(ADDON_PATH, 'icon.png')
    return icon_path if os.path.exists(icon_path) else 'DefaultAddonVideo.png'


def get_addon_fanart():
    fanart_path = os.path.join(ADDON_PATH, 'fanart.jpg')
    return fanart_path if os.path.exists(fanart_path) else ''


def _http_get(url, timeout=15):
    """HTTP GET request, returns json data or None"""
    try:
        req = Request(url, headers={'User-Agent': USER_AGENT}, method='GET')
        response = urlopen(req, timeout=timeout)
        body = response.read().decode('utf-8')
        return json.loads(body)
    except HTTPError as e:
        xbmc.log(f'Anime API HTTP Error: {e.code} for {url}', xbmc.LOGWARNING)
        return None
    except URLError as e:
        xbmc.log(f'Anime API URL Error: {e.reason}', xbmc.LOGERROR)
        return None
    except Exception as e:
        xbmc.log(f'Anime API Request Error: {e}', xbmc.LOGERROR)
        return None


def _build_url(query):
    return sys.argv[0] + '?' + '&'.join([f'{k}={quote_plus(str(v))}' for k, v in query.items()])


def _menu_item(label, action, is_folder=True, extra_params=None):
    """Create a menu item with addon icon/fanart."""
    q = {'action': action}
    if extra_params:
        q.update(extra_params)
    url = _build_url(q)
    li = xbmcgui.ListItem(label=label)
    icon = get_addon_icon()
    fanart = get_addon_fanart()
    li.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'fanart': fanart})
    return url, li, is_folder


# ══════════════════════════════════════════════════════════════════════════════
# ANIME GENRES
# ══════════════════════════════════════════════════════════════════════════════

ANIME_GENRES = {
    1: 'Action', 2: 'Adventure', 4: 'Comedy', 8: 'Drama',
    10: 'Fantasy', 14: 'Horror', 7: 'Mystery', 22: 'Romance',
    24: 'Sci-Fi', 36: 'Slice of Life', 30: 'Sports', 37: 'Supernatural',
    41: 'Suspense', 18: 'Mecha', 38: 'Military', 19: 'Music',
    6: 'Demons', 40: 'Psychological', 23: 'School', 42: 'Seinen',
    25: 'Shoujo', 27: 'Shounen', 43: 'Josei', 26: 'Girls Love',
    28: 'Boys Love', 11: 'Game', 13: 'Historical', 17: 'Martial Arts',
    29: 'Space', 31: 'Super Power', 32: 'Vampire', 35: 'Harem',
    39: 'Detective', 46: 'Award Winning', 47: 'Gourmet', 48: 'Work Life',
    49: 'Erotica'
}

# Streaming networks/platforms
ANIME_NETWORKS = {
    'crunchyroll': {'name': 'Crunchyroll', 'producer_id': 102},
    'netflix': {'name': 'Netflix', 'producer_id': 1847},
    'funimation': {'name': 'Funimation', 'producer_id': 102},
    'hidive': {'name': 'HIDIVE', 'producer_id': None},
    'prime': {'name': 'Amazon Prime Video', 'producer_id': None},
    'hulu': {'name': 'Hulu', 'producer_id': None},
    'disney': {'name': 'Disney+', 'producer_id': None},
    'crunchyroll_originals': {'name': 'Crunchyroll Originals', 'producer_id': 102},
    'mappa': {'name': 'MAPPA Studio', 'producer_id': 569},
    'ufotable': {'name': 'ufotable', 'producer_id': 43},
    'wit_studio': {'name': 'Wit Studio', 'producer_id': 858},
    'bones': {'name': 'Bones', 'producer_id': 4},
    'madhouse': {'name': 'Madhouse', 'producer_id': 11},
    'kyoto_animation': {'name': 'Kyoto Animation', 'producer_id': 2},
    'toei': {'name': 'Toei Animation', 'producer_id': 18},
    'sunrise': {'name': 'Sunrise', 'producer_id': 14},
    'a1_pictures': {'name': 'A-1 Pictures', 'producer_id': 56},
    'cloverworks': {'name': 'CloverWorks', 'producer_id': 1835}
}


# ══════════════════════════════════════════════════════════════════════════════
# ANIME MOVIES MENU
# ══════════════════════════════════════════════════════════════════════════════

def anime_movies_menu():
    """Display Anime Movies submenu"""
    handle = int(sys.argv[1])
    items = [
        _menu_item('New Releases', 'anime_movies_new'),
        _menu_item('Top Rated Movies', 'anime_movies_top'),
        _menu_item('Popular Movies', 'anime_movies_popular'),
        _menu_item('Upcoming Movies', 'anime_movies_upcoming'),
        _menu_item('Movies by Genre', 'anime_movie_genres'),
        _menu_item('Award Winning Movies', 'anime_movies_award'),
        _menu_item('Classic Movies (Pre-2010)', 'anime_movies_classic'),
        _menu_item('Recent Movies (2020+)', 'anime_movies_recent'),
        _menu_item('Studio Ghibli Collection', 'anime_movies_ghibli'),
        _menu_item('Search Anime Movies', 'anime_search', extra_params={'media_type': 'movie'}),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(handle)


def anime_tv_menu():
    """Display Anime TV Shows submenu"""
    handle = int(sys.argv[1])
    items = [
        _menu_item('New Episodes (Calendar)', 'anime_calendar'),
        _menu_item('Show Premieres (Brand New)', 'anime_premieres'),
        _menu_item('Currently Airing', 'anime_tv_airing'),
        _menu_item('Top Rated Shows', 'anime_tv_top'),
        _menu_item('Popular Shows', 'anime_tv_popular'),
        _menu_item('Upcoming Shows', 'anime_tv_upcoming'),
        _menu_item('Shows by Genre', 'anime_tv_genres'),
        _menu_item('By Network/Studio', 'anime_networks'),
        _menu_item('Seasonal Anime', 'anime_seasonal_menu'),
        _menu_item('Complete Series', 'anime_tv_complete'),
        _menu_item('Search Anime Shows', 'anime_search', extra_params={'media_type': 'tv'}),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(handle)


def manga_menu():
    """Display Manga submenu"""
    handle = int(sys.argv[1])
    items = [
        _menu_item('Top Manga', 'manga_top'),
        _menu_item('Popular Manga', 'manga_popular'),
        _menu_item('Publishing Now', 'manga_publishing'),
        _menu_item('Manga by Genre', 'manga_genres'),
        _menu_item('Light Novels', 'manga_lightnovel'),
        _menu_item('One-shots', 'manga_oneshot'),
        _menu_item('Manhwa (Korean)', 'manga_manhwa'),
        _menu_item('Manhua (Chinese)', 'manga_manhua'),
        _menu_item('Search Manga', 'manga_search'),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(handle)


def torrent_sites_menu():
    """Display Anime Torrent Sites submenu"""
    handle = int(sys.argv[1])
    items = [
        _menu_item('Nyaa.si (Best Overall)', 'anime_torrent_site', extra_params={'site': 'nyaa'}),
        _menu_item('SubsPlease (Daily Subs)', 'anime_torrent_site', extra_params={'site': 'subsplease'}),
        _menu_item('AnimeTosho (Ad-Free)', 'anime_torrent_site', extra_params={'site': 'animetosho'}),
        _menu_item('TokyoTosho (Japanese Media)', 'anime_torrent_site', extra_params={'site': 'tokyotosho'}),
        _menu_item('Erai-Raws (Raw Episodes)', 'anime_torrent_site', extra_params={'site': 'erairaws'}),
        _menu_item('AniDex (Multi-Language)', 'anime_torrent_site', extra_params={'site': 'anidex'}),
        _menu_item('Search All Anime Sites', 'anime_torrent_search'),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(handle)


# ══════════════════════════════════════════════════════════════════════════════
# JIKAN API FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _display_anime_list(data, media_type='tv', handle=None):
    """Display anime list items from Jikan API response"""
    if handle is None:
        handle = int(sys.argv[1])
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    items = data.get('data', [])
    if not items:
        xbmcgui.Dialog().notification('Anime', 'No results found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(handle)
        return
    
    for item in items:
        mal_id = item.get('mal_id', 0)
        title = item.get('title', item.get('title_english', 'Unknown'))
        title_jp = item.get('title_japanese', '')
        year = ''
        if item.get('aired') and item['aired'].get('from'):
            year = item['aired']['from'][:4]
        elif item.get('year'):
            year = str(item['year'])
        
        # Get poster image
        images = item.get('images', {})
        poster = images.get('jpg', {}).get('large_image_url', '')
        if not poster:
            poster = images.get('jpg', {}).get('image_url', addon_icon)
        
        # Build label
        score = item.get('score', 0)
        episodes = item.get('episodes', '?')
        status = item.get('status', '')
        
        label = title
        if year:
            label += f' ({year})'
        
        # Create list item
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': poster,
            'thumb': poster,
            'icon': poster,
            'fanart': addon_fanart
        })
        
        # Set info
        info = {
            'title': title,
            'originaltitle': title_jp,
            'year': int(year) if year and year.isdigit() else 0,
            'plot': item.get('synopsis', ''),
            'rating': score or 0,
            'genre': ', '.join([g.get('name', '') for g in item.get('genres', [])]),
            'status': status
        }
        
        if media_type == 'movie' or item.get('type') == 'Movie':
            info['mediatype'] = 'movie'
            li.setInfo('video', info)
            li.setProperty('IsPlayable', 'true')
            
            # Context menu
            li.addContextMenuItems([
                ('Anime Info', f'RunPlugin(plugin://plugin.video.genesis/?action=anime_info&mal_id={mal_id})'),
            ])
            
            url = _build_url({
                'action': 'play_anime',
                'title': title,
                'year': year,
                'mal_id': mal_id,
                'media_type': 'movie'
            })
            xbmcplugin.addDirectoryItem(handle, url, li, False)
        else:
            info['mediatype'] = 'tvshow'
            if episodes and episodes != '?':
                info['episode'] = int(episodes)
            li.setInfo('video', info)
            
            # Context menu
            li.addContextMenuItems([
                ('Anime Info', f'RunPlugin(plugin://plugin.video.genesis/?action=anime_info&mal_id={mal_id})'),
            ])
            
            url = _build_url({
                'action': 'anime_show_episodes',
                'mal_id': mal_id,
                'title': title
            })
            xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    # Pagination
    pagination = data.get('pagination', {})
    if pagination.get('has_next_page'):
        current_page = pagination.get('current_page', 1)
        next_li = xbmcgui.ListItem(label=f'>>> Next Page ({current_page + 1}) >>>')
        next_li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        # Store pagination info for next request
        xbmcplugin.addDirectoryItem(handle, '', next_li, True)
    
    content = 'movies' if media_type == 'movie' else 'tvshows'
    xbmcplugin.setContent(handle, content)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def get_anime_movies_new(page=1):
    """Get new anime movie releases"""
    url = f'{JIKAN_BASE}/anime?type=movie&order_by=start_date&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'movie')


def get_anime_movies_top(page=1):
    """Get top rated anime movies"""
    url = f'{JIKAN_BASE}/top/anime?type=movie&filter=bypopularity&page={page}'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'movie')


def get_anime_movies_popular(page=1):
    """Get popular anime movies"""
    url = f'{JIKAN_BASE}/anime?type=movie&order_by=popularity&sort=asc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'movie')


def get_anime_movies_upcoming(page=1):
    """Get upcoming anime movies"""
    url = f'{JIKAN_BASE}/anime?type=movie&status=upcoming&order_by=popularity&sort=asc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'movie')


def get_anime_movies_award(page=1):
    """Get award-winning anime movies"""
    url = f'{JIKAN_BASE}/anime?type=movie&genres=46&order_by=score&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'movie')


def get_anime_movies_classic(page=1):
    """Get classic anime movies (pre-2010)"""
    url = f'{JIKAN_BASE}/anime?type=movie&order_by=score&sort=desc&end_date=2010-01-01&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'movie')


def get_anime_movies_recent(page=1):
    """Get recent anime movies (2020+)"""
    url = f'{JIKAN_BASE}/anime?type=movie&order_by=score&sort=desc&start_date=2020-01-01&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'movie')


def get_anime_movies_ghibli(page=1):
    """Get Studio Ghibli movies"""
    url = f'{JIKAN_BASE}/anime?type=movie&producers=21&order_by=score&sort=desc&page={page}'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'movie')


# ══════════════════════════════════════════════════════════════════════════════
# ANIME TV SHOWS
# ══════════════════════════════════════════════════════════════════════════════

def get_anime_tv_airing(page=1):
    """Get currently airing anime"""
    url = f'{JIKAN_BASE}/anime?status=airing&order_by=popularity&sort=asc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'tv')


def get_anime_tv_top(page=1):
    """Get top rated anime shows"""
    url = f'{JIKAN_BASE}/top/anime?type=tv&filter=bypopularity&page={page}'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'tv')


def get_anime_tv_popular(page=1):
    """Get popular anime shows"""
    url = f'{JIKAN_BASE}/anime?type=tv&order_by=popularity&sort=asc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'tv')


def get_anime_tv_upcoming(page=1):
    """Get upcoming anime shows"""
    url = f'{JIKAN_BASE}/anime?type=tv&status=upcoming&order_by=popularity&sort=asc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'tv')


def get_anime_tv_complete(page=1):
    """Get complete anime series"""
    url = f'{JIKAN_BASE}/anime?type=tv&status=complete&order_by=score&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'tv')


def get_anime_premieres(page=1):
    """Get brand new show premieres"""
    # Get shows that started in the last 30 days
    today = datetime.now()
    start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    url = f'{JIKAN_BASE}/anime?type=tv&start_date={start_date}&order_by=start_date&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'tv')


def get_anime_calendar():
    """Get anime airing schedule calendar"""
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    today_idx = datetime.now().weekday()
    # Python weekday: Monday=0, Jikan: Sunday=0
    jikan_today = (today_idx + 1) % 7
    
    # Reorder to start from today
    ordered_days = days[jikan_today:] + days[:jikan_today]
    day_labels = ['Today', 'Tomorrow'] + [d.capitalize() for d in ordered_days[2:]]
    
    for i, day in enumerate(ordered_days):
        label = f'{day_labels[i]} ({day.capitalize()})'
        url = _build_url({'action': 'anime_calendar_day', 'day': day})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    xbmcplugin.endOfDirectory(handle)


def get_anime_calendar_day(day):
    """Get anime schedule for specific day"""
    url = f'{JIKAN_BASE}/schedules?filter={day}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'tv')


# ══════════════════════════════════════════════════════════════════════════════
# SEASONAL ANIME
# ══════════════════════════════════════════════════════════════════════════════

def anime_seasonal_menu():
    """Display seasonal anime menu"""
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    now = datetime.now()
    year = now.year
    month = now.month
    
    # Determine current season
    if month in [1, 2, 3]:
        current_season = 'winter'
    elif month in [4, 5, 6]:
        current_season = 'spring'
    elif month in [7, 8, 9]:
        current_season = 'summer'
    else:
        current_season = 'fall'
    
    seasons = ['winter', 'spring', 'summer', 'fall']
    
    # Current and recent seasons
    items = [
        (f'{current_season.capitalize()} {year} (Current)', year, current_season),
    ]
    
    # Previous seasons
    season_idx = seasons.index(current_season)
    for i in range(1, 5):
        prev_idx = (season_idx - i) % 4
        prev_year = year if prev_idx < season_idx else year - 1
        items.append((f'{seasons[prev_idx].capitalize()} {prev_year}', prev_year, seasons[prev_idx]))
    
    # Upcoming
    next_idx = (season_idx + 1) % 4
    next_year = year if next_idx > season_idx else year + 1
    items.append((f'{seasons[next_idx].capitalize()} {next_year} (Upcoming)', next_year, seasons[next_idx]))
    
    for label, y, s in items:
        url = _build_url({'action': 'anime_seasonal', 'year': y, 'season': s})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    xbmcplugin.endOfDirectory(handle)


def get_anime_seasonal(year, season, page=1):
    """Get anime for specific season"""
    url = f'{JIKAN_BASE}/seasons/{year}/{season}?page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, 'tv')


# ══════════════════════════════════════════════════════════════════════════════
# GENRES
# ══════════════════════════════════════════════════════════════════════════════

def anime_movie_genres():
    """Display anime movie genres"""
    _display_genres('movie')


def anime_tv_genres():
    """Display anime TV genres"""
    _display_genres('tv')


def _display_genres(media_type):
    """Display genre selection menu"""
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for genre_id, genre_name in sorted(ANIME_GENRES.items(), key=lambda x: x[1]):
        url = _build_url({
            'action': 'anime_by_genre',
            'genre_id': genre_id,
            'media_type': media_type
        })
        li = xbmcgui.ListItem(label=genre_name)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    xbmcplugin.endOfDirectory(handle)


def get_anime_by_genre(genre_id, media_type='tv', page=1):
    """Get anime by genre"""
    anime_type = 'movie' if media_type == 'movie' else 'tv'
    url = f'{JIKAN_BASE}/anime?genres={genre_id}&type={anime_type}&order_by=score&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, media_type)


# ══════════════════════════════════════════════════════════════════════════════
# NETWORKS/STUDIOS
# ══════════════════════════════════════════════════════════════════════════════

def anime_networks_menu():
    """Display networks/studios menu"""
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    # Group by type
    streaming = ['crunchyroll', 'netflix', 'funimation', 'hidive', 'prime', 'hulu', 'disney']
    studios = ['mappa', 'ufotable', 'wit_studio', 'bones', 'madhouse', 'kyoto_animation', 'toei', 'sunrise', 'a1_pictures', 'cloverworks']
    
    # Streaming platforms header
    li = xbmcgui.ListItem(label='-- Streaming Platforms --')
    li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
    xbmcplugin.addDirectoryItem(handle, '', li, False)
    
    for key in streaming:
        network = ANIME_NETWORKS.get(key, {})
        url = _build_url({'action': 'anime_by_network', 'network': key})
        li = xbmcgui.ListItem(label=network.get('name', key))
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    # Studios header
    li = xbmcgui.ListItem(label='-- Animation Studios --')
    li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
    xbmcplugin.addDirectoryItem(handle, '', li, False)
    
    for key in studios:
        network = ANIME_NETWORKS.get(key, {})
        url = _build_url({'action': 'anime_by_studio', 'studio': key})
        li = xbmcgui.ListItem(label=network.get('name', key))
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    xbmcplugin.endOfDirectory(handle)


def get_anime_by_studio(studio, page=1):
    """Get anime by production studio"""
    network = ANIME_NETWORKS.get(studio, {})
    producer_id = network.get('producer_id')
    
    if producer_id:
        url = f'{JIKAN_BASE}/anime?producers={producer_id}&order_by=score&sort=desc&page={page}&sfw=true'
        data = _http_get(url)
        if data:
            _display_anime_list(data, 'tv')
    else:
        # Search by name if no producer ID
        name = network.get('name', studio)
        search_anime(name, 'tv', page)


# ══════════════════════════════════════════════════════════════════════════════
# MANGA
# ══════════════════════════════════════════════════════════════════════════════

def _display_manga_list(data, handle=None):
    """Display manga list items from Jikan API response"""
    if handle is None:
        handle = int(sys.argv[1])
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    items = data.get('data', [])
    if not items:
        xbmcgui.Dialog().notification('Manga', 'No results found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(handle)
        return
    
    for item in items:
        mal_id = item.get('mal_id', 0)
        title = item.get('title', item.get('title_english', 'Unknown'))
        
        # Get poster image
        images = item.get('images', {})
        poster = images.get('jpg', {}).get('large_image_url', '')
        if not poster:
            poster = images.get('jpg', {}).get('image_url', addon_icon)
        
        # Build label
        score = item.get('score', 0)
        chapters = item.get('chapters', '?')
        volumes = item.get('volumes', '?')
        status = item.get('status', '')
        manga_type = item.get('type', 'Manga')
        
        label = f'{title}'
        if score:
            label += f' [{score}]'
        
        # Create list item
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': poster,
            'thumb': poster,
            'icon': poster,
            'fanart': addon_fanart
        })
        
        # Set info
        plot = item.get('synopsis', '')
        if chapters and chapters != '?':
            plot = f'Chapters: {chapters}\n' + plot
        if volumes and volumes != '?':
            plot = f'Volumes: {volumes}\n' + plot
        plot = f'Type: {manga_type}\nStatus: {status}\n\n' + plot
        
        info = {
            'title': title,
            'plot': plot,
            'rating': score or 0,
            'genre': ', '.join([g.get('name', '') for g in item.get('genres', [])])
        }
        li.setInfo('video', info)
        
        url = _build_url({'action': 'manga_info', 'mal_id': mal_id})
        xbmcplugin.addDirectoryItem(handle, url, li, False)
    
    xbmcplugin.setContent(handle, 'movies')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def get_manga_top(page=1):
    """Get top rated manga"""
    url = f'{JIKAN_BASE}/top/manga?page={page}'
    data = _http_get(url)
    if data:
        _display_manga_list(data)


def get_manga_popular(page=1):
    """Get popular manga"""
    url = f'{JIKAN_BASE}/manga?order_by=popularity&sort=asc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_manga_list(data)


def get_manga_publishing(page=1):
    """Get currently publishing manga"""
    url = f'{JIKAN_BASE}/manga?status=publishing&order_by=popularity&sort=asc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_manga_list(data)


def get_manga_lightnovel(page=1):
    """Get light novels"""
    url = f'{JIKAN_BASE}/manga?type=lightnovel&order_by=score&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_manga_list(data)


def get_manga_oneshot(page=1):
    """Get one-shot manga"""
    url = f'{JIKAN_BASE}/manga?type=oneshot&order_by=score&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_manga_list(data)


def get_manga_manhwa(page=1):
    """Get Korean manhwa"""
    url = f'{JIKAN_BASE}/manga?type=manhwa&order_by=score&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_manga_list(data)


def get_manga_manhua(page=1):
    """Get Chinese manhua"""
    url = f'{JIKAN_BASE}/manga?type=manhua&order_by=score&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_manga_list(data)


def manga_genres():
    """Display manga genres"""
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for genre_id, genre_name in sorted(ANIME_GENRES.items(), key=lambda x: x[1]):
        url = _build_url({'action': 'manga_by_genre', 'genre_id': genre_id})
        li = xbmcgui.ListItem(label=genre_name)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    xbmcplugin.endOfDirectory(handle)


def get_manga_by_genre(genre_id, page=1):
    """Get manga by genre"""
    url = f'{JIKAN_BASE}/manga?genres={genre_id}&order_by=score&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_manga_list(data)


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH
# ══════════════════════════════════════════════════════════════════════════════

def search_anime_dialog(media_type='tv'):
    """Show search dialog for anime"""
    keyboard = xbmc.Keyboard('', f'Search Anime {"Movies" if media_type == "movie" else "Shows"}')
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            search_anime(query, media_type)


def search_anime(query, media_type='tv', page=1):
    """Search anime by query"""
    anime_type = 'movie' if media_type == 'movie' else 'tv'
    url = f'{JIKAN_BASE}/anime?q={quote_plus(query)}&type={anime_type}&order_by=score&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_anime_list(data, media_type)


def search_manga_dialog():
    """Show search dialog for manga"""
    keyboard = xbmc.Keyboard('', 'Search Manga')
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            search_manga(query)


def search_manga(query, page=1):
    """Search manga by query"""
    url = f'{JIKAN_BASE}/manga?q={quote_plus(query)}&order_by=score&sort=desc&page={page}&sfw=true'
    data = _http_get(url)
    if data:
        _display_manga_list(data)


# ══════════════════════════════════════════════════════════════════════════════
# ANIME EPISODES/DETAILS
# ══════════════════════════════════════════════════════════════════════════════

def show_anime_episodes(mal_id, title):
    """Show episodes for an anime series"""
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    # Get anime details first
    url = f'{JIKAN_BASE}/anime/{mal_id}'
    data = _http_get(url)
    
    if not data or not data.get('data'):
        xbmcgui.Dialog().notification('Error', 'Could not load anime info', xbmcgui.NOTIFICATION_ERROR)
        return
    
    anime = data['data']
    total_episodes = anime.get('episodes', 0)
    poster = anime.get('images', {}).get('jpg', {}).get('large_image_url', addon_icon)
    
    # Get episodes list
    episodes_url = f'{JIKAN_BASE}/anime/{mal_id}/episodes'
    episodes_data = _http_get(episodes_url)
    
    if episodes_data and episodes_data.get('data'):
        for ep in episodes_data['data']:
            ep_num = ep.get('mal_id', 0)
            ep_title = ep.get('title', f'Episode {ep_num}')
            aired = ep.get('aired', '')[:10] if ep.get('aired') else ''
            
            label = f'{ep_num}. {ep_title}'
            if aired:
                label += f' [{aired}]'
            
            li = xbmcgui.ListItem(label=label)
            li.setArt({
                'poster': poster,
                'thumb': poster,
                'icon': poster,
                'fanart': addon_fanart
            })
            li.setInfo('video', {
                'title': ep_title,
                'episode': ep_num,
                'mediatype': 'episode'
            })
            li.setProperty('IsPlayable', 'true')
            
            play_url = _build_url({
                'action': 'play_anime_episode',
                'title': title,
                'episode': ep_num,
                'mal_id': mal_id
            })
            xbmcplugin.addDirectoryItem(handle, play_url, li, False)
    else:
        # No episode data, create numbered episodes
        if total_episodes:
            for ep_num in range(1, total_episodes + 1):
                label = f'Episode {ep_num}'
                li = xbmcgui.ListItem(label=label)
                li.setArt({
                    'poster': poster,
                    'thumb': poster,
                    'icon': poster,
                    'fanart': addon_fanart
                })
                li.setInfo('video', {'title': label, 'episode': ep_num, 'mediatype': 'episode'})
                li.setProperty('IsPlayable', 'true')
                
                play_url = _build_url({
                    'action': 'play_anime_episode',
                    'title': title,
                    'episode': ep_num,
                    'mal_id': mal_id
                })
                xbmcplugin.addDirectoryItem(handle, play_url, li, False)
    
    xbmcplugin.setContent(handle, 'episodes')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def show_anime_info(mal_id):
    """Show detailed anime info dialog"""
    url = f'{JIKAN_BASE}/anime/{mal_id}/full'
    data = _http_get(url)
    
    if not data or not data.get('data'):
        xbmcgui.Dialog().notification('Error', 'Could not load anime info', xbmcgui.NOTIFICATION_ERROR)
        return
    
    anime = data['data']
    
    lines = [
        f'[B]{anime.get("title", "Unknown")}[/B]',
        f'Japanese: {anime.get("title_japanese", "N/A")}',
        '',
        f'[B]Score:[/B] {anime.get("score", "N/A")} / 10',
        f'[B]Ranked:[/B] #{anime.get("rank", "N/A")}',
        f'[B]Popularity:[/B] #{anime.get("popularity", "N/A")}',
        '',
        f'[B]Type:[/B] {anime.get("type", "N/A")}',
        f'[B]Episodes:[/B] {anime.get("episodes", "?")}',
        f'[B]Status:[/B] {anime.get("status", "N/A")}',
        f'[B]Aired:[/B] {anime.get("aired", {}).get("string", "N/A")}',
        '',
        f'[B]Studios:[/B] {", ".join([s.get("name", "") for s in anime.get("studios", [])])}',
        f'[B]Genres:[/B] {", ".join([g.get("name", "") for g in anime.get("genres", [])])}',
        '',
        '[B]Synopsis:[/B]',
        anime.get('synopsis', 'No synopsis available.'),
    ]
    
    xbmcgui.Dialog().textviewer(anime.get('title', 'Anime Info'), '\n'.join(lines))


def show_manga_info(mal_id):
    """Show detailed manga info dialog"""
    url = f'{JIKAN_BASE}/manga/{mal_id}/full'
    data = _http_get(url)
    
    if not data or not data.get('data'):
        xbmcgui.Dialog().notification('Error', 'Could not load manga info', xbmcgui.NOTIFICATION_ERROR)
        return
    
    manga = data['data']
    
    lines = [
        f'[B]{manga.get("title", "Unknown")}[/B]',
        f'Japanese: {manga.get("title_japanese", "N/A")}',
        '',
        f'[B]Score:[/B] {manga.get("score", "N/A")} / 10',
        f'[B]Ranked:[/B] #{manga.get("rank", "N/A")}',
        f'[B]Popularity:[/B] #{manga.get("popularity", "N/A")}',
        '',
        f'[B]Type:[/B] {manga.get("type", "N/A")}',
        f'[B]Chapters:[/B] {manga.get("chapters", "?")}',
        f'[B]Volumes:[/B] {manga.get("volumes", "?")}',
        f'[B]Status:[/B] {manga.get("status", "N/A")}',
        '',
        f'[B]Authors:[/B] {", ".join([a.get("name", "") for a in manga.get("authors", [])])}',
        f'[B]Genres:[/B] {", ".join([g.get("name", "") for g in manga.get("genres", [])])}',
        '',
        '[B]Synopsis:[/B]',
        manga.get('synopsis', 'No synopsis available.'),
    ]
    
    xbmcgui.Dialog().textviewer(manga.get('title', 'Manga Info'), '\n'.join(lines))
