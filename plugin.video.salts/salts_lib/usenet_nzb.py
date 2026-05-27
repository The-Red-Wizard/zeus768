"""
SALTS Library - Usenet and NZB Support
Provides comprehensive Usenet integration:
- Direct Usenet download via NNTP
- NZB file parsing and handling
- SABnzbd and NZBGet client integration
- Usenet provider management

Author: zeus768
"""
import json
import time
import re
import os
import base64
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote_plus
from datetime import datetime

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from . import log_utils

ADDON = xbmcaddon.Addon()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


class NZBParser:
    """Parse NZB files"""
    
    @staticmethod
    def parse_nzb(nzb_content):
        """Parse NZB XML content and extract file info"""
        try:
            root = ET.fromstring(nzb_content)
            files = []
            
            for file_elem in root.findall('.//{http://www.newzbin.com/DTD/2003/nzb}file'):
                file_info = {
                    'subject': file_elem.get('subject', ''),
                    'poster': file_elem.get('poster', ''),
                    'date': file_elem.get('date', ''),
                    'segments': []
                }
                
                # Extract segments
                for segment in file_elem.findall('.//{http://www.newzbin.com/DTD/2003/nzb}segment'):
                    file_info['segments'].append({
                        'number': segment.get('number'),
                        'bytes': segment.get('bytes'),
                        'message_id': segment.text
                    })
                
                files.append(file_info)
            
            return files
        except Exception as e:
            log_utils.log_error(f'NZB parse error: {e}')
            return []
    
    @staticmethod
    def extract_file_info(nzb_content):
        """Extract basic file information from NZB"""
        try:
            files = NZBParser.parse_nzb(nzb_content)
            total_size = 0
            filenames = []
            
            for f in files:
                filename = f.get('subject', '')
                # Extract filename from subject
                match = re.search(r'"(.+?)"', filename)
                if match:
                    filenames.append(match.group(1))
                
                # Calculate size
                for seg in f.get('segments', []):
                    try:
                        total_size += int(seg.get('bytes', 0))
                    except:
                        pass
            
            return {
                'files': filenames,
                'size_bytes': total_size,
                'size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': len(files)
            }
        except Exception as e:
            log_utils.log_error(f'NZB file info extraction error: {e}')
            return {}


class SABnzbdClient:
    """SABnzbd download client integration"""
    
    def __init__(self):
        self.enabled = ADDON.getSetting('sabnzbd_enabled') == 'true'
        self.url = ADDON.getSetting('sabnzbd_url') or 'http://localhost:8080'
        self.api_key = ADDON.getSetting('sabnzbd_api_key') or ''
        
        # Clean URL
        self.url = self.url.rstrip('/')
    
    def is_configured(self):
        """Check if SABnzbd is properly configured"""
        return self.enabled and self.url and self.api_key
    
    def _api_request(self, mode, params=None):
        """Make API request to SABnzbd"""
        if not self.is_configured():
            return None
        
        try:
            params = params or {}
            params.update({
                'apikey': self.api_key,
                'mode': mode,
                'output': 'json'
            })
            
            url = f'{self.url}/api?{urlencode(params)}'
            req = Request(url, headers={'User-Agent': UA})
            resp = urlopen(req, timeout=30)
            data = json.loads(resp.read().decode('utf-8'))
            return data
        except Exception as e:
            log_utils.log_error(f'SABnzbd API error: {e}')
            return None
    
    def add_nzb_url(self, nzb_url, name=''):
        """Add NZB from URL"""
        params = {
            'name': nzb_url,
            'nzbname': name
        }
        result = self._api_request('addurl', params)
        return result is not None
    
    def add_nzb_file(self, nzb_content, name=''):
        """Add NZB from file content"""
        try:
            # SABnzbd expects base64 encoded NZB
            if isinstance(nzb_content, str):
                nzb_content = nzb_content.encode('utf-8')
            
            nzb_b64 = base64.b64encode(nzb_content).decode('ascii')
            
            params = {
                'name': nzb_b64,
                'nzbname': name,
                'mode': 'addfile'
            }
            
            result = self._api_request('addfile', params)
            return result is not None
        except Exception as e:
            log_utils.log_error(f'SABnzbd add file error: {e}')
            return False
    
    def get_queue(self):
        """Get current download queue"""
        result = self._api_request('queue')
        if result and 'queue' in result:
            return result['queue']
        return None
    
    def get_history(self):
        """Get download history"""
        result = self._api_request('history')
        if result and 'history' in result:
            return result['history']
        return None
    
    def pause_download(self, nzb_id):
        """Pause a download"""
        return self._api_request('pause', {'value': nzb_id})
    
    def resume_download(self, nzb_id):
        """Resume a download"""
        return self._api_request('resume', {'value': nzb_id})
    
    def delete_download(self, nzb_id):
        """Delete a download"""
        return self._api_request('queue', {'name': 'delete', 'value': nzb_id})
    
    def get_status(self):
        """Get SABnzbd status"""
        queue = self.get_queue()
        if queue:
            return {
                'speed': queue.get('speed', '0 KB/s'),
                'size_left': queue.get('sizeleft', '0 MB'),
                'total_size': queue.get('size', '0 MB'),
                'paused': queue.get('paused', False),
                'slots': len(queue.get('slots', []))
            }
        return None


