"""
SALTS - Unified Debrid Cloud Manager

Comprehensive cloud/download manager for all supported debrid services:
- Real-Debrid (torrents)
- Premiumize (transfers)
- AllDebrid (magnets)
- TorBox (torrents)
- Put.io (transfers)
- EasyNews (Usenet)
- SABnzbd/NZBGet (NZB downloads)

Author: zeus768
"""

import json
import time
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import threading
from urllib.parse import urlencode
from . import log_utils
from .debrid import (RealDebrid, Premiumize, AllDebrid, TorBox, PutIO, 
                     EasyNews, _get, _post, _http)
from .usenet_nzb import SABnzbdClient, NZBGetClient, get_download_client

ADDON = xbmcaddon.Addon()


class UnifiedDebridCloudManager:
    """Unified cloud manager for all debrid services and download clients"""
    
    def __init__(self):
        self.rd = RealDebrid()
        self.pm = Premiumize()
        self.ad = AllDebrid()
        self.tb = TorBox()
        self.putio = PutIO()
        self.easynews = EasyNews()
        self._monitor_thread = None
        self._stop_monitoring = False
    
    def get_enabled_services(self):
        """Get list of enabled debrid services"""
        services = []
        
        if self.rd.is_authorized():
            services.append(('realdebrid', 'Real-Debrid', self.rd))
        if self.pm.is_authorized():
            services.append(('premiumize', 'Premiumize', self.pm))
        if self.ad.is_authorized():
            services.append(('alldebrid', 'AllDebrid', self.ad))
        if self.tb.is_authorized():
            services.append(('torbox', 'TorBox', self.tb))
        if self.putio.is_authorized():
            services.append(('putio', 'Put.io', self.putio))
        if self.easynews.is_authorized():
            services.append(('easynews', 'EasyNews', self.easynews))
        
        return services
    
    # ==================== Real-Debrid ====================
    
    def rd_get_torrents(self):
        """Get Real-Debrid torrents"""
        if not self.rd.is_authorized():
            return []
        
        try:
            code, result = _get(
                f'{self.rd.BASE_URL}/torrents',
                headers=self.rd._auth_headers()
            )
            
            if code == 200 and isinstance(result, list):
                return result
        except Exception as e:
            log_utils.log_error(f'RD get torrents error: {e}')
        
        return []
    
    def rd_get_downloading(self):
        """Get downloading torrents"""
        torrents = self.rd_get_torrents()
        return [t for t in torrents if t.get('status') in ['downloading', 'queued', 'magnet_conversion']]
    
    def rd_get_completed(self):
        """Get completed torrents"""
        torrents = self.rd_get_torrents()
        return [t for t in torrents if t.get('status') == 'downloaded']
    
    def rd_delete_torrent(self, torrent_id):
        """Delete Real-Debrid torrent"""
        if not self.rd.is_authorized():
            return False
        
        try:
            code, _ = _http(
                f'{self.rd.BASE_URL}/torrents/delete/{torrent_id}',
                method='DELETE',
                headers=self.rd._auth_headers()
            )
            
            if code == 204:
                xbmcgui.Dialog().notification(
                    'Real-Debrid',
                    'Torrent deleted',
                    xbmcgui.NOTIFICATION_INFO,
                    3000
                )
                return True
        except Exception as e:
            log_utils.log_error(f'RD delete error: {e}')
        
        return False
    
    def rd_add_magnet(self, magnet):
        """Add magnet to Real-Debrid"""
        if not self.rd.is_authorized():
            return False
        
        try:
            code, result = _post(
                f'{self.rd.BASE_URL}/torrents/addMagnet',
                data={'magnet': magnet},
                headers=self.rd._auth_headers()
            )
            
            if code in (200, 201) and isinstance(result, dict):
                xbmcgui.Dialog().notification(
                    'Real-Debrid',
                    'Magnet added to cloud',
                    xbmcgui.NOTIFICATION_INFO,
                    3000
                )
                return True
        except Exception as e:
            log_utils.log_error(f'RD add magnet error: {e}')
        
        return False
    
    # ==================== Premiumize ====================
    
    def pm_get_transfers(self):
        """Get Premiumize transfers"""
        if not self.pm.is_authorized():
            return []
        
        try:
            code, result = _get(
                f'{self.pm.BASE_URL}/transfer/list',
                params={'apikey': self.pm.token}
            )
            
            if code == 200 and isinstance(result, dict):
                if result.get('status') == 'success':
                    return result.get('transfers', [])
        except Exception as e:
            log_utils.log_error(f'PM get transfers error: {e}')
        
        return []
    
    def pm_get_downloading(self):
        """Get downloading transfers"""
        transfers = self.pm_get_transfers()
        return [t for t in transfers if t.get('status') in ['running', 'waiting', 'queued']]
    
    def pm_get_completed(self):
        """Get completed transfers"""
        transfers = self.pm_get_transfers()
        return [t for t in transfers if t.get('status') == 'finished']
    
    def pm_delete_transfer(self, transfer_id):
        """Delete Premiumize transfer"""
        if not self.pm.is_authorized():
            return False
        
        try:
            code, _ = _post(
                f'{self.pm.BASE_URL}/transfer/delete',
                params={'apikey': self.pm.token},
                data={'id': transfer_id}
            )
            
            if code == 200:
                xbmcgui.Dialog().notification(
                    'Premiumize',
                    'Transfer deleted',
                    xbmcgui.NOTIFICATION_INFO,
                    3000
                )
                return True
        except Exception as e:
            log_utils.log_error(f'PM delete error: {e}')
        
        return False
    
    def pm_add_magnet(self, magnet):
        """Add magnet to Premiumize"""
        if not self.pm.is_authorized():
            return False
        
        try:
            code, result = _post(
                f'{self.pm.BASE_URL}/transfer/create',
                params={'apikey': self.pm.token},
                data={'src': magnet}
            )
            
            if code == 200 and isinstance(result, dict):
                if result.get('status') == 'success':
                    xbmcgui.Dialog().notification(
                        'Premiumize',
                        'Magnet added to cloud',
                        xbmcgui.NOTIFICATION_INFO,
                        3000
                    )
                    return True
        except Exception as e:
            log_utils.log_error(f'PM add magnet error: {e}')
        
        return False
    
    # ==================== AllDebrid ====================
    
    def ad_get_magnets(self):
        """Get AllDebrid magnets"""
        if not self.ad.is_authorized():
            return []
        
        try:
            code, result = _get(
                f'{self.ad.BASE_URL}/magnet/status',
                params={'agent': self.ad.AGENT, 'apikey': self.ad.token}
            )
            
            if code == 200 and isinstance(result, dict):
                if result.get('status') == 'success':
                    return result.get('data', {}).get('magnets', [])
        except Exception as e:
            log_utils.log_error(f'AD get magnets error: {e}')
        
        return []
    
    def ad_get_downloading(self):
        """Get downloading magnets"""
        magnets = self.ad_get_magnets()
        return [m for m in magnets if m.get('status') in ['Downloading', 'Processing', 'Uploading']]
    
    def ad_get_completed(self):
        """Get completed magnets"""
        magnets = self.ad_get_magnets()
        return [m for m in magnets if m.get('status') == 'Ready']
    
    def ad_delete_magnet(self, magnet_id):
        """Delete AllDebrid magnet"""
        if not self.ad.is_authorized():
            return False
        
        try:
            code, _ = _get(
                f'{self.ad.BASE_URL}/magnet/delete',
                params={
                    'agent': self.ad.AGENT,
                    'apikey': self.ad.token,
                    'id': magnet_id
                }
            )
            
            if code == 200:
                xbmcgui.Dialog().notification(
                    'AllDebrid',
                    'Magnet deleted',
                    xbmcgui.NOTIFICATION_INFO,
                    3000
                )
                return True
        except Exception as e:
            log_utils.log_error(f'AD delete error: {e}')
        
        return False
    
    def ad_add_magnet(self, magnet):
        """Add magnet to AllDebrid"""
        if not self.ad.is_authorized():
            return False
        
        try:
            code, result = _get(
                f'{self.ad.BASE_URL}/magnet/upload',
                params={
                    'agent': self.ad.AGENT,
                    'apikey': self.ad.token,
                    'magnets[]': magnet
                }
            )
            
            if code == 200 and isinstance(result, dict):
                if result.get('status') == 'success':
                    xbmcgui.Dialog().notification(
                        'AllDebrid',
                        'Magnet added to cloud',
                        xbmcgui.NOTIFICATION_INFO,
                        3000
                    )
                    return True
        except Exception as e:
            log_utils.log_error(f'AD add magnet error: {e}')
        
        return False
    
    # ==================== TorBox ====================
    
    def tb_get_torrents(self):
        """Get TorBox torrents (using existing torbox_cloud functionality)"""
        try:
            code, result = _get(
                f'{self.tb.BASE_URL}/torrents/mylist',
                params={'bypass_cache': 'true'},
                headers=self.tb._auth_headers()
            )
            
            if code == 200 and isinstance(result, dict) and result.get('success'):
                return result.get('data', [])
        except Exception as e:
            log_utils.log_error(f'TB get torrents error: {e}')
        
        return []
    
    def tb_get_downloading(self):
        """Get downloading torrents"""
        torrents = self.tb_get_torrents()
        downloading_states = ['downloading', 'queued', 'checking', 'magnet_conversion']
        return [t for t in torrents if any(s in str(t.get('download_state', '')).lower() for s in downloading_states)]
    
    def tb_get_completed(self):
        """Get completed torrents"""
        torrents = self.tb_get_torrents()
        completed_states = ['completed', 'cached', 'uploading', 'seeding']
        return [t for t in torrents if t.get('download_finished') or any(s in str(t.get('download_state', '')).lower() for s in completed_states)]
    
    def tb_delete_torrent(self, torrent_id):
        """Delete TorBox torrent"""
        if not self.tb.is_authorized():
            return False
        
        try:
            code, _ = _post(
                f'{self.tb.BASE_URL}/torrents/controltorrent',
                data=json.dumps({
                    'torrent_id': int(torrent_id),
                    'operation': 'delete'
                }),
                headers={
                    **self.tb._auth_headers(),
                    'Content-Type': 'application/json'
                }
            )
            
            if code == 200:
                xbmcgui.Dialog().notification(
                    'TorBox',
                    'Torrent deleted',
                    xbmcgui.NOTIFICATION_INFO,
                    3000
                )
                return True
        except Exception as e:
            log_utils.log_error(f'TB delete error: {e}')
        
        return False
    
    def tb_add_magnet(self, magnet):
        """Add magnet to TorBox"""
        if not self.tb.is_authorized():
            return False
        
        try:
            code, result = _post(
                f'{self.tb.BASE_URL}/torrents/createtorrent',
                data=json.dumps({
                    'magnet': magnet,
                    'seed': 1
                }),
                headers={
                    **self.tb._auth_headers(),
                    'Content-Type': 'application/json'
                }
            )
            
            if code == 200 and isinstance(result, dict) and result.get('success'):
                xbmcgui.Dialog().notification(
                    'TorBox',
                    'Magnet added to cloud',
                    xbmcgui.NOTIFICATION_INFO,
                    3000
                )
                return True
        except Exception as e:
            log_utils.log_error(f'TB add magnet error: {e}')
        
        return False
    
    # ==================== Put.io ====================
    
    def putio_get_transfers(self):
        """Get Put.io transfers"""
        if not self.putio.is_authorized():
            return []
        
        try:
            code, result = _get(
                f'{self.putio.BASE_URL}/transfers/list',
                headers=self.putio._auth_headers()
            )
            
            if code == 200 and isinstance(result, dict):
                return result.get('transfers', [])
        except Exception as e:
            log_utils.log_error(f'Put.io get transfers error: {e}')
        
        return []
    
    def putio_get_downloading(self):
        """Get downloading transfers"""
        transfers = self.putio_get_transfers()
        return [t for t in transfers if t.get('status') in ['DOWNLOADING', 'IN_QUEUE', 'WAITING']]
    
    def putio_get_completed(self):
        """Get completed transfers"""
        transfers = self.putio_get_transfers()
        return [t for t in transfers if t.get('status') == 'COMPLETED']
    
    def putio_delete_transfer(self, transfer_id):
        """Delete Put.io transfer"""
        if not self.putio.is_authorized():
            return False
        
        try:
            code, _ = _post(
                f'{self.putio.BASE_URL}/transfers/cancel',
                data=json.dumps({'transfer_ids': [transfer_id]}),
                headers={
                    **self.putio._auth_headers(),
                    'Content-Type': 'application/json'
                }
            )
            
            if code == 200:
                xbmcgui.Dialog().notification(
                    'Put.io',
                    'Transfer deleted',
                    xbmcgui.NOTIFICATION_INFO,
                    3000
                )
                return True
        except Exception as e:
            log_utils.log_error(f'Put.io delete error: {e}')
        
        return False
    
    def putio_add_magnet(self, magnet):
        """Add magnet to Put.io"""
        if not self.putio.is_authorized():
            return False
        
        try:
            code, result = _post(
                f'{self.putio.BASE_URL}/transfers/add',
                data={'url': magnet},
                headers=self.putio._auth_headers()
            )
            
            if code == 200 and isinstance(result, dict):
                xbmcgui.Dialog().notification(
                    'Put.io',
                    'Magnet added to cloud',
                    xbmcgui.NOTIFICATION_INFO,
                    3000
                )
                return True
        except Exception as e:
            log_utils.log_error(f'Put.io add magnet error: {e}')
        
        return False
    
    # ==================== NZB Download Clients ====================
    
    def nzb_get_queue(self):
        """Get NZB download queue (SABnzbd or NZBGet)"""
        client = get_download_client()
        if client and client.is_configured():
            return client.get_queue()
        return None
    
    def nzb_get_history(self):
        """Get NZB download history"""
        client = get_download_client()
        if client and client.is_configured():
            return client.get_history()
        return None
    
    def nzb_get_status(self):
        """Get NZB client status"""
        client = get_download_client()
        if client and client.is_configured():
            return client.get_status()
        return None
    
    def nzb_delete_download(self, nzb_id):
        """Delete NZB download"""
        client = get_download_client()
        if client and client.is_configured():
            return client.delete_download(nzb_id)
        return False
    
    # ==================== Unified Operations ====================
    
    def get_all_downloads(self):
        """Get all downloads from all services"""
        all_downloads = []
        
        # Real-Debrid
        for t in self.rd_get_downloading():
            all_downloads.append({
                'service': 'Real-Debrid',
                'id': t.get('id'),
                'name': t.get('filename', 'Unknown'),
                'status': t.get('status', 'Unknown'),
                'progress': t.get('progress', 0),
                'size': t.get('bytes', 0),
                'seeds': t.get('seeders', 0)
            })
        
        # Premiumize
        for t in self.pm_get_downloading():
            all_downloads.append({
                'service': 'Premiumize',
                'id': t.get('id'),
                'name': t.get('name', 'Unknown'),
                'status': t.get('status', 'Unknown'),
                'progress': t.get('progress', 0),
                'size': t.get('size', 0),
                'seeds': 0
            })
        
        # AllDebrid
        for m in self.ad_get_downloading():
            all_downloads.append({
                'service': 'AllDebrid',
                'id': m.get('id'),
                'name': m.get('filename', 'Unknown'),
                'status': m.get('status', 'Unknown'),
                'progress': m.get('downloaded', 0) / max(m.get('size', 1), 1) * 100,
                'size': m.get('size', 0),
                'seeds': 0
            })
        
        # TorBox
        for t in self.tb_get_downloading():
            all_downloads.append({
                'service': 'TorBox',
                'id': t.get('id'),
                'name': t.get('name', 'Unknown'),
                'status': t.get('download_state', 'Unknown'),
                'progress': t.get('progress', 0),
                'size': t.get('size', 0),
                'seeds': t.get('seeds', 0)
            })
        
        # Put.io
        for t in self.putio_get_downloading():
            all_downloads.append({
                'service': 'Put.io',
                'id': t.get('id'),
                'name': t.get('name', 'Unknown'),
                'status': t.get('status', 'Unknown'),
                'progress': t.get('percent_done', 0),
                'size': t.get('size', 0),
                'seeds': 0
            })
        
        return all_downloads
    
    def add_magnet_to_all(self, magnet):
        """Add magnet to all enabled services"""
        success_count = 0
        
        if self.rd.is_authorized():
            if self.rd_add_magnet(magnet):
                success_count += 1
        
        if self.pm.is_authorized():
            if self.pm_add_magnet(magnet):
                success_count += 1
        
        if self.ad.is_authorized():
            if self.ad_add_magnet(magnet):
                success_count += 1
        
        if self.tb.is_authorized():
            if self.tb_add_magnet(magnet):
                success_count += 1
        
        if self.putio.is_authorized():
            if self.putio_add_magnet(magnet):
                success_count += 1
        
        return success_count > 0
