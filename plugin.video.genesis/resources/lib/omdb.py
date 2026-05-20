# -*- coding: utf-8 -*-
"""
OMDB API Module for Genesis
Provides multi-source ratings: IMDB, Rotten Tomatoes, Metacritic
Also: Awards, Box Office, Plot details
"""
import json
import xbmc
import xbmcaddon
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

USER_AGENT = 'Genesis Kodi Addon'

# Cache for OMDB data
_omdb_cache = {}


def get_addon():
    return xbmcaddon.Addon()


def _http_get(url, timeout=10):
    """HTTP GET helper"""
    try:
        req = Request(url, headers={'User-Agent': USER_AGENT})
        response = urlopen(req, timeout=timeout)
        return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        xbmc.log(f'OMDB HTTP Error: {e}', xbmc.LOGWARNING)
        return None


def get_api_key():
    """Get OMDB API key from settings"""
    addon = get_addon()
    return addon.getSetting('omdb_api_key') or ''


def get_movie_data(imdb_id=None, title=None, year=None):
    """
    Get comprehensive movie data from OMDB
    Returns: ratings, awards, box office, plot, etc.
    """
    api_key = get_api_key()
    if not api_key:
        return None
    
    # Build cache key
    cache_key = imdb_id or f"{title}_{year}"
    if cache_key in _omdb_cache:
        return _omdb_cache[cache_key]
    
    # Build URL
    if imdb_id:
        url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={api_key}&plot=full"
    elif title:
        url = f"http://www.omdbapi.com/?t={title}&apikey={api_key}&plot=full"
        if year:
            url += f"&y={year}"
    else:
        return None
    
    data = _http_get(url)
    
    if not data or data.get('Response') == 'False':
        return None
    
    # Parse ratings
    ratings = {}
    for rating in data.get('Ratings', []):
        source = rating.get('Source', '')
        value = rating.get('Value', '')
        
        if 'Internet Movie Database' in source:
            ratings['imdb'] = {
                'source': 'IMDb',
                'value': value,
                'score': value.split('/')[0] if '/' in value else value,
                'icon': 'imdb'
            }
        elif 'Rotten Tomatoes' in source:
            ratings['rotten_tomatoes'] = {
                'source': 'Rotten Tomatoes',
                'value': value,
                'score': value.replace('%', ''),
                'icon': 'rt'
            }
        elif 'Metacritic' in source:
            ratings['metacritic'] = {
                'source': 'Metacritic',
                'value': value,
                'score': value.split('/')[0] if '/' in value else value,
                'icon': 'mc'
            }
    
    # Add IMDb rating from main field if not in Ratings array
    if 'imdb' not in ratings and data.get('imdbRating') and data['imdbRating'] != 'N/A':
        ratings['imdb'] = {
            'source': 'IMDb',
            'value': f"{data['imdbRating']}/10",
            'score': data['imdbRating'],
            'votes': data.get('imdbVotes', ''),
            'icon': 'imdb'
        }
    
    result = {
        'title': data.get('Title', ''),
        'year': data.get('Year', ''),
        'rated': data.get('Rated', ''),
        'released': data.get('Released', ''),
        'runtime': data.get('Runtime', ''),
        'genre': data.get('Genre', ''),
        'director': data.get('Director', ''),
        'writer': data.get('Writer', ''),
        'actors': data.get('Actors', ''),
        'plot': data.get('Plot', ''),
        'language': data.get('Language', ''),
        'country': data.get('Country', ''),
        'awards': data.get('Awards', ''),
        'poster': data.get('Poster', ''),
        'ratings': ratings,
        'metascore': data.get('Metascore', ''),
        'imdb_rating': data.get('imdbRating', ''),
        'imdb_votes': data.get('imdbVotes', ''),
        'imdb_id': data.get('imdbID', ''),
        'type': data.get('Type', ''),
        'dvd': data.get('DVD', ''),
        'box_office': data.get('BoxOffice', ''),
        'production': data.get('Production', ''),
        'website': data.get('Website', '')
    }
    
    _omdb_cache[cache_key] = result
    return result


def format_ratings_display(ratings):
    """Format ratings for display in Kodi"""
    if not ratings:
        return []
    
    lines = []
    
    if 'imdb' in ratings:
        r = ratings['imdb']
        votes = f" ({r.get('votes', '')} votes)" if r.get('votes') else ''
        lines.append(f"[COLOR gold]IMDb:[/COLOR] {r['value']}{votes}")
    
    if 'rotten_tomatoes' in ratings:
        r = ratings['rotten_tomatoes']
        score = int(r['score']) if r['score'].isdigit() else 0
        color = 'lime' if score >= 60 else 'red'
        icon = 'Fresh' if score >= 60 else 'Rotten'
        lines.append(f"[COLOR {color}]Rotten Tomatoes ({icon}):[/COLOR] {r['value']}")
    
    if 'metacritic' in ratings:
        r = ratings['metacritic']
        score = int(r['score']) if r['score'].isdigit() else 0
        if score >= 61:
            color = 'lime'
            label = 'Generally Favorable'
        elif score >= 40:
            color = 'yellow'
            label = 'Mixed'
        else:
            color = 'red'
            label = 'Generally Unfavorable'
        lines.append(f"[COLOR {color}]Metacritic ({label}):[/COLOR] {r['value']}")
    
    return lines


def get_ratings_summary(imdb_id=None, title=None, year=None):
    """Get a brief ratings summary string"""
    data = get_movie_data(imdb_id, title, year)
    if not data or not data.get('ratings'):
        return ''
    
    parts = []
    ratings = data['ratings']
    
    if 'imdb' in ratings:
        parts.append(f"IMDb: {ratings['imdb']['score']}")
    if 'rotten_tomatoes' in ratings:
        parts.append(f"RT: {ratings['rotten_tomatoes']['value']}")
    if 'metacritic' in ratings:
        parts.append(f"MC: {ratings['metacritic']['score']}")
    
    return ' | '.join(parts)
