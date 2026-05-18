"""
SALTS Library - Debrid Service Integration
Supports Real-Debrid, Premiumize, AllDebrid, TorBox
Revived by zeus768 for Kodi 21+
Uses native urllib (no external requests module)
"""
import json
import time
import re
import os
import ssl
import threading
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote_plus
from datetime import datetime

from . import log_utils

ADDON = xbmcaddon.Addon()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# ---------- Common helpers used by debrid resolvers ----------

_VIDEO_EXTS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v',
               '.mpg', '.mpeg', '.ts', '.webm', '.m2ts', '.iso', '.vob')

_EXTRAS_KEYWORDS = (
    'sample', 'trailer', 'rarbg.com', 'rarbg.to',
    'extras', 'featurette', 'behind.the.scenes',
    'deleted.scene', 'bloopers', 'outtakes', 'interview',
    'making.of', 'screener'
)


def _seas_ep_filter(season, episode, name):
    """Return True if filename matches the requested season/episode.

    Mirrors the canonical S01E01 / 1x01 / season.1.episode.1 patterns.
    """
    try:
        if not season or not episode:
            return False
        s = int(season)
        e = int(episode)
        n = name.lower().replace(' ', '.').replace('_', '.').replace('-', '.')
        patterns = (
            r's%02de%02d' % (s, e),
            r's%de%d' % (s, e),
            r'%dx%02d' % (s, e),
            r'%dx%d' % (s, e),
            r'season.?%d.?episode.?%d' % (s, e),
            r'season.?%02d.?episode.?%02d' % (s, e),
            r'\.%02d\.' % e if s == 1 else None,
        )
        for p in patterns:
            if not p:
                continue
            if re.search(p, n):
                return True
        return False
    except Exception:
        return False


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


# ==================== Helper: Batch Cache Check ====================

