"""
Trakt API Module - List/Search functionality
Uses native urllib (no external requests module)
OPTIMIZED: Faster list loading with optional TMDB metadata
"""
import json
import xbmcgui
import xbmcplugin
import sys
import xbmcaddon
import xbmc
import xbmcvfs
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote_plus
from . import tmdb
from . import trakt_auth

def get_addon():
    return xbmcaddon.Addon()

ADDON_ID = 'plugin.video.trakt_player'
ADDON_PATH = xbmcvfs.translatePath(f'special://home/addons/{ADDON_ID}/')

# Use same client ID as trakt_auth
CLIENT_ID = 'd2a8e820fec0d46079cbbceaca851648df9431cbc73ede2c10d35dfb1c7a36e2'
USER_AGENT = 'TraktPlayer Kodi Addon'

# Pagination settings - reduced for faster loading
ITEMS_PER_PAGE = 30


def get_addon_icon():
    """Get addon icon path"""
    import os
    icon_path = os.path.join(ADDON_PATH, 'icon.png')
    if os.path.exists(icon_path):
        return icon_path
    return 'DefaultAddonVideo.png'


def get_addon_fanart():
    """Get addon fanart path"""
    import os
    fanart_path = os.path.join(ADDON_PATH, 'fanart.jpg')
    if os.path.exists(fanart_path):
        return fanart_path
    return ''


def _http_get(url, headers=None, timeout=10):
    """HTTP GET request using urllib, returns (status_code, json_data or None)"""
    hdrs = {
        'Content-Type': 'application/json',
        'User-Agent': USER_AGENT,
        'trakt-api-version': '2',
        'trakt-api-key': CLIENT_ID
    }
    if headers:
        hdrs.update(headers)
    
    try:
        req = Request(url, headers=hdrs, method='GET')
        response = urlopen(req, timeout=timeout)
        body = response.read().decode('utf-8')
        return response.getcode(), json.loads(body)
    except HTTPError as e:
        return e.code, None
    except URLError as e:
        xbmc.log(f'Trakt URL Error: {e.reason}', xbmc.LOGERROR)
        return 0, None
    except Exception as e:
        xbmc.log(f'Trakt Request Error: {e}', xbmc.LOGERROR)
        return 0, None


