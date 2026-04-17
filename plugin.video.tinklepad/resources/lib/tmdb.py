"""
Tinklepad TMDB Module
Enhanced metadata support with cast, ratings, runtime, and more
Now with caching for faster menu loading
"""
import requests
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import xbmc
import sys
import os
import json
import time
import urllib.parse

ADDON = xbmcaddon.Addon()
BASE_URL = 'https://api.themoviedb.org/3'
IMG_BASE = 'https://image.tmdb.org/t/p'

# Default TMDB API Key
DEFAULT_TMDB_KEY = 'f15af109700aab95d564acda15bdcd97'

# Cache settings
CACHE_DIR = xbmcvfs.translatePath('special://temp/tinklepad_cache/')
CACHE_EXPIRY_SHORT = 1800   # 30 mins for trending/popular
CACHE_EXPIRY_LONG = 86400   # 24 hours for static content (genres, years)


def ensure_cache_dir():
    """Ensure cache directory exists"""
    if not xbmcvfs.exists(CACHE_DIR):
        xbmcvfs.mkdirs(CACHE_DIR)


def get_cache(cache_key, expiry=CACHE_EXPIRY_SHORT):
    """Get cached data if valid"""
    try:
        ensure_cache_dir()
        cache_file = os.path.join(CACHE_DIR, f'{cache_key}.json')
        if xbmcvfs.exists(cache_file):
            stat = xbmcvfs.Stat(cache_file)
            if time.time() - stat.st_mtime() < expiry:
                with xbmcvfs.File(cache_file, 'r') as f:
                    data = f.read()
                    if data:
                        return json.loads(data)
    except Exception as e:
        xbmc.log(f'[Tinklepad] Cache read error: {e}', xbmc.LOGDEBUG)
    return None


def set_cache(cache_key, data):
    """Save data to cache"""
    try:
        ensure_cache_dir()
        cache_file = os.path.join(CACHE_DIR, f'{cache_key}.json')
        with xbmcvfs.File(cache_file, 'w') as f:
            f.write(json.dumps(data))
    except Exception as e:
        xbmc.log(f'[Tinklepad] Cache write error: {e}', xbmc.LOGDEBUG)


def clear_all_cache():
    """Clear all cached data"""
    try:
        if xbmcvfs.exists(CACHE_DIR):
            dirs, files = xbmcvfs.listdir(CACHE_DIR)
            for f in files:
                xbmcvfs.delete(os.path.join(CACHE_DIR, f))
        return True
    except:
        return False

def get_key():
    """Get TMDB API key from settings or use default"""
    key = ADDON.getSetting('tmdb_api')
    if not key or key.strip() == '':
        return DEFAULT_TMDB_KEY
    return key

def get_headers():
    """Get request headers"""
    return {'Accept': 'application/json'}

# ==================== GENRE LISTS ====================

MOVIE_GENRES = {
    28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy',
    80: 'Crime', 99: 'Documentary', 18: 'Drama', 10751: 'Family',
    14: 'Fantasy', 36: 'History', 27: 'Horror', 10402: 'Music',
    9648: 'Mystery', 10749: 'Romance', 878: 'Science Fiction',
    10770: 'TV Movie', 53: 'Thriller', 10752: 'War', 37: 'Western'
}

TV_GENRES = {
    10759: 'Action & Adventure', 16: 'Animation', 35: 'Comedy',
    80: 'Crime', 99: 'Documentary', 18: 'Drama', 10751: 'Family',
    10762: 'Kids', 9648: 'Mystery', 10763: 'News', 10764: 'Reality',
    10765: 'Sci-Fi & Fantasy', 10766: 'Soap', 10767: 'Talk',
    10768: 'War & Politics', 37: 'Western'
}

NETWORKS = {
    213: 'Netflix', 1024: 'Amazon Prime Video', 2739: 'Disney+',
    453: 'Hulu', 2552: 'Apple TV+', 49: 'HBO', 2697: 'HBO Max',
    67: 'Showtime', 16: 'CBS', 6: 'NBC', 2: 'ABC', 19: 'FOX',
    174: 'AMC', 4: 'BBC One', 71: 'The CW', 88: 'FX', 318: 'Starz',
    359: 'Cinemax', 1: 'Fuji TV', 614: 'Paramount+'
}

# ==================== HELPER FUNCTIONS ====================

