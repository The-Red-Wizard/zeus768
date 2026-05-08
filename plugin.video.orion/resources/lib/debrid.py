# -*- coding: utf-8 -*-
"""
Debrid Services Integration for Orion
Supports: Real-Debrid, Premiumize, AllDebrid, TorBox
"""

import urllib.request
import urllib.parse
import json
import time
import ssl
import xbmcgui
import xbmcaddon
import xbmc

ADDON = xbmcaddon.Addon()
SSL_CONTEXT = ssl._create_unverified_context()

def http_request(url, data=None, headers=None, method='GET'):
    """Make HTTP request"""
    default_headers = {'User-Agent': 'Orion/2.0'}
    if headers:
        default_headers.update(headers)
    
    if data and isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=default_headers, method=method)
    
    try:
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8'))
        except:
            return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}


def check_cache_batch(hashes):
    """Check multiple hashes against all enabled debrid services.
    Returns dict: {hash_lower: True/False} for cached status.
    A hash is True if ANY service has it cached.
    """
    import re as _re
    
    if not hashes:
        return {}
    
    # Normalize hashes to lowercase
    hashes = [h.lower() for h in hashes]
    result = {h: False for h in hashes}
    
    # Real-Debrid batch cache check
    if ADDON.getSetting('rd_enabled') == 'true':
        rd = RealDebrid()
        if rd.is_authorized():
            try:
                hash_str = '/'.join(hashes)
                url = f"{rd.BASE_URL}/rest/1.0/torrents/instantAvailability/{hash_str}"
                headers = {'Authorization': f'Bearer {rd.token}'}
                rd_result = http_request(url, headers=headers)
                if isinstance(rd_result, dict):
                    for h in hashes:
                        entry = rd_result.get(h) or rd_result.get(h.upper()) or {}
                        if entry.get('rd'):
                            result[h] = True
            except Exception as e:
                xbmc.log(f"RD batch cache check error: {e}", xbmc.LOGWARNING)
    
    if all(result.values()):
        return result
    
    # Premiumize batch cache check
    uncached = [h for h, v in result.items() if not v]
    if uncached and ADDON.getSetting('pm_enabled') == 'true':
        pm = Premiumize()
        if pm.is_authorized():
            try:
                items_str = '&'.join(f'items[]={h}' for h in uncached)
                url = f"{pm.BASE_URL}/cache/check?apikey={pm.token}&{items_str}"
                pm_result = http_request(url)
                if isinstance(pm_result, dict) and pm_result.get('status') == 'success':
                    responses = pm_result.get('response', [])
                    for i, h in enumerate(uncached):
                        if i < len(responses) and responses[i]:
                            result[h] = True
            except Exception as e:
                xbmc.log(f"PM batch cache check error: {e}", xbmc.LOGWARNING)
    
    if all(result.values()):
        return result
    
    # AllDebrid batch cache check
    uncached = [h for h, v in result.items() if not v]
    if uncached and ADDON.getSetting('ad_enabled') == 'true':
        ad = AllDebrid()
        if ad.is_authorized():
            try:
                magnets_str = '&'.join(f'magnets[]={h}' for h in uncached)
                url = f"{ad.BASE_URL}/magnet/instant?agent={ad.AGENT}&apikey={ad.token}&{magnets_str}"
                ad_result = http_request(url)
                if isinstance(ad_result, dict) and ad_result.get('status') == 'success':
                    magnets = ad_result.get('data', {}).get('magnets', [])
                    for i, h in enumerate(uncached):
                        if i < len(magnets) and magnets[i].get('instant'):
                            result[h] = True
            except Exception as e:
                xbmc.log(f"AD batch cache check error: {e}", xbmc.LOGWARNING)
    
    if all(result.values()):
        return result
    
    # TorBox batch cache check
    uncached = [h for h, v in result.items() if not v]
    if uncached and ADDON.getSetting('tb_enabled') == 'true':
        tb = TorBox()
        if tb.is_authorized():
            try:
                hash_csv = ','.join(uncached)
                url = f'{tb.BASE_URL}/torrents/checkcached?hash={hash_csv}&format=list'
                tb_result = http_request(url, headers=tb._auth_headers())
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
                xbmc.log(f"TB batch cache check error: {e}", xbmc.LOGWARNING)
    
    return result


