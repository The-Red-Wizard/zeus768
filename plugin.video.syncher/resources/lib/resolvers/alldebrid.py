# -*- coding: utf-8 -*-
"""Syncher - AllDebrid resolver"""

import time
from resources.lib.modules import control
from resources.lib.modules import client

AD_BASE = 'https://api.alldebrid.com/v4'
AGENT = 'syncher'

def auth():
    try:
        r = client.request_json(AD_BASE + '/pin/get?agent=%s' % AGENT)
        if not r or not r.get('data'):
            control.infoDialog('Failed to get AllDebrid code')
            return

        data = r['data']
        user_code = data['pin']
        check_url = data['check']
        verification_url = data['base_url']
        expires_in = int(data['expires_in'])

        dp = control.progressDialog()
        dp.create('AllDebrid',
                   'Go to: [COLOR skyblue]%s[/COLOR]\nEnter code: [COLOR skyblue]%s[/COLOR]' % (verification_url, user_code))

        for i in range(0, expires_in):
            if dp.iscanceled():
                break
            time.sleep(1)
            if not float(i) % 5 == 0:
                continue
            try:
                cr = client.request_json(check_url + '?agent=%s&pin=%s' % (AGENT, user_code))
                if cr and cr.get('data', {}).get('activated'):
                    api_key = cr['data']['apikey']
                    control.set_setting('ad.apikey', api_key)
                    control.set_setting('ad.enabled', 'true')
                    dp.close()
                    control.infoDialog('AllDebrid Authorized!')
                    return
            except:
                pass

        try:
            dp.close()
        except:
            pass
    except Exception as e:
        control.log('AD auth error: %s' % e)

def is_enabled():
    return control.setting('ad.enabled') == 'true' and bool(control.setting('ad.apikey'))

def resolve(url):
    try:
        apikey = control.setting('ad.apikey')
        if not apikey:
            return None
        r = client.request_json(AD_BASE + '/link/unlock?agent=%s&apikey=%s&link=%s' % (AGENT, apikey, url))
        if r and r.get('data', {}).get('link'):
            return r['data']['link']
    except Exception as e:
        control.log('AD resolve error: %s' % e)
    return None

def check_cache(hashes):
    try:
        apikey = control.setting('ad.apikey')
        if not apikey:
            return {}
        magnets = '&'.join(['magnets[]=%s' % h for h in hashes[:100]])
        r = client.request_json(AD_BASE + '/magnet/instant?agent=%s&apikey=%s&%s' % (AGENT, apikey, magnets))
        if r and r.get('data', {}).get('magnets'):
            cached = {}
            for m in r['data']['magnets']:
                if m.get('instant'):
                    cached[m['hash'].lower()] = True
            return cached
    except:
        pass
    return {}

def add_magnet(magnet):
    try:
        apikey = control.setting('ad.apikey')
        if not apikey:
            return None
        r = client.request_json(AD_BASE + '/magnet/upload?agent=%s&apikey=%s&magnets[]=%s' % (AGENT, apikey, magnet))
        if r and r.get('data', {}).get('magnets'):
            mag_id = r['data']['magnets'][0].get('id')
            if mag_id:
                time.sleep(2)
                info = client.request_json(AD_BASE + '/magnet/status?agent=%s&apikey=%s&id=%s' % (AGENT, apikey, mag_id))
                if info and info.get('data', {}).get('magnets', {}).get('links'):
                    link = info['data']['magnets']['links'][0].get('link')
                    if link:
                        return resolve(link)
    except Exception as e:
        control.log('AD magnet error: %s' % e)
    return None
