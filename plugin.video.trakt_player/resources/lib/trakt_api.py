import requests
import xbmcgui
import xbmcplugin
import sys
import xbmcaddon
import xbmc
from urllib.parse import urlencode, quote_plus
from . import tmdb
from . import trakt_auth

ADDON = xbmcaddon.Addon()

# Use same client ID as trakt_auth (Umbrella addon credentials)
CLIENT_ID = '87e3f055fc4d8fcfd96e61a47463327ca877c51e8597b448e132611c5a677b13'

def get_headers():
    """Get headers for Trakt API requests"""
    token = trakt_auth.get_token()
    headers = {
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': CLIENT_ID
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers

def get_list(path, media_type='movie'):
    """Fetch and display a Trakt list"""
    headers = get_headers()
    
    # Check if this needs authentication
    needs_auth = 'sync/' in path or 'users/' in path
    if needs_auth and not trakt_auth.is_authorized():
        xbmcgui.Dialog().notification('Trakt', 'Please authorize Trakt first', xbmcgui.NOTIFICATION_WARNING)
        trakt_auth.authorize()
        return
    
    try:
        url = f'https://api.trakt.tv/{path}?extended=full&limit=50'
        xbmc.log(f'Trakt API request: {url}', xbmc.LOGINFO)
        response = requests.get(url, headers=headers, timeout=15)
        
        xbmc.log(f'Trakt API response status: {response.status_code}', xbmc.LOGINFO)
        
        if response.status_code == 401:
            # Token expired, try refresh
            if trakt_auth.refresh_token():
                headers = get_headers()
                response = requests.get(url, headers=headers, timeout=15)
            else:
                xbmcgui.Dialog().notification('Trakt', 'Session expired. Please re-authorize.', xbmcgui.NOTIFICATION_WARNING)
                trakt_auth.authorize()
                return
        
        if response.status_code != 200:
            xbmcgui.Dialog().notification('Trakt', f'API error: {response.status_code}', xbmcgui.NOTIFICATION_ERROR)
            return
        
        data = response.json()
        
        if not data:
            xbmcgui.Dialog().notification('Trakt', 'No results found', xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(int(sys.argv[1]))
            return
        
        for item in data:
            # Handle different response formats
            if media_type == 'show':
                content = item.get('show', item)
            else:
                content = item.get('movie', item)
            
            title = content.get('title', 'Unknown')
            year = content.get('year', '')
            ids = content.get('ids', {})
            tmdb_id = ids.get('tmdb')
            imdb_id = ids.get('imdb', '')
            
            # Get TMDB metadata
            meta = tmdb.get_details(tmdb_id, 'movie' if media_type == 'movie' else 'tv')
            
            # Create list item
            label = f'{title}' if not year else f'{title} ({year})'
            li = xbmcgui.ListItem(label=label)
            
            # Set artwork
            li.setArt({
                'poster': meta.get('poster', ''),
                'fanart': meta.get('backdrop', ''),
                'thumb': meta.get('poster', '')
            })
            
            # Set info
            info = {
                'title': title,
                'year': year,
                'plot': meta.get('overview', content.get('overview', '')),
                'rating': meta.get('rating', content.get('rating', 0)),
                'genre': ', '.join(meta.get('genres', []))
            }
            
            if media_type == 'movie':
                info['mediatype'] = 'movie'
                info['duration'] = meta.get('runtime', 0) * 60  # Convert to seconds
                li.setInfo('video', info)
                li.setProperty('IsPlayable', 'true')
                
                # Play URL
                play_url = f"{sys.argv[0]}?action=play&title={quote_plus(title)}&year={year}&imdb_id={imdb_id}"
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), play_url, li, False)
            else:
                # TV Show - go to seasons
                info['mediatype'] = 'tvshow'
                li.setInfo('video', info)
                
                show_url = f"{sys.argv[0]}?action=show_seasons&tmdb_id={tmdb_id}&title={quote_plus(title)}"
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), show_url, li, True)
        
        xbmcplugin.setContent(int(sys.argv[1]), 'movies' if media_type == 'movie' else 'tvshows')
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        
    except requests.exceptions.RequestException as e:
        xbmc.log(f'Trakt API network error: {str(e)}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', 'Network error - check connection', xbmcgui.NOTIFICATION_ERROR)
    except Exception as e:
        xbmc.log(f'Trakt API error: {str(e)}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', f'Failed to load: {str(e)}', xbmcgui.NOTIFICATION_ERROR)