def get_headers():
    """Get headers for Trakt API requests"""
    token = trakt_auth.get_token()
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def get_list(path, media_type='movie', page=1):
    """Fetch and display a Trakt list with pagination - OPTIMIZED for speed"""
    headers = get_headers()
    handle = int(sys.argv[1])
    
    # Get addon artwork
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    # Check if this needs authentication
    needs_auth = 'sync/' in path or 'users/' in path
    if needs_auth and not trakt_auth.is_authorized():
        xbmcgui.Dialog().notification('Trakt', 'Please authorize Trakt first', xbmcgui.NOTIFICATION_WARNING)
        trakt_auth.authorize()
        return
    
    try:
        # Build URL with pagination
        page = int(page)
        url = f'https://api.trakt.tv/{path}?extended=full&limit={ITEMS_PER_PAGE}&page={page}'
        xbmc.log(f'Trakt API request: {url} (page {page})', xbmc.LOGINFO)
        
        status, data = _http_get(url, headers=headers)
        
        if status == 401:
            # Token expired, try refresh
            if trakt_auth.refresh_token():
                headers = get_headers()
                status, data = _http_get(url, headers=headers)
            else:
                xbmcgui.Dialog().notification('Trakt', 'Session expired. Please re-authorize.', xbmcgui.NOTIFICATION_WARNING)
                trakt_auth.authorize()
                return
        
        if status != 200 or data is None:
            xbmcgui.Dialog().notification('Trakt', f'API error: {status}', xbmcgui.NOTIFICATION_ERROR)
            return
        
        if not data:
            if page == 1:
                xbmcgui.Dialog().notification('Trakt', 'No results found', xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(handle)
            return
        
        # Collect all TMDB IDs for batch fetching (faster)
        items_data = []
        for item in data:
            if media_type == 'show':
                content = item.get('show', item)
            else:
                content = item.get('movie', item)
            
            title = content.get('title', 'Unknown')
            year = content.get('year', '')
            ids = content.get('ids', {})
            tmdb_id = ids.get('tmdb')
            imdb_id = ids.get('imdb', '')
            overview = content.get('overview', '')
            rating = content.get('rating', 0)
            
            items_data.append({
                'title': title,
                'year': year,
                'tmdb_id': tmdb_id,
                'imdb_id': imdb_id,
                'overview': overview,
                'rating': rating,
                'media_type': media_type
            })
        
        # Fetch TMDB images in batch (faster than individual calls)
        tmdb_type = 'movie' if media_type == 'movie' else 'tv'
        tmdb_ids = [item['tmdb_id'] for item in items_data if item['tmdb_id']]
        images_cache = tmdb.get_images_batch(tmdb_ids, tmdb_type) if tmdb_ids else {}
        
        # Build list items
        for item in items_data:
            title = item['title']
            year = item['year']
            tmdb_id = item['tmdb_id']
            imdb_id = item['imdb_id']
            
            # Create list item
            label = f'{title}' if not year else f'{title} ({year})'
            li = xbmcgui.ListItem(label=label)
            
            # Get images from cache or use defaults
            images = images_cache.get(tmdb_id, {})
            poster = images.get('poster', '')
            fanart = images.get('backdrop', '') or addon_fanart
            
            li.setArt({
                'poster': poster or addon_icon,
                'fanart': fanart,
                'thumb': poster or addon_icon,
                'icon': poster or addon_icon,
                'banner': fanart
            })
            
            # Set info from Trakt data (no extra TMDB call needed)
            info = {
                'title': title,
                'year': year,
                'plot': item['overview'],
                'rating': item['rating']
            }
            
            if media_type == 'movie':
                info['mediatype'] = 'movie'
                li.setInfo('video', info)
                li.setProperty('IsPlayable', 'true')
                
                play_url = f"{sys.argv[0]}?action=play&title={quote_plus(title)}&year={year}&imdb_id={imdb_id}"
                xbmcplugin.addDirectoryItem(handle, play_url, li, False)
            else:
                info['mediatype'] = 'tvshow'
                li.setInfo('video', info)
                
                show_url = f"{sys.argv[0]}?action=show_seasons&tmdb_id={tmdb_id}&title={quote_plus(title)}"
                xbmcplugin.addDirectoryItem(handle, show_url, li, True)
        
        # Add "Next Page" item for infinite scroll
        if len(data) >= ITEMS_PER_PAGE:
            next_page = page + 1
            next_li = xbmcgui.ListItem(label=f'[B][COLOR yellow]>>> Next Page ({next_page}) >>>[/COLOR][/B]')
            next_li.setArt({
                'icon': addon_icon,
                'thumb': addon_icon,
                'fanart': addon_fanart
            })
            next_url = f"{sys.argv[0]}?action=trakt_list&path={quote_plus(path)}&media_type={media_type}&page={next_page}"
            xbmcplugin.addDirectoryItem(handle, next_url, next_li, True)
        
        xbmcplugin.setContent(handle, 'movies' if media_type == 'movie' else 'tvshows')
        xbmcplugin.endOfDirectory(handle, cacheToDisc=True)
        
    except Exception as e:
        xbmc.log(f'Trakt API error: {str(e)}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', f'Failed to load: {str(e)}', xbmcgui.NOTIFICATION_ERROR)


def show_seasons(tmdb_id, show_title):
    """Display seasons for a TV show with addon icon/fanart"""
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    seasons = tmdb.get_tv_seasons(tmdb_id)
    
    for season in seasons:
        season_num = season.get('season_number', 0)
        if season_num == 0:  # Skip specials
            continue
            
        name = season.get('name', f'Season {season_num}')
        poster = f"https://image.tmdb.org/t/p/w500{season.get('poster_path')}" if season.get('poster_path') else ''
        
        li = xbmcgui.ListItem(label=name)
        li.setArt({
            'poster': poster or addon_icon,
            'thumb': poster or addon_icon,
            'icon': poster or addon_icon,
            'fanart': addon_fanart
        })
        li.setInfo('video', {'title': name, 'season': season_num})
        
        url = f"{sys.argv[0]}?action=show_episodes&tmdb_id={tmdb_id}&season={season_num}&title={quote_plus(show_title)}"
        xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    xbmcplugin.setContent(handle, 'seasons')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def show_episodes(tmdb_id, season_number, show_title):
    """Display episodes for a season with addon icon/fanart"""
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    episodes = tmdb.get_season_episodes(tmdb_id, season_number)
    
    for ep in episodes:
        ep_num = ep.get('episode_number', 0)
        name = ep.get('name', f'Episode {ep_num}')
        still = f"https://image.tmdb.org/t/p/w500{ep.get('still_path')}" if ep.get('still_path') else ''
        
        label = f"{ep_num}. {name}"
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'thumb': still or addon_icon,
            'icon': still or addon_icon,
            'fanart': still or addon_fanart,
            'poster': addon_icon
        })
        li.setInfo('video', {
            'title': name,
            'episode': ep_num,
            'season': int(season_number),
            'plot': ep.get('overview', ''),
            'mediatype': 'episode'
        })
        li.setProperty('IsPlayable', 'true')
        
        url = f"{sys.argv[0]}?action=play_episode&title={quote_plus(show_title)}&season={season_number}&episode={ep_num}"
        xbmcplugin.addDirectoryItem(handle, url, li, False)
    
    xbmcplugin.setContent(handle, 'episodes')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def search(query, media_type='movie', page=1):
    """Search Trakt for movies or shows with pagination"""
    headers = get_headers()
    handle = int(sys.argv[1])
    endpoint = 'movie' if media_type == 'movie' else 'show'
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    try:
        page = int(page)
        url = f'https://api.trakt.tv/search/{endpoint}?query={quote_plus(query)}&extended=full&limit={ITEMS_PER_PAGE}&page={page}'
        status, data = _http_get(url, headers=headers)
        
        if status != 200 or data is None:
            xbmcgui.Dialog().notification('Search', 'No results found', xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(handle)
            return
        
        # Collect TMDB IDs for batch image fetching
        items_data = []
        for item in data:
            content = item.get(endpoint, {})
            items_data.append({
                'title': content.get('title', 'Unknown'),
                'year': content.get('year', ''),
                'tmdb_id': content.get('ids', {}).get('tmdb'),
                'imdb_id': content.get('ids', {}).get('imdb', ''),
                'overview': content.get('overview', '')
            })
        
        # Batch fetch images
        tmdb_type = 'movie' if media_type == 'movie' else 'tv'
        tmdb_ids = [item['tmdb_id'] for item in items_data if item['tmdb_id']]
        images_cache = tmdb.get_images_batch(tmdb_ids, tmdb_type) if tmdb_ids else {}
        
        for item in items_data:
            title = item['title']
            year = item['year']
            tmdb_id = item['tmdb_id']
            imdb_id = item['imdb_id']
            
            label = f'{title} ({year})' if year else title
            li = xbmcgui.ListItem(label=label)
            
            images = images_cache.get(tmdb_id, {})
            poster = images.get('poster', '')
            fanart = images.get('backdrop', '') or addon_fanart
            
            li.setArt({
                'poster': poster or addon_icon,
                'fanart': fanart,
                'thumb': poster or addon_icon,
                'icon': poster or addon_icon
            })
            li.setInfo('video', {
                'title': title,
                'year': year,
                'plot': item['overview']
            })
            
            if media_type == 'movie':
                li.setProperty('IsPlayable', 'true')
                play_url = f"{sys.argv[0]}?action=play&title={quote_plus(title)}&year={year}&imdb_id={imdb_id}"
                xbmcplugin.addDirectoryItem(handle, play_url, li, False)
            else:
                show_url = f"{sys.argv[0]}?action=show_seasons&tmdb_id={tmdb_id}&title={quote_plus(title)}"
                xbmcplugin.addDirectoryItem(handle, show_url, li, True)
        
        # Add "Next Page" for infinite scroll
        if len(data) >= ITEMS_PER_PAGE:
            next_page = page + 1
            next_li = xbmcgui.ListItem(label=f'[B][COLOR yellow]>>> Next Page ({next_page}) >>>[/COLOR][/B]')
            next_li.setArt({
                'icon': addon_icon,
                'thumb': addon_icon,
                'fanart': addon_fanart
            })
            next_url = f"{sys.argv[0]}?action=search_results&query={quote_plus(query)}&media_type={media_type}&page={next_page}"
            xbmcplugin.addDirectoryItem(handle, next_url, next_li, True)
        
        xbmcplugin.endOfDirectory(handle, cacheToDisc=True)
        
    except Exception as e:
        xbmc.log(f'Search error: {str(e)}', xbmc.LOGERROR)



# ══════════════════════════════════════════════════════════════════════════
# Superpower Features (merged from zeus768's custom build)
# ══════════════════════════════════════════════════════════════════════════

def _http_post(url, data=None, headers=None, timeout=15):
    """HTTP POST for Trakt API."""
    hdrs = {
        'Content-Type': 'application/json',
        'User-Agent': USER_AGENT,
        'trakt-api-version': '2',
        'trakt-api-key': CLIENT_ID
    }
    if headers:
        hdrs.update(headers)
    token = trakt_auth.get_token()
    if token:
        hdrs['Authorization'] = f'Bearer {token}'
    
    from urllib.request import urlopen, Request
    try:
        post_data = json.dumps(data).encode('utf-8') if data else None
        req = Request(url, data=post_data, headers=hdrs, method='POST')
        response = urlopen(req, timeout=timeout)
        body = response.read().decode('utf-8')
        try:
            return response.getcode(), json.loads(body)
        except json.JSONDecodeError:
            return response.getcode(), body
    except HTTPError as e:
        return e.code, None
    except Exception as e:
        xbmc.log(f'Trakt POST error: {e}', xbmc.LOGERROR)
        return 0, None


def _display_items(items, media_type='movie', key=None):
    """Display Trakt items with TMDB metadata in Kodi directory.

    FIX: Determines per-item media type (movie/show/episode) from Trakt's
    own 'type' field so we query the correct TMDB endpoint (movie vs tv).
    TMDB movie and TV IDs are separate namespaces - using the wrong one
    returns completely unrelated posters.
    """
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    if not items or not isinstance(items, list):
        xbmcgui.Dialog().notification('Trakt', 'No items found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(handle)
        return
    
    default_is_movie = media_type in ('movie', 'movies')
    
    # First pass: parse each item and determine its ACTUAL media type
    parsed = []
    for item in items:
        if not isinstance(item, dict):
            continue
        
        # Detect actual per-item type (Trakt returns 'movie', 'show', 'episode', 'season', 'person')
        item_type = item.get('type')
        data = None
        actual_type = None
        
        if key and key in item:
            data = item[key]
            actual_type = 'show' if key == 'show' else ('movie' if key == 'movie' else None)
        
        if data is None:
            if item_type == 'movie' and isinstance(item.get('movie'), dict):
                data = item['movie']
                actual_type = 'movie'
            elif item_type == 'show' and isinstance(item.get('show'), dict):
                data = item['show']
                actual_type = 'show'
            elif item_type == 'episode' and isinstance(item.get('show'), dict):
                # Episode entries (history, playback): use show for poster
                data = item['show']
                actual_type = 'show'
            elif isinstance(item.get('movie'), dict):
                data = item['movie']
                actual_type = 'movie'
            elif isinstance(item.get('show'), dict):
                data = item['show']
                actual_type = 'show'
            elif 'title' in item and 'ids' in item:
                data = item
                actual_type = 'movie' if default_is_movie else 'show'
            else:
                continue
        
        if not data or not isinstance(data, dict):
            continue
        
        if actual_type is None:
            actual_type = 'movie' if default_is_movie else 'show'
        
        parsed.append({'data': data, 'actual_type': actual_type})
    
    if not parsed:
        xbmcgui.Dialog().notification('Trakt', 'No items found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(handle)
        return
    
    # Batch-fetch TMDB images grouped by actual type (much faster than sequential)
    movie_ids = [str(p['data'].get('ids', {}).get('tmdb') or '')
                 for p in parsed if p['actual_type'] == 'movie' and p['data'].get('ids', {}).get('tmdb')]
    show_ids = [str(p['data'].get('ids', {}).get('tmdb') or '')
                for p in parsed if p['actual_type'] == 'show' and p['data'].get('ids', {}).get('tmdb')]
    
    movie_images = tmdb.get_images_batch(movie_ids, 'movie') if movie_ids else {}
    show_images = tmdb.get_images_batch(show_ids, 'tv') if show_ids else {}
    
    # Track what content type to set: mixed lists default to 'videos'
    has_movie = any(p['actual_type'] == 'movie' for p in parsed)
    has_show = any(p['actual_type'] == 'show' for p in parsed)
    
    for p in parsed:
        data = p['data']
        actual_type = p['actual_type']
        
        title = data.get('title', 'Unknown')
        year = data.get('year', '')
        ids = data.get('ids', {})
        tmdb_id_raw = ids.get('tmdb') if ids else None
        tmdb_id = str(tmdb_id_raw) if tmdb_id_raw else ''
        imdb_id = str(ids.get('imdb', '')) if ids else ''
        
        label = f'{title} ({year})' if year else title
        overview = data.get('overview', '')
        
        # Look up artwork from the correct namespace
        images = {}
        if tmdb_id:
            if actual_type == 'movie':
                # get_images_batch keys results by the original tmdb_id value type.
                images = movie_images.get(tmdb_id_raw) or movie_images.get(tmdb_id) or {}
            else:
                images = show_images.get(tmdb_id_raw) or show_images.get(tmdb_id) or {}
        
        poster_url = images.get('poster') or addon_icon
        backdrop_url = images.get('backdrop') or addon_fanart
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'icon': poster_url, 'thumb': poster_url,
            'poster': poster_url, 'fanart': backdrop_url,
            'banner': backdrop_url
        })
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setYear(int(year) if year else 0)
        info_tag.setPlot(overview)
        
        if actual_type == 'movie':
            info_tag.setMediaType('movie')
            url = f"{sys.argv[0]}?action=play&title={quote_plus(title)}&year={year}&imdb_id={imdb_id}"
            li.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(handle, url, li, False)
        else:
            info_tag.setMediaType('tvshow')
            url = f"{sys.argv[0]}?action=show_seasons&tmdb_id={tmdb_id}&title={quote_plus(title)}"
            xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    # Pick content view based on what we actually have
    if has_movie and not has_show:
        content = 'movies'
    elif has_show and not has_movie:
        content = 'tvshows'
    else:
        content = 'videos'
    xbmcplugin.setContent(handle, content)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def get_recommendations(media_type='movie'):
    """Get personalized Trakt recommendations."""
    mt = 'movies' if media_type == 'movie' else 'shows'
    headers = get_headers()
    status, data = _http_get(f'https://api.trakt.tv/recommendations/{mt}?limit=30', headers=headers)
    if status == 200 and data:
        _display_items(data, media_type)
    else:
        xbmcgui.Dialog().notification('Trakt', 'Could not load recommendations', xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))


