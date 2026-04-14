# -*- coding: utf-8 -*-
"""
Debrid Services Integration for Orion - FIXED VERSION
Based on SALTS debrid implementation for reliable link resolution
Supports: Real-Debrid, Premiumize, AllDebrid, TorBox

FIXES APPLIED:
- Token expiry tracking with proactive refresh
- Proper HTTP request handling with status codes
- Improved is_authorized() checks
- Better error handling and logging
"""

import json
import time
import re
import xbmc
import xbmcgui
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote_plus
from datetime import datetime, timezone

# Get fresh addon instance each time to ensure latest settings
def get_addon():
    return xbmcaddon.Addon()

UA = 'Orion/3.0 (Kodi)'

# Expiry alert threshold (days)
EXPIRY_ALERT_DAYS = 10


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
        xbmc.log(f'Orion HTTP error: {e}', xbmc.LOGERROR)
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


# ==================== Helper: Batch Cache Check ====================

def check_cache_batch(hashes):
    """Check multiple hashes against all enabled debrid services.
    Returns dict: {hash: True/False} for cached status.
    Checks in priority order: RD > PM > AD > TB. 
    A hash is True if ANY service has it cached.
    """
    if not hashes:
        return {}
    
    # Normalize hashes to lowercase
    hashes = [h.lower() for h in hashes]
    result = {h: False for h in hashes}
    addon = get_addon()
    
    # Real-Debrid batch cache check (up to 100 at once)
    if addon.getSetting('rd_enabled') == 'true':
        rd = RealDebrid()
        if rd.is_authorized():
            try:
                hash_str = '/'.join(hashes)
                _, rd_result = _get(
                    f'{rd.BASE_URL}/torrents/instantAvailability/{hash_str}',
                    headers=rd._auth_headers()
                )
                if isinstance(rd_result, dict):
                    for h in hashes:
                        # Check both lowercase and uppercase
                        entry = rd_result.get(h) or rd_result.get(h.upper()) or {}
                        if entry.get('rd'):
                            result[h] = True
            except Exception as e:
                xbmc.log(f'RD batch cache check error: {e}', xbmc.LOGWARNING)
    
    # If all found, return early
    if all(result.values()):
        return result
    
    # Premiumize batch cache check
    uncached = [h for h, v in result.items() if not v]
    if uncached and addon.getSetting('pm_enabled') == 'true':
        pm = Premiumize()
        if pm.is_authorized():
            try:
                # Premiumize accepts items[] for each hash
                items_str = '&'.join(f'items[]={h}' for h in uncached)
                _, pm_result = _post(
                    f'{pm.BASE_URL}/cache/check',
                    params={'apikey': pm.token},
                    data=items_str
                )
                if isinstance(pm_result, dict) and pm_result.get('status') == 'success':
                    responses = pm_result.get('response', [])
                    for i, h in enumerate(uncached):
                        if i < len(responses) and responses[i]:
                            result[h] = True
            except Exception as e:
                xbmc.log(f'PM batch cache check error: {e}', xbmc.LOGWARNING)
    
    if all(result.values()):
        return result
    
    # AllDebrid batch cache check
    uncached = [h for h, v in result.items() if not v]
    if uncached and addon.getSetting('ad_enabled') == 'true':
        ad = AllDebrid()
        if ad.is_authorized():
            try:
                params_str = '&'.join(f'magnets[]={h}' for h in uncached)
                _, ad_result = _get(
                    f'{ad.BASE_URL}/magnet/instant?agent={ad.AGENT}&apikey={ad.token}&{params_str}'
                )
                if isinstance(ad_result, dict) and ad_result.get('status') == 'success':
                    magnets = ad_result.get('data', {}).get('magnets', [])
                    for i, h in enumerate(uncached):
                        if i < len(magnets) and magnets[i].get('instant'):
                            result[h] = True
            except Exception as e:
                xbmc.log(f'AD batch cache check error: {e}', xbmc.LOGWARNING)
    
    if all(result.values()):
        return result
    
    # TorBox batch cache check
    uncached = [h for h, v in result.items() if not v]
    if uncached and addon.getSetting('tb_enabled') == 'true':
        tb = TorBox()
        if tb.is_authorized():
            try:
                hash_csv = ','.join(uncached)
                _, tb_result = _get(
                    f'{tb.BASE_URL}/torrents/checkcached',
                    params={'hash': hash_csv, 'format': 'list'},
                    headers=tb._auth_headers()
                )
                if isinstance(tb_result, dict) and tb_result.get('success'):
                    cached_data = tb_result.get('data', [])
                    if isinstance(cached_data, list):
                        for item in cached_data:
                            h = (item.get('hash', '') if isinstance(item, dict) else str(item)).lower()
                            if h in result:
                                result[h] = True
                    elif isinstance(cached_data, dict):
                        for h in uncached:
                            if cached_data.get(h):
                                result[h] = True
            except Exception as e:
                xbmc.log(f'TB batch cache check error: {e}', xbmc.LOGWARNING)
    
    return result


