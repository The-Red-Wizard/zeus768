# -*- coding: utf-8 -*-
"""
Debrid Services Integration for Orion
Supports: Real-Debrid, Premiumize, AllDebrid
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
        try:
            if progress:
                progress.update(10, 'Adding magnet to Real-Debrid...')
            
            torrent_id = self.add_magnet(magnet)
            if not torrent_id:
                return None
            
            if progress:
                progress.update(30, 'Selecting files...')
            
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
                        
                        # Find largest video file
                        stream_url = self.unrestrict_link(links[0])
                        return stream_url
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