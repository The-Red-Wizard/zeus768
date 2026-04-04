# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    Real-Debrid resolver with device code authentication
'''

import urllib
import json
import time
import urlparse

from resources.lib.libraries import cache
from resources.lib.libraries import control
from resources.lib.libraries import client


CLIENT_ID = 'X245A4XAIBGVM'
USER_AGENT = 'Genesis for Kodi/1.0'


def rdAuthorize():
    try:
        if not '' in credentials()['realdebrid'].values():
            if control.yesnoDialog(
                'Real-Debrid is already authorized.',
                'Do you want to reset authorization?', '',
                'Real-Debrid',
                'No', 'Yes'
            ):
                control.set_setting('realdebrid_client_id', '')
                control.set_setting('realdebrid_client_secret', '')
                control.set_setting('realdebrid_token', '')
                control.set_setting('realdebrid_refresh', '')
                control.set_setting('realdebrid_auth', '')
            raise Exception()

        headers = {'User-Agent': USER_AGENT}
        url = 'https://api.real-debrid.com/oauth/v2/device/code?client_id=%s&new_credentials=yes' % (CLIENT_ID)
        result = client.request(url, headers=headers)
        result = json.loads(result)
        verification_url = control.lang(30416).encode('utf-8') + '[COLOR skyblue]%s[/COLOR]' % (result['verification_url'])
        user_code = control.lang(30417).encode('utf-8') + '[COLOR skyblue]%s[/COLOR]' % (result['user_code'])
        device_code = result['device_code']
        interval = result['interval']

        progressDialog = control.progressDialog
        progressDialog.create('Real-Debrid', verification_url, user_code)

        for i in range(0, 3600):
            try:
                if progressDialog.iscanceled(): break
                time.sleep(1)
                if not float(i) % interval == 0: raise Exception()
                url = 'https://api.real-debrid.com/oauth/v2/device/credentials?client_id=%s&code=%s' % (CLIENT_ID, device_code)
                result = client.request(url, headers=headers, error=True)
                result = json.loads(result)
                if 'client_secret' in result: break
            except:
                pass

        try: progressDialog.close()
        except: pass

        id, secret = result['client_id'], result['client_secret']

        url = 'https://api.real-debrid.com/oauth/v2/token'
        post = urllib.urlencode({'client_id': id, 'client_secret': secret, 'code': device_code, 'grant_type': 'http://oauth.net/grant_type/device/1.0'})

        result = client.request(url, post=post, headers=headers)
        result = json.loads(result)

        token, refresh = result['access_token'], result['refresh_token']
        control.log("### Real-Debrid Auth - id:%s, secret:%s, token:%s, refresh:%s " % (id, secret, token, refresh))
        control.set_setting('realdebrid_client_id', id)
        control.set_setting('realdebrid_client_secret', secret)
        control.set_setting('realdebrid_token', token)
        control.set_setting('realdebrid_refresh', refresh)
        control.set_setting('realdebrid_auth', '*************')

        control.infoDialog('Authorization Successful', heading='Real-Debrid')
        raise Exception()
    except:
        control.openSettings('3.13')


def rdDict():
    try:
        if '' in credentials()['realdebrid'].values(): raise Exception()
        url = 'https://api.real-debrid.com/rest/1.0/hosts/domains'
        result = cache.get(client.request, 24, url)
        hosts = json.loads(result)
        hosts = [i.lower() for i in hosts]
        return hosts
    except:
        return []


def pzDict():
    try:
        if '' in credentials()['premiumize'].values(): raise Exception()
        user, password = credentials()['premiumize']['user'], credentials()['premiumize']['pass']
        url = 'http://api.premiumize.me/pm-api/v1.php?method=hosterlist&params[login]=%s&params[pass]=%s' % (user, password)
        result = cache.get(client.request, 24, url)
        hosts = json.loads(result)['result']['hosterlist']
        hosts = [i.lower() for i in hosts]
        return hosts
    except:
        return []


def adDict():
    try:
        if '' in credentials()['alldebrid'].values(): raise Exception()
        url = 'http://alldebrid.com/api.php?action=get_host'
        result = cache.get(client.request, 24, url)
        hosts = json.loads('[%s]' % result)
        hosts = [i.lower() for i in hosts]
        return hosts
    except:
        return []


def rpDict():
    try:
        if '' in credentials()['rpnet'].values(): raise Exception()
        url = 'http://premium.rpnet.biz/hoster2.json'
        result = cache.get(client.request, 24, url)
        result = json.loads(result)
        hosts = result['supported']
        hosts = [i.lower() for i in hosts]
        return hosts
    except:
        return []


def debridDict():
    return {
        'realdebrid': rdDict(),
        'premiumize': pzDict(),
        'alldebrid': adDict(),
        'rpnet': rpDict()
    }


def credentials():
    return {
        'realdebrid': {
            'id': control.setting('realdebrid_client_id'),
            'secret': control.setting('realdebrid_client_secret'),
            'token': control.setting('realdebrid_token'),
            'refresh': control.setting('realdebrid_refresh')
        },
        'premiumize': {
            'user': control.setting('premiumize.user'),
            'pass': control.setting('premiumize.pin')
        },
        'alldebrid': {
            'user': control.setting('alldebrid.user'),
            'pass': control.setting('alldebrid.pass')
        },
        'rpnet': {
            'user': control.setting('rpnet.user'),
            'pass': control.setting('rpnet.api')
        }
    }


def status():
    try:
        c = [i for i in credentials().values() if not '' in i.values()]
        if len(c) == 0: return False
        else: return True
    except:
        return False


def getHosts():
    myhosts2 = rdDict()
    myhosts = rdDict()
    for i in range(len(myhosts)):
        myhosts[i] = myhosts[i].split('.')[-2].encode('utf-8')
    myhosts = myhosts + myhosts2
    return myhosts


def checkCache(magnets):
    '''Check if torrents are cached on Real-Debrid'''
    try:
        creds = credentials()['realdebrid']
        if '' in creds.values():
            return {}

        token = creds['token']
        headers = {'Authorization': 'Bearer %s' % token, 'User-Agent': USER_AGENT}

        # Extract hashes
        import re
        hashes = []
        for magnet in magnets:
            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
            if hash_match:
                hashes.append(hash_match.group(1).lower())

        if not hashes:
            return {}

        # Check cache (max 100 hashes)
        cached = {}
        for i in range(0, len(hashes), 100):
            batch = hashes[i:i+100]
            url = 'https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/' + '/'.join(batch)
            result = client.request(url, headers=headers, timeout=15)
            if result:
                data = json.loads(result)
                for h in batch:
                    if h in data and data[h]:
                        # Check if there's actual cached content
                        rd_data = data[h].get('rd', [])
                        if rd_data:
                            cached[h] = True

        return cached
    except:
        return {}


def addMagnet(magnet):
    '''Add magnet to Real-Debrid'''
    try:
        creds = credentials()['realdebrid']
        if '' in creds.values():
            return None

        token = creds['token']
        headers = {'Authorization': 'Bearer %s' % token, 'User-Agent': USER_AGENT}

        url = 'https://api.real-debrid.com/rest/1.0/torrents/addMagnet'
        post = urllib.urlencode({'magnet': magnet})
        result = client.request(url, post=post, headers=headers, timeout=30)

        if result is None:
            return None

        data = json.loads(result)
        return data.get('id')
    except:
        return None


def selectFiles(torrent_id, files='all'):
    '''Select files for download'''
    try:
        creds = credentials()['realdebrid']
        if '' in creds.values():
            return False

        token = creds['token']
        headers = {'Authorization': 'Bearer %s' % token, 'User-Agent': USER_AGENT}

        url = 'https://api.real-debrid.com/rest/1.0/torrents/selectFiles/%s' % torrent_id
        post = urllib.urlencode({'files': files})
        client.request(url, post=post, headers=headers, timeout=15)
        return True
    except:
        return False


def getTorrentInfo(torrent_id):
    '''Get torrent info'''
    try:
        creds = credentials()['realdebrid']
        if '' in creds.values():
            return None

        token = creds['token']
        headers = {'Authorization': 'Bearer %s' % token, 'User-Agent': USER_AGENT}

        url = 'https://api.real-debrid.com/rest/1.0/torrents/info/%s' % torrent_id
        result = client.request(url, headers=headers, timeout=15)

        if result is None:
            return None

        return json.loads(result)
    except:
        return None


def resolve(url, debrid='realdebrid'):
    u = url
    u = u.replace('filefactory.com/stream/', 'filefactory.com/file/')
    
    try:
        u1 = urlparse.urlparse(url)[1].split('.')
        u1 = u1[-2] + '.' + u1[-1]
        if status() is False: raise Exception()
        if not debrid == 'realdebrid' and not debrid == True: raise Exception()

        if '' in credentials()['realdebrid'].values(): raise Exception()
        id, secret, token, refresh = credentials()['realdebrid']['id'], credentials()['realdebrid']['secret'], credentials()['realdebrid']['token'], credentials()['realdebrid']['refresh']
        control.log('@@ Real-Debrid refresh@@ %s' % refresh)

        # Handle magnet links
        if u.startswith('magnet:'):
            torrent_id = addMagnet(u)
            if not torrent_id:
                return None

            # Select all files
            selectFiles(torrent_id)

            # Wait for torrent to be ready (max 60 seconds)
            for i in range(60):
                time.sleep(1)
                info = getTorrentInfo(torrent_id)
                if info and info.get('status') == 'downloaded':
                    links = info.get('links', [])
                    if links:
                        # Unrestrict the first link
                        headers = {'Authorization': 'Bearer %s' % token, 'User-Agent': USER_AGENT}
                        unrestrict_url = 'https://api.real-debrid.com/rest/1.0/unrestrict/link'
                        post = urllib.urlencode({'link': links[0]})
                        result = client.request(unrestrict_url, post=post, headers=headers)
                        if result:
                            data = json.loads(result)
                            return data.get('download')
                    break

            return None

        # Handle regular links
        post = urllib.urlencode({'link': u})
        headers = {'Authorization': 'Bearer %s' % token, 'User-Agent': USER_AGENT}
        url = 'https://api.real-debrid.com/rest/1.0/unrestrict/link'

        result = client.request(url, post=post, headers=headers, error=True)
        control.log('@@ Real-Debrid RESULTS@@ %s' % result)

        result = json.loads(result)

        if 'error' in result and result['error'] == 'bad_token':
            result = client.request('https://api.real-debrid.com/oauth/v2/token', post=urllib.urlencode({'client_id': id, 'client_secret': secret, 'code': refresh, 'grant_type': 'http://oauth.net/grant_type/device/1.0'}), headers={'User-Agent': USER_AGENT}, error=True)
            result = json.loads(result)
            control.log('Refreshing Expired Real Debrid Token: |%s|%s|' % (id, refresh))
            control.log('Refreshing Expired : |%s|' % (result))

            if 'error' in result: return
            token, refresh = result['access_token'], result['refresh_token']

            control.set_setting('realdebrid_token', token)
            control.set_setting('realdebrid_refresh', refresh)

            headers['Authorization'] = 'Bearer %s' % result['access_token']
            result = client.request(url, post=post, headers=headers)
            result = json.loads(result)
            
        if 'error' in result and result['error'] == 'file_unavailable':
            control.log("@@@@ Real-Debrid FILE UNAVAIL %s ###" % (url))
            return

        url = result['download']
        return url
    except:
        pass

    try:
        if not debrid == 'premiumize' and not debrid == True: raise Exception()

        if '' in credentials()['premiumize'].values(): raise Exception()
        user, password = credentials()['premiumize']['user'], credentials()['premiumize']['pass']

        url = 'http://api.premiumize.me/pm-api/v1.php?method=directdownloadlink&params[login]=%s&params[pass]=%s&params[link]=%s' % (user, password, urllib.quote_plus(u))
        result = client.request(url, close=False)
        url = json.loads(result)['result']['location']
        return url
    except:
        pass

    try:
        if not debrid == 'alldebrid' and not debrid == True: raise Exception()

        if '' in credentials()['alldebrid'].values(): raise Exception()
        user, password = credentials()['alldebrid']['user'], credentials()['alldebrid']['pass']

        login_data = {'action': 'login', 'login_login': user, 'login_password': password}
        login_link = 'http://alldebrid.com/register/?%s' % login_data
        cookie = client.request(login_link, output='cookie', close=False)

        url = 'http://www.alldebrid.com/service.php?link=%s' % urllib.quote_plus(u)
        result = client.request(url, cookie=cookie, close=False)
        url = client.parseDOM(result, 'a', ret='href', attrs={'class': 'link_dl'})[0]
        url = client.replaceHTMLCodes(url)
        url = '%s|Cookie=%s' % (url, urllib.quote_plus(cookie))
        return url
    except:
        pass

    try:
        if not debrid == 'rpnet' and not debrid == True: raise Exception()

        if '' in credentials()['rpnet'].values(): raise Exception()
        user, password = credentials()['rpnet']['user'], credentials()['rpnet']['pass']

        login_data = {'username': user, 'password': password, 'action': 'generate', 'links': u}
        login_link = 'http://premium.rpnet.biz/client_api.php?%s' % login_data
        result = client.request(login_link, close=False)
        result = json.loads(result)
        url = result['links'][0]['generated']
        return url
    except:
        return
