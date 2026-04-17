# -*- coding: utf-8 -*-
"""
Live Channels with EPG for Test1
24 Movie Channels with simulated EPG programming
Inspired by SALTS channel system
"""
import json
import time
import random
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import sys
import os
from datetime import datetime, timedelta
from urllib.parse import quote_plus

ADDON_ID = 'plugin.video.genesis'
ADDON_PATH = xbmcvfs.translatePath(f'special://home/addons/{ADDON_ID}/')

# Channel definitions with genres for EPG content
CHANNELS = [
    # Sky Cinema variants
    {'id': 'sky_premiere', 'name': 'Sky Cinema Premiere', 'genre': 'new releases', 'logo': 'sky_cinema.png'},
    {'id': 'sky_hits', 'name': 'Sky Cinema Hits', 'genre': 'popular', 'logo': 'sky_cinema.png'},
    {'id': 'sky_greats', 'name': 'Sky Cinema Greats', 'genre': 'classics', 'logo': 'sky_cinema.png'},
    {'id': 'sky_action', 'name': 'Sky Cinema Action', 'genre': '28', 'logo': 'sky_cinema.png'},
    {'id': 'sky_comedy', 'name': 'Sky Cinema Comedy', 'genre': '35', 'logo': 'sky_cinema.png'},
    {'id': 'sky_thriller', 'name': 'Sky Cinema Thriller', 'genre': '53', 'logo': 'sky_cinema.png'},
    {'id': 'sky_drama', 'name': 'Sky Cinema Drama', 'genre': '18', 'logo': 'sky_cinema.png'},
    {'id': 'sky_scifi', 'name': 'Sky Cinema Sci-Fi/Horror', 'genre': '878', 'logo': 'sky_cinema.png'},
    
    # Sony Movies variants
    {'id': 'sony_movies', 'name': 'Sony Movies', 'genre': 'popular', 'logo': 'sony.png'},
    {'id': 'sony_classic', 'name': 'Sony Movies Classic', 'genre': 'classics', 'logo': 'sony.png'},
    {'id': 'sony_action', 'name': 'Sony Movies Action', 'genre': '28', 'logo': 'sony.png'},
    
    # Other channels
    {'id': 'hallmark', 'name': 'Hallmark Channel', 'genre': '10749', 'logo': 'hallmark.png'},
    {'id': 'film4', 'name': 'Film4', 'genre': 'popular', 'logo': 'film4.png'},
    {'id': 'movies4men', 'name': 'Movies4Men', 'genre': '28,10752', 'logo': 'movies4men.png'},
    {'id': 'great_movies', 'name': 'Great! Movies', 'genre': 'popular', 'logo': 'great.png'},
    {'id': 'hbo', 'name': 'HBO', 'genre': 'new releases', 'logo': 'hbo.png'},
    {'id': 'showtime', 'name': 'Showtime', 'genre': 'popular', 'logo': 'showtime.png'},
    {'id': 'starz', 'name': 'Starz', 'genre': 'new releases', 'logo': 'starz.png'},
    {'id': 'amc', 'name': 'AMC', 'genre': 'popular', 'logo': 'amc.png'},
    {'id': 'tcm', 'name': 'TCM (Turner Classic Movies)', 'genre': 'classics', 'logo': 'tcm.png'},
    {'id': 'fx', 'name': 'FX Movies', 'genre': '28,53', 'logo': 'fx.png'},
    {'id': 'syfy', 'name': 'Syfy', 'genre': '878,27', 'logo': 'syfy.png'},
    {'id': 'paramount', 'name': 'Paramount Network', 'genre': 'popular', 'logo': 'paramount.png'},
    {'id': 'cinemax', 'name': 'Cinemax', 'genre': '28,53', 'logo': 'cinemax.png'},
]

# EPG cache
_epg_cache = {}
_epg_cache_time = 0
EPG_CACHE_DURATION = 3600  # 1 hour


def get_addon_icon():
    icon_path = os.path.join(ADDON_PATH, 'icon.png')
    return icon_path if os.path.exists(icon_path) else 'DefaultAddonVideo.png'


def get_addon_fanart():
    fanart_path = os.path.join(ADDON_PATH, 'fanart.jpg')
    return fanart_path if os.path.exists(fanart_path) else ''


def _get_tmdb_api_key():
    """Get TMDB API key from tmdb module"""
    try:
        from . import tmdb
        return tmdb.get_api_key()
    except:
        return "f15af109700aab95d564acda15bdcd97"


