# -*- coding: utf-8 -*-
"""
Orion Media Explorer v3.0 - Kodi 21 Omega Addon
Multi-scraper support with debrid, history, favorites, and auto-play
"""

import sys
import urllib.parse
import urllib.request
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

# Addon info
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_FANART = ADDON.getAddonInfo('fanart')

BASE_URL = sys.argv[0]
HANDLE = int(sys.argv[1])

# Category icons - using addon path
import os
ICONS_PATH = os.path.join(ADDON_PATH, 'resources', 'icons')

def get_icon(name):
    """Get category icon path"""
    icon_path = os.path.join(ICONS_PATH, f'{name}.png')
    if os.path.exists(icon_path):
        return icon_path
    return ADDON_ICON

def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)

def build_url(query):
    return f"{BASE_URL}?{urllib.parse.urlencode(query)}"

def add_directory_item(name, query, is_folder=True, icon=None, fanart=None, plot="", context_menu=None):
    """Add a directory item with artwork"""
    li = xbmcgui.ListItem(label=name)
    li.setArt({
        'icon': icon or ADDON_ICON,
        'thumb': icon or ADDON_ICON,
        'poster': icon or ADDON_ICON,
        'fanart': fanart or ADDON_FANART
    })
    li.setInfo('video', {'title': name, 'plot': plot})
    
    if context_menu:
        li.addContextMenuItems(context_menu)
    
    xbmcplugin.addDirectoryItem(HANDLE, build_url(query), li, isFolder=is_folder)

def main_menu():
    """Display main menu"""
    # Check for expiry alerts on main menu load
    from resources.lib import debrid
    debrid.check_expiry_alerts()
    
    items = [
        ("[B]Movies[/B]", {'action': 'movies_menu'}, True, get_icon('movies'), "Browse movies by genre"),
        ("[B]TV Shows[/B]", {'action': 'tvshows_menu'}, True, get_icon('tvshows'), "Browse TV shows by genre"),
        ("[B]Kids Zone[/B]", {'action': 'kids_menu'}, True, get_icon('kids'), "Family-friendly content for kids 12 and under"),
        ("[B]In Cinema[/B]", {'action': 'in_cinema'}, True, get_icon('cinema'), "Currently showing in theaters"),
        ("[B]Latest Episodes[/B]", {'action': 'latest_episodes'}, True, get_icon('episodes'), "Latest TV show episodes"),
        ("[B]Search[/B]", {'action': 'search_menu'}, True, get_icon('search'), "Search movies, TV shows, actors"),
        ("[COLOR lime]Continue Watching[/COLOR]", {'action': 'continue_watching'}, True, get_icon('continue'), "Resume where you left off"),
        ("[COLOR lime]Watch History[/COLOR]", {'action': 'watch_history'}, True, get_icon('history'), "Your watch history"),
        ("[COLOR gold]Favorites[/COLOR]", {'action': 'favorites_menu'}, True, get_icon('favorites'), "Your favorite movies and shows"),
        ("[COLOR yellow]Trakt[/COLOR]", {'action': 'trakt_menu'}, True, get_icon('trakt'), "Trakt lists and watchlist"),
        ("[COLOR magenta]Account Status[/COLOR]", {'action': 'account_status'}, True, get_icon('settings'), "View debrid account status and expiry"),
        ("[COLOR cyan]Settings[/COLOR]", {'action': 'open_settings'}, False, get_icon('settings'), "Configure addon settings"),
        ("[COLOR orange]Buy Me a Beer[/COLOR]", {'action': 'buy_beer'}, False, get_icon('settings'), "Support zeus768 on Ko-fi"),
    ]
    
    for name, query, is_folder, icon, plot in items:
        add_directory_item(name, query, is_folder, icon=icon, plot=plot)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def movies_menu():
    """Movies sub-menu with genres"""
    from resources.lib import tmdb
    
    add_directory_item("[B]Popular Movies[/B]", {'action': 'list_content', 'type': 'movie', 'category': 'popular', 'page': 1}, icon=get_icon('popular'))
    add_directory_item("[B]Top Rated Movies[/B]", {'action': 'list_content', 'type': 'movie', 'category': 'top_rated', 'page': 1}, icon=get_icon('toprated'))
    add_directory_item("[B]Now Playing[/B]", {'action': 'list_content', 'type': 'movie', 'category': 'now_playing', 'page': 1}, icon=get_icon('nowplaying'))
    add_directory_item("[B]Upcoming[/B]", {'action': 'list_content', 'type': 'movie', 'category': 'upcoming', 'page': 1}, icon=get_icon('upcoming'))
    
    genres = tmdb.get_genres('movie')
    for genre in genres:
        add_directory_item(
            f"[COLOR lime]{genre['name']}[/COLOR]",
            {'action': 'list_content', 'type': 'movie', 'genre': genre['id'], 'page': 1},
            icon=get_icon('genre')
        )
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def tvshows_menu():
    """TV Shows sub-menu with genres"""
    from resources.lib import tmdb
    
    add_directory_item("[B]Popular TV Shows[/B]", {'action': 'list_content', 'type': 'tv', 'category': 'popular', 'page': 1}, icon=get_icon('popular'))
    add_directory_item("[B]Top Rated TV Shows[/B]", {'action': 'list_content', 'type': 'tv', 'category': 'top_rated', 'page': 1}, icon=get_icon('toprated'))
    add_directory_item("[B]On The Air[/B]", {'action': 'list_content', 'type': 'tv', 'category': 'on_the_air', 'page': 1}, icon=get_icon('onair'))
    add_directory_item("[B]Airing Today[/B]", {'action': 'list_content', 'type': 'tv', 'category': 'airing_today', 'page': 1}, icon=get_icon('airingtoday'))
    
    genres = tmdb.get_genres('tv')
    for genre in genres:
        add_directory_item(
            f"[COLOR lime]{genre['name']}[/COLOR]",
            {'action': 'list_content', 'type': 'tv', 'genre': genre['id'], 'page': 1},
            icon=get_icon('genre')
        )
    
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def list_content(params):
    """List movies or TV shows"""
    from resources.lib import tmdb, database
    
    media_type = params.get('type', 'movie')
    page = int(params.get('page', 1))
    genre = params.get('genre')
    category = params.get('category')
    query = params.get('query')
    person_id = params.get('person_id')
    
    if query:
        data = tmdb.search_content(media_type, query, page)
    elif person_id:
        data = tmdb.get_person_credits(person_id, media_type)
    elif category:
        data = tmdb.get_category(media_type, category, page)
    elif genre:
        data = tmdb.get_by_genre(media_type, genre, page)
    else:
        data = tmdb.get_category(media_type, 'popular', page)
    
    results = data.get('results', data.get('cast', []))
    total_pages = data.get('total_pages', 1)
    
    for item in results:
        title = item.get('title') or item.get('name', 'Unknown')
        item_id = item.get('id')
        poster = tmdb.get_poster_url(item.get('poster_path'))
        backdrop = tmdb.get_backdrop_url(item.get('backdrop_path'))
        year = (item.get('release_date') or item.get('first_air_date', ''))[:4]
        rating = item.get('vote_average', 0)
        plot = item.get('overview', '')
        
        display_title = f"{title} ({year})" if year else title
        if rating:
            display_title = f"{display_title} [COLOR yellow]★{rating:.1f}[/COLOR]"
        
        # Check if favorite
        is_fav = database.is_favorite(media_type, item_id)
        if is_fav:
            display_title = f"[COLOR gold]★[/COLOR] {display_title}"
        
        li = xbmcgui.ListItem(label=display_title)
        li.setArt({
            'icon': poster or ADDON_ICON,
            'thumb': poster or ADDON_ICON,
            'poster': poster or ADDON_ICON,
            'fanart': backdrop or ADDON_FANART
        })
        
        info = {
            'title': title,
            'plot': plot,
            'year': int(year) if year else None,
            'rating': rating,
            'mediatype': 'movie' if media_type == 'movie' else 'tvshow'
        }
        li.setInfo('video', info)
        
        # Context menu
        context_items = []
        if is_fav:
            context_items.append(('Remove from Favorites', f'RunPlugin({build_url({"action": "remove_favorite", "type": media_type, "id": item_id})})'))
        else:
            context_items.append(('Add to Favorites', f'RunPlugin({build_url({"action": "add_favorite", "type": media_type, "id": item_id, "title": title, "year": year, "poster": poster or "", "backdrop": backdrop or ""})})'))
        li.addContextMenuItems(context_items)
        
        action = 'movie_sources' if media_type == 'movie' else 'tv_seasons'
        url = build_url({'action': action, 'id': item_id, 'title': title, 'year': year})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    if page < total_pages:
        next_params = dict(params)
        next_params['page'] = page + 1
        add_directory_item(f"[B]Next Page ({page+1}/{total_pages})[/B]", next_params)
    
    content_type = 'movies' if media_type == 'movie' else 'tvshows'
    xbmcplugin.setContent(HANDLE, content_type)
    xbmcplugin.endOfDirectory(HANDLE)