def check_cache_batch(hashes):
    """Check multiple hashes against all enabled debrid services.
    Returns dict: {hash: True/False} for cached status.
    Checks in priority order: RD > PM > AD > TB. 
    A hash is True if ANY service has it cached.
    """
    if not hashes:
        return {}
    
    result = {h: False for h in hashes}
    
    # Real-Debrid batch cache check (up to 100 at once)
    if ADDON.getSetting('realdebrid_enabled') == 'true':
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
                        if rd_result.get(h, {}).get('rd'):
                            result[h] = True
            except Exception as e:
                log_utils.log_error(f'RD batch cache check error: {e}')
    
    # If all found, return early
    if all(result.values()):
        return result
    
    # Premiumize batch cache check
    uncached = [h for h, v in result.items() if not v]
    if uncached and ADDON.getSetting('premiumize_enabled') == 'true':
        pm = Premiumize()
        if pm.is_authorized():
            try:
                # Premiumize accepts items[] for each hash
                post_data = '&'.join(f'items[]={h}' for h in uncached)
                _, pm_result = _post(
                    f'{pm.BASE_URL}/cache/check',
                    params={'apikey': pm.token},
                    data=post_data
                )
                if isinstance(pm_result, dict) and pm_result.get('status') == 'success':
                    responses = pm_result.get('response', [])
                    for i, h in enumerate(uncached):
                        if i < len(responses) and responses[i]:
                            result[h] = True
            except Exception as e:
                log_utils.log_error(f'PM batch cache check error: {e}')
    
    if all(result.values()):
        return result
    
    # AllDebrid batch cache check
    uncached = [h for h, v in result.items() if not v]
    if uncached and ADDON.getSetting('alldebrid_enabled') == 'true':
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
                log_utils.log_error(f'AD batch cache check error: {e}')
    
    if all(result.values()):
        return result
    
    # TorBox batch cache check (POST /torrents/checkcached?format=list with {"hashes":[...]})
    uncached = [h for h, v in result.items() if not v]
    if (uncached
            and ADDON.getSetting('torbox_enabled') == 'true'
            and ADDON.getSetting('torbox_cache_check') != 'false'):
        tb = TorBox()
        if tb.is_authorized():
            try:
                _, tb_result = _post(
                    f'{tb.BASE_URL}/torrents/checkcached',
                    params={'format': 'list'},
                    data=json.dumps({'hashes': uncached}),
                    headers={**tb._auth_headers(), 'Content-Type': 'application/json'}
                )
                if isinstance(tb_result, dict) and tb_result.get('success'):
                    cached_data = tb_result.get('data', [])
                    if isinstance(cached_data, list):
                        for item in cached_data:
                            h = (item.get('hash') or '').lower()
                            if h in result:
                                result[h] = True
                    elif isinstance(cached_data, dict):
                        for h in uncached:
                            if cached_data.get(h):
                                result[h] = True
            except Exception as e:
                log_utils.log_error(f'TB batch cache check error: {e}')
    
    return result


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
        if not self.token:
            return False
        if time.time() > self.expires - 600:
            return self._refresh_token()
        return True
    
    def _refresh_token(self):
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
        except Exception as e:
            log_utils.log_error(f'Real-Debrid refresh error: {e}')
        return False
    
    def authorize(self):
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
                f'Go to: {verification_url}\n\nEnter code: {user_code}\n\nWaiting...'
            )
            
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
        if not self.is_authorized():
            return None
        
        VIDEO_EXTS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.mpg', '.mpeg', '.ts', '.webm')
        
        try:
            status, result = _post(
                f'{self.BASE_URL}/torrents/addMagnet',
                data={'magnet': magnet},
                headers=self._auth_headers()
            )
            
            if not isinstance(result, dict) or 'id' not in result:
                return None
            
            torrent_id = result['id']
            
            _, info = _get(f'{self.BASE_URL}/torrents/info/{torrent_id}', headers=self._auth_headers())
            
            if isinstance(info, dict):
                files = info.get('files', [])
                # Select only video files
                video_ids = [str(f['id']) for f in files if f.get('path', '').lower().endswith(VIDEO_EXTS)]
                file_ids = ','.join(video_ids) if video_ids else ('all' if not files else ','.join([str(f['id']) for f in files]))
                _post(
                    f'{self.BASE_URL}/torrents/selectFiles/{torrent_id}',
                    data={'files': file_ids},
                    headers=self._auth_headers()
                )
            
            for _ in range(30):
                _, status_info = _get(
                    f'{self.BASE_URL}/torrents/info/{torrent_id}',
                    headers=self._auth_headers()
                )
                
                if isinstance(status_info, dict) and status_info.get('status') == 'downloaded':
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
                                        xbmc.log(f'SALTS RD: Skipping non-video: {dl_url[:80]}', xbmc.LOGINFO)
                                        continue
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
                
                time.sleep(1)
            
            return None
            
        except Exception as e:
            log_utils.log_error(f'Real-Debrid resolve error: {e}')
            return None
    
    def check_cache(self, info_hash):
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
        if not self.is_authorized():
            return None
        
        try:
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
                    links = links_result.get('data', {}).get('magnets', {}).get('files', [])
                    if links:
                        sources = []
                        for link in links:
                            for e in link.get('e') or [link]:
                                name = (e.get('n') or '').lower()
                                if any(name.endswith(x) for x in xbmc.getSupportedMedia('video').lower().split('|') if x):
                                    sources.append((e.get('s'), e.get('l')))
                        url = max(sources)[1]
                        
                        _, unlock_result = _get(
                            f'{self.BASE_URL}/link/unlock',
                            params={'agent': self.AGENT, 'apikey': self.token, 'link': url}
                        )
                        if isinstance(unlock_result, dict) and unlock_result.get('status') == 'success':
                            return unlock_result.get('data', {}).get('link')
            
            return None
            
        except Exception as e:
            xbmc.log('Exception test.', xbmc.LOGINFO)
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