class RealDebrid:
    """Real-Debrid API Integration"""
    
    BASE_URL = "https://api.real-debrid.com"
    CLIENT_ID = "X245A4XAIBGVM"
    
    def __init__(self):
        self.token = ADDON.getSetting('rd_token')
        self.refresh_token = ADDON.getSetting('rd_refresh')
        self.client_id = ADDON.getSetting('rd_client_id') or self.CLIENT_ID
        self.client_secret = ADDON.getSetting('rd_client_secret')
    
    def pair(self):
        """Start device pairing"""
        try:
            # Get device code
            url = f"{self.BASE_URL}/oauth/v2/device/code?client_id={self.client_id}&new_credentials=yes"
            data = http_request(url)
            
            if 'error' in data:
                xbmcgui.Dialog().ok('Real-Debrid Error', str(data.get('error')))
                return False
            
            device_code = data['device_code']
            user_code = data['user_code']
            verification_url = data.get('verification_url', 'https://real-debrid.com/device')
            expires_in = data.get('expires_in', 600)
            interval = data.get('interval', 5)
            
            # Show progress dialog
            progress = xbmcgui.DialogProgress()
            progress.create(
                'Real-Debrid Authorization',
                f'Visit: [COLOR cyan]{verification_url}[/COLOR]\n'
                f'Enter Code: [COLOR yellow]{user_code}[/COLOR]\n'
                'Waiting for authorization...'
            )
            
            start_time = time.time()
            while not progress.iscanceled():
                elapsed = time.time() - start_time
                if elapsed > expires_in:
                    progress.close()
                    xbmcgui.Dialog().ok('Real-Debrid', 'Authorization timed out')
                    return False
                
                progress.update(int((elapsed / expires_in) * 100))
                
                time.sleep(interval)
                
                # Check for credentials
                cred_url = f"{self.BASE_URL}/oauth/v2/device/credentials?client_id={self.client_id}&code={device_code}"
                cred_data = http_request(cred_url)
                
                if 'client_secret' in cred_data:
                    # Got credentials, now get token
                    client_id = cred_data['client_id']
                    client_secret = cred_data['client_secret']
                    
                    token_url = f"{self.BASE_URL}/oauth/v2/token"
                    token_data = http_request(token_url, {
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'code': device_code,
                        'grant_type': 'http://oauth.net/grant_type/device/1.0'
                    }, method='POST')
                    
                    if 'access_token' in token_data:
                        ADDON.setSetting('rd_token', token_data['access_token'])
                        ADDON.setSetting('rd_refresh', token_data.get('refresh_token', ''))
                        ADDON.setSetting('rd_client_id', client_id)
                        ADDON.setSetting('rd_client_secret', client_secret)
                        
                        progress.close()
                        xbmcgui.Dialog().ok('Real-Debrid', '[COLOR lime]Successfully authorized![/COLOR]')
                        return True
            
            progress.close()
            return False
            
        except Exception as e:
            xbmcgui.Dialog().ok('Real-Debrid Error', str(e))
            return False
    
    def is_authorized(self):
        """Check if authorized"""
        return bool(self.token)
    
    def add_magnet(self, magnet):
        """Add magnet link to Real-Debrid"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/rest/1.0/torrents/addMagnet"
        headers = {'Authorization': f'Bearer {self.token}'}
        data = http_request(url, {'magnet': magnet}, headers, method='POST')
        
        return data.get('id')
    
    def get_torrent_info(self, torrent_id):
        """Get torrent information"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/rest/1.0/torrents/info/{torrent_id}"
        headers = {'Authorization': f'Bearer {self.token}'}
        return http_request(url, headers=headers)
    
    def select_files(self, torrent_id, files='all'):
        """Select files to download"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/rest/1.0/torrents/selectFiles/{torrent_id}"
        headers = {'Authorization': f'Bearer {self.token}'}
        return http_request(url, {'files': files}, headers, method='POST')
    
    def unrestrict_link(self, link):
        """Unrestrict a link for streaming"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/rest/1.0/unrestrict/link"
        headers = {'Authorization': f'Bearer {self.token}'}
        data = http_request(url, {'link': link}, headers, method='POST')
        
        return data.get('download')
    
    def resolve_magnet(self, magnet, progress=None):
        """Resolve magnet to stream URL"""
        VIDEO_EXTS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.mpg', '.mpeg', '.ts', '.webm')
        
        try:
            if progress:
                progress.update(10, 'Adding magnet to Real-Debrid...')
            
            torrent_id = self.add_magnet(magnet)
            if not torrent_id:
                return None
            
            if progress:
                progress.update(20, 'Getting file list...')
            
            # Get torrent info to find video files before selecting
            info = self.get_torrent_info(torrent_id)
            files = info.get('files', [])
            
            # Pick only video files by extension, select largest
            video_file_ids = []
            for f in files:
                path = f.get('path', '').lower()
                if path.endswith(VIDEO_EXTS):
                    video_file_ids.append(str(f.get('id', 0)))
            
            if progress:
                progress.update(30, 'Selecting video files...')
            
            if video_file_ids:
                self.select_files(torrent_id, ','.join(video_file_ids))
            else:
                # Fallback: select all and hope for the best
                self.select_files(torrent_id)
            
            # Wait for torrent to be ready
            for i in range(60):
                if progress:
                    progress.update(30 + i, 'Processing torrent...')
                
                info = self.get_torrent_info(torrent_id)
                status = info.get('status')
                
                if status == 'downloaded':
                    links = info.get('links', [])
                    if links:
                        if progress:
                            progress.update(90, 'Getting stream link...')
                        
                        # Try each link, prefer video files
                        for link in links:
                            stream_url = self.unrestrict_link(link)
                            if stream_url:
                                # Check the resolved URL is a video, not .rar/.zip
                                url_lower = stream_url.lower().split('?')[0]
                                if url_lower.endswith(('.rar', '.zip', '.7z', '.nfo', '.txt', '.srt')):
                                    xbmc.log(f"RealDebrid: Skipping non-video link: {stream_url[:80]}", xbmc.LOGINFO)
                                    continue
                                return stream_url
                        
                        # If all links were archives, try first one anyway as last resort
                        if links:
                            return self.unrestrict_link(links[0])
                elif status in ['error', 'dead', 'magnet_error']:
                    return None
                
                time.sleep(2)
            
            return None
        except Exception as e:
            xbmc.log(f"RealDebrid resolve error: {e}", xbmc.LOGERROR)
            return None


