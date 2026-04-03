# -*- coding: utf-8 -*-
"""Trakt Auth - Device flow using zeus768 credentials. Native urllib."""
import json
import ssl
import time
import urllib.request
import urllib.error
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
SSL_CTX = ssl._create_unverified_context()

CLIENT_ID = 'd2a8e820fec0d46079cbbceaca851648df9431cbc73ede2c10d35dfb1c7a36e2'
CLIENT_SECRET = '9c7c29e76166465882ba6723d578e97fce466cf466414a76c36184540b31e9a6'


def _post(url, data, headers=None):
    hdrs = {
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': CLIENT_ID,
        'User-Agent': 'Kodi TraktPlayer/2.1.0'
    }
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=hdrs, method='POST')
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        xbmc.log('Trakt Auth HTTP error %d for %s' % (e.code, url), xbmc.LOGERROR)
        try:
            body = e.read().decode('utf-8')
            xbmc.log('Trakt Auth error body: %s' % body[:500], xbmc.LOGERROR)
        except Exception:
            pass
        return e.code, {}
    except Exception as e:
        xbmc.log('Trakt Auth network error for %s: %s' % (url, str(e)), xbmc.LOGERROR)
        return 0, {}


def is_authorized():
    return bool(ADDON.getSetting('trakt_access_token')) and ADDON.getSetting('trakt_auth_done') == 'true'


def get_token():
    return ADDON.getSetting('trakt_access_token')


def authorize():
    xbmc.log('Trakt Auth: Requesting device code from api.trakt.tv...', xbmc.LOGINFO)
    status, data = _post('https://api.trakt.tv/oauth/device/code', {'client_id': CLIENT_ID})
    xbmc.log('Trakt Auth: device/code response status=%d, data_keys=%s' % (status, list(data.keys()) if data else 'empty'), xbmc.LOGINFO)
    if status != 200 or not data:
        xbmcgui.Dialog().notification('Error', 'Failed to get device code (HTTP %d)' % status, xbmcgui.NOTIFICATION_ERROR)
        return False

    device_code = data.get('device_code', '')
    user_code = data.get('user_code', '')
    url = data.get('verification_url', 'https://trakt.tv/activate')
    expires = data.get('expires_in', 600)
    interval = data.get('interval', 5)

    if not device_code or not user_code:
        xbmc.log('Trakt Auth: Missing device_code or user_code in response', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', 'Invalid device code response', xbmcgui.NOTIFICATION_ERROR)
        return False

    xbmc.log('Trakt Auth: Got code=%s, url=%s, expires=%d' % (user_code, url, expires), xbmc.LOGINFO)

    progress = xbmcgui.DialogProgress()
    progress.create('Trakt Authorization',
                    f'Go to: [B][COLOR skyblue]{url}[/COLOR][/B]\n\n'
                    f'Enter code: [B][COLOR yellow]{user_code}[/COLOR][/B]')

    start = time.time()
    while time.time() - start < expires:
        if progress.iscanceled():
            progress.close()
            return False
        progress.update(int(((time.time() - start) / expires) * 100))
        time.sleep(interval)

        s, tokens = _post('https://api.trakt.tv/oauth/device/token', {
            'code': device_code, 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET
        })
        if s == 200 and tokens.get('access_token'):
            ADDON.setSetting('trakt_access_token', tokens['access_token'])
            ADDON.setSetting('trakt_refresh_token', tokens.get('refresh_token', ''))
            ADDON.setSetting('trakt_auth_done', 'true')
            progress.close()
            xbmcgui.Dialog().notification('Success', 'Trakt authorized!', xbmcgui.NOTIFICATION_INFO)
            return True
        if s in (404, 409, 410, 418):
            progress.close()
            return False

    progress.close()
    return False


def refresh_token():
    refresh = ADDON.getSetting('trakt_refresh_token')
    if not refresh:
        return False
    s, tokens = _post('https://api.trakt.tv/oauth/token', {
        'refresh_token': refresh, 'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET, 'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'grant_type': 'refresh_token'
    })
    if s == 200 and tokens.get('access_token'):
        ADDON.setSetting('trakt_access_token', tokens['access_token'])
        ADDON.setSetting('trakt_refresh_token', tokens.get('refresh_token', refresh))
        return True
    return False


def revoke():
    ADDON.setSetting('trakt_access_token', '')
    ADDON.setSetting('trakt_refresh_token', '')
    ADDON.setSetting('trakt_auth_done', 'false')
    xbmcgui.Dialog().notification('Trakt', 'Account unlinked', xbmcgui.NOTIFICATION_INFO)
