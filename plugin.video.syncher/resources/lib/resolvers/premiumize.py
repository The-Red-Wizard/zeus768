# -*- coding: utf-8 -*-
"""Syncher - Premiumize resolver"""

import time
from resources.lib.modules import control
from resources.lib.modules import client

PM_BASE = 'https://www.premiumize.me/api'
OAUTH_BASE = 'https://www.premiumize.me'
CLIENT_ID = '887834873'

def auth():
    try:
        result = client.request_json(OAUTH_BASE + '/token?grant_type=device_code&client_id=%s' % CLIENT_ID)
        if not result:
            control.infoDialog('Failed to get Premiumize code')
            return

        user_code = result['user_code']
        verification_uri = result['verification_uri']
        device_code = result['device_code']
        expires_in = int(result['expires_in'])
        interval = int(result.get('interval', 5))

        dp = control.progressDialog()
        dp.create('Premiumize',
                   'Go to: [COLOR skyblue]%s[/COLOR]\nEnter code: [COLOR skyblue]%s[/COLOR]' % (verification_uri, user_code))

        for i in range(0, expires_in):
            if dp.iscanceled():
                break
            time.sleep(1)
            if not float(i) % interval == 0:
                continue
            try:
                r = client.request_json(
                    OAUTH_BASE + '/token?grant_type=device_code&client_id=%s&code=%s' % (CLIENT_ID, device_code)
                )
                if r and 'access_token' in r:
                    control.set_setting('pm.token', r['access_token'])
                    control.set_setting('pm.enabled', 'true')
                    dp.close()
                    control.infoDialog('Premiumize Authorized!')
                    return
            except:
                pass

        try:
            dp.close()
        except:
            pass
    except Exception as e:
        control.log('PM auth error: %s' % e)

def is_enabled():
    return control.setting('pm.enabled') == 'true' and bool(control.setting('pm.token'))

def resolve(url):
    try:
        token = control.setting('pm.token')
        if not token:
            return None
        r = client.request_json(PM_BASE + '/transfer/directdl?apikey=%s&src=%s' % (token, url))
        if r and r.get('status') == 'success' and r.get('content'):
            # Get largest file
            content = r['content']
            if isinstance(content, list) and len(content) > 0:
                best = sorted(content, key=lambda x: x.get('size', 0), reverse=True)[0]
                return best.get('link') or best.get('stream_link')
    except Exception as e:
        control.log('PM resolve error: %s' % e)
    return None

def check_cache(hashes):
    try:
        token = control.setting('pm.token')
        if not token:
            return {}
        items = '&'.join(['items[]=%s' % h for h in hashes[:100]])
        r = client.request_json(PM_BASE + '/cache/check?apikey=%s&%s' % (token, items))
        if r and r.get('status') == 'success':
            result = {}
            response = r.get('response', [])
            for i, h in enumerate(hashes[:100]):
                if i < len(response) and response[i]:
                    result[h.lower()] = True
            return result
    except:
        pass
    return {}

def add_magnet(magnet):
    try:
        token = control.setting('pm.token')
        if not token:
            return None
        r = client.request_json(PM_BASE + '/transfer/directdl?apikey=%s&src=%s' % (token, magnet))
        if r and r.get('status') == 'success' and r.get('content'):
            content = r['content']
            if isinstance(content, list) and len(content) > 0:
                best = sorted(content, key=lambda x: x.get('size', 0), reverse=True)[0]
                return best.get('link') or best.get('stream_link')
    except Exception as e:
        control.log('PM magnet error: %s' % e)
    return None
