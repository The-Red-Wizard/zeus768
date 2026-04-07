# -*- coding: utf-8 -*-
"""Syncher - TorBox resolver"""

from resources.lib.modules import control
from resources.lib.modules import client

TB_BASE = 'https://api.torbox.app/v1/api'

def auth():
    try:
        dp = control.progressDialog()
        dp.create('TorBox Authorization', '')
        dp.update(0, 'Go to: [COLOR skyblue]https://torbox.app/settings[/COLOR]\nCopy your API key and enter it below')

        import time
        time.sleep(3)
        dp.close()

        api_key = control.keyboard('', 'Enter TorBox API Key')
        if not api_key:
            return

        # Verify key
        r = client.request_json(TB_BASE + '/user/me', headers={'Authorization': 'Bearer %s' % api_key})
        if r and r.get('data'):
            control.set_setting('tb.apikey', api_key)
            control.set_setting('tb.enabled', 'true')
            username = r['data'].get('email', 'User')
            control.infoDialog('TorBox Authorized: %s' % username)
        else:
            control.infoDialog('TorBox: Invalid API key')
    except Exception as e:
        control.log('TB auth error: %s' % e)

def is_enabled():
    return control.setting('tb.enabled') == 'true' and bool(control.setting('tb.apikey'))

def resolve(url):
    try:
        apikey = control.setting('tb.apikey')
        if not apikey:
            return None
        h = {'Authorization': 'Bearer %s' % apikey}
        # For direct links, create a web download
        r = client.request_json(TB_BASE + '/webdl/createwebdownload', post={'url': url, 'name': ''}, headers=h)
        if r and r.get('data', {}).get('download_url'):
            return r['data']['download_url']
        # Fallback: check if already cached
        if r and r.get('data', {}).get('id'):
            dl_id = r['data']['id']
            import time
            time.sleep(2)
            link = client.request_json(TB_BASE + '/webdl/requestdl?token=%s&web_id=%s' % (apikey, dl_id), headers=h)
            if link and link.get('data'):
                return link['data']
    except Exception as e:
        control.log('TB resolve error: %s' % e)
    return None

def check_cache(hashes):
    try:
        apikey = control.setting('tb.apikey')
        if not apikey:
            return {}
        h = {'Authorization': 'Bearer %s' % apikey}
        hash_str = ','.join(hashes[:100])
        r = client.request_json(TB_BASE + '/torrents/checkcached?hash=%s' % hash_str, headers=h)
        if r and r.get('data'):
            cached = {}
            for h_val in r['data']:
                if isinstance(h_val, str):
                    cached[h_val.lower()] = True
                elif isinstance(h_val, dict) and h_val.get('hash'):
                    cached[h_val['hash'].lower()] = True
            return cached
    except:
        pass
    return {}

def add_magnet(magnet):
    try:
        apikey = control.setting('tb.apikey')
        if not apikey:
            return None
        h = {'Authorization': 'Bearer %s' % apikey}
        r = client.request_json(TB_BASE + '/torrents/createtorrent', post={'magnet': magnet}, headers=h)
        if r and r.get('data', {}).get('torrent_id'):
            torrent_id = r['data']['torrent_id']
            import time
            time.sleep(3)
            link = client.request_json(
                TB_BASE + '/torrents/requestdl?token=%s&torrent_id=%s&file_id=0' % (apikey, torrent_id), headers=h)
            if link and link.get('data'):
                return link['data']
    except Exception as e:
        control.log('TB magnet error: %s' % e)
    return None
