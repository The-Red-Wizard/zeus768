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
    
    for tmdb_id in tmdb_ids[:100]:  # Support larger lists (user lists can be 50+)
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
    """List genres and display in Kodi.

    FIX 2.4.4: Previously built a Trakt URL that was wrong (`tvs/popular` -> 405)
    and passed a `genre` query param that was never read (same list for every
    genre). Now routes each genre through the tmdb_discover action which filters
    correctly and supports infinite pagination.
    """
    key = get_api_key()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    url = f"https://api.themoviedb.org/3/genre/{endpoint}/list?api_key={key}"

    try:
        data = _http_get(url)
        if not data:
            return

        genres = data.get('genres', [])
        for g in genres:
            list_url = (f"{sys.argv[0]}?action=tmdb_discover"
                        f"&media_type={endpoint}&genre_id={g['id']}"
                        f"&label={quote_plus(g['name'])}&page=1")
            xbmcplugin.addDirectoryItem(
                int(sys.argv[1]),
                list_url,
                xbmcgui.ListItem(label=g['name']),
                isFolder=True
            )
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
    except Exception as e:
        xbmc.log(f"TMDB genres error: {str(e)}", xbmc.LOGERROR)


def _tmdb_list(url, media_type):
    """Internal: fetch a TMDB list endpoint and normalise to a list of dicts."""
    data = _http_get(url, timeout=10)
    if not data:
        return [], 0
    return data.get('results', []) or [], int(data.get('total_pages', 1))


def get_trending_movies(page=1):
    """TMDB trending movies - used by the Discovery Feed."""
    key = get_api_key()
    url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={key}&page={page}"
    items, _ = _tmdb_list(url, 'movie')
    return items


def get_trending_shows(page=1):
    """TMDB trending TV shows."""
    key = get_api_key()
    url = f"https://api.themoviedb.org/3/trending/tv/week?api_key={key}&page={page}"
    items, _ = _tmdb_list(url, 'tv')
    return items


def get_now_playing(page=1):
    """Movies currently in theaters."""
    key = get_api_key()
    url = f"https://api.themoviedb.org/3/movie/now_playing?api_key={key}&page={page}&region=US"
    items, _ = _tmdb_list(url, 'movie')
    return items


def get_upcoming_movies(page=1):
    """Upcoming theatrical releases."""
    key = get_api_key()
    url = f"https://api.themoviedb.org/3/movie/upcoming?api_key={key}&page={page}&region=US"
    items, _ = _tmdb_list(url, 'movie')
    return items


def get_trailer(tmdb_id, media_type='movie'):
    """Return the YouTube key of the best available trailer, or ''."""
    if not tmdb_id:
        return ''
    key = get_api_key()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    url = f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}/videos?api_key={key}"
    data = _http_get(url, timeout=6)
    if not data:
        return ''
    videos = data.get('results', []) or []
    # Prefer Trailer > Teaser, YouTube-hosted, official first
    def _score(v):
        s = 0
        if v.get('site', '').lower() == 'youtube': s += 10
        vtype = v.get('type', '').lower()
        if vtype == 'trailer': s += 6
        elif vtype == 'teaser': s += 3
        if v.get('official'): s += 2
        return s
    videos = [v for v in videos if v.get('key')]
    if not videos:
        return ''
    videos.sort(key=_score, reverse=True)
    return videos[0].get('key', '') if _score(videos[0]) > 0 else ''


def discover_by_genre(media_type, genre_id, page=1):
    """TMDB discover endpoint filtered by genre. Returns (items, total_pages)."""
    key = get_api_key()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    url = (f"https://api.themoviedb.org/3/discover/{endpoint}?api_key={key}"
           f"&with_genres={genre_id}&sort_by=popularity.desc&page={page}")
    return _tmdb_list(url, endpoint)


