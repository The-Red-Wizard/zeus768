# -*- coding: utf-8 -*-
"""
Enhanced Cloud Browser for Genesis
Browses debrid cloud storage:
- Downloaded files
- Cached torrents
- Currently downloading
Supports: Real-Debrid, AllDebrid, Premiumize, TorBox
"""
import os
import json
import time
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote_plus

ADDON_ID = 'plugin.video.genesis'
USER_AGENT = 'Genesis Kodi Addon'


def get_addon():
    return xbmcaddon.Addon()


def _format_size(size_bytes):
    """Format bytes to human readable size"""
    if not size_bytes:
        return ''
    try:
        size_bytes = int(size_bytes)
    except:
        return str(size_bytes)
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def _http_get(url, headers=None, timeout=30):
    """HTTP GET helper"""
    hdrs = {'User-Agent': USER_AGENT}
    if headers:
        hdrs.update(headers)
    
    try:
        req = Request(url, headers=hdrs)
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
        except:
            pass
        try:
            return e.code, json.loads(body)
        except:
            return e.code, body
    except Exception as e:
        xbmc.log(f'Cloud HTTP Error: {e}', xbmc.LOGERROR)
        return 0, None


def is_cloud_configured():
    """Check if any debrid cloud service is configured"""
    from resources.lib import debrid
    
    rd = debrid.RealDebrid()
    ad = debrid.AllDebrid()
    pm = debrid.Premiumize()
    tb = debrid.Torbox()
    
    return rd.is_authorized() or ad.is_authorized() or pm.is_authorized() or tb.is_authorized()


def get_available_services():
    """Get list of authorized cloud services"""
    from resources.lib import debrid
    
    services = []
    
    rd = debrid.RealDebrid()
    if rd.is_authorized():
        services.append({
            'name': 'Real-Debrid',
            'code': 'rd',
            'icon': 'debrid_cloud.png'
        })
    
    ad = debrid.AllDebrid()
    if ad.is_authorized():
        services.append({
            'name': 'AllDebrid',
            'code': 'ad',
            'icon': 'debrid_cloud.png'
        })
    
    pm = debrid.Premiumize()
    if pm.is_authorized():
        services.append({
            'name': 'Premiumize',
            'code': 'pm',
            'icon': 'debrid_cloud.png'
        })
    
    tb = debrid.Torbox()
    if tb.is_authorized():
        services.append({
            'name': 'TorBox',
            'code': 'tb',
            'icon': 'debrid_cloud.png'
        })
    
    return services


# ══════════════════════════════════════════════════════════════════════════════
# REAL-DEBRID CLOUD
# ══════════════════════════════════════════════════════════════════════════════

def rd_get_cloud_items():
    """Get all Real-Debrid cloud items"""
    from resources.lib import debrid
    rd = debrid.RealDebrid()
    
    if not rd.is_authorized():
        return {'downloaded': [], 'downloading': [], 'cached': []}
    
    items = {
        'downloaded': [],
        'downloading': [],
        'cached': []
    }
    
    # Get torrents
    status, result = _http_get(
        f"{rd.BASE_URL}/torrents",
        headers={'Authorization': f'Bearer {rd.token}'}
    )
    
    if status == 200 and isinstance(result, list):
        for torrent in result:
            t_status = torrent.get('status', '')
            
            item = {
                'id': torrent.get('id', ''),
                'name': torrent.get('filename', ''),
                'size': _format_size(torrent.get('bytes', 0)),
                'progress': torrent.get('progress', 0),
                'status': t_status,
                'added': torrent.get('added', ''),
                'links': torrent.get('links', []),
                'service': 'rd'
            }
            
            if t_status == 'downloaded':
                items['downloaded'].append(item)
            elif t_status in ('downloading', 'queued', 'compressing', 'uploading'):
                items['downloading'].append(item)
            elif t_status == 'magnet_conversion':
                items['downloading'].append(item)
    
    # Get download history (last 50)
    status, history = _http_get(
        f"{rd.BASE_URL}/downloads?limit=50",
        headers={'Authorization': f'Bearer {rd.token}'}
    )
    
    if status == 200 and isinstance(history, list):
        for dl in history:
            items['cached'].append({
                'id': dl.get('id', ''),
                'name': dl.get('filename', ''),
                'size': _format_size(dl.get('filesize', 0)),
                'link': dl.get('download', ''),
                'generated': dl.get('generated', ''),
                'service': 'rd',
                'type': 'download'
            })
    
    return items


