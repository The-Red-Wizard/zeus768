# -*- coding: utf-8 -*-
"""
TMDB API Integration for Orion
"""

import urllib.request
import urllib.parse
import json
import ssl

TMDB_API_KEY = "f15af109700aab95d564acda15bdcd97"
BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE_URL = "https://image.tmdb.org/t/p"
SSL_CONTEXT = ssl._create_unverified_context()

def fetch_json(endpoint, params=None):
    """Fetch JSON from TMDB API"""
    url = f"{BASE_URL}{endpoint}"
    
    # Build query parameters
    query_params = {'api_key': TMDB_API_KEY}
    if params:
        query_params.update(params)
    
    url += "?" + urllib.parse.urlencode(query_params)
    
    headers = {'User-Agent': 'Orion/2.0'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"TMDB API Error: {e}")
        return {"results": [], "total_pages": 1}

def get_poster_url(path, size='w500'):
    """Get full poster URL"""
    if path:
        return f"{IMG_BASE_URL}/{size}{path}"
    return None

def get_backdrop_url(path, size='w1280'):
    """Get full backdrop URL"""
    if path:
        return f"{IMG_BASE_URL}/{size}{path}"
    return None

def get_genres(media_type):
    """Get list of genres for movies or TV"""
    data = fetch_json(f"/genre/{media_type}/list")
    return data.get('genres', [])

def get_category(media_type, category, page=1):
    """Get content by category"""
    endpoint = f"/{media_type}/{category}"
    return fetch_json(endpoint, {'page': page})

def get_by_genre(media_type, genre_id, page=1):
    """Get content by genre"""
    return fetch_json(f"/discover/{media_type}", {
        'with_genres': genre_id,
        'page': page,
        'sort_by': 'popularity.desc'
    })

def search_content(media_type, query, page=1):
    """Search movies or TV shows"""
    return fetch_json(f"/search/{media_type}", {
        'query': query,
        'page': page
    })

def search_people(query):
    """Search for people/actors"""
    return fetch_json("/search/person", {'query': query})

def get_person_credits(person_id, media_type='movie'):
    """Get person's filmography"""
    data = fetch_json(f"/person/{person_id}/combined_credits")
    
    # Filter by media type
    if media_type == 'movie':
        results = [item for item in data.get('cast', []) if item.get('media_type') == 'movie']
    else:
        results = [item for item in data.get('cast', []) if item.get('media_type') == 'tv']
    
    # Sort by popularity
    results.sort(key=lambda x: x.get('popularity', 0), reverse=True)
    
    return {'results': results[:50], 'total_pages': 1}

def get_movie_details(movie_id):
    """Get movie details"""
    return fetch_json(f"/movie/{movie_id}")

def get_tv_details(show_id):
    """Get TV show details including seasons"""
    return fetch_json(f"/tv/{show_id}")

def get_season_episodes(show_id, season_number):
    """Get episodes for a season"""
    return fetch_json(f"/tv/{show_id}/season/{season_number}")

def get_external_ids(media_type, item_id):
    """Get external IDs (IMDB, etc.)"""
    return fetch_json(f"/{media_type}/{item_id}/external_ids")

def get_kids_movies(page=1, certification='G,PG'):
    """Get family-friendly movies (G, PG rated)"""
    return fetch_json("/discover/movie", {
        'certification_country': 'US',
        'certification.lte': 'PG',
        'sort_by': 'popularity.desc',
        'page': page,
        'vote_count.gte': 100
    })

def get_animation_movies(page=1):
    """Get animated movies"""
    return fetch_json("/discover/movie", {
        'with_genres': '16',  # Animation genre ID
        'sort_by': 'popularity.desc',
        'page': page
    })

def get_kids_animation(page=1):
    """Get family-friendly animated movies (kids under 12)"""
    return fetch_json("/discover/movie", {
        'with_genres': '16,10751',  # Animation + Family
        'certification_country': 'US',
        'certification.lte': 'PG',
        'sort_by': 'popularity.desc',
        'page': page,
        'vote_count.gte': 50
    })

def get_kids_tvshows(page=1):
    """Get family-friendly TV shows"""
    return fetch_json("/discover/tv", {
        'with_genres': '10762,16',  # Kids + Animation
        'sort_by': 'popularity.desc',
        'page': page
    })

def get_family_movies(page=1):
    """Get family genre movies"""
    return fetch_json("/discover/movie", {
        'with_genres': '10751',  # Family genre
        'sort_by': 'popularity.desc',
        'page': page
    })

def get_disney_style_movies(page=1):
    """Get Disney-style family animation"""
    return fetch_json("/discover/movie", {
        'with_genres': '16,10751',
        'with_companies': '2|3|521',  # Disney, Pixar, DreamWorks
        'sort_by': 'popularity.desc',
        'page': page
    })