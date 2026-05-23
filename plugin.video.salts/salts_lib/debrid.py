"""
SALTS Library - Debrid Service Integration
Supports Real-Debrid, Premiumize, AllDebrid, TorBox, Put.io, EasyDebrid,
Debrid-Link, Offcloud, LinkSnappy
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
    
    # EasyDebrid batch cache check
    # POST /link/lookup with {"urls": [magnet,...]} -> {"cached": [bool,...]}
    uncached = [h for h, v in result.items() if not v]
    if uncached and ADDON.getSetting('easydebrid_enabled') == 'true':
        ed = EasyDebrid()
        if ed.is_authorized():
            try:
                magnets = [f'magnet:?xt=urn:btih:{h}' for h in uncached]
                _, ed_result = _post(
                    f'{ed.BASE_URL}/link/lookup',
                    data=json.dumps({'urls': magnets}),
                    headers={**ed._auth_headers(), 'Content-Type': 'application/json'}
                )
                if isinstance(ed_result, dict):
                    cached_list = ed_result.get('cached', [])
                    if isinstance(cached_list, list):
                        for i, h in enumerate(uncached):
                            if i < len(cached_list) and cached_list[i]:
                                result[h] = True
            except Exception as e:
                log_utils.log_error(f'ED batch cache check error: {e}')
    
    # Offcloud batch cache check
    # POST /api/cache?key=KEY body {"hashes":[...]} -> {"cachedItems":[hash,...]}
    uncached = [h for h, v in result.items() if not v]
    if uncached and ADDON.getSetting('offcloud_enabled') == 'true':
        oc = Offcloud()
        if oc.is_authorized():
            try:
                _, oc_result = _post(
                    f'{Offcloud.BASE_URL}/cache?key={oc.token}',
                    data=json.dumps({'hashes': uncached}),
                    headers={'Content-Type': 'application/json'}
                )
                if isinstance(oc_result, dict):
                    cached_items = oc_result.get('cachedItems') or []
                    cached_set = {h.lower() for h in cached_items
                                  if isinstance(h, str)}
                    for h in uncached:
                        if h.lower() in cached_set:
                            result[h] = True
            except Exception as e:
                log_utils.log_error(f'OC batch cache check error: {e}')
    
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
    
    def resolve_magnet(self, magnet, title='', season='', episode='',
                       store_to_cloud=False):
        """Resolve a magnet via Real-Debrid. Selects only video files,
        and prefers the file matching the requested S/E for TV shows.
        Falls back to the largest video. Extra kwargs are accepted for
        API parity with TorBox so default.py can pass them blindly.
        """
        if not self.is_authorized():
            return None

        VIDEO_EXTS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
                      '.m4v', '.mpg', '.mpeg', '.ts', '.webm')
        SKIP_EXTS = ('.rar', '.zip', '.7z', '.nfo', '.txt', '.srt',
                     '.sub', '.idx', '.exe', '.iso')
        torrent_id = None

        def _se_match(name, s, e):
            if not s or not e:
                return False
            try:
                s = int(s)
                e = int(e)
            except (TypeError, ValueError):
                return False
            n = name.lower().replace(' ', '.').replace('_', '.').replace('-', '.')
            patterns = (
                r's%02de%02d' % (s, e),
                r's%de%d' % (s, e),
                r'%dx%02d' % (s, e),
                r'%dx%d' % (s, e),
            )
            return any(re.search(p, n) for p in patterns)

        try:
            _, result = _post(
                f'{self.BASE_URL}/torrents/addMagnet',
                data={'magnet': magnet},
                headers=self._auth_headers()
            )
            if not isinstance(result, dict) or 'id' not in result:
                return None
            torrent_id = result['id']

            _, info = _get(f'{self.BASE_URL}/torrents/info/{torrent_id}',
                           headers=self._auth_headers())

            # File selection: prefer video files; if season/episode given,
            # narrow to the matching file only so RD doesn't download the
            # whole pack.
            selected_path = None
            if isinstance(info, dict):
                files = info.get('files', []) or []
                videos = [
                    f for f in files
                    if f.get('path', '').lower().endswith(VIDEO_EXTS)
                ]
                chosen_ids = []
                if season and episode and videos:
                    se_hits = [
                        f for f in videos
                        if _se_match(f.get('path', ''), season, episode)
                    ]
                    if se_hits:
                        chosen_ids = [str(f['id']) for f in se_hits]
                        selected_path = se_hits[0].get('path', '')
                if not chosen_ids and videos:
                    chosen_ids = [str(f['id']) for f in videos]
                file_ids = ','.join(chosen_ids) if chosen_ids else 'all'
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
                    links = status_info.get('links', []) or []
                    # Align link index with selected file path when possible
                    sel_files = [
                        f for f in (status_info.get('files') or [])
                        if f.get('selected')
                    ]
                    ordered_links = links
                    if selected_path and sel_files and len(sel_files) == len(links):
                        for f, lk in zip(sel_files, links):
                            if f.get('path') == selected_path:
                                ordered_links = [lk] + [
                                    ll for ll in links if ll != lk
                                ]
                                break
                    for link in ordered_links:
                        _, unrestrict = _post(
                            f'{self.BASE_URL}/unrestrict/link',
                            data={'link': link},
                            headers=self._auth_headers()
                        )
                        if isinstance(unrestrict, dict):
                            dl_url = unrestrict.get('download', '')
                            if dl_url:
                                lower = dl_url.lower().split('?')[0]
                                if lower.endswith(SKIP_EXTS):
                                    continue
                                return dl_url
                    if links:
                        # Last resort: return whatever the first link unrestricts to
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
    
    def resolve_magnet(self, magnet, title='', season='', episode='',
                       store_to_cloud=False):
        """Resolve a magnet via AllDebrid. Picks the file matching the
        requested S/E (TV) or the largest video file (movie). Extra
        kwargs are accepted for API parity with TorBox.
        """
        if not self.is_authorized():
            return None

        VIDEO_EXTS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
                      '.m4v', '.mpg', '.mpeg', '.ts', '.webm')

        def _se_match(name, s, e):
            if not s or not e:
                return False
            try:
                s = int(s)
                e = int(e)
            except (TypeError, ValueError):
                return False
            n = name.lower().replace(' ', '.').replace('_', '.').replace('-', '.')
            patterns = (
                r's%02de%02d' % (s, e),
                r's%de%d' % (s, e),
                r'%dx%02d' % (s, e),
                r'%dx%d' % (s, e),
            )
            return any(re.search(p, n) for p in patterns)

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
            if not magnets[0].get('ready'):
                return None

            _, links_result = _get(
                f'{self.BASE_URL}/magnet/status',
                params={'agent': self.AGENT, 'apikey': self.token, 'id': magnet_id}
            )
            if not (isinstance(links_result, dict)
                    and links_result.get('status') == 'success'):
                return None

            links = (links_result.get('data', {})
                     .get('magnets', {}).get('files', []) or [])
            if not links:
                return None

            # Flatten nested folder structure into (size, name, link) tuples
            sources = []
            def _walk(node):
                # File node: {n: 'name', s: size, l: 'link'}
                # Folder node: {n: 'name', e: [child, ...]}
                if isinstance(node, dict):
                    children = node.get('e')
                    if children:
                        for c in children:
                            _walk(c)
                    else:
                        name = (node.get('n') or '').strip()
                        link = node.get('l')
                        size = node.get('s') or 0
                        if name and link and name.lower().endswith(VIDEO_EXTS):
                            try:
                                size = int(size)
                            except (TypeError, ValueError):
                                size = 0
                            sources.append((size, name, link))
            for top in links:
                _walk(top)

            if not sources:
                return None

            chosen = None
            if season and episode:
                hits = [t for t in sources if _se_match(t[1], season, episode)]
                if hits:
                    chosen = max(hits, key=lambda t: t[0])
            if chosen is None:
                chosen = max(sources, key=lambda t: t[0])

            url = chosen[2]
            _, unlock_result = _get(
                f'{self.BASE_URL}/link/unlock',
                params={'agent': self.AGENT, 'apikey': self.token, 'link': url}
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


# ---------------------------------------------------------------------------
# Split-pane QR dialog used by TorBox device-code auth (v2.9.26).
# QR sits on the LEFT, instructions on the RIGHT. Press OK or Back to close.
# Rendered with explicit pixel coordinates against a 1280x720 reference
# resolution (Kodi auto-scales to the active skin resolution).
# ---------------------------------------------------------------------------
class _TorBoxQRDialog(xbmcgui.WindowDialog):
    """Custom dialog: QR image (left) + instructions (right)."""

    # Reference resolution Kodi WindowDialog coords map to
    _REF_W = 1280
    _REF_H = 720

    # QR pane (left)
    _QR_X = 110
    _QR_Y = 180
    _QR_SIZE = 360

    # Text pane (right)
    _TXT_X = 540
    _TXT_Y = 180
    _TXT_W = 620
    _TXT_H = 360

    def __init__(self, qr_file=None, url='', user_code='', friendly_url=''):
        super().__init__()
        self._qr_file = qr_file
        self._url = url or ''
        self._user_code = user_code or ''
        self._friendly_url = friendly_url or url or ''
        self._build()

    def _build(self):
        # Absolute paths to bundled solid-color PNG textures.
        # ControlImage with an empty texture path does not render on most
        # Kodi skins (colorDiffuse alone is not enough), so we ship our own.
        _addon_path = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
        _black_png = os.path.join(_addon_path, 'art', 'black.png')
        _white_png = os.path.join(_addon_path, 'art', 'white.png')

        # Solid black full-screen background so the dialog stands out and
        # nothing behind it (Kodi home, posters, fanart) bleeds through.
        # aspectRatio=0 = STRETCH (fill the region, ignore aspect). We also
        # over-size the rect with negative origin so the backdrop reaches the
        # physical screen edges regardless of the skin's coord resolution.
        bg = xbmcgui.ControlImage(
            -200, -200, self._REF_W + 400, self._REF_H + 400,
            _black_png,
            aspectRatio=0
        )
        self.addControl(bg)

        # Title bar
        title = xbmcgui.ControlLabel(
            60, 80, self._REF_W - 120, 50,
            '[B]TorBox - Scan to Authorize[/B]',
            font='font30', textColor='FFFFFFFF'
        )
        self.addControl(title)

        # QR backdrop card (solid white quiet zone, so the QR contrasts
        # crisply against the black dialog background and stays scannable)
        qr_card = xbmcgui.ControlImage(
            self._QR_X - 20, self._QR_Y - 20,
            self._QR_SIZE + 40, self._QR_SIZE + 40,
            _white_png,
            aspectRatio=0
        )
        self.addControl(qr_card)

        # QR image (or fallback note if download failed)
        if self._qr_file and os.path.exists(self._qr_file):
            qr_img = xbmcgui.ControlImage(
                self._QR_X, self._QR_Y,
                self._QR_SIZE, self._QR_SIZE,
                self._qr_file,
                aspectRatio=2  # 2 = stretch to fit
            )
            self.addControl(qr_img)
        else:
            no_qr = xbmcgui.ControlLabel(
                self._QR_X, self._QR_Y + self._QR_SIZE // 2 - 20,
                self._QR_SIZE, 40,
                '[B]QR unavailable[/B]\nUse the URL on the right',
                font='font13', textColor='FF101216',
                alignment=0x00000002 | 0x00000004  # CENTER_X | CENTER_Y
            )
            self.addControl(no_qr)

        # Right-side message
        lines = [
            '[B]1. On your phone:[/B]',
            '   Scan the QR code on the left',
            '',
            '[B]or  visit:[/B]',
            f'   [COLOR cyan]{self._friendly_url}[/COLOR]',
            '',
        ]
        if self._user_code:
            lines += [
                '[B]2. Enter the code:[/B]',
                f'   [COLOR FFFFD700][B]{self._user_code}[/B][/COLOR]',
                '',
            ]
        lines += [
            '[B]3. Approve the request[/B]',
            '   in your TorBox account.',
            '',
            '[COLOR FF888888]Press OK or Back when done.[/COLOR]',
        ]
        body = xbmcgui.ControlTextBox(
            self._TXT_X, self._TXT_Y,
            self._TXT_W, self._TXT_H,
            font='font13', textColor='FFFFFFFF'
        )
        self.addControl(body)
        body.setText('\n'.join(lines))

        # Close button at the bottom-right
        self._close_btn = xbmcgui.ControlButton(
            self._REF_W - 220, self._REF_H - 110,
            160, 50,
            'Close',
            focusTexture='', noFocusTexture='',
            textColor='FFFFFFFF', focusedColor='FF1E90FF',
            alignment=0x00000002 | 0x00000004
        )
        self.addControl(self._close_btn)
        self.setFocus(self._close_btn)

    # Esc / Back / OK / Enter -> close
    def onAction(self, action):
        # ACTION_PREVIOUS_MENU=10, ACTION_NAV_BACK=92,
        # ACTION_SELECT_ITEM=7 (OK on remote)
        if action.getId() in (10, 92, 7):
            self.close()

    def onControl(self, control):
        if control == self._close_btn:
            self.close()


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
    def _show_qr(url, user_code='', friendly_url=''):
        """Render the verification URL as a QR code and show it in a
        custom split-pane dialog (QR on the left, instructions on the
        right) instead of Kodi's full-screen picture viewer.

        v2.9.26 fix: the old implementation used `ShowPicture()` and then
        layered `Dialog().ok()` on top of it - which left the user
        staring at a blank/dim screen because the dialog covered the
        picture. This version uses a `WindowDialog` so QR + text are
        visible at the same time.
        """
        # ---- fetch the QR image ----------------------------------------
        qr_file = None
        try:
            qr_url = (
                'https://api.qrserver.com/v1/create-qr-code/'
                f'?size=512x512&margin=10&data={quote_plus(url)}'
                '&bgcolor=255-255-255&color=0-0-0'
            )
            temp_dir = xbmcvfs.translatePath('special://temp/')
            try:
                os.makedirs(temp_dir, exist_ok=True)
            except Exception:
                pass
            qr_file = os.path.join(temp_dir, 'salts_torbox_qr.png')
            ctx = ssl._create_unverified_context()
            req = Request(qr_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, context=ctx, timeout=15) as resp:
                payload = resp.read()
            if not payload:
                raise RuntimeError('empty QR response')
            with open(qr_file, 'wb') as f:
                f.write(payload)
            if not (os.path.exists(qr_file) and os.path.getsize(qr_file) > 0):
                raise RuntimeError('QR file empty after write')
        except Exception as e:
            log_utils.log_error(f'TorBox QR fetch failed: {e}')
            qr_file = None

        # ---- show the split-pane dialog --------------------------------
        try:
            dlg = _TorBoxQRDialog(
                qr_file=qr_file,
                url=url,
                user_code=user_code,
                friendly_url=friendly_url or url,
            )
            dlg.doModal()
            del dlg
            return
        except Exception as e:
            log_utils.log_error(f'TorBox QR dialog failed: {e}')

        # ---- last-ditch text-only fallback -----------------------------
        xbmcgui.Dialog().ok(
            'TorBox Authorization',
            (f'Code: [B]{user_code}[/B]\n' if user_code else '')
            + f'Visit: [COLOR cyan]{url}[/COLOR]\n\n'
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
            self._show_qr(verify_url, user_code=user_code,
                          friendly_url=friendly_url)

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
          * Server-side cache check first; cached torrents become playable
            in a few seconds.
          * If not cached and `torbox_allow_uncached` is enabled the addon
            will start the torrent on TorBox and poll with a progress
            dialog (showing TorBox-side download progress) for up to
            `torbox_uncached_wait_minutes` minutes. User can cancel.
          * If not cached and the setting is off, bail immediately rather
            than hanging the UI.
        """
        if not self.is_authorized():
            return None

        torrent_id = None
        progress_dlg = None
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

            allow_uncached = (
                ADDON.getSetting('torbox_allow_uncached') == 'true'
            )
            try:
                wait_minutes = int(float(
                    ADDON.getSetting('torbox_uncached_wait_minutes') or 5
                ))
            except (TypeError, ValueError):
                wait_minutes = 5
            wait_minutes = max(1, min(wait_minutes, 30))

            files = []

            if server_cached:
                # Cached: short, tight poll - file list materialises in
                # a handful of seconds.
                max_iters = 30
                sleep_s = 1.0
                for _ in range(max_iters):
                    info = self._torrent_info(torrent_id)
                    if info and info.get('success'):
                        tdata = info.get('data') or {}
                        state = (tdata.get('download_state')
                                 or tdata.get('state') or '').lower()
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
            elif allow_uncached:
                # Uncached + user opted in: TorBox has to fetch the torrent
                # to its CDN first (its API can't stream while downloading
                # the way Real-Debrid can). We poll quietly in the
                # background and start playback the moment TorBox flags
                # the file as ready (`download_present`). Kodi stays
                # usable while this runs.
                xbmcgui.Dialog().notification(
                    'TorBox',
                    'Not cached - downloading on TorBox, playback '
                    'will start automatically when ready.',
                    xbmcgui.NOTIFICATION_INFO,
                    6000
                )
                progress_dlg = xbmcgui.DialogProgressBG()
                try:
                    progress_dlg.create(
                        'TorBox', 'Preparing torrent on TorBox...'
                    )
                except Exception:
                    progress_dlg = None
                deadline = time.time() + wait_minutes * 60
                sleep_s = 1.0
                last_pct = -1
                last_notify_min = -1
                while time.time() < deadline:
                    # User abort: monitor Kodi's global "stop/abort"
                    # signal rather than a blocking cancel dialog.
                    if xbmc.Monitor().abortRequested():
                        log_utils.log(
                            f'TorBox uncached torrent {torrent_id} '
                            f'aborted (Kodi shutdown)',
                            xbmc.LOGINFO
                        )
                        return None
                    info = self._torrent_info(torrent_id)
                    if info and info.get('success'):
                        tdata = info.get('data') or {}
                        state = (tdata.get('download_state')
                                 or tdata.get('state') or '').lower()
                        if any(d in state for d in self._DEAD_STATES):
                            log_utils.log_error(
                                f'TorBox torrent {torrent_id} unplayable '
                                f'state="{state}"'
                            )
                            xbmcgui.Dialog().notification(
                                'TorBox',
                                'Torrent cannot be downloaded '
                                f'({state}) - trying next source.',
                                xbmcgui.NOTIFICATION_WARNING,
                                5000
                            )
                            return None
                        files = tdata.get('files') or []
                        is_ready = (
                            tdata.get('download_present')
                            or tdata.get('download_finished')
                            or any(r in state for r in self._READY_STATES)
                        )
                        if files and is_ready:
                            if progress_dlg:
                                try:
                                    progress_dlg.update(
                                        100, 'TorBox', 'Ready - starting playback'
                                    )
                                except Exception:
                                    pass
                            break

                        # Progress %: TorBox returns `progress` as 0..1
                        try:
                            prog = float(tdata.get('progress') or 0) * 100.0
                        except (TypeError, ValueError):
                            prog = 0.0
                        try:
                            dl_speed = float(
                                tdata.get('download_speed') or 0
                            ) / (1024 * 1024)
                        except (TypeError, ValueError):
                            dl_speed = 0.0
                        try:
                            seeds = int(tdata.get('seeds') or 0)
                        except (TypeError, ValueError):
                            seeds = 0
                        pct = int(prog)
                        remaining_s = max(0, int(deadline - time.time()))
                        remaining_m = remaining_s // 60
                        if pct != last_pct and progress_dlg:
                            pretty_state = (state or 'queued').replace(
                                '_', ' '
                            )
                            try:
                                progress_dlg.update(
                                    max(pct, 1),
                                    'TorBox - preparing torrent',
                                    f'{pretty_state} | {prog:.0f}% | '
                                    f'{dl_speed:.1f} MB/s | seeds: {seeds} '
                                    f'| up to {remaining_m}m left'
                                )
                            except Exception:
                                pass
                            last_pct = pct
                        # Friendly minute-by-minute heads up so the user
                        # knows it's still working, without spamming.
                        elapsed_min = int(
                            (wait_minutes * 60 - remaining_s) // 60
                        )
                        if (elapsed_min > 0
                                and elapsed_min != last_notify_min
                                and elapsed_min % 2 == 0):
                            xbmcgui.Dialog().notification(
                                'TorBox',
                                f'Still preparing... {pct}% downloaded '
                                f'({remaining_m}m wait left)',
                                xbmcgui.NOTIFICATION_INFO,
                                3500
                            )
                            last_notify_min = elapsed_min
                    time.sleep(sleep_s)
                if progress_dlg:
                    try:
                        progress_dlg.close()
                    except Exception:
                        pass
                    progress_dlg = None
                # Timed out without becoming ready -> tell the user and bail.
                if not files:
                    xbmcgui.Dialog().notification(
                        'TorBox',
                        f'Torrent not ready after {wait_minutes}m - '
                        f'trying next source.',
                        xbmcgui.NOTIFICATION_WARNING,
                        5000
                    )
            else:
                # Uncached + user did not opt in -> bail fast (no UI hang).
                log_utils.log(
                    f'TorBox torrent {torrent_id} not cached; '
                    f'torbox_allow_uncached is disabled - skipping',
                    xbmc.LOGINFO
                )
                return None

            if not files:
                log_utils.log_error(
                    f'TorBox torrent {torrent_id} no files after '
                    f'wait (cached={server_cached}, '
                    f'allow_uncached={allow_uncached})'
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
        finally:
            if progress_dlg is not None:
                try:
                    progress_dlg.close()
                except Exception:
                    pass

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


class PutIO:
    """Put.io API integration (https://api.put.io/v2)

    Auth model: OAuth Bearer token.  Users generate a personal OAuth
    token at https://app.put.io/oauth (Settings -> API/Apps -> Create
    application -> copy the OAuth token) and paste it into Kodi.

    Resolver flow (mirrors the documented Put.io v2 API):
      1. POST /transfers/add        (form-data: url=<magnet>)
      2. GET  /transfers/<id>       -> poll until status == COMPLETED.
      3. GET  /files/list?parent_id=<file_id>
                                    -> list of video files in the
                                       completed transfer's folder
                                       (or a single file if it was a
                                       direct-link transfer).
      4. GET  /files/<file_id>/url  -> direct download / streaming URL.
      5. Optionally remove the transfer + files from the user's cloud
         in a background thread once playback has started.

    Put.io does NOT expose a public "instant cache" lookup, so
    ``check_cache`` returns False.  Cached torrents still resolve in a
    handful of seconds; uncached ones honour the same opt-in /
    max-wait settings as the TorBox flow.
    """

    BASE_URL = 'https://api.put.io/v2'

    def __init__(self):
        self.token = ADDON.getSetting('putio_token')

    # ---------- HTTP helpers ----------
    def _auth_headers(self):
        return {'Authorization': f'Bearer {self.token}'}

    def is_authorized(self):
        return bool(self.token)

    # ---------- Auth ----------
    def _verify_key(self, api_key):
        """Verify an OAuth token against /account/info. Returns user data
        dict or None."""
        try:
            code, info = _get(
                f'{self.BASE_URL}/account/info',
                headers={'Authorization': f'Bearer {api_key}'}
            )
            if code == 200 and isinstance(info, dict) and info.get('status') == 'OK':
                return info.get('info') or {}
        except Exception as e:
            log_utils.log_error(f'Put.io key verify error: {e}')
        return None

    def authorize(self):
        """Authorize Put.io.  If already authorized show a status menu;
        otherwise prompt for the OAuth token."""
        if self.is_authorized():
            user = self._verify_key(self.token)
            if user:
                username = user.get('username') or ''
                mail = user.get('mail') or ''
                plan_expires = user.get('plan_expiration_date') or 'n/a'
                disk = user.get('disk') or {}
                avail_gb = (disk.get('avail') or 0) / (1024 ** 3)
                size_gb = (disk.get('size') or 0) / (1024 ** 3)
                msg = (f'Put.io authorised\n'
                       f'User: {username}\n'
                       f'Email: {mail}\n'
                       f'Plan expires: {plan_expires}\n'
                       f'Disk: {avail_gb:.1f}G free / {size_gb:.1f}G')
                choice = xbmcgui.Dialog().select(
                    'Put.io', [msg, 'Re-authorize', 'Revoke', 'Cancel']
                )
                if choice in (-1, 0, 3):
                    return True
                if choice == 2:
                    self.revoke()
                    return False
                # choice == 1 -> fall through to re-authorize
            else:
                xbmcgui.Dialog().notification(
                    'Put.io', 'Stored token invalid - please re-authorize',
                    xbmcgui.NOTIFICATION_WARNING
                )

        # Show a brief instruction dialog, then collect the OAuth token.
        xbmcgui.Dialog().ok(
            'Put.io Authorization',
            'Generate an OAuth token at:\n'
            '[COLOR cyan]https://app.put.io/oauth[/COLOR]\n\n'
            'Settings -> API -> Create application -> copy the OAuth Token.\n'
            'Then paste it on the next screen.'
        )

        keyboard = xbmc.Keyboard('', 'Enter Put.io OAuth Token')
        keyboard.doModal()
        if not keyboard.isConfirmed():
            return False

        api_key = keyboard.getText().strip()
        if not api_key:
            xbmcgui.Dialog().notification(
                'Put.io', 'No token entered', xbmcgui.NOTIFICATION_ERROR
            )
            return False

        user = self._verify_key(api_key)
        if user is None:
            xbmcgui.Dialog().notification(
                'Put.io', 'Invalid OAuth token', xbmcgui.NOTIFICATION_ERROR
            )
            return False

        self.token = api_key
        ADDON.setSetting('putio_token', api_key)
        ADDON.setSetting('putio_enabled', 'true')
        xbmcgui.Dialog().notification(
            'Put.io', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO
        )
        return True

    def revoke(self):
        ADDON.setSetting('putio_token', '')
        ADDON.setSetting('putio_enabled', 'false')
        self.token = ''
        xbmcgui.Dialog().notification(
            'Put.io', 'Authorization reset', xbmcgui.NOTIFICATION_INFO
        )

    # ---------- Transfer / file ops ----------
    def _add_transfer(self, magnet):
        """POST /transfers/add - returns transfer dict or None."""
        _, result = _post(
            f'{self.BASE_URL}/transfers/add',
            data={'url': magnet},
            headers=self._auth_headers()
        )
        if isinstance(result, dict) and result.get('status') == 'OK':
            return result.get('transfer') or {}
        log_utils.log_error(f'Put.io transfers/add failed: {result}')
        return None

    def _transfer_info(self, transfer_id):
        _, result = _get(
            f'{self.BASE_URL}/transfers/{transfer_id}',
            headers=self._auth_headers()
        )
        if isinstance(result, dict) and result.get('status') == 'OK':
            return result.get('transfer') or {}
        return None

    def _list_files(self, parent_id):
        _, result = _get(
            f'{self.BASE_URL}/files/list',
            params={'parent_id': parent_id, 'per_page': 1000},
            headers=self._auth_headers()
        )
        if isinstance(result, dict) and result.get('status') == 'OK':
            return result.get('files') or []
        return []

    def _file_info(self, file_id):
        _, result = _get(
            f'{self.BASE_URL}/files/{file_id}',
            headers=self._auth_headers()
        )
        if isinstance(result, dict) and result.get('status') == 'OK':
            return result.get('file') or {}
        return None

    def _file_url(self, file_id):
        """GET /files/{id}/url -> direct download URL."""
        _, result = _get(
            f'{self.BASE_URL}/files/{file_id}/url',
            headers=self._auth_headers()
        )
        if isinstance(result, dict) and result.get('url'):
            return result.get('url')
        return None

    def _delete_transfer(self, transfer_id, file_id=None):
        """Best-effort cleanup: cancel the transfer and remove the file
        from the cloud once playback has started."""
        try:
            _post(
                f'{self.BASE_URL}/transfers/cancel',
                data={'transfer_ids': str(transfer_id)},
                headers=self._auth_headers()
            )
        except Exception:
            pass
        if file_id:
            try:
                _post(
                    f'{self.BASE_URL}/files/delete',
                    data={'file_ids': str(file_id)},
                    headers=self._auth_headers()
                )
            except Exception:
                pass

    # ---------- Recursive video file collection ----------
    def _collect_video_files(self, root_file):
        """Given a file dict from put.io, return a flat list of video
        files.  Put.io marks regular files with file_type='VIDEO' and
        folders with file_type='FOLDER'.
        """
        results = []

        def _walk(node):
            if not isinstance(node, dict):
                return
            ftype = (node.get('file_type') or '').upper()
            name = node.get('name') or ''
            if ftype == 'FOLDER':
                for child in self._list_files(node.get('id')):
                    _walk(child)
            else:
                lower = name.lower()
                is_video = (
                    ftype == 'VIDEO'
                    or lower.endswith(_VIDEO_EXTS)
                )
                if is_video:
                    results.append({
                        'id': node.get('id'),
                        'name': name,
                        'size': node.get('size') or 0,
                    })

        _walk(root_file)
        return results

    # ---------- Resolve ----------
    _DEAD_STATES = (
        'error', 'error_no_retry', 'cancelled', 'cancelling',
    )
    _READY_STATES = ('completed', 'seeding')

    def resolve_magnet(self, magnet, title='', season='', episode='',
                       store_to_cloud=False):
        """Resolve a magnet via Put.io to a direct video URL.

        Honours the same opt-in / max-wait pattern as the TorBox
        resolver - if the user disabled "auto-play uncached" we bail
        the moment the cache check (driven by Put.io's own transfer
        progress) shows the magnet is not instantly ready.
        """
        if not self.is_authorized():
            return None

        transfer = None
        progress_dlg = None
        try:
            transfer = self._add_transfer(magnet)
            if not transfer:
                return None
            transfer_id = transfer.get('id')
            if not transfer_id:
                return None

            allow_uncached = (
                ADDON.getSetting('putio_allow_uncached') == 'true'
            )
            try:
                wait_minutes = int(float(
                    ADDON.getSetting('putio_uncached_wait_minutes') or 5
                ))
            except (TypeError, ValueError):
                wait_minutes = 5
            wait_minutes = max(1, min(wait_minutes, 30))

            # Quick burst poll for the cached path - put.io completes
            # cached torrents within a couple of seconds.
            file_id = None
            status_lower = (transfer.get('status') or '').lower()
            if status_lower in self._READY_STATES:
                file_id = transfer.get('file_id')

            if not file_id:
                quick_deadline = time.time() + 8  # generous "cached" window
                while time.time() < quick_deadline and not file_id:
                    info = self._transfer_info(transfer_id)
                    if not info:
                        time.sleep(1)
                        continue
                    status_lower = (info.get('status') or '').lower()
                    if any(d in status_lower for d in self._DEAD_STATES):
                        log_utils.log_error(
                            f'Put.io transfer {transfer_id} unplayable '
                            f'state="{status_lower}"'
                        )
                        return None
                    if status_lower in self._READY_STATES:
                        file_id = info.get('file_id')
                        break
                    time.sleep(1)

            if not file_id:
                # Not cached.  Honour the opt-in setting.
                if not allow_uncached:
                    log_utils.log(
                        f'Put.io transfer {transfer_id} not cached; '
                        f'putio_allow_uncached is disabled - skipping',
                        xbmc.LOGINFO
                    )
                    return None
                xbmcgui.Dialog().notification(
                    'Put.io',
                    'Not cached - downloading on Put.io, playback '
                    'will start automatically when ready.',
                    xbmcgui.NOTIFICATION_INFO,
                    6000
                )
                progress_dlg = xbmcgui.DialogProgressBG()
                try:
                    progress_dlg.create('Put.io', 'Preparing torrent on Put.io...')
                except Exception:
                    progress_dlg = None

                deadline = time.time() + wait_minutes * 60
                last_pct = -1
                while time.time() < deadline:
                    if xbmc.Monitor().abortRequested():
                        log_utils.log(
                            f'Put.io transfer {transfer_id} aborted '
                            f'(Kodi shutdown)', xbmc.LOGINFO
                        )
                        return None
                    info = self._transfer_info(transfer_id)
                    if not info:
                        time.sleep(1)
                        continue
                    status_lower = (info.get('status') or '').lower()
                    if any(d in status_lower for d in self._DEAD_STATES):
                        log_utils.log_error(
                            f'Put.io transfer {transfer_id} unplayable '
                            f'state="{status_lower}"'
                        )
                        xbmcgui.Dialog().notification(
                            'Put.io',
                            f'Torrent cannot be downloaded '
                            f'({status_lower}) - trying next source.',
                            xbmcgui.NOTIFICATION_WARNING,
                            5000
                        )
                        return None
                    if status_lower in self._READY_STATES:
                        file_id = info.get('file_id')
                        if file_id:
                            if progress_dlg:
                                try:
                                    progress_dlg.update(
                                        100, 'Put.io', 'Ready - starting playback'
                                    )
                                except Exception:
                                    pass
                            break

                    try:
                        pct = int(info.get('percent_done') or 0)
                    except (TypeError, ValueError):
                        pct = 0
                    try:
                        dl_speed = float(info.get('down_speed') or 0) / (1024 * 1024)
                    except (TypeError, ValueError):
                        dl_speed = 0.0
                    try:
                        peers = int(info.get('current_seeds') or 0)
                    except (TypeError, ValueError):
                        peers = 0
                    remaining_s = max(0, int(deadline - time.time()))
                    remaining_m = remaining_s // 60
                    if pct != last_pct and progress_dlg:
                        pretty_state = (status_lower or 'queued').replace('_', ' ')
                        try:
                            progress_dlg.update(
                                max(pct, 1),
                                'Put.io - preparing torrent',
                                f'{pretty_state} | {pct}% | '
                                f'{dl_speed:.1f} MB/s | seeds: {peers} '
                                f'| up to {remaining_m}m left'
                            )
                        except Exception:
                            pass
                        last_pct = pct
                    time.sleep(1)

                if progress_dlg:
                    try:
                        progress_dlg.close()
                    except Exception:
                        pass
                    progress_dlg = None

                if not file_id:
                    xbmcgui.Dialog().notification(
                        'Put.io',
                        f'Torrent not ready after {wait_minutes}m - '
                        f'trying next source.',
                        xbmcgui.NOTIFICATION_WARNING,
                        5000
                    )
                    return None

            # Have a file_id - could be a single video file OR a folder.
            root = self._file_info(file_id)
            if not root:
                log_utils.log_error(
                    f'Put.io file/{file_id} returned no info'
                )
                return None

            video_files = self._collect_video_files(root)
            if not video_files:
                log_utils.log_error(
                    f'Put.io transfer {transfer_id} has no video files '
                    f'under file_id={file_id}'
                )
                return None

            # Pick file matching S/E for TV, else largest non-extras.
            chosen = None
            if season and episode:
                for f in video_files:
                    if _seas_ep_filter(season, episode, f['name']):
                        chosen = f
                        break
                if not chosen:
                    chosen = max(video_files, key=lambda f: f.get('size') or 0)
            else:
                clean = [
                    f for f in video_files
                    if not any(k in f['name'].lower()
                               for k in _EXTRAS_KEYWORDS)
                ]
                pool = clean or video_files
                chosen = max(pool, key=lambda f: f.get('size') or 0)

            if not chosen:
                return None

            url = self._file_url(chosen['id'])
            if not url:
                log_utils.log_error(
                    f'Put.io file/{chosen.get("id")}/url returned no url'
                )
                return None

            if not store_to_cloud:
                threading.Thread(
                    target=self._delete_transfer,
                    args=(transfer_id, file_id),
                ).start()
            return url

        except Exception as e:
            log_utils.log_error(f'Put.io resolve error: {e}')
            if transfer and transfer.get('id'):
                try:
                    self._delete_transfer(
                        transfer.get('id'), transfer.get('file_id')
                    )
                except Exception:
                    pass
            return None
        finally:
            if progress_dlg is not None:
                try:
                    progress_dlg.close()
                except Exception:
                    pass

    # ---------- Cache check ----------
    def check_cache(self, info_hash):
        """Put.io exposes no public instant-cache lookup. Always False
        so the source list doesn't falsely flag torrents as cached;
        resolve_magnet still works (cached completes instantly,
        uncached honours putio_allow_uncached)."""
        return False



# ---------------------------------------------------------------------------
# Premium.to - file-hoster multihost (NOT a torrent/magnet debrid).
#
# API docs: http://premium.to/API.html
#   Auth   : userid + apikey passed as query params on every call.
#   Hosters: alfafile.net, turbobit.net, filer.net, 1fichier.com, mega.nz,
#            ddownload.com, rapidgator.net, filestore.to, uploaded.net, ...
#
# premium.to cannot resolve magnet links; it is wired into the hoster-URL
# resolution chain in default.py (before ResolveURL), not the magnet chain.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# EasyDebrid (easydebrid.com) - Real-Debrid-equivalent magnet/cache resolver.
# Authentication: single API key (bearer token), entered manually via keyboard
# prompt (no OAuth flow exposed by the service).
# Endpoints used (all under https://easydebrid.com/api/v1):
#   POST /link/lookup     - body {"urls":[magnet,...]} -> {"cached":[bool,...]}
#   POST /link/generate   - body {"url": magnet} -> {"files":[{filename,url}, ...]}
#   GET  /user/details    - account info (paid_until timestamp)
# ---------------------------------------------------------------------------
class EasyDebrid:
    """EasyDebrid API integration (Real-Debrid feature parity)."""

    BASE_URL = 'https://easydebrid.com/api/v1'

    def __init__(self):
        self.token = ADDON.getSetting('easydebrid_token')

    # ---------- Auth ----------
    def _auth_headers(self):
        return {'Authorization': f'Bearer {self.token}'} if self.token else {}

    def is_authorized(self):
        return bool(self.token)

    def _verify_key(self, api_key):
        """Validate an API key against /user/details. Returns True on 200 OK."""
        try:
            status, _ = _get(
                f'{self.BASE_URL}/user/details',
                headers={'Authorization': f'Bearer {api_key}'}
            )
            return 200 <= int(status or 0) < 300
        except Exception as e:
            log_utils.log_error(f'EasyDebrid verify error: {e}')
            return False

    def authorize(self):
        """Prompt the user for an EasyDebrid API key (from
        https://easydebrid.com/dashboard), validate it via /user/details,
        and persist it to settings on success."""
        kb = xbmc.Keyboard('', 'Enter EasyDebrid API Key')
        kb.doModal()
        if not kb.isConfirmed():
            return False
        api_key = kb.getText().strip()
        if not api_key:
            xbmcgui.Dialog().notification(
                'EasyDebrid', 'API Key is required',
                xbmcgui.NOTIFICATION_ERROR)
            return False

        if self._verify_key(api_key):
            self.token = api_key
            ADDON.setSetting('easydebrid_token', api_key)
            ADDON.setSetting('easydebrid_enabled', 'true')
            xbmcgui.Dialog().notification(
                'EasyDebrid', 'Authorization successful!',
                xbmcgui.NOTIFICATION_INFO)
            return True

        xbmcgui.Dialog().notification(
            'EasyDebrid', 'Invalid API key',
            xbmcgui.NOTIFICATION_ERROR)
        return False

    def revoke(self):
        ADDON.setSetting('easydebrid_token', '')
        ADDON.setSetting('easydebrid_enabled', 'false')
        self.token = ''

    # ---------- Account info ----------
    def account_info(self):
        if not self.is_authorized():
            return None
        try:
            _, result = _get(
                f'{self.BASE_URL}/user/details',
                headers=self._auth_headers()
            )
            return result if isinstance(result, dict) else None
        except Exception as e:
            log_utils.log_error(f'EasyDebrid account error: {e}')
            return None

    # ---------- Resolve ----------
    def resolve_magnet(self, magnet, title='', season='', episode='',
                       store_to_cloud=False):
        """Resolve a magnet via EasyDebrid. Picks the file matching the
        requested S/E (TV) or the largest video file (movie). Extra kwargs
        are accepted for API parity with TorBox/Put.io.
        """
        if not self.is_authorized() or not magnet:
            return None

        def _se_match(name, s, e):
            if not s or not e:
                return False
            try:
                s = int(s)
                e = int(e)
            except (TypeError, ValueError):
                return False
            n = name.lower().replace(' ', '.').replace('_', '.').replace('-', '.')
            patterns = (
                r's%02de%02d' % (s, e),
                r's%de%d' % (s, e),
                r'%dx%02d' % (s, e),
                r'%dx%d' % (s, e),
            )
            return any(re.search(p, n) for p in patterns)

        try:
            _, result = _post(
                f'{self.BASE_URL}/link/generate',
                data=json.dumps({'url': magnet}),
                headers={**self._auth_headers(),
                         'Content-Type': 'application/json'}
            )
            if not isinstance(result, dict):
                return None

            files = result.get('files') or []
            # Keep only playable video files, attach a size if provided.
            sources = []
            for f in files:
                name = (f.get('filename') or f.get('name') or '').strip()
                link = f.get('url') or f.get('link')
                if not (name and link):
                    continue
                lname = name.lower()
                if not lname.endswith(_VIDEO_EXTS):
                    continue
                # Skip obvious extras/samples
                if any(k in lname.replace(' ', '.') for k in _EXTRAS_KEYWORDS):
                    continue
                try:
                    size = int(f.get('size') or f.get('filesize') or 0)
                except (TypeError, ValueError):
                    size = 0
                sources.append((size, name, link))

            if not sources:
                return None

            chosen = None
            if season and episode:
                hits = [t for t in sources if _se_match(t[1], season, episode)]
                if hits:
                    chosen = max(hits, key=lambda t: t[0])
                else:
                    # Fall back to canonical SxxExx filter helper
                    hits2 = [t for t in sources
                             if _seas_ep_filter(season, episode, t[1])]
                    if hits2:
                        chosen = max(hits2, key=lambda t: t[0])
            if chosen is None:
                chosen = max(sources, key=lambda t: t[0])

            return chosen[2]
        except Exception as e:
            log_utils.log_error(f'EasyDebrid resolve error: {e}')
            return None

    # ---------- Single cache check ----------
    def check_cache(self, info_hash):
        if not self.is_authorized() or not info_hash:
            return False
        try:
            magnet = f'magnet:?xt=urn:btih:{info_hash}'
            _, result = _post(
                f'{self.BASE_URL}/link/lookup',
                data=json.dumps({'urls': [magnet]}),
                headers={**self._auth_headers(),
                         'Content-Type': 'application/json'}
            )
            if isinstance(result, dict):
                cached = result.get('cached') or []
                return bool(cached and cached[0])
        except Exception as e:
            log_utils.log_error(f'EasyDebrid cache check error: {e}')
        return False


# ---------------------------------------------------------------------------
# Debrid-Link (debrid-link.com) - Real-Debrid-equivalent magnet/cache resolver.
# Authentication: Private API key (Bearer token), generated by the user at
# https://debrid-link.com/webapp/apikey
# Endpoints used (all under https://debrid-link.com/api/v2):
#   POST   /seedbox/add        - body {url: magnet} -> torrent object with
#                                 files[] (downloadUrl) and downloadPercent
#   GET    /seedbox/list?ids=  - poll torrent state
#   DELETE /seedbox/:id/remove - cleanup uncached probes / unwanted seeds
#   GET    /account/infos      - account information
# Notes: Debrid-Link has no batch cache endpoint; single-hash check_cache()
# probes /seedbox/add with the bare info_hash (docs guarantee the hash is
# only added if already cached server-side) and removes the entry on miss.
# ---------------------------------------------------------------------------
class DebridLink:
    """Debrid-Link API integration (Real-Debrid feature parity)."""

    BASE_URL = 'https://debrid-link.com/api/v2'

    def __init__(self):
        self.token = ADDON.getSetting('debridlink_token')

    def _auth_headers(self):
        return {'Authorization': f'Bearer {self.token}'} if self.token else {}

    def is_authorized(self):
        return bool(self.token)

    def _verify_key(self, api_key):
        try:
            status, body = _get(
                f'{self.BASE_URL}/account/infos',
                headers={'Authorization': f'Bearer {api_key}'}
            )
            return (200 <= int(status or 0) < 300
                    and isinstance(body, dict)
                    and body.get('success') is True)
        except Exception as e:
            log_utils.log_error(f'DebridLink verify error: {e}')
            return False

    def authorize(self):
        kb = xbmc.Keyboard('', 'Enter Debrid-Link API Key')
        kb.doModal()
        if not kb.isConfirmed():
            return False
        api_key = kb.getText().strip()
        if not api_key:
            xbmcgui.Dialog().notification(
                'Debrid-Link', 'API Key is required',
                xbmcgui.NOTIFICATION_ERROR)
            return False
        if self._verify_key(api_key):
            self.token = api_key
            ADDON.setSetting('debridlink_token', api_key)
            ADDON.setSetting('debridlink_enabled', 'true')
            xbmcgui.Dialog().notification(
                'Debrid-Link', 'Authorization successful!',
                xbmcgui.NOTIFICATION_INFO)
            return True
        xbmcgui.Dialog().notification(
            'Debrid-Link', 'Invalid API key',
            xbmcgui.NOTIFICATION_ERROR)
        return False

    def revoke(self):
        ADDON.setSetting('debridlink_token', '')
        ADDON.setSetting('debridlink_enabled', 'false')
        self.token = ''

    def account_info(self):
        if not self.is_authorized():
            return None
        try:
            _, body = _get(
                f'{self.BASE_URL}/account/infos',
                headers=self._auth_headers()
            )
            if isinstance(body, dict) and body.get('success'):
                return body.get('value')
        except Exception as e:
            log_utils.log_error(f'DebridLink account error: {e}')
        return None

    def _remove_torrent(self, tid):
        try:
            _http(f'{self.BASE_URL}/seedbox/{tid}/remove',
                  method='DELETE', headers=self._auth_headers())
        except Exception:
            pass

    def _add_torrent(self, url):
        """POST /seedbox/add - returns the torrent value object or None."""
        try:
            _, body = _post(
                f'{self.BASE_URL}/seedbox/add',
                data=json.dumps({'url': url, 'wait': False}),
                headers={**self._auth_headers(),
                         'Content-Type': 'application/json'}
            )
            if isinstance(body, dict) and body.get('success'):
                return body.get('value')
        except Exception as e:
            log_utils.log_error(f'DebridLink add error: {e}')
        return None

    def resolve_magnet(self, magnet, title='', season='', episode='',
                       store_to_cloud=False):
        if not self.is_authorized() or not magnet:
            return None

        def _se_match(name, s, e):
            try:
                s, e = int(s), int(e)
            except (TypeError, ValueError):
                return False
            n = name.lower().replace(' ', '.').replace('_', '.').replace('-', '.')
            patterns = (
                r's%02de%02d' % (s, e),
                r's%de%d' % (s, e),
                r'%dx%02d' % (s, e),
                r'%dx%d' % (s, e),
            )
            return any(re.search(p, n) for p in patterns)

        tor = self._add_torrent(magnet)
        if not tor:
            return None
        tid = tor.get('id')
        try:
            if int(tor.get('downloadPercent') or 0) < 100:
                # Not cached - remove and bail (we don't queue uncached)
                if tid:
                    self._remove_torrent(tid)
                return None
            files = tor.get('files') or []
            sources = []
            for f in files:
                name = (f.get('name') or '').strip()
                link = f.get('downloadUrl')
                if not (name and link):
                    continue
                lname = name.lower()
                if not lname.endswith(_VIDEO_EXTS):
                    continue
                if any(k in lname.replace(' ', '.') for k in _EXTRAS_KEYWORDS):
                    continue
                try:
                    size = int(f.get('size') or 0)
                except (TypeError, ValueError):
                    size = 0
                sources.append((size, name, link))
            if not sources:
                return None
            chosen = None
            if season and episode:
                hits = [t for t in sources if _se_match(t[1], season, episode)]
                if hits:
                    chosen = max(hits, key=lambda t: t[0])
                else:
                    hits2 = [t for t in sources
                             if _seas_ep_filter(season, episode, t[1])]
                    if hits2:
                        chosen = max(hits2, key=lambda t: t[0])
            if chosen is None:
                chosen = max(sources, key=lambda t: t[0])
            return chosen[2]
        except Exception as e:
            log_utils.log_error(f'DebridLink resolve error: {e}')
            return None

    def check_cache(self, info_hash):
        """Probe /seedbox/add with bare hash; cached iff downloadPercent==100.
        Always cleans up the seedbox entry afterward.
        """
        if not self.is_authorized() or not info_hash:
            return False
        tor = self._add_torrent(info_hash)
        if not tor:
            return False
        tid = tor.get('id')
        try:
            cached = int(tor.get('downloadPercent') or 0) >= 100
        except (TypeError, ValueError):
            cached = False
        # Always clean up regardless of cached state to keep the seedbox tidy.
        if tid:
            self._remove_torrent(tid)
        return cached


# ---------------------------------------------------------------------------
# Offcloud (offcloud.com) - Real-Debrid-equivalent magnet/cache resolver.
# Authentication: API key (?key=...) appended to every request.
# Endpoints used (all under https://offcloud.com/api):
#   POST /cache              - body {hashes:[...]} -> {cachedItems:[hash,...]}
#   POST /cloud              - body {url: magnet}  -> {requestId, ...}
#   POST /cloud/status       - body {requestId}    -> {status, ...}
#   GET  /cloud/explore/:id  -> JSON array of direct file download URLs
#   GET  /account/stats      - account info (alias used by various clients)
# ---------------------------------------------------------------------------
class Offcloud:
    """Offcloud API integration (Real-Debrid feature parity)."""

    BASE_URL = 'https://offcloud.com/api'

    def __init__(self):
        self.token = ADDON.getSetting('offcloud_token')

    def _url(self, path):
        return f'{self.BASE_URL}{path}?key={self.token}'

    def is_authorized(self):
        return bool(self.token)

    def _verify_key(self, api_key):
        """Validate the API key via a minimal /cache probe."""
        try:
            status, body = _post(
                f'{self.BASE_URL}/cache?key={api_key}',
                data=json.dumps({'hashes': []}),
                headers={'Content-Type': 'application/json'}
            )
            if not (200 <= int(status or 0) < 300):
                return False
            # An invalid key returns an "error" field.
            if isinstance(body, dict) and body.get('error'):
                return False
            return True
        except Exception as e:
            log_utils.log_error(f'Offcloud verify error: {e}')
            return False

    def authorize(self):
        kb = xbmc.Keyboard('', 'Enter Offcloud API Key')
        kb.doModal()
        if not kb.isConfirmed():
            return False
        api_key = kb.getText().strip()
        if not api_key:
            xbmcgui.Dialog().notification(
                'Offcloud', 'API Key is required',
                xbmcgui.NOTIFICATION_ERROR)
            return False
        if self._verify_key(api_key):
            self.token = api_key
            ADDON.setSetting('offcloud_token', api_key)
            ADDON.setSetting('offcloud_enabled', 'true')
            xbmcgui.Dialog().notification(
                'Offcloud', 'Authorization successful!',
                xbmcgui.NOTIFICATION_INFO)
            return True
        xbmcgui.Dialog().notification(
            'Offcloud', 'Invalid API key',
            xbmcgui.NOTIFICATION_ERROR)
        return False

    def revoke(self):
        ADDON.setSetting('offcloud_token', '')
        ADDON.setSetting('offcloud_enabled', 'false')
        self.token = ''

    def account_info(self):
        if not self.is_authorized():
            return None
        # Offcloud has no canonical "account" GET; return a minimal stub.
        return {'apiKey': self.token[:4] + '...' if self.token else None}

    def resolve_magnet(self, magnet, title='', season='', episode='',
                       store_to_cloud=False):
        if not self.is_authorized() or not magnet:
            return None

        def _se_match(name, s, e):
            try:
                s, e = int(s), int(e)
            except (TypeError, ValueError):
                return False
            n = name.lower().replace(' ', '.').replace('_', '.').replace('-', '.')
            patterns = (
                r's%02de%02d' % (s, e),
                r's%de%d' % (s, e),
                r'%dx%02d' % (s, e),
                r'%dx%d' % (s, e),
            )
            return any(re.search(p, n) for p in patterns)

        try:
            # Submit to cloud
            _, body = _post(
                self._url('/cloud'),
                data=json.dumps({'url': magnet}),
                headers={'Content-Type': 'application/json'}
            )
            if not isinstance(body, dict) or body.get('not_available'):
                return None
            request_id = body.get('requestId')
            if not request_id:
                return None

            # Poll status up to ~60s, only for cached results
            ready = (body.get('status') == 'downloaded')
            attempts = 0
            while not ready and attempts < 20:
                xbmc.sleep(3000)
                attempts += 1
                _, status_body = _post(
                    self._url('/cloud/status'),
                    data=json.dumps({'requestId': request_id}),
                    headers={'Content-Type': 'application/json'}
                )
                if isinstance(status_body, dict):
                    # API returns {requests:[{requestId,status,...}]} OR flat
                    st = None
                    if 'requests' in status_body:
                        for r in (status_body.get('requests') or []):
                            if r.get('requestId') == request_id:
                                st = r.get('status')
                                break
                    else:
                        st = status_body.get('status')
                    if st == 'downloaded':
                        ready = True
                        break
                    if st in ('error', 'canceled'):
                        return None
            if not ready:
                return None

            # Explore the archive for actual file URLs
            _, files = _get(self._url(f'/cloud/explore/{request_id}'))
            if not isinstance(files, list):
                return None

            sources = []
            for link in files:
                if not isinstance(link, str):
                    continue
                name = link.rsplit('/', 1)[-1]
                lname = name.lower()
                if not lname.endswith(_VIDEO_EXTS):
                    continue
                if any(k in lname.replace(' ', '.') for k in _EXTRAS_KEYWORDS):
                    continue
                sources.append((0, name, link))

            if not sources:
                return None

            chosen = None
            if season and episode:
                hits = [t for t in sources if _se_match(t[1], season, episode)]
                if hits:
                    chosen = hits[0]
                else:
                    hits2 = [t for t in sources
                             if _seas_ep_filter(season, episode, t[1])]
                    if hits2:
                        chosen = hits2[0]
            if chosen is None:
                # Without size, pick the first video (or the longest filename
                # as a weak proxy for the main file).
                chosen = max(sources, key=lambda t: len(t[1]))
            return chosen[2]
        except Exception as e:
            log_utils.log_error(f'Offcloud resolve error: {e}')
            return None

    def check_cache(self, info_hash):
        if not self.is_authorized() or not info_hash:
            return False
        try:
            _, body = _post(
                self._url('/cache'),
                data=json.dumps({'hashes': [info_hash]}),
                headers={'Content-Type': 'application/json'}
            )
            if isinstance(body, dict):
                cached = body.get('cachedItems') or []
                return info_hash.lower() in {
                    h.lower() for h in cached if isinstance(h, str)
                }
        except Exception as e:
            log_utils.log_error(f'Offcloud cache check error: {e}')
        return False


# ---------------------------------------------------------------------------
# LinkSnappy (linksnappy.com) - Hoster-unlocker debrid (NOT a magnet/torrent
# streamer like RD). LinkSnappy's strength is converting filehoster premium
# links (Uploaded, Rapidgator, etc.) into direct download URLs. Its torrent
# pipeline has no instant-cache API, so we deliberately do NOT implement
# resolve_magnet here - SALTS will skip magnet sources for LinkSnappy and
# only hand it hoster URLs via resolve_url().
# Authentication: username + password (sent on every request as query args).
# Endpoints used (all under https://linksnappy.com/api):
#   GET /AUTH?username=X&password=Y  - validate credentials
#   GET /LINKGEN?genLinks={"link":...}&username=X&password=Y
#   GET /USERSTATUS?username=X&password=Y
# ---------------------------------------------------------------------------
class LinkSnappy:
    """LinkSnappy API integration (hoster-unlocker; no magnet support)."""

    BASE_URL = 'https://linksnappy.com/api'

    def __init__(self):
        self.username = ADDON.getSetting('linksnappy_username')
        self.password = ADDON.getSetting('linksnappy_password')

    def is_authorized(self):
        return bool(self.username and self.password)

    def _verify(self, username, password):
        try:
            _, body = _get(
                f'{self.BASE_URL}/AUTH',
                params={'username': username, 'password': password}
            )
            return (isinstance(body, dict)
                    and body.get('status') == 'OK'
                    and not body.get('error'))
        except Exception as e:
            log_utils.log_error(f'LinkSnappy verify error: {e}')
            return False

    def authorize(self):
        kb1 = xbmc.Keyboard('', 'LinkSnappy Username (email)')
        kb1.doModal()
        if not kb1.isConfirmed():
            return False
        username = kb1.getText().strip()
        kb2 = xbmc.Keyboard('', 'LinkSnappy Password', True)
        kb2.doModal()
        if not kb2.isConfirmed():
            return False
        password = kb2.getText().strip()
        if not (username and password):
            xbmcgui.Dialog().notification(
                'LinkSnappy', 'Username and password required',
                xbmcgui.NOTIFICATION_ERROR)
            return False
        if self._verify(username, password):
            self.username = username
            self.password = password
            ADDON.setSetting('linksnappy_username', username)
            ADDON.setSetting('linksnappy_password', password)
            ADDON.setSetting('linksnappy_enabled', 'true')
            xbmcgui.Dialog().notification(
                'LinkSnappy', 'Authorization successful!',
                xbmcgui.NOTIFICATION_INFO)
            return True
        xbmcgui.Dialog().notification(
            'LinkSnappy', 'Invalid credentials',
            xbmcgui.NOTIFICATION_ERROR)
        return False

    def revoke(self):
        ADDON.setSetting('linksnappy_username', '')
        ADDON.setSetting('linksnappy_password', '')
        ADDON.setSetting('linksnappy_enabled', 'false')
        self.username = ''
        self.password = ''

    def account_info(self):
        if not self.is_authorized():
            return None
        try:
            _, body = _get(
                f'{self.BASE_URL}/USERSTATUS',
                params={'username': self.username, 'password': self.password}
            )
            if isinstance(body, dict) and body.get('status') == 'OK':
                return body.get('return')
        except Exception as e:
            log_utils.log_error(f'LinkSnappy account error: {e}')
        return None

    def supports(self, url):
        """Return True if LinkSnappy might unlock this URL.
        Probes the FILEHOSTS endpoint (cached at module level) for the
        domain. Falls back to True so the resolver can try and let
        LINKGEN respond authoritatively.
        """
        if not url or url.startswith('magnet:'):
            return False
        return True

    def resolve_url(self, url):
        """Convert a hoster URL into a LinkSnappy premium direct link."""
        if not self.is_authorized() or not url or url.startswith('magnet:'):
            return None
        try:
            _, body = _get(
                f'{self.BASE_URL}/linkgen',
                params={
                    'username': self.username,
                    'password': self.password,
                    'genLinks': json.dumps({'link': url}),
                }
            )
            if not isinstance(body, dict):
                return None
            ret = body.get('links') or body.get('return') or []
            if isinstance(ret, list) and ret:
                first = ret[0]
                if isinstance(first, dict):
                    gen = first.get('generated') or first.get('link')
                    if gen and not first.get('error'):
                        return gen
        except Exception as e:
            log_utils.log_error(f'LinkSnappy resolve error: {e}')
        return None

    # No resolve_magnet / check_cache - LinkSnappy is hoster-only.


class Premium:
    """Premium.to filehoster multi-host API integration."""

    BASE_URL = 'http://api.premium.to/api/2'
    _HOSTS_TTL = 300  # seconds - cache hosts list to avoid hammering API

    def __init__(self):
        self.userid = ADDON.getSetting('premiumto_userid')
        self.apikey = ADDON.getSetting('premiumto_apikey')

    # ---------- Auth ----------
    def is_authorized(self):
        return bool(self.userid and self.apikey)

    def _params(self, extra=None):
        p = {'userid': self.userid, 'apikey': self.apikey}
        if extra:
            p.update(extra)
        return p

    def authorize(self):
        """Two-step keyboard prompt: User ID, then API key. Validated via
        the traffic endpoint before being persisted to settings."""
        kb_uid = xbmc.Keyboard('', 'Enter Premium.to User ID')
        kb_uid.doModal()
        if not kb_uid.isConfirmed():
            return False
        userid = kb_uid.getText().strip()

        kb_key = xbmc.Keyboard('', 'Enter Premium.to API Key')
        kb_key.doModal()
        if not kb_key.isConfirmed():
            return False
        apikey = kb_key.getText().strip()

        if not userid or not apikey:
            xbmcgui.Dialog().notification(
                'Premium.to', 'User ID and API Key are required',
                xbmcgui.NOTIFICATION_ERROR)
            return False

        try:
            _, result = _get(f'{self.BASE_URL}/traffic.php',
                             params={'userid': userid, 'apikey': apikey})
            if isinstance(result, dict) and result.get('code') == 200:
                self.userid = userid
                self.apikey = apikey
                ADDON.setSetting('premiumto_userid', userid)
                ADDON.setSetting('premiumto_apikey', apikey)
                ADDON.setSetting('premiumto_enabled', 'true')
                traffic_mb = result.get('traffic', 0)
                xbmcgui.Dialog().notification(
                    'Premium.to',
                    f'Authorized - Traffic: {traffic_mb} MB',
                    xbmcgui.NOTIFICATION_INFO)
                return True
            msg = (result.get('message')
                   if isinstance(result, dict) else 'Invalid response')
            xbmcgui.Dialog().notification(
                'Premium.to', msg or 'Authorization failed',
                xbmcgui.NOTIFICATION_ERROR)
        except Exception as e:
            log_utils.log_error(f'Premium.to auth error: {e}')
            xbmcgui.Dialog().notification(
                'Premium.to', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
        return False

    def revoke(self):
        ADDON.setSetting('premiumto_userid', '')
        ADDON.setSetting('premiumto_apikey', '')
        ADDON.setSetting('premiumto_enabled', 'false')
        self.userid = ''
        self.apikey = ''

    # ---------- Account info ----------
    def get_traffic(self):
        if not self.is_authorized():
            return None
        try:
            _, result = _get(f'{self.BASE_URL}/traffic.php',
                             params=self._params())
            if isinstance(result, dict) and result.get('code') == 200:
                return {
                    'traffic': result.get('traffic', 0),
                    'specialtraffic': result.get('specialtraffic', 0),
                }
        except Exception as e:
            log_utils.log_error(f'Premium.to traffic error: {e}')
        return None

    def get_hosts(self):
        """Enabled file hosts on the user's account (cached briefly)."""
        if not self.is_authorized():
            return []
        now = time.time()
        cached = getattr(self, '_hosts_cache', None)
        if cached and (now - cached[0] < self._HOSTS_TTL):
            return cached[1]
        try:
            _, result = _get(f'{self.BASE_URL}/hosts.php',
                             params=self._params())
            if isinstance(result, dict) and result.get('code') == 200:
                hosts = [h.lower() for h in (result.get('hosts') or [])]
                self._hosts_cache = (now, hosts)
                return hosts
        except Exception as e:
            log_utils.log_error(f'Premium.to hosts error: {e}')
        return []

    # ---------- Host matching ----------
    def supports(self, url):
        """True if `url`'s hostname matches one of the user's enabled hosts."""
        if not url or not self.is_authorized():
            return False
        try:
            from urllib.parse import urlparse
            host = (urlparse(url).hostname or '').lower()
            if not host:
                return False
            for h in self.get_hosts():
                if host == h or host.endswith('.' + h):
                    return True
        except Exception:
            pass
        return False

    # ---------- Resolve ----------
    def resolve_url(self, url):
        """Resolve a supported filehoster link via premium.to.

        getfile.php either returns:
          * 302 -> direct CDN URL (preferred - we capture Location)
          * 200 octet-stream -> Kodi can play directly via the API URL
          * 200 JSON -> auth/traffic/host error
        Returns a stream URL playable by Kodi, or None on error.
        """
        if not self.is_authorized() or not url:
            return None

        api_url = (f'{self.BASE_URL}/getfile.php'
                   f'?userid={quote_plus(self.userid)}'
                   f'&apikey={quote_plus(self.apikey)}'
                   f'&link={quote_plus(url)}')

        try:
            # Custom opener that does NOT follow 30x so we can grab Location.
            import urllib.request as _ur

            class _NoRedirect(_ur.HTTPRedirectHandler):
                def redirect_request(self, *_args, **_kwargs):
                    return None

            opener = _ur.build_opener(_NoRedirect)
            req = Request(api_url, headers={'User-Agent': UA})

            try:
                resp = opener.open(req, timeout=30)
                ctype = (resp.headers.get('Content-Type') or '').lower()
                if 'application/json' in ctype:
                    body = resp.read().decode('utf-8', errors='replace')
                    try:
                        err = json.loads(body)
                        log_utils.log_error(
                            f'Premium.to error {err.get("code")}: '
                            f'{err.get("message")}')
                    except Exception:
                        log_utils.log_error(
                            f'Premium.to error body: {body[:200]}')
                    return None
                # octet-stream: hand the API URL to Kodi; libcurl follows
                # any subsequent redirects natively.
                return api_url
            except HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    loc = e.headers.get('Location')
                    if loc:
                        return loc
                log_utils.log_error(f'Premium.to HTTP {e.code}')
                return None

        except Exception as e:
            log_utils.log_error(f'Premium.to resolve error: {e}')
            return None

    # ---------- Compatibility shims ----------
    # premium.to is filehost-only; magnets are not supported.
    def resolve_magnet(self, *_a, **_kw):
        return None

    def check_cache(self, _info_hash):
        return False
