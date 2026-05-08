"""
TMDB API Module for Genesis
Uses native urllib (no external requests module)
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

USER_AGENT = 'Genesis Kodi Addon'

# User's TMDB API key
DEFAULT_TMDB_KEY = "f15af109700aab95d564acda15bdcd97"

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
        addon.setSetting('tmdb_key_prompted', 'true')


def _fetch_single_image(tmdb_id, media_type, api_key, results):
    """Fetch images for a single item (used in threading)"""
    if not tmdb_id:
        return
    
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
    """Fetch images for multiple items in parallel"""
    if not tmdb_ids:
        return {}
    
    api_key = get_api_key()
    results = {}
    threads = []
    
    max_threads = 10
    
    for tmdb_id in tmdb_ids[:30]:
        if tmdb_id:
            cache_key = f"{media_type}_{tmdb_id}"
            if cache_key in _image_cache:
                results[tmdb_id] = _image_cache[cache_key]
                continue
            
            t = threading.Thread(
                target=_fetch_single_image,
                args=(tmdb_id, media_type, api_key, results)
            )
            threads.append(t)
    
    for i in range(0, len(threads), max_threads):
        batch = threads[i:i+max_threads]
        for t in batch:
            t.start()
        for t in batch:
            t.join(timeout=5)
    
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
    """List genres and display in Kodi - uses TMDB discover by genre"""
    key = get_api_key()
    # media_type comes as 'movie' or 'tv'
    endpoint = media_type if media_type in ('movie', 'tv') else 'movie'
    url = f"https://api.themoviedb.org/3/genre/{endpoint}/list?api_key={key}"
    
    try:
        data = _http_get(url)
        if not data:
            return
        
        genres = data.get('genres', [])
        for g in genres:
            # Use genre_discover action with proper media_type
            list_url = f"{sys.argv[0]}?action=genre_discover&media_type={endpoint}&genre_id={g['id']}&genre_name={quote_plus(g['name'])}"
            li = xbmcgui.ListItem(label=g['name'])
            xbmcplugin.addDirectoryItem(
                int(sys.argv[1]), 
                list_url, 
                li, 
                isFolder=True
            )
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
    except Exception as e:
        xbmc.log(f"TMDB genres error: {str(e)}", xbmc.LOGERROR)


def discover_by_genre(media_type, genre_id, page=1):
    """Discover movies/shows by genre using TMDB"""
    key = get_api_key()
    endpoint = media_type if media_type in ('movie', 'tv') else 'movie'
    url = f"https://api.themoviedb.org/3/discover/{endpoint}?api_key={key}&with_genres={genre_id}&sort_by=popularity.desc&page={page}"
    
    try:
        data = _http_get(url)
        if not data:
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
            return
        
        results = data.get('results', [])
        handle = int(sys.argv[1])
        
        for item in results:
            tmdb_id = item.get('id')
            if endpoint == 'movie':
                title = item.get('title', 'Unknown')
                year = (item.get('release_date') or '')[:4]
            else:
                title = item.get('name', 'Unknown')
                year = (item.get('first_air_date') or '')[:4]
            
            poster = f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get('poster_path') else ''
            backdrop = f"https://image.tmdb.org/t/p/original{item.get('backdrop_path')}" if item.get('backdrop_path') else ''
            overview = item.get('overview', '')
            rating = item.get('vote_average', 0)
            
            label = f"{title} ({year})" if year else title
            li = xbmcgui.ListItem(label=label)
            li.setArt({
                'poster': poster,
                'fanart': backdrop,
                'thumb': poster,
                'icon': poster
            })
            
            info = {
                'title': title,
                'year': int(year) if year else 0,
                'plot': overview,
                'rating': rating
            }
            
            if endpoint == 'movie':
                info['mediatype'] = 'movie'
                li.setInfo('video', info)
                li.setProperty('IsPlayable', 'true')
                
                # Add X-Ray and Extras context menu
                li.addContextMenuItems([
                    ('X-Ray: Cast & Info', f'RunPlugin(plugin://plugin.video.genesis/?action=xray&tmdb_id={tmdb_id}&media_type=movie&title={quote_plus(title)})'),
                    ('Extras: Similar & Cast', f'Container.Update(plugin://plugin.video.genesis/?action=extras_menu&tmdb_id={tmdb_id}&media_type=movie&title={quote_plus(title)})'),
                ])
                
                play_url = f"{sys.argv[0]}?action=play&title={quote_plus(title)}&year={year}&tmdb_id={tmdb_id}"
                xbmcplugin.addDirectoryItem(handle, play_url, li, False)
            else:
                info['mediatype'] = 'tvshow'
                li.setInfo('video', info)
                
                # Add X-Ray context menu for TV shows
                li.addContextMenuItems([
                    ('X-Ray: Cast & Info', f'RunPlugin(plugin://plugin.video.genesis/?action=xray&tmdb_id={tmdb_id}&media_type=tv&title={quote_plus(title)})'),
                ])
                
                show_url = f"{sys.argv[0]}?action=show_seasons&tmdb_id={tmdb_id}&title={quote_plus(title)}"
                xbmcplugin.addDirectoryItem(handle, show_url, li, True)
        
        # Add next page
        total_pages = data.get('total_pages', 1)
        if page < total_pages and page < 10:  # Limit to 10 pages
            next_li = xbmcgui.ListItem(label=f'[B][COLOR yellow]>>> Next Page ({page + 1}) >>>[/COLOR][/B]')
            next_url = f"{sys.argv[0]}?action=genre_discover&media_type={endpoint}&genre_id={genre_id}&page={page + 1}"
            xbmcplugin.addDirectoryItem(handle, next_url, next_li, True)
        
        content_type = 'movies' if endpoint == 'movie' else 'tvshows'
        xbmcplugin.setContent(handle, content_type)
        xbmcplugin.endOfDirectory(handle, cacheToDisc=True)
        
    except Exception as e:
        xbmc.log(f"TMDB discover error: {str(e)}", xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))


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


def get_latest_releases(page=1):
    """Get movies currently in cinemas using now_playing endpoint"""
    key = get_api_key()
    url = f"https://api.themoviedb.org/3/movie/now_playing?api_key={key}&language=en-US&page={page}"
    
    try:
        data = _http_get(url)
        if not data:
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
            return
        
        results = data.get('results', [])
        handle = int(sys.argv[1])
        
        for item in results:
            tmdb_id = item.get('id')
            title = item.get('title', 'Unknown')
            year = (item.get('release_date') or '')[:4]
            
            poster = f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get('poster_path') else ''
            backdrop = f"https://image.tmdb.org/t/p/original{item.get('backdrop_path')}" if item.get('backdrop_path') else ''
            overview = item.get('overview', '')
            rating = item.get('vote_average', 0)
            
            label = f"{title} ({year})" if year else title
            li = xbmcgui.ListItem(label=label)
            li.setArt({
                'poster': poster,
                'fanart': backdrop,
                'thumb': poster,
                'icon': poster
            })
            
            info_tag = li.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setYear(int(year) if year else 0)
            info_tag.setPlot(overview)
            info_tag.setRating(rating)
            info_tag.setMediaType('movie')
            
            li.setProperty('IsPlayable', 'true')
            
            # Add X-Ray and Extras context menu
            li.addContextMenuItems([
                ('X-Ray: Cast & Info', f'RunPlugin(plugin://plugin.video.genesis/?action=xray&tmdb_id={tmdb_id}&media_type=movie&title={quote_plus(title)})'),
                ('Extras: Similar & Cast', f'Container.Update(plugin://plugin.video.genesis/?action=extras_menu&tmdb_id={tmdb_id}&media_type=movie&title={quote_plus(title)})'),
            ])
            
            play_url = f"{sys.argv[0]}?action=play&title={quote_plus(title)}&year={year}&tmdb_id={tmdb_id}"
            xbmcplugin.addDirectoryItem(handle, play_url, li, False)
        
        # Add next page
        total_pages = data.get('total_pages', 1)
        if page < total_pages and page < 10:
            next_li = xbmcgui.ListItem(label=f'[B][COLOR yellow]>>> Next Page ({page + 1}) >>>[/COLOR][/B]')
            next_url = f"{sys.argv[0]}?action=latest_releases&page={page + 1}"
            xbmcplugin.addDirectoryItem(handle, next_url, next_li, True)
        
        xbmcplugin.setContent(handle, 'movies')
        xbmcplugin.endOfDirectory(handle, cacheToDisc=True)
        
    except Exception as e:
        xbmc.log(f"TMDB now_playing error: {str(e)}", xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