def tv_seasons(params):
    """List TV show seasons"""
    from resources.lib import tmdb
    
    show_id = params.get('id')
    show_title = params.get('title', '')
    
    details = tmdb.get_tv_details(show_id)
    seasons = details.get('seasons', [])
    
    for season in seasons:
        season_num = season.get('season_number', 0)
        name = season.get('name', f'Season {season_num}')
        episode_count = season.get('episode_count', 0)
        poster = tmdb.get_poster_url(season.get('poster_path'))
        
        display_name = f"{name} ({episode_count} episodes)"
        
        li = xbmcgui.ListItem(label=display_name)
        li.setArt({
            'icon': poster or ADDON_ICON,
            'thumb': poster or ADDON_ICON,
            'poster': poster or ADDON_ICON,
            'fanart': ADDON_FANART
        })
        
        url = build_url({
            'action': 'tv_episodes',
            'id': show_id,
            'title': show_title,
            'season': season_num
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'seasons')
    xbmcplugin.endOfDirectory(HANDLE)

def tv_episodes(params):
    """List TV show episodes"""
    from resources.lib import tmdb
    
    show_id = params.get('id')
    show_title = params.get('title', '')
    season_num = int(params.get('season', 1))
    
    episodes = tmdb.get_season_episodes(show_id, season_num)
    
    for ep in episodes.get('episodes', []):
        ep_num = ep.get('episode_number', 0)
        ep_name = ep.get('name', f'Episode {ep_num}')
        still = tmdb.get_backdrop_url(ep.get('still_path'))
        plot = ep.get('overview', '')
        air_date = ep.get('air_date', '')
        rating = ep.get('vote_average', 0)
        
        display_name = f"S{season_num:02d}E{ep_num:02d} - {ep_name}"
        if rating:
            display_name = f"{display_name} [COLOR yellow]★{rating:.1f}[/COLOR]"
        
        li = xbmcgui.ListItem(label=display_name)
        li.setArt({
            'icon': still or ADDON_ICON,
            'thumb': still or ADDON_ICON,
            'fanart': still or ADDON_FANART
        })
        li.setInfo('video', {
            'title': ep_name,
            'plot': plot,
            'episode': ep_num,
            'season': season_num,
            'aired': air_date,
            'mediatype': 'episode'
        })
        
        url = build_url({
            'action': 'episode_sources',
            'id': show_id,
            'title': show_title,
            'season': season_num,
            'episode': ep_num
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)

def search_menu():
    """Search sub-menu"""
    items = [
        ("[B]Search Movies[/B]", {'action': 'search', 'type': 'movie'}, get_icon('search')),
        ("[B]Search TV Shows[/B]", {'action': 'search', 'type': 'tv'}, get_icon('search')),
        ("[B]Search by Actor[/B]", {'action': 'search_actor'}, get_icon('actor')),
    ]
    
    for name, query, icon in items:
        add_directory_item(name, query, icon=icon)
    
    xbmcplugin.endOfDirectory(HANDLE)

def do_search(params):
    """Perform search"""
    media_type = params.get('type', 'movie')
    
    keyboard = xbmc.Keyboard('', f'Search {media_type.title()}s')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText().strip()
        if query:
            list_content({'type': media_type, 'query': query, 'page': 1})
            return
    
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def search_actor(params):
    """Search for actor"""
    from resources.lib import tmdb
    
    keyboard = xbmc.Keyboard('', 'Search Actor')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        query = keyboard.getText().strip()
        if query:
            results = tmdb.search_people(query)
            
            for person in results.get('results', []):
                name = person.get('name', 'Unknown')
                person_id = person.get('id')
                profile = tmdb.get_poster_url(person.get('profile_path'))
                known_for = person.get('known_for_department', '')
                
                li = xbmcgui.ListItem(label=f"{name} ({known_for})")
                li.setArt({
                    'icon': profile or ADDON_ICON,
                    'thumb': profile or ADDON_ICON,
                    'fanart': ADDON_FANART
                })
                
                url = build_url({'action': 'actor_works', 'id': person_id, 'name': name})
                xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
            
            xbmcplugin.endOfDirectory(HANDLE)
            return
    
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def actor_works(params):
    """Show actor's filmography"""
    person_id = params.get('id')
    actor_name = params.get('name', '')
    
    add_directory_item(f"[B]{actor_name}'s Movies[/B]", {'action': 'list_content', 'type': 'movie', 'person_id': person_id})
    add_directory_item(f"[B]{actor_name}'s TV Shows[/B]", {'action': 'list_content', 'type': 'tv', 'person_id': person_id})
    
    xbmcplugin.endOfDirectory(HANDLE)

def in_cinema(params):
    """Movies currently in cinema"""
    list_content({'type': 'movie', 'category': 'now_playing', 'page': params.get('page', 1)})

def latest_episodes(params):
    """Latest TV episodes"""
    list_content({'type': 'tv', 'category': 'on_the_air', 'page': params.get('page', 1)})

# ============== HISTORY & FAVORITES ==============

def continue_watching(params):
    """Show continue watching list"""
    from resources.lib import database, tmdb
    
    items = database.get_continue_watching()
    
    if not items:
        xbmcgui.Dialog().notification('Orion', 'No items in continue watching', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    
    for item in items:
        title = item.get('title', 'Unknown')
        item_type = item.get('type', 'movie')
        item_id = item.get('id')
        poster = item.get('poster') or ADDON_ICON
        progress = item.get('progress', 0)
        
        if item_type == 'tv':
            season = item.get('season', 1)
            episode = item.get('episode', 1)
            display = f"{title} S{season:02d}E{episode:02d} [{progress}%]"
            action_params = {
                'action': 'episode_sources',
                'id': item_id,
                'title': title,
                'season': season,
                'episode': episode
            }
        else:
            year = item.get('year', '')
            display = f"{title} ({year}) [{progress}%]"
            action_params = {
                'action': 'movie_sources',
                'id': item_id,
                'title': title,
                'year': year
            }
        
        li = xbmcgui.ListItem(label=display)
        li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': ADDON_FANART})
        li.setProperty('ResumeTime', str(item.get('position', 0)))
        li.setProperty('TotalTime', str(item.get('duration', 0)))
        
        # Context menu
        context_items = [
            ('Remove from History', f'RunPlugin({build_url({"action": "remove_history", "key": item.get("key", "")})})')
        ]
        li.addContextMenuItems(context_items)
        
        url = build_url(action_params)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def watch_history(params):
    """Show full watch history"""
    from resources.lib import database
    
    items = database.get_history_list()
    
    if not items:
        xbmcgui.Dialog().notification('Orion', 'No watch history', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    
    for item in items:
        title = item.get('title', 'Unknown')
        item_type = item.get('type', 'movie')
        item_id = item.get('id')
        poster = item.get('poster') or ADDON_ICON
        progress = item.get('progress', 0)
        
        if item_type == 'tv':
            season = item.get('season', 1)
            episode = item.get('episode', 1)
            display = f"{title} S{season:02d}E{episode:02d}"
            if progress > 0:
                display += f" [{progress}%]"
            action_params = {
                'action': 'episode_sources',
                'id': item_id,
                'title': title,
                'season': season,
                'episode': episode
            }
        else:
            year = item.get('year', '')
            display = f"{title} ({year})"
            if progress > 0:
                display += f" [{progress}%]"
            action_params = {
                'action': 'movie_sources',
                'id': item_id,
                'title': title,
                'year': year
            }
        
        li = xbmcgui.ListItem(label=display)
        li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': ADDON_FANART})
        
        context_items = [
            ('Remove from History', f'RunPlugin({build_url({"action": "remove_history", "key": item.get("key", "")})})')
        ]
        li.addContextMenuItems(context_items)
        
        url = build_url(action_params)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def favorites_menu(params):
    """Show favorites menu"""
    add_directory_item("[B]Favorite Movies[/B]", {'action': 'favorites_list', 'type': 'movie'}, icon=get_icon('favorites'))
    add_directory_item("[B]Favorite TV Shows[/B]", {'action': 'favorites_list', 'type': 'tv'}, icon=get_icon('favorites'))
    
    xbmcplugin.endOfDirectory(HANDLE)

def favorites_list(params):
    """Show favorites list"""
    from resources.lib import database, tmdb
    
    item_type = params.get('type', 'movie')
    items = database.get_favorites_list(item_type)
    
    if not items:
        xbmcgui.Dialog().notification('Orion', f'No favorite {item_type}s', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    
    for item in items:
        title = item.get('title', 'Unknown')
        item_id = item.get('id')
        year = item.get('year', '')
        poster = item.get('poster') or ADDON_ICON
        backdrop = item.get('backdrop') or ADDON_FANART
        
        display = f"{title} ({year})" if year else title
        
        li = xbmcgui.ListItem(label=display)
        li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': backdrop})
        
        context_items = [
            ('Remove from Favorites', f'RunPlugin({build_url({"action": "remove_favorite", "type": item_type, "id": item_id})})')
        ]
        li.addContextMenuItems(context_items)
        
        if item_type == 'movie':
            action = 'movie_sources'
            url = build_url({'action': action, 'id': item_id, 'title': title, 'year': year})
        else:
            action = 'tv_seasons'
            url = build_url({'action': action, 'id': item_id, 'title': title})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'movies' if item_type == 'movie' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def add_favorite(params):
    """Add item to favorites"""
    from resources.lib import database
    
    item = {
        'id': params.get('id'),
        'type': params.get('type'),
        'title': params.get('title'),
        'year': params.get('year'),
        'poster': params.get('poster'),
        'backdrop': params.get('backdrop')
    }
    
    database.add_to_favorites(item)
    xbmcgui.Dialog().notification('Orion', f'Added to favorites', ADDON_ICON)
    xbmc.executebuiltin('Container.Refresh')

def remove_favorite(params):
    """Remove item from favorites"""
    from resources.lib import database
    
    key = f"{params.get('type')}_{params.get('id')}"
    database.remove_from_favorites(key)
    xbmcgui.Dialog().notification('Orion', 'Removed from favorites', ADDON_ICON)
    xbmc.executebuiltin('Container.Refresh')

def remove_history(params):
    """Remove item from history"""
    from resources.lib import database
    
    key = params.get('key', '')
    if key:
        database.remove_from_history(key)
        xbmcgui.Dialog().notification('Orion', 'Removed from history', ADDON_ICON)
        xbmc.executebuiltin('Container.Refresh')

# ============== SOURCES & PLAYBACK ==============

def movie_sources(params):
    """Get movie sources from scraper"""
    from resources.lib import scraper
    
    title = params.get('title', '')
    year = params.get('year', '')
    tmdb_id = params.get('id', '')
    quality_filter = params.get('quality_filter', 'all')
    source_filter = params.get('source_filter', 'all')
    
    progress = xbmcgui.DialogProgress()
    progress.create('Orion', f'Searching sources for {title}...')
    
    try:
        sources = scraper.search_movie(title, year, tmdb_id, progress)
        progress.close()
        
        if not sources:
            xbmcgui.Dialog().notification('Orion', 'No sources found', ADDON_ICON)
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return
        
        sources = scraper.filter_sources_by_type(sources, source_filter)
        sources = scraper.sort_sources(sources, quality_filter)
        
        show_sources(sources, title, tmdb_id, 'movie', params)
    except Exception as e:
        progress.close()
        log(f"Error getting sources: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Orion', f'Error: {str(e)}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def episode_sources(params):
    """Get episode sources from scraper"""
    from resources.lib import scraper
    
    title = params.get('title', '')
    season = int(params.get('season', 1))
    episode = int(params.get('episode', 1))
    tmdb_id = params.get('id', '')
    quality_filter = params.get('quality_filter', 'all')
    source_filter = params.get('source_filter', 'all')
    
    progress = xbmcgui.DialogProgress()
    progress.create('Orion', f'Searching sources for {title} S{season}E{episode}...')
    
    try:
        sources = scraper.search_episode(title, season, episode, tmdb_id, progress)
        progress.close()
        
        if not sources:
            xbmcgui.Dialog().notification('Orion', 'No sources found', ADDON_ICON)
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return
        
        sources = scraper.filter_sources_by_type(sources, source_filter)
        sources = scraper.sort_sources(sources, quality_filter)
        
        show_sources(sources, f"{title} S{season:02d}E{episode:02d}", tmdb_id, 'tv', params)
    except Exception as e:
        progress.close()
        log(f"Error getting sources: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Orion', f'Error: {str(e)}', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def show_sources(sources, title, tmdb_id=None, media_type='movie', original_params=None):
    """Display available sources with color coding, filtering, and [CACHED] tags"""
    from resources.lib import scraper, debrid
    import re
    
    current_quality = (original_params or {}).get('quality_filter', 'all')
    current_source = (original_params or {}).get('source_filter', 'all')
    
    # --- Batch cache check ---
    hash_map = {}  # hash -> source index list
    for idx, source in enumerate(sources):
        magnet = source.get('magnet', '')
        hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet, re.IGNORECASE)
        if hash_match:
            h = hash_match.group(1).lower()
            hash_map.setdefault(h, []).append(idx)
    
    cache_status = {}
    if hash_map:
        try:
            cache_status = debrid.check_cache_batch(list(hash_map.keys()))
        except Exception as e:
            log(f"Cache check error: {e}", xbmc.LOGWARNING)
    
    # Tag sources with cached status
    for h, indices in hash_map.items():
        is_cached = cache_status.get(h, False)
        for idx in indices:
            sources[idx]['cached'] = is_cached
    
    # Sort: cached first, then by quality and seeds
    quality_order = {'4K': 0, '2160p': 0, '1080p': 1, '720p': 2, 'SD': 3, '480p': 3, 'Unknown': 4}
    sources.sort(key=lambda x: (
        0 if x.get('cached') else 1,
        quality_order.get(x.get('quality', 'Unknown'), 4),
        -x.get('seeds', 0)
    ))
    
    # Quality filter menu
    quality_label = f"[COLOR magenta]Filter Quality: {current_quality.upper()}[/COLOR]"
    li = xbmcgui.ListItem(label=quality_label)
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({
        'action': 'filter_quality',
        'title': (original_params or {}).get('title', title),
        'year': (original_params or {}).get('year', ''),
        'id': tmdb_id or '',
        'media_type': media_type,
        'season': (original_params or {}).get('season', ''),
        'episode': (original_params or {}).get('episode', ''),
        'current_source_filter': current_source
    })
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Source filter menu
    source_label = f"[COLOR magenta]Filter Source: {current_source.upper()}[/COLOR]"
    li = xbmcgui.ListItem(label=source_label)
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    url = build_url({
        'action': 'filter_source',
        'title': (original_params or {}).get('title', title),
        'year': (original_params or {}).get('year', ''),
        'id': tmdb_id or '',
        'media_type': media_type,
        'season': (original_params or {}).get('season', ''),
        'episode': (original_params or {}).get('episode', ''),
        'current_quality_filter': current_quality
    })
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Count cached
    cached_count = sum(1 for s in sources if s.get('cached'))
    if cached_count:
        summary_label = f"[COLOR lime]{cached_count} cached[/COLOR] / {len(sources)} total sources"
    else:
        summary_label = f"{len(sources)} sources found"
    li = xbmcgui.ListItem(label=summary_label)
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
    
    for source in sources:
        quality = source.get('quality', 'Unknown')
        size = source.get('size', '')
        seeds = source.get('seeds', 0)
        name = source.get('name', 'Unknown')
        source_type = source.get('source_type', 'torrent')
        source_name = source.get('source', 'Unknown')
        is_cached = source.get('cached', False)
        
        # Source color coding
        if source_type == 'orionoid':
            source_tag = '[COLOR dodgerblue][Orionoid][/COLOR]'
        elif source_type == 'torrentio':
            source_tag = '[COLOR orange][Torrentio][/COLOR]'
        elif source_type == 'mediafusion':
            source_tag = '[COLOR purple][MediaFusion][/COLOR]'
        elif source_type == 'jackettio':
            source_tag = '[COLOR cyan][Jackettio][/COLOR]'
        elif source_type == 'meteor':
            source_tag = '[COLOR magenta][Meteor][/COLOR]'
        elif source_type == 'bitmagnet':
            source_tag = '[COLOR lime][Bitmagnet][/COLOR]'
        elif source_type == 'coco':
            source_tag = f'[COLOR yellow][{source_name}][/COLOR]'
        else:
            source_tag = f'[COLOR white][{source_name}][/COLOR]'
        
        # Quality color coding
        if quality in ['4K', '2160p']:
            quality_color = 'gold'
        elif quality == '1080p':
            quality_color = 'lime'
        elif quality == '720p':
            quality_color = 'cyan'
        else:
            quality_color = 'white'
        
        # Build display string
        cached_tag = '[COLOR lime][CACHED][/COLOR] ' if is_cached else ''
        display = f"{cached_tag}{source_tag} [COLOR {quality_color}][{quality}][/COLOR] {name[:60]}"
        if size:
            display += f" [{size}]"
        if seeds:
            display += f" [COLOR lime]S:{seeds}[/COLOR]"
        
        li = xbmcgui.ListItem(label=display)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({
            'action': 'play',
            'magnet': source.get('magnet', ''),
            'title': title,
            'quality': quality,
            'tmdb_id': tmdb_id,
            'media_type': media_type,
            'season': (original_params or {}).get('season', ''),
            'episode': (original_params or {}).get('episode', '')
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def filter_quality(params):
    """Show quality filter options"""
    title = params.get('title', '')
    year = params.get('year', '')
    tmdb_id = params.get('id', '')
    media_type = params.get('media_type', 'movie')
    season = params.get('season', '')
    episode = params.get('episode', '')
    current_source = params.get('current_source_filter', 'all')
    
    options = [
        ('All Qualities', 'all'),
        ('4K Only', '4k'),
        ('1080p Only', '1080p'),
        ('720p Only', '720p'),
        ('SD Only', 'sd'),
    ]
    
    for label, quality_value in options:
        li = xbmcgui.ListItem(label=f"[COLOR cyan]{label}[/COLOR]")
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        if media_type == 'tv' and season and episode:
            url = build_url({
                'action': 'episode_sources',
                'title': title,
                'id': tmdb_id,
                'season': season,
                'episode': episode,
                'quality_filter': quality_value,
                'source_filter': current_source
            })
        else:
            url = build_url({
                'action': 'movie_sources',
                'title': title,
                'year': year,
                'id': tmdb_id,
                'quality_filter': quality_value,
                'source_filter': current_source
            })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def filter_source(params):
    """Show source filter options"""
    title = params.get('title', '')
    year = params.get('year', '')
    tmdb_id = params.get('id', '')
    media_type = params.get('media_type', 'movie')
    season = params.get('season', '')
    episode = params.get('episode', '')
    current_quality = params.get('current_quality_filter', 'all')
    
    options = [
        ('All Sources', 'all'),
        ('[COLOR dodgerblue]Orionoid Only[/COLOR]', 'orionoid'),
        ('[COLOR orange]Torrentio Only[/COLOR]', 'torrentio'),
        ('[COLOR purple]MediaFusion Only[/COLOR]', 'mediafusion'),
        ('[COLOR cyan]Jackettio Only[/COLOR]', 'jackettio'),
        ('[COLOR magenta]Meteor Only[/COLOR]', 'meteor'),
        ('[COLOR lime]Bitmagnet Only[/COLOR]', 'bitmagnet'),
        ('[COLOR yellow]Coco Scrapers Only[/COLOR]', 'coco'),
    ]
    
    for label, source_value in options:
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        if media_type == 'tv' and season and episode:
            url = build_url({
                'action': 'episode_sources',
                'title': title,
                'id': tmdb_id,
                'season': season,
                'episode': episode,
                'quality_filter': current_quality,
                'source_filter': source_value
            })
        else:
            url = build_url({
                'action': 'movie_sources',
                'title': title,
                'year': year,
                'id': tmdb_id,
                'quality_filter': current_quality,
                'source_filter': source_value
            })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def play_source(params):
    """Resolve and play source via debrid"""
    from resources.lib import resolver, database, tmdb
    
    magnet = params.get('magnet', '')
    title = params.get('title', '')
    tmdb_id = params.get('tmdb_id', '')
    media_type = params.get('media_type', 'movie')
    season = params.get('season', '')
    episode = params.get('episode', '')
    
    if not magnet:
        xbmcgui.Dialog().notification('Orion', 'Invalid source', ADDON_ICON)
        return
    
    progress = xbmcgui.DialogProgress()
    progress.create('Orion', 'Resolving link via debrid...')
    
    try:
        stream_url = resolver.resolve_magnet(magnet, progress)
        progress.close()
        
        if stream_url:
            # Get poster/backdrop for history
            poster = ''
            backdrop = ''
            year = ''
            
            if tmdb_id:
                try:
                    if media_type == 'movie':
                        details = tmdb.get_movie_details(tmdb_id)
                    else:
                        details = tmdb.get_tv_details(tmdb_id)
                    poster = tmdb.get_poster_url(details.get('poster_path'))
                    backdrop = tmdb.get_backdrop_url(details.get('backdrop_path'))
                    year = (details.get('release_date') or details.get('first_air_date', ''))[:4]
                except:
                    pass
            
            # Add to history
            history_item = {
                'id': tmdb_id,
                'type': media_type,
                'title': title.split(' S')[0] if ' S' in title else title,
                'year': year,
                'poster': poster,
                'backdrop': backdrop,
                'progress': 0,
                'position': 0,
                'duration': 0
            }
            
            if media_type == 'tv' and season and episode:
                history_item['season'] = int(season)
                history_item['episode'] = int(episode)
            
            database.add_to_history(history_item)
            
            # Play the stream
            li = xbmcgui.ListItem(path=stream_url)
            li.setInfo('video', {'title': title})
            
            # Check for resume point
            resume_point = 0
            if tmdb_id:
                if media_type == 'tv' and season and episode:
                    resume_point = database.get_resume_point('tv', tmdb_id, season, episode)
                else:
                    resume_point = database.get_resume_point('movie', tmdb_id)
            
            if resume_point > 0:
                li.setProperty('StartOffset', str(resume_point))
            
            xbmcplugin.setResolvedUrl(HANDLE, True, li)
            
            # Setup auto-play next episode if enabled
            if media_type == 'tv' and ADDON.getSetting('auto_next_episode') == 'true':
                if season and episode:
                    database.set_next_episode(
                        tmdb_id,
                        title.split(' S')[0] if ' S' in title else title,
                        int(season),
                        int(episode) + 1,
                        poster,
                        backdrop
                    )
        else:
            xbmcgui.Dialog().notification('Orion', 'Failed to resolve link', ADDON_ICON)
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
    except Exception as e:
        progress.close()
        log(f"Error resolving: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Orion', f'Error: {str(e)}', ADDON_ICON)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

# ============== KIDS ZONE ==============

def kids_menu(params):
    """Kids Zone menu - family-friendly content"""
    items = [
        ("[B][COLOR cyan]Animation Movies[/COLOR][/B]", {'action': 'kids_list', 'category': 'animation', 'page': 1}, get_icon('kids')),
        ("[B][COLOR lime]Family Movies[/COLOR][/B]", {'action': 'kids_list', 'category': 'family', 'page': 1}, get_icon('kids')),
        ("[B][COLOR gold]Kids TV Shows[/COLOR][/B]", {'action': 'kids_list', 'category': 'kids_tv', 'page': 1}, get_icon('kids')),
        ("[B][COLOR magenta]Disney & Pixar Style[/COLOR][/B]", {'action': 'kids_list', 'category': 'disney', 'page': 1}, get_icon('kids')),
        ("[B][COLOR orange]G & PG Rated Movies[/COLOR][/B]", {'action': 'kids_list', 'category': 'pg_movies', 'page': 1}, get_icon('kids')),
    ]
    
    for name, query, icon in items:
        add_directory_item(name, query, icon=icon)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def kids_list(params):
    """List kids content with infinite scrolling"""
    from resources.lib import tmdb, database
    
    category = params.get('category', 'animation')
    page = int(params.get('page', 1))
    
    # Get content based on category
    if category == 'animation':
        data = tmdb.get_animation_movies(page)
        media_type = 'movie'
    elif category == 'family':
        data = tmdb.get_family_movies(page)
        media_type = 'movie'
    elif category == 'kids_tv':
        data = tmdb.get_kids_tvshows(page)
        media_type = 'tv'
    elif category == 'disney':
        data = tmdb.get_disney_style_movies(page)
        media_type = 'movie'
    elif category == 'pg_movies':
        data = tmdb.get_kids_movies(page)
        media_type = 'movie'
    else:
        data = tmdb.get_kids_animation(page)
        media_type = 'movie'
    
    results = data.get('results', [])
    total_pages = data.get('total_pages', 1)
    
    for item in results:
        title = item.get('title') or item.get('name', 'Unknown')
        item_id = item.get('id')
        poster = tmdb.get_poster_url(item.get('poster_path'))
        backdrop = tmdb.get_backdrop_url(item.get('backdrop_path'))
        year = (item.get('release_date') or item.get('first_air_date', ''))[:4]
        rating = item.get('vote_average', 0)
        plot = item.get('overview', '')
        
        display_title = f"{title} ({year})" if year else title
        if rating:
            display_title = f"{display_title} [COLOR yellow]★{rating:.1f}[/COLOR]"
        
        # Check if favorite
        is_fav = database.is_favorite(media_type, item_id)
        if is_fav:
            display_title = f"[COLOR gold]★[/COLOR] {display_title}"
        
        li = xbmcgui.ListItem(label=display_title)
        li.setArt({
            'icon': poster or ADDON_ICON,
            'thumb': poster or ADDON_ICON,
            'poster': poster or ADDON_ICON,
            'fanart': backdrop or ADDON_FANART
        })
        
        info = {
            'title': title,
            'plot': plot,
            'year': int(year) if year else None,
            'rating': rating,
            'mediatype': 'movie' if media_type == 'movie' else 'tvshow'
        }
        li.setInfo('video', info)
        
        # Context menu
        context_items = []
        if is_fav:
            context_items.append(('Remove from Favorites', f'RunPlugin({build_url({"action": "remove_favorite", "type": media_type, "id": item_id})})'))
        else:
            context_items.append(('Add to Favorites', f'RunPlugin({build_url({"action": "add_favorite", "type": media_type, "id": item_id, "title": title, "year": year, "poster": poster or "", "backdrop": backdrop or ""})})'))
        li.addContextMenuItems(context_items)
        
        action = 'movie_sources' if media_type == 'movie' else 'tv_seasons'
        url = build_url({'action': action, 'id': item_id, 'title': title, 'year': year})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Infinite scrolling - always show next page if available
    if page < total_pages:
        next_params = {
            'action': 'kids_list',
            'category': category,
            'page': page + 1
        }
        add_directory_item(
            f"[B][COLOR cyan]Load More... (Page {page+1}/{total_pages})[/COLOR][/B]", 
            next_params,
            icon=get_icon('kids')
        )
    
    content_type = 'movies' if media_type == 'movie' else 'tvshows'
    xbmcplugin.setContent(HANDLE, content_type)
    xbmcplugin.endOfDirectory(HANDLE)

# ============== TRAKT ==============

def trakt_menu():
    """Trakt integration menu"""
    if not ADDON.getSetting('trakt_token'):
        add_directory_item("[COLOR red]Trakt Not Authorized - Click to Authorize[/COLOR]", {'action': 'pair_trakt'}, False)
    else:
        items = [
            # Watchlists
            ("[B][COLOR gold]My Watchlist - Movies[/COLOR][/B]", {'action': 'trakt_watchlist', 'type': 'movies', 'page': 1}),
            ("[B][COLOR gold]My Watchlist - TV Shows[/COLOR][/B]", {'action': 'trakt_watchlist', 'type': 'shows', 'page': 1}),
            # My Lists
            ("[B][COLOR cyan]My Custom Lists[/COLOR][/B]", {'action': 'trakt_my_lists'}),
            ("[B][COLOR magenta]My Liked Lists[/COLOR][/B]", {'action': 'trakt_liked_lists', 'page': 1}),
            # Collection
            ("[B][COLOR lime]My Collection - Movies[/COLOR][/B]", {'action': 'trakt_collection', 'type': 'movies'}),
            ("[B][COLOR lime]My Collection - TV Shows[/COLOR][/B]", {'action': 'trakt_collection', 'type': 'shows'}),
            # History
            ("[B]Watched Movies[/B]", {'action': 'trakt_watched', 'type': 'movies'}),
            ("[B]Watched TV Shows[/B]", {'action': 'trakt_watched', 'type': 'shows'}),
            # Recommendations
            ("[B][COLOR orange]Recommended Movies[/COLOR][/B]", {'action': 'trakt_recommendations', 'type': 'movies', 'page': 1}),
            ("[B][COLOR orange]Recommended TV Shows[/COLOR][/B]", {'action': 'trakt_recommendations', 'type': 'shows', 'page': 1}),
            # Trending & Popular
            ("[B]Trending Movies[/B]", {'action': 'trakt_list', 'list': 'trending', 'type': 'movies'}),
            ("[B]Trending TV Shows[/B]", {'action': 'trakt_list', 'list': 'trending', 'type': 'shows'}),
            ("[B]Popular Movies[/B]", {'action': 'trakt_list', 'list': 'popular', 'type': 'movies'}),
            ("[B]Popular TV Shows[/B]", {'action': 'trakt_list', 'list': 'popular', 'type': 'shows'}),
            # Settings
            ("[COLOR yellow]Re-authorize Trakt[/COLOR]", {'action': 'pair_trakt'}, False),
        ]
        
        for item in items:
            if len(item) == 3:
                add_directory_item(item[0], item[1], item[2])
            else:
                add_directory_item(item[0], item[1])
    
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_watchlist(params):
    """Display Trakt watchlist with pagination"""
    from resources.lib import trakt, tmdb
    
    media_type = params.get('type', 'movies')
    page = int(params.get('page', 1))
    
    trakt_api = trakt.TraktAPI()
    
    if media_type == 'movies':
        items = trakt_api.get_watchlist_movies(page)
    else:
        items = trakt_api.get_watchlist_shows(page)
    
    _display_trakt_items(items, media_type, 'watchlist')
    
    # Pagination
    if len(items) >= 20:
        add_directory_item(
            f"[B][COLOR cyan]Next Page ({page+1})[/COLOR][/B]",
            {'action': 'trakt_watchlist', 'type': media_type, 'page': page + 1}
        )
    
    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movies' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_my_lists(params):
    """Display user's custom Trakt lists"""
    from resources.lib import trakt
    
    trakt_api = trakt.TraktAPI()
    lists = trakt_api.get_user_lists()
    
    if not lists:
        xbmcgui.Dialog().notification('Orion', 'No custom lists found', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    
    for lst in lists:
        name = lst.get('name', 'Unknown List')
        item_count = lst.get('item_count', 0)
        list_id = lst.get('ids', {}).get('slug', '')
        
        display = f"[COLOR cyan]{name}[/COLOR] ({item_count} items)"
        
        li = xbmcgui.ListItem(label=display)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        url = build_url({
            'action': 'trakt_list_items',
            'username': 'me',
            'list_id': list_id,
            'list_name': name
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_liked_lists(params):
    """Display user's liked Trakt lists"""
    from resources.lib import trakt
    
    page = int(params.get('page', 1))
    trakt_api = trakt.TraktAPI()
    liked = trakt_api.get_liked_lists(page)
    
    if not liked:
        xbmcgui.Dialog().notification('Orion', 'No liked lists found', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    
    for item in liked:
        lst = item.get('list', {})
        user = lst.get('user', {})
        
        name = lst.get('name', 'Unknown List')
        username = user.get('username', 'unknown')
        item_count = lst.get('item_count', 0)
        list_id = lst.get('ids', {}).get('slug', '')
        
        display = f"[COLOR magenta]{name}[/COLOR] by {username} ({item_count} items)"
        
        li = xbmcgui.ListItem(label=display)
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        
        url = build_url({
            'action': 'trakt_list_items',
            'username': username,
            'list_id': list_id,
            'list_name': name
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Pagination
    if len(liked) >= 20:
        add_directory_item(
            f"[B][COLOR cyan]Load More Liked Lists[/COLOR][/B]",
            {'action': 'trakt_liked_lists', 'page': page + 1}
        )
    
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_list_items(params):
    """Display items from a specific Trakt list"""
    from resources.lib import trakt, tmdb
    
    username = params.get('username', 'me')
    list_id = params.get('list_id', '')
    list_name = params.get('list_name', 'List')
    page = int(params.get('page', 1))
    
    trakt_api = trakt.TraktAPI()
    items = trakt_api.get_list_items(username, list_id, page)
    
    if not items:
        xbmcgui.Dialog().notification('Orion', 'No items in list', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    
    for item in items:
        item_type = item.get('type', 'movie')
        
        if item_type == 'movie':
            media = item.get('movie', {})
            media_type = 'movie'
        elif item_type == 'show':
            media = item.get('show', {})
            media_type = 'tv'
        else:
            continue
        
        title = media.get('title', 'Unknown')
        year = media.get('year', '')
        tmdb_id = media.get('ids', {}).get('tmdb')
        
        poster = ADDON_ICON
        backdrop = ADDON_FANART
        plot = ''
        
        if tmdb_id:
            try:
                if media_type == 'movie':
                    details = tmdb.get_movie_details(tmdb_id)
                else:
                    details = tmdb.get_tv_details(tmdb_id)
                poster = tmdb.get_poster_url(details.get('poster_path')) or ADDON_ICON
                backdrop = tmdb.get_backdrop_url(details.get('backdrop_path')) or ADDON_FANART
                plot = details.get('overview', '')
            except:
                pass
        
        display = f"{title} ({year})" if year else title
        
        li = xbmcgui.ListItem(label=display)
        li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': backdrop})
        li.setInfo('video', {'title': title, 'year': year, 'plot': plot})
        
        if media_type == 'movie':
            url = build_url({'action': 'movie_sources', 'id': tmdb_id, 'title': title, 'year': year})
        else:
            url = build_url({'action': 'tv_seasons', 'id': tmdb_id, 'title': title})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Pagination
    if len(items) >= 50:
        add_directory_item(
            f"[B][COLOR cyan]Load More...[/COLOR][/B]",
            {'action': 'trakt_list_items', 'username': username, 'list_id': list_id, 'list_name': list_name, 'page': page + 1}
        )
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_collection(params):
    """Display Trakt collection"""
    from resources.lib import trakt, tmdb
    
    media_type = params.get('type', 'movies')
    
    trakt_api = trakt.TraktAPI()
    
    if media_type == 'movies':
        items = trakt_api.get_collection_movies()
    else:
        items = trakt_api.get_collection_shows()
    
    _display_trakt_items(items, media_type, 'collection')
    
    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movies' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_watched(params):
    """Display Trakt watched history"""
    from resources.lib import trakt, tmdb
    
    media_type = params.get('type', 'movies')
    
    trakt_api = trakt.TraktAPI()
    
    if media_type == 'movies':
        items = trakt_api.get_watched_movies()
    else:
        items = trakt_api.get_watched_shows()
    
    _display_trakt_items(items, media_type, 'watched')
    
    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movies' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_recommendations(params):
    """Display Trakt recommendations"""
    from resources.lib import trakt, tmdb
    
    media_type = params.get('type', 'movies')
    page = int(params.get('page', 1))
    
    trakt_api = trakt.TraktAPI()
    
    if media_type == 'movies':
        items = trakt_api.get_recommendations_movies(page)
    else:
        items = trakt_api.get_recommendations_shows(page)
    
    for item in items:
        title = item.get('title', 'Unknown')
        year = item.get('year', '')
        tmdb_id = item.get('ids', {}).get('tmdb')
        
        poster = ADDON_ICON
        backdrop = ADDON_FANART
        plot = ''
        
        if tmdb_id:
            try:
                if media_type == 'movies':
                    details = tmdb.get_movie_details(tmdb_id)
                else:
                    details = tmdb.get_tv_details(tmdb_id)
                poster = tmdb.get_poster_url(details.get('poster_path')) or ADDON_ICON
                backdrop = tmdb.get_backdrop_url(details.get('backdrop_path')) or ADDON_FANART
                plot = details.get('overview', '')
            except:
                pass
        
        display = f"{title} ({year})" if year else title
        
        li = xbmcgui.ListItem(label=display)
        li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': backdrop})
        li.setInfo('video', {'title': title, 'year': year, 'plot': plot})
        
        if media_type == 'movies':
            url = build_url({'action': 'movie_sources', 'id': tmdb_id, 'title': title, 'year': year})
        else:
            url = build_url({'action': 'tv_seasons', 'id': tmdb_id, 'title': title})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    # Pagination
    if len(items) >= 20:
        add_directory_item(
            f"[B][COLOR cyan]Load More Recommendations[/COLOR][/B]",
            {'action': 'trakt_recommendations', 'type': media_type, 'page': page + 1}
        )
    
    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movies' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def _display_trakt_items(items, media_type, list_type):
    """Helper to display Trakt items"""
    from resources.lib import tmdb
    
    for item in items:
        if media_type == 'movies':
            media = item.get('movie', item)
            mt = 'movie'
        else:
            media = item.get('show', item)
            mt = 'tv'
        
        title = media.get('title', 'Unknown')
        year = media.get('year', '')
        tmdb_id = media.get('ids', {}).get('tmdb')
        
        poster = ADDON_ICON
        backdrop = ADDON_FANART
        plot = ''
        
        if tmdb_id:
            try:
                if mt == 'movie':
                    details = tmdb.get_movie_details(tmdb_id)
                else:
                    details = tmdb.get_tv_details(tmdb_id)
                poster = tmdb.get_poster_url(details.get('poster_path')) or ADDON_ICON
                backdrop = tmdb.get_backdrop_url(details.get('backdrop_path')) or ADDON_FANART
                plot = details.get('overview', '')
            except:
                pass
        
        display = f"{title} ({year})" if year else title
        
        li = xbmcgui.ListItem(label=display)
        li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': backdrop})
        li.setInfo('video', {'title': title, 'year': year, 'plot': plot, 'mediatype': 'movie' if mt == 'movie' else 'tvshow'})
        
        # Context menu for watchlist
        if list_type == 'watchlist':
            trakt_ids = media.get('ids', {})
            context_items = [
                ('Remove from Watchlist', f'RunPlugin({build_url({"action": "trakt_remove_watchlist", "type": mt, "imdb": trakt_ids.get("imdb", ""), "tmdb": tmdb_id or ""})})')
            ]
            li.addContextMenuItems(context_items)
        
        if mt == 'movie':
            url = build_url({'action': 'movie_sources', 'id': tmdb_id, 'title': title, 'year': year})
        else:
            url = build_url({'action': 'tv_seasons', 'id': tmdb_id, 'title': title})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

def trakt_list(params):
    """Display Trakt list"""
    from resources.lib import trakt, tmdb
    
    list_type = params.get('list', 'watchlist')
    media_type = params.get('type', 'movies')
    
    trakt_api = trakt.TraktAPI()
    items = trakt_api.get_list(list_type, media_type)
    
    for item in items:
        if media_type == 'movies':
            movie = item.get('movie', item)
            title = movie.get('title', 'Unknown')
            year = movie.get('year', '')
            tmdb_id = movie.get('ids', {}).get('tmdb')
            
            if tmdb_id:
                details = tmdb.get_movie_details(tmdb_id)
                poster = tmdb.get_poster_url(details.get('poster_path'))
                backdrop = tmdb.get_backdrop_url(details.get('backdrop_path'))
                plot = details.get('overview', '')
            else:
                poster = ADDON_ICON
                backdrop = ADDON_FANART
                plot = ''
            
            display = f"{title} ({year})" if year else title
            
            li = xbmcgui.ListItem(label=display)
            li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': backdrop})
            li.setInfo('video', {'title': title, 'year': year, 'plot': plot, 'mediatype': 'movie'})
            
            url = build_url({'action': 'movie_sources', 'id': tmdb_id, 'title': title, 'year': year})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        else:
            show = item.get('show', item)
            title = show.get('title', 'Unknown')
            year = show.get('year', '')
            tmdb_id = show.get('ids', {}).get('tmdb')
            
            if tmdb_id:
                details = tmdb.get_tv_details(tmdb_id)
                poster = tmdb.get_poster_url(details.get('poster_path'))
                backdrop = tmdb.get_backdrop_url(details.get('backdrop_path'))
                plot = details.get('overview', '')
            else:
                poster = ADDON_ICON
                backdrop = ADDON_FANART
                plot = ''
            
            display = f"{title} ({year})" if year else title
            
            li = xbmcgui.ListItem(label=display)
            li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': backdrop})
            li.setInfo('video', {'title': title, 'year': year, 'plot': plot, 'mediatype': 'tvshow'})
            
            url = build_url({'action': 'tv_seasons', 'id': tmdb_id, 'title': title})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movies' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

# ============== SERVICE PAIRING ==============

def pair_orionoid():
    """Orionoid API key authorization"""
    keyboard = xbmc.Keyboard('', 'Enter Orionoid API Key')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        api_key = keyboard.getText().strip()
        if api_key:
            ADDON.setSetting('orionoid_api_key', api_key)
            ADDON.setSetting('orionoid_status', 'Authorized')
            xbmcgui.Dialog().ok('Orionoid', '[COLOR lime]API Key saved successfully![/COLOR]\n\nGet your API key from: https://panel.orionoid.com')

def configure_mediafusion():
    """Configure MediaFusion manifest URL"""
    dialog = xbmcgui.Dialog()
    result = dialog.yesno(
        'MediaFusion Configuration',
        'MediaFusion requires configuration on their website.\n\n'
        'Visit: https://mediafusion.elfhosted.com/configure\n\n'
        'After configuring, copy the manifest URL and enter it here.',
        yeslabel='Enter URL',
        nolabel='Open Browser'
    )
    
    if result:
        keyboard = xbmc.Keyboard(ADDON.getSetting('mediafusion_manifest'), 'Enter MediaFusion Manifest URL')
        keyboard.doModal()
        
        if keyboard.isConfirmed():
            manifest_url = keyboard.getText().strip()
            if manifest_url:
                ADDON.setSetting('mediafusion_manifest', manifest_url)
                ADDON.setSetting('mediafusion_status', 'Configured')
                xbmcgui.Dialog().ok('MediaFusion', '[COLOR lime]Manifest URL saved![/COLOR]')

def configure_jackettio():
    """Configure Jackettio manifest URL"""
    dialog = xbmcgui.Dialog()
    result = dialog.yesno(
        'Jackettio Configuration',
        'Jackettio requires configuration on their website.\n\n'
        'Visit: https://jackettio.elfhosted.com/configure\n\n'
        'After configuring, copy the manifest URL and enter it here.',
        yeslabel='Enter URL',
        nolabel='Cancel'
    )
    
    if result:
        keyboard = xbmc.Keyboard(ADDON.getSetting('jackettio_manifest'), 'Enter Jackettio Manifest URL')
        keyboard.doModal()
        
        if keyboard.isConfirmed():
            manifest_url = keyboard.getText().strip()
            if manifest_url:
                ADDON.setSetting('jackettio_manifest', manifest_url)
                ADDON.setSetting('jackettio_status', 'Configured')
                xbmcgui.Dialog().ok('Jackettio', '[COLOR lime]Manifest URL saved![/COLOR]')

def configure_meteor():
    """Configure Meteor Stremio addon URL"""
    dialog = xbmcgui.Dialog()
    result = dialog.yesno(
        'Meteor Configuration',
        'Meteor is a Stremio addon for movies, TV shows & anime.\n\n'
        'Visit: https://meteorfortheweebs.midnightignite.me/configure\n\n'
        'After configuring with your debrid service, copy the manifest URL.',
        yeslabel='Enter URL',
        nolabel='Use Default'
    )
    
    if result:
        keyboard = xbmc.Keyboard(ADDON.getSetting('meteor_manifest'), 'Enter Meteor Manifest URL')
        keyboard.doModal()
        
        if keyboard.isConfirmed():
            manifest_url = keyboard.getText().strip()
            if manifest_url:
                ADDON.setSetting('meteor_manifest', manifest_url)
                ADDON.setSetting('meteor_status', 'Configured')
                ADDON.setSetting('meteor_enabled', 'true')
                xbmcgui.Dialog().ok('Meteor', '[COLOR lime]Meteor configured successfully![/COLOR]')
    else:
        # Use default public instance
        ADDON.setSetting('meteor_manifest', 'https://meteorfortheweebs.midnightignite.me')
        ADDON.setSetting('meteor_status', 'Using Public Instance')
        ADDON.setSetting('meteor_enabled', 'true')
        xbmcgui.Dialog().ok('Meteor', '[COLOR lime]Using default Meteor instance.[/COLOR]\n\nFor best results, configure with your debrid service on the website.')

def configure_bitmagnet():
    """Configure Bitmagnet self-hosted indexer URL"""
    dialog = xbmcgui.Dialog()
    dialog.ok(
        'Bitmagnet Configuration',
        'Bitmagnet is a self-hosted torrent indexer.\n\n'
        'You need to have Bitmagnet running on your network.\n'
        'Default port is 3333.\n\n'
        'Example: http://192.168.1.100:3333'
    )
    
    keyboard = xbmc.Keyboard(ADDON.getSetting('bitmagnet_url'), 'Enter Bitmagnet URL (e.g. http://192.168.1.100:3333)')
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        bitmagnet_url = keyboard.getText().strip()
        if bitmagnet_url:
            # Test the connection
            import urllib.request
            import ssl
            import json
            
            try:
                test_url = f"{bitmagnet_url}/graphql"
                test_query = {"query": "{ __typename }"}
                
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                req = urllib.request.Request(
                    test_url,
                    data=json.dumps(test_query).encode('utf-8'),
                    headers=headers,
                    method='POST'
                )
                
                ctx = ssl._create_unverified_context()
                with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    
                if result:
                    ADDON.setSetting('bitmagnet_url', bitmagnet_url)
                    ADDON.setSetting('bitmagnet_status', 'Connected')
                    ADDON.setSetting('bitmagnet_enabled', 'true')
                    xbmcgui.Dialog().ok('Bitmagnet', '[COLOR lime]Successfully connected to Bitmagnet![/COLOR]')
                else:
                    raise Exception("Invalid response")
                    
            except Exception as e:
                xbmc.log(f"Bitmagnet connection test failed: {e}", xbmc.LOGWARNING)
                # Still save the URL but mark as not verified
                ADDON.setSetting('bitmagnet_url', bitmagnet_url)
                ADDON.setSetting('bitmagnet_status', 'URL Saved (Not Verified)')
                xbmcgui.Dialog().ok('Bitmagnet', f'[COLOR yellow]URL saved but connection test failed.[/COLOR]\n\nError: {str(e)[:50]}\n\nPlease verify your Bitmagnet is running.')

def open_settings():
    """Open addon settings"""
    ADDON.openSettings()

def clear_cache():
    """Clear addon cache"""
    import xbmcvfs
    
    cache_path = xbmcvfs.translatePath(f'special://temp/{ADDON_ID}/')
    if xbmcvfs.exists(cache_path):
        import shutil
        shutil.rmtree(cache_path)
    
    xbmcgui.Dialog().notification('Orion', 'Cache cleared', ADDON_ICON)

def clear_history():
    """Clear watch history"""
    from resources.lib import database
    
    if xbmcgui.Dialog().yesno('Clear History', 'Are you sure you want to clear all watch history?'):
        database.clear_history()
        xbmcgui.Dialog().notification('Orion', 'History cleared', ADDON_ICON)

def clear_favorites():
    """Clear all favorites"""
    from resources.lib import database
    
    if xbmcgui.Dialog().yesno('Clear Favorites', 'Are you sure you want to clear all favorites?'):
        database.clear_favorites()
        xbmcgui.Dialog().notification('Orion', 'Favorites cleared', ADDON_ICON)

# ============== ACCOUNT STATUS ==============

def account_status(params):
    """Display debrid account status menu"""
    from resources.lib import debrid
    
    # Get all account info
    accounts = debrid.get_all_account_info()
    services = debrid.get_debrid_status_summary()
    
    # Header
    li = xbmcgui.ListItem(label="[B][COLOR gold]═══ Debrid Account Status ═══[/COLOR][/B]")
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
    
    # Quick Status Popup button
    li = xbmcgui.ListItem(label="[B][COLOR lime]📊 Quick Status Popup[/COLOR][/B]")
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'quick_status_popup'}), li, isFolder=False)
    
    # Test All Connections button
    li = xbmcgui.ListItem(label="[B][COLOR cyan]🔌 Test All Connections[/COLOR][/B]")
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'test_all_connections'}), li, isFolder=False)
    
    # Debug Info button
    li = xbmcgui.ListItem(label="[B][COLOR orange]🔧 Debug Settings Info[/COLOR][/B]")
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'debug_settings'}), li, isFolder=False)
    
    # Spacer
    li = xbmcgui.ListItem(label="")
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
    
    # Display each service
    for service in services:
        service_name = service['name']
        status = service['status']
        key = service['key']
        
        # Find detailed account info if available
        account_info = None
        for acc in accounts:
            if acc['service'] == service_name:
                account_info = acc
                break
        
        if account_info:
            # Authorized service with details
            days_left = account_info.get('days_left', 0)
            expiry_date = account_info.get('expiry_date', 'Unknown')
            premium_status = account_info.get('status', 'Unknown')
            username = account_info.get('username', 'Unknown')
            points = account_info.get('points', 0)
            
            # Color code days left
            if days_left <= 0:
                days_color = 'red'
                days_text = 'EXPIRED'
            elif days_left <= 10:
                days_color = 'orange'
                days_text = f'{days_left} days left'
            elif days_left <= 30:
                days_color = 'yellow'
                days_text = f'{days_left} days left'
            else:
                days_color = 'lime'
                days_text = f'{days_left} days left'
            
            # Main service entry
            display = f"[B][COLOR cyan]{service_name}[/COLOR][/B] - [COLOR lime]{premium_status}[/COLOR]"
            li = xbmcgui.ListItem(label=display)
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': f'account_details', 'service': key}), li, isFolder=True)
            
            # Username
            li = xbmcgui.ListItem(label=f"    [COLOR white]User:[/COLOR] {username}")
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
            
            # Expiry
            li = xbmcgui.ListItem(label=f"    [COLOR white]Expires:[/COLOR] {expiry_date} [COLOR {days_color}]({days_text})[/COLOR]")
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
            
            # Points (if applicable)
            if points:
                li = xbmcgui.ListItem(label=f"    [COLOR white]Points:[/COLOR] {points}")
                li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
                xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
            
            # Spacer
            li = xbmcgui.ListItem(label="")
            xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
        else:
            # Not authorized
            display = f"[B][COLOR cyan]{service_name}[/COLOR][/B] - {status}"
            li = xbmcgui.ListItem(label=display)
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            
            # Link to authorize
            action_map = {'rd': 'pair_rd', 'pm': 'pair_pm', 'ad': 'pair_ad', 'tb': 'pair_tb'}
            xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': action_map.get(key, 'noop')}), li, isFolder=False)
            
            li = xbmcgui.ListItem(label=f"    [COLOR yellow]Click above to authorize[/COLOR]")
            li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
            xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': action_map.get(key, 'noop')}), li, isFolder=False)
            
            # Spacer
            li = xbmcgui.ListItem(label="")
            xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
    
    # Refresh button
    li = xbmcgui.ListItem(label="[B][COLOR cyan]↻ Refresh Status[/COLOR][/B]")
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'account_status'}), li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'files')
    xbmcplugin.endOfDirectory(HANDLE)


def quick_status_popup(params):
    """Show a quick popup dialog with all debrid service statuses"""
    from resources.lib import debrid
    
    addon = xbmcaddon.Addon()
    
    lines = []
    lines.append("[B]═══ DEBRID STATUS ═══[/B]\n")
    
    service_info = [
        ('Real-Debrid', 'rd'),
        ('Premiumize', 'pm'),
        ('AllDebrid', 'ad'),
        ('TorBox', 'tb')
    ]
    
    any_authorized = False
    
    for name, key in service_info:
        token = addon.getSetting(f'{key}_token')
        enabled = addon.getSetting(f'{key}_enabled')
        
        if token:
            any_authorized = True
            if enabled == 'true':
                status = "[COLOR lime]✓ READY[/COLOR]"
            else:
                status = "[COLOR yellow]⚠ Authorized but DISABLED[/COLOR]"
            
            # Try to get account info
            service_map = {
                'rd': debrid.RealDebrid,
                'pm': debrid.Premiumize,
                'ad': debrid.AllDebrid,
                'tb': debrid.TorBox
            }
            
            try:
                service = service_map[key]()
                info = service.get_account_info()
                if info:
                    days = info.get('days_left', 0)
                    if days <= 0:
                        expiry = "[COLOR red]EXPIRED[/COLOR]"
                    elif days <= 10:
                        expiry = f"[COLOR orange]{days} days left[/COLOR]"
                    else:
                        expiry = f"[COLOR lime]{days} days left[/COLOR]"
                    status += f" - {expiry}"
            except:
                pass
        else:
            status = "[COLOR red]✗ Not Authorized[/COLOR]"
        
        lines.append(f"[B]{name}:[/B] {status}")
    
    if not any_authorized:
        lines.append("\n[COLOR yellow]No debrid services are authorized![/COLOR]")
        lines.append("Go to Settings to authorize a service.")
    
    message = "\n".join(lines)
    
    xbmcgui.Dialog().ok('Orion - Debrid Status', message)


def test_all_connections(params):
    """Test connections to all authorized debrid services"""
    from resources.lib import debrid
    
    addon = xbmcaddon.Addon()
    
    progress = xbmcgui.DialogProgress()
    progress.create('Testing Debrid Connections', 'Please wait...')
    
    results = []
    
    service_info = [
        ('Real-Debrid', 'rd', debrid.RealDebrid),
        ('Premiumize', 'pm', debrid.Premiumize),
        ('AllDebrid', 'ad', debrid.AllDebrid),
        ('TorBox', 'tb', debrid.TorBox)
    ]
    
    for i, (name, key, cls) in enumerate(service_info):
        progress.update(int((i / len(service_info)) * 100), f'Testing {name}...')
        
        token = addon.getSetting(f'{key}_token')
        enabled = addon.getSetting(f'{key}_enabled')
        
        if not token:
            results.append(f"[B]{name}:[/B] [COLOR gray]Not configured[/COLOR]")
            continue
        
        try:
            service = cls()
            info = service.get_account_info()
            
            if info:
                username = info.get('username', 'Unknown')
                status = info.get('status', 'Unknown')
                days = info.get('days_left', 0)
                
                if enabled == 'true':
                    enable_status = "[COLOR lime]Enabled[/COLOR]"
                else:
                    enable_status = "[COLOR yellow]Disabled[/COLOR]"
                
                results.append(f"[B]{name}:[/B] [COLOR lime]✓ Connected[/COLOR] - {username} ({status}) - {enable_status}")
            else:
                results.append(f"[B]{name}:[/B] [COLOR red]✗ API Error[/COLOR] - Token may be invalid")
        except Exception as e:
            results.append(f"[B]{name}:[/B] [COLOR red]✗ Error: {str(e)[:50]}[/COLOR]")
    
    progress.close()
    
    message = "\n".join(results)
    xbmcgui.Dialog().ok('Connection Test Results', message)


def debug_settings(params):
    """Show raw settings values for debugging"""
    addon = xbmcaddon.Addon()
    
    lines = []
    lines.append("[B]═══ RAW SETTINGS DEBUG ═══[/B]\n")
    
    settings_to_check = [
        ('rd_token', 'Real-Debrid Token'),
        ('rd_enabled', 'Real-Debrid Enabled'),
        ('rd_refresh', 'Real-Debrid Refresh Token'),
        ('rd_client_id', 'Real-Debrid Client ID'),
        ('rd_client_secret', 'Real-Debrid Client Secret'),
        ('pm_token', 'Premiumize Token'),
        ('pm_enabled', 'Premiumize Enabled'),
        ('ad_token', 'AllDebrid Token'),
        ('ad_enabled', 'AllDebrid Enabled'),
        ('tb_token', 'TorBox Token'),
        ('tb_enabled', 'TorBox Enabled'),
    ]
    
    for setting_id, label in settings_to_check:
        value = addon.getSetting(setting_id)
        if 'token' in setting_id.lower() or 'secret' in setting_id.lower():
            # Mask sensitive values
            if value:
                display = f"[COLOR lime]SET[/COLOR] ({len(value)} chars)"
            else:
                display = "[COLOR red]EMPTY[/COLOR]"
        else:
            display = f"'{value}'" if value else "[COLOR red]EMPTY[/COLOR]"
        
        lines.append(f"{label}: {display}")
    
    lines.append("\n[COLOR yellow]TIP: If tokens show SET but enabled shows EMPTY,[/COLOR]")
    lines.append("[COLOR yellow]try re-authorizing the service.[/COLOR]")
    
    message = "\n".join(lines)
    xbmcgui.Dialog().textviewer('Debug Settings', message)


def clear_debrid_auth(params):
    """Clear authorization for a specific debrid service"""
    service_key = params.get('service', '')
    
    if not service_key:
        return
    
    service_names = {
        'rd': 'Real-Debrid',
        'pm': 'Premiumize',
        'ad': 'AllDebrid',
        'tb': 'TorBox'
    }
    
    service_name = service_names.get(service_key, 'Unknown')
    
    if xbmcgui.Dialog().yesno('Clear Authorization', f'Are you sure you want to clear {service_name} authorization?\n\nYou will need to re-authorize to use this service.'):
        addon = xbmcaddon.Addon()
        
        # Clear all related settings
        settings_to_clear = [f'{service_key}_token', f'{service_key}_enabled']
        if service_key == 'rd':
            settings_to_clear.extend(['rd_refresh', 'rd_client_id', 'rd_client_secret'])
        
        for setting in settings_to_clear:
            addon.setSetting(setting, '')
        
        xbmcgui.Dialog().notification('Orion', f'{service_name} authorization cleared', ADDON_ICON)
        xbmc.executebuiltin('Container.Refresh')
    """Show detailed account information for a specific service"""
    from resources.lib import debrid
    
    service_key = params.get('service', 'rd')
    
    service_map = {
        'rd': ('Real-Debrid', debrid.RealDebrid),
        'pm': ('Premiumize', debrid.Premiumize),
        'ad': ('AllDebrid', debrid.AllDebrid),
        'tb': ('TorBox', debrid.TorBox)
    }
    
    service_name, service_cls = service_map.get(service_key, ('Unknown', None))
    
    if not service_cls:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    
    service = service_cls()
    account_info = service.get_account_info()
    
    if not account_info:
        xbmcgui.Dialog().notification('Orion', f'{service_name} account info unavailable', ADDON_ICON)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    
    # Header
    li = xbmcgui.ListItem(label=f"[B][COLOR gold]═══ {service_name} Account ═══[/COLOR][/B]")
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
    
    # Account details
    details = [
        ('Status', account_info.get('status', 'Unknown')),
        ('Username', account_info.get('username', 'Unknown')),
        ('Email', account_info.get('email', 'N/A') or 'N/A'),
        ('Expiry Date', account_info.get('expiry_date', 'Unknown')),
        ('Days Remaining', str(account_info.get('days_left', 0))),
    ]
    
    if account_info.get('points'):
        details.append(('Points/Credits', str(account_info.get('points', 0))))
    
    if account_info.get('plan'):
        details.append(('Plan', account_info.get('plan')))
    
    for label, value in details:
        # Color code days remaining
        if label == 'Days Remaining':
            days = int(value)
            if days <= 0:
                value = f'[COLOR red]{value} (EXPIRED)[/COLOR]'
            elif days <= 10:
                value = f'[COLOR orange]{value}[/COLOR]'
            elif days <= 30:
                value = f'[COLOR yellow]{value}[/COLOR]'
            else:
                value = f'[COLOR lime]{value}[/COLOR]'
        
        li = xbmcgui.ListItem(label=f"[COLOR white]{label}:[/COLOR] {value}")
        li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
    
    # Actions
    li = xbmcgui.ListItem(label="")
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'noop'}), li, isFolder=False)
    
    # Re-authorize option
    action_map = {'rd': 'pair_rd', 'pm': 'pair_pm', 'ad': 'pair_ad', 'tb': 'pair_tb'}
    li = xbmcgui.ListItem(label=f"[COLOR yellow]Re-authorize {service_name}[/COLOR]")
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': action_map.get(service_key, 'noop')}), li, isFolder=False)
    
    # Clear authorization option
    li = xbmcgui.ListItem(label=f"[COLOR red]Clear {service_name} Authorization[/COLOR]")
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'clear_debrid_auth', 'service': service_key}), li, isFolder=False)
    
    # Back to status
    li = xbmcgui.ListItem(label="[B][COLOR cyan]← Back to Account Status[/COLOR][/B]")
    li.setArt({'icon': ADDON_ICON, 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'account_status'}), li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'files')
    xbmcplugin.endOfDirectory(HANDLE)