def _fetch_movies_for_genre(genre, limit=10):
    """Fetch movies from TMDB for a specific genre or category"""
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    
    api_key = _get_tmdb_api_key()
    movies = []
    
    try:
        if genre == 'new releases':
            url = f"https://api.themoviedb.org/3/movie/now_playing?api_key={api_key}&language=en-US&page=1"
        elif genre == 'popular':
            url = f"https://api.themoviedb.org/3/movie/popular?api_key={api_key}&language=en-US&page={random.randint(1, 5)}"
        elif genre == 'classics':
            # Movies from before 2000 that are highly rated
            url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&language=en-US&sort_by=vote_average.desc&vote_count.gte=1000&primary_release_date.lte=2000-01-01&page={random.randint(1, 10)}"
        else:
            # Genre ID(s)
            url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&language=en-US&sort_by=popularity.desc&with_genres={genre}&page={random.randint(1, 10)}"
        
        req = Request(url, headers={'User-Agent': 'Genesis Kodi Addon'})
        response = urlopen(req, timeout=10)
        data = json.loads(response.read().decode('utf-8'))
        
        for item in data.get('results', [])[:limit]:
            # Try to get actual runtime from TMDB
            runtime = item.get('runtime', 0)
            if not runtime:
                try:
                    detail_url = f"https://api.themoviedb.org/3/movie/{item.get('id')}?api_key={api_key}"
                    detail_req = Request(detail_url, headers={'User-Agent': 'Genesis Kodi Addon'})
                    detail_resp = urlopen(detail_req, timeout=5)
                    detail_data = json.loads(detail_resp.read().decode('utf-8'))
                    runtime = detail_data.get('runtime', 0)
                except:
                    pass
            if not runtime or runtime < 30:
                runtime = random.randint(90, 150)
            movies.append({
                'id': item.get('id'),
                'title': item.get('title', 'Unknown'),
                'year': (item.get('release_date') or '')[:4],
                'overview': item.get('overview', ''),
                'poster': f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get('poster_path') else '',
                'backdrop': f"https://image.tmdb.org/t/p/original{item.get('backdrop_path')}" if item.get('backdrop_path') else '',
                'rating': item.get('vote_average', 0),
                'runtime': runtime
            })
    except Exception as e:
        xbmc.log(f'Genesis Live: Failed to fetch movies for {genre}: {e}', xbmc.LOGWARNING)
    
    return movies


def _generate_epg_for_channel(channel):
    """Generate a daily EPG schedule for a channel"""
    movies = _fetch_movies_for_genre(channel['genre'], limit=12)
    
    if not movies:
        return []
    
    schedule = []
    now = datetime.now()
    # Start from midnight today
    current_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    movie_index = 0
    while current_time < now.replace(hour=23, minute=59):
        movie = movies[movie_index % len(movies)]
        runtime_minutes = movie.get('runtime', 120)
        
        end_time = current_time + timedelta(minutes=runtime_minutes)
        
        schedule.append({
            'start': current_time.strftime('%H:%M'),
            'end': end_time.strftime('%H:%M'),
            'start_timestamp': current_time.timestamp(),
            'end_timestamp': end_time.timestamp(),
            'movie': movie
        })
        
        current_time = end_time
        movie_index += 1
    
    return schedule


def _get_channel_epg(channel_id):
    """Get EPG for a specific channel with caching"""
    global _epg_cache, _epg_cache_time
    
    now = time.time()
    
    # Refresh cache if expired
    if now - _epg_cache_time > EPG_CACHE_DURATION:
        _epg_cache = {}
        _epg_cache_time = now
    
    if channel_id not in _epg_cache:
        channel = next((c for c in CHANNELS if c['id'] == channel_id), None)
        if channel:
            _epg_cache[channel_id] = _generate_epg_for_channel(channel)
    
    return _epg_cache.get(channel_id, [])


def _get_current_program(channel_id):
    """Get the currently playing program on a channel"""
    epg = _get_channel_epg(channel_id)
    now = time.time()
    
    for program in epg:
        if program['start_timestamp'] <= now <= program['end_timestamp']:
            return program
    
    # Fallback: return first program if nothing found
    return epg[0] if epg else None


def _get_next_programs(channel_id, count=3):
    """Get upcoming programs for a channel"""
    epg = _get_channel_epg(channel_id)
    now = time.time()
    
    upcoming = []
    for program in epg:
        if program['start_timestamp'] > now:
            upcoming.append(program)
            if len(upcoming) >= count:
                break
    
    return upcoming


