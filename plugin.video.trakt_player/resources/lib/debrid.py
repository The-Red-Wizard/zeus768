"""
Debrid Service Integration Module
Supports Real-Debrid, Premiumize, AllDebrid
Uses native urllib (no external requests module)
FIXED: Token persistence using file-based storage + cached torrent support
"""
import json
import time
import os
import xbmcgui
import xbmcaddon
import xbmc
import xbmcvfs

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# Get fresh addon instance each time for settings
def get_addon():
    return xbmcaddon.Addon()

ADDON_ID = 'plugin.video.trakt_player'
ADDON_DATA_PATH = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')
ADDON_PATH = xbmcvfs.translatePath(f'special://home/addons/{ADDON_ID}/')

# Quality priorities (highest to lowest)
QUALITY_ORDER = ['2160p', '1080p', '720p', '480p', '360p']
USER_AGENT = 'TraktPlayer Kodi Addon'

# Token files
RD_TOKEN_FILE = os.path.join(ADDON_DATA_PATH, 'rd_token.json')
AD_TOKEN_FILE = os.path.join(ADDON_DATA_PATH, 'ad_token.json')
PM_TOKEN_FILE = os.path.join(ADDON_DATA_PATH, 'pm_token.json')
TB_TOKEN_FILE = os.path.join(ADDON_DATA_PATH, 'tb_token.json')
LS_TOKEN_FILE = os.path.join(ADDON_DATA_PATH, 'ls_token.json')


def _ensure_data_path():
    """Ensure addon data directory exists"""
    if not xbmcvfs.exists(ADDON_DATA_PATH):
        xbmcvfs.mkdirs(ADDON_DATA_PATH)
    if not os.path.exists(ADDON_DATA_PATH):
        os.makedirs(ADDON_DATA_PATH, exist_ok=True)


def _http(url, method='GET', data=None, headers=None, timeout=30):
    """HTTP helper - returns (status_code, parsed_json_or_text)"""
    hdrs = {'User-Agent': USER_AGENT}
    if headers:
        hdrs.update(headers)
    
    post_data = None
    if data is not None:
        if isinstance(data, dict):
            post_data = urlencode(data).encode('utf-8')
            hdrs.setdefault('Content-Type', 'application/x-www-form-urlencoded')
        elif isinstance(data, str):
            post_data = data.encode('utf-8')
        elif isinstance(data, bytes):
            post_data = data
    
    try:
        req = Request(url, data=post_data, headers=hdrs, method=method)
        resp = urlopen(req, timeout=timeout)
        body = resp.read().decode('utf-8', errors='replace')
        try:
            return resp.getcode(), json.loads(body)
        except json.JSONDecodeError:
            return resp.getcode(), body
    except HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8')
        except Exception:
            pass
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body
    except URLError as e:
        xbmc.log(f'Debrid URL Error: {e.reason}', xbmc.LOGERROR)
        return 0, None
    except Exception as e:
        xbmc.log(f'Debrid HTTP error: {e}', xbmc.LOGERROR)
        return 0, None


def _get(url, params=None, headers=None, timeout=30):
    """HTTP GET helper"""
    if params:
        query = urlencode(params)
        sep = '&' if '?' in url else '?'
        url = f'{url}{sep}{query}'
    return _http(url, method='GET', headers=headers, timeout=timeout)


def _post(url, data=None, params=None, headers=None, timeout=30):
    """HTTP POST helper"""
    if params:
        query = urlencode(params)
        sep = '&' if '?' in url else '?'
        url = f'{url}{sep}{query}'
    return _http(url, method='POST', data=data, headers=headers, timeout=timeout)


