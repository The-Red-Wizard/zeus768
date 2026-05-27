"""
SALTS - Torbox Cloud/Download Manager

Provides a comprehensive interface for managing Torbox cloud downloads:
- View currently downloading torrents with progress
- View completed torrents
- Notifications when downloads complete
- Delete torrents
- Add torrents to cloud

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
from .debrid import TorBox, _get, _post

ADDON = xbmcaddon.Addon()


class TorBoxCloudManager:
    """Manages Torbox cloud downloads and torrents"""
    
    def __init__(self):
        self.torbox = TorBox()
        self._monitor_thread = None
        self._stop_monitoring = False
        self._completed_cache = set()
    
    def get_all_torrents(self):
        """Get all torrents from Torbox (downloading + completed)"""
        if not self.torbox.is_authorized():
            return []
        
        try:
            code, result = _get(
                f'{self.torbox.BASE_URL}/torrents/mylist',
                params={'bypass_cache': 'true'},
                headers=self.torbox._auth_headers()
            )
            
            if code == 200 and isinstance(result, dict) and result.get('success'):
                data = result.get('data') or []
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            log_utils.log_error(f'TorBox get torrents error: {e}')
            return []
    
    def get_downloading_torrents(self):
        """Get currently downloading/active torrents"""
        all_torrents = self.get_all_torrents()
        
        downloading_states = [
            'downloading', 'queued', 'checking', 'magnet_conversion',
            'magnet_upload', 'waiting_files_select'
        ]
        
        downloading = []
        for t in all_torrents:
            state = (t.get('download_state') or t.get('state') or '').lower()
            if any(s in state for s in downloading_states):
                downloading.append(t)
        
        return downloading
    
    def get_completed_torrents(self):
        """Get completed torrents"""
        all_torrents = self.get_all_torrents()
        
        completed_states = ['completed', 'cached', 'uploading', 'seeding']
        
        completed = []
        for t in all_torrents:
            state = (t.get('download_state') or t.get('state') or '').lower()
            download_finished = t.get('download_finished', False)
            download_present = t.get('download_present', False)
            
            if download_finished or download_present or any(s in state for s in completed_states):
                completed.append(t)
        
        return completed
    
    def delete_torrent(self, torrent_id):
        """Delete a torrent from Torbox"""
        if not self.torbox.is_authorized():
            return False
        
        try:
            code, result = _post(
                f'{self.torbox.BASE_URL}/torrents/controltorrent',
                data=json.dumps({
                    'torrent_id': int(torrent_id),
                    'operation': 'delete'
                }),
                headers={
                    **self.torbox._auth_headers(),
                    'Content-Type': 'application/json'
                }
            )
            
            if code == 200:
                xbmcgui.Dialog().notification(
                    'Torbox Cloud',
                    'Torrent deleted successfully',
                    xbmcgui.NOTIFICATION_INFO,
                    3000
                )
                return True
            else:
                xbmcgui.Dialog().notification(
                    'Torbox Cloud',
                    'Failed to delete torrent',
                    xbmcgui.NOTIFICATION_ERROR,
                    3000
                )
                return False
        except Exception as e:
            log_utils.log_error(f'TorBox delete error: {e}')
            xbmcgui.Dialog().notification(
                'Torbox Cloud',
                'Error deleting torrent',
                xbmcgui.NOTIFICATION_ERROR,
                3000
            )
            return False
    
    def add_magnet_to_cloud(self, magnet_link):
        """Add a magnet link to Torbox cloud"""
        if not self.torbox.is_authorized():
            xbmcgui.Dialog().notification(
                'Torbox Cloud',
                'Please authorize Torbox first',
                xbmcgui.NOTIFICATION_WARNING,
                3000
            )
            return False
        
        try:
            # Show progress
            progress = xbmcgui.DialogProgress()
            progress.create('Torbox Cloud', 'Adding torrent to cloud...')
            
            code, result = _post(
                f'{self.torbox.BASE_URL}/torrents/createtorrent',
                data={
                    'magnet': magnet_link,
                    'seed': 3,
                    'allow_zip': 'false'
                },
                headers=self.torbox._auth_headers()
            )
            
            progress.close()
            
            if code == 200 and isinstance(result, dict) and result.get('success'):
                torrent_name = (result.get('data') or {}).get('name', 'Unknown')
                xbmcgui.Dialog().notification(
                    'Torbox Cloud',
                    f'Added: {torrent_name[:40]}...',
                    xbmcgui.NOTIFICATION_INFO,
                    4000
                )
                return True
            else:
                error_msg = (result.get('detail') if isinstance(result, dict) else 'Unknown error')
                xbmcgui.Dialog().notification(
                    'Torbox Cloud',
                    f'Failed: {error_msg}',
                    xbmcgui.NOTIFICATION_ERROR,
                    4000
                )
                return False
        except Exception as e:
            log_utils.log_error(f'TorBox add magnet error: {e}')
            xbmcgui.Dialog().notification(
                'Torbox Cloud',
                'Error adding torrent',
                xbmcgui.NOTIFICATION_ERROR,
                3000
            )
            return False
    
    def start_download_monitor(self):
        """Start background thread to monitor downloads and notify when complete"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return  # Already running
        
        self._stop_monitoring = False
        self._monitor_thread = threading.Thread(target=self._monitor_downloads)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
        log_utils.log('TorBox download monitor started', xbmc.LOGINFO)
    
    def stop_download_monitor(self):
        """Stop the background download monitor"""
        self._stop_monitoring = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        log_utils.log('TorBox download monitor stopped', xbmc.LOGINFO)
    
    def _monitor_downloads(self):
        """Background thread function to monitor downloads
        
        This only monitors for NEW completions to notify the user.
        It does NOT interfere with active playback.
        """
        check_interval = 60  # Check every 60 seconds
        consecutive_errors = 0
        max_errors = 5  # Stop after 5 consecutive errors
        
        while not self._stop_monitoring:
            try:
                if not self.torbox.is_authorized():
                    log_utils.log('TorBox monitor: Not authorized, stopping', xbmc.LOGINFO)
                    break
                
                # Skip monitoring if Kodi is currently playing
                # This prevents API spam during active playback
                if xbmc.Player().isPlaying():
                    log_utils.log('TorBox monitor: Playback active, skipping check', xbmc.LOGDEBUG)
                    time.sleep(check_interval)
                    continue
                
                # Get completed torrents
                completed = self.get_completed_torrents()
                
                # Check for newly completed torrents
                for torrent in completed:
                    torrent_id = torrent.get('id')
                    torrent_name = torrent.get('name', 'Unknown')
                    
                    # If this torrent wasn't in our completed cache, it's new!
                    if torrent_id and torrent_id not in self._completed_cache:
                        self._completed_cache.add(torrent_id)
                        
                        # Notify user
                        xbmcgui.Dialog().notification(
                            'Torbox Cloud',
                            f'Download complete: {torrent_name[:40]}...',
                            xbmcgui.NOTIFICATION_INFO,
                            6000
                        )
                        
                        # Play sound if enabled
                        if ADDON.getSetting('torbox_notify_sound') == 'true':
                            xbmc.playSFX('special://home/sounds/notify.wav')
                
                # Reset error counter on successful check
                consecutive_errors = 0
                
                # Sleep in small chunks so we can stop quickly
                for _ in range(check_interval):
                    if self._stop_monitoring:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                consecutive_errors += 1
                log_utils.log_error(f'TorBox monitor error ({consecutive_errors}/{max_errors}): {e}')
                
                # Stop monitoring after too many errors to prevent spam
                if consecutive_errors >= max_errors:
                    log_utils.log_error('TorBox monitor: Too many errors, stopping')
                    break
                    
                time.sleep(check_interval)
    
    def format_torrent_info(self, torrent):
        """Format torrent info for display"""
        name = torrent.get('name', 'Unknown')
        state = (torrent.get('download_state') or torrent.get('state') or 'unknown').lower()
        
        # Progress
        try:
            progress = float(torrent.get('progress', 0)) * 100.0
        except (TypeError, ValueError):
            progress = 0.0
        
        # Size
        try:
            size_bytes = int(torrent.get('size', 0))
            size_gb = size_bytes / (1024 * 1024 * 1024)
        except (TypeError, ValueError):
            size_gb = 0.0
        
        # Speed
        try:
            speed_bps = float(torrent.get('download_speed', 0))
            speed_mbps = speed_bps / (1024 * 1024)
        except (TypeError, ValueError):
            speed_mbps = 0.0
        
        # Seeds
        try:
            seeds = int(torrent.get('seeds', 0))
        except (TypeError, ValueError):
            seeds = 0
        
        # Build info string
        state_display = state.replace('_', ' ').title()
        
        if progress < 100:
            info = f'{state_display} - {progress:.1f}% | {speed_mbps:.1f} MB/s | {seeds} seeds | {size_gb:.2f} GB'
        else:
            info = f'{state_display} | {size_gb:.2f} GB'
        
        return name, info
    
    def get_torrent_files(self, torrent_id):
        """Get files list for a torrent"""
        if not self.torbox.is_authorized():
            return []
        
        try:
            code, result = _get(
                f'{self.torbox.BASE_URL}/torrents/mylist',
                params={'id': torrent_id, 'bypass_cache': 'true'},
                headers=self.torbox._auth_headers()
            )
            
            if code == 200 and isinstance(result, dict) and result.get('success'):
                data = result.get('data') or {}
                return data.get('files', [])
            return []
        except Exception as e:
            log_utils.log_error(f'TorBox get files error: {e}')
            return []
    
    def get_file_playback_url(self, torrent_id, file_id):
        """Get direct playback URL for a specific file in a torrent
        
        This method retrieves the direct download URL from TorBox for playing
        a file. This is the critical missing piece that was causing 
        "Failed playback" errors when users tried to play cached torrents.
        """
        if not self.torbox.is_authorized():
            log_utils.log_error('TorBox: Not authorized for playback')
            return None
        
        try:
            # Request download URL from TorBox
            code, result = _get(
                f'{self.torbox.BASE_URL}/torrents/requestdl',
                params={
                    'token': self.torbox.token,
                    'torrent_id': torrent_id,
                    'file_id': file_id,
                    'redirect': 'false'
                },
                headers=self.torbox._auth_headers()
            )
            
            if code == 200 and isinstance(result, dict) and result.get('success'):
                playback_url = result.get('data')
                if playback_url and isinstance(playback_url, str):
                    log_utils.log(f'TorBox: Got playback URL for file {file_id}', xbmc.LOGINFO)
                    return playback_url
                else:
                    log_utils.log_error(f'TorBox: requestdl returned no valid URL for file {file_id}')
            else:
                error_detail = result.get('detail') if isinstance(result, dict) else 'Unknown error'
                log_utils.log_error(f'TorBox: requestdl failed with code {code}: {error_detail}')
            
            return None
        except Exception as e:
            log_utils.log_error(f'TorBox get playback URL error: {e}')
            return None


# Singleton instance
_manager = None

def get_torbox_manager():
    """Get the singleton TorBoxCloudManager instance"""
    global _manager
    if _manager is None:
        _manager = TorBoxCloudManager()
    return _manager
