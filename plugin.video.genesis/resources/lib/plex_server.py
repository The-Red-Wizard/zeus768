# -*- coding: utf-8 -*-
"""
Plex Server Integration for Genesis
Allows browsing and playing content from Plex Media Server
"""
import json
import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import xbmcplugin
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote_plus

ADDON_ID = 'plugin.video.genesis'
USER_AGENT = 'Genesis Kodi Addon'


def get_addon():
    return xbmcaddon.Addon()


def is_configured():
    """Check if Plex server is configured and enabled"""
    addon = get_addon()
    enabled = addon.getSetting('plex_enabled') == 'true'
    url = addon.getSetting('plex_url')
    token = addon.getSetting('plex_token')
    return enabled and url and token


def get_server_info():
    """Get Plex server URL and token"""
    addon = get_addon()
    return {
        'url': addon.getSetting('plex_url').rstrip('/'),
        'token': addon.getSetting('plex_token')
    }


def _http_get(url, token, timeout=10):
    """Make HTTP GET request to Plex server"""
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
            'X-Plex-Token': token,
            'X-Plex-Client-Identifier': 'genesis-kodi-addon',
            'X-Plex-Product': 'Genesis',
            'X-Plex-Version': '1.4.0'
        }
        req = Request(url, headers=headers, method='GET')
        response = urlopen(req, timeout=timeout)
        body = response.read().decode('utf-8')
        return json.loads(body)
    except HTTPError as e:
        xbmc.log(f'Plex HTTP Error: {e.code} for {url}', xbmc.LOGWARNING)
        return None
    except URLError as e:
        xbmc.log(f'Plex URL Error: {e.reason}', xbmc.LOGERROR)
        return None
    except Exception as e:
        xbmc.log(f'Plex Request Error: {e}', xbmc.LOGERROR)
        return None


def test_connection():
    """Test connection to Plex server"""
    if not is_configured():
        return False, "Not configured"
    
    server = get_server_info()
    url = f"{server['url']}/identity"
    data = _http_get(url, server['token'])
    
    if data:
        return True, data.get('MediaContainer', {}).get('friendlyName', 'Unknown Server')
    return False, "Connection failed"


def get_libraries():
    """Get all libraries from Plex server"""
    if not is_configured():
        return []
    
    server = get_server_info()
    url = f"{server['url']}/library/sections"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    libraries = []
    container = data.get('MediaContainer', {})
    
    for directory in container.get('Directory', []):
        libraries.append({
            'key': directory.get('key'),
            'title': directory.get('title'),
            'type': directory.get('type'),  # movie, show, artist, photo
            'uuid': directory.get('uuid'),
            'art': directory.get('art'),
            'thumb': directory.get('thumb')
        })
    
    return libraries


def get_library_items(library_key, item_type='all'):
    """Get items from a specific library"""
    if not is_configured():
        return []
    
    server = get_server_info()
    url = f"{server['url']}/library/sections/{library_key}/{item_type}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    items = []
    container = data.get('MediaContainer', {})
    base_url = server['url']
    token = server['token']
    
    for metadata in container.get('Metadata', []):
        item = _parse_plex_item(metadata, base_url, token)
        items.append(item)
    
    return items


def get_recently_added(library_key=None, limit=50):
    """Get recently added items"""
    if not is_configured():
        return []
    
    server = get_server_info()
    
    if library_key:
        url = f"{server['url']}/library/sections/{library_key}/recentlyAdded?X-Plex-Container-Start=0&X-Plex-Container-Size={limit}"
    else:
        url = f"{server['url']}/library/recentlyAdded?X-Plex-Container-Start=0&X-Plex-Container-Size={limit}"
    
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    items = []
    container = data.get('MediaContainer', {})
    base_url = server['url']
    token = server['token']
    
    for metadata in container.get('Metadata', []):
        item = _parse_plex_item(metadata, base_url, token)
        items.append(item)
    
    return items


def get_on_deck(limit=50):
    """Get On Deck (continue watching) items"""
    if not is_configured():
        return []
    
    server = get_server_info()
    url = f"{server['url']}/library/onDeck?X-Plex-Container-Start=0&X-Plex-Container-Size={limit}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    items = []
    container = data.get('MediaContainer', {})
    base_url = server['url']
    token = server['token']
    
    for metadata in container.get('Metadata', []):
        item = _parse_plex_item(metadata, base_url, token)
        items.append(item)
    
    return items


def get_show_seasons(show_key):
    """Get seasons for a TV show"""
    if not is_configured():
        return []
    
    server = get_server_info()
    url = f"{server['url']}{show_key}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    seasons = []
    container = data.get('MediaContainer', {})
    base_url = server['url']
    token = server['token']
    
    for metadata in container.get('Metadata', []):
        if metadata.get('type') == 'season':
            season = {
                'key': metadata.get('key'),
                'title': metadata.get('title'),
                'index': metadata.get('index'),
                'thumb': _build_image_url(metadata.get('thumb'), base_url, token),
                'art': _build_image_url(metadata.get('art'), base_url, token),
                'leaf_count': metadata.get('leafCount', 0),
                'viewed_leaf_count': metadata.get('viewedLeafCount', 0)
            }
            seasons.append(season)
    
    return seasons


