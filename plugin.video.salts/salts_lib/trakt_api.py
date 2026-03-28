"""
SALTS Library - Trakt.tv API Integration (API v2)
Modernized by zeus768 for Kodi 21+
Uses native urllib (no external requests module)
"""
import json
import time
import xbmc
import xbmcgui
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus

from . import log_utils
from .db_utils import DB_Connection

ADDON = xbmcaddon.Addon()

# Trakt API v2 settings
CLIENT_ID = '527628bac6bf261a98c20d218dda4541c3fd5c6c2586bded94c2ea802e32faf3'
CLIENT_SECRET = '5e51354a2e4e8d4f8e3f6d2e1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b'
API_URL = 'https://api.trakt.tv'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

class TraktError(Exception):
    pass

class TransientTraktError(Exception):
    pass

class TraktAPI:
    """Trakt.tv API v2 integration"""
    
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.access_token = ADDON.getSetting('trakt_access_token')
        self.refresh_token = ADDON.getSetting('trakt_refresh_token')
        self.expires = float(ADDON.getSetting('trakt_expires') or 0)
        self.db = DB_Connection()
        
        self.headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id
        }
    
    def is_authorized(self):
        """Check if we have valid authorization"""
        if not self.access_token:
            return False
        
        # Check if token needs refresh (1 hour buffer)
        if time.time() > self.expires - 3600:
            return self._refresh_token()
        
        return True
    
    def _http_request(self, url, method='GET', data=None, headers=None, timeout=30):
        """Make HTTP request using urllib, returns (status_code, response_body)"""
        hdrs = headers or {}
        post_data = None
        if data is not None:
            post_data = json.dumps(data).encode('utf-8')
        
        req = Request(url, data=post_data, headers=hdrs, method=method)
        
        try:
            response = urlopen(req, timeout=timeout)
            body = response.read().decode('utf-8')
            return response.getcode(), body
        except HTTPError as e:
            body = ''
            try:
                body = e.read().decode('utf-8')
            except Exception:
                pass
            return e.code, body
        except URLError as e:
            raise TransientTraktError(f'Trakt connection error: {e.reason}')
    
    def _refresh_token(self):
        """Refresh the access token"""
        if not self.refresh_token:
            return False
        
        try:
            data = {
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': REDIRECT_URI,
                'grant_type': 'refresh_token'
            }
            
            status, body = self._http_request(
                f'{API_URL}/oauth/token',
                method='POST',
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            if status == 200:
                result = json.loads(body)
                self._save_tokens(result)
                return True
            
        except Exception as e:
            log_utils.log_error(f'Trakt refresh error: {e}')
        
        return False
    
    def _save_tokens(self, data):
        """Save OAuth tokens"""
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.expires = time.time() + data['expires_in']
        
        ADDON.setSetting('trakt_access_token', self.access_token)
        ADDON.setSetting('trakt_refresh_token', self.refresh_token)
        ADDON.setSetting('trakt_expires', str(self.expires))
    
    def authorize(self):
        """OAuth device authorization flow"""
        try:
            # Get device code
            data = {'client_id': self.client_id}
            status, body = self._http_request(
                f'{API_URL}/oauth/device/code',
                method='POST',
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            if status != 200:
                raise TraktError('Failed to get device code')
            
            result = json.loads(body)
            
            device_code = result['device_code']
            user_code = result['user_code']
            verification_url = result['verification_url']
            interval = result['interval']
            expires_in = result['expires_in']
            
            # Show dialog
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                'Trakt Authorization',
                f'Go to: {verification_url}\n\nEnter code: {user_code}\n\nWaiting for authorization...'
            )
            
            # Poll for authorization
            start_time = time.time()
            while time.time() - start_time < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                time.sleep(interval)
                
                try:
                    token_data = {
                        'code': device_code,
                        'client_id': self.client_id,
                        'client_secret': self.client_secret
                    }
                    
                    token_status, token_body = self._http_request(
                        f'{API_URL}/oauth/device/token',
                        method='POST',
                        data=token_data,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if token_status == 200:
                        self._save_tokens(json.loads(token_body))
                        ADDON.setSetting('trakt_enabled', 'true')
                        
                        dialog.close()
                        xbmcgui.Dialog().notification('Trakt', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO)
                        return True
                    elif token_status != 400:
                        # 400 means pending, anything else is an error
                        break
                        
                except Exception as e:
                    log_utils.log_error(f'Trakt poll error: {e}')
            
            dialog.close()
            xbmcgui.Dialog().notification('Trakt', 'Authorization timeout', xbmcgui.NOTIFICATION_ERROR)
            return False
            
        except Exception as e:
            log_utils.log_error(f'Trakt auth error: {e}')
            xbmcgui.Dialog().notification('Trakt', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
            return False
    
    def _call_api(self, endpoint, method='GET', data=None, cache_limit=1):
        """Make API call to Trakt"""
        url = f'{API_URL}{endpoint}'
        
        # Check cache for GET requests
        if method == 'GET' and cache_limit > 0:
            _, cached = self.db.get_cached_url(url, cache_limit)
            if cached:
                return json.loads(cached)
        
        headers = self.headers.copy()
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        try:
            status, body = self._http_request(url, method=method, data=data, headers=headers)
            
            if status == 401:
                # Token expired, try to refresh
                if self._refresh_token():
                    return self._call_api(endpoint, method, data, cache_limit)
                raise TraktError('Authorization failed')
            
            if status == 404:
                return None
            
            if status >= 500:
                raise TransientTraktError(f'Trakt server error: {status}')
            
            if status >= 400:
                raise TraktError(f'Trakt API error: {status}')
            
            result = json.loads(body) if body else {}
            
            # Cache GET responses
            if method == 'GET' and cache_limit > 0:
                self.db.cache_url(url, json.dumps(result))
            
            return result
            
        except TransientTraktError:
            raise
        except TraktError:
            raise
        except Exception as e:
            raise TraktError(f'Trakt request error: {e}')
    
    # ==================== User Methods ====================
    
    def get_user_settings(self):
        """Get user settings/profile"""
        return self._call_api('/users/settings')
    
    def get_watchlist(self, media_type='movies'):
        """Get user's watchlist"""
        endpoint = f'/users/me/watchlist/{media_type}'
        return self._call_api(endpoint, cache_limit=0)
    
    def add_to_watchlist(self, media_type, items):
        """Add items to watchlist"""
        data = {media_type: items if isinstance(items, list) else [items]}
        return self._call_api('/sync/watchlist', method='POST', data=data)
    
    def remove_from_watchlist(self, media_type, items):
        """Remove items from watchlist"""
        data = {media_type: items if isinstance(items, list) else [items]}
        return self._call_api('/sync/watchlist/remove', method='POST', data=data)
    
    def get_collection(self, media_type='movies'):
        """Get user's collection"""
        endpoint = f'/users/me/collection/{media_type}'
        return self._call_api(endpoint, cache_limit=0)
    
    def add_to_collection(self, media_type, items):
        """Add items to collection"""
        data = {media_type: items if isinstance(items, list) else [items]}
        return self._call_api('/sync/collection', method='POST', data=data)
    
    def remove_from_collection(self, media_type, items):
        """Remove items from collection"""
        data = {media_type: items if isinstance(items, list) else [items]}
        return self._call_api('/sync/collection/remove', method='POST', data=data)
    
    def get_watched(self, media_type='movies'):
        """Get user's watched history"""
        endpoint = f'/users/me/watched/{media_type}'
        return self._call_api(endpoint, cache_limit=0)
    
    def mark_watched(self, media_type, items):
        """Mark items as watched"""
        data = {media_type: items if isinstance(items, list) else [items]}
        return self._call_api('/sync/history', method='POST', data=data)
    
    def mark_unwatched(self, media_type, items):
        """Remove items from watched history"""
        data = {media_type: items if isinstance(items, list) else [items]}
        return self._call_api('/sync/history/remove', method='POST', data=data)
    
    # ==================== Lists ====================
    
    def get_lists(self):
        """Get user's custom lists"""
        return self._call_api('/users/me/lists', cache_limit=0)
    
    def get_list(self, list_id):
        """Get items in a list"""
        return self._call_api(f'/users/me/lists/{list_id}/items', cache_limit=0)
    
    def add_to_list(self, list_id, items):
        """Add items to a list"""
        return self._call_api(f'/users/me/lists/{list_id}/items', method='POST', data=items)
    
    def remove_from_list(self, list_id, items):
        """Remove items from a list"""
        return self._call_api(f'/users/me/lists/{list_id}/items/remove', method='POST', data=items)
    
    # ==================== Discovery ====================
    
    def get_trending(self, media_type='movies', page=1, limit=20):
        """Get trending movies/shows"""
        endpoint = f'/{media_type}/trending?page={page}&limit={limit}'
        return self._call_api(endpoint)
    
    def get_popular(self, media_type='movies', page=1, limit=20):
        """Get popular movies/shows"""
        endpoint = f'/{media_type}/popular?page={page}&limit={limit}'
        return self._call_api(endpoint)
    
    def get_recommended(self, media_type='movies', page=1, limit=20):
        """Get recommended movies/shows (requires auth)"""
        if not self.is_authorized():
            return []
        endpoint = f'/recommendations/{media_type}?page={page}&limit={limit}'
        return self._call_api(endpoint)
    
    def get_anticipated(self, media_type='movies', page=1, limit=20):
        """Get anticipated movies/shows"""
        endpoint = f'/{media_type}/anticipated?page={page}&limit={limit}'
        return self._call_api(endpoint)
    
    # ==================== Search ====================
    
    def search(self, query, media_type='movie', page=1, limit=20):
        """Search for movies/shows"""
        endpoint = f'/search/{media_type}?query={quote_plus(query)}&page={page}&limit={limit}'
        return self._call_api(endpoint)
    
    def search_by_id(self, id_type, media_id, media_type='movie'):
        """Search by external ID (imdb, tmdb, tvdb)"""
        endpoint = f'/search/{id_type}/{media_id}?type={media_type}'
        return self._call_api(endpoint)
    
    # ==================== Details ====================
    
    def get_movie(self, movie_id):
        """Get movie details"""
        endpoint = f'/movies/{movie_id}?extended=full'
        return self._call_api(endpoint)
    
    def get_show(self, show_id):
        """Get show details"""
        endpoint = f'/shows/{show_id}?extended=full'
        return self._call_api(endpoint)
    
    def get_seasons(self, show_id):
        """Get seasons for a show"""
        endpoint = f'/shows/{show_id}/seasons?extended=full'
        return self._call_api(endpoint)
    
    def get_episodes(self, show_id, season):
        """Get episodes for a season"""
        endpoint = f'/shows/{show_id}/seasons/{season}?extended=full'
        return self._call_api(endpoint)
    
    def get_episode(self, show_id, season, episode):
        """Get episode details"""
        endpoint = f'/shows/{show_id}/seasons/{season}/episodes/{episode}?extended=full'
        return self._call_api(endpoint)
    
    # ==================== Progress ====================
    
    def get_show_progress(self, show_id):
        """Get watched progress for a show"""
        if not self.is_authorized():
            return None
        endpoint = f'/shows/{show_id}/progress/watched'
        return self._call_api(endpoint, cache_limit=0)
    
    def get_playback_progress(self):
        """Get all playback progress (for resume)"""
        if not self.is_authorized():
            return []
        return self._call_api('/sync/playback', cache_limit=0)
    
    # ==================== Calendar ====================
    
    def get_calendar_shows(self, start_date=None, days=7):
        """Get TV show calendar"""
        if start_date:
            endpoint = f'/calendars/my/shows/{start_date}/{days}'
        else:
            endpoint = f'/calendars/my/shows/{days}'
        return self._call_api(endpoint) if self.is_authorized() else self._call_api(f'/calendars/all/shows/{days}')
    
    def get_calendar_movies(self, start_date=None, days=30):
        """Get movie calendar (releases)"""
        if start_date:
            endpoint = f'/calendars/my/movies/{start_date}/{days}'
        else:
            endpoint = f'/calendars/my/movies/{days}'
        return self._call_api(endpoint) if self.is_authorized() else self._call_api(f'/calendars/all/movies/{days}')
    
    # ==================== Ratings ====================
    
    def rate(self, media_type, media_id, rating):
        """Rate an item (1-10)"""
        data = {
            media_type: [{
                'ids': {'trakt': media_id} if isinstance(media_id, int) else {'slug': media_id},
                'rating': rating
            }]
        }
        return self._call_api('/sync/ratings', method='POST', data=data)
    
    def get_ratings(self, media_type='movies'):
        """Get user's ratings"""
        return self._call_api(f'/users/me/ratings/{media_type}', cache_limit=0)
    
    # ==================== Scrobble ====================
    
    def scrobble_start(self, media_type, media_id, progress=0):
        """Start scrobbling (playing)"""
        data = {
            media_type[:-1]: {'ids': {'trakt': media_id}},
            'progress': progress
        }
        return self._call_api('/scrobble/start', method='POST', data=data)
    
    def scrobble_pause(self, media_type, media_id, progress):
        """Pause scrobbling"""
        data = {
            media_type[:-1]: {'ids': {'trakt': media_id}},
            'progress': progress
        }
        return self._call_api('/scrobble/pause', method='POST', data=data)
    
    def scrobble_stop(self, media_type, media_id, progress):
        """Stop scrobbling"""
        data = {
            media_type[:-1]: {'ids': {'trakt': media_id}},
            'progress': progress
        }
        return self._call_api('/scrobble/stop', method='POST', data=data)