def show_seasons(tmdb_id, show_title):
    """Display seasons for a TV show"""
    seasons = tmdb.get_tv_seasons(tmdb_id)
    
    for season in seasons:
        season_num = season.get('season_number', 0)
        if season_num == 0:  # Skip specials
            continue
            
        name = season.get('name', f'Season {season_num}')
        poster = f"https://image.tmdb.org/t/p/w500{season.get('poster_path')}" if season.get('poster_path') else ''
        
        li = xbmcgui.ListItem(label=name)
        li.setArt({'poster': poster, 'thumb': poster})
        li.setInfo('video', {'title': name, 'season': season_num})
        
        url = f"{sys.argv[0]}?action=show_episodes&tmdb_id={tmdb_id}&season={season_num}&title={quote_plus(show_title)}"
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, True)
    
    xbmcplugin.setContent(int(sys.argv[1]), 'seasons')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def show_episodes(tmdb_id, season_number, show_title):
    """Display episodes for a season"""
    episodes = tmdb.get_season_episodes(tmdb_id, season_number)
    
    for ep in episodes:
        ep_num = ep.get('episode_number', 0)
        name = ep.get('name', f'Episode {ep_num}')
        still = f"https://image.tmdb.org/t/p/w500{ep.get('still_path')}" if ep.get('still_path') else ''
        
        label = f"{ep_num}. {name}"
        li = xbmcgui.ListItem(label=label)
        li.setArt({'thumb': still, 'fanart': still})
        li.setInfo('video', {
            'title': name,
            'episode': ep_num,
            'season': int(season_number),
            'plot': ep.get('overview', ''),
            'mediatype': 'episode'
        })
        li.setProperty('IsPlayable', 'true')
        
        url = f"{sys.argv[0]}?action=play_episode&title={quote_plus(show_title)}&season={season_number}&episode={ep_num}"
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, li, False)
    
    xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def search(query, media_type='movie'):
    """Search Trakt for movies or shows"""
    headers = get_headers()
    endpoint = 'movie' if media_type == 'movie' else 'show'
    
    try:
        url = f'https://api.trakt.tv/search/{endpoint}?query={quote_plus(query)}&extended=full&limit=30'
        data = requests.get(url, headers=headers, timeout=15).json()
        
        for item in data:
            content = item.get(endpoint, {})
            title = content.get('title', 'Unknown')
            year = content.get('year', '')
            ids = content.get('ids', {})
            tmdb_id = ids.get('tmdb')
            imdb_id = ids.get('imdb', '')
            
            meta = tmdb.get_details(tmdb_id, 'movie' if media_type == 'movie' else 'tv')
            
            label = f'{title} ({year})' if year else title
            li = xbmcgui.ListItem(label=label)
            li.setArt({
                'poster': meta.get('poster', ''),
                'fanart': meta.get('backdrop', '')
            })
            li.setInfo('video', {
                'title': title,
                'year': year,
                'plot': meta.get('overview', '')
            })
            
            if media_type == 'movie':
                li.setProperty('IsPlayable', 'true')
                play_url = f"{sys.argv[0]}?action=play&title={quote_plus(title)}&year={year}&imdb_id={imdb_id}"
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), play_url, li, False)
            else:
                show_url = f"{sys.argv[0]}?action=show_seasons&tmdb_id={tmdb_id}&title={quote_plus(title)}"
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), show_url, li, True)
        
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        
    except Exception as e:
        xbmc.log(f'Search error: {str(e)}', xbmc.LOGERROR)