def get_metadata(tmdb_id, content_type='movie'):
    """Fetch basic metadata (fanart, plot) for a title"""
    api_key = get_key()
    if not api_key or not tmdb_id:
        return None
    
    try:
        endpoint = 'movie' if content_type == 'movie' else 'tv'
        url = f'{BASE_URL}/{endpoint}/{tmdb_id}?api_key={api_key}'
        response = requests.get(url, headers=get_headers(), timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            backdrop = data.get('backdrop_path')
            
            return {
                'fanart': f'{IMG_BASE}/w1280{backdrop}' if backdrop else '',
                'plot': data.get('overview', ''),
                'title': data.get('title') or data.get('name', ''),
                'year': (data.get('release_date') or data.get('first_air_date', ''))[:4],
                'rating': data.get('vote_average', 0)
            }
    except Exception as e:
        pass
    return None


def get_full_metadata(tmdb_id, content_type='movie'):
    """
    Fetch full metadata for source search overlay display
    Returns: fanart, poster, plot, title, year, rating, runtime, genres
    """
    api_key = get_key()
    if not api_key or not tmdb_id:
        return {}
    
    try:
        endpoint = 'movie' if content_type == 'movie' else 'tv'
        url = f'{BASE_URL}/{endpoint}/{tmdb_id}?api_key={api_key}'
        response = requests.get(url, headers=get_headers(), timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Images
            backdrop = data.get('backdrop_path')
            poster = data.get('poster_path')
            
            # Genres
            genre_list = [g.get('name', '') for g in data.get('genres', [])]
            genres_str = ' • '.join(genre_list[:4])  # Limit to 4 genres
            
            # Runtime
            if content_type == 'movie':
                runtime = data.get('runtime', 0)
            else:
                # For TV, use episode runtime average
                runtimes = data.get('episode_run_time', [])
                runtime = runtimes[0] if runtimes else 0
            
            return {
                'fanart': f'{IMG_BASE}/w1280{backdrop}' if backdrop else '',
                'poster': f'{IMG_BASE}/w500{poster}' if poster else '',
                'plot': data.get('overview', ''),
                'title': data.get('title') or data.get('name', ''),
                'year': (data.get('release_date') or data.get('first_air_date', ''))[:4],
                'rating': str(data.get('vote_average', 0)),
                'runtime': str(runtime),
                'genres': genres_str
            }
    except Exception as e:
        import xbmc
        xbmc.log(f'[Tinklepad] get_full_metadata error: {e}', xbmc.LOGERROR)
    
    return {}

def show_genres(m_type):
    """Display genre list"""
    from resources.lib import gui
    
    genres = MOVIE_GENRES if m_type == 'movie' else TV_GENRES
    genre_icon = os.path.join(gui.MEDIA, 'm_genres.png')
    
    for genre_id, genre_name in sorted(genres.items(), key=lambda x: x[1]):
        li = xbmcgui.ListItem(genre_name)
        li.setArt({'icon': genre_icon, 'thumb': genre_icon, 'fanart': gui.FANART})
        url = f"{sys.argv[0]}?action=list_content&type={m_type}&genre_id={genre_id}"
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, True)
    
    xbmcplugin.setContent(int(sys.argv[1]), 'addons')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def show_years(m_type):
    """Display year list"""
    from resources.lib import gui
    
    year_icon = os.path.join(gui.MEDIA, 'm_years.png')
    
    for year in range(2026, 1960, -1):
        li = xbmcgui.ListItem(str(year))
        li.setArt({'icon': year_icon, 'thumb': year_icon, 'fanart': gui.FANART})
        url = f"{sys.argv[0]}?action=list_content&type={m_type}&year={year}"
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, True)
    
    xbmcplugin.setContent(int(sys.argv[1]), 'years')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def show_networks():
    """Display TV network list"""
    from resources.lib import gui
    
    net_icon = os.path.join(gui.MEDIA, 't_nets.png')
    
    for net_id, net_name in sorted(NETWORKS.items(), key=lambda x: x[1]):
        li = xbmcgui.ListItem(net_name)
        li.setArt({'icon': net_icon, 'thumb': net_icon, 'fanart': gui.FANART})
        url = f"{sys.argv[0]}?action=list_content&type=tv&net_id={net_id}"
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, True)
    
    xbmcplugin.setContent(int(sys.argv[1]), 'addons')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def show_actors(m_type):
    """Display popular actors"""
    api_key = get_key()
    if not api_key:
        xbmcgui.Dialog().ok("Tinklepad", "TMDB API Key required!")
        return
    
    from resources.lib import gui
    
    try:
        url = f'{BASE_URL}/person/popular?api_key={api_key}'
        response = requests.get(url, headers=get_headers(), timeout=10)
        data = response.json()
        
        for person in data.get('results', []):
            name = person.get('name', '')
            person_id = person.get('id')
            profile = person.get('profile_path')
            
            img = f'{IMG_BASE}/w185{profile}' if profile else ''
            
            li = xbmcgui.ListItem(name)
            li.setArt({'icon': img, 'thumb': img, 'fanart': gui.FANART, 'poster': img})
            
            # Set actor info
            li.setInfo('video', {
                'title': name,
                'plot': f"Known for: {', '.join([m.get('title', m.get('name', '')) for m in person.get('known_for', [])[:3]])}"
            })
            
            url = f"{sys.argv[0]}?action=actor_content&type={m_type}&person_id={person_id}&name={urllib.parse.quote(name)}"
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, True)
        
        xbmcplugin.setContent(int(sys.argv[1]), 'actors')
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        
    except Exception as e:
        xbmcgui.Dialog().notification("Tinklepad", f"Error: {e}", xbmcgui.NOTIFICATION_ERROR, 3000)