def get_calendar():
    """Get upcoming episodes from Trakt calendar."""
    headers = get_headers()
    status, data = _http_get('https://api.trakt.tv/calendars/my/shows?extended=full&limit=30', headers=headers)
    handle = int(sys.argv[1])
    
    if status != 200 or not data:
        xbmcgui.Dialog().notification('Trakt', 'Could not load calendar', xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(handle)
        return
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for item in data:
        if not isinstance(item, dict):
            continue
        show = item.get('show', {})
        episode = item.get('episode', {})
        title = show.get('title', 'Unknown')
        ep_title = episode.get('title', '')
        season = episode.get('season', 0)
        ep_num = episode.get('number', 0)
        first_aired = item.get('first_aired', '')[:10]
        
        label = f'{title} S{season:02d}E{ep_num:02d}'
        if ep_title:
            label += f' - {ep_title}'
        if first_aired:
            label += f' [{first_aired}]'
        
        ids = show.get('ids', {})
        tmdb_id = str(ids.get('tmdb', ''))
        imdb_id = str(ids.get('imdb', ''))
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(label)
        info_tag.setPlot(episode.get('overview', ''))
        
        url = f"{sys.argv[0]}?action=play_episode&title={quote_plus(title)}&season={season}&episode={ep_num}&imdb_id={imdb_id}&tmdb_id={tmdb_id}"
        li.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(handle, url, li, False)
    
    xbmcplugin.setContent(handle, 'episodes')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def get_history(media_type='movie'):
    """Get recently watched history."""
    mt = 'movies' if media_type == 'movie' else 'episodes'
    headers = get_headers()
    status, data = _http_get(f'https://api.trakt.tv/sync/history/{mt}?limit=30', headers=headers)
    if status == 200 and data:
        _display_items(data, media_type)
    else:
        xbmcgui.Dialog().notification('Trakt', 'Could not load history', xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))


