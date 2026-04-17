# -*- coding: utf-8 -*-
"""
Local Media Scanner for Genesis
Scans configured local folders for movies and TV shows
Uses filename parsing to identify media
"""
import os
import re
import json
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import xbmcplugin

ADDON_ID = 'plugin.video.genesis'

# Video extensions to scan
VIDEO_EXTENSIONS = {
    '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
    '.m4v', '.mpg', '.mpeg', '.m2ts', '.ts', '.divx', '.xvid',
    '.iso', '.vob', '.3gp', '.ogv', '.rmvb'
}

# Patterns for parsing filenames
MOVIE_PATTERNS = [
    # Movie.Title.2024.1080p.BluRay.x264
    r'^(.+?)[\.\s](\d{4})[\.\s]',
    # Movie Title (2024)
    r'^(.+?)\s*\((\d{4})\)',
    # Movie.Title.1080p
    r'^(.+?)[\.\s](1080p|720p|480p|2160p|4k)',
]

TV_PATTERNS = [
    # Show.Name.S01E01
    r'^(.+?)[\.\s][Ss](\d{1,2})[Ee](\d{1,2})',
    # Show.Name.1x01
    r'^(.+?)[\.\s](\d{1,2})x(\d{2})',
    # Show Name - S01E01
    r'^(.+?)\s*-\s*[Ss](\d{1,2})[Ee](\d{1,2})',
]

# Settings file for local folders
LOCAL_SETTINGS_FILE = None


def get_addon():
    return xbmcaddon.Addon()


def _get_settings_path():
    global LOCAL_SETTINGS_FILE
    if LOCAL_SETTINGS_FILE is None:
        addon_data = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
        if not xbmcvfs.exists(addon_data):
            xbmcvfs.mkdirs(addon_data)
        LOCAL_SETTINGS_FILE = os.path.join(addon_data, 'local_folders.json')
    return LOCAL_SETTINGS_FILE


def get_configured_folders():
    """Get list of configured local folders"""
    settings_path = _get_settings_path()
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                data = json.load(f)
                return data.get('folders', [])
        except Exception as e:
            xbmc.log(f'Local Scanner: Error loading folders: {e}', xbmc.LOGWARNING)
    return []


def save_folders(folders):
    """Save configured folders"""
    settings_path = _get_settings_path()
    try:
        with open(settings_path, 'w') as f:
            json.dump({'folders': folders}, f, indent=2)
        return True
    except Exception as e:
        xbmc.log(f'Local Scanner: Error saving folders: {e}', xbmc.LOGERROR)
        return False


def is_configured():
    """Check if local scanning is configured"""
    folders = get_configured_folders()
    return len(folders) > 0


def add_folder():
    """Show dialog to add a new folder"""
    dialog = xbmcgui.Dialog()
    path = dialog.browse(0, 'Select Media Folder', 'files', '', False, False, '')
    
    if path:
        folders = get_configured_folders()
        if path not in folders:
            folders.append(path)
            if save_folders(folders):
                dialog.notification('Local Scanner', f'Added: {os.path.basename(path)}', 
                                   xbmcgui.NOTIFICATION_INFO, 2000)
                return True
            else:
                dialog.notification('Error', 'Failed to save folder', 
                                   xbmcgui.NOTIFICATION_ERROR)
        else:
            dialog.notification('Info', 'Folder already configured', 
                               xbmcgui.NOTIFICATION_INFO)
    return False


def remove_folder(path):
    """Remove a configured folder"""
    folders = get_configured_folders()
    if path in folders:
        folders.remove(path)
        save_folders(folders)
        return True
    return False


def parse_movie_filename(filename):
    """Parse movie information from filename"""
    # Remove extension
    name = os.path.splitext(filename)[0]
    
    for pattern in MOVIE_PATTERNS:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            title = match.group(1).replace('.', ' ').replace('_', ' ').strip()
            year = match.group(2) if len(match.groups()) > 1 else ''
            
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            
            return {
                'title': title,
                'year': year,
                'type': 'movie'
            }
    
    # Fallback - just use filename as title
    title = name.replace('.', ' ').replace('_', ' ').strip()
    title = re.sub(r'\s+', ' ', title)
    return {'title': title, 'year': '', 'type': 'movie'}


def parse_tv_filename(filename):
    """Parse TV show information from filename"""
    # Remove extension
    name = os.path.splitext(filename)[0]
    
    for pattern in TV_PATTERNS:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            title = match.group(1).replace('.', ' ').replace('_', ' ').strip()
            season = int(match.group(2))
            episode = int(match.group(3))
            
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            
            return {
                'title': title,
                'season': season,
                'episode': episode,
                'type': 'tv'
            }
    
    return None


def detect_quality(filename):
    """Detect quality from filename"""
    name = filename.lower()
    if '2160p' in name or '4k' in name or 'uhd' in name:
        return '4K'
    elif '1080p' in name or '1080i' in name:
        return '1080p'
    elif '720p' in name:
        return '720p'
    elif '480p' in name or 'sd' in name:
        return '480p'
    return 'Unknown'


