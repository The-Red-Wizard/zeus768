import sys
from urllib.parse import parse_qsl, urlencode, quote_plus
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
from resources.lib import tmdb, trakt_auth, trakt_api, filehost, debrid

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])

def build_url(query):
    return sys.argv[0] + '?' + urlencode(query)

def main_menu():
    # Prompt for TMDB API key on first run
    tmdb.prompt_for_api_key()
    
    items = [
        ("Movies", "movie_menu", "DefaultMovies.png"),
        ("TV Shows", "tv_menu", "DefaultTVShows.png"),
        ("Search", "search_menu", "DefaultAddonsSearch.png"),
        ("My Trakt", "my_trakt", "DefaultAddonProgram.png"),
        ("Settings", "open_settings", "DefaultAddonService.png")
    ]
    
    for label, action, icon in items:
        url = build_url({'action': action})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': icon})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def movie_menu():
    items = [
        ("Trending", "trakt_list", "movies/trending"),
        ("Popular", "trakt_list", "movies/popular"),
        ("Most Watched (Week)", "trakt_list", "movies/watched/weekly"),
        ("Most Watched (All Time)", "trakt_list", "movies/watched/all"),
        ("Box Office", "trakt_list", "movies/boxoffice"),
        ("Genres", "list_genres", "movie")
    ]
    
    for label, action, path in items:
        url = build_url({'action': action, 'path': path, 'media_type': 'movie'})
        xbmcplugin.addDirectoryItem(HANDLE, url, xbmcgui.ListItem(label=label), isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def tv_menu():
    items = [
        ("Trending Shows", "trakt_list", "shows/trending"),
        ("Popular Shows", "trakt_list", "shows/popular"),
        ("Most Watched (Week)", "trakt_list", "shows/watched/weekly"),
        ("Most Watched (All Time)", "trakt_list", "shows/watched/all"),
        ("Genres", "list_genres", "tv")
    ]
    
    for label, action, path in items:
        url = build_url({'action': action, 'path': path, 'media_type': 'show'})
        xbmcplugin.addDirectoryItem(HANDLE, url, xbmcgui.ListItem(label=label), isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def search_menu():
    items = [
        ("Search Movies", "search_dialog", "movie"),
        ("Search TV Shows", "search_dialog", "show")
    ]
    
    for label, action, media_type in items:
        url = build_url({'action': action, 'media_type': media_type})
        xbmcplugin.addDirectoryItem(HANDLE, url, xbmcgui.ListItem(label=label), isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def my_trakt():
    """User's Trakt lists and watchlist"""
    if ADDON.getSetting('trakt_auth_done') != 'true':
        xbmcgui.Dialog().notification("Trakt", "Please authorize Trakt first", xbmcgui.NOTIFICATION_WARNING)
        return
    
    items = [
        ("Movie Watchlist", "trakt_list", "sync/watchlist/movies"),
        ("Show Watchlist", "trakt_list", "sync/watchlist/shows"),
        ("Movie Collection", "trakt_list", "sync/collection/movies"),
        ("Show Collection", "trakt_list", "sync/collection/shows"),
        ("Watched Movies", "trakt_list", "sync/watched/movies"),
        ("Watched Shows", "trakt_list", "sync/watched/shows")
    ]
    
    for label, action, path in items:
        media = 'movie' if 'movie' in path else 'show'
        url = build_url({'action': action, 'path': path, 'media_type': media})
        xbmcplugin.addDirectoryItem(HANDLE, url, xbmcgui.ListItem(label=label), isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def search_dialog(media_type):
    """Show search keyboard and search"""
    keyboard = xbmc.Keyboard('', f'Search {"Movies" if media_type == "movie" else "TV Shows"}')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            trakt_api.search(query, media_type)

if __name__ == '__main__':
    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get('action')
    
    if not action:
        main_menu()
    
    # Navigation
    elif action == 'movie_menu':
        movie_menu()
    elif action == 'tv_menu':
        tv_menu()
    elif action == 'search_menu':
        search_menu()
    elif action == 'my_trakt':
        my_trakt()
    elif action == 'open_settings':
        ADDON.openSettings()
    
    # Content
    elif action == 'list_genres':
        tmdb.get_genres(params.get('path'))
    elif action == 'trakt_list':
        trakt_api.get_list(params.get('path'), params.get('media_type', 'movie'))
    elif action == 'search_dialog':
        search_dialog(params.get('media_type', 'movie'))
    elif action == 'show_seasons':
        trakt_api.show_seasons(params.get('tmdb_id'), params.get('title'))
    elif action == 'show_episodes':
        trakt_api.show_episodes(
            params.get('tmdb_id'),
            params.get('season'),
            params.get('title')
        )
    
    # Playback
    elif action == 'play':
        filehost.play_video(
            params.get('title'),
            params.get('year'),
            params.get('imdb_id')
        )
    elif action == 'play_episode':
        # For TV episodes, build proper search query
        title = params.get('title')
        season = params.get('season')
        episode = params.get('episode')
        search_title = f"{title} S{season.zfill(2)}E{episode.zfill(2)}"
        filehost.play_video(search_title, '', params.get('imdb_id'))
    
    # Auth - Trakt
    elif action == 'auth_trakt':
        trakt_auth.authorize()
    elif action == 'revoke_trakt':
        trakt_auth.revoke()
    
    # Auth - Real-Debrid
    elif action == 'auth_rd':
        debrid.RealDebrid().authorize()
    elif action == 'revoke_rd':
        debrid.RealDebrid().revoke()
    
    # Auth - AllDebrid  
    elif action == 'auth_ad':
        debrid.AllDebrid().authorize()
    elif action == 'revoke_ad':
        debrid.AllDebrid().revoke()
    
    # Auth - Premiumize
    elif action == 'auth_pm':
        debrid.Premiumize().authorize()
    elif action == 'revoke_pm':
        debrid.Premiumize().revoke()
