"""
SALTS Library - Debrid Service Integration
Supports Real-Debrid, Premiumize, AllDebrid
Revived by zeus768 for Kodi 21+
"""
import requests
import xbmc
import xbmcgui
import xbmcaddon
import json
import time

from . import log_utils

ADDON = xbmcaddon.Addon()

class RealDebrid:
    """Real-Debrid API integration"""
    
    BASE_URL = 'https://api.real-debrid.com/rest/1.0'
    OAUTH_URL = 'https://api.real-debrid.com/oauth/v2'
    CLIENT_ID = 'X245A4XAIBGVM'  # Open source client ID
    
    def __init__(self):
        self.token = ADDON.getSetting('realdebrid_token')
        self.refresh_token = ADDON.getSetting('realdebrid_refresh')
        self.expires = float(ADDON.getSetting('realdebrid_expires') or 0)
    
    def is_authorized(self):
        """Check if authorized"""
        if not self.token:
            return False
        
        # Check if token needs refresh
        if time.time() > self.expires - 600:  # 10 min buffer
            return self._refresh_token()
        
        return True
    
    def _refresh_token(self):
        """Refresh the access token"""
        if not self.refresh_token:
            return False
        
        try:
            data = {
                'client_id': self.CLIENT_ID,
                'grant_type': 'http://oauth.net/grant_type/device/1.0',
                'code': self.refresh_token
            }
            
            response = requests.post(f'{self.OAUTH_URL}/token', data=data)
            result = response.json()
            
            if 'access_token' in result:
                self.token = result['access_token']
                self.refresh_token = result['refresh_token']
                self.expires = time.time() + result['expires_in']
                
                ADDON.setSetting('realdebrid_token', self.token)
                ADDON.setSetting('realdebrid_refresh', self.refresh_token)
                ADDON.setSetting('realdebrid_expires', str(self.expires))
                
                return True
        except Exception as e:
            log_utils.log_error(f'Real-Debrid refresh error: {e}')
        
        return False
    
    def authorize(self):
        """OAuth device authorization flow"""
        try:
            # Get device code
            response = requests.get(
                f'{self.OAUTH_URL}/device/code',
                params={'client_id': self.CLIENT_ID, 'new_credentials': 'yes'}
            )
            result = response.json()
            
            device_code = result['device_code']
            user_code = result['user_code']
            verification_url = result['verification_url']
            interval = result['interval']
            expires_in = result['expires_in']
            
            # Show dialog with instructions
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                'Real-Debrid Authorization',
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
                    token_response = requests.get(
                        f'{self.OAUTH_URL}/device/credentials',
                        params={'client_id': self.CLIENT_ID, 'code': device_code}
                    )
                    token_result = token_response.json()
                    
                    if 'client_id' in token_result:
                        # Get tokens
                        auth_data = {
                            'client_id': token_result['client_id'],
                            'client_secret': token_result['client_secret'],
                            'code': device_code,
                            'grant_type': 'http://oauth.net/grant_type/device/1.0'
                        }
                        
                        final_response = requests.post(f'{self.OAUTH_URL}/token', data=auth_data)
                        final_result = final_response.json()
                        
                        if 'access_token' in final_result:
                            self.token = final_result['access_token']
                            self.refresh_token = final_result['refresh_token']
                            self.expires = time.time() + final_result['expires_in']
                            
                            ADDON.setSetting('realdebrid_token', self.token)
                            ADDON.setSetting('realdebrid_refresh', self.refresh_token)
                            ADDON.setSetting('realdebrid_expires', str(self.expires))
                            ADDON.setSetting('realdebrid_enabled', 'true')
                            
                            dialog.close()
                            xbmcgui.Dialog().notification('Real-Debrid', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO)
                            return True
                except:
                    pass
            
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
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            # Add magnet
            response = requests.post(
                f'{self.BASE_URL}/torrents/addMagnet',
                headers=headers,
                data={'magnet': magnet}
            )
            result = response.json()
            
            if 'id' not in result:
                return None
            
            torrent_id = result['id']
            
            # Get torrent info
            info_response = requests.get(
                f'{self.BASE_URL}/torrents/info/{torrent_id}',
                headers=headers
            )
            info = info_response.json()
            
            # Select all files
            files = ','.join([str(f['id']) for f in info.get('files', [])])
            requests.post(
                f'{self.BASE_URL}/torrents/selectFiles/{torrent_id}',
                headers=headers,
                data={'files': files or 'all'}
            )
            
            # Wait for download/cached status
            for _ in range(30):
                status_response = requests.get(
                    f'{self.BASE_URL}/torrents/info/{torrent_id}',
                    headers=headers
                )
                status = status_response.json()
                
                if status.get('status') == 'downloaded':
                    links = status.get('links', [])
                    if links:
                        # Unrestrict the link
                        unrestrict_response = requests.post(
                            f'{self.BASE_URL}/unrestrict/link',
                            headers=headers,
                            data={'link': links[0]}
                        )
                        unrestrict = unrestrict_response.json()
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
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.get(
                f'{self.BASE_URL}/torrents/instantAvailability/{info_hash}',
                headers=headers
            )
            result = response.json()
            return bool(result.get(info_hash, {}).get('rd'))
        except:
            return False


