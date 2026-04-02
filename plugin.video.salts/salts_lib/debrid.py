"""
SALTS Library - Debrid Service Integration
Supports Real-Debrid, Premiumize, AllDebrid
Revived by zeus768 for Kodi 21+
Uses native urllib (no external requests module)
"""
import json
import time
import xbmc
import xbmcgui
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote_plus

from . import log_utils

ADDON = xbmcaddon.Addon()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


def _http(url, method='GET', data=None, headers=None, timeout=30):
    """HTTP helper - returns (status_code, parsed_json_or_None)"""
    hdrs = {'User-Agent': UA}
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
    except Exception as e:
        xbmc.log(f'SALTS HTTP error: {e}', xbmc.LOGERROR)
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
    """Real-Debrid API integration"""
    
    BASE_URL = 'https://api.real-debrid.com/rest/1.0'
    OAUTH_URL = 'https://api.real-debrid.com/oauth/v2'
    CLIENT_ID = 'X245A4XAIBGVM'
    
    def __init__(self):
        self.token = ADDON.getSetting('realdebrid_token')
        self.refresh_token = ADDON.getSetting('realdebrid_refresh')
        self.client_id = ADDON.getSetting('realdebrid_client_id') or self.CLIENT_ID
        self.client_secret = ADDON.getSetting('realdebrid_client_secret') or ''
        self.expires = float(ADDON.getSetting('realdebrid_expires') or 0)
    
    def _auth_headers(self):
        return {'Authorization': f'Bearer {self.token}'}
    
    def is_authorized(self):
        """Check if authorized"""
        if not self.token:
            return False
        if time.time() > self.expires - 600:
            return self._refresh_token()
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
                self.refresh_token = result['refresh_token']
                self.expires = time.time() + result.get('expires_in', 86400)
                
                ADDON.setSetting('realdebrid_token', self.token)
                ADDON.setSetting('realdebrid_refresh', self.refresh_token)
                ADDON.setSetting('realdebrid_expires', str(self.expires))
                return True
            else:
                log_utils.log_error(f'RD refresh failed: status={status}')
        except Exception as e:
            log_utils.log_error(f'Real-Debrid refresh error: {e}')
        return False
    
    def authorize(self):
        """OAuth device authorization flow"""
        try:
            # Step 1: Get device code
            status, result = _get(
                f'{self.OAUTH_URL}/device/code',
                params={'client_id': self.CLIENT_ID, 'new_credentials': 'yes'}
            )
            
            if status != 200 or not isinstance(result, dict):
                xbmcgui.Dialog().notification('Real-Debrid', 'Failed to get device code', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            device_code = result['device_code']
            user_code = result['user_code']
            verification_url = result.get('verification_url', 'https://real-debrid.com/device')
            interval = result.get('interval', 5)
            expires_in = result.get('expires_in', 600)
            
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                'Real-Debrid Authorization',
                f'Go to: {verification_url}\n\nEnter code: {user_code}\n\nWaiting...'
            )
            
            # Step 2: Poll for credentials
            start_time = time.time()
            while time.time() - start_time < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                time.sleep(interval)
                
                cred_status, cred_result = _get(
                    f'{self.OAUTH_URL}/device/credentials',
                    params={'client_id': self.CLIENT_ID, 'code': device_code}
                )
                
                if cred_status == 200 and isinstance(cred_result, dict) and 'client_id' in cred_result:
                    # Step 3: Exchange for tokens
                    token_data = {
                        'client_id': cred_result['client_id'],
                        'client_secret': cred_result['client_secret'],
                        'code': device_code,
                        'grant_type': 'http://oauth.net/grant_type/device/1.0'
                    }
                    
                    tok_status, tok_result = _post(f'{self.OAUTH_URL}/token', data=token_data)
                    
                    if tok_status == 200 and isinstance(tok_result, dict) and 'access_token' in tok_result:
                        self.token = tok_result['access_token']
                        self.refresh_token = tok_result['refresh_token']
                        self.client_id = cred_result['client_id']
                        self.client_secret = cred_result['client_secret']
                        self.expires = time.time() + tok_result.get('expires_in', 86400)
                        
                        ADDON.setSetting('realdebrid_token', self.token)
                        ADDON.setSetting('realdebrid_refresh', self.refresh_token)
                        ADDON.setSetting('realdebrid_client_id', self.client_id)
                        ADDON.setSetting('realdebrid_client_secret', self.client_secret)
                        ADDON.setSetting('realdebrid_expires', str(self.expires))
                        ADDON.setSetting('realdebrid_enabled', 'true')
                        
                        dialog.close()
                        xbmcgui.Dialog().notification('Real-Debrid', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO)
                        return True
            
            dialog.close()
            xbmcgui.Dialog().notification('Real-Debrid', 'Authorization timeout', xbmcgui.NOTIFICATION_ERROR)
            return False
            
        except Exception as e:
            log_utils.log_error(f'Real-Debrid auth error: {e}')
            xbmcgui.Dialog().notification('Real-Debrid', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
            return False
    
    def resolve_magnet(self, magnet):
        """Resolve magnet link to direct download"""
        if not self.is_authorized():
            return None
        
        try:
            # Add magnet
            status, result = _post(
                f'{self.BASE_URL}/torrents/addMagnet',
                data={'magnet': magnet},
                headers=self._auth_headers()
            )
            
            if not isinstance(result, dict) or 'id' not in result:
                log_utils.log_error(f'RD addMagnet failed: {result}')
                return None
            
            torrent_id = result['id']
            
            # Get torrent info
            _, info = _get(f'{self.BASE_URL}/torrents/info/{torrent_id}', headers=self._auth_headers())
            
            if isinstance(info, dict):
                files = info.get('files', [])
                file_ids = ','.join([str(f['id']) for f in files]) if files else 'all'
                
                # Select files
                _post(
                    f'{self.BASE_URL}/torrents/selectFiles/{torrent_id}',
                    data={'files': file_ids},
                    headers=self._auth_headers()
                )
            
            # Wait for ready status
            for _ in range(30):
                _, status_info = _get(
                    f'{self.BASE_URL}/torrents/info/{torrent_id}',
                    headers=self._auth_headers()
                )
                
                if isinstance(status_info, dict) and status_info.get('status') == 'downloaded':
                    links = status_info.get('links', [])
                    if links:
                        _, unrestrict = _post(
                            f'{self.BASE_URL}/unrestrict/link',
                            data={'link': links[0]},
                            headers=self._auth_headers()
                        )
                        if isinstance(unrestrict, dict):
                            return unrestrict.get('download')
                
                time.sleep(1)
            
            return None
            
        except Exception as e:
            log_utils.log_error(f'Real-Debrid resolve error: {e}')
            return None
    
    def check_cache(self, info_hash):
        """Check if torrent is cached"""
        if not self.is_authorized():
            return False
        try:
            _, result = _get(
                f'{self.BASE_URL}/torrents/instantAvailability/{info_hash}',
                headers=self._auth_headers()
            )
            return bool(isinstance(result, dict) and result.get(info_hash, {}).get('rd'))
        except Exception:
            return False


class Premiumize:
    """Premiumize API integration"""
    
    BASE_URL = 'https://www.premiumize.me/api'
    OAUTH_URL = 'https://www.premiumize.me/token'
    CLIENT_ID = '664286978'
    
    def __init__(self):
        self.token = ADDON.getSetting('premiumize_token')
    
    def is_authorized(self):
        return bool(self.token)
    
    def authorize(self):
        """API key authorization"""
        keyboard = xbmc.Keyboard('', 'Enter Premiumize API Key')
        keyboard.doModal()
        
        if keyboard.isConfirmed():
            api_key = keyboard.getText().strip()
            if api_key:
                try:
                    status, result = _get(
                        f'{self.BASE_URL}/account/info',
                        params={'apikey': api_key}
                    )
                    
                    if isinstance(result, dict) and result.get('status') == 'success':
                        self.token = api_key
                        ADDON.setSetting('premiumize_token', api_key)
                        ADDON.setSetting('premiumize_enabled', 'true')
                        xbmcgui.Dialog().notification('Premiumize', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO)
                        return True
                    else:
                        xbmcgui.Dialog().notification('Premiumize', 'Invalid API key', xbmcgui.NOTIFICATION_ERROR)
                except Exception as e:
                    log_utils.log_error(f'Premiumize auth error: {e}')
                    xbmcgui.Dialog().notification('Premiumize', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
        return False
    
    def resolve_magnet(self, magnet):
        """Resolve magnet link to direct download"""
        if not self.is_authorized():
            return None
        
        try:
            # Check cache first
            status, cache_result = _post(
                f'{self.BASE_URL}/cache/check',
                params={'apikey': self.token},
                data={'items[]': magnet}
            )
            
            if isinstance(cache_result, dict) and cache_result.get('status') == 'success':
                responses = cache_result.get('response', [])
                if responses and responses[0]:
                    _, ddl_result = _post(
                        f'{self.BASE_URL}/transfer/directdl',
                        params={'apikey': self.token},
                        data={'src': magnet}
                    )
                    
                    if isinstance(ddl_result, dict) and ddl_result.get('status') == 'success':
                        content = ddl_result.get('content', [])
                        if content:
                            largest = max(content, key=lambda x: x.get('size', 0))
                            return largest.get('link')
            
            return None
            
        except Exception as e:
            log_utils.log_error(f'Premiumize resolve error: {e}')
            return None
    
    def check_cache(self, info_hash):
        if not self.is_authorized():
            return False
        try:
            _, result = _post(
                f'{self.BASE_URL}/cache/check',
                params={'apikey': self.token},
                data={'items[]': info_hash}
            )
            if isinstance(result, dict) and result.get('status') == 'success':
                responses = result.get('response', [])
                return bool(responses and responses[0])
        except Exception:
            pass
        return False


class AllDebrid:
    """AllDebrid API integration"""
    
    BASE_URL = 'https://api.alldebrid.com/v4.1'
    AGENT = 'SALTS'
    
    def __init__(self):
        self.token = ADDON.getSetting('alldebrid_token')
    
    def is_authorized(self):
        return bool(self.token)
    
    def authorize(self):
        """PIN-based authorization"""
        try:
            status, result = _get(
                f'{self.BASE_URL}/pin/get',
                params={'agent': self.AGENT}
            )
            
            if not isinstance(result, dict) or result.get('status') != 'success':
                xbmcgui.Dialog().notification('AllDebrid', 'Failed to get PIN', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            data = result.get('data', {})
            pin = data.get('pin')
            check = data.get('check')
            user_url = data.get('user_url', 'https://alldebrid.com/pin/')
            expires_in = data.get('expires_in', 600)
            
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                'AllDebrid Authorization',
                f'Go to: {user_url}\n\nEnter PIN: {pin}\n\nWaiting...'
            )
            
            start_time = time.time()
            while time.time() - start_time < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                time.sleep(5)
                
                chk_status, chk_result = _get(
                    f'{self.BASE_URL}/pin/check',
                    params={'pin': pin, 'check': check, 'agent': self.AGENT}
                )
                
                if isinstance(chk_result, dict) and chk_result.get('status') == 'success':
                    chk_data = chk_result.get('data', {})
                    if chk_data.get('activated'):
                        self.token = chk_data.get('apikey')
                        ADDON.setSetting('alldebrid_token', self.token)
                        ADDON.setSetting('alldebrid_enabled', 'true')
                        
                        dialog.close()
                        xbmcgui.Dialog().notification('AllDebrid', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO)
                        return True
            
            dialog.close()
            xbmcgui.Dialog().notification('AllDebrid', 'Authorization timeout', xbmcgui.NOTIFICATION_ERROR)
            return False
            
        except Exception as e:
            log_utils.log_error(f'AllDebrid auth error: {e}')
            xbmcgui.Dialog().notification('AllDebrid', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
            return False
    
    def resolve_magnet(self, magnet):
        """Resolve magnet link to direct download"""
        if not self.is_authorized():
            return None
        
        try:
            _, result = _post(
                f'{self.BASE_URL}/magnet/upload',
                params={'agent': self.AGENT, 'apikey': self.token},
                data={'magnets[]': magnet}
            )
            
            if not isinstance(result, dict) or result.get('status') != 'success':
                return None
            
            magnets = result.get('data', {}).get('magnets', [])
            if not magnets:
                return None
            
            magnet_id = magnets[0].get('id')
            if magnets[0].get('ready'):
                _, links_result = _get(
                    f'{self.BASE_URL}/magnet/status',
                    params={'agent': self.AGENT, 'apikey': self.token, 'id': magnet_id}
                )
                
                if isinstance(links_result, dict) and links_result.get('status') == 'success':
                    links = links_result.get('data', {}).get('magnets', {}).get('links', [])
                    if links:
                        _, unlock_result = _get(
                            f'{self.BASE_URL}/link/unlock',
                            params={'agent': self.AGENT, 'apikey': self.token, 'link': links[0].get('link')}
                        )
                        if isinstance(unlock_result, dict) and unlock_result.get('status') == 'success':
                            return unlock_result.get('data', {}).get('link')
            
            return None
            
        except Exception as e:
            log_utils.log_error(f'AllDebrid resolve error: {e}')
            return None
    
    def check_cache(self, info_hash):
        if not self.is_authorized():
            return False
        try:
            _, result = _get(
                f'{self.BASE_URL}/magnet/instant',
                params={'agent': self.AGENT, 'apikey': self.token, 'magnets[]': info_hash}
            )
            if isinstance(result, dict) and result.get('status') == 'success':
                magnets = result.get('data', {}).get('magnets', [])
                return bool(magnets and magnets[0].get('instant'))
        except Exception:
            pass
        return False
