"""
Tinklepad Debrid Manager v1.5
Handles Real-Debrid, AllDebrid, and Premiumize authorization and link resolution
Fixed: Token persistence issue in Kodi 21 (Omega) - uses file backup for tokens
"""
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import requests
import time
import os
import json

# API Endpoints
RD_BASE = 'https://api.real-debrid.com/rest/1.0'
RD_OAUTH = 'https://api.real-debrid.com/oauth/v2'
AD_BASE = 'https://api.alldebrid.com/v4'
PM_BASE = 'https://www.premiumize.me/api'

# Real-Debrid Client ID (public)
RD_CLIENT_ID = 'X245A4XAIBGVM'

# Addon ID
ADDON_ID = 'plugin.video.tinklepad'


def get_addon_data_path():
    """Get the addon userdata path"""
    try:
        addon = xbmcaddon.Addon(ADDON_ID)
        return xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    except:
        return xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.tinklepad/')


def get_token_file_path():
    """Get path to token storage file"""
    data_path = get_addon_data_path()
    if not xbmcvfs.exists(data_path):
        xbmcvfs.mkdirs(data_path)
    return os.path.join(data_path, 'debrid_tokens.json')


class DebridManager:
    def __init__(self):
        self._token_cache = None
        self._cache_time = 0
        self._load_tokens()
    
    def _load_tokens(self):
        """Load tokens from file"""
        try:
            token_file = get_token_file_path()
            if xbmcvfs.exists(token_file):
                f = xbmcvfs.File(token_file, 'r')
                data = f.read()
                f.close()
                if data:
                    self._token_cache = json.loads(data)
                    xbmc.log(f'[Tinklepad] Loaded tokens from file: {list(self._token_cache.keys())}', xbmc.LOGINFO)
                    return
        except Exception as e:
            xbmc.log(f'[Tinklepad] Failed to load tokens from file: {e}', xbmc.LOGERROR)
        
        self._token_cache = {}
    
    def _save_tokens(self):
        """Save tokens to file"""
        try:
            token_file = get_token_file_path()
            data_path = get_addon_data_path()
            
            # Ensure directory exists
            if not xbmcvfs.exists(data_path):
                xbmcvfs.mkdirs(data_path)
            
            f = xbmcvfs.File(token_file, 'w')
            f.write(json.dumps(self._token_cache, indent=2))
            f.close()
            xbmc.log(f'[Tinklepad] Saved tokens to file', xbmc.LOGINFO)
            return True
        except Exception as e:
            xbmc.log(f'[Tinklepad] Failed to save tokens: {e}', xbmc.LOGERROR)
            return False
    
    def get_token(self, key):
        """Get a token value"""
        if self._token_cache is None:
            self._load_tokens()
        
        value = self._token_cache.get(key, '')
        xbmc.log(f'[Tinklepad] Get {key} = {value[:20] if value and len(str(value)) > 20 else value}', xbmc.LOGDEBUG)
        return value
    
    def set_token(self, key, value):
        """Set a token value and save to file"""
        if self._token_cache is None:
            self._token_cache = {}
        
        self._token_cache[key] = str(value)
        xbmc.log(f'[Tinklepad] Set {key} = {value[:20] if len(str(value)) > 20 else value}...', xbmc.LOGINFO)
        
        # Also try to save to Kodi settings for UI display
        try:
            addon = xbmcaddon.Addon(ADDON_ID)
            addon.setSetting(key, str(value))
        except:
            pass
        
        return self._save_tokens()
    
    def clear_tokens(self, prefix):
        """Clear all tokens with given prefix"""
        if self._token_cache is None:
            self._token_cache = {}
        
        keys_to_remove = [k for k in self._token_cache if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._token_cache[key]
        
        self._save_tokens()
    
    # ==================== REAL-DEBRID ====================
    def rd_enabled(self):
        """Check if Real-Debrid has a valid token"""
        token = self.get_token('rd.token')
        return bool(token and len(token) > 10)
    
    def rd_authorized(self):
        """Check if we have a valid Real-Debrid token"""
        token = self.get_token('rd.token')
        is_auth = bool(token and len(token) > 10)
        xbmc.log(f'[Tinklepad] RD authorized check: {is_auth} (token len: {len(token) if token else 0})', xbmc.LOGINFO)
        return is_auth
    
    def rd_authorize(self):
        """OAuth device code flow for Real-Debrid"""
        try:
            xbmc.log('[Tinklepad] RD: Starting authorization...', xbmc.LOGINFO)
            
            # Step 1: Get device code
            response = requests.get(
                f'{RD_OAUTH}/device/code',
                params={'client_id': RD_CLIENT_ID, 'new_credentials': 'yes'},
                timeout=15
            )
            data = response.json()
            
            xbmc.log(f'[Tinklepad] RD: Got device code response: {list(data.keys())}', xbmc.LOGINFO)
            
            device_code = data['device_code']
            user_code = data['user_code']
            verification_url = data['verification_url']
            interval = data.get('interval', 5)
            expires_in = data.get('expires_in', 600)
            
            # Show user the code
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                'Real-Debrid Authorization',
                f'Go to: [COLOR gold]{verification_url}[/COLOR]\n\nEnter code: [COLOR gold]{user_code}[/COLOR]\n\nWaiting for authorization...'
            )
            
            # Step 2: Poll for authorization
            start_time = time.time()
            while time.time() - start_time < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                xbmc.sleep(interval * 1000)
                
                try:
                    cred_response = requests.get(
                        f'{RD_OAUTH}/device/credentials',
                        params={'client_id': RD_CLIENT_ID, 'code': device_code},
                        timeout=15
                    )
                    cred_data = cred_response.json()
                    
                    xbmc.log(f'[Tinklepad] RD: Credentials response: {cred_data}', xbmc.LOGDEBUG)
                    
                    if 'client_id' in cred_data and 'client_secret' in cred_data:
                        # Got credentials, now get token
                        client_id = cred_data['client_id']
                        client_secret = cred_data['client_secret']
                        
                        token_response = requests.post(
                            f'{RD_OAUTH}/token',
                            data={
                                'client_id': client_id,
                                'client_secret': client_secret,
                                'code': device_code,
                                'grant_type': 'http://oauth.net/grant_type/device/1.0'
                            },
                            timeout=15
                        )
                        token_data = token_response.json()
                        
                        xbmc.log(f'[Tinklepad] RD: Token response keys: {list(token_data.keys())}', xbmc.LOGINFO)
                        
                        if 'access_token' in token_data:
                            access_token = token_data['access_token']
                            refresh_token = token_data.get('refresh_token', '')
                            expires_in_token = token_data.get('expires_in', 0)
                            expiry_time = str(int(time.time()) + expires_in_token)
                            
                            xbmc.log('[Tinklepad] RD: Saving credentials to file...', xbmc.LOGINFO)
                            
                            # Save all credentials to file
                            self.set_token('rd.token', access_token)
                            self.set_token('rd.refresh', refresh_token)
                            self.set_token('rd.expiry', expiry_time)
                            self.set_token('rd.client_id', client_id)
                            self.set_token('rd.secret', client_secret)
                            
                            # Get username
                            username = self._rd_get_username(access_token)
                            if username:
                                self.set_token('rd.username', username)
                            
                            dialog.close()
                            
                            # Verify save worked
                            saved_token = self.get_token('rd.token')
                            xbmc.log(f'[Tinklepad] RD: Verification - saved token length: {len(saved_token) if saved_token else 0}', xbmc.LOGINFO)
                            
                            xbmcgui.Dialog().notification('Tinklepad', 'Real-Debrid Authorized!', xbmcgui.NOTIFICATION_INFO, 3000)
                            xbmc.log('[Tinklepad] RD: Authorization successful!', xbmc.LOGINFO)
                            return True
                            
                except Exception as e:
                    xbmc.log(f'[Tinklepad] RD poll error: {e}', xbmc.LOGDEBUG)
                    continue
            
            dialog.close()
            xbmcgui.Dialog().notification('Tinklepad', 'Authorization timed out', xbmcgui.NOTIFICATION_ERROR, 3000)
            return False
            
        except Exception as e:
            xbmc.log(f'[Tinklepad] RD auth error: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Tinklepad', f'Auth failed: {e}', xbmcgui.NOTIFICATION_ERROR, 3000)
            return False
    
    def _rd_get_username(self, token=None):
        """Fetch RD username"""
        try:
            if not token:
                token = self.get_token('rd.token')
            if not token:
                return None
                
            response = requests.get(
                f'{RD_BASE}/user',
                headers={'Authorization': f'Bearer {token}'},
                timeout=10
            )
            data = response.json()
            xbmc.log(f'[Tinklepad] RD User data: {data}', xbmc.LOGINFO)
            
            username = data.get('username', '') or data.get('email', '').split('@')[0]
            return username
        except Exception as e:
            xbmc.log(f'[Tinklepad] RD: Failed to get username: {e}', xbmc.LOGERROR)
            return None
    
    def rd_refresh_token(self):
        """Refresh Real-Debrid token"""
        try:
            refresh = self.get_token('rd.refresh')
            client_id = self.get_token('rd.client_id')
            client_secret = self.get_token('rd.secret')
            
            if not all([refresh, client_id, client_secret]):
                xbmc.log('[Tinklepad] RD: Missing refresh credentials', xbmc.LOGWARNING)
                return False
            
            response = requests.post(
                f'{RD_OAUTH}/token',
                data={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'refresh_token': refresh,
                    'grant_type': 'refresh_token'
                },
                timeout=15
            )
            data = response.json()
            
            if 'access_token' in data:
                self.set_token('rd.token', data['access_token'])
                self.set_token('rd.refresh', data.get('refresh_token', refresh))
                self.set_token('rd.expiry', str(int(time.time()) + data.get('expires_in', 0)))
                xbmc.log('[Tinklepad] RD: Token refreshed', xbmc.LOGINFO)
                return True
        except Exception as e:
            xbmc.log(f'[Tinklepad] RD refresh error: {e}', xbmc.LOGERROR)
        return False
    
    def rd_resolve(self, url):
        """Resolve a link through Real-Debrid"""
        try:
            token = self.get_token('rd.token')
            
            if not token:
                xbmc.log('[Tinklepad] RD: No token available', xbmc.LOGWARNING)
                return None
            
            # Check if token needs refresh
            expiry = self.get_token('rd.expiry')
            if expiry:
                try:
                    if int(expiry) < time.time():
                        xbmc.log('[Tinklepad] RD: Token expired, refreshing...', xbmc.LOGINFO)
                        if not self.rd_refresh_token():
                            return None
                        token = self.get_token('rd.token')
                except:
                    pass
            
            headers = {'Authorization': f'Bearer {token}'}
            
            # Handle magnets differently
            if url.startswith('magnet:'):
                # Add magnet to RD
                add_response = requests.post(
                    f'{RD_BASE}/torrents/addMagnet',
                    headers=headers,
                    data={'magnet': url},
                    timeout=15
                )
                add_data = add_response.json()
                
                if 'id' in add_data:
                    torrent_id = add_data['id']
                    
                    # Select all files
                    requests.post(
                        f'{RD_BASE}/torrents/selectFiles/{torrent_id}',
                        headers=headers,
                        data={'files': 'all'},
                        timeout=15
                    )
                    
                    # Wait for it to be ready
                    for _ in range(30):
                        info_response = requests.get(
                            f'{RD_BASE}/torrents/info/{torrent_id}',
                            headers=headers,
                            timeout=15
                        )
                        info_data = info_response.json()
                        
                        if info_data.get('status') == 'downloaded':
                            links = info_data.get('links', [])
                            if links:
                                # Unrestrict the first link
                                unrestrict_response = requests.post(
                                    f'{RD_BASE}/unrestrict/link',
                                    headers=headers,
                                    data={'link': links[0]},
                                    timeout=15
                                )
                                unrestrict_data = unrestrict_response.json()
                                
                                if 'download' in unrestrict_data:
                                    return unrestrict_data['download']
                            break
                        elif info_data.get('status') in ['magnet_error', 'error', 'dead']:
                            xbmc.log(f'[Tinklepad] RD: Torrent error: {info_data.get("status")}', xbmc.LOGWARNING)
                            break
                        
                        xbmc.sleep(2000)
            else:
                # Regular link - unrestrict
                response = requests.post(
                    f'{RD_BASE}/unrestrict/link',
                    headers=headers,
                    data={'link': url},
                    timeout=15
                )
                data = response.json()
                
                if 'download' in data:
                    xbmc.log(f'[Tinklepad] RD resolved successfully', xbmc.LOGINFO)
                    return data['download']
                elif 'error' in data:
                    error_code = data.get('error_code', 0)
                    error_msg = data.get('error', 'Unknown error')
                    xbmc.log(f'[Tinklepad] RD error: {error_msg} (code: {error_code})', xbmc.LOGWARNING)
                    
                    # Check for hoster_unavailable or similar errors that might work with remote upload
                    # Error codes: hoster_unavailable, hoster_not_free, hoster_limit_reached
                    if error_code in [23, 24, 25] or 'hoster_unavailable' in error_msg.lower() or 'unavailable' in error_msg.lower():
                        xbmc.log(f'[Tinklepad] RD: Direct unrestrict failed, trying remote download fallback...', xbmc.LOGINFO)
                        return self._rd_remote_download_fallback(url, headers)
                    
        except Exception as e:
            xbmc.log(f'[Tinklepad] RD resolve error: {e}', xbmc.LOGERROR)
        return None
    
    def _rd_remote_download_fallback(self, url, headers):
        """
        Fallback: Use Real-Debrid's remote download (downloads) feature
        when direct unrestriction fails (e.g., hoster_unavailable for Nitroflare/Rapidgator)
        """
        try:
            xbmc.log(f'[Tinklepad] RD: Adding link to remote downloads: {url[:50]}...', xbmc.LOGINFO)
            
            # Add link to RD downloads (remote upload)
            add_response = requests.post(
                f'{RD_BASE}/downloads/add',
                headers=headers,
                data={'link': url},
                timeout=30
            )
            add_data = add_response.json()
            
            xbmc.log(f'[Tinklepad] RD: Remote download add response: {add_data}', xbmc.LOGDEBUG)
            
            if 'id' in add_data:
                download_id = add_data['id']
                xbmc.log(f'[Tinklepad] RD: Remote download added with ID: {download_id}', xbmc.LOGINFO)
                
                # Show progress dialog
                dialog = xbmcgui.DialogProgress()
                dialog.create('Real-Debrid', 'Downloading file to Real-Debrid cloud...\nThis may take a few minutes.')
                
                # Poll for completion (max 5 minutes)
                max_wait = 300
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    if dialog.iscanceled():
                        xbmc.log('[Tinklepad] RD: Remote download cancelled by user', xbmc.LOGINFO)
                        dialog.close()
                        return None
                    
                    # Check download status
                    status_response = requests.get(
                        f'{RD_BASE}/downloads/info/{download_id}',
                        headers=headers,
                        timeout=15
                    )
                    status_data = status_response.json()
                    
                    status = status_data.get('status', '')
                    progress = status_data.get('progress', 0)
                    
                    xbmc.log(f'[Tinklepad] RD: Remote download status: {status}, progress: {progress}%', xbmc.LOGDEBUG)
                    
                    # Update dialog
                    elapsed = int(time.time() - start_time)
                    dialog.update(int(progress), f'Status: {status}\nProgress: {progress}%\nElapsed: {elapsed}s')
                    
                    if status == 'downloaded':
                        # Download complete - get the link
                        download_link = status_data.get('download', '')
                        if download_link:
                            dialog.close()
                            xbmc.log(f'[Tinklepad] RD: Remote download complete!', xbmc.LOGINFO)
                            return download_link
                        else:
                            # Try to get link from the download info
                            link = status_data.get('link', '')
                            if link:
                                # Unrestrict this RD link
                                unrestrict_response = requests.post(
                                    f'{RD_BASE}/unrestrict/link',
                                    headers=headers,
                                    data={'link': link},
                                    timeout=15
                                )
                                unrestrict_data = unrestrict_response.json()
                                if 'download' in unrestrict_data:
                                    dialog.close()
                                    return unrestrict_data['download']
                        dialog.close()
                        break
                    
                    elif status in ['error', 'dead', 'virus', 'magnet_error']:
                        xbmc.log(f'[Tinklepad] RD: Remote download failed with status: {status}', xbmc.LOGWARNING)
                        dialog.close()
                        return None
                    
                    elif status == 'queued' or status == 'downloading':
                        # Still in progress
                        pass
                    
                    xbmc.sleep(3000)  # Poll every 3 seconds
                
                dialog.close()
                xbmc.log('[Tinklepad] RD: Remote download timed out', xbmc.LOGWARNING)
                
            elif 'error' in add_data:
                xbmc.log(f'[Tinklepad] RD: Failed to add remote download: {add_data["error"]}', xbmc.LOGWARNING)
                
        except Exception as e:
            xbmc.log(f'[Tinklepad] RD: Remote download fallback error: {e}', xbmc.LOGERROR)
        
        return None
    
    # ==================== ALLDEBRID ====================
    def ad_enabled(self):
        """Check if AllDebrid has a valid token"""
        token = self.get_token('ad.token')
        return bool(token and len(token) > 10)
    
    def ad_authorized(self):
        token = self.get_token('ad.token')
        is_auth = bool(token and len(token) > 10)
        xbmc.log(f'[Tinklepad] AD authorized check: {is_auth}', xbmc.LOGINFO)
        return is_auth
    
    def ad_authorize(self):
        """PIN-based authorization for AllDebrid"""
        try:
            xbmc.log('[Tinklepad] AD: Starting authorization...', xbmc.LOGINFO)
            
            # Step 1: Get PIN
            response = requests.get(
                f'{AD_BASE}/pin/get',
                params={'agent': 'Tinklepad'},
                timeout=15
            )
            data = response.json()
            
            if data.get('status') != 'success':
                raise Exception(data.get('error', {}).get('message', 'Unknown error'))
            
            pin_data = data['data']
            pin = pin_data['pin']
            check_url = pin_data['check_url']
            user_url = pin_data['user_url']
            expires_in = pin_data.get('expires_in', 600)
            
            # Show user the PIN
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                'AllDebrid Authorization',
                f'Go to: [COLOR gold]{user_url}[/COLOR]\n\nEnter PIN: [COLOR gold]{pin}[/COLOR]\n\nWaiting for authorization...'
            )
            
            # Step 2: Poll for authorization
            start_time = time.time()
            while time.time() - start_time < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                xbmc.sleep(5000)
                
                try:
                    check_response = requests.get(check_url, params={'agent': 'Tinklepad'}, timeout=15)
                    check_data = check_response.json()
                    
                    if check_data.get('status') == 'success' and check_data.get('data', {}).get('activated'):
                        apikey = check_data['data']['apikey']
                        
                        # Save token to file
                        self.set_token('ad.token', apikey)
                        
                        # Get username
                        username = self._ad_get_username(apikey)
                        if username:
                            self.set_token('ad.username', username)
                        
                        dialog.close()
                        xbmcgui.Dialog().notification('Tinklepad', 'AllDebrid Authorized!', xbmcgui.NOTIFICATION_INFO, 3000)
                        xbmc.log('[Tinklepad] AD: Authorization successful!', xbmc.LOGINFO)
                        return True
                        
                except Exception as e:
                    xbmc.log(f'[Tinklepad] AD poll error: {e}', xbmc.LOGDEBUG)
                    continue
            
            dialog.close()
            xbmcgui.Dialog().notification('Tinklepad', 'Authorization timed out', xbmcgui.NOTIFICATION_ERROR, 3000)
            return False
            
        except Exception as e:
            xbmc.log(f'[Tinklepad] AD auth error: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Tinklepad', f'Auth failed: {e}', xbmcgui.NOTIFICATION_ERROR, 3000)
            return False
    
    def _ad_get_username(self, token=None):
        """Fetch AD username"""
        try:
            if not token:
                token = self.get_token('ad.token')
            response = requests.get(
                f'{AD_BASE}/user',
                params={'agent': 'Tinklepad', 'apikey': token},
                timeout=10
            )
            data = response.json()
            if data.get('status') == 'success':
                return data['data'].get('username', 'Unknown')
        except Exception as e:
            xbmc.log(f'[Tinklepad] AD: Failed to get username: {e}', xbmc.LOGERROR)
        return None
    
    def ad_resolve(self, url):
        """Resolve a link through AllDebrid"""
        try:
            token = self.get_token('ad.token')
            if not token:
                return None
            
            # Handle magnets
            if url.startswith('magnet:'):
                # Upload magnet
                upload_response = requests.get(
                    f'{AD_BASE}/magnet/upload',
                    params={'agent': 'Tinklepad', 'apikey': token, 'magnets[]': url},
                    timeout=15
                )
                upload_data = upload_response.json()
                
                if upload_data.get('status') == 'success':
                    magnets = upload_data.get('data', {}).get('magnets', [])
                    if magnets:
                        magnet_id = magnets[0].get('id')
                        
                        # Wait for ready
                        for _ in range(30):
                            status_response = requests.get(
                                f'{AD_BASE}/magnet/status',
                                params={'agent': 'Tinklepad', 'apikey': token, 'id': magnet_id},
                                timeout=15
                            )
                            status_data = status_response.json()
                            
                            if status_data.get('status') == 'success':
                                magnet_info = status_data.get('data', {}).get('magnets', {})
                                if magnet_info.get('status') == 'Ready':
                                    links = magnet_info.get('links', [])
                                    if links:
                                        return self.ad_resolve(links[0]['link'])
                                elif magnet_info.get('status') in ['Error']:
                                    break
                            
                            xbmc.sleep(2000)
            else:
                response = requests.get(
                    f'{AD_BASE}/link/unlock',
                    params={'agent': 'Tinklepad', 'apikey': token, 'link': url},
                    timeout=15
                )
                data = response.json()
                
                if data.get('status') == 'success' and 'link' in data.get('data', {}):
                    resolved = data['data']['link']
                    xbmc.log(f'[Tinklepad] AD resolved successfully', xbmc.LOGINFO)
                    return resolved
                elif 'error' in data:
                    xbmc.log(f'[Tinklepad] AD error: {data.get("error")}', xbmc.LOGWARNING)
                    
        except Exception as e:
            xbmc.log(f'[Tinklepad] AD resolve error: {e}', xbmc.LOGERROR)
        return None
    
    # ==================== PREMIUMIZE ====================
    def pm_enabled(self):
        """Check if Premiumize has a valid token"""
        token = self.get_token('pm.token')
        return bool(token and len(token) > 10)
    
    def pm_authorized(self):
        token = self.get_token('pm.token')
        is_auth = bool(token and len(token) > 10)
        xbmc.log(f'[Tinklepad] PM authorized check: {is_auth}', xbmc.LOGINFO)
        return is_auth
    
    def pm_authorize(self):
        """API key authorization for Premiumize - user enters their API key from premiumize.me/account"""
        try:
            xbmc.log('[Tinklepad] PM: Starting authorization...', xbmc.LOGINFO)
            
            # Ask user for API key
            dialog = xbmcgui.Dialog()
            api_key = dialog.input(
                'Premiumize API Key',
                defaultt='',
                type=xbmcgui.INPUT_ALPHANUM
            )
            
            if not api_key or len(api_key) < 5:
                dialog.notification('Tinklepad', 'No API key entered', xbmcgui.NOTIFICATION_WARNING, 3000)
                return False
            
            # Verify the key works
            progress = xbmcgui.DialogProgress()
            progress.create('Tinklepad', 'Verifying Premiumize API key...')
            
            response = requests.get(
                f'{PM_BASE}/account/info',
                params={'apikey': api_key},
                timeout=10
            )
            data = response.json()
            progress.close()
            
            if data.get('status') == 'success':
                # Save token
                self.set_token('pm.token', api_key)
                
                customer_id = str(data.get('customer_id', 'Unknown'))
                self.set_token('pm.username', customer_id)
                
                premium_until = data.get('premium_until', 0)
                
                xbmcgui.Dialog().notification('Tinklepad', f'Premiumize Authorized! (ID: {customer_id})', xbmcgui.NOTIFICATION_INFO, 3000)
                xbmc.log(f'[Tinklepad] PM: Authorization successful! Customer: {customer_id}', xbmc.LOGINFO)
                return True
            else:
                msg = data.get('message', 'Invalid API key')
                xbmcgui.Dialog().ok('Tinklepad', f'Premiumize authorization failed:\n{msg}\n\nGet your API key from premiumize.me/account')
                xbmc.log(f'[Tinklepad] PM: Auth failed: {msg}', xbmc.LOGWARNING)
                return False
                
        except Exception as e:
            xbmc.log(f'[Tinklepad] PM auth error: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Tinklepad', f'Auth failed: {e}', xbmcgui.NOTIFICATION_ERROR, 3000)
            return False
    
    def _pm_get_username(self, token=None):
        """Fetch PM username"""
        try:
            if not token:
                token = self.get_token('pm.token')
            response = requests.get(
                f'{PM_BASE}/account/info',
                params={'apikey': token},
                timeout=10
            )
            data = response.json()
            if data.get('status') == 'success':
                return str(data.get('customer_id', 'Unknown'))
        except Exception as e:
            xbmc.log(f'[Tinklepad] PM: Failed to get username: {e}', xbmc.LOGERROR)
        return None
    
    def pm_resolve(self, url):
        """Resolve a link through Premiumize"""
        try:
            token = self.get_token('pm.token')
            if not token:
                return None
            
            response = requests.post(
                f'{PM_BASE}/transfer/directdl',
                data={'apikey': token, 'src': url},
                timeout=30
            )
            data = response.json()
            
            if data.get('status') == 'success':
                content = data.get('content', [])
                if content:
                    # Get the best quality link
                    best = max(content, key=lambda x: x.get('size', 0))
                    resolved = best.get('link')
                    if resolved:
                        xbmc.log(f'[Tinklepad] PM resolved successfully', xbmc.LOGINFO)
                        return resolved
                        
        except Exception as e:
            xbmc.log(f'[Tinklepad] PM resolve error: {e}', xbmc.LOGERROR)
        return None
    
    # ==================== UNIFIED RESOLVER ====================
    def resolve(self, url):
        """Try to resolve URL through available debrid services"""
        xbmc.log(f'[Tinklepad] Resolving URL: {url[:50]}...', xbmc.LOGINFO)
        xbmc.log(f'[Tinklepad] RD enabled: {self.rd_enabled()}, authorized: {self.rd_authorized()}', xbmc.LOGINFO)
        xbmc.log(f'[Tinklepad] AD enabled: {self.ad_enabled()}, authorized: {self.ad_authorized()}', xbmc.LOGINFO)
        xbmc.log(f'[Tinklepad] PM enabled: {self.pm_enabled()}, authorized: {self.pm_authorized()}', xbmc.LOGINFO)
        
        resolved = None
        
        # Try Real-Debrid first
        if self.rd_authorized():
            xbmc.log('[Tinklepad] Trying Real-Debrid...', xbmc.LOGINFO)
            resolved = self.rd_resolve(url)
            if resolved:
                return resolved, 'RD'
        
        # Try AllDebrid
        if self.ad_authorized():
            xbmc.log('[Tinklepad] Trying AllDebrid...', xbmc.LOGINFO)
            resolved = self.ad_resolve(url)
            if resolved:
                return resolved, 'AD'
        
        # Try Premiumize
        if self.pm_authorized():
            xbmc.log('[Tinklepad] Trying Premiumize...', xbmc.LOGINFO)
            resolved = self.pm_resolve(url)
            if resolved:
                return resolved, 'PM'
        
        xbmc.log('[Tinklepad] No debrid service could resolve the URL', xbmc.LOGWARNING)
        return None, None
    
    def get_status(self):
        """Get status of all debrid services"""
        status = []
        
        if self.rd_authorized():
            username = self.get_token('rd.username') or 'OK'
            status.append(f'[COLOR green]RD: {username}[/COLOR]')
        
        if self.ad_authorized():
            username = self.get_token('ad.username') or 'OK'
            status.append(f'[COLOR green]AD: {username}[/COLOR]')
        
        if self.pm_authorized():
            username = self.get_token('pm.username') or 'OK'
            status.append(f'[COLOR green]PM: {username}[/COLOR]')
        
        if not status:
            return '[COLOR yellow]No Debrid Authorized - Go to Tools[/COLOR]'
        
        return ' | '.join(status)


# Global instance
debrid_manager = DebridManager()
