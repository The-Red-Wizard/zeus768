# -*- coding: utf-8 -*-
"""
Emby Server Integration for Genesis
Allows browsing and playing content from Emby Media Server
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
    """Check if Emby server is configured and enabled"""
    addon = get_addon()
    enabled = addon.getSetting('emby_enabled') == 'true'
    url = addon.getSetting('emby_url')
    token = addon.getSetting('emby_token')
    return enabled and url and token


def get_server_info():
    """Get Emby server URL, token, and user ID"""
    addon = get_addon()
    return {
        'url': addon.getSetting('emby_url').rstrip('/'),
        'token': addon.getSetting('emby_token'),
        'user_id': addon.getSetting('emby_user_id')
    }


def _http_get(url, token, timeout=10):
    """Make HTTP GET request to Emby server"""
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
            'X-Emby-Token': token,
            'X-Emby-Client': 'Genesis',
            'X-Emby-Client-Version': '1.4.0',
            'X-Emby-Device-Name': 'Kodi',
            'X-Emby-Device-Id': 'genesis-kodi-addon'
        }
        req = Request(url, headers=headers, method='GET')
        response = urlopen(req, timeout=timeout)
        body = response.read().decode('utf-8')
        return json.loads(body)
    except HTTPError as e:
        xbmc.log(f'Emby HTTP Error: {e.code} for {url}', xbmc.LOGWARNING)
        return None
    except URLError as e:
        xbmc.log(f'Emby URL Error: {e.reason}', xbmc.LOGERROR)
        return None
    except Exception as e:
        xbmc.log(f'Emby Request Error: {e}', xbmc.LOGERROR)
        return None


def _http_post(url, token, data=None, timeout=10):
    """Make HTTP POST request to Emby server"""
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Emby-Token': token,
            'X-Emby-Client': 'Genesis',
            'X-Emby-Client-Version': '1.4.0',
            'X-Emby-Device-Name': 'Kodi',
            'X-Emby-Device-Id': 'genesis-kodi-addon'
        }
        req = Request(url, headers=headers, method='POST')
        if data:
            req.data = json.dumps(data).encode('utf-8')
        response = urlopen(req, timeout=timeout)
        body = response.read().decode('utf-8')
        return json.loads(body) if body else {}
    except Exception as e:
        xbmc.log(f'Emby POST Error: {e}', xbmc.LOGERROR)
        return None


def test_connection():
    """Test connection to Emby server"""
    if not is_configured():
        return False, "Not configured"
    
    server = get_server_info()
    url = f"{server['url']}/emby/System/Info"
    data = _http_get(url, server['token'])
    
    if data:
        return True, data.get('ServerName', 'Unknown Server')
    return False, "Connection failed"


def get_users():
    """Get list of users (for selecting user ID during setup)"""
    addon = get_addon()
    url = addon.getSetting('emby_url').rstrip('/')
    token = addon.getSetting('emby_token')
    
    if not url or not token:
        return []
    
    users_url = f"{url}/emby/Users"
    data = _http_get(users_url, token)
    
    if not data:
        return []
    
    users = []
    for user in data:
        users.append({
            'id': user.get('Id'),
            'name': user.get('Name'),
            'has_password': user.get('HasPassword', False)
        })
    
    return users


def get_libraries():
    """Get all libraries (views) from Emby server"""
    if not is_configured():
        return []
    
    server = get_server_info()
    url = f"{server['url']}/emby/Users/{server['user_id']}/Views"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    libraries = []
    base_url = server['url']
    
    for item in data.get('Items', []):
        libraries.append({
            'id': item.get('Id'),
            'name': item.get('Name'),
            'type': item.get('CollectionType', 'mixed'),  # movies, tvshows, music, boxsets
            'thumb': _build_image_url(item.get('Id'), 'Primary', base_url),
            'backdrop': _build_image_url(item.get('Id'), 'Backdrop', base_url)
        })
    
    return libraries


def get_library_items(library_id, include_types=None, sort_by='SortName', sort_order='Ascending', limit=100, start_index=0):
    """Get items from a specific library"""
    if not is_configured():
        return []
    
    server = get_server_info()
    
    params = {
        'ParentId': library_id,
        'SortBy': sort_by,
        'SortOrder': sort_order,
        'Recursive': 'true',
        'Limit': limit,
        'StartIndex': start_index,
        'Fields': 'Overview,Genres,Studios,DateCreated,MediaSources,Path'
    }
    
    if include_types:
        params['IncludeItemTypes'] = include_types
    
    url = f"{server['url']}/emby/Users/{server['user_id']}/Items?{urlencode(params)}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    items = []
    base_url = server['url']
    
    for item in data.get('Items', []):
        parsed = _parse_emby_item(item, base_url)
        items.append(parsed)
    
    return items


def get_recently_added(library_id=None, limit=50):
    """Get recently added items"""
    if not is_configured():
        return []
    
    server = get_server_info()
    
    params = {
        'SortBy': 'DateCreated',
        'SortOrder': 'Descending',
        'Recursive': 'true',
        'Limit': limit,
        'Fields': 'Overview,Genres,Studios,DateCreated,MediaSources,Path'
    }
    
    if library_id:
        params['ParentId'] = library_id
    
    url = f"{server['url']}/emby/Users/{server['user_id']}/Items?{urlencode(params)}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    items = []
    base_url = server['url']
    
    for item in data.get('Items', []):
        parsed = _parse_emby_item(item, base_url)
        items.append(parsed)
    
    return items


def get_continue_watching(limit=50):
    """Get items to continue watching"""
    if not is_configured():
        return []
    
    server = get_server_info()
    
    params = {
        'Limit': limit,
        'Recursive': 'true',
        'Filters': 'IsResumable',
        'SortBy': 'DatePlayed',
        'SortOrder': 'Descending',
        'Fields': 'Overview,Genres,Studios,DateCreated,MediaSources,Path'
    }
    
    url = f"{server['url']}/emby/Users/{server['user_id']}/Items?{urlencode(params)}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    items = []
    base_url = server['url']
    
    for item in data.get('Items', []):
        parsed = _parse_emby_item(item, base_url)
        items.append(parsed)
    
    return items


def get_next_up(limit=50):
    """Get next episodes to watch"""
    if not is_configured():
        return []
    
    server = get_server_info()
    
    params = {
        'Limit': limit,
        'Fields': 'Overview,Genres,Studios,DateCreated,MediaSources,Path'
    }
    
    url = f"{server['url']}/emby/Shows/NextUp?{urlencode(params)}&UserId={server['user_id']}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    items = []
    base_url = server['url']
    
    for item in data.get('Items', []):
        parsed = _parse_emby_item(item, base_url)
        items.append(parsed)
    
    return items


def get_show_seasons(show_id):
    """Get seasons for a TV show"""
    if not is_configured():
        return []
    
    server = get_server_info()
    
    params = {
        'ParentId': show_id,
        'Fields': 'Overview,DateCreated'
    }
    
    url = f"{server['url']}/emby/Users/{server['user_id']}/Items?{urlencode(params)}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    seasons = []
    base_url = server['url']
    
    for item in data.get('Items', []):
        if item.get('Type') == 'Season':
            seasons.append({
                'id': item.get('Id'),
                'name': item.get('Name'),
                'index': item.get('IndexNumber'),
                'overview': item.get('Overview', ''),
                'thumb': _build_image_url(item.get('Id'), 'Primary', base_url),
                'backdrop': _build_image_url(item.get('Id'), 'Backdrop', base_url),
                'episode_count': item.get('ChildCount', 0)
            })
    
    return sorted(seasons, key=lambda x: x.get('index', 0))


def get_season_episodes(season_id):
    """Get episodes for a season"""
    if not is_configured():
        return []
    
    server = get_server_info()
    
    params = {
        'ParentId': season_id,
        'Fields': 'Overview,DateCreated,MediaSources,Path'
    }
    
    url = f"{server['url']}/emby/Users/{server['user_id']}/Items?{urlencode(params)}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    episodes = []
    base_url = server['url']
    
    for item in data.get('Items', []):
        if item.get('Type') == 'Episode':
            episode = _parse_emby_item(item, base_url)
            episodes.append(episode)
    
    return sorted(episodes, key=lambda x: x.get('episode_index', 0))


def get_playback_url(item_id):
    """Get direct playback URL for an item"""
    if not is_configured():
        return None
    
    server = get_server_info()
    
    # Get item info to find media source
    url = f"{server['url']}/emby/Users/{server['user_id']}/Items/{item_id}?Fields=MediaSources,Path"
    data = _http_get(url, server['token'])
    
    if not data:
        return None
    
    media_sources = data.get('MediaSources', [])
    if not media_sources:
        return None
    
    # Get the first media source
    media = media_sources[0]
    
    # Build direct stream URL
    # Emby supports direct play via /Videos/{Id}/stream
    container = media.get('Container', 'mp4')
    playback_url = f"{server['url']}/emby/Videos/{item_id}/stream.{container}?Static=true&api_key={server['token']}"
    
    return playback_url


def search(query, limit=50):
    """Search Emby library"""
    if not is_configured():
        return []
    
    server = get_server_info()
    
    params = {
        'SearchTerm': query,
        'Limit': limit,
        'Recursive': 'true',
        'Fields': 'Overview,Genres,Studios,DateCreated,MediaSources,Path'
    }
    
    url = f"{server['url']}/emby/Users/{server['user_id']}/Items?{urlencode(params)}"
    data = _http_get(url, server['token'])
    
    if not data:
        return []
    
    items = []
    base_url = server['url']
    
    for item in data.get('Items', []):
        parsed = _parse_emby_item(item, base_url)
        items.append(parsed)
    
    return items


def _build_image_url(item_id, image_type, base_url):
    """Build image URL for an Emby item"""
    if not item_id:
        return ''
    return f"{base_url}/emby/Items/{item_id}/Images/{image_type}"


def _parse_emby_item(item, base_url):
    """Parse Emby item into a standardized dict"""
    item_type = item.get('Type', '').lower()
    item_id = item.get('Id')
    
    parsed = {
        'id': item_id,
        'type': item_type,
        'name': item.get('Name', ''),
        'year': item.get('ProductionYear'),
        'overview': item.get('Overview', ''),
        'rating': item.get('CommunityRating', 0),
        'thumb': _build_image_url(item_id, 'Primary', base_url),
        'backdrop': _build_image_url(item_id, 'Backdrop', base_url),
        'banner': _build_image_url(item_id, 'Banner', base_url),
        'duration': item.get('RunTimeTicks', 0) // 10000000,  # Convert ticks to seconds
        'played': item.get('UserData', {}).get('Played', False),
        'play_count': item.get('UserData', {}).get('PlayCount', 0),
        'resume_position': item.get('UserData', {}).get('PlaybackPositionTicks', 0) // 10000000,
        'date_added': item.get('DateCreated'),
        'genres': item.get('Genres', []),
        'studios': [s.get('Name') for s in item.get('Studios', [])]
    }
    
    # Episode specific fields
    if item_type == 'episode':
        parsed['episode_index'] = item.get('IndexNumber')
        parsed['season_index'] = item.get('ParentIndexNumber')
        parsed['show_name'] = item.get('SeriesName')
        parsed['show_id'] = item.get('SeriesId')
        parsed['season_id'] = item.get('SeasonId')
    
    # Quality info from media sources
    media_sources = item.get('MediaSources', [])
    if media_sources:
        media = media_sources[0]
        parsed['container'] = media.get('Container', '')
        parsed['bitrate'] = media.get('Bitrate', 0)
        
        video_streams = [s for s in media.get('MediaStreams', []) if s.get('Type') == 'Video']
        if video_streams:
            video = video_streams[0]
            parsed['resolution'] = f"{video.get('Width', 0)}x{video.get('Height', 0)}"
            parsed['codec'] = video.get('Codec', '')
    
    return parsed


def configure_server():
    """Show configuration dialog for Emby server"""
    addon = get_addon()
    dialog = xbmcgui.Dialog()
    
    # Get current values
    current_url = addon.getSetting('emby_url') or 'http://192.168.1.100:8096'
    current_token = addon.getSetting('emby_token') or ''
    
    # Get server URL
    new_url = dialog.input('Enter Emby Server URL', current_url)
    if not new_url:
        return False
    
    # Get API key/token
    new_token = dialog.input('Enter Emby API Key', current_token)
    if not new_token:
        dialog.notification('Emby', 'API Key is required', xbmcgui.NOTIFICATION_WARNING)
        return False
    
    # Save settings temporarily
    addon.setSetting('emby_url', new_url)
    addon.setSetting('emby_token', new_token)
    
    # Get users to select from
    users = get_users()
    
    if users:
        user_names = [u['name'] for u in users]
        selected = dialog.select('Select Emby User', user_names)
        
        if selected >= 0:
            addon.setSetting('emby_user_id', users[selected]['id'])
            addon.setSetting('emby_username', users[selected]['name'])
        else:
            dialog.notification('Emby', 'User selection required', xbmcgui.NOTIFICATION_WARNING)
            return False
    else:
        # Manual user ID entry
        current_user_id = addon.getSetting('emby_user_id') or ''
        user_id = dialog.input('Enter User ID (or leave blank)', current_user_id)
        if user_id:
            addon.setSetting('emby_user_id', user_id)
    
    # Test connection
    dialog.notification('Emby', 'Testing connection...', xbmcgui.NOTIFICATION_INFO, 2000)
    success, message = test_connection()
    
    if success:
        addon.setSetting('emby_enabled', 'true')
        dialog.notification('Emby', f'Connected to: {message}', xbmcgui.NOTIFICATION_INFO, 3000)
        return True
    else:
        addon.setSetting('emby_enabled', 'false')
        dialog.notification('Emby', f'Connection failed: {message}', xbmcgui.NOTIFICATION_ERROR, 5000)
        return False


def disable_server():
    """Disable Emby server"""
    addon = get_addon()
    addon.setSetting('emby_enabled', 'false')
    xbmcgui.Dialog().notification('Emby', 'Server disabled', xbmcgui.NOTIFICATION_INFO, 2000)
