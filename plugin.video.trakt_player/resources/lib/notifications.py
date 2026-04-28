# -*- coding: utf-8 -*-
"""
New Episode Notifications Service
Checks Trakt calendar for new episodes and notifies user
"""
import json
import os
import time
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

ADDON_ID = 'plugin.video.trakt_player'
ADDON_DATA_PATH = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
NOTIFIED_FILE = os.path.join(ADDON_DATA_PATH, 'notified_episodes.json')
CLIENT_ID = 'd2a8e820fec0d46079cbbceaca851648df9431cbc73ede2c10d35dfb1c7a36e2'


def _ensure_data_path():
    if not os.path.exists(ADDON_DATA_PATH):
        os.makedirs(ADDON_DATA_PATH, exist_ok=True)


def _get_trakt_token():
    """Get Trakt token from storage"""
    token_file = os.path.join(ADDON_DATA_PATH, 'trakt_token.json')
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                data = json.load(f)
                return data.get('access_token', '')
        except:
            pass
    return xbmcaddon.Addon().getSetting('trakt_access_token')


def _http_get(url, timeout=15):
    """HTTP GET with Trakt headers"""
    token = _get_trakt_token()
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'TraktPlayer Kodi Addon',
        'trakt-api-version': '2',
        'trakt-api-key': CLIENT_ID
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=timeout)
        return resp.getcode(), json.loads(resp.read().decode('utf-8'))
    except HTTPError as e:
        return e.code, None
    except Exception as e:
        xbmc.log(f'Notifications HTTP error: {e}', xbmc.LOGERROR)
        return 0, None


def _load_notified():
    """Load already notified episodes"""
    _ensure_data_path()
    if os.path.exists(NOTIFIED_FILE):
        try:
            with open(NOTIFIED_FILE, 'r') as f:
                data = json.load(f)
                # Clean old entries (older than 7 days)
                cutoff = time.time() - (7 * 24 * 3600)
                return {k: v for k, v in data.items() if v > cutoff}
        except:
            pass
    return {}


def _save_notified(notified):
    """Save notified episodes"""
    _ensure_data_path()
    try:
        with open(NOTIFIED_FILE, 'w') as f:
            json.dump(notified, f)
    except Exception as e:
        xbmc.log(f'Failed to save notified: {e}', xbmc.LOGERROR)


def check_new_episodes():
    """Check for new episodes that aired today and notify user"""
    addon = xbmcaddon.Addon()
    
    # Check if notifications are enabled
    if addon.getSetting('enable_notifications') != 'true':
        return []
    
    token = _get_trakt_token()
    if not token:
        return []
    
    # Get today's calendar
    today = datetime.now().strftime('%Y-%m-%d')
    url = f'https://api.trakt.tv/calendars/my/shows/{today}/1'
    
    status, data = _http_get(url)
    if status != 200 or not data:
        return []
    
    # Load already notified
    notified = _load_notified()
    new_episodes = []
    
    for item in data:
        if not isinstance(item, dict):
            continue
        
        show = item.get('show', {})
        episode = item.get('episode', {})
        first_aired = item.get('first_aired', '')
        
        show_title = show.get('title', 'Unknown')
        season = episode.get('season', 0)
        ep_num = episode.get('number', 0)
        ep_title = episode.get('title', '')
        
        # Create unique key
        ep_key = f"{show.get('ids', {}).get('trakt', '')}_{season}_{ep_num}"
        
        # Skip if already notified
        if ep_key in notified:
            continue
        
        # Check if episode has aired
        if first_aired:
            try:
                aired_time = datetime.strptime(first_aired[:19], '%Y-%m-%dT%H:%M:%S')
                if aired_time > datetime.utcnow():
                    continue  # Not aired yet
            except:
                pass
        
        # Add to new episodes
        new_episodes.append({
            'show': show_title,
            'season': season,
            'episode': ep_num,
            'title': ep_title,
            'key': ep_key,
            'tmdb_id': show.get('ids', {}).get('tmdb', ''),
            'imdb_id': show.get('ids', {}).get('imdb', '')
        })
        
        # Mark as notified
        notified[ep_key] = time.time()
    
    # Save updated notified list
    if new_episodes:
        _save_notified(notified)
    
    return new_episodes


def notify_new_episodes(episodes):
    """Show notifications for new episodes"""
    if not episodes:
        return
    
    addon = xbmcaddon.Addon()
    notification_style = addon.getSetting('notification_style') or 'individual'
    
    if notification_style == 'summary' and len(episodes) > 1:
        # Show single summary notification
        msg = f'{len(episodes)} new episodes available!'
        shows = list(set(ep['show'] for ep in episodes[:3]))
        if shows:
            msg += f" ({', '.join(shows)}{'...' if len(episodes) > 3 else ''})"
        xbmcgui.Dialog().notification(
            'New Episodes!',
            msg,
            xbmcgui.NOTIFICATION_INFO,
            5000
        )
    else:
        # Show individual notifications (max 3)
        for ep in episodes[:3]:
            msg = f"S{ep['season']:02d}E{ep['episode']:02d}"
            if ep['title']:
                msg += f" - {ep['title'][:30]}"
            xbmcgui.Dialog().notification(
                ep['show'],
                msg,
                xbmcgui.NOTIFICATION_INFO,
                4000
            )
            xbmc.sleep(1000)  # Small delay between notifications


def run_check():
    """Run the notification check"""
    xbmc.log('TraktPlayer: Checking for new episodes...', xbmc.LOGINFO)
    episodes = check_new_episodes()
    if episodes:
        xbmc.log(f'TraktPlayer: Found {len(episodes)} new episodes', xbmc.LOGINFO)
        notify_new_episodes(episodes)
    return episodes


def get_watchlist_shows():
    """Get shows from user's Trakt watchlist for monitoring"""
    token = _get_trakt_token()
    if not token:
        return []
    
    status, data = _http_get('https://api.trakt.tv/sync/watchlist/shows?extended=full')
    if status != 200 or not data:
        return []
    
    shows = []
    for item in data:
        show = item.get('show', {})
        shows.append({
            'title': show.get('title', ''),
            'trakt_id': show.get('ids', {}).get('trakt', ''),
            'tmdb_id': show.get('ids', {}).get('tmdb', ''),
            'imdb_id': show.get('ids', {}).get('imdb', '')
        })
    return shows