class Premiumize:
    """Premiumize API Integration"""
    
    BASE_URL = "https://www.premiumize.me/api"
    
    def __init__(self):
        self.token = ADDON.getSetting('pm_token')
    
    def pair(self):
        """Start device pairing"""
        try:
            # Get device code - Premiumize uses different endpoint
            url = f"{self.BASE_URL}/device/code"
            data = http_request(url)
            
            if data.get('status') != 'success':
                xbmcgui.Dialog().ok('Premiumize Error', data.get('message', 'Failed to get device code'))
                return False
            
            device_code = data['device_code']
            user_code = data['user_code']
            verification_url = data.get('verification_uri', 'https://premiumize.me/device')
            expires_in = data.get('expires_in', 600)
            interval = data.get('interval', 5)
            
            # Show progress dialog
            progress = xbmcgui.DialogProgress()
            progress.create(
                'Premiumize Authorization',
                f'Visit: [COLOR cyan]{verification_url}[/COLOR]\n'
                f'Enter Code: [COLOR yellow]{user_code}[/COLOR]\n'
                'Waiting for authorization...'
            )
            
            start_time = time.time()
            while not progress.iscanceled():
                elapsed = time.time() - start_time
                if elapsed > expires_in:
                    progress.close()
                    xbmcgui.Dialog().ok('Premiumize', 'Authorization timed out')
                    return False
                
                progress.update(int((elapsed / expires_in) * 100))
                
                time.sleep(interval)
                
                # Check for token
                check_url = f"{self.BASE_URL}/device/check"
                check_data = http_request(check_url, {'code': device_code}, method='POST')
                
                if check_data.get('status') == 'success' and 'apikey' in check_data:
                    ADDON.setSetting('pm_token', check_data['apikey'])
                    
                    progress.close()
                    xbmcgui.Dialog().ok('Premiumize', '[COLOR lime]Successfully authorized![/COLOR]')
                    return True
            
            progress.close()
            return False
            
        except Exception as e:
            xbmcgui.Dialog().ok('Premiumize Error', str(e))
            return False
    
    def is_authorized(self):
        """Check if authorized"""
        return bool(self.token)
    
    def add_magnet(self, magnet):
        """Add magnet to Premiumize"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/transfer/create"
        data = http_request(url, {'apikey': self.token, 'src': magnet}, method='POST')
        
        return data.get('id')
    
    def get_transfer(self, transfer_id):
        """Get transfer status"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/transfer/list"
        data = http_request(url, {'apikey': self.token}, method='POST')
        
        for transfer in data.get('transfers', []):
            if transfer.get('id') == transfer_id:
                return transfer
        return None
    
    def direct_download(self, magnet):
        """Direct download via cache"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/transfer/directdl"
        data = http_request(url, {'apikey': self.token, 'src': magnet}, method='POST')
        
        if data.get('status') == 'success':
            content = data.get('content', [])
            if content:
                # Find largest video file
                videos = [f for f in content if f.get('stream_link')]
                if videos:
                    videos.sort(key=lambda x: x.get('size', 0), reverse=True)
                    return videos[0].get('stream_link')
        return None
    
    def resolve_magnet(self, magnet, progress=None):
        """Resolve magnet to stream URL"""
        try:
            if progress:
                progress.update(20, 'Checking Premiumize cache...')
            
            # Try direct download first (cached)
            stream_url = self.direct_download(magnet)
            if stream_url:
                return stream_url
            
            if progress:
                progress.update(40, 'Adding to Premiumize cloud...')
            
            # Add to cloud if not cached
            transfer_id = self.add_magnet(magnet)
            if not transfer_id:
                return None
            
            # Wait for transfer
            for i in range(60):
                if progress:
                    progress.update(40 + i, 'Waiting for transfer...')
                
                transfer = self.get_transfer(transfer_id)
                if transfer:
                    status = transfer.get('status')
                    if status == 'finished':
                        folder_id = transfer.get('folder_id')
                        if folder_id:
                            # Get folder contents
                            stream_url = self.direct_download(magnet)
                            if stream_url:
                                return stream_url
                    elif status in ['error', 'deleted']:
                        return None
                
                time.sleep(3)
            
            return None
        except Exception as e:
            xbmc.log(f"Premiumize resolve error: {e}", xbmc.LOGERROR)
            return None


class AllDebrid:
    """AllDebrid API Integration"""
    
    BASE_URL = "https://api.alldebrid.com/v4"
    AGENT = "Orion"
    
    def __init__(self):
        self.token = ADDON.getSetting('ad_token')
    
    def pair(self):
        """Start PIN pairing"""
        try:
            # Get PIN
            url = f"{self.BASE_URL}/pin/get?agent={self.AGENT}"
            data = http_request(url)
            
            if data.get('status') != 'success':
                xbmcgui.Dialog().ok('AllDebrid Error', data.get('error', {}).get('message', 'Failed to get PIN'))
                return False
            
            pin_data = data.get('data', {})
            pin = pin_data.get('pin')
            check_code = pin_data.get('check')
            verification_url = pin_data.get('user_url', 'https://alldebrid.com/pin')
            expires_in = pin_data.get('expires_in', 600)
            
            # Show progress dialog
            progress = xbmcgui.DialogProgress()
            progress.create(
                'AllDebrid Authorization',
                f'Visit: [COLOR cyan]{verification_url}[/COLOR]\n'
                f'Enter PIN: [COLOR yellow]{pin}[/COLOR]\n'
                'Waiting for authorization...'
            )
            
            start_time = time.time()
            while not progress.iscanceled():
                elapsed = time.time() - start_time
                if elapsed > expires_in:
                    progress.close()
                    xbmcgui.Dialog().ok('AllDebrid', 'Authorization timed out')
                    return False
                
                progress.update(int((elapsed / expires_in) * 100))
                
                time.sleep(5)
                
                # Check for token
                check_url = f"{self.BASE_URL}/pin/check?agent={self.AGENT}&check={check_code}&pin={pin}"
                check_data = http_request(check_url)
                
                if check_data.get('status') == 'success':
                    pin_result = check_data.get('data', {})
                    if pin_result.get('activated'):
                        apikey = pin_result.get('apikey')
                        if apikey:
                            ADDON.setSetting('ad_token', apikey)
                            
                            progress.close()
                            xbmcgui.Dialog().ok('AllDebrid', '[COLOR lime]Successfully authorized![/COLOR]')
                            return True
            
            progress.close()
            return False
            
        except Exception as e:
            xbmcgui.Dialog().ok('AllDebrid Error', str(e))
            return False
    
    def is_authorized(self):
        """Check if authorized"""
        return bool(self.token)
    
    def add_magnet(self, magnet):
        """Add magnet to AllDebrid"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/magnet/upload?agent={self.AGENT}&apikey={self.token}"
        data = http_request(url, {'magnets[]': magnet}, method='POST')
        
        if data.get('status') == 'success':
            magnets = data.get('data', {}).get('magnets', [])
            if magnets:
                return magnets[0].get('id')
        return None
    
    def get_magnet_status(self, magnet_id):
        """Get magnet status"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/magnet/status?agent={self.AGENT}&apikey={self.token}&id={magnet_id}"
        data = http_request(url)
        
        if data.get('status') == 'success':
            return data.get('data', {}).get('magnets')
        return None
    
    def unlock_link(self, link):
        """Unlock link for streaming"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/link/unlock?agent={self.AGENT}&apikey={self.token}&link={urllib.parse.quote(link)}"
        data = http_request(url)
        
        if data.get('status') == 'success':
            return data.get('data', {}).get('link')
        return None
    
    def instant_availability(self, magnet):
        """Check instant availability (cached)"""
        if not self.token:
            return None
        
        url = f"{self.BASE_URL}/magnet/instant?agent={self.AGENT}&apikey={self.token}&magnets[]={urllib.parse.quote(magnet)}"
        data = http_request(url)
        
        if data.get('status') == 'success':
            magnets = data.get('data', {}).get('magnets', [])
            if magnets and magnets[0].get('instant'):
                return True
        return False
    
    def resolve_magnet(self, magnet, progress=None):
        """Resolve magnet to stream URL"""
        try:
            if progress:
                progress.update(10, 'Adding magnet to AllDebrid...')
            
            magnet_id = self.add_magnet(magnet)
            if not magnet_id:
                return None
            
            # Wait for magnet to be ready
            for i in range(60):
                if progress:
                    progress.update(20 + i, 'Processing magnet...')
                
                status = self.get_magnet_status(magnet_id)
                if status:
                    magnet_status = status.get('status')
                    if magnet_status == 'Ready':
                        links = status.get('links', [])
                        if links:
                            if progress:
                                progress.update(90, 'Unlocking stream...')
                            
                            # Find largest video file
                            video_links = [l for l in links if l.get('filename', '').lower().endswith(('.mp4', '.mkv', '.avi', '.mov'))]
                            if video_links:
                                video_links.sort(key=lambda x: x.get('size', 0), reverse=True)
                                link = video_links[0].get('link')
                            else:
                                link = links[0].get('link')
                            
                            if link:
                                stream_url = self.unlock_link(link)
                                return stream_url
                    elif magnet_status in ['Error', 'Virus']:
                        return None
                
                time.sleep(2)
            
            return None
        except Exception as e:
            xbmc.log(f"AllDebrid resolve error: {e}", xbmc.LOGERROR)
            return None