class TorBox:
    """TorBox API integration (https://api.torbox.app)

    Auth model: API key (Bearer token).  Get yours from
    https://torbox.app/settings  ->  API Keys.

    The resolver is a straightforward implementation of the documented
    TorBox flow:
      1. POST /torrents/createtorrent  (form data: magnet, seed, allow_zip)
      2. GET  /torrents/mylist?id=<id>          ->  list of files
      3. Filter files for the requested season/episode (or pick the
         largest video file for a movie).
      4. GET  /torrents/requestdl?token=&torrent_id=&file_id=
                                                ->  direct download URL
      5. Optionally remove the torrent from the cloud afterwards
         (we do this in a background thread so playback is not
         delayed).
    """

    BASE_URL = 'https://api.torbox.app/v1/api'

    def __init__(self):
        self.token = ADDON.getSetting('torbox_token')

    # ---------- HTTP helpers ----------
    def _auth_headers(self):
        return {'Authorization': f'Bearer {self.token}'}

    def is_authorized(self):
        return bool(self.token)

    # ---------- Auth ----------
    def _verify_key(self, api_key):
        """Verify an API key against /user/me. Returns user data dict or None."""
        try:
            code, info = _get(
                f'{self.BASE_URL}/user/me',
                headers={'Authorization': f'Bearer {api_key}'}
            )
            if code == 200 and isinstance(info, dict) and info.get('success'):
                return info.get('data') or {}
        except Exception as e:
            log_utils.log_error(f'TorBox key verify error: {e}')
        return None

    def authorize(self):
        """Authorize TorBox. If already authorised, show a status menu instead
        of unconditionally re-prompting for the API key.
        """
        # Already authorised? Show a status / management dialog rather than
        # re-prompting (which was confusing users into thinking auth was lost).
        if self.is_authorized():
            user = self._verify_key(self.token)
            if user:
                plan_map = {0: 'Free', 1: 'Essential', 2: 'Standard', 3: 'Pro'}
                plan = plan_map.get(user.get('plan'), str(user.get('plan')))
                expires = user.get('premium_expires_at') or 'n/a'
                email = user.get('email') or ''
                msg = (f'TorBox authorised\n'
                       f'Plan: {plan}\n'
                       f'Email: {email}\n'
                       f'Premium expires: {expires}')
                choice = xbmcgui.Dialog().select(
                    'TorBox', [msg, 'Re-authorize', 'Revoke', 'Cancel']
                )
                if choice in (-1, 0, 3):
                    return True
                if choice == 2:
                    self.revoke()
                    return False
                # choice == 1 -> fall through to re-authorize
            else:
                # Stored key no longer works -> let them re-enter
                xbmcgui.Dialog().notification(
                    'TorBox', 'Stored key invalid - please re-authorize',
                    xbmcgui.NOTIFICATION_WARNING
                )

        # Let the user pick how to authorize: device code or API key
        method = xbmcgui.Dialog().select(
            'TorBox Authorization',
            [
                'Device Code (recommended - sign in on torbox.app)',
                'API Key (paste from torbox.app/settings)',
            ]
        )
        if method == 0:
            return self._authorize_device_code()
        if method == 1:
            return self._authorize_api_key()
        return False

    def _save_token(self, api_key):
        self.token = api_key
        ADDON.setSetting('torbox_token', api_key)
        ADDON.setSetting('torbox_enabled', 'true')

    def _authorize_api_key(self):
        """Manual API key entry flow."""
        keyboard = xbmc.Keyboard('', 'Enter TorBox API Key')
        keyboard.doModal()
        if not keyboard.isConfirmed():
            return False

        api_key = keyboard.getText().strip()
        if not api_key:
            xbmcgui.Dialog().notification(
                'TorBox', 'No API key entered', xbmcgui.NOTIFICATION_ERROR
            )
            return False

        user = self._verify_key(api_key)
        if user is None:
            xbmcgui.Dialog().notification(
                'TorBox', 'Invalid API key', xbmcgui.NOTIFICATION_ERROR
            )
            return False

        self._save_token(api_key)
        xbmcgui.Dialog().notification(
            'TorBox', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO
        )
        return True

    @staticmethod
    def _show_qr(url):
        """Render the verification URL as a QR via api.qrserver.com and
        display it with Kodi's built-in picture viewer. Best-effort - if
        the network/render fails we just fall back to showing the URL.
        """
        try:
            qr_url = (
                'https://api.qrserver.com/v1/create-qr-code/'
                f'?size=400x400&data={quote_plus(url)}&bgcolor=0-0-0&color=255-255-255'
            )
            temp_dir = xbmcvfs.translatePath('special://temp/')
            qr_file = os.path.join(temp_dir, 'salts_torbox_qr.png')
            ctx = ssl._create_unverified_context()
            req = Request(qr_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, context=ctx, timeout=15) as resp:
                with open(qr_file, 'wb') as f:
                    f.write(resp.read())
            if os.path.exists(qr_file):
                xbmc.executebuiltin(f'ShowPicture({qr_file})')
                xbmc.sleep(500)
                xbmcgui.Dialog().ok(
                    'TorBox - QR Code',
                    f'Scan the QR code behind this dialog, or visit:\n'
                    f'[COLOR cyan]{url}[/COLOR]\n\n'
                    'Press OK then BACK to close the QR image.'
                )
                xbmc.executebuiltin('Action(Back)')
                return
        except Exception as e:
            log_utils.log_error(f'TorBox QR display failed: {e}')
        xbmcgui.Dialog().ok(
            'TorBox Authorization',
            f'Visit: [COLOR cyan]{url}[/COLOR]\n\n'
            'Scan the QR code or visit the URL above to authorize.'
        )

    @staticmethod
    def _extract_token(data):
        """Pull the API token out of the device/token success payload."""
        if isinstance(data, str):
            return data.strip()
        if isinstance(data, dict):
            for key in ('token', 'api_key', 'apiKey', 'api_token', 'access_token'):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            user = data.get('user')
            if isinstance(user, dict):
                for key in ('token', 'api_key', 'apiKey'):
                    val = user.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
        return None

    def _authorize_device_code(self):
        """Authorize TorBox via the official device-code flow.

        1. GET  /v1/api/user/auth/device/start?app=SALTS
        2. Show code + URL (+ optional QR) to user
        3. Poll POST /v1/api/user/auth/device/token until success/expiry/cancel
        """
        _, result = _get(
            f'{self.BASE_URL}/user/auth/device/start',
            params={'app': 'SALTS'}
        )
        if not isinstance(result, dict) or not result.get('success'):
            detail = (result or {}).get('detail') if isinstance(result, dict) else 'Network error'
            xbmcgui.Dialog().notification(
                'TorBox', f'Could not start device auth: {detail}',
                xbmcgui.NOTIFICATION_ERROR
            )
            return False

        data = result.get('data') or {}
        device_code = data.get('device_code')
        user_code = data.get('code', '')
        verify_url = data.get('verification_url') or 'https://torbox.app/oauth/device'
        friendly_url = data.get('friendly_verification_url') or verify_url
        interval = int(data.get('interval') or 5)
        if interval < 2:
            interval = 2

        if not device_code:
            xbmcgui.Dialog().notification(
                'TorBox', 'Malformed device auth response',
                xbmcgui.NOTIFICATION_ERROR
            )
            return False

        # Deadline from server expires_at (fallback: 10 minutes)
        deadline = time.time() + 600
        expires_at = data.get('expires_at')
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                deadline = exp_dt.timestamp()
            except Exception:
                pass

        # Offer to show a QR code for the verification URL
        if xbmcgui.Dialog().yesno(
            'TorBox - Device Code',
            f'Code: [B]{user_code}[/B]\n'
            f'URL: [COLOR cyan]{friendly_url}[/COLOR]\n\n'
            'Show QR code to scan with your phone?',
            yeslabel='Show QR', nolabel='Skip'
        ):
            self._show_qr(verify_url)

        # Poll for completion with a cancellable progress dialog
        progress = xbmcgui.DialogProgress()
        progress.create(
            'TorBox Authorization',
            f'1. Open: [COLOR cyan]{friendly_url}[/COLOR]\n'
            f'2. Enter code: [B]{user_code}[/B]\n'
            'Waiting for authorization...'
        )

        token_value = None
        try:
            while True:
                if progress.iscanceled():
                    xbmcgui.Dialog().notification(
                        'TorBox', 'Authorization cancelled',
                        xbmcgui.NOTIFICATION_WARNING
                    )
                    return False

                remaining = int(deadline - time.time())
                if remaining <= 0:
                    xbmcgui.Dialog().notification(
                        'TorBox', 'Device code expired. Try again.',
                        xbmcgui.NOTIFICATION_ERROR
                    )
                    return False

                pct = max(0, min(100, int(100 * (1 - remaining / 600))))
                progress.update(
                    pct,
                    f'1. Open: [COLOR cyan]{friendly_url}[/COLOR]\n'
                    f'2. Enter code: [B]{user_code}[/B]\n'
                    f'Waiting... ({remaining}s left)'
                )

                _, poll = _post(
                    f'{self.BASE_URL}/user/auth/device/token',
                    data=json.dumps({'device_code': device_code}),
                    headers={'Content-Type': 'application/json'}
                )

                if isinstance(poll, dict) and poll.get('success'):
                    token_value = self._extract_token(poll.get('data'))
                    break

                err = (poll or {}).get('error') if isinstance(poll, dict) else None
                if err in ('DEVICE_CODE_NOT_USED', 'AUTHORIZATION_PENDING', 'SLOW_DOWN', 'PENDING', None):
                    pass
                elif err in ('EXPIRED_TOKEN', 'CONFIRMATION_EXPIRED'):
                    xbmcgui.Dialog().notification(
                        'TorBox', 'Device code expired. Try again.',
                        xbmcgui.NOTIFICATION_ERROR
                    )
                    return False
                else:
                    detail = (poll or {}).get('detail') or err or 'Authorization failed'
                    xbmcgui.Dialog().notification(
                        'TorBox', detail, xbmcgui.NOTIFICATION_ERROR
                    )
                    return False

                # Sleep in 500ms chunks so cancel stays responsive
                slept = 0
                while slept < interval * 1000:
                    if progress.iscanceled():
                        return False
                    xbmc.sleep(500)
                    slept += 500
        finally:
            try:
                progress.close()
            except Exception:
                pass

        if not token_value or self._verify_key(token_value) is None:
            xbmcgui.Dialog().notification(
                'TorBox', 'Authorization succeeded but token is invalid',
                xbmcgui.NOTIFICATION_ERROR
            )
            return False

        self._save_token(token_value)
        xbmcgui.Dialog().notification(
            'TorBox', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO
        )
        return True

    def revoke(self):
        ADDON.setSetting('torbox_token', '')
        ADDON.setSetting('torbox_enabled', 'false')
        self.token = ''
        xbmcgui.Dialog().notification(
            'TorBox', 'Authorization reset', xbmcgui.NOTIFICATION_INFO
        )

    # ---------- Account ----------
    def account_info(self):
        try:
            _, info = _get(
                f'{self.BASE_URL}/user/me', headers=self._auth_headers()
            )
            return info if isinstance(info, dict) else None
        except Exception:
            return None

    # ---------- Torrent ops ----------
    def _add_magnet(self, magnet, store_to_cloud=False):
        """POST createtorrent with form data, as the API expects."""
        data = {
            'magnet': magnet,
            'seed': 3,                     # never seed
            'allow_zip': 'false',
        }
        _, result = _post(
            f'{self.BASE_URL}/torrents/createtorrent',
            data=data,
            headers=self._auth_headers()
        )
        return result if isinstance(result, dict) else None

    def _torrent_info(self, torrent_id):
        _, info = _get(
            f'{self.BASE_URL}/torrents/mylist',
            params={'id': torrent_id, 'bypass_cache': 'true'},
            headers=self._auth_headers()
        )
        return info if isinstance(info, dict) else None

    def _request_dl(self, torrent_id, file_id):
        _, dl = _get(
            f'{self.BASE_URL}/torrents/requestdl',
            params={
                'token': self.token,
                'torrent_id': torrent_id,
                'file_id': file_id,
                'redirect': 'false',
            },
            headers=self._auth_headers()
        )
        if isinstance(dl, dict) and dl.get('success'):
            return dl.get('data')
        return None

    def _delete_torrent(self, torrent_id):
        try:
            _post(
                f'{self.BASE_URL}/torrents/controltorrent',
                data=json.dumps(
                    {'torrent_id': torrent_id, 'operation': 'delete'}
                ),
                headers={**self._auth_headers(),
                         'Content-Type': 'application/json'}
            )
        except Exception:
            pass

    # ---------- Resolve ----------
    # States that mean the torrent will never be playable in a reasonable
    # time-frame and we should bail immediately rather than wait the full
    # poll budget.
    _DEAD_STATES = (
        'stalled', 'error', 'missingfiles', 'metadl error',
        'failed', 'cancelled', 'paused',
    )
    # States that mean the torrent files are usable.
    _READY_STATES = (
        'completed', 'cached', 'uploading', 'seeding',
    )

    def resolve_magnet(self, magnet, title='', season='', episode='',
                       store_to_cloud=False):
        """Resolve a magnet to a direct video URL via TorBox.

        Behaviour:
          * Server-side cache check first; if the torrent is not cached for
            this account TorBox cannot serve it instantly so we abort early
            instead of hanging the UI.
          * Poll mylist for a short, bounded window for the file list to
            appear.  Bail immediately on dead states (stalled / error /
            missing files).
        """
        if not self.is_authorized():
            return None

        torrent_id = None
        try:
            create = self._add_magnet(magnet, store_to_cloud=store_to_cloud)
            if not create or not create.get('success'):
                log_utils.log_error(f'TorBox createtorrent failed: {create}')
                return None

            data = create.get('data') or {}
            torrent_id = data.get('torrent_id') or data.get('id')
            if not torrent_id:
                log_utils.log_error(f'TorBox createtorrent missing id: {create}')
                return None

            # "Found Cached Torrent" in the detail message is a strong hint
            # that the torrent will become ready quickly; otherwise fall back
            # to checking the global cache so we don't sit on a 60s spinner
            # for a torrent TorBox can't serve.
            detail = (create.get('detail') or '').lower()
            server_cached = 'cached' in detail
            if not server_cached:
                # info_hash is required for the cache check
                m = re.search(r'btih:([A-Fa-f0-9]{40})', magnet)
                if m:
                    info_hash = m.group(1).lower()
                    try:
                        server_cached = self.check_cache(info_hash)
                    except Exception:
                        server_cached = False

            files = []
            # Bounded polling.  Cached torrents transition out of "checking"
            # in a handful of seconds; uncached torrents would never become
            # ready so we keep the budget tight.
            max_iters = 20 if server_cached else 6      # ~20s / ~6s
            sleep_s = 1.0
            for _ in range(max_iters):
                info = self._torrent_info(torrent_id)
                if info and info.get('success'):
                    tdata = info.get('data') or {}
                    state = (tdata.get('download_state')
                             or tdata.get('state') or '').lower()

                    # Bail fast on dead states.
                    if any(d in state for d in self._DEAD_STATES):
                        log_utils.log_error(
                            f'TorBox torrent {torrent_id} unplayable '
                            f'state="{state}"'
                        )
                        return None

                    files = tdata.get('files') or []
                    is_ready = (
                        tdata.get('download_present')
                        or tdata.get('download_finished')
                        or any(r in state for r in self._READY_STATES)
                    )
                    if files and is_ready:
                        break
                time.sleep(sleep_s)

            if not files:
                log_utils.log_error(
                    f'TorBox torrent {torrent_id} no files after '
                    f'{max_iters}s (cached_hint={server_cached})'
                )
                return None

            # Build a list of video files.  Each TorBox file has at least
            # id, name/short_name and size.
            def _name_of(f):
                return (f.get('short_name') or f.get('name') or '').lower()

            video_files = [
                {
                    'id': f.get('id'),
                    'name': _name_of(f),
                    'size': f.get('size', 0),
                }
                for f in files
                if _name_of(f).endswith(_VIDEO_EXTS)
            ]
            if not video_files:
                log_utils.log_error(
                    f'TorBox torrent {torrent_id} has no video files'
                )
                return None

            # If we know season/episode pick the matching file, else pick
            # the largest non-extras video.
            chosen = None
            if season and episode:
                for f in video_files:
                    if _seas_ep_filter(season, episode, f['name']):
                        chosen = f
                        break
                if not chosen:
                    # fall back to largest if no S/E match
                    chosen = max(video_files, key=lambda f: f['size'])
            else:
                clean = [f for f in video_files
                         if not any(k in f['name'] for k in _EXTRAS_KEYWORDS)]
                pool = clean or video_files
                chosen = max(pool, key=lambda f: f['size'])

            if not chosen:
                return None

            url = self._request_dl(torrent_id, chosen['id'])
            if not url:
                log_utils.log_error(
                    f'TorBox requestdl returned no url for '
                    f'torrent={torrent_id} file={chosen.get("id")}'
                )
                return None

            # Optionally drop the torrent from the user's cloud once we
            # have the playback URL.
            if not store_to_cloud:
                threading.Thread(
                    target=self._delete_torrent, args=(torrent_id,)
                ).start()
            return url

        except Exception as e:
            log_utils.log_error(f'TorBox resolve error: {e}')
            if torrent_id:
                try:
                    self._delete_torrent(torrent_id)
                except Exception:
                    pass
            return None

    # ---------- Cache check ----------
    def check_cache(self, info_hash):
        """Single hash cache lookup."""
        if not self.is_authorized():
            return False
        if ADDON.getSetting('torbox_cache_check') == 'false':
            return False
        try:
            _, result = _get(
                f'{self.BASE_URL}/torrents/checkcached',
                params={'hash': info_hash, 'format': 'list'},
                headers=self._auth_headers()
            )
            if isinstance(result, dict) and result.get('success'):
                cached_data = result.get('data', [])
                if isinstance(cached_data, list):
                    return bool(cached_data)
                if isinstance(cached_data, dict):
                    return bool(cached_data.get(info_hash.lower()))
        except Exception:
            pass
        return False