def show_actor_content(m_type, person_id, name):
    """Show movies/shows for specific actor"""
    api_key = get_key()
    if not api_key:
        return
    
    from resources.lib import gui
    
    try:
        endpoint = 'movie_credits' if m_type == 'movie' else 'tv_credits'
        url = f'{BASE_URL}/person/{person_id}/{endpoint}?api_key={api_key}'
        response = requests.get(url, headers=get_headers(), timeout=10)
        data = response.json()
        
        items = data.get('cast', [])
        # Sort by popularity
        items.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        
        for item in items[:50]:
            add_content_item(int(sys.argv[1]), item, m_type)
        
        xbmcplugin.setContent(int(sys.argv[1]), 'movies' if m_type == 'movie' else 'tvshows')
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        
    except Exception as e:
        xbmcgui.Dialog().notification("Tinklepad", f"Error: {e}", xbmcgui.NOTIFICATION_ERROR, 3000)

# ==================== CONTENT LISTING ====================

def get_content_details(content_id, m_type):
    """Get detailed info for a movie/show"""
    api_key = get_key()
    if not api_key:
        return None
    
    try:
        url = f'{BASE_URL}/{m_type}/{content_id}?api_key={api_key}&append_to_response=credits,videos,external_ids'
        response = requests.get(url, headers=get_headers(), timeout=10)
        return response.json()
    except:
        return None