def get_season_episodes(season_key):
    """Get episodes for a season"""
    if not is_configured():
        return []
    
    server = get_server_info()
    url = f"{server['url']}{season_key}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    episodes = []
    container = data.get('MediaContainer', {})
    base_url = server['url']
    token = server['token']
    
    for metadata in container.get('Metadata', []):
        episode = _parse_plex_item(metadata, base_url, token)
        episodes.append(episode)
    
    return episodes


def get_playback_url(item_key):
    """Get direct playback URL for an item"""
    if not is_configured():
        return None
    
    server = get_server_info()
    
    # Get the item metadata to find the media part
    url = f"{server['url']}{item_key}"
    data = _http_get(url, server['token'])
    
    if not data:
        return None
    
    container = data.get('MediaContainer', {})
    metadata_list = container.get('Metadata', [])
    
    if not metadata_list:
        return None
    
    metadata = metadata_list[0]
    media_list = metadata.get('Media', [])
    
    if not media_list:
        return None
    
    # Get the first media and part
    media = media_list[0]
    parts = media.get('Part', [])
    
    if not parts:
        return None
    
    part = parts[0]
    part_key = part.get('key')
    
    if not part_key:
        return None
    
    # Build direct stream URL
    playback_url = f"{server['url']}{part_key}?X-Plex-Token={server['token']}"
    
    return playback_url


def search(query, limit=50):
    """Search Plex library"""
    if not is_configured():
        return []
    
    server = get_server_info()
    url = f"{server['url']}/search?query={quote_plus(query)}&limit={limit}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    items = []
    container = data.get('MediaContainer', {})
    base_url = server['url']
    token = server['token']
    
    for metadata in container.get('Metadata', []):
        item = _parse_plex_item(metadata, base_url, token)
        items.append(item)
    
    return items


def _build_image_url(path, base_url, token):
    """Build full image URL with token"""
    if not path:
        return ''
    if path.startswith('http'):
        return path
    return f"{base_url}{path}?X-Plex-Token={token}"


def _parse_plex_item(metadata, base_url, token):
    """Parse Plex metadata into a standardized item dict"""
    item_type = metadata.get('type')
    
    item = {
        'key': metadata.get('key'),
        'rating_key': metadata.get('ratingKey'),
        'type': item_type,
        'title': metadata.get('title'),
        'year': metadata.get('year'),
        'summary': metadata.get('summary', ''),
        'rating': metadata.get('rating', 0),
        'thumb': _build_image_url(metadata.get('thumb'), base_url, token),
        'art': _build_image_url(metadata.get('art'), base_url, token),
        'duration': metadata.get('duration', 0),
        'view_count': metadata.get('viewCount', 0),
        'view_offset': metadata.get('viewOffset', 0),
        'added_at': metadata.get('addedAt'),
    }
    
    # Episode specific fields
    if item_type == 'episode':
        item['episode_index'] = metadata.get('index')
        item['season_index'] = metadata.get('parentIndex')
        item['show_title'] = metadata.get('grandparentTitle')
        item['season_title'] = metadata.get('parentTitle')
    
    # Movie/Video quality info
    media_list = metadata.get('Media', [])
    if media_list:
        media = media_list[0]
        item['resolution'] = media.get('videoResolution', '')
        item['codec'] = media.get('videoCodec', '')
        item['container'] = media.get('container', '')
        item['bitrate'] = media.get('bitrate', 0)
    
    return item


def configure_server():
    """Show configuration dialog for Plex server"""
    addon = get_addon()
    dialog = xbmcgui.Dialog()
    
    # Get current values
    current_url = addon.getSetting('plex_url') or 'http://192.168.1.100:32400'
    current_token = addon.getSetting('plex_token') or ''
    
    # Get server URL
    new_url = dialog.input('Enter Plex Server URL', current_url)
    if not new_url:
        return False
    
    # Get token
    new_token = dialog.input('Enter Plex Token', current_token)
    if not new_token:
        dialog.notification('Plex', 'Token is required', xbmcgui.NOTIFICATION_WARNING)
        return False
    
    # Save settings temporarily
    addon.setSetting('plex_url', new_url)
    addon.setSetting('plex_token', new_token)
    
    # Test connection
    dialog.notification('Plex', 'Testing connection...', xbmcgui.NOTIFICATION_INFO, 2000)
    success, message = test_connection()
    
    if success:
        addon.setSetting('plex_enabled', 'true')
        dialog.notification('Plex', f'Connected to: {message}', xbmcgui.NOTIFICATION_INFO, 3000)
        return True
    else:
        addon.setSetting('plex_enabled', 'false')
        dialog.notification('Plex', f'Connection failed: {message}', xbmcgui.NOTIFICATION_ERROR, 5000)
        return False


def disable_server():
    """Disable Plex server"""
    addon = get_addon()
    addon.setSetting('plex_enabled', 'false')
    xbmcgui.Dialog().notification('Plex', 'Server disabled', xbmcgui.NOTIFICATION_INFO, 2000)
