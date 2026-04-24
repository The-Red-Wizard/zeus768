"""
SALTS Library - Trakt.tv API Integration (API v2)
Modernized by zeus768 for Kodi 21+
Uses native urllib (no external requests module)
"""
import json
import time
import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus, urlencode

from . import log_utils
from .db_utils import DB_Connection

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_DATA_PATH = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')

def _fresh_addon():
    """Always return a fresh Addon instance to avoid stale settings cache."""
    return xbmcaddon.Addon()

# Trakt API v2 settings
CLIENT_ID = '42eba69a18795ae48fc5d6dbdd99396e9e3894dc4f18930e6187d36c8b4346d3'
CLIENT_SECRET = 'e5bc7e20660e73622344ebf93c250a8fc2814a8f7c2b082bdee51545d5f71969'
API_URL = 'https://api.trakt.tv'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
USER_AGENT = 'SALTS Kodi Addon/2.5.2'

# Token file path
TOKEN_FILE = os.path.join(ADDON_DATA_PATH, 'trakt_auth.json')


class TraktError(Exception):
    pass


class TransientTraktError(Exception):
    pass


class TraktAPI:
    """Trakt.tv API v2 integration with device authentication"""
    
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.db = DB_Connection()
        
        # Load tokens from file first, then fall back to addon settings
        self._load_tokens()
        
        self.headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id,
            'User-Agent': USER_AGENT
        }
    
    def _ensure_data_path(self):
        """Ensure addon data directory exists"""
        if not xbmcvfs.exists(ADDON_DATA_PATH):
            xbmcvfs.mkdirs(ADDON_DATA_PATH)
    
    def _load_tokens(self):
        """Load OAuth tokens from file or addon settings"""
        self._ensure_data_path()
        
        # Try loading from file first (more reliable)
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    self.access_token = data.get('access_token', '')
                    self.refresh_token = data.get('refresh_token', '')
                    self.expires = float(data.get('expires', 0))
                    log_utils.log('Trakt: Loaded tokens from file', xbmc.LOGDEBUG)
                    return
            except Exception as e:
                log_utils.log(f'Trakt: Failed to load tokens from file: {e}', xbmc.LOGWARNING)
        
        # Fall back to addon settings (use fresh instance)
        addon = _fresh_addon()
        self.access_token = addon.getSetting('trakt_access_token')
        self.refresh_token = addon.getSetting('trakt_refresh_token')
        self.expires = float(addon.getSetting('trakt_expires') or 0)
    
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
        hdrs = self.headers.copy()
        if headers:
            hdrs.update(headers)
        
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
            log_utils.log(f'Trakt HTTP Error: {e.code} - {body}', xbmc.LOGWARNING)
            return e.code, body
        except URLError as e:
            log_utils.log(f'Trakt URL Error: {e.reason}', xbmc.LOGERROR)
            raise TransientTraktError(f'Trakt connection error: {e.reason}')
        except Exception as e:
            log_utils.log(f'Trakt Request Error: {e}', xbmc.LOGERROR)
            raise TransientTraktError(f'Trakt request failed: {e}')
    
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
                data=data
            )
            
            if status == 200:
                result = json.loads(body)
                self._save_tokens(result)
                log_utils.log('Trakt: Token refreshed successfully', xbmc.LOGINFO)
                return True
            else:
                log_utils.log(f'Trakt: Token refresh failed with status {status}', xbmc.LOGWARNING)
            
        except Exception as e:
            log_utils.log(f'Trakt refresh error: {e}', xbmc.LOGERROR)
        
        return False
    
    def _save_tokens(self, data):
        """Save OAuth tokens to file and addon settings"""
        self._ensure_data_path()
        
        self.access_token = data.get('access_token', '')
        self.refresh_token = data.get('refresh_token', '')
        expires_in = data.get('expires_in', 7776000)  # Default 90 days
        self.expires = time.time() + expires_in
        
        # Save to file (primary storage)
        token_data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires': self.expires,
            'created_at': time.time()
        }
        
        try:
            with open(TOKEN_FILE, 'w') as f:
                json.dump(token_data, f, indent=2)
            log_utils.log('Trakt: Tokens saved to file', xbmc.LOGDEBUG)
        except Exception as e:
            log_utils.log(f'Trakt: Failed to save tokens to file: {e}', xbmc.LOGWARNING)
        
        # Also save to addon settings (backup) - use fresh instance
        addon = _fresh_addon()
        addon.setSetting('trakt_access_token', self.access_token)
        addon.setSetting('trakt_refresh_token', self.refresh_token)
        addon.setSetting('trakt_expires', str(self.expires))
        addon.setSetting('trakt_enabled', 'true')
    
    def clear_authorization(self):
        """Clear all stored authorization data"""
        self.access_token = ''
        self.refresh_token = ''
        self.expires = 0
        
        # Clear file
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
            except Exception:
                pass
        
        # Clear addon settings (use fresh instance)
        addon = _fresh_addon()
        addon.setSetting('trakt_access_token', '')
        addon.setSetting('trakt_refresh_token', '')
        addon.setSetting('trakt_expires', '0')
        addon.setSetting('trakt_enabled', 'false')
    
    def authorize(self):
        """OAuth device authorization flow - get device code and poll for token"""
        try:
            # Step 1: Request device code
            log_utils.log('Trakt: Requesting device code...', xbmc.LOGINFO)
            
            data = {'client_id': self.client_id}
            
            status, body = self._http_request(
                f'{API_URL}/oauth/device/code',
                method='POST',
                data=data
            )
            
            log_utils.log(f'Trakt: Device code response - Status: {status}', xbmc.LOGDEBUG)
            
            if status != 200:
                error_msg = f'Failed to get device code (HTTP {status})'
                try:
                    error_data = json.loads(body)
                    error_msg = error_data.get('error_description', error_data.get('error', error_msg))
                except Exception:
                    pass
                log_utils.log(f'Trakt: {error_msg}', xbmc.LOGERROR)
                xbmcgui.Dialog().ok('Trakt Error', error_msg)
                return False
            
            result = json.loads(body)
            
            device_code = result.get('device_code')
            user_code = result.get('user_code')
            verification_url = result.get('verification_url', 'https://trakt.tv/activate')
            interval = result.get('interval', 5)
            expires_in = result.get('expires_in', 600)
            
            if not device_code or not user_code:
                log_utils.log('Trakt: Invalid device code response', xbmc.LOGERROR)
                xbmcgui.Dialog().ok('Trakt Error', 'Invalid response from Trakt. Please try again.')
                return False
            
            log_utils.log(f'Trakt: Got device code, user_code: {user_code}', xbmc.LOGINFO)
            
            # Step 2: Show dialog with instructions
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                'Trakt Authorization',
                f'Visit: {verification_url}\n\n'
                f'Enter Code: [B]{user_code}[/B]\n\n'
                'Waiting for authorization...'
            )
            
            # Step 3: Poll for token
            start_time = time.time()
            poll_count = 0
            
            while time.time() - start_time < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    log_utils.log('Trakt: Authorization cancelled by user', xbmc.LOGINFO)
                    return False
                
                # Update progress
                elapsed = time.time() - start_time
                remaining = expires_in - elapsed
                percent = int((elapsed / expires_in) * 100)
                dialog.update(
                    percent,
                    f'Visit: {verification_url}\n\n'
                    f'Enter Code: [B]{user_code}[/B]\n\n'
                    f'Time remaining: {int(remaining)} seconds'
                )
                
                # Wait for interval
                time.sleep(interval)
                poll_count += 1
                
                # Poll for token
                try:
                    token_data = {
                        'code': device_code,
                        'client_id': self.client_id,
                        'client_secret': self.client_secret
                    }
                    
                    token_status, token_body = self._http_request(
                        f'{API_URL}/oauth/device/token',
                        method='POST',
                        data=token_data
                    )
                    
                    log_utils.log(f'Trakt: Poll #{poll_count} - Status: {token_status}', xbmc.LOGDEBUG)
                    
                    if token_status == 200:
                        # Success! Save tokens
                        token_result = json.loads(token_body)
                        self._save_tokens(token_result)
                        
                        dialog.close()
                        
                        # Verify authorization
                        try:
                            user_info = self.get_user_settings()
                            username = user_info.get('user', {}).get('username', 'User')
                            xbmcgui.Dialog().ok(
                                'Trakt Authorization',
                                f'Success! Authorized as: {username}'
                            )
                        except Exception:
                            xbmcgui.Dialog().ok(
                                'Trakt Authorization',
                                'Authorization successful!'
                            )
                        
                        log_utils.log('Trakt: Authorization completed successfully', xbmc.LOGINFO)
                        return True
                    
                    elif token_status == 400:
                        # Still pending - continue polling
                        continue
                    
                    elif token_status == 404:
                        # Invalid device code
                        dialog.close()
                        log_utils.log('Trakt: Invalid device code', xbmc.LOGERROR)
                        xbmcgui.Dialog().ok('Trakt Error', 'Invalid device code. Please try again.')
                        return False
                    
                    elif token_status == 409:
                        # Code already used
                        dialog.close()
                        log_utils.log('Trakt: Device code already used', xbmc.LOGERROR)
                        xbmcgui.Dialog().ok('Trakt Error', 'This code has already been used. Please try again.')
                        return False
                    
                    elif token_status == 410:
                        # Code expired
                        dialog.close()
                        log_utils.log('Trakt: Device code expired', xbmc.LOGERROR)
                        xbmcgui.Dialog().ok('Trakt Error', 'Authorization code expired. Please try again.')
                        return False
                    
                    elif token_status == 418:
                        # User denied
                        dialog.close()
                        log_utils.log('Trakt: User denied authorization', xbmc.LOGINFO)
                        xbmcgui.Dialog().ok('Trakt', 'Authorization was denied.')
                        return False
                    
                    elif token_status == 429:
                        # Rate limited - increase interval
                        interval = min(interval + 1, 10)
                        log_utils.log(f'Trakt: Rate limited, increasing interval to {interval}s', xbmc.LOGWARNING)
                        continue
                    
                    else:
                        # Unknown error
                        log_utils.log(f'Trakt: Unexpected status {token_status}: {token_body}', xbmc.LOGWARNING)
                        continue
                        
                except TransientTraktError as e:
                    log_utils.log(f'Trakt: Network error during poll: {e}', xbmc.LOGWARNING)
                    continue
                except Exception as e:
                    log_utils.log(f'Trakt: Poll error: {e}', xbmc.LOGWARNING)
                    continue
            
            # Timeout
            dialog.close()
            log_utils.log('Trakt: Authorization timeout', xbmc.LOGWARNING)
            xbmcgui.Dialog().ok('Trakt', 'Authorization timeout. Please try again.')
            return False
            
        except TransientTraktError as e:
            log_utils.log(f'Trakt: Connection error during auth: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Trakt Error', f'Connection error: {e}')
            return False
        except Exception as e:
            log_utils.log(f'Trakt auth error: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Trakt Error', f'Authorization failed: {e}')
            return False
    
    def _call_api(self, endpoint, method='GET', data=None, cache_limit=1):
        """Make API call to Trakt"""
        url = f'{API_URL}{endpoint}'
        
        # Check cache for GET requests
        if method == 'GET' and cache_limit > 0:
            _, cached = self.db.get_cached_url(url, cache_limit)
            if cached:
                return json.loads(cached)
        
        headers = {}
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
    
    def get_item_rating(self, media_type, tmdb_id):
        """Get Trakt community rating for a movie/show by TMDB ID.
        Returns (rating, votes) tuple or (None, None).
        media_type: 'movie' or 'show'
        """
        try:
            lookup_type = 'movies' if media_type == 'movie' else 'shows'
            # Trakt search by TMDB ID
            results = self._call_api(f'/search/tmdb/{tmdb_id}?type={media_type}', cache_limit=24)
            if results and isinstance(results, list) and len(results) > 0:
                item = results[0].get(media_type, {})
                trakt_slug = item.get('ids', {}).get('slug')
                if trakt_slug:
                    rating_data = self._call_api(f'/{lookup_type}/{trakt_slug}/ratings', cache_limit=24)
                    if isinstance(rating_data, dict):
                        rating = rating_data.get('rating')
                        votes = rating_data.get('votes', 0)
                        if rating is not None:
                            return (round(rating, 1), votes)
        except Exception as e:
            log_utils.log(f'Trakt rating lookup error: {e}', xbmc.LOGWARNING)
        return (None, None)
    
    def get_batch_ratings(self, media_type, tmdb_ids):
        """Get Trakt ratings for multiple items by TMDB ID.
        Returns dict: {tmdb_id: (rating, votes)}
        media_type: 'movie' or 'show'
        """
        results = {}
        for tmdb_id in tmdb_ids:
            try:
                r, v = self.get_item_rating(media_type, tmdb_id)
                if r is not None:
                    results[str(tmdb_id)] = (r, v)
            except Exception:
                continue
        return results
    
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