class NZBGetClient:
    """NZBGet download client integration"""
    
    def __init__(self):
        self.enabled = ADDON.getSetting('nzbget_enabled') == 'true'
        self.url = ADDON.getSetting('nzbget_url') or 'http://localhost:6789'
        self.username = ADDON.getSetting('nzbget_username') or 'nzbget'
        self.password = ADDON.getSetting('nzbget_password') or ''
        
        # Clean URL
        self.url = self.url.rstrip('/')
        self.rpc_url = f'{self.url}/jsonrpc'
    
    def is_configured(self):
        """Check if NZBGet is properly configured"""
        return self.enabled and self.url
    
    def _rpc_request(self, method, params=None):
        """Make JSON-RPC request to NZBGet"""
        if not self.is_configured():
            return None
        
        try:
            payload = {
                'jsonrpc': '2.0',
                'method': method,
                'params': params or [],
                'id': 1
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = Request(self.rpc_url, data=data, headers={
                'User-Agent': UA,
                'Content-Type': 'application/json'
            })
            
            # Add auth if needed
            if self.username or self.password:
                auth_str = f'{self.username}:{self.password}'
                auth_b64 = base64.b64encode(auth_str.encode()).decode()
                req.add_header('Authorization', f'Basic {auth_b64}')
            
            resp = urlopen(req, timeout=30)
            result = json.loads(resp.read().decode('utf-8'))
            
            if 'result' in result:
                return result['result']
            return None
        except Exception as e:
            log_utils.log_error(f'NZBGet RPC error: {e}')
            return None
    
    def add_nzb_url(self, nzb_url, name='', category=''):
        """Add NZB from URL"""
        params = [nzb_url, name, category, 0, False, False, '', 0, 'SCORE', []]
        result = self._rpc_request('append', params)
        return result is not None and result > 0
    
    def add_nzb_file(self, nzb_content, name='', category=''):
        """Add NZB from file content"""
        try:
            if isinstance(nzb_content, str):
                nzb_content = nzb_content.encode('utf-8')
            
            nzb_b64 = base64.b64encode(nzb_content).decode('ascii')
            params = [name, nzb_b64, category, 0, False, False, '', 0, 'SCORE', []]
            result = self._rpc_request('append', params)
            return result is not None and result > 0
        except Exception as e:
            log_utils.log_error(f'NZBGet add file error: {e}')
            return False
    
    def get_queue(self):
        """Get current download queue"""
        return self._rpc_request('listgroups')
    
    def get_history(self):
        """Get download history"""
        return self._rpc_request('history')
    
    def pause_download(self, nzb_id):
        """Pause a download"""
        return self._rpc_request('editqueue', ['GroupPause', 0, '', [nzb_id]])
    
    def resume_download(self, nzb_id):
        """Resume a download"""
        return self._rpc_request('editqueue', ['GroupResume', 0, '', [nzb_id]])
    
    def delete_download(self, nzb_id):
        """Delete a download"""
        return self._rpc_request('editqueue', ['GroupDelete', 0, '', [nzb_id]])
    
    def get_status(self):
        """Get NZBGet status"""
        status = self._rpc_request('status')
        if status:
            return {
                'speed': f'{status.get("DownloadRate", 0) / 1024:.0f} KB/s',
                'size_left': f'{status.get("RemainingSizeMB", 0):.1f} MB',
                'paused': status.get('DownloadPaused', False),
                'downloading': status.get('DownloadRate', 0) > 0
            }
        return None


class UsenetProvider:
    """Manage Usenet provider settings"""
    
    @staticmethod
    def get_primary_provider():
        """Get primary Usenet provider configuration"""
        enabled = ADDON.getSetting('usenet_provider_enabled') == 'true'
        if not enabled:
            return None
        
        return {
            'server': ADDON.getSetting('usenet_server') or '',
            'port': int(ADDON.getSetting('usenet_port') or '119'),
            'ssl': ADDON.getSetting('usenet_ssl') == 'true',
            'username': ADDON.getSetting('usenet_username') or '',
            'password': ADDON.getSetting('usenet_password') or '',
            'connections': int(ADDON.getSetting('usenet_connections') or '8')
        }
    
    @staticmethod
    def is_configured():
        """Check if any Usenet provider is configured"""
        provider = UsenetProvider.get_primary_provider()
        if provider:
            return bool(provider['server'] and provider['username'])
        return False


def get_download_client():
    """Get configured download client (SABnzbd or NZBGet)"""
    client_type = ADDON.getSetting('nzb_download_client') or 'sabnzbd'
    
    if client_type == 'sabnzbd':
        return SABnzbdClient()
    elif client_type == 'nzbget':
        return NZBGetClient()
    
    return None


def add_nzb(nzb_url_or_content, name='', is_url=True):
    """Add NZB to configured download client"""
    client = get_download_client()
    if not client or not client.is_configured():
        xbmcgui.Dialog().notification(
            'SALTS Usenet',
            'No download client configured',
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )
        return False
    
    try:
        if is_url:
            success = client.add_nzb_url(nzb_url_or_content, name)
        else:
            success = client.add_nzb_file(nzb_url_or_content, name)
        
        if success:
            xbmcgui.Dialog().notification(
                'SALTS Usenet',
                f'Added to {client.__class__.__name__}',
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
            return True
        else:
            xbmcgui.Dialog().notification(
                'SALTS Usenet',
                'Failed to add NZB',
                xbmcgui.NOTIFICATION_ERROR,
                3000
            )
            return False
    except Exception as e:
        log_utils.log_error(f'Add NZB error: {e}')
        xbmcgui.Dialog().notification(
            'SALTS Usenet',
            'Error adding NZB',
            xbmcgui.NOTIFICATION_ERROR,
            3000
        )
        return False
