# -*- coding: utf-8 -*-
"""Debrid services: RD, PM, AD, TorBox. Native urllib. Video-only file selection."""
import json
import ssl
import time
import urllib.request
import urllib.error
import urllib.parse
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
SSL_CTX = ssl._create_unverified_context()
VIDEO_EXTS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.mpg', '.mpeg', '.ts', '.webm')


def _http(url, data=None, headers=None, method='GET'):
    hdrs = {'User-Agent': 'TraktPlayer/2.0'}
    if headers:
        hdrs.update(headers)
    if data and isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except:
            return e.code, {}
    except Exception as e:
        return 0, {'error': str(e)}


class RealDebrid:
    BASE_URL = 'https://api.real-debrid.com/rest/1.0'
    CLIENT_ID = 'X245A4XAIBGVM'

    def __init__(self):
        self.token = ADDON.getSetting('rd_access_token')

    def is_authorized(self):
        return bool(self.token) and ADDON.getSetting('rd_auth_done') == 'true'

    def authorize(self):
        _, data = _http(f'{self.BASE_URL}/oauth/v2/device/code?client_id={self.CLIENT_ID}&new_credentials=yes')
        if not data.get('device_code'):
            return False
        device_code = data['device_code']
        user_code = data['user_code']
        url = data.get('verification_url', 'https://real-debrid.com/device')
        expires = data.get('expires_in', 600)
        interval = data.get('interval', 5)

        dlg = xbmcgui.DialogProgress()
        dlg.create('Real-Debrid', f'Go to: [B]{url}[/B]\nEnter: [B][COLOR yellow]{user_code}[/COLOR][/B]')
        start = time.time()
        while time.time() - start < expires:
            if dlg.iscanceled():
                dlg.close()
                return False
            dlg.update(int(((time.time() - start) / expires) * 100))
            time.sleep(interval)
            s, creds = _http(f'{self.BASE_URL}/oauth/v2/device/credentials?client_id={self.CLIENT_ID}&code={device_code}')
            if s == 200 and creds.get('client_id'):
                _, tokens = _http(f'{self.BASE_URL}/oauth/v2/token', data={
                    'client_id': creds['client_id'], 'client_secret': creds['client_secret'],
                    'code': device_code, 'grant_type': 'http://oauth.net/grant_type/device/1.0'
                }, method='POST')
                if tokens.get('access_token'):
                    ADDON.setSetting('rd_access_token', tokens['access_token'])
                    ADDON.setSetting('rd_refresh_token', tokens.get('refresh_token', ''))
                    ADDON.setSetting('rd_client_id', creds['client_id'])
                    ADDON.setSetting('rd_client_secret', creds['client_secret'])
                    ADDON.setSetting('rd_auth_done', 'true')
                    self.token = tokens['access_token']
                    dlg.close()
                    xbmcgui.Dialog().notification('Success', 'Real-Debrid linked!', xbmcgui.NOTIFICATION_INFO)
                    return True
        dlg.close()
        return False

    def resolve_magnet(self, magnet):
        if not self.is_authorized():
            return None
        auth = {'Authorization': f'Bearer {self.token}'}
        _, res = _http(f'{self.BASE_URL}/torrents/addMagnet', data={'magnet': magnet}, headers=auth, method='POST')
        tid = res.get('id')
        if not tid:
            return None
        _, info = _http(f'{self.BASE_URL}/torrents/info/{tid}', headers=auth)
        files = info.get('files', [])
        vids = [str(f['id']) for f in files if f.get('path', '').lower().endswith(VIDEO_EXTS)]
        fids = ','.join(vids) if vids else 'all'
        _http(f'{self.BASE_URL}/torrents/selectFiles/{tid}', data={'files': fids}, headers=auth, method='POST')
        for _ in range(30):
            _, st = _http(f'{self.BASE_URL}/torrents/info/{tid}', headers=auth)
            if st.get('status') == 'downloaded':
                for link in st.get('links', []):
                    _, dl = _http(f'{self.BASE_URL}/unrestrict/link', data={'link': link}, headers=auth, method='POST')
                    url = dl.get('download', '')
                    if url and not url.lower().split('?')[0].endswith(('.rar', '.zip', '.7z')):
                        return url
                links = st.get('links', [])
                if links:
                    _, dl = _http(f'{self.BASE_URL}/unrestrict/link', data={'link': links[0]}, headers=auth, method='POST')
                    return dl.get('download')
            elif st.get('status') in ('error', 'dead', 'magnet_error'):
                return None
            time.sleep(2)
        return None

    def revoke(self):
        for k in ('rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret'):
            ADDON.setSetting(k, '')
        ADDON.setSetting('rd_auth_done', 'false')
        xbmcgui.Dialog().notification('Real-Debrid', 'Unlinked', xbmcgui.NOTIFICATION_INFO)


