# -*- coding: utf-8 -*-
"""
Database module for Orion v3.0
Handles watch history, favorites, and playback progress
"""

import os
import json
import time
import xbmc
import xbmcvfs
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

def get_data_path():
    """Get the addon data path"""
    path = xbmcvfs.translatePath(f'special://userdata/addon_data/{ADDON_ID}/')
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)
    return path

def load_json_file(filename):
    """Load JSON data from file"""
    filepath = os.path.join(get_data_path(), filename)
    try:
        if xbmcvfs.exists(filepath):
            with xbmcvfs.File(filepath, 'r') as f:
                return json.loads(f.read())
    except Exception as e:
        xbmc.log(f"Error loading {filename}: {e}", xbmc.LOGWARNING)
    return {}

def save_json_file(filename, data):
    """Save JSON data to file"""
    filepath = os.path.join(get_data_path(), filename)
    try:
        with xbmcvfs.File(filepath, 'w') as f:
            f.write(json.dumps(data, indent=2))
        return True
    except Exception as e:
        xbmc.log(f"Error saving {filename}: {e}", xbmc.LOGERROR)
    return False

# ============== WATCH HISTORY ==============

def get_history():
    """Get watch history"""
    return load_json_file('history.json')

def add_to_history(item):
    """Add item to watch history
    
    item should contain:
    - id: TMDB ID
    - type: 'movie' or 'tv'
    - title: Title
    - year: Year (optional)
    - season: Season number (for TV)
    - episode: Episode number (for TV)
    - poster: Poster URL
    - backdrop: Backdrop URL
    - progress: Playback progress (0-100)
    - duration: Total duration in seconds
    - position: Current position in seconds
    """
    if ADDON.getSetting('save_history') != 'true':
        return
    
    history = get_history()
    
    # Create unique key
    if item.get('type') == 'tv':
        key = f"tv_{item.get('id')}_{item.get('season')}_{item.get('episode')}"
    else:
        key = f"movie_{item.get('id')}"
    
    # Add timestamp
    item['timestamp'] = int(time.time())
    item['key'] = key
    
    # Update or add
    history[key] = item
    
    # Enforce history limit
    limit = int(ADDON.getSetting('history_limit') or 100)
    if len(history) > limit:
        # Sort by timestamp and keep only the newest
        sorted_items = sorted(history.items(), key=lambda x: x[1].get('timestamp', 0), reverse=True)
        history = dict(sorted_items[:limit])
    
    save_json_file('history.json', history)

def get_history_list():
    """Get history as sorted list for display"""
    history = get_history()
    items = list(history.values())
    items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return items

def get_continue_watching():
    """Get items that have progress > 5% and < 90%"""
    items = get_history_list()
    return [i for i in items if 5 < i.get('progress', 0) < 90]

def remove_from_history(key):
    """Remove item from history"""
    history = get_history()
    if key in history:
        del history[key]
        save_json_file('history.json', history)

def clear_history():
    """Clear all history"""
    save_json_file('history.json', {})

def update_progress(key, position, duration):
    """Update playback progress for an item"""
    history = get_history()
    if key in history:
        progress = int((position / duration) * 100) if duration > 0 else 0
        history[key]['progress'] = progress
        history[key]['position'] = position
        history[key]['duration'] = duration
        history[key]['timestamp'] = int(time.time())
        save_json_file('history.json', history)

# ============== FAVORITES ==============

def get_favorites():
    """Get favorites"""
    return load_json_file('favorites.json')

def add_to_favorites(item):
    """Add item to favorites
    
    item should contain:
    - id: TMDB ID
    - type: 'movie' or 'tv'
    - title: Title
    - year: Year
    - poster: Poster URL
    - backdrop: Backdrop URL
    """
    favorites = get_favorites()
    
    key = f"{item.get('type')}_{item.get('id')}"
    item['timestamp'] = int(time.time())
    item['key'] = key
    
    favorites[key] = item
    save_json_file('favorites.json', favorites)

def remove_from_favorites(key):
    """Remove item from favorites"""
    favorites = get_favorites()
    if key in favorites:
        del favorites[key]
        save_json_file('favorites.json', favorites)

def is_favorite(item_type, item_id):
    """Check if item is in favorites"""
    favorites = get_favorites()
    key = f"{item_type}_{item_id}"
    return key in favorites

def get_favorites_list(item_type=None):
    """Get favorites as sorted list for display"""
    favorites = get_favorites()
    items = list(favorites.values())
    
    if item_type:
        items = [i for i in items if i.get('type') == item_type]
    
    items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return items

def clear_favorites():
    """Clear all favorites"""
    save_json_file('favorites.json', {})

# ============== NEXT EPISODE TRACKING ==============

def get_next_episode():
    """Get next episode data"""
    return load_json_file('next_episode.json')

def set_next_episode(show_id, show_title, season, episode, poster=None, backdrop=None):
    """Set next episode to play"""
    data = {
        'show_id': show_id,
        'show_title': show_title,
        'season': season,
        'episode': episode,
        'poster': poster,
        'backdrop': backdrop,
        'timestamp': int(time.time())
    }
    save_json_file('next_episode.json', data)

def clear_next_episode():
    """Clear next episode data"""
    save_json_file('next_episode.json', {})

# ============== RESUME PLAYBACK ==============

def get_resume_point(item_type, item_id, season=None, episode=None):
    """Get resume point for an item"""
    history = get_history()
    
    if item_type == 'tv':
        key = f"tv_{item_id}_{season}_{episode}"
    else:
        key = f"movie_{item_id}"
    
    if key in history:
        item = history[key]
        if item.get('progress', 0) > 5 and item.get('progress', 0) < 95:
            return item.get('position', 0)
    
    return 0
