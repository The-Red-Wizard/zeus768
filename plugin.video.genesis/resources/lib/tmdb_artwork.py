# -*- coding: utf-8 -*-
"""
TMDb Artwork Fetcher for Local Media
Fetches posters, fanart, and backdrops for local movies and TV shows
"""
import json
import os
import re
import xbmc
import xbmcaddon
import xbmcvfs
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus

ADDON_ID = 'plugin.video.genesis'
USER_AGENT = 'Genesis Kodi Addon'

# Cache for artwork to avoid repeated API calls
_artwork_cache = {}
_cache_file = None

# TMDb API key - use from tmdb module
DEFAULT_TMDB_KEY = "f15af109700aab95d564acda15bdcd97"


def get_addon():
    return xbmcaddon.Addon()


def get_api_key():
    """Get TMDB API key"""
    addon = get_addon()
    user_key = addon.getSetting('tmdb_api_key')
    if user_key and len(user_key) > 10:
        return user_key
    return DEFAULT_TMDB_KEY


def _get_cache_path():
    """Get path to artwork cache file"""
    global _cache_file
    if _cache_file is None:
        addon_data = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
        if not xbmcvfs.exists(addon_data):
            xbmcvfs.mkdirs(addon_data)
        _cache_file = os.path.join(addon_data, 'artwork_cache.json')
    return _cache_file


def _load_cache():
    """Load artwork cache from disk"""
    global _artwork_cache
    cache_path = _get_cache_path()
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                _artwork_cache = json.load(f)
        except Exception as e:
            xbmc.log(f'TMDb Artwork: Cache load error: {e}', xbmc.LOGWARNING)
            _artwork_cache = {}


def _save_cache():
    """Save artwork cache to disk"""
    cache_path = _get_cache_path()
    try:
        with open(cache_path, 'w') as f:
            json.dump(_artwork_cache, f)
    except Exception as e:
        xbmc.log(f'TMDb Artwork: Cache save error: {e}', xbmc.LOGWARNING)


def _http_get(url, timeout=8):
    """HTTP GET request using urllib, returns json data or None"""
    try:
        req = Request(url, headers={'User-Agent': USER_AGENT}, method='GET')
        response = urlopen(req, timeout=timeout)
        body = response.read().decode('utf-8')
        return json.loads(body)
    except HTTPError as e:
        xbmc.log(f'TMDb Artwork HTTP Error: {e.code}', xbmc.LOGWARNING)
        return None
    except URLError as e:
        xbmc.log(f'TMDb Artwork URL Error: {e.reason}', xbmc.LOGERROR)
        return None
    except Exception as e:
        xbmc.log(f'TMDb Artwork Request Error: {e}', xbmc.LOGERROR)
        return None


def search_movie(title, year=None):
    """Search TMDb for a movie by title and optional year"""
    api_key = get_api_key()
    
    # Try with year first for better accuracy
    if year:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={quote_plus(title)}&year={year}"
        data = _http_get(url)
        if data and data.get('results'):
            return data['results'][0]
    
    # Search without year
    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={quote_plus(title)}"
    data = _http_get(url)
    
    if data and data.get('results'):
        # If year provided, try to find best match
        if year:
            for result in data['results']:
                release_date = result.get('release_date', '')
                if release_date and release_date.startswith(str(year)):
                    return result
        return data['results'][0]
    
    return None


def search_tv_show(title):
    """Search TMDb for a TV show by title"""
    api_key = get_api_key()
    url = f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={quote_plus(title)}"
    data = _http_get(url)
    
    if data and data.get('results'):
        return data['results'][0]
    
    return None


def get_movie_artwork(tmdb_id):
    """Get artwork URLs for a movie by TMDb ID"""
    api_key = get_api_key()
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}"
    data = _http_get(url)
    
    if not data:
        return {}
    
    artwork = {
        'tmdb_id': tmdb_id,
        'title': data.get('title', ''),
        'year': (data.get('release_date') or '')[:4],
        'overview': data.get('overview', ''),
        'rating': data.get('vote_average', 0),
    }
    
    if data.get('poster_path'):
        artwork['poster'] = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
        artwork['poster_thumb'] = f"https://image.tmdb.org/t/p/w185{data['poster_path']}"
    
    if data.get('backdrop_path'):
        artwork['fanart'] = f"https://image.tmdb.org/t/p/original{data['backdrop_path']}"
        artwork['banner'] = f"https://image.tmdb.org/t/p/w1280{data['backdrop_path']}"
    
    return artwork