# Route actions
params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
action = params.get('action')

log(f"Action: {action}, Params: {params}")

if not action:
    main_menu()
elif action == 'movies_menu':
    movies_menu()
elif action == 'tvshows_menu':
    tvshows_menu()
elif action == 'kids_menu':
    kids_menu(params)
elif action == 'kids_list':
    kids_list(params)
elif action == 'list_content':
    list_content(params)
elif action == 'tv_seasons':
    tv_seasons(params)
elif action == 'tv_episodes':
    tv_episodes(params)
elif action == 'search_menu':
    search_menu()
elif action == 'search':
    do_search(params)
elif action == 'search_actor':
    search_actor(params)
elif action == 'actor_works':
    actor_works(params)
elif action == 'in_cinema':
    in_cinema(params)
elif action == 'latest_episodes':
    latest_episodes(params)
elif action == 'continue_watching':
    continue_watching(params)
elif action == 'watch_history':
    watch_history(params)
elif action == 'favorites_menu':
    favorites_menu(params)
elif action == 'favorites_list':
    favorites_list(params)
elif action == 'add_favorite':
    add_favorite(params)
elif action == 'remove_favorite':
    remove_favorite(params)
elif action == 'remove_history':
    remove_history(params)
elif action == 'movie_sources':
    movie_sources(params)
