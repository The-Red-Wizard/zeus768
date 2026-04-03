import requests
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc
import sys

ADDON = xbmcaddon.Addon()

# Default TMDB API key - users are encouraged to use their own
DEFAULT_TMDB_KEY = "8265bd1679663a7ea12ac168da84d2e8"

def get_api_key():
    """Get TMDB API key - user's key or default"""
    user_key = ADDON.getSetting('tmdb_api_key')
    if user_key and len(user_key) > 10:
        return user_key
    return DEFAULT_TMDB_KEY

def prompt_for_api_key():
    """Show prompt suggesting user to add their own API key"""
    if ADDON.getSetting('tmdb_key_prompted') != 'true':
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
                    ADDON.setSetting('tmdb_api_key', key)
                    xbmcgui.Dialog().notification("Success", "TMDB API key saved", xbmcgui.NOTIFICATION_INFO)
        
        ADDON.setSetting('tmdb_key_prompted', 'true')

def get_details(tmdb_id, media_type='movie'):
    """Get movie or TV show details from TMDB"""
    if not tmdb_id:
        return {'overview': '', 'poster': '', 'backdrop': '', 'runtime': 0}
    
    key = get_api_key()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    url = f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}?api_key={key}"
    
    try:
        data = requests.get(url, timeout=10).json()
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
    url = f"https://api.themoviedb.org/3/search/{endpoint}?api_key={key}&query={query}"
    
    try:
        data = requests.get(url, timeout=10).json()
        return data.get('results', [])
    except:
        return []

def get_genres(media_type):
    """List genres and display in Kodi"""
    key = get_api_key()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    url = f"https://api.themoviedb.org/3/genre/{endpoint}/list?api_key={key}"
    
    try:
        genres = requests.get(url, timeout=10).json().get('genres', [])
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
        data = requests.get(url, timeout=10).json()
        return data.get('episodes', [])
    except:
        return []

def get_tv_seasons(tmdb_id):
    """Get all seasons for a TV show"""
    key = get_api_key()
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={key}"
    
    try:
        data = requests.get(url, timeout=10).json()
        return data.get('seasons', [])
    except:
        return []