class AllDebrid:
    BASE_URL = 'https://api.alldebrid.com/v4'
    AGENT = 'TraktPlayer'

    def __init__(self):
        self.token = ADDON.getSetting('ad_api_key')

    def is_authorized(self):
        return bool(self.token) and ADDON.getSetting('ad_auth_done') == 'true'

    def authorize(self):
        _, data = _http(f'{self.BASE_URL}/pin/get?agent={self.AGENT}')
        if data.get('status') != 'success':
            return False
        d = data.get('data', {})
        pin, check_url, url = d.get('pin'), d.get('check_url'), d.get('user_url', 'https://alldebrid.com/pin/')
        expires = d.get('expires_in', 600)

        dlg = xbmcgui.DialogProgress()
        dlg.create('AllDebrid', f'Go to: [B]{url}[/B]\nEnter PIN: [B][COLOR yellow]{pin}[/COLOR][/B]')
        start = time.time()
        while time.time() - start < expires:
            if dlg.iscanceled():
                dlg.close()
                return False
            dlg.update(int(((time.time() - start) / expires) * 100))
            time.sleep(5)
            _, ck = _http(f'{check_url}&agent={self.AGENT}')
            if ck.get('status') == 'success':
                apikey = ck.get('data', {}).get('apikey')
                if apikey:
                    ADDON.setSetting('ad_api_key', apikey)
                    ADDON.setSetting('ad_auth_done', 'true')
                    self.token = apikey
                    dlg.close()
                    xbmcgui.Dialog().notification('Success', 'AllDebrid linked!', xbmcgui.NOTIFICATION_INFO)
                    return True
        dlg.close()
        return False

    def resolve_magnet(self, magnet):
        if not self.is_authorized():
            return None
        _, res = _http(f'{self.BASE_URL}/magnet/upload?agent={self.AGENT}&apikey={self.token}&magnets[]={urllib.parse.quote(magnet)}')
        if res.get('status') != 'success':
            return None
        mid = res.get('data', {}).get('magnets', [{}])[0].get('id')
        if not mid:
            return None
        for _ in range(30):
            _, st = _http(f'{self.BASE_URL}/magnet/status?agent={self.AGENT}&apikey={self.token}&id={mid}')
            if st.get('status') == 'success':
                md = st.get('data', {}).get('magnets', {})
                if md.get('status') == 'Ready':
                    links = md.get('links', [])
                    if links:
                        _, dl = _http(f'{self.BASE_URL}/link/unlock?agent={self.AGENT}&apikey={self.token}&link={urllib.parse.quote(links[0].get("link", ""))}')
                        if dl.get('status') == 'success':
                            return dl.get('data', {}).get('link')
            time.sleep(2)
        return None

    def revoke(self):
        ADDON.setSetting('ad_api_key', '')
        ADDON.setSetting('ad_auth_done', 'false')
        xbmcgui.Dialog().notification('AllDebrid', 'Unlinked', xbmcgui.NOTIFICATION_INFO)


class Premiumize:
    BASE_URL = 'https://www.premiumize.me/api'
    CLIENT_ID = '855400527'

    def __init__(self):
        self.token = ADDON.getSetting('pm_access_token')

    def is_authorized(self):
        return bool(self.token) and ADDON.getSetting('pm_auth_done') == 'true'

    def authorize(self):
        _, data = _http(f'{self.BASE_URL}/token', data={'grant_type': 'device_code', 'client_id': self.CLIENT_ID}, method='POST')
        device_code = data.get('device_code')
        user_code = data.get('user_code')
        url = data.get('verification_uri', 'https://www.premiumize.me/device')
        expires = data.get('expires_in', 600)
        interval = data.get('interval', 5)

        dlg = xbmcgui.DialogProgress()
        dlg.create('Premiumize', f'Go to: [B]{url}[/B]\nEnter: [B][COLOR yellow]{user_code}[/COLOR][/B]')
        start = time.time()
        while time.time() - start < expires:
            if dlg.iscanceled():
                dlg.close()
                return False
            dlg.update(int(((time.time() - start) / expires) * 100))
            time.sleep(interval)
            _, ck = _http(f'{self.BASE_URL}/token', data={'grant_type': 'device_code', 'client_id': self.CLIENT_ID, 'code': device_code}, method='POST')
            if ck.get('access_token'):
                ADDON.setSetting('pm_access_token', ck['access_token'])
                ADDON.setSetting('pm_auth_done', 'true')
                self.token = ck['access_token']
                dlg.close()
                xbmcgui.Dialog().notification('Success', 'Premiumize linked!', xbmcgui.NOTIFICATION_INFO)
                return True
        dlg.close()
        return False

    def resolve_magnet(self, magnet):
        if not self.is_authorized():
            return None
        _, res = _http(f'{self.BASE_URL}/transfer/directdl', data={'src': magnet}, headers={'Authorization': f'Bearer {self.token}'}, method='POST')
        if res.get('status') == 'success':
            content = res.get('content', [])
            if content:
                biggest = max(content, key=lambda x: x.get('size', 0))
                return biggest.get('link')
        return None

    def revoke(self):
        ADDON.setSetting('pm_access_token', '')
        ADDON.setSetting('pm_auth_done', 'false')
        xbmcgui.Dialog().notification('Premiumize', 'Unlinked', xbmcgui.NOTIFICATION_INFO)


