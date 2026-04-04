# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    TorBox resolver with PIN-based authentication
'''

import urllib
import json
import time

from resources.lib.libraries import cache
from resources.lib.libraries import control
from resources.lib.libraries import client


def tbAuthorize():
    '''Device code flow for TorBox API authorization'''
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

        # TorBox uses direct API key input via PIN
        progressDialog = control.progressDialog
        progressDialog.create('TorBox Authorization', '')
        
        verification_url = control.lang(30416).encode('utf-8') + '[COLOR skyblue]https://torbox.app/settings[/COLOR]'
        instructions = 'Get your API key from TorBox settings and enter it below'
        
        progressDialog.update(0, verification_url, instructions)

        # Close progress and ask for API key
        time.sleep(2)
        progressDialog.close()
        
        # Show keyboard for API key input
        keyboard = control.keyboard
        k = keyboard('', 'Enter TorBox API Key')
        k.doModal()
        
        if not k.isConfirmed():
            raise Exception()
        
        api_key = k.getText()
        if not api_key:
            raise Exception()

        # Validate the API key
        headers = {'Authorization': 'Bearer %s' % api_key}
        url = 'https://api.torbox.app/v1/api/user/me'
        result = client.request(url, headers=headers, timeout=15)
        
        if result is None:
            control.infoDialog('Invalid API Key', heading='TorBox')
            raise Exception()
        
        result = json.loads(result)
        if not result.get('success', False):
            control.infoDialog('Invalid API Key', heading='TorBox')
            raise Exception()

        # Save the API key
        control.set_setting('torbox_api_key', api_key)
        control.infoDialog('Authorization Successful', heading='TorBox')
        
    except:
        control.openSettings('3.16')


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