class RealDebrid:
    """Real-Debrid API integration - SALTS-style implementation"""
    
    BASE_URL = 'https://api.real-debrid.com/rest/1.0'
    OAUTH_URL = 'https://api.real-debrid.com/oauth/v2'
    CLIENT_ID = 'X245A4XAIBGVM'
    
    def __init__(self):
        addon = get_addon()
        self.token = addon.getSetting('rd_token')
        self.refresh_token = addon.getSetting('rd_refresh')
        self.client_id = addon.getSetting('rd_client_id') or self.CLIENT_ID
        self.client_secret = addon.getSetting('rd_client_secret') or ''
        self.expires = float(addon.getSetting('rd_expires') or 0)
        
        xbmc.log(f"RealDebrid init: token={'SET' if self.token else 'EMPTY'}, "
                 f"expires={self.expires}, now={time.time()}", xbmc.LOGDEBUG)
    
    def _auth_headers(self):
        return {'Authorization': f'Bearer {self.token}'}
    
    def is_authorized(self):
        """Check if authorized - proactively refresh token if expiring soon"""
        if not self.token:
            return False
        # Refresh token 10 minutes before expiry (SALTS approach)
        if self.expires > 0 and time.time() > self.expires - 600:
            xbmc.log("RealDebrid: Token expiring soon, attempting refresh...", xbmc.LOGINFO)
            return self._refresh_token()
        return True
    
    def _refresh_token(self):
        """Refresh the access token using refresh token"""
        if not self.refresh_token or not self.client_secret:
            xbmc.log("RealDebrid: Cannot refresh - missing refresh_token or client_secret", xbmc.LOGWARNING)
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
                
                addon = get_addon()
                addon.setSetting('rd_token', self.token)
                addon.setSetting('rd_refresh', self.refresh_token)
                addon.setSetting('rd_expires', str(self.expires))
                
                xbmc.log("RealDebrid: Token refreshed successfully!", xbmc.LOGINFO)
                return True
            else:
                xbmc.log(f"RealDebrid: Token refresh failed: {result}", xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log(f'Real-Debrid refresh error: {e}', xbmc.LOGERROR)
        return False
    
    def pair(self):
        """Start device pairing - authorize with Real-Debrid"""
        try:
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
                f'Go to: [COLOR cyan]{verification_url}[/COLOR]\n\n'
                f'Enter code: [COLOR yellow]{user_code}[/COLOR]\n\n'
                'Waiting for authorization...'
            )
            
            start_time = time.time()
            while time.time() - start_time < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                elapsed = time.time() - start_time
                dialog.update(int((elapsed / expires_in) * 100))
                
                time.sleep(interval)
                
                cred_status, cred_result = _get(
                    f'{self.OAUTH_URL}/device/credentials',
                    params={'client_id': self.CLIENT_ID, 'code': device_code}
                )
                
                if cred_status == 200 and isinstance(cred_result, dict) and 'client_id' in cred_result:
                    token_data = {
                        'client_id': cred_result['client_id'],
                        'client_secret': cred_result['client_secret'],
                        'code': device_code,
                        'grant_type': 'http://oauth.net/grant_type/device/1.0'
                    }
                    
                    tok_status, tok_result = _post(f'{self.OAUTH_URL}/token', data=token_data)
                    
                    if tok_status == 200 and isinstance(tok_result, dict) and 'access_token' in tok_result:
                        self.token = tok_result['access_token']
                        self.refresh_token = tok_result.get('refresh_token', '')
                        self.client_id = cred_result['client_id']
                        self.client_secret = cred_result['client_secret']
                        self.expires = time.time() + tok_result.get('expires_in', 86400)
                        
                        addon = get_addon()
                        addon.setSetting('rd_token', self.token)
                        addon.setSetting('rd_refresh', self.refresh_token)
                        addon.setSetting('rd_client_id', self.client_id)
                        addon.setSetting('rd_client_secret', self.client_secret)
                        addon.setSetting('rd_expires', str(self.expires))
                        addon.setSetting('rd_enabled', 'true')
                        
                        dialog.close()
                        xbmcgui.Dialog().notification('Real-Debrid', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO)
                        return True
            
            dialog.close()
            xbmcgui.Dialog().notification('Real-Debrid', 'Authorization timeout', xbmcgui.NOTIFICATION_ERROR)
            return False
            
        except Exception as e:
            xbmc.log(f'Real-Debrid auth error: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Real-Debrid', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
            return False
    
    def get_account_info(self):
        """Get Real-Debrid account information"""
        if not self.is_authorized():
            return None
        
        status, data = _get(f'{self.BASE_URL}/user', headers=self._auth_headers())
        
        if status != 200 or not isinstance(data, dict) or 'error' in data:
            xbmc.log(f"RealDebrid: get_account_info error: {data}", xbmc.LOGWARNING)
            return None
        
        # Parse expiration date
        expiration = data.get('expiration', '')
        days_left = 0
        expiry_date = ''
        
        if expiration:
            try:
                exp_dt = datetime.fromisoformat(expiration.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                days_left = (exp_dt - now).days
                expiry_date = exp_dt.strftime('%Y-%m-%d')
            except:
                expiry_date = expiration[:10] if len(expiration) >= 10 else expiration
        
        return {
            'service': 'Real-Debrid',
            'username': data.get('username', 'Unknown'),
            'email': data.get('email', ''),
            'premium': data.get('type') == 'premium',
            'expiry_date': expiry_date,
            'days_left': days_left,
            'points': data.get('points', 0),
            'status': 'Premium' if data.get('type') == 'premium' else 'Free'
        }
    
    def resolve_magnet(self, magnet, progress=None):
        """Resolve magnet to stream URL - SALTS-style implementation"""
        if not self.is_authorized():
            xbmc.log("RealDebrid: Not authorized for resolve_magnet", xbmc.LOGWARNING)
            return None
        
        VIDEO_EXTS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.mpg', '.mpeg', '.ts', '.webm')
        
        try:
            # Step 1: Add magnet
            status, result = _post(
                f'{self.BASE_URL}/torrents/addMagnet',
                data={'magnet': magnet},
                headers=self._auth_headers()
            )
            
            if not isinstance(result, dict) or 'id' not in result:
                xbmc.log(f"RealDebrid: addMagnet failed: {result}", xbmc.LOGWARNING)
                return None
            
            torrent_id = result['id']
            xbmc.log(f"RealDebrid: Added magnet, torrent_id={torrent_id}", xbmc.LOGINFO)
            
            # Step 2: Get torrent info and select video files
            _, info = _get(f'{self.BASE_URL}/torrents/info/{torrent_id}', headers=self._auth_headers())
            
            if isinstance(info, dict):
                files = info.get('files', [])
                # Select only video files
                video_ids = [str(f['id']) for f in files if f.get('path', '').lower().endswith(VIDEO_EXTS)]
                file_ids = ','.join(video_ids) if video_ids else 'all'
                
                _post(
                    f'{self.BASE_URL}/torrents/selectFiles/{torrent_id}',
                    data={'files': file_ids},
                    headers=self._auth_headers()
                )
            
            # Step 3: Wait for torrent to be ready
            for i in range(60):
                if progress:
                    progress.update(30 + i, 'Processing torrent...')
                
                _, status_info = _get(
                    f'{self.BASE_URL}/torrents/info/{torrent_id}',
                    headers=self._auth_headers()
                )
                
                if isinstance(status_info, dict):
                    torrent_status = status_info.get('status')
                    xbmc.log(f"RealDebrid: Torrent status: {torrent_status}", xbmc.LOGDEBUG)
                    
                    if torrent_status == 'downloaded':
                        links = status_info.get('links', [])
                        if links:
                            # Try each link, skip archives
                            for link in links:
                                _, unrestrict = _post(
                                    f'{self.BASE_URL}/unrestrict/link',
                                    data={'link': link},
                                    headers=self._auth_headers()
                                )
                                if isinstance(unrestrict, dict):
                                    dl_url = unrestrict.get('download', '')
                                    if dl_url:
                                        url_lower = dl_url.lower().split('?')[0]
                                        if url_lower.endswith(('.rar', '.zip', '.7z', '.nfo', '.txt', '.srt')):
                                            xbmc.log(f'RealDebrid: Skipping non-video: {dl_url[:80]}', xbmc.LOGINFO)
                                            continue
                                        xbmc.log(f"RealDebrid: Resolved successfully", xbmc.LOGINFO)
                                        return dl_url
                            
                            # Last resort: return first link anyway
                            if links:
                                _, unrestrict = _post(
                                    f'{self.BASE_URL}/unrestrict/link',
                                    data={'link': links[0]},
                                    headers=self._auth_headers()
                                )
                                if isinstance(unrestrict, dict):
                                    return unrestrict.get('download')
                    
                    elif torrent_status in ['error', 'dead', 'magnet_error']:
                        xbmc.log(f"RealDebrid: Torrent failed with status: {torrent_status}", xbmc.LOGWARNING)
                        return None
                
                time.sleep(2)
            
            xbmc.log("RealDebrid: Timeout waiting for torrent", xbmc.LOGWARNING)
            return None
            
        except Exception as e:
            xbmc.log(f'Real-Debrid resolve error: {e}', xbmc.LOGERROR)
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
            return bool(isinstance(result, dict) and (result.get(info_hash, {}).get('rd') or result.get(info_hash.upper(), {}).get('rd')))
        except Exception:
            return False
    
    def unrestrict_link(self, link):
        """Unrestrict a link for streaming"""
        if not self.is_authorized():
            return None
        
        _, data = _post(
            f'{self.BASE_URL}/unrestrict/link',
            data={'link': link},
            headers=self._auth_headers()
        )
        
        if isinstance(data, dict):
            return data.get('download')
        return None


class Premiumize:
    """Premiumize API integration - SALTS-style implementation"""
    
    BASE_URL = 'https://www.premiumize.me/api'
    
    def __init__(self):
        addon = get_addon()
        self.token = addon.getSetting('pm_token')
        xbmc.log(f"Premiumize init: token={'SET' if self.token else 'EMPTY'}", xbmc.LOGDEBUG)
    
    def is_authorized(self):
        return bool(self.token)
    
    def pair(self):
        """API key authorization for Premiumize"""
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
                        addon = get_addon()
                        addon.setSetting('pm_token', api_key)
                        addon.setSetting('pm_enabled', 'true')
                        xbmcgui.Dialog().notification('Premiumize', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO)
                        return True
                    else:
                        xbmcgui.Dialog().notification('Premiumize', 'Invalid API key', xbmcgui.NOTIFICATION_ERROR)
                except Exception as e:
                    xbmc.log(f'Premiumize auth error: {e}', xbmc.LOGERROR)
                    xbmcgui.Dialog().notification('Premiumize', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
        return False
    
    def get_account_info(self):
        """Get Premiumize account information"""
        if not self.is_authorized():
            return None
        
        _, data = _post(f'{self.BASE_URL}/account/info', params={'apikey': self.token})
        
        if not isinstance(data, dict) or data.get('status') != 'success':
            return None
        
        # Parse expiration date
        premium_until = data.get('premium_until', 0)
        days_left = 0
        expiry_date = ''
        
        if premium_until:
            try:
                exp_dt = datetime.fromtimestamp(premium_until, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                days_left = (exp_dt - now).days
                expiry_date = exp_dt.strftime('%Y-%m-%d')
            except:
                pass
        
        return {
            'service': 'Premiumize',
            'username': data.get('customer_id', 'Unknown'),
            'email': '',
            'premium': premium_until > time.time(),
            'expiry_date': expiry_date,
            'days_left': days_left,
            'points': data.get('limit_used', 0),
            'space_used': data.get('space_used', 0),
            'status': 'Premium' if premium_until > time.time() else 'Free'
        }
    
    def resolve_magnet(self, magnet, progress=None):
        """Resolve magnet to stream URL"""
        if not self.is_authorized():
            return None
        
        try:
            # Check cache and use directdl
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
                            # Find largest video file
                            videos = [f for f in content if f.get('link') or f.get('stream_link')]
                            if videos:
                                largest = max(videos, key=lambda x: x.get('size', 0))
                                return largest.get('stream_link') or largest.get('link')
            
            return None
            
        except Exception as e:
            xbmc.log(f'Premiumize resolve error: {e}', xbmc.LOGERROR)
            return None
    
    def check_cache(self, info_hash):
        """Check if torrent is cached"""
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
    """AllDebrid API integration - SALTS-style implementation"""
    
    BASE_URL = 'https://api.alldebrid.com/v4'
    AGENT = 'Orion'
    
    def __init__(self):
        addon = get_addon()
        self.token = addon.getSetting('ad_token')
        xbmc.log(f"AllDebrid init: token={'SET' if self.token else 'EMPTY'}", xbmc.LOGDEBUG)
    
    def is_authorized(self):
        return bool(self.token)
    
    def pair(self):
        """PIN pairing for AllDebrid"""
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
                f'Go to: [COLOR cyan]{user_url}[/COLOR]\n\n'
                f'Enter PIN: [COLOR yellow]{pin}[/COLOR]\n\n'
                'Waiting for authorization...'
            )
            
            start_time = time.time()
            while time.time() - start_time < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False
                
                elapsed = time.time() - start_time
                dialog.update(int((elapsed / expires_in) * 100))
                
                time.sleep(5)
                
                chk_status, chk_result = _get(
                    f'{self.BASE_URL}/pin/check',
                    params={'pin': pin, 'check': check, 'agent': self.AGENT}
                )
                
                if isinstance(chk_result, dict) and chk_result.get('status') == 'success':
                    chk_data = chk_result.get('data', {})
                    if chk_data.get('activated'):
                        self.token = chk_data.get('apikey')
                        addon = get_addon()
                        addon.setSetting('ad_token', self.token)
                        addon.setSetting('ad_enabled', 'true')
                        
                        dialog.close()
                        xbmcgui.Dialog().notification('AllDebrid', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO)
                        return True
            
            dialog.close()
            xbmcgui.Dialog().notification('AllDebrid', 'Authorization timeout', xbmcgui.NOTIFICATION_ERROR)
            return False
            
        except Exception as e:
            xbmc.log(f'AllDebrid auth error: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('AllDebrid', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
            return False
    
    def get_account_info(self):
        """Get AllDebrid account information"""
        if not self.is_authorized():
            return None
        
        _, data = _get(
            f'{self.BASE_URL}/user',
            params={'agent': self.AGENT, 'apikey': self.token}
        )
        
        if not isinstance(data, dict) or data.get('status') != 'success':
            return None
        
        user_data = data.get('data', {}).get('user', {})
        
        # Parse expiration date
        premium_until = user_data.get('premiumUntil', 0)
        days_left = 0
        expiry_date = ''
        
        if premium_until:
            try:
                exp_dt = datetime.fromtimestamp(premium_until, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                days_left = (exp_dt - now).days
                expiry_date = exp_dt.strftime('%Y-%m-%d')
            except:
                pass
        
        return {
            'service': 'AllDebrid',
            'username': user_data.get('username', 'Unknown'),
            'email': user_data.get('email', ''),
            'premium': user_data.get('isPremium', False),
            'expiry_date': expiry_date,
            'days_left': days_left,
            'points': user_data.get('fidelityPoints', 0),
            'status': 'Premium' if user_data.get('isPremium', False) else 'Free'
        }
    
    def resolve_magnet(self, magnet, progress=None):
        """Resolve magnet to stream URL - SALTS-style"""
        if not self.is_authorized():
            return None
        
        try:
            _, result = _post(
                f'{self.BASE_URL}/magnet/upload',
                params={'agent': self.AGENT, 'apikey': self.token},
                data={'magnets[]': magnet}
            )
            
            if not isinstance(result, dict) or result.get('status') != 'success':
                xbmc.log(f"AllDebrid: magnet/upload failed: {result}", xbmc.LOGWARNING)
                return None
            
            magnets = result.get('data', {}).get('magnets', [])
            if not magnets:
                return None
            
            magnet_id = magnets[0].get('id')
            
            # Check if already ready
            if magnets[0].get('ready'):
                _, links_result = _get(
                    f'{self.BASE_URL}/magnet/status',
                    params={'agent': self.AGENT, 'apikey': self.token, 'id': magnet_id}
                )
                
                if isinstance(links_result, dict) and links_result.get('status') == 'success':
                    magnet_data = links_result.get('data', {}).get('magnets', {})
                    files = magnet_data.get('files', [])
                    
                    if files:
                        # Find largest video file
                        sources = []
                        for f in files:
                            for e in f.get('e') or [f]:
                                name = (e.get('n') or '').lower()
                                if any(name.endswith(x) for x in ['.mp4', '.mkv', '.avi', '.mov', '.wmv']):
                                    sources.append((e.get('s', 0), e.get('l', '')))
                        
                        if sources:
                            url = max(sources)[1]
                            
                            # Unlock the link
                            _, unlock_result = _get(
                                f'{self.BASE_URL}/link/unlock',
                                params={'agent': self.AGENT, 'apikey': self.token, 'link': url}
                            )
                            
                            if isinstance(unlock_result, dict) and unlock_result.get('status') == 'success':
                                stream_url = unlock_result.get('data', {}).get('link')
                                if stream_url:
                                    xbmc.log("AllDebrid: Resolved successfully", xbmc.LOGINFO)
                                    return stream_url
            
            return None
            
        except Exception as e:
            xbmc.log(f'AllDebrid resolve error: {e}', xbmc.LOGERROR)
            return None
    
    def check_cache(self, info_hash):
        """Check if torrent is cached"""
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


class TorBox:
    """TorBox API integration (https://api.torbox.app) - SALTS-style"""
    
    BASE_URL = 'https://api.torbox.app/v1/api'
    
    def __init__(self):
        addon = get_addon()
        self.token = addon.getSetting('tb_token')
        xbmc.log(f"TorBox init: token={'SET' if self.token else 'EMPTY'}", xbmc.LOGDEBUG)
    
    def _auth_headers(self):
        return {'Authorization': f'Bearer {self.token}'}
    
    def is_authorized(self):
        return bool(self.token)
    
    def pair(self):
        """API key authorization for TorBox"""
        keyboard = xbmc.Keyboard('', 'Enter TorBox API Key')
        keyboard.doModal()
        
        if keyboard.isConfirmed():
            api_key = keyboard.getText().strip()
            if api_key:
                try:
                    # Verify the key by calling /user/me
                    status, result = _get(
                        f'{self.BASE_URL}/user/me',
                        headers={'Authorization': f'Bearer {api_key}'}
                    )
                    
                    if isinstance(result, dict) and result.get('success'):
                        self.token = api_key
                        addon = get_addon()
                        addon.setSetting('tb_token', api_key)
                        addon.setSetting('tb_enabled', 'true')
                        
                        user_data = result.get('data', {})
                        plan = user_data.get('plan', 'Unknown')
                        xbmcgui.Dialog().notification(
                            'TorBox',
                            f'Authorized! Plan: {plan}',
                            xbmcgui.NOTIFICATION_INFO
                        )
                        return True
                    else:
                        xbmcgui.Dialog().notification('TorBox', 'Invalid API key', xbmcgui.NOTIFICATION_ERROR)
                except Exception as e:
                    xbmc.log(f'TorBox auth error: {e}', xbmc.LOGERROR)
                    xbmcgui.Dialog().notification('TorBox', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
        return False
    
    def get_account_info(self):
        """Get TorBox account information"""
        if not self.is_authorized():
            return None
        
        _, result = _get(f'{self.BASE_URL}/user/me', headers=self._auth_headers())
        
        if not isinstance(result, dict) or not result.get('success'):
            return None
        
        user_data = result.get('data', {})
        
        # Parse expiration date
        premium_expires = user_data.get('premium_expires_at', '')
        days_left = 0
        expiry_date = ''
        
        if premium_expires:
            try:
                exp_dt = datetime.fromisoformat(premium_expires.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                days_left = (exp_dt - now).days
                expiry_date = exp_dt.strftime('%Y-%m-%d')
            except:
                expiry_date = premium_expires[:10] if len(premium_expires) >= 10 else premium_expires
        
        plan = user_data.get('plan', 0)
        plan_names = {0: 'Free', 1: 'Essential', 2: 'Pro', 3: 'Standard'}
        
        return {
            'service': 'TorBox',
            'username': user_data.get('email', 'Unknown'),
            'email': user_data.get('email', ''),
            'premium': plan > 0,
            'expiry_date': expiry_date,
            'days_left': days_left,
            'points': 0,
            'plan': plan_names.get(plan, f'Plan {plan}'),
            'status': plan_names.get(plan, f'Plan {plan}')
        }
    
    def resolve_magnet(self, magnet, progress=None):
        """Resolve magnet link to direct download via TorBox - SALTS-style"""
        if not self.is_authorized():
            return None
        
        try:
            # Extract hash from magnet
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
            if not hash_match:
                hash_match = re.search(r'btih:([a-zA-Z2-7]{32})', magnet)
            
            # Step 1: Create torrent (add magnet) using multipart form
            boundary = '----OrionBoundary'
            body_parts = []
            body_parts.append(f'--{boundary}')
            body_parts.append('Content-Disposition: form-data; name="magnet"')
            body_parts.append('')
            body_parts.append(magnet)
            body_parts.append(f'--{boundary}--')
            body_data = '\r\n'.join(body_parts).encode('utf-8')
            
            create_headers = self._auth_headers()
            create_headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
            
            status, result = _http(
                f'{self.BASE_URL}/torrents/createtorrent',
                method='POST',
                data=body_data,
                headers=create_headers
            )
            
            if not isinstance(result, dict) or not result.get('success'):
                xbmc.log(f'TorBox createtorrent failed: {result}', xbmc.LOGERROR)
                return None
            
            torrent_id = result.get('data', {}).get('torrent_id')
            if not torrent_id:
                return None
            
            # Step 2: Wait for ready and get file list
            for _ in range(30):
                if progress:
                    progress.update(50, 'Waiting for TorBox...')
                
                _, info_result = _get(
                    f'{self.BASE_URL}/torrents/mylist',
                    params={'id': torrent_id},
                    headers=self._auth_headers()
                )
                
                if isinstance(info_result, dict) and info_result.get('success'):
                    torrent_data = info_result.get('data', {})
                    dl_state = torrent_data.get('download_state', '')
                    
                    if dl_state in ('completed', 'cached', 'downloading'):
                        files = torrent_data.get('files', [])
                        if files:
                            # Pick largest file (video)
                            largest = max(files, key=lambda f: f.get('size', 0))
                            file_id = largest.get('id', 0)
                            
                            # Step 3: Request download link
                            _, dl_result = _get(
                                f'{self.BASE_URL}/torrents/requestdl',
                                params={
                                    'token': self.token,
                                    'torrent_id': torrent_id,
                                    'file_id': file_id
                                },
                                headers=self._auth_headers()
                            )
                            
                            if isinstance(dl_result, dict) and dl_result.get('success'):
                                download_url = dl_result.get('data')
                                if download_url:
                                    xbmc.log("TorBox: Resolved successfully", xbmc.LOGINFO)
                                    return download_url
                        break
                    elif dl_state in ('error', 'stalled'):
                        return None
                
                time.sleep(2)
            
            return None
            
        except Exception as e:
            xbmc.log(f'TorBox resolve error: {e}', xbmc.LOGERROR)
            return None
    
    def check_cache(self, info_hash):
        """Check if torrent is cached on TorBox"""
        if not self.is_authorized():
            return False
        try:
            _, result = _get(
                f'{self.BASE_URL}/torrents/checkcached',
                params={'hash': info_hash, 'format': 'list'},
                headers=self._auth_headers()
            )
            if isinstance(result, dict) and result.get('success'):
                cached_data = result.get('data', [])
                return bool(cached_data)
        except Exception:
            pass
        return False


# ==================== Helper Functions ====================

def get_all_account_info():
    """Get account information for all authorized debrid services"""
    accounts = []
    addon = get_addon()
    
    # Check Real-Debrid
    if addon.getSetting('rd_token'):
        rd = RealDebrid()
        info = rd.get_account_info()
        if info:
            accounts.append(info)
    
    # Check Premiumize
    if addon.getSetting('pm_token'):
        pm = Premiumize()
        info = pm.get_account_info()
        if info:
            accounts.append(info)
    
    # Check AllDebrid
    if addon.getSetting('ad_token'):
        ad = AllDebrid()
        info = ad.get_account_info()
        if info:
            accounts.append(info)
    
    # Check TorBox
    if addon.getSetting('tb_token'):
        tb = TorBox()
        info = tb.get_account_info()
        if info:
            accounts.append(info)
    
    return accounts


def check_expiry_alerts():
    """Check for expiring accounts and show alerts"""
    accounts = get_all_account_info()
    addon = get_addon()
    
    for account in accounts:
        days_left = account.get('days_left', 999)
        service = account.get('service', 'Unknown')
        
        # Only alert for premium accounts within 10 days of expiry
        if account.get('premium', False) and 0 < days_left <= EXPIRY_ALERT_DAYS:
            # Check if we already showed alert today
            alert_key = f'{service.lower().replace("-", "_")}_last_expiry_alert'
            last_alert = addon.getSetting(alert_key)
            today = datetime.now().strftime('%Y-%m-%d')
            
            if last_alert != today:
                addon.setSetting(alert_key, today)
                
                if days_left == 1:
                    msg = f'[COLOR red]EXPIRES TOMORROW![/COLOR]'
                else:
                    msg = f'[COLOR orange]Expires in {days_left} days[/COLOR]'
                
                xbmcgui.Dialog().notification(
                    f'{service} Expiring',
                    msg,
                    xbmcgui.NOTIFICATION_WARNING,
                    5000
                )


def get_debrid_status_summary():
    """Get a summary of all debrid service statuses"""
    services = []
    addon = get_addon()
    
    # Real-Debrid
    rd_token = addon.getSetting('rd_token')
    rd_enabled = addon.getSetting('rd_enabled') == 'true'
    if rd_token:
        services.append({
            'name': 'Real-Debrid',
            'key': 'rd',
            'authorized': True,
            'enabled': rd_enabled,
            'status': '[COLOR lime]Authorized[/COLOR]' if rd_enabled else '[COLOR yellow]Authorized (Disabled)[/COLOR]'
        })
    else:
        services.append({
            'name': 'Real-Debrid',
            'key': 'rd',
            'authorized': False,
            'enabled': False,
            'status': '[COLOR red]Not Authorized[/COLOR]'
        })
    
    # Premiumize
    pm_token = addon.getSetting('pm_token')
    pm_enabled = addon.getSetting('pm_enabled') == 'true'
    if pm_token:
        services.append({
            'name': 'Premiumize',
            'key': 'pm',
            'authorized': True,
            'enabled': pm_enabled,
            'status': '[COLOR lime]Authorized[/COLOR]' if pm_enabled else '[COLOR yellow]Authorized (Disabled)[/COLOR]'
        })
    else:
        services.append({
            'name': 'Premiumize',
            'key': 'pm',
            'authorized': False,
            'enabled': False,
            'status': '[COLOR red]Not Authorized[/COLOR]'
        })
    
    # AllDebrid
    ad_token = addon.getSetting('ad_token')
    ad_enabled = addon.getSetting('ad_enabled') == 'true'
    if ad_token:
        services.append({
            'name': 'AllDebrid',
            'key': 'ad',
            'authorized': True,
            'enabled': ad_enabled,
            'status': '[COLOR lime]Authorized[/COLOR]' if ad_enabled else '[COLOR yellow]Authorized (Disabled)[/COLOR]'
        })
    else:
        services.append({
            'name': 'AllDebrid',
            'key': 'ad',
            'authorized': False,
            'enabled': False,
            'status': '[COLOR red]Not Authorized[/COLOR]'
        })
    
    # TorBox
    tb_token = addon.getSetting('tb_token')
    tb_enabled = addon.getSetting('tb_enabled') == 'true'
    if tb_token:
        services.append({
            'name': 'TorBox',
            'key': 'tb',
            'authorized': True,
            'enabled': tb_enabled,
            'status': '[COLOR lime]Authorized[/COLOR]' if tb_enabled else '[COLOR yellow]Authorized (Disabled)[/COLOR]'
        })
    else:
        services.append({
            'name': 'TorBox',
            'key': 'tb',
            'authorized': False,
            'enabled': False,
            'status': '[COLOR red]Not Authorized[/COLOR]'
        })
    
    return services