def _render_tmdb_items(items, total_pages, media_type, page, next_url_factory):
    """Shared renderer for TMDB-sourced directory listings.

    Adds infinite pagination: a "Next Page" tile is appended while page < total.
    """
    handle = int(sys.argv[1])
    try:
        from resources.lib import trakt_api as _ta
        addon_icon = _ta.get_addon_icon()
        addon_fanart = _ta.get_addon_fanart()
        ctx_builder = _ta._build_context_menu
    except Exception:
        addon_icon = ''
        addon_fanart = ''
        ctx_builder = lambda *a, **kw: []

    for item in items:
        tmdb_id = item.get('id')
        title = item.get('title') or item.get('name', 'Unknown')
        year = (item.get('release_date') or item.get('first_air_date', ''))[:4]
        overview = item.get('overview', '')
        rating = item.get('vote_average', 0)
        poster = ('https://image.tmdb.org/t/p/w500' + item['poster_path']) if item.get('poster_path') else ''
        backdrop = ('https://image.tmdb.org/t/p/original' + item['backdrop_path']) if item.get('backdrop_path') else ''

        label = f'{title} ({year})' if year else title
        li = xbmcgui.ListItem(label=label)
        li.setArt({'poster': poster or addon_icon,
                   'fanart': backdrop or addon_fanart,
                   'thumb': poster or addon_icon,
                   'icon': poster or addon_icon})

        info = {'title': title, 'year': year, 'plot': overview, 'rating': rating,
                'mediatype': 'movie' if media_type == 'movie' else 'tvshow'}
        li.setInfo('video', info)

        # Build context menu if we have an imdb id via external_ids lookup - skip
        # here to keep pagination fast; only context menu needs imdb_id.
        li.addContextMenuItems(ctx_builder(media_type, '', tmdb_id, title))

        if media_type == 'movie':
            li.setProperty('IsPlayable', 'true')
            play_url = f"{sys.argv[0]}?action=play&title={quote_plus(title)}&year={year}&imdb_id="
            xbmcplugin.addDirectoryItem(handle, play_url, li, False)
        else:
            show_url = f"{sys.argv[0]}?action=show_seasons&tmdb_id={tmdb_id}&title={quote_plus(title)}"
            xbmcplugin.addDirectoryItem(handle, show_url, li, True)

    # Next page tile (infinite pagination)
    if page < total_pages:
        next_li = xbmcgui.ListItem(
            label=f'[B][COLOR yellow]>>> Next Page ({page + 1}/{total_pages}) >>>[/COLOR][/B]'
        )
        next_li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        xbmcplugin.addDirectoryItem(handle, next_url_factory(page + 1), next_li, True)

    xbmcplugin.setContent(handle, 'movies' if media_type == 'movie' else 'tvshows')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def show_tmdb_list(endpoint, media_type='movie', page=1):
    """Render a TMDB-sourced list (now_playing / upcoming / trending) with pagination.

    v2.4.4: Box Office had only 10 items and no Next Page (bug #5).
    Now backed by TMDB now_playing, which paginates properly.
    """
    key = get_api_key()
    page = int(page)
    if endpoint == 'now_playing':
        url = f"https://api.themoviedb.org/3/movie/now_playing?api_key={key}&page={page}&region=US"
    elif endpoint == 'upcoming':
        url = f"https://api.themoviedb.org/3/movie/upcoming?api_key={key}&page={page}&region=US"
    elif endpoint == 'trending_movie':
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={key}&page={page}"
        media_type = 'movie'
    elif endpoint == 'trending_tv':
        url = f"https://api.themoviedb.org/3/trending/tv/week?api_key={key}&page={page}"
        media_type = 'tv'
    else:
        xbmcgui.Dialog().notification('TMDB', f'Unknown endpoint: {endpoint}', xbmcgui.NOTIFICATION_ERROR)
        return

    items, total_pages = _tmdb_list(url, media_type)
    if not items and page == 1:
        xbmcgui.Dialog().notification('TMDB', 'No results', xbmcgui.NOTIFICATION_INFO)

    next_factory = lambda n: (f"{sys.argv[0]}?action=tmdb_list&endpoint={endpoint}"
                              f"&media_type={media_type}&page={n}")
    _render_tmdb_items(items, total_pages, media_type, page, next_factory)


def show_genre_discover(media_type, genre_id, label='', page=1):
    """Infinite-pagination genre browse via /discover."""
    page = int(page)
    items, total_pages = discover_by_genre(media_type, genre_id, page=page)
    if not items and page == 1:
        xbmcgui.Dialog().notification('TMDB', f'No {label} results', xbmcgui.NOTIFICATION_INFO)

    next_factory = lambda n: (f"{sys.argv[0]}?action=tmdb_discover"
                              f"&media_type={media_type}&genre_id={genre_id}"
                              f"&label={quote_plus(label)}&page={n}")
    _render_tmdb_items(items, total_pages, media_type, page, next_factory)


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