class TorBox:
    """TorBox API Integration (https://api.torbox.app)"""
    
    BASE_URL = 'https://api.torbox.app/v1/api'
    
    def __init__(self):
        self.token = ADDON.getSetting('tb_token')
    
    def _auth_headers(self):
        return {'Authorization': f'Bearer {self.token}'}
    
    def is_authorized(self):
        return bool(self.token)
    
    def pair(self):
        """TorBox device code authorization (JSON POST required by API)"""
        try:
            xbmc.log('TorBox: Requesting device code...', xbmc.LOGINFO)

            # Step 1: Get device code via GET
            start_url = f'{self.BASE_URL}/user/auth/device/start'
            result = http_request(start_url)

            if not isinstance(result, dict) or not result.get('success'):
                xbmcgui.Dialog().ok('TorBox', 'Failed to get device code. Try again.')
                return False

            data = result.get('data', {})
            device_code = data.get('device_code', '')
            user_code = data.get('code') or data.get('user_code') or ''
            verify_url = data.get('friendly_verification_url') or data.get('verification_url') or 'https://torbox.app/devices'
            interval = data.get('interval', 5)
            # TorBox returns expires_at (ISO timestamp), not expires_in
            expires_in = 600
            exp_at = data.get('expires_at')
            if exp_at:
                try:
                    from datetime import datetime, timezone as tz
                    ts = exp_at.replace('Z', '+00:00')
                    exp_dt = datetime.fromisoformat(ts)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=tz.utc)
                    expires_in = max(60, int(exp_dt.timestamp() - time.time()))
                except Exception:
                    pass

            if not device_code or not user_code:
                xbmcgui.Dialog().ok('TorBox', 'No device code received.')
                return False

            xbmc.log(f'TorBox: Got device code, user_code: {user_code}', xbmc.LOGINFO)

            # Step 2: Show code and poll
            dialog = xbmcgui.DialogProgress()
            dialog.create(
                'TorBox Authorization',
                f'Go to: [COLOR cyan]{verify_url}[/COLOR]\n\n'
                f'Enter Code: [COLOR yellow]{user_code}[/COLOR]\n\n'
                'Waiting for authorization...'
            )

            import time as _time
            start = _time.time()
            while _time.time() - start < expires_in:
                if dialog.iscanceled():
                    dialog.close()
                    return False

                _time.sleep(interval)
                elapsed = _time.time() - start
                remaining = max(0, expires_in - elapsed)
                pct = int((elapsed / expires_in) * 100)
                dialog.update(
                    pct,
                    f'Go to: [COLOR cyan]{verify_url}[/COLOR]\n\n'
                    f'Enter Code: [COLOR yellow]{user_code}[/COLOR]\n\n'
                    f'Time remaining: {int(remaining)} seconds'
                )

                try:
                    # TorBox requires JSON POST for token endpoint
                    token_url = f'{self.BASE_URL}/user/auth/device/token'
                    import json as _json
                    from urllib.request import Request, urlopen
                    req = Request(
                        token_url,
                        data=_json.dumps({"device_code": device_code}).encode('utf-8'),
                        headers={
                            'Content-Type': 'application/json',
                            'User-Agent': 'Orion/3.0 (Kodi)'
                        },
                        method='POST'
                    )
                    resp = urlopen(req, timeout=15)
                    poll_result = _json.loads(resp.read().decode('utf-8'))

                    xbmc.log(f'TorBox poll result: {poll_result}', xbmc.LOGDEBUG)

                    if isinstance(poll_result, dict) and poll_result.get('success'):
                        token_data = poll_result.get('data', {})
                        api_key = token_data.get('access_token') or token_data.get('api_key') or token_data.get('token') or ''
                        if api_key:
                            self.token = api_key
                            ADDON.setSetting('tb_token', api_key)
                            ADDON.setSetting('tb_enabled', 'true')
                            dialog.close()
                            xbmcgui.Dialog().notification('TorBox', 'Authorization successful!', xbmcgui.NOTIFICATION_INFO)
                            xbmc.log('TorBox: Authorization successful', xbmc.LOGINFO)
                            return True
                except Exception as poll_err:
                    # authorization_pending or other transient error - keep polling
                    xbmc.log(f'TorBox poll: {poll_err}', xbmc.LOGDEBUG)

            dialog.close()
            xbmcgui.Dialog().notification('TorBox', 'Authorization timeout', xbmcgui.NOTIFICATION_WARNING)
            return False

        except Exception as e:
            xbmc.log(f'TorBox auth error: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('TorBox', f'Error: {e}', xbmcgui.NOTIFICATION_ERROR)
            return False
    
    def check_cache(self, info_hash):
        """Check if torrent is cached on TorBox"""
        if not self.token:
            return False
        try:
            url = f'{self.BASE_URL}/torrents/checkcached?hash={info_hash}&format=list'
            result = http_request(url, headers=self._auth_headers())
            if isinstance(result, dict) and result.get('success'):
                cached_data = result.get('data', [])
                return bool(cached_data)
        except Exception:
            pass
        return False
    
    def resolve_magnet(self, magnet, progress=None):
        """Resolve magnet link to direct download via TorBox"""
        if not self.token:
            return None
        
        try:
            import re as _re
            
            if progress:
                progress.update(10, 'Checking TorBox cache...')
            
            # Extract hash from magnet
            hash_match = _re.search(r'btih:([a-fA-F0-9]{40})', magnet)
            if not hash_match:
                hash_match = _re.search(r'btih:([a-zA-Z2-7]{32})', magnet)
            
            # Step 1: Create torrent (add magnet) using multipart form
            if progress:
                progress.update(20, 'Adding magnet to TorBox...')
            
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
            
            url = f'{self.BASE_URL}/torrents/createtorrent'
            req = urllib.request.Request(url, data=body_data, headers=create_headers, method='POST')
            
            try:
                with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=30) as response:
                    result = json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                try:
                    result = json.loads(e.read().decode('utf-8'))
                except:
                    result = {'error': str(e)}
            
            if not isinstance(result, dict) or not result.get('success'):
                xbmc.log(f"TorBox createtorrent failed: {result}", xbmc.LOGERROR)
                return None
            
            torrent_id = result.get('data', {}).get('torrent_id')
            if not torrent_id:
                return None
            
            # Step 2: Wait for ready and get file list
            if progress:
                progress.update(40, 'Processing torrent on TorBox...')
            
            for i in range(30):
                if progress:
                    progress.update(40 + i, 'Waiting for TorBox...')
                
                info_url = f'{self.BASE_URL}/torrents/mylist?id={torrent_id}'
                info_result = http_request(info_url, headers=self._auth_headers())
                
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
                            if progress:
                                progress.update(85, 'Getting TorBox stream link...')
                            
                            dl_url = f'{self.BASE_URL}/torrents/requestdl?token={self.token}&torrent_id={torrent_id}&file_id={file_id}'
                            dl_result = http_request(dl_url, headers=self._auth_headers())
                            
                            if isinstance(dl_result, dict) and dl_result.get('success'):
                                download_url = dl_result.get('data')
                                if download_url:
                                    return download_url
                        break
                    elif dl_state in ('error', 'stalled'):
                        return None
                
                time.sleep(2)
            
            return None
            
        except Exception as e:
            xbmc.log(f"TorBox resolve error: {e}", xbmc.LOGERROR)
            return None