def rd_get_torrent_info(torrent_id):
    """Get detailed info for a Real-Debrid torrent"""
    from resources.lib import debrid
    rd = debrid.RealDebrid()
    
    if not rd.is_authorized():
        return None
    
    status, result = _http_get(
        f"{rd.BASE_URL}/torrents/info/{torrent_id}",
        headers={'Authorization': f'Bearer {rd.token}'}
    )
    
    if status == 200 and isinstance(result, dict):
        files = []
        for f in result.get('files', []):
            if f.get('selected', 0) == 1:
                files.append({
                    'id': f.get('id', 0),
                    'name': f.get('path', '').split('/')[-1],
                    'size': _format_size(f.get('bytes', 0)),
                    'path': f.get('path', '')
                })
        
        return {
            'id': result.get('id', ''),
            'name': result.get('filename', ''),
            'status': result.get('status', ''),
            'progress': result.get('progress', 0),
            'links': result.get('links', []),
            'files': files
        }
    
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ALLDEBRID CLOUD
# ══════════════════════════════════════════════════════════════════════════════

def ad_get_cloud_items():
    """Get AllDebrid cloud items"""
    from resources.lib import debrid
    ad = debrid.AllDebrid()
    
    if not ad.is_authorized():
        return {'downloaded': [], 'downloading': [], 'cached': []}
    
    items = {
        'downloaded': [],
        'downloading': [],
        'cached': []
    }
    
    # Get magnets
    status, result = _http_get(
        f"{ad.BASE_URL}/magnet/status?agent=Genesis&apikey={ad.token}"
    )
    
    if status == 200 and isinstance(result, dict) and result.get('status') == 'success':
        magnets = result.get('data', {}).get('magnets', [])
        
        for magnet in magnets:
            m_status = magnet.get('status', '')
            
            item = {
                'id': str(magnet.get('id', '')),
                'name': magnet.get('filename', ''),
                'size': _format_size(magnet.get('size', 0)),
                'status': m_status,
                'progress': magnet.get('downloaded', 0),
                'links': magnet.get('links', []),
                'service': 'ad'
            }
            
            if m_status == 'Ready':
                items['downloaded'].append(item)
            elif m_status in ('Downloading', 'Uploading', 'Processing', 'Queued'):
                items['downloading'].append(item)
    
    return items


# ══════════════════════════════════════════════════════════════════════════════
# PREMIUMIZE CLOUD
# ══════════════════════════════════════════════════════════════════════════════

