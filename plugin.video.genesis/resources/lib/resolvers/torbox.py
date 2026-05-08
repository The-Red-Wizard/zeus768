# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    TorBox resolver with PIN-based authentication
'''

import json
import time
try:
    import urllib
except ImportError:
    import urllib.parse as urllib

from resources.lib.libraries import cache
from resources.lib.libraries import control
from resources.lib.libraries import client


def tbAuthorize():
    '''Device code flow for TorBox API authorization (JSON POST required)'''
    try:
        if not '' in credentials().values():
            if control.yesnoDialog(
                'TorBox is already authorized.',
                'Do you want to reset authorization?', '',
                'TorBox',
                'No', 'Yes'
            ):
                control.set_setting('torbox_api_key', '')
            raise Exception()

        import xbmcgui
        from urllib.request import urlopen, Request

        # Step 1: Get device code via GET
        start_url = 'https://api.torbox.app/v1/api/user/auth/device/start'
        req = Request(start_url, headers={'User-Agent': 'Genesis Kodi Addon'})
        resp = urlopen(req, timeout=15)
        result = json.loads(resp.read().decode('utf-8'))

        if not result.get('success', False):
            control.infoDialog('Failed to get device code', heading='TorBox')
            raise Exception()

        data = result.get('data', {})
        device_code = data.get('device_code', '')
        user_code = data.get('code') or data.get('user_code') or ''
        verify_url = data.get('friendly_verification_url') or data.get('verification_url') or 'https://torbox.app/devices'
        interval = data.get('interval', 5)

        # Calculate expires_in from expires_at
        expires_in = 600
        exp_at = data.get('expires_at')
        if exp_at:
            try:
                from datetime import datetime, timezone
                ts = exp_at.replace('Z', '+00:00')
                exp_dt = datetime.fromisoformat(ts)
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                expires_in = max(60, int(exp_dt.timestamp() - time.time()))
            except Exception:
                pass

        if not device_code or not user_code:
            control.infoDialog('No device code received', heading='TorBox')
            raise Exception()

        # Step 2: Show code and poll
        progressDialog = control.progressDialog
        progressDialog.create(
            'TorBox Authorization',
            'Go to: [COLOR skyblue]%s[/COLOR]\n\nEnter Code: [COLOR yellow]%s[/COLOR]\n\nWaiting for authorization...' % (verify_url, user_code)
        )

        start_time = time.time()
        while time.time() - start_time < expires_in:
            if progressDialog.iscanceled():
                progressDialog.close()
                raise Exception()

            time.sleep(interval)
            elapsed = time.time() - start_time
            remaining = max(0, expires_in - elapsed)
            pct = int((elapsed / expires_in) * 100)
            progressDialog.update(
                pct,
                'Go to: [COLOR skyblue]%s[/COLOR]\n\nEnter Code: [COLOR yellow]%s[/COLOR]\n\nTime remaining: %d seconds' % (verify_url, user_code, int(remaining))
            )

            try:
                # TorBox requires JSON POST for token endpoint
                token_url = 'https://api.torbox.app/v1/api/user/auth/device/token'
                post_data = json.dumps({"device_code": device_code}).encode('utf-8')
                poll_req = Request(
                    token_url,
                    data=post_data,
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'Genesis Kodi Addon'
                    },
                    method='POST'
                )
                poll_resp = urlopen(poll_req, timeout=15)
                poll_result = json.loads(poll_resp.read().decode('utf-8'))

                if poll_result.get('success', False):
                    token_data = poll_result.get('data', {})
                    api_key = token_data.get('access_token') or token_data.get('api_key') or token_data.get('token') or ''
                    if api_key:
                        control.set_setting('torbox_api_key', api_key)
                        progressDialog.close()
                        control.infoDialog('Authorization Successful', heading='TorBox')
                        return
            except Exception:
                # authorization_pending or transient error - keep polling
                pass

        progressDialog.close()
        control.infoDialog('Authorization timed out', heading='TorBox')

    except:
        control.openSettings('4.9')


def credentials():
    return {
        'api_key': control.setting('torbox_api_key')
    }


def getHosts():
    '''Get supported hosts from TorBox'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return []
        
        # TorBox supports magnet links and various hosters
        return ['torbox', 'magnet', 'torrent']
    except:
        return []


def checkCache(magnets):
    '''Check if torrents are cached on TorBox'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return {}

        headers = {'Authorization': 'Bearer %s' % api_key}
        
        # Extract hashes from magnets
        hashes = []
        for magnet in magnets:
            import re
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
            if hash_match:
                hashes.append(hash_match.group(1).lower())
        
        if not hashes:
            return {}

        # Check cache
        url = 'https://api.torbox.app/v1/api/torrents/checkcached?hash=%s' % ','.join(hashes)
        result = client.request(url, headers=headers, timeout=15)
        
        if result is None:
            return {}
        
        data = json.loads(result)
        if not data.get('success', False):
            return {}
        
        cached = {}
        cache_data = data.get('data', {})
        for h in hashes:
            if h in cache_data and cache_data[h]:
                cached[h] = True
        
        return cached
    except:
        return {}


def addTorrent(magnet):
    '''Add torrent to TorBox for downloading'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return None

        headers = {
            'Authorization': 'Bearer %s' % api_key,
            'Content-Type': 'application/json'
        }
        
        url = 'https://api.torbox.app/v1/api/torrents/createtorrent'
        post_data = json.dumps({'magnet': magnet})
        
        result = client.request(url, post=post_data, headers=headers, timeout=30)
        
        if result is None:
            return None
        
        data = json.loads(result)
        if not data.get('success', False):
            return None
        
        return data.get('data', {}).get('torrent_id')
    except:
        return None


def getTorrentInfo(torrent_id):
    '''Get torrent info from TorBox'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return None

        headers = {'Authorization': 'Bearer %s' % api_key}
        url = 'https://api.torbox.app/v1/api/torrents/mylist?id=%s' % torrent_id
        
        result = client.request(url, headers=headers, timeout=15)
        
        if result is None:
            return None
        
        data = json.loads(result)
        if not data.get('success', False):
            return None
        
        return data.get('data')
    except:
        return None


def getDownloadLink(torrent_id, file_id=None):
    '''Get download link from TorBox'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return None

        headers = {'Authorization': 'Bearer %s' % api_key}
        
        url = 'https://api.torbox.app/v1/api/torrents/requestdl?torrent_id=%s&token=%s' % (torrent_id, api_key)
        if file_id:
            url += '&file_id=%s' % file_id
        
        result = client.request(url, headers=headers, timeout=15)
        
        if result is None:
            return None
        
        data = json.loads(result)
        if not data.get('success', False):
            return None
        
        return data.get('data')
    except:
        return None


def resolve(url):
    '''Resolve magnet link through TorBox'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return None

        # Add torrent
        torrent_id = addTorrent(url)
        if not torrent_id:
            return None

        # Wait for torrent to be ready (max 60 seconds)
        for i in range(60):
            time.sleep(1)
            info = getTorrentInfo(torrent_id)
            if info and info.get('download_finished', False):
                break

        # Get download link
        download_url = getDownloadLink(torrent_id)
        return download_url
    except:
        return None
