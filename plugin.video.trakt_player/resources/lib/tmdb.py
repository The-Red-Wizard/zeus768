"""
TMDB API Module
Uses native urllib (no external requests module)
OPTIMIZED: Added batch image fetching for faster list loading
"""
import json
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc
import sys
import threading
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus

def get_addon():
    return xbmcaddon.Addon()

USER_AGENT = 'TraktPlayer Kodi Addon'

# Default TMDB API key - users are encouraged to use their own
DEFAULT_TMDB_KEY = "8265bd1679663a7ea12ac168da84d2e8"

# Simple in-memory cache for images
_image_cache = {}


def _http_get(url, timeout=8):
    """HTTP GET request using urllib, returns json data or None"""
    try:
        req = Request(url, headers={'User-Agent': USER_AGENT}, method='GET')
        response = urlopen(req, timeout=timeout)
        body = response.read().decode('utf-8')
        return json.loads(body)
    except HTTPError as e:
        xbmc.log(f'TMDB HTTP Error: {e.code}', xbmc.LOGWARNING)
        return None
    except URLError as e:
        xbmc.log(f'TMDB URL Error: {e.reason}', xbmc.LOGERROR)
        return None
    except Exception as e:
        xbmc.log(f'TMDB Request Error: {e}', xbmc.LOGERROR)
        return None


def get_api_key():
    """Get TMDB API key - user's key or default"""
    addon = get_addon()
    user_key = addon.getSetting('tmdb_api_key')
    if user_key and len(user_key) > 10:
        return user_key
    return DEFAULT_TMDB_KEY


def prompt_for_api_key():
    """Show prompt suggesting user to add their own API key"""
    addon = get_addon()
    if addon.getSetting('tmdb_key_prompted') != 'true':
        dialog = xbmcgui.Dialog()
        result = dialog.yesno(
            "TMDB API Key",
            "A default TMDB API key is being used.\n\nFor better reliability, it's recommended to use your own free API key from themoviedb.org\n\nWould you like to add your own key now?",
            nolabel="Use Default",
            yeslabel="Add My Key"
        )
        
        if result:
            keyboard = xbmc.Keyboard('', 'Enter your TMDB API Key')
            keyboard.doModal()
            if keyboard.isConfirmed():
                key = keyboard.getText()
                if key and len(key) > 10:
                    addon.setSetting('tmdb_api_key', key)
                    xbmcgui.Dialog().notification("Success", "TMDB API key saved", xbmcgui.NOTIFICATION_INFO)
        
        addon.setSetting('tmdb_key_prompted', 'true')


def _fetch_single_image(tmdb_id, media_type, api_key, results):
    """Fetch images for a single item (used in threading)"""
    if not tmdb_id:
        return
    
    # Check cache first
    cache_key = f"{media_type}_{tmdb_id}"
    if cache_key in _image_cache:
        results[tmdb_id] = _image_cache[cache_key]
        return
    
    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={api_key}"
        data = _http_get(url, timeout=5)
        
        if data:
            poster = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else ''
            backdrop = f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get('backdrop_path') else ''
            
            result = {'poster': poster, 'backdrop': backdrop}
            results[tmdb_id] = result
            _image_cache[cache_key] = result
    except Exception as e:
        xbmc.log(f"TMDB image fetch error for {tmdb_id}: {e}", xbmc.LOGWARNING)


def get_images_batch(tmdb_ids, media_type='movie'):
    """
    Fetch images for multiple items in parallel (much faster than sequential)
    Returns dict: {tmdb_id: {'poster': url, 'backdrop': url}}
    """
    if not tmdb_ids:
        return {}
    
    api_key = get_api_key()
    results = {}
    threads = []
    
    # Limit concurrent requests to avoid overwhelming the API
    max_threads = 10
    
    for tmdb_id in tmdb_ids[:30]:  # Limit to 30 items max
        if tmdb_id:
            # Check cache first
            cache_key = f"{media_type}_{tmdb_id}"
            if cache_key in _image_cache:
                results[tmdb_id] = _image_cache[cache_key]
                continue
            
            t = threading.Thread(
                target=_fetch_single_image,
                args=(tmdb_id, media_type, api_key, results)
            )
            threads.append(t)
    
    # Start threads in batches
    for i in range(0, len(threads), max_threads):
        batch = threads[i:i+max_threads]
        for t in batch:
            t.start()
        for t in batch:
            t.join(timeout=5)  # 5 second timeout per batch
    
    return results


def get_details(tmdb_id, media_type='movie'):
    """Get movie or TV show details from TMDB"""
    if not tmdb_id:
        return {'overview': '', 'poster': '', 'backdrop': '', 'runtime': 0}
    
    key = get_api_key()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    url = f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}?api_key={key}"
    
    try:
        data = _http_get(url)
        if not data:
            return {'overview': '', 'poster': '', 'backdrop': '', 'runtime': 0}
        
        poster = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else ''
        backdrop = f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get('backdrop_path') else ''
        
        return {
            'overview': data.get('overview', ''),
            'poster': poster,
            'backdrop': backdrop,
            'runtime': data.get('runtime', 0),
            'rating': data.get('vote_average', 0),
            'genres': [g['name'] for g in data.get('genres', [])],
            'year': (data.get('release_date') or data.get('first_air_date', ''))[:4]
        }
    except Exception as e:
        xbmc.log(f"TMDB details error: {str(e)}", xbmc.LOGERROR)
        return {'overview': '', 'poster': '', 'backdrop': '', 'runtime': 0}


def search(query, media_type='movie'):
    """Search TMDB for movies or TV shows"""
    key = get_api_key()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    url = f"https://api.themoviedb.org/3/search/{endpoint}?api_key={key}&query={quote_plus(query)}"
    
    try:
        data = _http_get(url)
        return data.get('results', []) if data else []
    except:
        return []


def get_genres(media_type):
    """List genres and display in Kodi"""
    key = get_api_key()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    url = f"https://api.themoviedb.org/3/genre/{endpoint}/list?api_key={key}"
    
    try:
        data = _http_get(url)
        if not data:
            return
        
        genres = data.get('genres', [])
        for g in genres:
            list_url = f"{sys.argv[0]}?action=trakt_list&path={endpoint}s/popular&genre={g['id']}"
            xbmcplugin.addDirectoryItem(
                int(sys.argv[1]), 
                list_url, 
                xbmcgui.ListItem(label=g['name']), 
                isFolder=True
            )
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
    except Exception as e:
        xbmc.log(f"TMDB genres error: {str(e)}", xbmc.LOGERROR)


def get_season_episodes(tmdb_id, season_number):
    """Get episodes for a TV show season"""
    key = get_api_key()
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}?api_key={key}"
    
    try:
        data = _http_get(url)
        return data.get('episodes', []) if data else []
    except:
        return []


def get_tv_seasons(tmdb_id):
    """Get all seasons for a TV show"""
    key = get_api_key()
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={key}"
    
    try:
        data = _http_get(url)
        return data.get('seasons', []) if data else []
    except:
        return []
