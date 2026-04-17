# -*- coding: utf-8 -*-
"""
Trakt API Integration for Orion v3.0
Includes scrobbling, watchlists, liked lists
"""

import urllib.request
import urllib.parse
import json
import time
import ssl
import xbmcgui
import xbmcaddon
import xbmc
import threading

ADDON = xbmcaddon.Addon()
SSL_CONTEXT = ssl._create_unverified_context()

class TraktScrobbler:
    """Background scrobbler for Trakt"""
    
    def __init__(self, trakt_api):
        self.trakt = trakt_api
        self.is_playing = False
        self.current_item = None
        self.scrobble_thread = None
    
    def start_watching(self, media_type, ids, progress=0):
        """Start watching - send start scrobble"""
        if not self.trakt.is_authorized():
            return
        
        self.is_playing = True
        self.current_item = {'type': media_type, 'ids': ids}
        
        try:
            data = self._build_scrobble_data(media_type, ids, progress)
            self.trakt._request('/scrobble/start', data, method='POST')
            xbmc.log(f"Trakt: Started scrobbling {media_type}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"Trakt scrobble start error: {e}", xbmc.LOGWARNING)
    
    def pause_watching(self, progress=0):
        """Pause watching - send pause scrobble"""
        if not self.trakt.is_authorized() or not self.current_item:
            return
        
        try:
            data = self._build_scrobble_data(
                self.current_item['type'], 
                self.current_item['ids'], 
                progress
            )
            self.trakt._request('/scrobble/pause', data, method='POST')
        except Exception as e:
            xbmc.log(f"Trakt scrobble pause error: {e}", xbmc.LOGWARNING)
    
    def stop_watching(self, progress=0):
        """Stop watching - send stop scrobble"""
        if not self.trakt.is_authorized() or not self.current_item:
            return
        
        self.is_playing = False
        
        try:
            data = self._build_scrobble_data(
                self.current_item['type'], 
                self.current_item['ids'], 
                progress
            )
            self.trakt._request('/scrobble/stop', data, method='POST')
            xbmc.log(f"Trakt: Stopped scrobbling at {progress}%", xbmc.LOGINFO)
            
            # Auto-mark as watched if progress > 80%
            if progress >= 80:
                self.trakt.mark_watched(
                    self.current_item['type'], 
                    self.current_item['ids']
                )
        except Exception as e:
            xbmc.log(f"Trakt scrobble stop error: {e}", xbmc.LOGWARNING)
        
        self.current_item = None
    
    def _build_scrobble_data(self, media_type, ids, progress):
        """Build scrobble request data"""
        if media_type == 'movie':
            return {
                'movie': {'ids': ids},
                'progress': progress
            }
        else:
            return {
                'episode': {'ids': ids},
                'progress': progress
            }


class TraktAPI:
    """Trakt.tv API Integration"""
    
    BASE_URL = "https://api.trakt.tv"
    # User's Trakt API credentials
    CLIENT_ID = "548931ffe1f7bfc9b5586436226857bd099f55e0a419c821e7ab729a6d0005f8"
    CLIENT_SECRET = "6fd2939fcf6e95006de5c340206d3d3227bdff5474d22de80ea89e17c2636c87"
    
    def __init__(self):
        self.token = ADDON.getSetting('trakt_token')
        self.refresh_token = ADDON.getSetting('trakt_refresh')
    
    def _headers(self, auth=True):
        """Get API headers"""
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.CLIENT_ID,
            'User-Agent': 'Orion/2.0'
        }
        if auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    def _request(self, endpoint, data=None, method='GET', auth=True):
        """Make API request"""
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._headers(auth)
        
        if data:
            data = json.dumps(data).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Try to refresh token
                if self.refresh_token and self._refresh_token():
                    return self._request(endpoint, data, method, auth)
            try:
                return json.loads(e.read().decode('utf-8'))
            except:
                return {'error': str(e)}
        except Exception as e:
            return {'error': str(e)}
    
    def pair(self):
        """Start device pairing"""
        try:
            # Get device code
            device_data = {'client_id': self.CLIENT_ID}
            
            url = f"{self.BASE_URL}/oauth/device/code"
            headers = self._headers(auth=False)
            req = urllib.request.Request(
                url, 
                data=json.dumps(device_data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            device_code = data['device_code']
            user_code = data['user_code']
            verification_url = data.get('verification_url', 'https://trakt.tv/activate')
            expires_in = data.get('expires_in', 600)
            interval = data.get('interval', 5)
            
            # Show progress dialog
            progress = xbmcgui.DialogProgress()
            progress.create(
                'Trakt Authorization',
                f'Visit: [COLOR cyan]{verification_url}[/COLOR]\n'
                f'Enter Code: [COLOR yellow]{user_code}[/COLOR]\n'
                'Waiting for authorization...'
            )
            
            start_time = time.time()
            while not progress.iscanceled():
                elapsed = time.time() - start_time
                if elapsed > expires_in:
                    progress.close()
                    xbmcgui.Dialog().ok('Trakt', 'Authorization timed out')
                    return False
                
                progress.update(int((elapsed / expires_in) * 100))
                
                time.sleep(interval)
                
                # Poll for token
                token_data = {
                    'code': device_code,
                    'client_id': self.CLIENT_ID,
                    'client_secret': self.CLIENT_SECRET
                }
                
                try:
                    token_url = f"{self.BASE_URL}/oauth/device/token"
                    token_req = urllib.request.Request(
                        token_url,
                        data=json.dumps(token_data).encode('utf-8'),
                        headers=self._headers(auth=False),
                        method='POST'
                    )
                    
                    with urllib.request.urlopen(token_req, context=SSL_CONTEXT, timeout=10) as token_response:
                        result = json.loads(token_response.read().decode('utf-8'))
                        
                        if 'access_token' in result:
                            ADDON.setSetting('trakt_token', result['access_token'])
                            ADDON.setSetting('trakt_refresh', result.get('refresh_token', ''))
                            self.token = result['access_token']
                            self.refresh_token = result.get('refresh_token', '')
                            
                            progress.close()
                            xbmcgui.Dialog().ok('Trakt', '[COLOR lime]Successfully authorized![/COLOR]')
                            return True
                except urllib.error.HTTPError as e:
                    # 400 means user hasn't authorized yet, keep polling
                    if e.code != 400:
                        raise
            
            progress.close()
            return False
            
        except Exception as e:
            xbmcgui.Dialog().ok('Trakt Error', str(e))
            return False
    
    def _refresh_token(self):
        """Refresh access token"""
        try:
            token_data = {
                'refresh_token': self.refresh_token,
                'client_id': self.CLIENT_ID,
                'client_secret': self.CLIENT_SECRET,
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'grant_type': 'refresh_token'
            }
            
            url = f"{self.BASE_URL}/oauth/token"
            req = urllib.request.Request(
                url,
                data=json.dumps(token_data).encode('utf-8'),
                headers=self._headers(auth=False),
                method='POST'
            )
            
            with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if 'access_token' in result:
                    ADDON.setSetting('trakt_token', result['access_token'])
                    ADDON.setSetting('trakt_refresh', result.get('refresh_token', ''))
                    self.token = result['access_token']
                    self.refresh_token = result.get('refresh_token', '')
                    return True
            
            return False
        except:
            return False
    
    def is_authorized(self):
        """Check if authorized"""
        return bool(self.token)
    
    def get_list(self, list_type, media_type):
        """Get Trakt list"""
        if list_type == 'watchlist':
            endpoint = f"/users/me/watchlist/{media_type}"
        elif list_type == 'trending':
            endpoint = f"/{media_type}/trending"
        elif list_type == 'popular':
            endpoint = f"/{media_type}/popular"
        elif list_type == 'watched':
            endpoint = f"/users/me/watched/{media_type}"
        elif list_type == 'collected':
            endpoint = f"/users/me/collection/{media_type}"
        else:
            endpoint = f"/{media_type}/trending"
        
        auth_required = list_type in ['watchlist', 'watched', 'collected']
        data = self._request(endpoint, auth=auth_required)
        
        if isinstance(data, list):
            return data
        return []
    
    def add_to_watchlist(self, media_type, ids):
        """Add item to watchlist"""
        key = 'movies' if media_type == 'movie' else 'shows'
        data = {key: [{'ids': ids}]}
        return self._request('/sync/watchlist', data, method='POST')
    
    def remove_from_watchlist(self, media_type, ids):
        """Remove item from watchlist"""
        key = 'movies' if media_type == 'movie' else 'shows'
        data = {key: [{'ids': ids}]}
        return self._request('/sync/watchlist/remove', data, method='POST')
    
    def mark_watched(self, media_type, ids):
        """Mark item as watched"""
        key = 'movies' if media_type == 'movie' else 'episodes'
        data = {key: [{'ids': ids}]}
        return self._request('/sync/history', data, method='POST')
    
    def get_liked_lists(self, page=1, limit=20):
        """Get user's liked lists"""
        endpoint = f"/users/likes/lists?page={page}&limit={limit}"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []
    
    def get_user_lists(self, page=1):
        """Get user's custom lists"""
        endpoint = f"/users/me/lists"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []
    
    def get_list_items(self, username, list_id, page=1, limit=50):
        """Get items from a specific list"""
        endpoint = f"/users/{username}/lists/{list_id}/items?page={page}&limit={limit}"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []
    
    def get_watchlist_movies(self, page=1):
        """Get movies watchlist with pagination"""
        endpoint = f"/users/me/watchlist/movies?page={page}&limit=20"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []
    
    def get_watchlist_shows(self, page=1):
        """Get shows watchlist with pagination"""
        endpoint = f"/users/me/watchlist/shows?page={page}&limit=20"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []
    
    def get_collection_movies(self, page=1):
        """Get collected movies"""
        endpoint = f"/users/me/collection/movies"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []
    
    def get_collection_shows(self, page=1):
        """Get collected shows"""
        endpoint = f"/users/me/collection/shows"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []
    
    def get_watched_movies(self):
        """Get watched movies history"""
        endpoint = "/users/me/watched/movies"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []
    
    def get_watched_shows(self):
        """Get watched shows history"""
        endpoint = "/users/me/watched/shows"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []
    
    def get_recommendations_movies(self, page=1):
        """Get movie recommendations"""
        endpoint = f"/recommendations/movies?page={page}&limit=20"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []
    
    def get_recommendations_shows(self, page=1):
        """Get show recommendations"""
        endpoint = f"/recommendations/shows?page={page}&limit=20"
        data = self._request(endpoint, auth=True)
        if isinstance(data, list):
            return data
        return []