class RealDebrid:
    """Real-Debrid API integration using device auth with file-based token storage"""
    
    BASE_URL = "https://api.real-debrid.com/rest/1.0"
    OAUTH_URL = "https://api.real-debrid.com/oauth/v2"
    DEVICE_URL = "https://real-debrid.com/device"
    CLIENT_ID = "X245A4XAIBGVM"  # Public client ID for device auth
    
    def __init__(self):
        self._load_from_file()
    
    def _load_from_file(self):
        """Load tokens from file"""
        _ensure_data_path()
        
        self.token = ''
        self.refresh_token = ''
        self.client_id = self.CLIENT_ID
        self.client_secret = ''
        self.expires = 0
        
        if os.path.exists(RD_TOKEN_FILE):
            try:
                with open(RD_TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    self.token = data.get('access_token', '')
                    self.refresh_token = data.get('refresh_token', '')
                    self.client_id = data.get('client_id', self.CLIENT_ID)
                    self.client_secret = data.get('client_secret', '')
                    self.expires = float(data.get('expires', 0))
                    if self.token:
                        xbmc.log('Real-Debrid: Loaded tokens from file', xbmc.LOGDEBUG)
            except Exception as e:
                xbmc.log(f'Real-Debrid: Failed to load from file: {e}', xbmc.LOGWARNING)
        
        # Fallback to addon settings
        if not self.token:
            addon = get_addon()
            self.token = addon.getSetting('rd_access_token')
            self.refresh_token = addon.getSetting('rd_refresh_token')
            self.client_id = addon.getSetting('rd_client_id') or self.CLIENT_ID
            self.client_secret = addon.getSetting('rd_client_secret') or ''
            try:
                self.expires = float(addon.getSetting('rd_expires') or 0)
            except:
                self.expires = 0
    
    def _save_to_file(self):
        """Save tokens to file"""
        _ensure_data_path()
        
        data = {
            'access_token': self.token,
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'expires': self.expires,
            'created_at': time.time()
        }
        
        try:
            with open(RD_TOKEN_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            xbmc.log('Real-Debrid: Tokens saved to file', xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f'Real-Debrid: Failed to save to file: {e}', xbmc.LOGERROR)
        
        # Also save to addon settings as backup
        try:
            addon = get_addon()
            addon.setSetting('rd_access_token', self.token)
            addon.setSetting('rd_refresh_token', self.refresh_token)
            addon.setSetting('rd_client_id', self.client_id)
            addon.setSetting('rd_client_secret', self.client_secret)
            addon.setSetting('rd_expires', str(self.expires))
            addon.setSetting('rd_auth_done', 'true')
        except Exception as e:
            xbmc.log(f'Real-Debrid: Failed to save to addon settings: {e}', xbmc.LOGWARNING)
    
    def _auth_headers(self):
        return {'Authorization': f'Bearer {self.token}'}
    
    def is_authorized(self):
        """Check if Real-Debrid is authorized"""
        if not self.token:
            xbmc.log('Real-Debrid: No token found', xbmc.LOGDEBUG)
            return False
        
        # Check if token needs refresh (10 min buffer)
        if self.expires and time.time() > self.expires - 600:
            xbmc.log('Real-Debrid: Token near expiry, refreshing...', xbmc.LOGINFO)
            refreshed = self._refresh_token()
            if not refreshed:
                # Token refresh failed, but token might still work
                # Try a quick API call to verify
                xbmc.log('Real-Debrid: Refresh failed, testing current token...', xbmc.LOGINFO)
                try:
                    status, result = _get(
                        f"{self.BASE_URL}/user",
                        headers=self._auth_headers()
                    )
                    if status == 200:
                        xbmc.log('Real-Debrid: Token still valid despite refresh failure', xbmc.LOGINFO)
                        return True
                except:
                    pass
                xbmc.log('Real-Debrid: Token expired and refresh failed', xbmc.LOGWARNING)
                return False
            return True
        
        xbmc.log('Real-Debrid: Authorization valid', xbmc.LOGDEBUG)
        return True
    
    def _refresh_token(self):
        """Refresh the access token"""
        if not self.refresh_token or not self.client_secret:
            return False
        
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': self.refresh_token,
                'grant_type': 'http://oauth.net/grant_type/device/1.0'
            }
            
            status, result = _post(f'{self.OAUTH_URL}/token', data=data)
            
            if status == 200 and isinstance(result, dict) and 'access_token' in result:
                self.token = result['access_token']
                self.refresh_token = result.get('refresh_token', self.refresh_token)
                self.expires = time.time() + result.get('expires_in', 86400)
                
                self._save_to_file()
                xbmc.log('Real-Debrid: Token refreshed successfully', xbmc.LOGINFO)
                return True
        except Exception as e:
            xbmc.log(f'Real-Debrid refresh error: {e}', xbmc.LOGERROR)
        
        return False
    
    def authorize(self):
        """Device code authorization flow"""
        try:
            # Step 1: Get device code
            xbmc.log('Real-Debrid: Requesting device code...', xbmc.LOGINFO)
            
            status, result = _get(
                f"{self.OAUTH_URL}/device/code",
                params={"client_id": self.CLIENT_ID, "new_credentials": "yes"}
            )
            
            if status != 200 or not isinstance(result, dict):
                xbmc.log(f'Real-Debrid: Failed to get device code - Status: {status}', xbmc.LOGERROR)
                xbmcgui.Dialog().notification('Error', 'Failed to get device code', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            device_code = result.get('device_code')
            user_code = result.get('user_code')
            verification_url = result.get('verification_url', self.DEVICE_URL)
            expires_in = result.get('expires_in', 600)
            interval = result.get('interval', 5)
            
            if not device_code or not user_code:
                xbmcgui.Dialog().notification('Error', 'Invalid response from Real-Debrid', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            xbmc.log(f'Real-Debrid: Got device code, user_code: {user_code}', xbmc.LOGINFO)
            
            # Step 2: Show dialog
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                "Real-Debrid Authorization",
                f"Go to: [B][COLOR skyblue]{verification_url}[/COLOR][/B]\n\n"
                f"Enter Code: [B][COLOR yellow]{user_code}[/COLOR][/B]\n\n"
                f"Waiting for authorization..."
            )
            
            # Step 3: Poll for credentials
            start = time.time()
            while time.time() - start < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                elapsed = time.time() - start
                remaining = expires_in - elapsed
                progress = int((elapsed / expires_in) * 100)
                dialog.update(
                    progress,
                    f"Go to: [B][COLOR skyblue]{verification_url}[/COLOR][/B]\n\n"
                    f"Enter Code: [B][COLOR yellow]{user_code}[/COLOR][/B]\n\n"
                    f"Time remaining: {int(remaining)} seconds"
                )
                
                time.sleep(interval)
                
                # Check credentials
                check_status, check_result = _get(
                    f"{self.OAUTH_URL}/device/credentials",
                    params={"client_id": self.CLIENT_ID, "code": device_code}
                )
                
                if check_status == 200 and isinstance(check_result, dict) and 'client_id' in check_result:
                    # Got credentials, now get access token
                    client_id = check_result.get('client_id')
                    client_secret = check_result.get('client_secret')
                    
                    token_data = {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": device_code,
                        "grant_type": "http://oauth.net/grant_type/device/1.0"
                    }
                    
                    tok_status, tok_result = _post(f"{self.OAUTH_URL}/token", data=token_data)
                    
                    if tok_status == 200 and isinstance(tok_result, dict) and 'access_token' in tok_result:
                        self.token = tok_result.get('access_token', '')
                        self.refresh_token = tok_result.get('refresh_token', '')
                        self.client_id = client_id
                        self.client_secret = client_secret
                        self.expires = time.time() + tok_result.get('expires_in', 86400)
                        
                        self._save_to_file()
                        
                        dialog.close()
                        xbmcgui.Dialog().notification("Success!", "Real-Debrid linked!", xbmcgui.NOTIFICATION_INFO)
                        xbmc.log('Real-Debrid: Authorization successful', xbmc.LOGINFO)
                        return True
            
            dialog.close()
            xbmcgui.Dialog().notification('Timeout', 'Authorization timed out', xbmcgui.NOTIFICATION_WARNING)
            return False
            
        except Exception as e:
            xbmc.log(f"RD auth error: {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Error', f'Auth failed: {str(e)}', xbmcgui.NOTIFICATION_ERROR)
            return False
    
    def check_cache(self, hashes):
        """Check if torrents are cached on Real-Debrid
        Args:
            hashes: List of torrent info hashes
        Returns:
            Dict of cached hashes with their info
        """
        if not self.is_authorized() or not hashes:
            return {}
        
        try:
            # RD accepts multiple hashes separated by /
            hash_str = '/'.join(hashes[:100])  # Limit to 100
            status, result = _get(
                f"{self.BASE_URL}/torrents/instantAvailability/{hash_str}",
                headers=self._auth_headers()
            )
            
            if status == 200 and isinstance(result, dict):
                cached = {}
                for hash_key, value in result.items():
                    if value and isinstance(value, dict):
                        rd_data = value.get('rd', [])
                        if rd_data:
                            cached[hash_key.lower()] = rd_data
                return cached
        except Exception as e:
            xbmc.log(f'RD cache check error: {e}', xbmc.LOGERROR)
        
        return {}
    
    def unrestrict_link(self, link):
        """Convert link to direct stream URL"""
        if not self.is_authorized():
            return None
        try:
            status, result = _post(
                f"{self.BASE_URL}/unrestrict/link",
                data={"link": link},
                headers=self._auth_headers()
            )
            if isinstance(result, dict):
                return result.get('download')
        except Exception as e:
            xbmc.log(f'RD unrestrict error: {e}', xbmc.LOGERROR)
        return None
    
    def add_magnet(self, magnet, check_cache_first=True):
        """Add magnet link and get download link
        Args:
            magnet: Magnet URI or info hash
            check_cache_first: If True, check if torrent is cached first
        """
        if not self.is_authorized():
            return None
        
        try:
            # Extract hash from magnet
            import re
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
            if not hash_match:
                hash_match = re.search(r'btih:([a-fA-F0-9]{32})', magnet)
            
            info_hash = hash_match.group(1).lower() if hash_match else None
            
            # Check cache first for instant availability
            if check_cache_first and info_hash:
                cached = self.check_cache([info_hash])
                if info_hash in cached:
                    xbmc.log(f'Real-Debrid: Torrent is cached! Using instant availability.', xbmc.LOGINFO)
            
            # Add magnet
            status, result = _post(
                f"{self.BASE_URL}/torrents/addMagnet",
                data={"magnet": magnet},
                headers=self._auth_headers()
            )
            
            if not isinstance(result, dict) or 'id' not in result:
                xbmc.log(f'RD addMagnet failed: {result}', xbmc.LOGERROR)
                return None
            
            torrent_id = result.get('id')
            
            # Select all files
            _post(
                f"{self.BASE_URL}/torrents/selectFiles/{torrent_id}",
                data={"files": "all"},
                headers=self._auth_headers()
            )
            
            # Wait for ready and get links (reduced wait time for cached)
            max_attempts = 30
            for attempt in range(max_attempts):
                _, info = _get(
                    f"{self.BASE_URL}/torrents/info/{torrent_id}",
                    headers=self._auth_headers()
                )
                
                if isinstance(info, dict):
                    status = info.get('status', '')
                    
                    if status == 'downloaded':
                        links = info.get('links', [])
                        if links:
                            # Get the largest file (usually the video)
                            return self.unrestrict_link(links[0])
                    
                    elif status in ['error', 'dead', 'virus']:
                        xbmc.log(f'RD torrent status: {status}', xbmc.LOGERROR)
                        return None
                    
                    elif status == 'waiting_files_selection':
                        # Re-select files
                        _post(
                            f"{self.BASE_URL}/torrents/selectFiles/{torrent_id}",
                            data={"files": "all"},
                            headers=self._auth_headers()
                        )
                
                time.sleep(2)
            
            xbmc.log('RD: Timeout waiting for torrent', xbmc.LOGWARNING)
            return None
            
        except Exception as e:
            xbmc.log(f'RD magnet error: {e}', xbmc.LOGERROR)
            return None
    
    def revoke(self):
        """Clear all Real-Debrid tokens"""
        # Clear file
        if os.path.exists(RD_TOKEN_FILE):
            try:
                os.remove(RD_TOKEN_FILE)
            except:
                pass
        
        # Clear addon settings
        try:
            addon = get_addon()
            addon.setSetting('rd_access_token', '')
            addon.setSetting('rd_refresh_token', '')
            addon.setSetting('rd_client_id', '')
            addon.setSetting('rd_client_secret', '')
            addon.setSetting('rd_expires', '0')
            addon.setSetting('rd_auth_done', 'false')
        except:
            pass
        
        self.token = ''
        self.refresh_token = ''
        xbmcgui.Dialog().notification("Real-Debrid", "Account unlinked", xbmcgui.NOTIFICATION_INFO)

    def account_info(self):
        """Get Real-Debrid account info (username, type, expiry, points)"""
        if not self.token:
            return {}
        try:
            status, result = _get(
                f"{self.BASE_URL}/user",
                headers=self._auth_headers()
            )
            if status == 200 and isinstance(result, dict):
                expiration = result.get('expiration', '')
                days_left = 0
                if expiration:
                    try:
                        from datetime import datetime
                        exp_date = datetime.strptime(expiration, '%Y-%m-%dT%H:%M:%S.%fZ')
                        delta = exp_date - datetime.utcnow()
                        days_left = max(0, delta.days)
                    except Exception:
                        try:
                            from datetime import datetime
                            exp_date = datetime.strptime(expiration[:19], '%Y-%m-%dT%H:%M:%S')
                            delta = exp_date - datetime.utcnow()
                            days_left = max(0, delta.days)
                        except:
                            pass

                return {
                    'username': result.get('username', ''),
                    'email': result.get('email', ''),
                    'type': result.get('type', 'free'),
                    'premium': result.get('type', '') == 'premium',
                    'expiration': expiration,
                    'days_left': days_left,
                    'points': result.get('points', 0),
                }
            elif status == 401:
                # Token invalid, try refresh
                if self._refresh_token():
                    return self.account_info()
                return {'type': 'expired', 'premium': False, 'days_left': 0,
                        'expiration': 'Token expired - re-authorize'}
        except Exception as e:
            xbmc.log(f'RD account_info error: {e}', xbmc.LOGERROR)
        return {}


class AllDebrid:
    """AllDebrid API integration with file-based token storage"""
    
    BASE_URL = "https://api.alldebrid.com/v4"
    DEVICE_URL = "https://alldebrid.com/pin/"
    AGENT = "TraktPlayer"
    
    def __init__(self):
        self._load_from_file()
    
    def _load_from_file(self):
        """Load token from file"""
        _ensure_data_path()
        self.token = ''
        
        if os.path.exists(AD_TOKEN_FILE):
            try:
                with open(AD_TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    self.token = data.get('api_key', '')
                    if self.token:
                        xbmc.log('AllDebrid: Loaded token from file', xbmc.LOGDEBUG)
            except:
                pass
        
        if not self.token:
            self.token = get_addon().getSetting('ad_api_key')
    
    def _save_to_file(self):
        """Save token to file"""
        _ensure_data_path()
        try:
            with open(AD_TOKEN_FILE, 'w') as f:
                json.dump({'api_key': self.token, 'created_at': time.time()}, f)
            addon = get_addon()
            addon.setSetting('ad_api_key', self.token)
            addon.setSetting('ad_auth_done', 'true')
        except:
            pass
    
    def is_authorized(self):
        return bool(self.token)
    
    def authorize(self):
        """PIN-based authorization"""
        try:
            xbmc.log('AllDebrid: Requesting PIN...', xbmc.LOGINFO)
            
            status, result = _get(
                f"{self.BASE_URL}/pin/get",
                params={"agent": self.AGENT}
            )
            
            if not isinstance(result, dict) or result.get('status') != 'success':
                xbmc.log(f'AllDebrid: Failed to get PIN - {result}', xbmc.LOGERROR)
                xbmcgui.Dialog().notification('Error', 'Failed to get PIN', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            data = result.get('data', {})
            pin = data.get('pin')
            check_url = data.get('check_url')
            user_url = data.get('user_url', self.DEVICE_URL)
            expires_in = data.get('expires_in', 600)
            
            if not pin:
                xbmcgui.Dialog().notification('Error', 'Invalid PIN response', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            xbmc.log(f'AllDebrid: Got PIN: {pin}', xbmc.LOGINFO)
            
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                "AllDebrid Authorization",
                f"Go to: [B][COLOR skyblue]{user_url}[/COLOR][/B]\n\n"
                f"Enter PIN: [B][COLOR yellow]{pin}[/COLOR][/B]\n\n"
                f"Waiting for authorization..."
            )
            
            start = time.time()
            while time.time() - start < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                elapsed = time.time() - start
                remaining = expires_in - elapsed
                progress = int((elapsed / expires_in) * 100)
                dialog.update(
                    progress,
                    f"Go to: [B][COLOR skyblue]{user_url}[/COLOR][/B]\n\n"
                    f"Enter PIN: [B][COLOR yellow]{pin}[/COLOR][/B]\n\n"
                    f"Time remaining: {int(remaining)} seconds"
                )
                
                time.sleep(5)
                
                check_status, check_result = _get(check_url, params={"agent": self.AGENT})
                
                if isinstance(check_result, dict) and check_result.get('status') == 'success':
                    api_key = check_result.get('data', {}).get('apikey')
                    if api_key:
                        self.token = api_key
                        self._save_to_file()
                        dialog.close()
                        xbmcgui.Dialog().notification("Success!", "AllDebrid linked!", xbmcgui.NOTIFICATION_INFO)
                        xbmc.log('AllDebrid: Authorization successful', xbmc.LOGINFO)
                        return True
            
            dialog.close()
            xbmcgui.Dialog().notification('Timeout', 'Authorization timed out', xbmcgui.NOTIFICATION_WARNING)
            return False
            
        except Exception as e:
            xbmc.log(f"AD auth error: {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Error', f'Auth failed: {str(e)}', xbmcgui.NOTIFICATION_ERROR)
            return False
    
    def check_cache(self, magnets):
        """Check if magnets are cached on AllDebrid"""
        if not self.is_authorized() or not magnets:
            return {}
        
        try:
            # AD uses magnets array
            params = {"agent": self.AGENT, "apikey": self.token}
            for i, m in enumerate(magnets[:50]):
                params[f'magnets[{i}]'] = m
            
            status, result = _get(f"{self.BASE_URL}/magnet/instant", params=params)
            
            if isinstance(result, dict) and result.get('status') == 'success':
                cached = {}
                data = result.get('data', {}).get('magnets', [])
                for item in data:
                    if item.get('instant'):
                        cached[item.get('hash', '').lower()] = True
                return cached
        except Exception as e:
            xbmc.log(f'AD cache check error: {e}', xbmc.LOGERROR)
        
        return {}
    
    def unrestrict_link(self, link):
        if not self.is_authorized():
            return None
        try:
            status, result = _get(
                f"{self.BASE_URL}/link/unlock",
                params={"agent": self.AGENT, "apikey": self.token, "link": link}
            )
            if isinstance(result, dict) and result.get('status') == 'success':
                return result.get('data', {}).get('link')
        except Exception as e:
            xbmc.log(f'AD unrestrict error: {e}', xbmc.LOGERROR)
        return None
    
    def add_magnet(self, magnet, check_cache_first=True):
        if not self.is_authorized():
            return None
        try:
            status, result = _get(
                f"{self.BASE_URL}/magnet/upload",
                params={"agent": self.AGENT, "apikey": self.token, "magnets[]": magnet}
            )
            
            if not isinstance(result, dict) or result.get('status') != 'success':
                return None
            
            magnet_id = result.get('data', {}).get('magnets', [{}])[0].get('id')
            if not magnet_id:
                return None
            
            for _ in range(30):
                _, status_result = _get(
                    f"{self.BASE_URL}/magnet/status",
                    params={"agent": self.AGENT, "apikey": self.token, "id": magnet_id}
                )
                
                if isinstance(status_result, dict) and status_result.get('status') == 'success':
                    magnet_data = status_result.get('data', {}).get('magnets', {})
                    if magnet_data.get('status') == 'Ready':
                        links = magnet_data.get('links', [])
                        if links:
                            return self.unrestrict_link(links[0].get('link'))
                time.sleep(2)
            
            return None
        except Exception as e:
            xbmc.log(f'AD magnet error: {e}', xbmc.LOGERROR)
            return None
    
    def revoke(self):
        if os.path.exists(AD_TOKEN_FILE):
            try:
                os.remove(AD_TOKEN_FILE)
            except:
                pass
        
        addon = get_addon()
        addon.setSetting('ad_api_key', '')
        addon.setSetting('ad_auth_done', 'false')
        self.token = ''
        xbmcgui.Dialog().notification("AllDebrid", "Account unlinked", xbmcgui.NOTIFICATION_INFO)

    def account_info(self):
        """Get AllDebrid account info"""
        if not self.token:
            return {}
        try:
            status, result = _get(
                f"{self.BASE_URL}/user",
                params={"agent": self.AGENT, "apikey": self.token}
            )
            if isinstance(result, dict) and result.get('status') == 'success':
                data = result.get('data', {}).get('user', {})
                premium_until = data.get('premiumUntil', 0)
                days_left = 0
                exp_str = 'Unknown'
                if premium_until:
                    try:
                        from datetime import datetime
                        exp_date = datetime.utcfromtimestamp(premium_until)
                        delta = exp_date - datetime.utcnow()
                        days_left = max(0, delta.days)
                        exp_str = exp_date.strftime('%Y-%m-%d')
                    except:
                        pass
                return {
                    'username': data.get('username', ''),
                    'email': data.get('email', ''),
                    'type': 'premium' if data.get('isPremium') else 'free',
                    'premium': bool(data.get('isPremium')),
                    'expiration': exp_str,
                    'days_left': days_left,
                }
        except Exception as e:
            xbmc.log(f'AD account_info error: {e}', xbmc.LOGERROR)
        return {}


class Premiumize:
    """Premiumize API integration with file-based token storage"""
    
    BASE_URL = "https://www.premiumize.me/api"
    TOKEN_URL = "https://www.premiumize.me/token"
    DEVICE_URL = "https://www.premiumize.me/device"
    CLIENT_ID = "855400527"  # Public client ID
    
    def __init__(self):
        self._load_from_file()
    
    def _load_from_file(self):
        """Load token from file"""
        _ensure_data_path()
        self.token = ''
        
        if os.path.exists(PM_TOKEN_FILE):
            try:
                with open(PM_TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    self.token = data.get('access_token', '')
                    if self.token:
                        xbmc.log('Premiumize: Loaded token from file', xbmc.LOGDEBUG)
            except:
                pass
        
        if not self.token:
            self.token = get_addon().getSetting('pm_access_token')
    
    def _save_to_file(self):
        """Save token to file"""
        _ensure_data_path()
        try:
            with open(PM_TOKEN_FILE, 'w') as f:
                json.dump({'access_token': self.token, 'created_at': time.time()}, f)
            addon = get_addon()
            addon.setSetting('pm_access_token', self.token)
            addon.setSetting('pm_auth_done', 'true')
        except:
            pass
    
    def is_authorized(self):
        return bool(self.token)
    
    def authorize(self):
        """OAuth device authorization"""
        try:
            xbmc.log('Premiumize: Requesting device code...', xbmc.LOGINFO)
            
            status, result = _post(
                f"{self.TOKEN_URL}",
                data={"response_type": "device_code", "client_id": self.CLIENT_ID}
            )
            
            if not isinstance(result, dict) or not result.get('device_code'):
                xbmc.log(f'Premiumize: Failed to get device code - {result}', xbmc.LOGERROR)
                xbmcgui.Dialog().notification('Error', 'Failed to get device code', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            device_code = result.get('device_code')
            user_code = result.get('user_code')
            verification_url = result.get('verification_uri', self.DEVICE_URL)
            expires_in = result.get('expires_in', 600)
            interval = result.get('interval', 5)
            
            xbmc.log(f'Premiumize: Got device code, user_code: {user_code}', xbmc.LOGINFO)
            
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                "Premiumize Authorization",
                f"Go to: [B][COLOR skyblue]{verification_url}[/COLOR][/B]\n\n"
                f"Enter Code: [B][COLOR yellow]{user_code}[/COLOR][/B]\n\n"
                f"Waiting for authorization..."
            )
            
            start = time.time()
            while time.time() - start < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                elapsed = time.time() - start
                remaining = expires_in - elapsed
                progress = int((elapsed / expires_in) * 100)
                dialog.update(
                    progress,
                    f"Go to: [B][COLOR skyblue]{verification_url}[/COLOR][/B]\n\n"
                    f"Enter Code: [B][COLOR yellow]{user_code}[/COLOR][/B]\n\n"
                    f"Time remaining: {int(remaining)} seconds"
                )
                
                time.sleep(interval)
                
                check_status, check_result = _post(
                    f"{self.TOKEN_URL}",
                    data={
                        "grant_type": "device_code",
                        "client_id": self.CLIENT_ID,
                        "code": device_code
                    }
                )
                
                if isinstance(check_result, dict) and check_result.get('access_token'):
                    self.token = check_result.get('access_token')
                    self._save_to_file()
                    dialog.close()
                    xbmcgui.Dialog().notification("Success!", "Premiumize linked!", xbmcgui.NOTIFICATION_INFO)
                    xbmc.log('Premiumize: Authorization successful', xbmc.LOGINFO)
                    return True
            
            dialog.close()
            xbmcgui.Dialog().notification('Timeout', 'Authorization timed out', xbmcgui.NOTIFICATION_WARNING)
            return False
            
        except Exception as e:
            xbmc.log(f"PM auth error: {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Error', f'Auth failed: {str(e)}', xbmcgui.NOTIFICATION_ERROR)
            return False
    
    def check_cache(self, hashes):
        """Check if files are cached on Premiumize"""
        if not self.is_authorized() or not hashes:
            return {}
        
        try:
            # PM uses items[] array
            params = {"items[]": hashes[:100]}
            status, result = _post(
                f"{self.BASE_URL}/cache/check",
                headers={"Authorization": f"Bearer {self.token}"},
                data=params
            )
            
            if isinstance(result, dict) and result.get('status') == 'success':
                response = result.get('response', [])
                cached = {}
                for i, is_cached in enumerate(response):
                    if is_cached and i < len(hashes):
                        cached[hashes[i].lower()] = True
                return cached
        except Exception as e:
            xbmc.log(f'PM cache check error: {e}', xbmc.LOGERROR)
        
        return {}
    
    def unrestrict_link(self, link):
        if not self.is_authorized():
            return None
        try:
            status, result = _post(
                f"{self.BASE_URL}/transfer/directdl",
                headers={"Authorization": f"Bearer {self.token}"},
                data={"src": link}
            )
            if isinstance(result, dict) and result.get('status') == 'success':
                content = result.get('content', [])
                if content:
                    return content[0].get('link')
        except Exception as e:
            xbmc.log(f'PM unrestrict error: {e}', xbmc.LOGERROR)
        return None
    
    def add_magnet(self, magnet, check_cache_first=True):
        return self.unrestrict_link(magnet)
    
    def revoke(self):
        if os.path.exists(PM_TOKEN_FILE):
            try:
                os.remove(PM_TOKEN_FILE)
            except:
                pass
        
        addon = get_addon()
        addon.setSetting('pm_access_token', '')
        addon.setSetting('pm_auth_done', 'false')
        self.token = ''
        xbmcgui.Dialog().notification("Premiumize", "Account unlinked", xbmcgui.NOTIFICATION_INFO)

    def account_info(self):
        """Get Premiumize account info"""
        if not self.token:
            return {}
        try:
            status, result = _get(
                f"{self.BASE_URL}/account/info",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if status == 200 and isinstance(result, dict) and result.get('status') == 'success':
                premium_until = result.get('premium_until', 0)
                days_left = 0
                exp_str = 'Unknown'
                if premium_until:
                    try:
                        from datetime import datetime
                        exp_date = datetime.utcfromtimestamp(premium_until)
                        delta = exp_date - datetime.utcnow()
                        days_left = max(0, delta.days)
                        exp_str = exp_date.strftime('%Y-%m-%d')
                    except:
                        pass
                return {
                    'username': str(result.get('customer_id', '')),
                    'type': 'premium' if premium_until else 'free',
                    'premium': bool(premium_until and days_left > 0),
                    'expiration': exp_str,
                    'days_left': days_left,
                    'space_used': result.get('space_used', 0),
                    'limit_used': result.get('limit_used', 0),
                }
            elif status == 401:
                return {'type': 'expired', 'premium': False, 'days_left': 0,
                        'expiration': 'Token expired - re-authorize'}
        except Exception as e:
            xbmc.log(f'PM account_info error: {e}', xbmc.LOGERROR)
        return {}


class TorBox:
    """TorBox debrid service - device code auth"""
    BASE_URL = 'https://api.torbox.app/v1/api'
    DEVICE_START = 'https://api.torbox.app/v1/api/user/auth/device/start'
    DEVICE_TOKEN = 'https://api.torbox.app/v1/api/user/auth/device/token'

    def __init__(self):
        self.token = ''
        self._load_token()

    def _load_token(self):
        addon = get_addon()
        self.token = addon.getSetting('tb_api_key') or ''
        if not self.token and os.path.exists(TB_TOKEN_FILE):
            try:
                with open(TB_TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    self.token = data.get('api_key', '')
                    if self.token:
                        addon.setSetting('tb_api_key', self.token)
            except:
                pass

    def _save_token(self, api_key):
        self.token = api_key
        addon = get_addon()
        addon.setSetting('tb_api_key', api_key)
        addon.setSetting('tb_auth_done', 'true')
        try:
            os.makedirs(os.path.dirname(TB_TOKEN_FILE), exist_ok=True)
            with open(TB_TOKEN_FILE, 'w') as f:
                json.dump({'api_key': api_key}, f)
        except:
            pass

    def _auth_headers(self):
        return {'Authorization': f'Bearer {self.token}', 'User-Agent': 'TraktPlayer/2.3.0'}

    def authorize(self):
        """TorBox device code authorization"""
        try:
            xbmc.log('TorBox: Requesting device code...', xbmc.LOGINFO)

            # Step 1: Get device code
            status, result = _get(self.DEVICE_START)
            if not isinstance(result, dict) or not result.get('success'):
                xbmcgui.Dialog().ok('TorBox', 'Failed to get device code. Try again.')
                return

            data = result.get('data', {})
            device_code = data.get('device_code', '')
            user_code = data.get('code', '')
            verify_url = data.get('friendly_verification_url', '') or data.get('verification_url', '')
            interval = data.get('interval', 5)

            if not device_code:
                xbmcgui.Dialog().ok('TorBox', 'No device code received.')
                return

            # Step 2: Show code and poll
            progress = xbmcgui.DialogProgress()
            progress.create('TorBox Authorization',
                            f'Go to: [COLOR skyblue]{verify_url}[/COLOR]\n'
                            f'Enter code: [COLOR gold][B]{user_code}[/B][/COLOR]')

            for i in range(120):
                if progress.iscanceled():
                    break

                xbmc.sleep(interval * 1000)
                pct = int((i / 120.0) * 100)
                progress.update(pct)

                try:
                    poll_url = f'{self.DEVICE_TOKEN}?device_code={device_code}'
                    poll_status, poll_result = _get(poll_url)
                    if isinstance(poll_result, dict) and poll_result.get('success'):
                        api_key = poll_result.get('data', {}).get('api_key', '') or poll_result.get('data', {}).get('access_token', '')
                        if api_key:
                            self._save_token(api_key)
                            progress.close()
                            xbmcgui.Dialog().notification('TorBox', 'Authorized!', xbmcgui.NOTIFICATION_INFO)
                            return
                except:
                    pass

            progress.close()
            xbmcgui.Dialog().notification('TorBox', 'Auth timed out', xbmcgui.NOTIFICATION_WARNING)

        except Exception as e:
            xbmc.log(f'TorBox auth error: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('TorBox', f'Auth error: {e}', xbmcgui.NOTIFICATION_ERROR)

    def is_authorized(self):
        if not self.token:
            return False
        try:
            status, result = _get(f'{self.BASE_URL}/user/me', headers=self._auth_headers())
            if status == 200 and isinstance(result, dict) and result.get('success'):
                return True
        except:
            pass
        return False

    def unrestrict_link(self, link):
        """Create a web download and get the link"""
        if not self.token:
            return None
        try:
            status, result = _post(
                f'{self.BASE_URL}/webdl/createwebdownload',
                headers=self._auth_headers(),
                data={'url': link}
            )
            if isinstance(result, dict) and result.get('success'):
                dl_url = result.get('data', {}).get('download_url')
                if dl_url:
                    return dl_url
                # If no direct URL, request download link
                dl_id = result.get('data', {}).get('id')
                if dl_id:
                    xbmc.sleep(2000)
                    s2, r2 = _get(
                        f'{self.BASE_URL}/webdl/requestdl?token={self.token}&web_id={dl_id}',
                        headers=self._auth_headers()
                    )
                    if isinstance(r2, dict) and r2.get('data'):
                        return r2['data']
        except Exception as e:
            xbmc.log(f'TorBox unrestrict error: {e}', xbmc.LOGERROR)
        return None

    def add_magnet(self, magnet, check_cache_first=True):
        """Add a magnet and get download link"""
        if not self.token:
            return None
        try:
            status, result = _post(
                f'{self.BASE_URL}/torrents/createtorrent',
                headers=self._auth_headers(),
                data={'magnet': magnet}
            )
            if isinstance(result, dict) and result.get('success'):
                torrent_id = result.get('data', {}).get('torrent_id')
                if torrent_id:
                    xbmc.sleep(3000)
                    s2, r2 = _get(
                        f'{self.BASE_URL}/torrents/requestdl?token={self.token}&torrent_id={torrent_id}&file_id=0',
                        headers=self._auth_headers()
                    )
                    if isinstance(r2, dict) and r2.get('data'):
                        return r2['data']
        except Exception as e:
            xbmc.log(f'TorBox magnet error: {e}', xbmc.LOGERROR)
        return None

    def check_cache(self, hashes):
        """Check which hashes are cached on TorBox"""
        if not self.token or not hashes:
            return {}
        try:
            hash_str = ','.join(hashes[:100])
            status, result = _get(
                f'{self.BASE_URL}/torrents/checkcached?hash={hash_str}',
                headers=self._auth_headers()
            )
            if isinstance(result, dict) and result.get('data'):
                cached = {}
                for item in result['data']:
                    if isinstance(item, str):
                        cached[item.lower()] = True
                    elif isinstance(item, dict) and item.get('hash'):
                        cached[item['hash'].lower()] = True
                return cached
        except Exception as e:
            xbmc.log(f'TorBox cache check error: {e}', xbmc.LOGERROR)
        return {}

    def revoke(self):
        if os.path.exists(TB_TOKEN_FILE):
            try:
                os.remove(TB_TOKEN_FILE)
            except:
                pass
        addon = get_addon()
        addon.setSetting('tb_api_key', '')
        addon.setSetting('tb_auth_done', 'false')
        self.token = ''
        xbmcgui.Dialog().notification('TorBox', 'Account unlinked', xbmcgui.NOTIFICATION_INFO)

    def account_info(self):
        """Get TorBox account info"""
        if not self.token:
            return {}
        try:
            status, result = _get(f'{self.BASE_URL}/user/me', headers=self._auth_headers())
            if status == 200 and isinstance(result, dict) and result.get('success'):
                data = result.get('data', {})
                premium_until = data.get('premium_expires_at', '') or data.get('plan_active_until', '')
                days_left = 0
                exp_str = 'Unknown'
                if premium_until:
                    try:
                        from datetime import datetime
                        exp_date = datetime.strptime(premium_until[:19], '%Y-%m-%dT%H:%M:%S')
                        delta = exp_date - datetime.utcnow()
                        days_left = max(0, delta.days)
                        exp_str = exp_date.strftime('%Y-%m-%d')
                    except:
                        exp_str = str(premium_until)[:10]
                plan = data.get('plan', 0)
                return {
                    'username': data.get('email', ''),
                    'email': data.get('email', ''),
                    'type': 'premium' if plan and plan > 0 else 'free',
                    'premium': bool(plan and plan > 0),
                    'expiration': exp_str,
                    'days_left': days_left,
                }
            elif status in (401, 403):
                return {'type': 'expired', 'premium': False, 'days_left': 0,
                        'expiration': 'API key invalid - re-authorize'}
        except Exception as e:
            xbmc.log(f'TB account_info error: {e}', xbmc.LOGERROR)
        return {}


class LinkSnappy:
    """LinkSnappy debrid service - API key auth"""
    BASE_URL = 'https://linksnappy.com/api'

    def __init__(self):
        self.username = ''
        self.password = ''
        self.cookie = ''
        self._load_credentials()

    def _load_credentials(self):
        addon = get_addon()
        self.username = addon.getSetting('ls_username') or ''
        self.password = addon.getSetting('ls_password') or ''
        self.cookie = addon.getSetting('ls_cookie') or ''
        if not self.cookie and os.path.exists(LS_TOKEN_FILE):
            try:
                with open(LS_TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    self.cookie = data.get('cookie', '')
                    self.username = data.get('username', self.username)
            except:
                pass

    def _save_credentials(self, cookie):
        self.cookie = cookie
        addon = get_addon()
        addon.setSetting('ls_cookie', cookie)
        addon.setSetting('ls_auth_done', 'true')
        try:
            os.makedirs(os.path.dirname(LS_TOKEN_FILE), exist_ok=True)
            with open(LS_TOKEN_FILE, 'w') as f:
                json.dump({'cookie': cookie, 'username': self.username}, f)
        except:
            pass

    def authorize(self):
        """LinkSnappy login auth"""
        try:
            dialog = xbmcgui.Dialog()
            username = dialog.input('LinkSnappy Username')
            if not username:
                return
            password = dialog.input('LinkSnappy Password', option=xbmcgui.ALPHANUM_HIDE_INPUT)
            if not password:
                return

            xbmc.log('LinkSnappy: Logging in...', xbmc.LOGINFO)

            import urllib.request
            import urllib.parse
            import http.cookiejar

            cj = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            data = urllib.parse.urlencode({
                'username': username,
                'password': password
            }).encode()
            req = urllib.request.Request(f'{self.BASE_URL}/AUTHENTICATE',
                                         data=data,
                                         headers={'User-Agent': 'TraktPlayer/2.3.0'})
            resp = opener.open(req, timeout=15)
            result = json.loads(resp.read().decode())

            if result.get('status') == 'OK':
                # Extract cookie string
                cookies = '; '.join([f'{c.name}={c.value}' for c in cj])
                self.username = username
                self.password = password
                addon = get_addon()
                addon.setSetting('ls_username', username)
                addon.setSetting('ls_password', password)
                self._save_credentials(cookies)
                dialog.notification('LinkSnappy', f'Logged in as {username}', xbmcgui.NOTIFICATION_INFO)
            else:
                error_msg = result.get('error', 'Login failed')
                dialog.notification('LinkSnappy', error_msg, xbmcgui.NOTIFICATION_ERROR)
                xbmc.log(f'LinkSnappy login error: {error_msg}', xbmc.LOGERROR)

        except Exception as e:
            xbmc.log(f'LinkSnappy auth error: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('LinkSnappy', f'Auth error: {e}', xbmcgui.NOTIFICATION_ERROR)

    def is_authorized(self):
        if self.username and self.password:
            return True
        if self.cookie:
            return True
        return False

    def _login_headers(self):
        headers = {'User-Agent': 'TraktPlayer/2.3.0'}
        if self.cookie:
            headers['Cookie'] = self.cookie
        return headers

    def unrestrict_link(self, link):
        """Generate a premium download link"""
        if not self.is_authorized():
            return None
        try:
            import urllib.request
            import urllib.parse

            # Re-login if needed
            if not self.cookie and self.username and self.password:
                self._re_login()

            data = urllib.parse.urlencode({
                'genLinks': json.dumps([{'link': link}]),
                'username': self.username,
                'password': self.password,
            }).encode()

            req = urllib.request.Request(f'{self.BASE_URL}/linkgen',
                                         data=data,
                                         headers=self._login_headers())
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode())

            if result.get('status') == 'OK':
                links = result.get('links', [])
                if links:
                    gen = links[0].get('generated', '')
                    if gen:
                        return gen
            elif result.get('status') == 'ERROR':
                xbmc.log(f'LinkSnappy linkgen error: {result.get("error", "")}', xbmc.LOGERROR)
        except Exception as e:
            xbmc.log(f'LinkSnappy unrestrict error: {e}', xbmc.LOGERROR)
        return None

    def _re_login(self):
        """Re-authenticate to get fresh cookies"""
        try:
            import urllib.request
            import urllib.parse
            import http.cookiejar

            cj = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            data = urllib.parse.urlencode({
                'username': self.username,
                'password': self.password
            }).encode()
            req = urllib.request.Request(f'{self.BASE_URL}/AUTHENTICATE',
                                         data=data,
                                         headers={'User-Agent': 'TraktPlayer/2.3.0'})
            resp = opener.open(req, timeout=15)
            result = json.loads(resp.read().decode())
            if result.get('status') == 'OK':
                cookies = '; '.join([f'{c.name}={c.value}' for c in cj])
                self._save_credentials(cookies)
        except:
            pass

    def add_magnet(self, magnet, check_cache_first=True):
        return self.unrestrict_link(magnet)

    def check_cache(self, hashes):
        return {}

    def revoke(self):
        if os.path.exists(LS_TOKEN_FILE):
            try:
                os.remove(LS_TOKEN_FILE)
            except:
                pass
        addon = get_addon()
        addon.setSetting('ls_username', '')
        addon.setSetting('ls_password', '')
        addon.setSetting('ls_cookie', '')
        addon.setSetting('ls_auth_done', 'false')
        self.username = ''
        self.password = ''
        self.cookie = ''
        xbmcgui.Dialog().notification('LinkSnappy', 'Account unlinked', xbmcgui.NOTIFICATION_INFO)

    def account_info(self):
        """Get LinkSnappy account info"""
        if not self.is_authorized():
            return {}
        try:
            import urllib.request
            import urllib.parse

            if not self.cookie and self.username and self.password:
                self._re_login()

            data = urllib.parse.urlencode({
                'username': self.username,
                'password': self.password,
            }).encode()
            req = urllib.request.Request(f'{self.BASE_URL}/USERDETAILS',
                                         data=data,
                                         headers=self._login_headers())
            resp = urllib.request.urlopen(req, timeout=15)
            result = json.loads(resp.read().decode())

            if result.get('status') == 'OK':
                user_data = result.get('return', {})
                expire = user_data.get('expire', '')
                days_left = 0
                exp_str = 'Unknown'
                if expire:
                    try:
                        from datetime import datetime
                        if str(expire).isdigit():
                            exp_date = datetime.utcfromtimestamp(int(expire))
                        else:
                            exp_date = datetime.strptime(str(expire)[:19], '%Y-%m-%dT%H:%M:%S')
                        delta = exp_date - datetime.utcnow()
                        days_left = max(0, delta.days)
                        exp_str = exp_date.strftime('%Y-%m-%d')
                    except:
                        exp_str = str(expire)
                return {
                    'username': self.username,
                    'type': user_data.get('package', 'unknown'),
                    'premium': bool(days_left > 0),
                    'expiration': exp_str,
                    'days_left': days_left,
                }
        except Exception as e:
            xbmc.log(f'LS account_info error: {e}', xbmc.LOGERROR)
        return {}


def get_debrid_services():
    """Get list of authorized debrid services in priority order"""
    services = []
    
    rd = RealDebrid()
    if rd.is_authorized():
        services.append(('Real-Debrid', rd))
        xbmc.log('Debrid: Real-Debrid is authorized', xbmc.LOGINFO)
    
    ad = AllDebrid()
    if ad.is_authorized():
        services.append(('AllDebrid', ad))
        xbmc.log('Debrid: AllDebrid is authorized', xbmc.LOGINFO)
    
    pm = Premiumize()
    if pm.is_authorized():
        services.append(('Premiumize', pm))
        xbmc.log('Debrid: Premiumize is authorized', xbmc.LOGINFO)
    
    tb = TorBox()
    if tb.is_authorized():
        services.append(('TorBox', tb))
        xbmc.log('Debrid: TorBox is authorized', xbmc.LOGINFO)
    
    ls = LinkSnappy()
    if ls.is_authorized():
        services.append(('LinkSnappy', ls))
        xbmc.log('Debrid: LinkSnappy is authorized', xbmc.LOGINFO)
    
    if not services:
        xbmc.log('Debrid: No debrid services authorized', xbmc.LOGWARNING)
    
    return services


def resolve_with_debrid(link_or_magnet, is_magnet=False):
    """Try to resolve link through available debrid services"""
    services = get_debrid_services()
    
    for name, service in services:
        try:
            xbmc.log(f"Attempting to resolve via {name}...", xbmc.LOGINFO)
            
            if is_magnet:
                result = service.add_magnet(link_or_magnet, check_cache_first=True)
            else:
                result = service.unrestrict_link(link_or_magnet)
            
            if result:
                xbmc.log(f"Resolved via {name}: {result[:80]}...", xbmc.LOGINFO)
                return result, name
        except Exception as e:
            xbmc.log(f"{name} failed: {str(e)}", xbmc.LOGERROR)
            continue
    
    return None, None


# ── Compatibility aliases for player.py ──────────────────────────────────

def get_active_services():
    """Alias for get_debrid_services() - returns list of (name, service) tuples."""
    return get_debrid_services()


def check_cache_all(hashes):
    """Check all hashes against all authorized debrid services. Returns set of cached hashes."""
    cached = set()
    services = get_debrid_services()
    
    for name, service in services:
        try:
            if hasattr(service, 'check_cache') and hashes:
                result = service.check_cache(hashes)
                if isinstance(result, (set, list)):
                    cached.update(set(h.lower() for h in result))
                elif isinstance(result, dict):
                    for h, is_cached in result.items():
                        if is_cached:
                            cached.add(h.lower())
        except Exception as e:
            xbmc.log(f'Cache check failed for {name}: {e}', xbmc.LOGDEBUG)
    
    return cached


def resolve_magnet(magnet):
    """Resolve a magnet link through debrid. Returns (url, service_name) or (None, None)."""
    return resolve_with_debrid(magnet, is_magnet=True)


def get_all_account_info():
    """Get account status for all debrid services."""
    accounts = []
    
    # Real-Debrid
    try:
        rd = RealDebrid()
        if rd.token:
            info = rd.account_info()
            if info:
                accounts.append({
                    'name': 'Real-Debrid',
                    'configured': True,
                    'username': info.get('username', ''),
                    'email': info.get('email', ''),
                    'type': info.get('type', 'unknown'),
                    'premium': info.get('premium', False),
                    'expires': info.get('expiration', 'Unknown'),
                    'days_left': info.get('days_left', 0),
                    'points': info.get('points', 0),
                })
            else:
                accounts.append({'name': 'Real-Debrid', 'configured': True, 
                                 'error': 'Could not fetch account info - try re-authorizing'})
        else:
            accounts.append({'name': 'Real-Debrid', 'configured': False})
    except Exception as e:
        accounts.append({'name': 'Real-Debrid', 'configured': True, 'error': str(e)})
    
    # AllDebrid
    try:
        ad = AllDebrid()
        if ad.token:
            info = ad.account_info()
            if info:
                accounts.append({
                    'name': 'AllDebrid',
                    'configured': True,
                    'username': info.get('username', ''),
                    'email': info.get('email', ''),
                    'type': info.get('type', 'unknown'),
                    'premium': info.get('premium', False),
                    'expires': info.get('expiration', 'Unknown'),
                    'days_left': info.get('days_left', 0),
                })
            else:
                accounts.append({'name': 'AllDebrid', 'configured': True,
                                 'error': 'Could not fetch account info - try re-authorizing'})
        else:
            accounts.append({'name': 'AllDebrid', 'configured': False})
    except Exception as e:
        accounts.append({'name': 'AllDebrid', 'configured': True, 'error': str(e)})
    
    # Premiumize
    try:
        pm = Premiumize()
        if pm.token:
            info = pm.account_info()
            if info:
                accounts.append({
                    'name': 'Premiumize',
                    'configured': True,
                    'username': info.get('username', ''),
                    'type': info.get('type', 'unknown'),
                    'premium': info.get('premium', False),
                    'expires': info.get('expiration', 'Unknown'),
                    'days_left': info.get('days_left', 0),
                })
            else:
                accounts.append({'name': 'Premiumize', 'configured': True,
                                 'error': 'Could not fetch account info - try re-authorizing'})
        else:
            accounts.append({'name': 'Premiumize', 'configured': False})
    except Exception as e:
        accounts.append({'name': 'Premiumize', 'configured': True, 'error': str(e)})
    
    # TorBox
    try:
        tb = TorBox()
        if tb.token:
            info = tb.account_info()
            if info:
                accounts.append({
                    'name': 'TorBox',
                    'configured': True,
                    'username': info.get('username', ''),
                    'email': info.get('email', ''),
                    'type': info.get('type', 'unknown'),
                    'premium': info.get('premium', False),
                    'expires': info.get('expiration', 'Unknown'),
                    'days_left': info.get('days_left', 0),
                })
            else:
                accounts.append({'name': 'TorBox', 'configured': True,
                                 'error': 'Could not fetch account info - try re-authorizing'})
        else:
            accounts.append({'name': 'TorBox', 'configured': False})
    except Exception as e:
        accounts.append({'name': 'TorBox', 'configured': True, 'error': str(e)})
    
    # LinkSnappy
    try:
        ls = LinkSnappy()
        if ls.is_authorized():
            info = ls.account_info()
            if info:
                accounts.append({
                    'name': 'LinkSnappy',
                    'configured': True,
                    'username': info.get('username', ''),
                    'type': info.get('type', 'unknown'),
                    'premium': info.get('premium', False),
                    'expires': info.get('expiration', 'Unknown'),
                    'days_left': info.get('days_left', 0),
                })
            else:
                accounts.append({'name': 'LinkSnappy', 'configured': True,
                                 'error': 'Could not fetch account info - try re-logging in'})
        else:
            accounts.append({'name': 'LinkSnappy', 'configured': False})
    except Exception as e:
        accounts.append({'name': 'LinkSnappy', 'configured': True, 'error': str(e)})
    
    return accounts