def pm_get_cloud_items():
    """Get Premiumize cloud items"""
    from resources.lib import debrid
    pm = debrid.Premiumize()
    
    if not pm.is_authorized():
        return {'downloaded': [], 'downloading': [], 'cached': []}
    
    items = {
        'downloaded': [],
        'downloading': [],
        'cached': []
    }
    
    # Get folder contents (root)
    status, result = _http_get(
        f"{pm.BASE_URL}/folder/list",
        headers={'Authorization': f'Bearer {pm.token}'}
    )
    
    if status == 200 and isinstance(result, dict) and result.get('status') == 'success':
        content = result.get('content', [])
        
        for item in content:
            if item.get('type') == 'file':
                items['downloaded'].append({
                    'id': item.get('id', ''),
                    'name': item.get('name', ''),
                    'size': _format_size(item.get('size', 0)),
                    'link': item.get('link', ''),
                    'service': 'pm'
                })
            elif item.get('type') == 'folder':
                items['downloaded'].append({
                    'id': item.get('id', ''),
                    'name': f"[FOLDER] {item.get('name', '')}",
                    'is_folder': True,
                    'service': 'pm'
                })
    
    # Get transfers (downloading)
    status, transfers = _http_get(
        f"{pm.BASE_URL}/transfer/list",
        headers={'Authorization': f'Bearer {pm.token}'}
    )
    
    if status == 200 and isinstance(transfers, dict) and transfers.get('status') == 'success':
        for tr in transfers.get('transfers', []):
            t_status = tr.get('status', '')
            
            if t_status in ('running', 'waiting', 'queued'):
                items['downloading'].append({
                    'id': tr.get('id', ''),
                    'name': tr.get('name', ''),
                    'progress': int(tr.get('progress', 0) * 100),
                    'status': t_status,
                    'service': 'pm'
                })
            elif t_status == 'finished':
                items['cached'].append({
                    'id': tr.get('id', ''),
                    'name': tr.get('name', ''),
                    'service': 'pm'
                })
    
    return items


def pm_get_folder_contents(folder_id):
    """Get contents of a Premiumize folder"""
    from resources.lib import debrid
    pm = debrid.Premiumize()
    
    if not pm.is_authorized():
        return []
    
    url = f"{pm.BASE_URL}/folder/list"
    if folder_id:
        url += f"?id={folder_id}"
    
    status, result = _http_get(url, headers={'Authorization': f'Bearer {pm.token}'})
    
    items = []
    if status == 200 and isinstance(result, dict) and result.get('status') == 'success':
        for item in result.get('content', []):
            items.append({
                'id': item.get('id', ''),
                'name': item.get('name', ''),
                'size': _format_size(item.get('size', 0)) if item.get('type') == 'file' else '',
                'link': item.get('link', ''),
                'is_folder': item.get('type') == 'folder',
                'service': 'pm'
            })
    
    return items


# ══════════════════════════════════════════════════════════════════════════════
# TORBOX CLOUD
# ══════════════════════════════════════════════════════════════════════════════

def tb_get_cloud_items():
    """Get TorBox cloud items"""
    from resources.lib import debrid
    tb = debrid.Torbox()
    
    if not tb.is_authorized():
        return {'downloaded': [], 'downloading': [], 'cached': []}
    
    items = {
        'downloaded': [],
        'downloading': [],
        'cached': []
    }
    
    # Get torrents
    status, result = _http_get(
        f"{tb.BASE_URL}/torrents/mylist",
        headers={'Authorization': f'Bearer {tb.token}'}
    )
    
    if status == 200 and isinstance(result, dict) and result.get('success'):
        torrents = result.get('data', [])
        if isinstance(torrents, dict):
            torrents = [torrents]
        
        for torrent in torrents:
            t_status = torrent.get('download_state', '')
            
            item = {
                'id': str(torrent.get('id', '')),
                'name': torrent.get('name', ''),
                'size': _format_size(torrent.get('size', 0)),
                'progress': int(torrent.get('progress', 0) * 100),
                'status': t_status,
                'files': torrent.get('files', []),
                'service': 'tb'
            }
            
            if t_status in ('completed', 'cached', 'uploading', 'seeding'):
                items['downloaded'].append(item)
            elif t_status in ('downloading', 'queued', 'stalled', 'paused'):
                items['downloading'].append(item)
    
    return items


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED CLOUD INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def get_all_cloud_items(service_code=None):
    """Get cloud items from all or specific service"""
    all_items = {
        'downloaded': [],
        'downloading': [],
        'cached': []
    }
    
    if service_code is None or service_code == 'rd':
        rd_items = rd_get_cloud_items()
        all_items['downloaded'].extend(rd_items['downloaded'])
        all_items['downloading'].extend(rd_items['downloading'])
        all_items['cached'].extend(rd_items['cached'])
    
    if service_code is None or service_code == 'ad':
        ad_items = ad_get_cloud_items()
        all_items['downloaded'].extend(ad_items['downloaded'])
        all_items['downloading'].extend(ad_items['downloading'])
        all_items['cached'].extend(ad_items['cached'])
    
    if service_code is None or service_code == 'pm':
        pm_items = pm_get_cloud_items()
        all_items['downloaded'].extend(pm_items['downloaded'])
        all_items['downloading'].extend(pm_items['downloading'])
        all_items['cached'].extend(pm_items['cached'])
    
    if service_code is None or service_code == 'tb':
        tb_items = tb_get_cloud_items()
        all_items['downloaded'].extend(tb_items['downloaded'])
        all_items['downloading'].extend(tb_items['downloading'])
        all_items['cached'].extend(tb_items['cached'])
    
    return all_items


