# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    AllDebrid resolver with PIN/Device code authentication
'''

import urllib
import json
import time

from resources.lib.libraries import cache
from resources.lib.libraries import control
from resources.lib.libraries import client


# AllDebrid API
ALLDEBRID_API = 'https://api.alldebrid.com/v4'
AGENT = 'Genesis Kodi Addon'


def adAuthorize():
    '''Device code flow for AllDebrid API authorization'''
    try:
        if not '' in credentials().values():
            if control.yesnoDialog(
                'AllDebrid is already authorized.',
                'Do you want to reset authorization?', '',
                'AllDebrid',
                'No', 'Yes'
            ):
                control.set_setting('alldebrid_api_key', '')
                control.set_setting('alldebrid_username', '')
            raise Exception()

        # Get PIN code
        url = '%s/pin/get?agent=%s' % (ALLDEBRID_API, urllib.quote_plus(AGENT))
        result = client.request(url, timeout=15)
        
        if result is None:
            control.infoDialog('Failed to get PIN', heading='AllDebrid')
            raise Exception()
        
        data = json.loads(result)
        if data.get('status') != 'success':
            control.infoDialog('Failed to get PIN', heading='AllDebrid')
            raise Exception()
        
        pin_data = data.get('data', {})
        pin = pin_data.get('pin', '')
        check_url = pin_data.get('check_url', '')
        user_url = pin_data.get('user_url', '')
        expires_in = pin_data.get('expires_in', 600)

        verification_url = control.lang(30416).encode('utf-8') + '[COLOR skyblue]%s[/COLOR]' % user_url
        user_code = control.lang(30417).encode('utf-8') + '[COLOR skyblue]%s[/COLOR]' % pin

        progressDialog = control.progressDialog
        progressDialog.create('AllDebrid', verification_url, user_code)

        # Poll for authorization
        for i in range(0, expires_in, 5):
            try:
                if progressDialog.iscanceled():
                    break
                
                progressDialog.update(int((float(i) / expires_in) * 100))
                time.sleep(5)
                
                check_result = client.request(check_url + '&agent=%s' % urllib.quote_plus(AGENT), timeout=15)
                if check_result is None:
                    continue
                
                check_data = json.loads(check_result)
                if check_data.get('status') != 'success':
                    continue
                
                check_info = check_data.get('data', {})
                if check_info.get('activated', False):
                    api_key = check_info.get('apikey', '')
                    if api_key:
                        control.set_setting('alldebrid_api_key', api_key)
                        
                        # Get username
                        user_info = getUserInfo(api_key)
                        if user_info:
                            control.set_setting('alldebrid_username', user_info.get('username', ''))
                        
                        control.infoDialog('Authorization Successful', heading='AllDebrid')
                        break
            except:
                pass

        try:
            progressDialog.close()
        except:
            pass
        
    except:
        control.openSettings('3.15')


def getUserInfo(api_key=None):
    '''Get user info from AllDebrid'''
    try:
        if api_key is None:
            api_key = credentials()['api_key']
        if not api_key:
            return None

        url = '%s/user?agent=%s&apikey=%s' % (ALLDEBRID_API, urllib.quote_plus(AGENT), api_key)
        result = client.request(url, timeout=15)
        
        if result is None:
            return None
        
        data = json.loads(result)
        if data.get('status') != 'success':
            return None
        
        return data.get('data', {}).get('user', {})
    except:
        return None


def credentials():
    return {
        'api_key': control.setting('alldebrid_api_key'),
        'username': control.setting('alldebrid_username')
    }


def getHosts():
    '''Get supported hosts from AllDebrid'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return []

        url = '%s/hosts?agent=%s&apikey=%s' % (ALLDEBRID_API, urllib.quote_plus(AGENT), api_key)
        result = cache.get(client.request, 24, url)
        
        if result is None:
            return []
        
        data = json.loads(result)
        if data.get('status') != 'success':
            return []
        
        hosts = data.get('data', {}).get('hosts', {})
        host_list = []
        for host_name, host_info in hosts.items():
            if isinstance(host_info, dict):
                domains = host_info.get('domains', [])
                host_list.extend(domains)
        
        return [h.lower() for h in host_list]
    except:
        return []