def scan_folder(folder_path, progress_callback=None):
    """Scan a single folder for media files"""
    results = {'movies': [], 'tv_shows': []}
    
    if not xbmcvfs.exists(folder_path):
        return results
    
    try:
        # List directory contents
        dirs, files = xbmcvfs.listdir(folder_path)
        
        total = len(files) + len(dirs)
        current = 0
        
        # Process files
        for filename in files:
            current += 1
            if progress_callback:
                progress_callback(int((current / total) * 100), f'Scanning: {filename}')
            
            ext = os.path.splitext(filename)[1].lower()
            if ext not in VIDEO_EXTENSIONS:
                continue
            
            full_path = os.path.join(folder_path, filename)
            
            # Try to parse as TV show first
            tv_info = parse_tv_filename(filename)
            if tv_info:
                tv_info['path'] = full_path
                tv_info['filename'] = filename
                tv_info['quality'] = detect_quality(filename)
                results['tv_shows'].append(tv_info)
            else:
                # Parse as movie
                movie_info = parse_movie_filename(filename)
                movie_info['path'] = full_path
                movie_info['filename'] = filename
                movie_info['quality'] = detect_quality(filename)
                results['movies'].append(movie_info)
        
        # Recursively scan subdirectories
        for dirname in dirs:
            current += 1
            if progress_callback:
                progress_callback(int((current / total) * 100), f'Scanning: {dirname}/')
            
            subdir_path = os.path.join(folder_path, dirname)
            sub_results = scan_folder(subdir_path)
            results['movies'].extend(sub_results['movies'])
            results['tv_shows'].extend(sub_results['tv_shows'])
            
    except Exception as e:
        xbmc.log(f'Local Scanner: Error scanning {folder_path}: {e}', xbmc.LOGERROR)
    
    return results


def scan_all_folders(progress_dialog=None):
    """Scan all configured folders"""
    folders = get_configured_folders()
    all_results = {'movies': [], 'tv_shows': []}
    
    total_folders = len(folders)
    for i, folder in enumerate(folders):
        if progress_dialog:
            progress_dialog.update(int((i / total_folders) * 100), 
                                   f'Scanning folder {i+1}/{total_folders}',
                                   folder)
        
        results = scan_folder(folder)
        all_results['movies'].extend(results['movies'])
        all_results['tv_shows'].extend(results['tv_shows'])
    
    # Remove duplicates based on path
    seen_paths = set()
    unique_movies = []
    for movie in all_results['movies']:
        if movie['path'] not in seen_paths:
            seen_paths.add(movie['path'])
            unique_movies.append(movie)
    
    unique_shows = []
    for show in all_results['tv_shows']:
        if show['path'] not in seen_paths:
            seen_paths.add(show['path'])
            unique_shows.append(show)
    
    all_results['movies'] = unique_movies
    all_results['tv_shows'] = unique_shows
    
    xbmc.log(f'Local Scanner: Found {len(unique_movies)} movies, {len(unique_shows)} TV episodes', 
             xbmc.LOGINFO)
    
    return all_results


def group_tv_shows(episodes):
    """Group TV episodes by show and season"""
    shows = {}
    
    for ep in episodes:
        title = ep['title']
        season = ep.get('season', 1)
        
        if title not in shows:
            shows[title] = {'title': title, 'seasons': {}}
        
        if season not in shows[title]['seasons']:
            shows[title]['seasons'][season] = []
        
        shows[title]['seasons'][season].append(ep)
    
    # Sort episodes within each season
    for show in shows.values():
        for season_num, season_eps in show['seasons'].items():
            show['seasons'][season_num] = sorted(season_eps, 
                                                  key=lambda x: x.get('episode', 0))
    
    return shows


def get_cached_scan():
    """Get cached scan results if available"""
    addon_data = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
    cache_file = os.path.join(addon_data, 'local_cache.json')
    
    if os.path.exists(cache_file):
        try:
            # Check if cache is less than 1 hour old
            import time
            if (time.time() - os.path.getmtime(cache_file)) < 3600:
                with open(cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            xbmc.log(f'Local Scanner: Cache read error: {e}', xbmc.LOGWARNING)
    
    return None


def save_scan_cache(results):
    """Save scan results to cache"""
    addon_data = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
    cache_file = os.path.join(addon_data, 'local_cache.json')
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        xbmc.log(f'Local Scanner: Cache write error: {e}', xbmc.LOGWARNING)


def clear_cache():
    """Clear the scan cache"""
    addon_data = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
    cache_file = os.path.join(addon_data, 'local_cache.json')
    
    if os.path.exists(cache_file):
        try:
            os.remove(cache_file)
            return True
        except:
            pass
    return False


def play_local_file(path):
    """Play a local media file"""
    li = xbmcgui.ListItem(path=path)
    xbmc.Player().play(path, li)