def delete_cloud_item(service, item_id):
    """Delete an item from cloud storage"""
    from resources.lib import debrid
    
    try:
        if service == 'rd':
            rd = debrid.RealDebrid()
            if rd.is_authorized():
                from urllib.request import Request, urlopen
                req = Request(
                    f"{rd.BASE_URL}/torrents/delete/{item_id}",
                    method='DELETE',
                    headers={'Authorization': f'Bearer {rd.token}', 'User-Agent': USER_AGENT}
                )
                urlopen(req, timeout=15)
                return True
        
        elif service == 'ad':
            ad = debrid.AllDebrid()
            if ad.is_authorized():
                status, _ = _http_get(
                    f"{ad.BASE_URL}/magnet/delete?agent=Genesis&apikey={ad.token}&id={item_id}"
                )
                return status == 200
        
        elif service == 'pm':
            pm = debrid.Premiumize()
            if pm.is_authorized():
                from urllib.request import Request, urlopen
                from urllib.parse import urlencode
                data = urlencode({'id': item_id}).encode()
                req = Request(
                    f"{pm.BASE_URL}/item/delete",
                    data=data,
                    headers={'Authorization': f'Bearer {pm.token}', 'User-Agent': USER_AGENT}
                )
                urlopen(req, timeout=15)
                return True
        
        elif service == 'tb':
            tb = debrid.Torbox()
            if tb.is_authorized():
                from urllib.request import Request, urlopen
                req = Request(
                    f"{tb.BASE_URL}/torrents/controltorrent?torrent_id={item_id}&operation=delete",
                    method='POST',
                    headers={'Authorization': f'Bearer {tb.token}', 'User-Agent': USER_AGENT}
                )
                urlopen(req, timeout=15)
                return True
                
    except Exception as e:
        xbmc.log(f'Cloud delete error: {e}', xbmc.LOGERROR)
    
    return False


def resolve_cloud_link(service, link_or_id, item_type='link'):
    """Resolve a cloud link to playable URL"""
    from resources.lib import debrid
    
    try:
        if service == 'rd':
            rd = debrid.RealDebrid()
            if rd.is_authorized():
                return rd.unrestrict_link(link_or_id)
        
        elif service == 'ad':
            ad = debrid.AllDebrid()
            if ad.is_authorized():
                return ad.unrestrict_link(link_or_id)
        
        elif service == 'pm':
            # Premiumize links are usually direct
            return link_or_id
        
        elif service == 'tb':
            tb = debrid.Torbox()
            if tb.is_authorized():
                # For TorBox, we need to request download link
                status, result = _http_get(
                    f"{tb.BASE_URL}/torrents/requestdl?torrent_id={link_or_id}&file_id=0",
                    headers={'Authorization': f'Bearer {tb.token}'}
                )
                if status == 200 and isinstance(result, dict) and result.get('success'):
                    return result.get('data')
                    
    except Exception as e:
        xbmc.log(f'Cloud resolve error: {e}', xbmc.LOGERROR)
    
    return None