def add_content_item(handle, item, m_type, detailed=False):
    """Add a content item to the directory listing"""
    from resources.lib import gui
    
    content_id = item.get('id')
    title = item.get('title') if m_type == 'movie' else item.get('name')
    
    if not title:
        return
    
    # Images
    poster = item.get('poster_path')
    backdrop = item.get('backdrop_path')
    poster_url = f'{IMG_BASE}/w500{poster}' if poster else ''
    fanart_url = f'{IMG_BASE}/w1280{backdrop}' if backdrop else gui.FANART
    
    # Basic info
    year = ''
    if m_type == 'movie' and item.get('release_date'):
        year = item['release_date'][:4]
    elif m_type == 'tv' and item.get('first_air_date'):
        year = item['first_air_date'][:4]
    
    overview = item.get('overview', '')
    rating = item.get('vote_average', 0)
    votes = item.get('vote_count', 0)
    
    # Create list item
    display_title = f"{title} ({year})" if year else title
    li = xbmcgui.ListItem(display_title)
    
    # Set art
    li.setArt({
        'icon': poster_url,
        'thumb': poster_url,
        'poster': poster_url,
        'fanart': fanart_url,
        'banner': fanart_url
    })
    
    # Build info dict
    info = {
        'title': title,
        'year': int(year) if year else 0,
        'plot': overview,
        'rating': rating,
        'votes': votes,
        'mediatype': 'movie' if m_type == 'movie' else 'tvshow'
    }
    
    # Add detailed info if available
    if detailed or 'runtime' in item:
        if m_type == 'movie':
            info['duration'] = item.get('runtime', 0) * 60  # Convert to seconds
            info['premiered'] = item.get('release_date', '')
            info['tagline'] = item.get('tagline', '')
            info['status'] = item.get('status', '')
            
            # Genres
            genres = [g.get('name') for g in item.get('genres', [])]
            info['genre'] = ', '.join(genres)
            
            # Production companies
            studios = [c.get('name') for c in item.get('production_companies', [])[:3]]
            info['studio'] = ', '.join(studios)
            
            # Credits
            credits = item.get('credits', {})
            cast = credits.get('cast', [])
            crew = credits.get('crew', [])
            
            # Director
            directors = [c.get('name') for c in crew if c.get('job') == 'Director']
            if directors:
                info['director'] = ', '.join(directors[:2])
            
            # Writer
            writers = [c.get('name') for c in crew if c.get('job') in ['Writer', 'Screenplay']]
            if writers:
                info['writer'] = ', '.join(writers[:2])
            
            # Cast (for cast info)
            if cast:
                cast_list = [(c.get('name'), c.get('character', '')) for c in cast[:10]]
                li.setCast([{'name': n, 'role': r} for n, r in cast_list])
        
        else:  # TV Show
            info['premiered'] = item.get('first_air_date', '')
            info['status'] = item.get('status', '')
            
            seasons = item.get('number_of_seasons', 0)
            episodes = item.get('number_of_episodes', 0)
            info['season'] = seasons
            info['episode'] = episodes
            
            # Genres
            genres = [g.get('name') for g in item.get('genres', [])]
            info['genre'] = ', '.join(genres)
            
            # Networks
            networks = [n.get('name') for n in item.get('networks', [])]
            info['studio'] = ', '.join(networks)
            
            # Episode runtime
            runtimes = item.get('episode_run_time', [])
            if runtimes:
                info['duration'] = runtimes[0] * 60
    else:
        # Basic info from list results
        genres = item.get('genre_ids', [])
        genre_dict = MOVIE_GENRES if m_type == 'movie' else TV_GENRES
        genre_names = [genre_dict.get(g, '') for g in genres if g in genre_dict]
        info['genre'] = ', '.join(genre_names)
    
    li.setInfo('video', info)
    li.setProperty('IsPlayable', 'true')
    
    # Context menu
    context_menu = [
        ('More Info', f'RunPlugin({sys.argv[0]}?action=info&type={m_type}&id={content_id})'),
    ]
    li.addContextMenuItems(context_menu)
    
    # Build URL for playback
    url_params = {
        'action': 'play',
        'type': m_type,
        'id': content_id,
        'title': title,
        'year': year
    }
    url = f"{sys.argv[0]}?{urllib.parse.urlencode(url_params)}"
    
    xbmcplugin.addDirectoryItem(handle, url, li, False)

def list_content(handle, params):
    """List movies or TV shows based on parameters - with caching"""
    api_key = get_key()
    if not api_key:
        xbmcgui.Dialog().ok("Tinklepad", "Engine Error: TMDB API Key Missing!\n\nGo to Settings to add your API key.")
        return
    
    from resources.lib import gui
    
    m_type = params.get('type', 'movie')
    page = int(params.get('page', '1'))
    sort = params.get('sort', 'popular')
    
    # Build cache key
    cache_params = f"{m_type}_{sort}_{page}"
    if params.get('genre_id'):
        cache_params += f"_g{params['genre_id']}"
    if params.get('year'):
        cache_params += f"_y{params['year']}"
    if params.get('net_id'):
        cache_params += f"_n{params['net_id']}"
    
    cache_key = f"content_{cache_params}"
    
    # Try cache first
    cached_data = get_cache(cache_key, CACHE_EXPIRY_SHORT)
    if cached_data:
        xbmc.log(f'[Tinklepad] Using cached data for {cache_key}', xbmc.LOGDEBUG)
        data = cached_data
    else:
        # Build API URL
        if sort == 'trending':
            url = f'{BASE_URL}/trending/{m_type}/week?api_key={api_key}&page={page}'
        else:
            url = f'{BASE_URL}/discover/{m_type}?api_key={api_key}&page={page}&sort_by=popularity.desc'
        
        # Apply filters
        if params.get('genre_id'):
            url += f"&with_genres={params['genre_id']}"
        if params.get('year'):
            if m_type == 'movie':
                url += f"&primary_release_year={params['year']}"
            else:
                url += f"&first_air_date_year={params['year']}"
        if params.get('net_id'):
            url += f"&with_networks={params['net_id']}"
        if params.get('certification'):
            url += f"&certification_country=US&certification={params['certification']}"
        
        try:
            response = requests.get(url, headers=get_headers(), timeout=15)
            data = response.json()
            # Cache the response
            set_cache(cache_key, data)
        except requests.exceptions.Timeout:
            xbmcgui.Dialog().notification("Tinklepad", "Connection timed out", xbmcgui.NOTIFICATION_ERROR, 3000)
            return
        except Exception as e:
            xbmcgui.Dialog().notification("Tinklepad", f"Error: {e}", xbmcgui.NOTIFICATION_ERROR, 3000)
            return
    
    results = data.get('results', [])
    total_pages = data.get('total_pages', 1)
    
    for item in results:
        add_content_item(handle, item, m_type)
    
    # Add "Next Page" if more pages exist
    if page < total_pages and page < 500:  # TMDB limit
        next_params = params.copy()
        next_params['page'] = str(page + 1)
        next_params['action'] = 'list_content'
        
        li = xbmcgui.ListItem(f'[COLOR gold]Next Page ({page + 1}/{min(total_pages, 500)})[/COLOR]')
        next_icon = os.path.join(gui.MEDIA, 'next.png') if os.path.exists(os.path.join(gui.MEDIA, 'next.png')) else ''
        li.setArt({'icon': next_icon, 'fanart': gui.FANART})
        
        next_url = f"{sys.argv[0]}?{urllib.parse.urlencode(next_params)}"
        xbmcplugin.addDirectoryItem(handle, next_url, li, True)
    
    content_type = 'movies' if m_type == 'movie' else 'tvshows'
    xbmcplugin.setContent(handle, content_type)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)

