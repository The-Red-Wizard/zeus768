"""
SALTS Library - Debrid Service Integration
Supports Real-Debrid, Premiumize, AllDebrid, TorBox
Revived by zeus768 for Kodi 21+
Uses native urllib (no external requests module)
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
 
 # TorBox batch cache check
 uncached = [h for h, v in result.items() if not v]
 if uncached and ADDON.getSetting('torbox_enabled') == 'true':
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
 h = item.get('hash', '').lower()
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
 self.token = ADDON.getSetting('realdebrid_token') or ''
 self.refresh_token = ADDON.getSetting('realdebrid_refresh') or ''
 try:
  self.client_id = ADDON.getSetting('realdebrid_client_id') or self.CLIENT_ID
 except:
  self.client_id = self.CLIENT_ID
 try:
  self.client_secret = ADDON.getSetting('realdebrid_client_secret') or ''
 except:
  self.client_secret = ''
 try:
  self.expires = float(ADDON.getSetting('realdebrid_expires') or 0)
 except:
  self.expires = 0
 
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
 """TorBox API integration (https://api.torbox.app)"""
 
 BASE_URL = 'https://api.torbox.app/v1/api'
 
 def __init__(self):
 self.token = ADDON.getSetting('torbox_token')
 
 def _auth_headers(self):
 return {'Authorization': f'Bearer {self.token}'}
 
 def is_authorized(self):
 return bool(self.token)
 
 def authorize(self):
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
 ADDON.setSetting('torbox_token', api_key)
 ADDON.setSetting('torbox_enabled', 'true')
 
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
 log_utils.log_error(f'TorBox auth error: {e}')
 xbmcgui.Dialog().notification('TorBox', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
 return False
 
 def resolve_magnet(self, magnet):
 """Resolve magnet link to direct download via TorBox"""
 if not self.is_authorized():
 return None
 
 try:
 # Extract hash from magnet
 hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
 if not hash_match:
 hash_match = re.search(r'btih:([a-zA-Z2-7]{32})', magnet)
 
 # Step 1: Check if cached first
 if hash_match:
 info_hash = hash_match.group(1).lower()
 cache_status, cache_result = _get(
 f'{self.BASE_URL}/torrents/checkcached',
 params={'hash': info_hash, 'format': 'list'},
 headers=self._auth_headers()
 )
 
 is_cached = False
 if isinstance(cache_result, dict) and cache_result.get('success'):
 cached_data = cache_result.get('data', [])
 if cached_data:
 is_cached = True
 
 # Step 2: Create torrent (add magnet)
 # Use multipart-like form data for createtorrent
 import io
 boundary = '----SALTSBoundary'
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
 log_utils.log_error(f'TorBox createtorrent failed: {result}')
 return None
 
 torrent_id = result.get('data', {}).get('torrent_id')
 if not torrent_id:
 return None
 
 # Step 3: Wait for ready and get file list
 for _ in range(30):
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
 
 # Step 4: Request download link
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
 return download_url
 break
 
 time.sleep(2)
 
 return None
 
 except Exception as e:
 log_utils.log_error(f'TorBox resolve error: {e}')
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