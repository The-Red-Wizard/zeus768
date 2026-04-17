# -*- coding: utf-8 -*-
"""Syncher - Real-Debrid resolver"""

import json
import time
from resources.lib.modules import control
from resources.lib.modules import client

RD_BASE = 'https://api.real-debrid.com/rest/1.0'
OAUTH_BASE = 'https://api.real-debrid.com/oauth/v2'
CLIENT_ID = 'X245A4XAIBGVM'

def auth():
    try:
        url = OAUTH_BASE + '/device/code?client_id=%s&new_credentials=yes' % CLIENT_ID
        result = client.request_json(url)
        if not result:
            control.infoDialog('Failed to get Real-Debrid code')
            return

        verification_url = result['verification_url']
        user_code = result['user_code']
        device_code = result['device_code']
        expires_in = int(result['expires_in'])
        interval = int(result['interval'])

        dp = control.progressDialog()
        dp.create('Real-Debrid',
                   'Go to: [COLOR skyblue]%s[/COLOR]\nEnter code: [COLOR skyblue]%s[/COLOR]' % (verification_url, user_code))

        for i in range(0, expires_in):
            if dp.iscanceled():
                break
            time.sleep(1)
            if not float(i) % interval == 0:
                continue
            try:
                r = client.request_json(OAUTH_BASE + '/device/credentials?client_id=%s&code=%s' % (CLIENT_ID, device_code))
                if r and 'client_id' in r:
                    client_id = r['client_id']
                    client_secret = r['client_secret']

                    # Get token
                    token_data = client.request_json(
                        OAUTH_BASE + '/token',
                        post='client_id=%s&client_secret=%s&code=%s&grant_type=http://oauth.net/grant_type/device/1.0' % (client_id, client_secret, device_code),
                        headers={'Content-Type': 'application/x-www-form-urlencoded'}
                    )
                    if token_data and 'access_token' in token_data:
                        control.set_setting('rd.token', token_data['access_token'])
                        control.set_setting('rd.refresh', token_data['refresh_token'])
                        control.set_setting('rd.client_id', client_id)
                        control.set_setting('rd.secret', client_secret)
                        control.set_setting('rd.expiry', str(int(time.time()) + int(token_data.get('expires_in', 0))))
                        control.set_setting('rd.enabled', 'true')
                        dp.close()
                        control.infoDialog('Real-Debrid Authorized!')
                        return
            except:
                pass

        try:
            dp.close()
        except:
            pass
    except Exception as e:
        control.log('RD auth error: %s' % e)

def _get_token():
    token = control.setting('rd.token')
    if not token:
        return None

    # Check expiry and refresh if needed
    try:
        expiry = int(control.setting('rd.expiry') or '0')
        if time.time() > expiry - 600:
            refresh = control.setting('rd.refresh')
            cid = control.setting('rd.client_id')
            secret = control.setting('rd.secret')
            if refresh and cid and secret:
                r = client.request_json(
                    OAUTH_BASE + '/token',
                    post='client_id=%s&client_secret=%s&code=%s&grant_type=http://oauth.net/grant_type/device/1.0' % (cid, secret, refresh),
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                if r and 'access_token' in r:
                    control.set_setting('rd.token', r['access_token'])
                    control.set_setting('rd.refresh', r['refresh_token'])
                    control.set_setting('rd.expiry', str(int(time.time()) + int(r.get('expires_in', 0))))
                    return r['access_token']
    except:
        pass
    return token

def is_enabled():
    return control.setting('rd.enabled') == 'true' and bool(control.setting('rd.token'))

def resolve(url):
    """Resolve a link through Real-Debrid"""
    try:
        token = _get_token()
        if not token:
            return None
        h = {'Authorization': 'Bearer %s' % token}
        r = client.request_json(RD_BASE + '/unrestrict/link', post={'link': url}, headers=h)
        if r and 'download' in r:
            return r['download']
    except Exception as e:
        control.log('RD resolve error: %s' % e)
    return None

def check_cache(hashes):
    """Check if torrents are cached on RD"""
    try:
        token = _get_token()
        if not token:
            return {}
        h = {'Authorization': 'Bearer %s' % token}
        hash_str = '/'.join(hashes[:100])
        r = client.request_json(RD_BASE + '/torrents/instantAvailability/%s' % hash_str, headers=h)
        if r:
            cached = {}
            for hash_val, data in r.items():
                if data and isinstance(data, dict) and data.get('rd'):
                    cached[hash_val.lower()] = True
            return cached
    except:
        pass
    return {}

def add_magnet(magnet):
    """Add a magnet to RD and get download link"""
    try:
        token = _get_token()
        if not token:
            return None
        h = {'Authorization': 'Bearer %s' % token}
        r = client.request_json(RD_BASE + '/torrents/addMagnet', post={'magnet': magnet}, headers=h)
        if r and 'id' in r:
            torrent_id = r['id']
            # Select all files
            client.request(RD_BASE + '/torrents/selectFiles/%s' % torrent_id,
                          post={'files': 'all'}, headers=h)
            time.sleep(1)
            # Get info
            info = client.request_json(RD_BASE + '/torrents/info/%s' % torrent_id, headers=h)
            if info and info.get('links'):
                return resolve(info['links'][0])
    except Exception as e:
        control.log('RD magnet error: %s' % e)
    return None