class TorBox:
    BASE_URL = 'https://api.torbox.app/v1/api'

    def __init__(self):
        self.token = ADDON.getSetting('tb_api_key')

    def is_authorized(self):
        return bool(self.token) and ADDON.getSetting('tb_auth_done') == 'true'

    def authorize(self):
        kb = xbmc.Keyboard('', 'Enter TorBox API Key')
        kb.doModal()
        if kb.isConfirmed():
            key = kb.getText().strip()
            if key:
                _, res = _http(f'{self.BASE_URL}/user/me', headers={'Authorization': f'Bearer {key}'})
                if isinstance(res, dict) and res.get('success'):
                    ADDON.setSetting('tb_api_key', key)
                    ADDON.setSetting('tb_auth_done', 'true')
                    self.token = key
                    plan = res.get('data', {}).get('plan', 'Unknown')
                    xbmcgui.Dialog().notification('Success', f'TorBox linked! Plan: {plan}', xbmcgui.NOTIFICATION_INFO)
                    return True
                else:
                    xbmcgui.Dialog().notification('Error', 'Invalid API key', xbmcgui.NOTIFICATION_ERROR)
        return False

    def resolve_magnet(self, magnet):
        if not self.is_authorized():
            return None
        auth = {'Authorization': f'Bearer {self.token}'}
        boundary = '----TBBoundary'
        body = f'--{boundary}\r\nContent-Disposition: form-data; name="magnet"\r\n\r\n{magnet}\r\n--{boundary}--'.encode('utf-8')
        hdrs = {**auth, 'Content-Type': f'multipart/form-data; boundary={boundary}'}
        req = urllib.request.Request(f'{self.BASE_URL}/torrents/createtorrent', data=body, headers={**{'User-Agent': 'TraktPlayer/2.0'}, **hdrs}, method='POST')
        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
                res = json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                res = json.loads(e.read().decode('utf-8'))
            except:
                return None
        if not res.get('success'):
            return None
        tid = res.get('data', {}).get('torrent_id')
        if not tid:
            return None
        for _ in range(30):
            _, info = _http(f'{self.BASE_URL}/torrents/mylist?id={tid}', headers=auth)
            if info.get('success'):
                td = info.get('data', {})
                if td.get('download_state') in ('completed', 'cached', 'downloading'):
                    files = td.get('files', [])
                    if files:
                        biggest = max(files, key=lambda f: f.get('size', 0))
                        fid = biggest.get('id', 0)
                        _, dl = _http(f'{self.BASE_URL}/torrents/requestdl?token={self.token}&torrent_id={tid}&file_id={fid}', headers=auth)
                        if dl.get('success') and dl.get('data'):
                            return dl['data']
                    break
                elif td.get('download_state') in ('error', 'stalled'):
                    return None
            time.sleep(2)
        return None

    def revoke(self):
        ADDON.setSetting('tb_api_key', '')
        ADDON.setSetting('tb_auth_done', 'false')
        xbmcgui.Dialog().notification('TorBox', 'Unlinked', xbmcgui.NOTIFICATION_INFO)


def get_active_services():
    services = []
    for cls in (RealDebrid, AllDebrid, Premiumize, TorBox):
        svc = cls()
        if svc.is_authorized():
            services.append((cls.__name__, svc))
    return services


def resolve_magnet(magnet):
    services = get_active_services()
    for name, svc in services:
        try:
            url = svc.resolve_magnet(magnet)
            if url:
                xbmc.log(f'Resolved via {name}', xbmc.LOGINFO)
                return url, name
        except Exception as e:
            xbmc.log(f'{name} failed: {e}', xbmc.LOGERROR)
    return None, None