def get_anticipated(media_type='movie'):
    """Get most anticipated movies/shows."""
    mt = 'movies' if media_type == 'movie' else 'shows'
    headers = get_headers()
    status, data = _http_get(f'https://api.trakt.tv/movies/anticipated?limit=30' if media_type == 'movie' 
                              else f'https://api.trakt.tv/shows/anticipated?limit=30', headers=headers)
    if status == 200 and data:
        _display_items(data, media_type)
    else:
        xbmcplugin.endOfDirectory(int(sys.argv[1]))


def get_popular_lists():
    """Get popular community lists from Trakt."""
    headers = get_headers()
    status, data = _http_get('https://api.trakt.tv/lists/popular?limit=30', headers=headers)
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    if status != 200 or not data:
        xbmcplugin.endOfDirectory(handle)
        return
    
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get('name', 'Unknown List')
        user = item.get('user', {}).get('username', '')
        slug = item.get('ids', {}).get('slug', '')
        likes = item.get('likes', 0)
        
        label = f'{name} by {user} ({likes} likes)' if user else name
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'fanart': addon_fanart})
        
        url = f"{sys.argv[0]}?action=list_items&user={quote_plus(user)}&list_slug={quote_plus(slug)}"
        xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def get_list_items(user, list_slug):
    """Get items from a specific Trakt list."""
    headers = get_headers()
    status, data = _http_get(f'https://api.trakt.tv/users/{user}/lists/{list_slug}/items?limit=50', headers=headers)
    if status == 200 and data:
        _display_items(data, 'movie')
    else:
        xbmcplugin.endOfDirectory(int(sys.argv[1]))