elif action == 'episode_sources':
    episode_sources(params)
elif action == 'play':
    play_source(params)
elif action == 'filter_quality':
    filter_quality(params)
elif action == 'filter_source':
    filter_source(params)
elif action == 'trakt_menu':
    trakt_menu()
elif action == 'trakt_list':
    trakt_list(params)
elif action == 'trakt_watchlist':
    trakt_watchlist(params)
elif action == 'trakt_my_lists':
    trakt_my_lists(params)
elif action == 'trakt_liked_lists':
    trakt_liked_lists(params)
elif action == 'trakt_list_items':
    trakt_list_items(params)
elif action == 'trakt_collection':
    trakt_collection(params)
elif action == 'trakt_watched':
    trakt_watched(params)
elif action == 'trakt_recommendations':
    trakt_recommendations(params)
elif action == 'trakt_remove_watchlist':
    from resources.lib import trakt
    trakt_api = trakt.TraktAPI()
    ids = {}
    if params.get('imdb'):
        ids['imdb'] = params.get('imdb')
    if params.get('tmdb'):
        ids['tmdb'] = int(params.get('tmdb'))
    trakt_api.remove_from_watchlist(params.get('type', 'movie'), ids)
    xbmcgui.Dialog().notification('Orion', 'Removed from watchlist', ADDON_ICON)
    xbmc.executebuiltin('Container.Refresh')