def show_live_channels():
    """Display all live channels with current programming"""
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    progress = xbmcgui.DialogProgress()
    progress.create('Live Channels', 'Loading EPG data...')
    
    for i, channel in enumerate(CHANNELS):
        if progress.iscanceled():
            break
        
        progress.update(int((i / len(CHANNELS)) * 100), f'Loading {channel["name"]}...')
        
        current = _get_current_program(channel['id'])
        
        if current:
            movie = current['movie']
            now_playing = f"{movie['title']}"
            if movie.get('year'):
                now_playing += f" ({movie['year']})"
            
            # Calculate time remaining
            now = time.time()
            remaining = int((current['end_timestamp'] - now) / 60)
            
            label = f"[B]{channel['name']}[/B]"
            label2 = f"Now: {now_playing} ({remaining}min left)"
            
            li = xbmcgui.ListItem(label=label, label2=label2)
            li.setArt({
                'poster': movie.get('poster', addon_icon),
                'fanart': movie.get('backdrop', addon_fanart),
                'thumb': movie.get('poster', addon_icon),
                'icon': addon_icon
            })
            
            # Set info
            info_tag = li.getVideoInfoTag()
            info_tag.setTitle(channel['name'])
            info_tag.setPlot(f"Now Playing: {now_playing}\n\n{movie.get('overview', '')}")
            info_tag.setMediaType('video')
            
            # Add context menu for full EPG
            li.addContextMenuItems([
                ('View Full Schedule', f'RunPlugin(plugin://{ADDON_ID}/?action=channel_epg&channel_id={channel["id"]})'),
                ('Play from Beginning', f'RunPlugin(plugin://{ADDON_ID}/?action=play_channel_movie&channel_id={channel["id"]}&mode=beginning)'),
            ])
            
            url = f"{sys.argv[0]}?action=channel_play_dialog&channel_id={channel['id']}"
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)
        else:
            # No EPG data available
            li = xbmcgui.ListItem(label=f"[B]{channel['name']}[/B]", label2="Schedule unavailable")
            li.setArt({'icon': addon_icon, 'fanart': addon_fanart})
            url = f"{sys.argv[0]}?action=channel_epg&channel_id={channel['id']}"
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)
    
    progress.close()
    
    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def show_channel_epg(channel_id):
    """Display full EPG schedule for a channel"""
    handle = int(sys.argv[1])
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    channel = next((c for c in CHANNELS if c['id'] == channel_id), None)
    if not channel:
        xbmcgui.Dialog().notification('Error', 'Channel not found', xbmcgui.NOTIFICATION_ERROR)
        return
    
    epg = _get_channel_epg(channel_id)
    now = time.time()
    
    for program in epg:
        movie = program['movie']
        is_current = program['start_timestamp'] <= now <= program['end_timestamp']
        is_past = program['end_timestamp'] < now
        
        # Format label
        time_slot = f"{program['start']} - {program['end']}"
        title = movie['title']
        if movie.get('year'):
            title += f" ({movie['year']})"
        
        if is_current:
            label = f"[COLOR lime][NOW][/COLOR] {time_slot} - [B]{title}[/B]"
        elif is_past:
            label = f"[COLOR gray]{time_slot} - {title}[/COLOR]"
        else:
            label = f"{time_slot} - {title}"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': movie.get('poster', addon_icon),
            'fanart': movie.get('backdrop', addon_fanart),
            'thumb': movie.get('poster', addon_icon),
            'icon': addon_icon
        })
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(title)
        info_tag.setPlot(movie.get('overview', ''))
        info_tag.setRating(movie.get('rating', 0))
        info_tag.setMediaType('movie')
        
        # URL includes TMDB ID and title for playback
        url = f"{sys.argv[0]}?action=play_epg_movie&tmdb_id={movie['id']}&title={quote_plus(movie['title'])}&year={movie.get('year', '')}"
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)
    
    xbmcplugin.setContent(handle, 'movies')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def show_play_dialog(channel_id):
    """Show 'Play from Beginning' or 'Watch Live' dialog"""
    current = _get_current_program(channel_id)
    
    if not current:
        xbmcgui.Dialog().notification('Error', 'No program data available', xbmcgui.NOTIFICATION_WARNING)
        return
    
    movie = current['movie']
    title = movie['title']
    if movie.get('year'):
        title += f" ({movie['year']})"
    
    # Calculate progress
    now = time.time()
    elapsed = int((now - current['start_timestamp']) / 60)
    total = int((current['end_timestamp'] - current['start_timestamp']) / 60)
    
    dialog = xbmcgui.Dialog()
    options = [
        f'[B]Play from Beginning[/B] - Start {title} from the start',
        f'[B]Watch Live[/B] - Join {elapsed}min into the movie'
    ]
    
    choice = dialog.select(
        f'Now Playing: {title}',
        options
    )
    
    if choice == 0:
        # Play from beginning - search for sources
        play_epg_movie(movie['id'], movie['title'], movie.get('year', ''))
    elif choice == 1:
        # Watch live - play and seek to approximate position
        play_epg_movie(movie['id'], movie['title'], movie.get('year', ''))