def show_info(content_id, m_type):
    """Show detailed info dialog"""
    details = get_content_details(content_id, m_type)
    if not details:
        return
    
    title = details.get('title') if m_type == 'movie' else details.get('name')
    overview = details.get('overview', 'No overview available.')
    rating = details.get('vote_average', 0)
    year = ''
    
    if m_type == 'movie':
        year = details.get('release_date', '')[:4]
        runtime = details.get('runtime', 0)
        runtime_str = f"{runtime // 60}h {runtime % 60}m" if runtime else 'N/A'
    else:
        year = details.get('first_air_date', '')[:4]
        seasons = details.get('number_of_seasons', 0)
        episodes = details.get('number_of_episodes', 0)
        runtime_str = f"{seasons} Seasons, {episodes} Episodes"
    
    # Genres
    genres = ', '.join([g.get('name') for g in details.get('genres', [])])
    
    # Build info text
    info_text = f"[B]{title}[/B] ({year})\n\n"
    info_text += f"[COLOR gold]Rating:[/COLOR] {rating}/10\n"
    info_text += f"[COLOR gold]Runtime:[/COLOR] {runtime_str}\n"
    info_text += f"[COLOR gold]Genres:[/COLOR] {genres}\n\n"
    info_text += f"[COLOR gold]Overview:[/COLOR]\n{overview}"
    
    xbmcgui.Dialog().textviewer(f'{title} - Info', info_text)

def search(query, m_type='movie'):
    """Search for movies or TV shows"""
    api_key = get_key()
    if not api_key:
        return []
    
    try:
        search_type = 'movie' if m_type == 'movie' else 'tv'
        url = f'{BASE_URL}/search/{search_type}?api_key={api_key}&query={urllib.parse.quote(query)}'
        response = requests.get(url, headers=get_headers(), timeout=10)
        data = response.json()
        return data.get('results', [])
    except:
        return []

def global_search(handle, query, m_type=None):
    """Perform global search across movies and TV"""
    api_key = get_key()
    if not api_key:
        xbmcgui.Dialog().ok("Tinklepad", "TMDB API Key required!")
        return
    
    if not query:
        keyboard = xbmc.Keyboard('', 'Search Tinklepad')
        keyboard.doModal()
        if keyboard.isConfirmed():
            query = keyboard.getText()
        else:
            return
    
    if not query:
        return
    
    from resources.lib import gui
    
    try:
        # Search both movies and TV if no type specified
        if m_type:
            types_to_search = [m_type]
        else:
            types_to_search = ['movie', 'tv']
        
        all_results = []
        
        for search_type in types_to_search:
            url = f'{BASE_URL}/search/{search_type}?api_key={api_key}&query={urllib.parse.quote(query)}'
            response = requests.get(url, headers=get_headers(), timeout=10)
            data = response.json()
            
            for item in data.get('results', []):
                item['_type'] = search_type
                all_results.append(item)
        
        # Sort by popularity
        all_results.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        
        for item in all_results[:50]:
            add_content_item(handle, item, item['_type'])
        
        xbmcplugin.setContent(handle, 'videos')
        xbmcplugin.endOfDirectory(handle)
        
    except Exception as e:
        xbmcgui.Dialog().notification("Tinklepad", f"Search error: {e}", xbmcgui.NOTIFICATION_ERROR, 3000)

# Import xbmc for keyboard