def checkCache(magnets):
    '''Check if magnets are cached on AllDebrid'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return {}

        # Extract hashes
        import re
        hashes = []
        for magnet in magnets:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
            if hash_match:
                hashes.append(hash_match.group(1).upper())
        
        if not hashes:
            return {}

        # Check cache (max 40 hashes per request)
        cached = {}
        for i in range(0, len(hashes), 40):
            batch = hashes[i:i+40]
            magnets_param = '&magnets[]=' + '&magnets[]='.join(batch)
            url = '%s/magnet/instant?agent=%s&apikey=%s%s' % (ALLDEBRID_API, urllib.quote_plus(AGENT), api_key, magnets_param)
            
            result = client.request(url, timeout=15)
            if result is None:
                continue
            
            data = json.loads(result)
            if data.get('status') != 'success':
                continue
            
            magnets_data = data.get('data', {}).get('magnets', [])
            for item in magnets_data:
                if item.get('instant', False):
                    cached[item.get('hash', '').lower()] = True
        
        return cached
    except:
        return {}


def addMagnet(magnet):
    '''Add magnet to AllDebrid'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return None

        url = '%s/magnet/upload?agent=%s&apikey=%s&magnets[]=%s' % (
            ALLDEBRID_API, urllib.quote_plus(AGENT), api_key, urllib.quote_plus(magnet)
        )
        
        result = client.request(url, timeout=30)
        if result is None:
            return None
        
        data = json.loads(result)
        if data.get('status') != 'success':
            return None
        
        magnets_data = data.get('data', {}).get('magnets', [])
        if magnets_data:
            return magnets_data[0].get('id')
        
        return None
    except:
        return None


def getMagnetStatus(magnet_id):
    '''Get magnet status from AllDebrid'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return None

        url = '%s/magnet/status?agent=%s&apikey=%s&id=%s' % (
            ALLDEBRID_API, urllib.quote_plus(AGENT), api_key, magnet_id
        )
        
        result = client.request(url, timeout=15)
        if result is None:
            return None
        
        data = json.loads(result)
        if data.get('status') != 'success':
            return None
        
        return data.get('data', {}).get('magnets', {})
    except:
        return None


def unlockLink(link):
    '''Unlock a link through AllDebrid'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return None

        url = '%s/link/unlock?agent=%s&apikey=%s&link=%s' % (
            ALLDEBRID_API, urllib.quote_plus(AGENT), api_key, urllib.quote_plus(link)
        )
        
        result = client.request(url, timeout=15)
        if result is None:
            return None
        
        data = json.loads(result)
        if data.get('status') != 'success':
            return None
        
        return data.get('data', {}).get('link')
    except:
        return None


def resolve(url):
    '''Resolve URL through AllDebrid'''
    try:
        api_key = credentials()['api_key']
        if not api_key:
            return None

        if url.startswith('magnet:'):
            # Handle magnet link
            magnet_id = addMagnet(url)
            if not magnet_id:
                return None
            
            # Wait for magnet to be ready (max 60 seconds)
            for i in range(60):
                time.sleep(1)
                status = getMagnetStatus(magnet_id)
                if status and status.get('status') == 'Ready':
                    links = status.get('links', [])
                    if links:
                        # Get the largest video file
                        video_link = None
                        max_size = 0
                        for link in links:
                            if link.get('size', 0) > max_size:
                                if any(ext in link.get('filename', '').lower() for ext in ['.mkv', '.mp4', '.avi', '.wmv']):
                                    max_size = link.get('size', 0)
                                    video_link = link.get('link')
                        
                        if video_link:
                            return unlockLink(video_link)
                    break
            
            return None
        else:
            # Handle regular link
            return unlockLink(url)
    except:
        return None