def play_epg_movie(tmdb_id, title, year):
    """Play a movie from EPG using scrapers and debrid"""
    from . import scrapers as scraper_module
    from . import debrid
    from . import source_picker
    from . import free_links_scraper
    
    services = debrid.get_active_services()
    if not services:
        xbmcgui.Dialog().notification('No Debrid', 'Configure a Debrid service in Settings', xbmcgui.NOTIFICATION_ERROR, 5000)
        return
    
    search_query = f'{title} {year}' if year else title
    
    progress = xbmcgui.DialogProgress()
    progress.create('Genesis', f'Searching sources for {title}...')
    
    try:
        results = scraper_module.search_all(search_query, '1080p')
    except Exception as e:
        xbmc.log(f'EPG scraper error: {e}', xbmc.LOGERROR)
        results = []
    
    if not results:
        progress.close()
        xbmcgui.Dialog().notification('No Sources', f'No torrents found for {title}', xbmcgui.NOTIFICATION_WARNING, 4000)
        return
    
    progress.update(40, f'Found {len(results)} sources. Checking debrid cache...')
    
    # Extract hashes for cache check
    hashes = []
    for r in results:
        h = scraper_module.extract_hash(r.get('magnet', ''))
        if h:
            hashes.append(h)
            r['hash'] = h
    
    # Check cache
    cached_set = set()
    if hashes:
        try:
            cached_set = debrid.check_cache_all(hashes)
        except:
            pass
    
    progress.close()
    
    # Show source picker
    selected = source_picker.show_source_picker(results, cached_set, title, include_free_links=True)
    
    if not selected:
        return
    
    # Handle free links
    if selected.get('is_free_link'):
        progress = xbmcgui.DialogProgress()
        progress.create('Genesis', 'Resolving free link...')
        resolved_url = free_links_scraper.resolve_free_link(selected.get('url', ''))
        progress.close()
        
        if resolved_url:
            li = xbmcgui.ListItem(path=resolved_url)
            li.setInfo('video', {'title': title})
            xbmc.Player().play(resolved_url, li)
        else:
            xbmcgui.Dialog().notification('Failed', 'Could not resolve free link', xbmcgui.NOTIFICATION_ERROR)
        return
    
    # Resolve magnet via debrid
    magnet = selected.get('magnet', '')
    if not magnet:
        xbmcgui.Dialog().notification('Error', 'No magnet link', xbmcgui.NOTIFICATION_ERROR)
        return
    
    progress = xbmcgui.DialogProgress()
    progress.create('Genesis', 'Resolving via debrid...')
    
    resolved_url, svc_name = debrid.resolve_magnet(magnet)
    progress.close()
    
    if resolved_url:
        quality_str = selected.get('quality', '')
        xbmcgui.Dialog().notification(svc_name, f'Playing {title} [{quality_str}]', xbmcgui.NOTIFICATION_INFO, 3000)
        
        li = xbmcgui.ListItem(path=resolved_url)
        li.setInfo('video', {'title': title})
        xbmc.Player().play(resolved_url, li)
    else:
        xbmcgui.Dialog().notification('Failed', 'Could not resolve source', xbmcgui.NOTIFICATION_ERROR, 5000)


def play_channel_movie(channel_id, mode='beginning'):
    """Play current movie on a channel"""
    current = _get_current_program(channel_id)
    
    if not current:
        xbmcgui.Dialog().notification('Error', 'No program available', xbmcgui.NOTIFICATION_WARNING)
        return
    
    movie = current['movie']
    play_epg_movie(movie['id'], movie['title'], movie.get('year', ''))