elif action == 'open_settings':
    open_settings()
elif action == 'account_status':
    account_status(params)
elif action == 'account_details':
    account_details(params)
elif action == 'quick_status_popup':
    quick_status_popup(params)
elif action == 'test_all_connections':
    test_all_connections(params)
elif action == 'debug_settings':
    debug_settings(params)
elif action == 'clear_debrid_auth':
    clear_debrid_auth(params)
elif action == 'clear_cache':
    clear_cache()
elif action == 'clear_history':
    clear_history()
elif action == 'clear_favorites':
    clear_favorites()
# Service pairing
elif action == 'pair_orionoid':
    pair_orionoid()
elif action == 'configure_mediafusion':
    configure_mediafusion()
elif action == 'configure_jackettio':
    configure_jackettio()
elif action == 'configure_meteor':
    configure_meteor()
elif action == 'configure_bitmagnet':
    configure_bitmagnet()
elif action == 'pair_rd':
    from resources.lib import debrid
    debrid.RealDebrid().pair()
elif action == 'pair_pm':
    from resources.lib import debrid
    debrid.Premiumize().pair()
elif action == 'pair_ad':
    from resources.lib import debrid
    debrid.AllDebrid().pair()
elif action == 'pair_tb':
    from resources.lib import debrid
    debrid.TorBox().pair()
