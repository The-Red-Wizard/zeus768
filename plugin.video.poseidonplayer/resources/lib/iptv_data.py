# -*- coding: utf-8 -*-
"""
Poseidon Player - IPTV Data Provider
Author: poseidon12
Generates M3U and XMLTV data for IPTV Manager
"""

import json
import os
import time
import requests
from datetime import datetime
import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

def log(message, level=xbmc.LOGINFO):
    xbmc.log(f"[plugin.video.poseidonplayer.iptv_data] {message}", level)

def get_credentials():
    """Get saved credentials from addon settings"""
    dns = ADDON.getSetting('dns').rstrip('/') or None
    username = ADDON.getSetting('username') or None
    password = ADDON.getSetting('password') or None
    return dns, username, password

def api_request(dns, username, password, action, extra_params=None, timeout=15):
    """Make API request to Xtream Codes server"""
    url = f"{dns}/player_api.php?username={username}&password={password}&action={action}"
    if extra_params:
        url += extra_params
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"API Error: {e}", xbmc.LOGERROR)
    return None

def load_cache(filename):
    """Load cache from file"""
    filepath = os.path.join(ADDON_DATA, filename)
    try:
        if xbmcvfs.exists(filepath):
            with xbmcvfs.File(filepath, 'r') as f:
                return json.loads(f.read())
    except Exception as e:
        log(f"Cache load error: {e}", xbmc.LOGERROR)
    return {'timestamp': 0, 'data': {}}

def get_channels():
    """Generate channels list for IPTV Manager"""
    dns, username, password = get_credentials()
    
    if not all([dns, username, password]):
        log("No credentials saved, cannot provide channels to IPTV Manager")
        return {'version': 1, 'streams': []}
    
    channels = []
    
    # Try to load from cache first
    cache = load_cache('categories_cache.json')
    categories = cache.get('data', {}).get('live', [])
    
    if not categories:
        categories = api_request(dns, username, password, "get_live_categories") or []
    
    for cat in categories:
        cat_name = cat.get('category_name', 'Unknown')
        cat_id = cat.get('category_id')
        
        # Try cache first
        channels_cache = load_cache('channels_cache.json')
        streams = channels_cache.get('data', {}).get(str(cat_id), [])
        
        if not streams:
            streams = api_request(dns, username, password, "get_live_streams", f"&category_id={cat_id}") or []
        
        for stream in streams:
            stream_id = stream.get('stream_id')
            name = stream.get('name', 'Unknown')
            icon = stream.get('stream_icon', '')
            epg_id = stream.get('epg_channel_id') or str(stream_id)
            
            play_url = f"plugin://plugin.video.poseidonplayer/?action=play_live&stream_id={stream_id}"
            
            channels.append({
                'name': name,
                'stream': play_url,
                'id': epg_id,
                'logo': icon,
                'group': cat_name,
                'radio': False
            })
    
    log(f"Providing {len(channels)} channels to IPTV Manager")
    return {'version': 1, 'streams': channels}

def get_epg():
    """Generate EPG data for IPTV Manager"""
    dns, username, password = get_credentials()
    
    if not all([dns, username, password]):
        log("No credentials saved, cannot provide EPG to IPTV Manager")
        return {'version': 1, 'epg': []}
    
    epg_data = []
    
    # Load EPG from cache
    epg_cache = load_cache('epg_cache.json')
    cached_epg = epg_cache.get('data', {})
    
    # Load channels cache
    channels_cache = load_cache('channels_cache.json')
    categories_cache = load_cache('categories_cache.json')
    
    categories = categories_cache.get('data', {}).get('live', [])
    
    for cat in categories:
        cat_id = cat.get('category_id')
        streams = channels_cache.get('data', {}).get(str(cat_id), [])
        
        for stream in streams:
            stream_id = str(stream.get('stream_id'))
            epg_id = stream.get('epg_channel_id') or stream_id
            
            # Get EPG listings from cache
            listings = cached_epg.get(stream_id, [])
            
            if not listings:
                # Fetch fresh EPG if not cached
                data = api_request(dns, username, password, "get_short_epg", f"&stream_id={stream_id}&limit=50")
                if data and 'epg_listings' in data:
                    listings = data['epg_listings']
            
            for prog in listings:
                start_ts = int(prog.get('start_timestamp', 0))
                end_ts = int(prog.get('stop_timestamp', 0))
                
                if start_ts and end_ts:
                    epg_data.append({
                        'start': datetime.utcfromtimestamp(start_ts).strftime('%Y-%m-%d %H:%M:%S'),
                        'stop': datetime.utcfromtimestamp(end_ts).strftime('%Y-%m-%d %H:%M:%S'),
                        'channel': epg_id,
                        'title': prog.get('title', ''),
                        'description': prog.get('description', ''),
                        'subtitle': '',
                        'episode': '',
                        'genre': '',
                        'image': ''
                    })
    
    log(f"Providing {len(epg_data)} EPG entries to IPTV Manager")
    return {'version': 1, 'epg': epg_data}