class Premiumize:
    """Premiumize API integration"""
    
    BASE_URL = 'https://www.premiumize.me/api'
    OAUTH_URL = 'https://www.premiumize.me/token'
    CLIENT_ID = '664286978'  # Public client ID
    
    def __init__(self):
        self.token = ADDON.getSetting('premiumize_token')
    
    def is_authorized(self):
        """Check if authorized"""
        return bool(self.token)
    
    def authorize(self):
        """API key authorization"""
        keyboard = xbmc.Keyboard('', 'Enter Premiumize API Key')
        keyboard.doModal()
        
        if keyboard.isConfirmed():
            api_key = keyboard.getText()
            if api_key:
                # Verify the key
                try:
                    response = requests.get(
                        f'{self.BASE_URL}/account/info',
                        params={'apikey': api_key}
                    )
                    result = response.json()
                    
                    if result.get('status') == 'success':
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
            cache_response = requests.post(
                f'{self.BASE_URL}/cache/check',
                params={'apikey': self.token},
                data={'items[]': magnet}
            )
            cache_result = cache_response.json()
            
            if cache_result.get('status') == 'success':
                responses = cache_result.get('response', [])
                if responses and responses[0]:
                    # Create direct download link
                    ddl_response = requests.post(
                        f'{self.BASE_URL}/transfer/directdl',
                        params={'apikey': self.token},
                        data={'src': magnet}
                    )
                    ddl_result = ddl_response.json()
                    
                    if ddl_result.get('status') == 'success':
                        content = ddl_result.get('content', [])
                        if content:
                            # Return largest file (likely the video)
                            largest = max(content, key=lambda x: x.get('size', 0))
                            return largest.get('link')
            
            return None
            
        except Exception as e:
            log_utils.log_error(f'Premiumize resolve error: {e}')
            return None
    
    def check_cache(self, info_hash):
        """Check if torrent is cached"""
        if not self.is_authorized():
            return False
        
        try:
            response = requests.post(
                f'{self.BASE_URL}/cache/check',
                params={'apikey': self.token},
                data={'items[]': info_hash}
            )
            result = response.json()
            
            if result.get('status') == 'success':
                responses = result.get('response', [])
                return bool(responses and responses[0])
        except:
            pass
        
        return False


class AllDebrid:
    """AllDebrid API integration"""
    
    BASE_URL = 'https://api.alldebrid.com/v4'
    AGENT = 'SALTS'
    
    def __init__(self):
        self.token = ADDON.getSetting('alldebrid_token')
    
    def is_authorized(self):
        """Check if authorized"""
        return bool(self.token)
    
    def authorize(self):
        """PIN-based authorization"""
        try:
            # Get PIN
            response = requests.get(
                f'{self.BASE_URL}/pin/get',
                params={'agent': self.AGENT}
            )
            result = response.json()
            
            if result.get('status') != 'success':
                return False
            
            data = result.get('data', {})
            pin = data.get('pin')
            check_url = data.get('check')
            user_url = data.get('user_url')
            expires_in = data.get('expires_in', 600)
            
            # Show dialog with instructions
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                'AllDebrid Authorization',
                f'Go to: {user_url}\n\nEnter PIN: {pin}\n\nWaiting for authorization...'
            )
            
            # Poll for authorization
            start_time = time.time()
            while time.time() - start_time < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                time.sleep(5)
                
                try:
                    check_response = requests.get(
                        f'{self.BASE_URL}/pin/check',
                        params={'agent': self.AGENT, 'check': check_url.split('check=')[1]}
                    )
                    check_result = check_response.json()
                    
                    if check_result.get('status') == 'success':
                        check_data = check_result.get('data', {})
                        if check_data.get('activated'):
                            self.token = check_data.get('apikey')
                            ADDON.setSetting('alldebrid_token', self.token)
                            ADDON.setSetting('alldebrid_enabled', 'true')
                            
                            dialog.close()
                            xbmcgui.Dialog().notification('AllDebrid', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO)
                            return True
                except:
                    pass
            
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
            # Add magnet
            response = requests.post(
                f'{self.BASE_URL}/magnet/upload',
                params={'agent': self.AGENT, 'apikey': self.token},
                data={'magnets[]': magnet}
            )
            result = response.json()
            
            if result.get('status') != 'success':
                return None
            
            magnets = result.get('data', {}).get('magnets', [])
            if not magnets:
                return None
            
            magnet_id = magnets[0].get('id')
            if magnets[0].get('ready'):
                # Already cached, get links
                links_response = requests.get(
                    f'{self.BASE_URL}/magnet/status',
                    params={'agent': self.AGENT, 'apikey': self.token, 'id': magnet_id}
                )
                links_result = links_response.json()
                
                if links_result.get('status') == 'success':
                    links = links_result.get('data', {}).get('magnets', {}).get('links', [])
                    if links:
                        # Unlock the link
                        unlock_response = requests.get(
                            f'{self.BASE_URL}/link/unlock',
                            params={
                                'agent': self.AGENT,
                                'apikey': self.token,
                                'link': links[0].get('link')
                            }
                        )
                        unlock_result = unlock_response.json()
                        
                        if unlock_result.get('status') == 'success':
                            return unlock_result.get('data', {}).get('link')
            
            return None
            
        except Exception as e:
            log_utils.log_error(f'AllDebrid resolve error: {e}')
            return None
    
    def check_cache(self, info_hash):
        """Check if torrent is cached"""
        if not self.is_authorized():
            return False
        
        try:
            response = requests.get(
                f'{self.BASE_URL}/magnet/instant',
                params={'agent': self.AGENT, 'apikey': self.token, 'magnets[]': info_hash}
            )
            result = response.json()
            
            if result.get('status') == 'success':
                magnets = result.get('data', {}).get('magnets', [])
                return bool(magnets and magnets[0].get('instant'))
        except:
            pass
        
        return False