def get_tv_artwork(tmdb_id, season=None, episode=None):
    """Get artwork URLs for a TV show by TMDb ID"""
    api_key = get_api_key()
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={api_key}"
    data = _http_get(url)
    
    if not data:
        return {}
    
    artwork = {
        'tmdb_id': tmdb_id,
        'title': data.get('name', ''),
        'year': (data.get('first_air_date') or '')[:4],
        'overview': data.get('overview', ''),
        'rating': data.get('vote_average', 0),
    }
    
    if data.get('poster_path'):
        artwork['poster'] = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
        artwork['poster_thumb'] = f"https://image.tmdb.org/t/p/w185{data['poster_path']}"
    
    if data.get('backdrop_path'):
        artwork['fanart'] = f"https://image.tmdb.org/t/p/original{data['backdrop_path']}"
        artwork['banner'] = f"https://image.tmdb.org/t/p/w1280{data['backdrop_path']}"
    
    # Get season/episode specific artwork if requested
    if season is not None:
        season_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season}?api_key={api_key}"
        season_data = _http_get(season_url)
        
        if season_data:
            if season_data.get('poster_path'):
                artwork['season_poster'] = f"https://image.tmdb.org/t/p/w500{season_data['poster_path']}"
            
            if episode is not None:
                for ep in season_data.get('episodes', []):
                    if ep.get('episode_number') == episode:
                        if ep.get('still_path'):
                            artwork['episode_thumb'] = f"https://image.tmdb.org/t/p/w500{ep['still_path']}"
                        artwork['episode_name'] = ep.get('name', '')
                        artwork['episode_overview'] = ep.get('overview', '')
                        break
    
    return artwork


def get_artwork_for_local_movie(title, year=None):
    """Get artwork for a local movie file"""
    # Load cache if not loaded
    if not _artwork_cache:
        _load_cache()
    
    # Create cache key
    cache_key = f"movie_{title.lower()}_{year or ''}"
    
    # Check cache
    if cache_key in _artwork_cache:
        return _artwork_cache[cache_key]
    
    # Search TMDb
    result = search_movie(title, year)
    
    if not result:
        return {}
    
    # Get detailed artwork
    artwork = get_movie_artwork(result['id'])
    
    # Cache result
    _artwork_cache[cache_key] = artwork
    _save_cache()
    
    return artwork


def get_artwork_for_local_tv(title, season=None, episode=None):
    """Get artwork for a local TV show file"""
    # Load cache if not loaded
    if not _artwork_cache:
        _load_cache()
    
    # Create cache key
    cache_key = f"tv_{title.lower()}"
    if season is not None:
        cache_key += f"_s{season}"
    if episode is not None:
        cache_key += f"_e{episode}"
    
    # Check cache (for basic show info)
    base_cache_key = f"tv_{title.lower()}"
    
    if base_cache_key in _artwork_cache:
        artwork = _artwork_cache[base_cache_key].copy()
        tmdb_id = artwork.get('tmdb_id')
        
        # If season/episode requested, get additional info
        if tmdb_id and (season is not None or episode is not None):
            extra_artwork = get_tv_artwork(tmdb_id, season, episode)
            artwork.update(extra_artwork)
        
        return artwork
    
    # Search TMDb
    result = search_tv_show(title)
    
    if not result:
        return {}
    
    # Get detailed artwork
    artwork = get_tv_artwork(result['id'], season, episode)
    
    # Cache result
    _artwork_cache[base_cache_key] = artwork
    _save_cache()
    
    return artwork


def enrich_local_media(media_list, media_type='movie', progress_callback=None):
    """Enrich a list of local media items with TMDb artwork
    
    Args:
        media_list: List of media items from local_scanner
        media_type: 'movie' or 'tv'
        progress_callback: Optional callback(percent, message) for progress updates
    
    Returns:
        Enriched media list with artwork URLs
    """
    total = len(media_list)
    
    for i, item in enumerate(media_list):
        if progress_callback:
            progress_callback(int((i / total) * 100), f"Fetching artwork: {item.get('title', 'Unknown')}")
        
        if media_type == 'movie':
            artwork = get_artwork_for_local_movie(
                item.get('title', ''),
                item.get('year')
            )
        else:
            artwork = get_artwork_for_local_tv(
                item.get('title', ''),
                item.get('season'),
                item.get('episode')
            )
        
        if artwork:
            item['artwork'] = artwork
            item['poster'] = artwork.get('poster', '')
            item['fanart'] = artwork.get('fanart', '')
            item['thumb'] = artwork.get('poster_thumb', artwork.get('poster', ''))
            if media_type == 'tv' and 'episode_thumb' in artwork:
                item['thumb'] = artwork['episode_thumb']
            item['tmdb_id'] = artwork.get('tmdb_id')
            item['overview'] = artwork.get('overview', '')
            item['rating'] = artwork.get('rating', 0)
    
    return media_list


def clear_artwork_cache():
    """Clear the artwork cache"""
    global _artwork_cache
    _artwork_cache = {}
    cache_path = _get_cache_path()
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            return True
        except:
            pass
    return False