elif action == 'pair_trakt':
    from resources.lib import trakt
    trakt.TraktAPI().pair()
# QR Code actions
elif action == 'qr_rd':
    from resources.lib import qrcode_helper
    qrcode_helper.show_qr('Real-Debrid', 'https://real-debrid.com/device')
elif action == 'qr_pm':
    from resources.lib import qrcode_helper
    qrcode_helper.show_qr('Premiumize', 'https://premiumize.me/device')
elif action == 'qr_ad':
    from resources.lib import qrcode_helper
    qrcode_helper.show_qr('AllDebrid', 'https://alldebrid.com/pin')
elif action == 'qr_tb':
    from resources.lib import qrcode_helper
    qrcode_helper.show_qr('TorBox', 'https://torbox.app/settings')
elif action == 'qr_trakt':
    from resources.lib import qrcode_helper
    qrcode_helper.show_qr('Trakt', 'https://trakt.tv/activate')
elif action == 'noop':
    pass
elif action == 'buy_beer':
    import ssl
    kofi_url = 'https://ko-fi.com/zeus768'
    qr_file = os.path.join(xbmcvfs.translatePath('special://temp/'), 'kofi_qr.png')
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            f'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(kofi_url)}&bgcolor=0-0-0&color=255-255-255',
            headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            with open(qr_file, 'wb') as f:
                f.write(resp.read())
        xbmc.executebuiltin(f'ShowPicture({qr_file})')
        xbmc.sleep(300)
    except:
        pass
    xbmcgui.Dialog().ok('Support zeus768', 'Scan QR or visit:\n[COLOR cyan]https://ko-fi.com/zeus768[/COLOR]')
    try:
        xbmc.executebuiltin('Action(Back)')
    except:
        pass
else:
    log(f"Unknown action: {action}", xbmc.LOGWARNING)
    main_menu()
