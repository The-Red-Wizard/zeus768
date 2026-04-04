# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    Premiumize resolver with PIN/OAuth device flow authentication
'''

import urllib
import json
import time

from resources.lib.libraries import cache
from resources.lib.libraries import control
from resources.lib.libraries import client


# Premiumize API
PREMIUMIZE_API = 'https://www.premiumize.me/api'
CLIENT_ID = 'Genesis'


def pmAuthorize():
    '''Device code flow for Premiumize API authorization'''
    try:
        if not '' in credentials().values():
            if control.yesnoDialog(
                'Premiumize is already authorized.',
                'Do you want to reset authorization?', '',
                'Premiumize',
                'No', 'Yes'
            ):
                control.set_setting('premiumize_token', '')
                control.set_setting('premiumize_user', '')
            raise Exception()

        # Get device code
        url = 'https://www.premiumize.me/token?grant_type=device_code&client_id=%s' % CLIENT_ID
        result = client.request(url, timeout=15)
        
        if result is None:
            control.infoDialog('Failed to get device code', heading='Premiumize')
            raise Exception()
        
        data = json.loads(result)
        device_code = data.get('device_code', '')
        user_code = data.get('user_code', '')
        verification_url = data.get('verification_uri', 'https://www.premiumize.me/device')
        expires_in = data.get('expires_in', 600)
        interval = data.get('interval', 5)

        verification_text = control.lang(30416).encode('utf-8') + '[COLOR skyblue]%s[/COLOR]' % verification_url
        user_code_text = control.lang(30417).encode('utf-8') + '[COLOR skyblue]%s[/COLOR]' % user_code

        progressDialog = control.progressDialog
        progressDialog.create('Premiumize', verification_text, user_code_text)

        # Poll for authorization
        for i in range(0, expires_in, interval):
            try:
                if progressDialog.iscanceled():
                    break
                
                progressDialog.update(int((float(i) / expires_in) * 100))
                time.sleep(interval)
                
                token_url = 'https://www.premiumize.me/token?grant_type=device_code&client_id=%s&code=%s' % (CLIENT_ID, device_code)
                token_result = client.request(token_url, timeout=15)
                
                if token_result is None:
                    continue
                
                token_data = json.loads(token_result)
                
                if 'access_token' in token_data:
                    access_token = token_data.get('access_token', '')
                    control.set_setting('premiumize_token', access_token)
                    
                    # Get user info
                    user_info = getUserInfo(access_token)
                    if user_info:
                        control.set_setting('premiumize_user', user_info.get('customer_id', ''))
                    
                    control.infoDialog('Authorization Successful', heading='Premiumize')
                    break
            except:
                pass

        try:
            progressDialog.close()
        except:
            pass
        
    except:
        control.openSettings('3.14')


def getUserInfo(token=None):
    '''Get user info from Premiumize'''
    try:
        if token is None:
            token = credentials()['token']
        if not token:
            return None

        url = '%s/account/info?apikey=%s' % (PREMIUMIZE_API, token)
        result = client.request(url, timeout=15)
        
        if result is None:
            return None
        
        data = json.loads(result)
        if data.get('status') != 'success':
            return None
        
        return data
    except:
        return None


def credentials():
    return {
        'token': control.setting('premiumize_token'),
        'user': control.setting('premiumize_user')
    }


def getCredentials():
    '''Legacy compatibility function'''
    token = control.setting('premiumize_token')
    user = control.setting('premiumize_user')
    if not token:
        return False
    return (user, token)


def getHosts():
    '''Get supported hosts from Premiumize'''
    try:
        token = credentials()['token']
        if not token:
            return []

        url = '%s/services/list?apikey=%s' % (PREMIUMIZE_API, token)
        result = cache.get(client.request, 24, url)
        
        if result is None:
            return []
        
        data = json.loads(result)
        if data.get('status') != 'success':
            return []
        
        # Get direct download hosts
        directdl = data.get('directdl', [])
        hosts = []
        for host in directdl:
            hosts.append(host.rsplit('.', 1)[0].lower())
        
        return hosts
    except:
        return []


def checkCache(magnets):
    '''Check if magnets are cached on Premiumize'''
    try:
        token = credentials()['token']
        if not token:
            return {}

        # Extract hashes
        import re
        items = []
        for magnet in magnets:
            items.append(magnet)
        
        if not items:
            return {}

        # Check cache
        url = '%s/cache/check?apikey=%s' % (PREMIUMIZE_API, token)
        post_data = urllib.urlencode({'items[]': items})
        
        result = client.request(url, post=post_data, timeout=15)
        if result is None:
            return {}
        
        data = json.loads(result)
        if data.get('status') != 'success':
            return {}
        
        cached = {}
        response = data.get('response', [])
        transcoded = data.get('transcoded', [])
        
        for i, item in enumerate(items):
            if i < len(response) and response[i]:
                # Extract hash from magnet
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', item)
                if hash_match:
                    cached[hash_match.group(1).lower()] = True
        
        return cached
    except:
        return {}


def addTransfer(magnet):
    '''Add transfer to Premiumize'''
    try:
        token = credentials()['token']
        if not token:
            return None

        url = '%s/transfer/create?apikey=%s' % (PREMIUMIZE_API, token)
        post_data = urllib.urlencode({'src': magnet})
        
        result = client.request(url, post=post_data, timeout=30)
        if result is None:
            return None
        
        data = json.loads(result)
        if data.get('status') != 'success':
            return None
        
        return data.get('id')
    except:
        return None


def directDownload(magnet):
    '''Direct download from cache'''
    try:
        token = credentials()['token']
        if not token:
            return None

        url = '%s/transfer/directdl?apikey=%s' % (PREMIUMIZE_API, token)
        post_data = urllib.urlencode({'src': magnet})
        
        result = client.request(url, post=post_data, timeout=30)
        if result is None:
            return None
        
        data = json.loads(result)
        if data.get('status') != 'success':
            return None
        
        content = data.get('content', [])
        if not content:
            return None
        
        # Find largest video file
        video_file = None
        max_size = 0
        for item in content:
            if item.get('size', 0) > max_size:
                filename = item.get('path', '')
                if any(ext in filename.lower() for ext in ['.mkv', '.mp4', '.avi', '.wmv', '.mov']):
                    max_size = item.get('size', 0)
                    video_file = item.get('link')
        
        return video_file
    except:
        return None


def resolve(url):
    '''Resolve URL through Premiumize'''
    try:
        token = credentials()['token']
        if not token:
            # Fallback to legacy credentials
            creds = getCredentials()
            if not creds:
                return None
            user, password = creds
            url = 'http://api.premiumize.me/pm-api/v1.php?method=directdownloadlink&params[login]=%s&params[pass]=%s&params[link]=%s' % (user, password, urllib.quote_plus(url))
            url = url.replace('filefactory.com/stream/', 'filefactory.com/file/')
            result = client.request(url, close=False)
            return json.loads(result)['result']['location']

        if url.startswith('magnet:'):
            # Try direct download first (cached)
            download_url = directDownload(url)
            if download_url:
                return download_url
            
            # If not cached, add transfer and wait
            transfer_id = addTransfer(url)
            if not transfer_id:
                return None
            
            # Wait for transfer (max 60 seconds)
            for i in range(60):
                time.sleep(1)
                # Check transfer status
                status_url = '%s/transfer/list?apikey=%s' % (PREMIUMIZE_API, token)
                status_result = client.request(status_url, timeout=15)
                if status_result:
                    status_data = json.loads(status_result)
                    transfers = status_data.get('transfers', [])
                    for t in transfers:
                        if t.get('id') == transfer_id and t.get('status') == 'finished':
                            folder_id = t.get('folder_id')
                            if folder_id:
                                # Get folder contents
                                folder_url = '%s/folder/list?apikey=%s&id=%s' % (PREMIUMIZE_API, token, folder_id)
                                folder_result = client.request(folder_url, timeout=15)
                                if folder_result:
                                    folder_data = json.loads(folder_result)
                                    content = folder_data.get('content', [])
                                    for item in content:
                                        if item.get('type') == 'file':
                                            return item.get('link')
                            break
            
            return None
        else:
            # Regular link
            url_encoded = '%s/transfer/directdl?apikey=%s' % (PREMIUMIZE_API, token)
            post_data = urllib.urlencode({'src': url})
            result = client.request(url_encoded, post=post_data, timeout=15)
            if result:
                data = json.loads(result)
                if data.get('status') == 'success':
                    return data.get('location')
            return None
    except:
        return None