def get_related(media_type, trakt_id):
    """Get related movies/shows."""
    mt = 'movies' if media_type == 'movie' else 'shows'
    headers = get_headers()
    status, data = _http_get(f'https://api.trakt.tv/{mt}/{trakt_id}/related?limit=20', headers=headers)
    if status == 200 and data:
        _display_items(data, media_type)
    else:
        xbmcplugin.endOfDirectory(int(sys.argv[1]))


def get_playback_progress():
    """Get continue watching / playback progress."""
    headers = get_headers()
    status, data = _http_get('https://api.trakt.tv/sync/playback?limit=30', headers=headers)
    if status == 200 and data:
        _display_items(data, 'movie')
    else:
        xbmcgui.Dialog().notification('Trakt', 'No playback progress', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))


def rate_item(media_type, trakt_id):
    """Rate a movie or show on Trakt."""
    rating = xbmcgui.Dialog().select('Rate', [f'{i}/10' for i in range(1, 11)])
    if rating < 0:
        return
    rating += 1
    mt = 'movies' if media_type == 'movie' else 'shows'
    status, _ = _http_post(f'https://api.trakt.tv/sync/ratings', data={
        mt: [{'ids': {'trakt': int(trakt_id)}, 'rating': rating}]
    })
    if status in (200, 201):
        xbmcgui.Dialog().notification('Trakt', f'Rated {rating}/10', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('Trakt', 'Rating failed', xbmcgui.NOTIFICATION_ERROR)


def add_to_watchlist(media_type, imdb_id):
    """Add item to Trakt watchlist."""
    mt = 'movies' if media_type == 'movie' else 'shows'
    status, _ = _http_post('https://api.trakt.tv/sync/watchlist', data={
        mt: [{'ids': {'imdb': imdb_id}}]
    })
    if status in (200, 201):
        xbmcgui.Dialog().notification('Trakt', 'Added to watchlist', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('Trakt', 'Failed to add', xbmcgui.NOTIFICATION_ERROR)


def get_friends():
    """Get Trakt friends list."""
    headers = get_headers()
    status, data = _http_get('https://api.trakt.tv/users/me/friends', headers=headers)
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    if status != 200 or not data:
        xbmcgui.Dialog().notification('Trakt', 'No friends found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(handle)
        return
    
    for item in data:
        user = item.get('user', {})
        username = user.get('username', 'Unknown')
        li = xbmcgui.ListItem(label=username)
        li.setArt({'icon': addon_icon, 'fanart': addon_fanart})
        url = f"{sys.argv[0]}?action=friend_activity&user={quote_plus(username)}"
        xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    xbmcplugin.endOfDirectory(handle)


def get_friend_activity(user):
    """Get a friend's recent activity."""
    headers = get_headers()
    status, data = _http_get(f'https://api.trakt.tv/users/{user}/watched/movies?limit=20', headers=headers)
    if status == 200 and data:
        _display_items(data, 'movie')
    else:
        xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_user_stats():
    """Show current user's Trakt statistics."""
    headers = get_headers()
    status, data = _http_get('https://api.trakt.tv/users/me/stats', headers=headers)
    
    if status != 200 or not data:
        xbmcgui.Dialog().notification('Trakt', 'Could not load stats', xbmcgui.NOTIFICATION_WARNING)
        return
    
    movies = data.get('movies', {})
    shows = data.get('shows', {})
    episodes = data.get('episodes', {})
    
    lines = [
        '[B][COLOR skyblue]--- Your Trakt Stats ---[/COLOR][/B]',
        '',
        f'[B]Movies[/B]',
        f'  Watched: {movies.get("watched", 0)}',
        f'  Collected: {movies.get("collected", 0)}',
        f'  Ratings: {movies.get("ratings", 0)}',
        '',
        f'[B]TV Shows[/B]',
        f'  Watched: {shows.get("watched", 0)}',
        f'  Collected: {shows.get("collected", 0)}',
        f'  Ratings: {shows.get("ratings", 0)}',
        '',
        f'[B]Episodes[/B]',
        f'  Watched: {episodes.get("watched", 0)}',
        f'  Collected: {episodes.get("collected", 0)}',
        f'  Ratings: {episodes.get("ratings", 0)}',
    ]
    
    xbmcgui.Dialog().textviewer('Trakt Stats', '\n'.join(lines))


def get_my_lists():
    """Get user's custom Trakt lists."""
    headers = get_headers()
    status, data = _http_get('https://api.trakt.tv/users/me/lists', headers=headers)
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    if status != 200 or not data:
        xbmcplugin.endOfDirectory(handle)
        return
    
    # Add "Create New List" option
    li = xbmcgui.ListItem(label='[B]+ Create New List[/B]')
    li.setArt({'icon': addon_icon, 'fanart': addon_fanart})
    url = f"{sys.argv[0]}?action=create_list"
    xbmcplugin.addDirectoryItem(handle, url, li, False)
    
    for item in data:
        name = item.get('name', 'Unknown')
        slug = item.get('ids', {}).get('slug', '')
        count = item.get('item_count', 0)
        
        label = f'{name} ({count} items)'
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'fanart': addon_fanart})
        url = f"{sys.argv[0]}?action=list_items&user=me&list_slug={quote_plus(slug)}"
        xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    xbmcplugin.endOfDirectory(handle)


def create_list():
    """Create a new Trakt list."""
    kb = xbmc.Keyboard('', 'List Name')
    kb.doModal()
    if not kb.isConfirmed():
        return
    name = kb.getText().strip()
    if not name:
        return
    
    status, _ = _http_post('https://api.trakt.tv/users/me/lists', data={
        'name': name, 'privacy': 'private', 'allow_comments': False
    })
    if status in (200, 201):
        xbmcgui.Dialog().notification('Trakt', f'Created: {name}', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('Trakt', 'Failed to create list', xbmcgui.NOTIFICATION_ERROR)


def delete_list(list_slug):
    """Delete a Trakt list."""
    if not xbmcgui.Dialog().yesno('Delete List', f'Delete list "{list_slug}"?'):
        return
    from urllib.request import Request, urlopen
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': USER_AGENT,
        'trakt-api-version': '2',
        'trakt-api-key': CLIENT_ID
    }
    token = trakt_auth.get_token()
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        req = Request(f'https://api.trakt.tv/users/me/lists/{list_slug}', headers=headers, method='DELETE')
        urlopen(req, timeout=15)
        xbmcgui.Dialog().notification('Trakt', 'List deleted', xbmcgui.NOTIFICATION_INFO)
    except Exception:
        xbmcgui.Dialog().notification('Trakt', 'Failed to delete', xbmcgui.NOTIFICATION_ERROR)


def add_to_list(media_type, imdb_id):
    """Add item to a user's custom list."""
    headers = get_headers()
    status, lists = _http_get('https://api.trakt.tv/users/me/lists', headers=headers)
    if status != 200 or not lists:
        xbmcgui.Dialog().notification('Trakt', 'No lists found', xbmcgui.NOTIFICATION_WARNING)
        return
    
    names = [l.get('name', '') for l in lists]
    idx = xbmcgui.Dialog().select('Add to List', names)
    if idx < 0:
        return
    
    slug = lists[idx].get('ids', {}).get('slug', '')
    mt = 'movies' if media_type == 'movie' else 'shows'
    s, _ = _http_post(f'https://api.trakt.tv/users/me/lists/{slug}/items', data={
        mt: [{'ids': {'imdb': imdb_id}}]
    })
    if s in (200, 201):
        xbmcgui.Dialog().notification('Trakt', f'Added to {names[idx]}', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('Trakt', 'Failed to add', xbmcgui.NOTIFICATION_ERROR)
