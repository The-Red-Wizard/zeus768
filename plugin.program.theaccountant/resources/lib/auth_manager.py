"""
The Accountant - Debrid & Trakt Device Code Auth + Account Info
All auth uses on-screen codes for TV remote friendly operation.
"""
import xbmc, xbmcgui, xbmcaddon
import json, time

try:
    import requests
except ImportError:
    import urllib.request, urllib.parse
    # Minimal requests shim
    class _Response:
        def __init__(self, data, code):
            self._data = data
            self.status_code = code
        def json(self):
            return json.loads(self._data)
    class requests:
        @staticmethod
        def get(url, params=None, headers=None, timeout=10):
            if params:
                url += '?' + urllib.parse.urlencode(params)
            hdrs = headers or {}
            hdrs.setdefault('User-Agent', 'TheAccountant/4.0')
            req = urllib.request.Request(url, headers=hdrs)
            resp = urllib.request.urlopen(req, timeout=timeout)
            return _Response(resp.read().decode('utf-8'), resp.getcode())
        @staticmethod
        def post(url, data=None, json_data=None, headers=None, timeout=10):
            hdrs = headers or {}
            hdrs.setdefault('User-Agent', 'TheAccountant/4.0')
            if json_data:
                body = json.dumps(json_data).encode('utf-8')
                hdrs['Content-Type'] = 'application/json'
            elif data:
                body = urllib.parse.urlencode(data).encode('utf-8')
                hdrs.setdefault('Content-Type', 'application/x-www-form-urlencoded')
            else:
                body = None
            req = urllib.request.Request(url, data=body, headers=hdrs)
            resp = urllib.request.urlopen(req, timeout=timeout)
            return _Response(resp.read().decode('utf-8'), resp.getcode())

ADDON = xbmcaddon.Addon()

# Real-Debrid OAuth
RD_CLIENT_ID = 'X245A4XAIBGVM'
RD_DEVICE_URL = 'https://api.real-debrid.com/oauth/v2/device/code'
RD_TOKEN_URL = 'https://api.real-debrid.com/oauth/v2/token'
RD_CREDENTIALS_URL = 'https://api.real-debrid.com/oauth/v2/device/credentials'
RD_API = 'https://api.real-debrid.com/rest/1.0'

# Premiumize
PM_API = 'https://www.premiumize.me/api'

# AllDebrid
AD_API = 'https://api.alldebrid.com/v4'
AD_AGENT = 'TheAccountant'

# Trakt
TRAKT_API = 'https://api.trakt.tv'
TRAKT_CLIENT_ID = '2b8ee0fae20cb32fdb290c277e1e1b4d79a9c94b61fb0c2c6bcf1e2ead81a35f'
TRAKT_CLIENT_SECRET = '8b8aefa71a0e56caae7a3e6e76f9dde7aa1bc00363a410a4c75bbf9d10f54d07'


def auth_rd_device_code(vault, save_fn):
    """Real-Debrid device code auth - shows code on screen"""
    try:
        # Step 1: Get device code
        resp = requests.get(RD_DEVICE_URL, params={'client_id': RD_CLIENT_ID, 'new_credentials': 'yes'}, timeout=15)
        data = resp.json()

        device_code = data['device_code']
        user_code = data['user_code']
        verify_url = data.get('verification_url', 'https://real-debrid.com/device')
        interval = data.get('interval', 5)
        expires = data.get('expires_in', 120)

        dialog = xbmcgui.DialogProgress()
        dialog.create('Real-Debrid', f'Go to: {verify_url}\n\nEnter code: {user_code}\n\nWaiting...')

        # Step 2: Poll
        start = time.time()
        while time.time() - start < expires:
            if dialog.iscanceled():
                dialog.close()
                return False
            xbmc.sleep(interval * 1000)
            try:
                cred = requests.get(RD_CREDENTIALS_URL, params={'client_id': RD_CLIENT_ID, 'code': device_code}, timeout=10)
                cred_data = cred.json()
                if 'client_id' in cred_data and 'client_secret' in cred_data:
                    # Step 3: Get token
                    token_resp = requests.post(RD_TOKEN_URL, data={
                        'client_id': cred_data['client_id'],
                        'client_secret': cred_data['client_secret'],
                        'code': device_code,
                        'grant_type': 'http://oauth.net/grant_type/device/1.0'
                    }, timeout=15)
                    token_data = token_resp.json()
                    if 'access_token' in token_data:
                        vault['rd_token'] = token_data['access_token']
                        vault['rd_refresh'] = token_data.get('refresh_token', '')
                        vault['rd_client_id'] = cred_data['client_id']
                        vault['rd_client_secret'] = cred_data['client_secret']
                        vault['rd_expires'] = str(int(time.time()) + token_data.get('expires_in', 86400))
                        save_fn(vault)
                        dialog.close()
                        xbmcgui.Dialog().notification('The Accountant', 'Real-Debrid Authorized!', xbmcgui.NOTIFICATION_INFO, 3000)
                        return True
            except:
                pass

        dialog.close()
        xbmcgui.Dialog().notification('The Accountant', 'Authorization timed out', xbmcgui.NOTIFICATION_ERROR)
        return False
    except Exception as e:
        xbmc.log(f'[Accountant] RD auth error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('The Accountant', f'RD Error: {e}', xbmcgui.NOTIFICATION_ERROR)
        return False


def auth_pm_apikey(vault, save_fn):
    """Premiumize API key auth - user enters key from premiumize.me/account"""
    api_key = xbmcgui.Dialog().input('Enter Premiumize API Key\n(Get from premiumize.me/account)', type=xbmcgui.INPUT_ALPHANUM)
    if not api_key:
        return False
    try:
        resp = requests.get(f'{PM_API}/account/info', params={'apikey': api_key}, timeout=10)
        data = resp.json()
        if data.get('status') == 'success':
            vault['pm_token'] = api_key
            vault['pm_customer_id'] = str(data.get('customer_id', ''))
            save_fn(vault)
            xbmcgui.Dialog().notification('The Accountant', 'Premiumize Authorized!', xbmcgui.NOTIFICATION_INFO, 3000)
            return True
        else:
            xbmcgui.Dialog().ok('Failed', f"Invalid key: {data.get('message', 'Unknown error')}\n\nGet your API key from premiumize.me/account")
    except Exception as e:
        xbmcgui.Dialog().notification('The Accountant', f'PM Error: {e}', xbmcgui.NOTIFICATION_ERROR)
    return False


def auth_ad_pin(vault, save_fn):
    """AllDebrid PIN auth - shows code on screen"""
    try:
        resp = requests.get(f'{AD_API}/pin/get', params={'agent': AD_AGENT}, timeout=15)
        data = resp.json()
        pin_data = data.get('data', {})
        pin = pin_data.get('pin', '')
        check_url = pin_data.get('check_url', '')
        user_url = pin_data.get('user_url', 'https://alldebrid.com/pin/')
        expires = pin_data.get('expires_in', 600)

        dialog = xbmcgui.DialogProgress()
        dialog.create('AllDebrid', f'Go to: {user_url}\n\nEnter PIN: {pin}\n\nWaiting...')

        start = time.time()
        while time.time() - start < expires:
            if dialog.iscanceled():
                dialog.close()
                return False
            xbmc.sleep(5000)
            try:
                check = requests.get(check_url, params={'agent': AD_AGENT, 'pin': pin}, timeout=10)
                check_data = check.json().get('data', {})
                if check_data.get('activated'):
                    vault['ad_token'] = check_data.get('apikey', '')
                    save_fn(vault)
                    dialog.close()
                    xbmcgui.Dialog().notification('The Accountant', 'AllDebrid Authorized!', xbmcgui.NOTIFICATION_INFO, 3000)
                    return True
            except:
                pass

        dialog.close()
        xbmcgui.Dialog().notification('The Accountant', 'Authorization timed out', xbmcgui.NOTIFICATION_ERROR)
        return False
    except Exception as e:
        xbmc.log(f'[Accountant] AD auth error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('The Accountant', f'AD Error: {e}', xbmcgui.NOTIFICATION_ERROR)
        return False



def auth_tb_apikey(vault, save_fn):
    """TorBox API key auth"""
    api_key = xbmcgui.Dialog().input('Enter TorBox API Key\n(Get from torbox.app/settings)', type=xbmcgui.INPUT_ALPHANUM)
    if not api_key:
        return False
    try:
        resp = requests.get('https://api.torbox.app/v1/api/user/me', headers={'Authorization': f'Bearer {api_key}'}, timeout=10)
        data = resp.json()
        if data.get('success'):
            vault['tb_token'] = api_key
            save_fn(vault)
            xbmcgui.Dialog().notification('The Accountant', 'TorBox Authorized!', xbmcgui.NOTIFICATION_INFO, 3000)
            return True
        else:
            xbmcgui.Dialog().ok('Failed', f"Invalid key: {data.get('detail', 'Unknown error')}")
    except Exception as e:
        xbmcgui.Dialog().notification('The Accountant', f'TB Error: {e}', xbmcgui.NOTIFICATION_ERROR)
    return False


def auth_trakt_device(vault, save_fn):
    """Trakt device code auth - shows code on screen"""
    try:
        headers = {'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': TRAKT_CLIENT_ID}
        resp = requests.post(f'{TRAKT_API}/oauth/device/code', json_data={'client_id': TRAKT_CLIENT_ID}, headers=headers, timeout=15)
        data = resp.json()

        device_code = data['device_code']
        user_code = data['user_code']
        verify_url = data.get('verification_url', 'https://trakt.tv/activate')
        interval = data.get('interval', 5)
        expires = data.get('expires_in', 600)

        dialog = xbmcgui.DialogProgress()
        dialog.create('Trakt', f'Go to: {verify_url}\n\nEnter code: {user_code}\n\nWaiting...')

        start = time.time()
        while time.time() - start < expires:
            if dialog.iscanceled():
                dialog.close()
                return False
            xbmc.sleep(interval * 1000)
            try:
                token_resp = requests.post(f'{TRAKT_API}/oauth/device/token', json_data={
                    'code': device_code,
                    'client_id': TRAKT_CLIENT_ID,
                    'client_secret': TRAKT_CLIENT_SECRET
                }, headers=headers, timeout=15)
                if token_resp.status_code == 200:
                    token_data = token_resp.json()
                    vault['trakt_token'] = token_data.get('access_token', '')
                    vault['trakt_refresh'] = token_data.get('refresh_token', '')
                    vault['trakt_expires'] = str(int(time.time()) + token_data.get('expires_in', 7776000))
                    vault['trakt_client_id'] = TRAKT_CLIENT_ID
                    vault['trakt_client_secret'] = TRAKT_CLIENT_SECRET
                    save_fn(vault)
                    dialog.close()
                    xbmcgui.Dialog().notification('The Accountant', 'Trakt Authorized!', xbmcgui.NOTIFICATION_INFO, 3000)
                    return True
            except:
                pass

        dialog.close()
        xbmcgui.Dialog().notification('The Accountant', 'Authorization timed out', xbmcgui.NOTIFICATION_ERROR)
        return False
    except Exception as e:
        xbmc.log(f'[Accountant] Trakt auth error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('The Accountant', f'Trakt Error: {e}', xbmcgui.NOTIFICATION_ERROR)
        return False


def get_rd_account_info(token):
    """Fetch Real-Debrid account details"""
    try:
        resp = requests.get(f'{RD_API}/user', headers={'Authorization': f'Bearer {token}'}, timeout=10)
        data = resp.json()
        expiry = data.get('expiration', '')
        days_left = 0
        if expiry:
            from datetime import datetime
            try:
                exp_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                days_left = (exp_dt - datetime.now(exp_dt.tzinfo)).days
            except:
                pass
        return {
            'username': data.get('username', 'Unknown'),
            'email': data.get('email', 'Unknown'),
            'type': data.get('type', 'free'),
            'expiration': expiry[:10] if expiry else 'N/A',
            'days_left': days_left,
            'fidelity': data.get('points', 0),
            'status': 'Premium' if data.get('type') == 'premium' else 'Free'
        }
    except:
        return None


def get_pm_account_info(token):
    """Fetch Premiumize account details"""
    try:
        resp = requests.get(f'{PM_API}/account/info', params={'apikey': token}, timeout=10)
        data = resp.json()
        if data.get('status') != 'success':
            return None
        exp_ts = data.get('premium_until', 0)
        days_left = max(0, int((exp_ts - time.time()) / 86400)) if exp_ts else 0
        return {
            'customer_id': str(data.get('customer_id', 'Unknown')),
            'status': 'Premium' if data.get('premium_until', 0) > time.time() else 'Free',
            'expiration': time.strftime('%Y-%m-%d', time.localtime(exp_ts)) if exp_ts else 'N/A',
            'days_left': days_left,
            'space_used': f"{data.get('space_used', 0) / (1024**3):.1f} GB",
            'limit_used': data.get('limit_used', 0)
        }
    except:
        return None


def get_ad_account_info(token):
    """Fetch AllDebrid account details"""
    try:
        resp = requests.get(f'{AD_API}/user', params={'agent': AD_AGENT, 'apikey': token}, timeout=10)
        data = resp.json().get('data', {}).get('user', {})
        exp_ts = data.get('premiumUntil', 0)
        days_left = max(0, int((exp_ts - time.time()) / 86400)) if exp_ts else 0
        return {
            'username': data.get('username', 'Unknown'),
            'email': data.get('email', 'Unknown'),
            'status': 'Premium' if data.get('isPremium') else 'Free',
            'expiration': time.strftime('%Y-%m-%d', time.localtime(exp_ts)) if exp_ts else 'N/A',
            'days_left': days_left,
            'fidelity': data.get('fidelityPoints', 0)
        }
    except:
        return None


def get_trakt_account_info(token):
    """Fetch Trakt account and stats"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': TRAKT_CLIENT_ID,
            'Authorization': f'Bearer {token}'
        }
        # User settings
        user_resp = requests.get(f'{TRAKT_API}/users/settings', headers=headers, timeout=10)
        user = user_resp.json()
        username = user.get('user', {}).get('username', 'Unknown')
        vip = user.get('user', {}).get('vip', False)
        joined = user.get('user', {}).get('joined_at', '')[:10]

        # User stats
        try:
            stats_resp = requests.get(f'{TRAKT_API}/users/{username}/stats', headers=headers, timeout=10)
            stats = stats_resp.json()
            movies_watched = stats.get('movies', {}).get('watched', 0)
            shows_watched = stats.get('shows', {}).get('watched', 0)
            episodes_watched = stats.get('episodes', {}).get('watched', 0)
            ratings = stats.get('ratings', {}).get('total', 0)
        except:
            movies_watched = shows_watched = episodes_watched = ratings = 0

        return {
            'username': username,
            'vip': 'VIP' if vip else 'Standard',
            'joined': joined,
            'movies_watched': movies_watched,
            'shows_watched': shows_watched,
            'episodes_watched': episodes_watched,
            'ratings': ratings
        }
    except:
        return None


# Addon sync mappings - comprehensive list of known Kodi addons
ADDON_SYNC_MAP = {
    # ===== ZEUS768 REPO ADDONS =====
    'plugin.video.genesis': {
        'rd': [('rd_access_token', 'rd_token'), ('rd_refresh_token', 'rd_refresh')],
        'pm': [('pm_access_token', 'pm_token')],
        'ad': [('ad_api_key', 'ad_token')],
        'tb': [('tb_api_key', 'tb_token')],
        'trakt': [('trakt_access_token', 'trakt_token'), ('trakt_refresh_token', 'trakt_refresh'), ('trakt_expires', 'trakt_expires')]
    },
    'plugin.video.orion': {
        'rd': [('rd_token', 'rd_token'), ('rd_refresh', 'rd_refresh')],
        'pm': [('pm_token', 'pm_token')],
        'ad': [('ad_token', 'ad_token')],
        'tb': [('tb_token', 'tb_token')],
        'trakt': [('trakt_token', 'trakt_token'), ('trakt_refresh', 'trakt_refresh')]
    },
    'plugin.video.salts': {
        'rd': [('realdebrid_token', 'rd_token'), ('realdebrid_refresh', 'rd_refresh'),
               ('realdebrid_client_id', 'rd_client_id'), ('realdebrid_client_secret', 'rd_client_secret'),
               ('realdebrid_expires', 'rd_expires')],
        'pm': [('premiumize_token', 'pm_token')],
        'ad': [('alldebrid_token', 'ad_token')],
        'tb': [('torbox_token', 'tb_token')],
        'trakt': [('trakt_access_token', 'trakt_token'), ('trakt_refresh_token', 'trakt_refresh')]
    },
    'plugin.video.tinklepad': {
        'rd': [('rd.token', 'rd_token'), ('rd.refresh', 'rd_refresh'),
               ('rd.client_id', 'rd_client_id'), ('rd.secret', 'rd_client_secret')],
        'pm': [('pm.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')]
    },
    'plugin.video.trakt_player': {
        'rd': [('rd_access_token', 'rd_token'), ('rd_refresh_token', 'rd_refresh'),
               ('rd_client_id', 'rd_client_id'), ('rd_client_secret', 'rd_client_secret'),
               ('rd_expires', 'rd_expires')],
        'pm': [('pm_access_token', 'pm_token')],
        'ad': [('ad_api_key', 'ad_token')],
        'tb': [('tb_api_key', 'tb_token')],
        'trakt': [('trakt_access_token', 'trakt_token'), ('trakt_refresh_token', 'trakt_refresh'),
                  ('trakt_expires', 'trakt_expires')]
    },
    'plugin.video.syncher': {
        'rd': [('realdebrid.token', 'rd_token')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.poseidonplayer': {
        'rd': [('rd_token', 'rd_token')],
        'trakt': [('trakt_token', 'trakt_token')]
    },
    # ===== POPULAR THIRD-PARTY ADDONS =====
    'plugin.video.umbrella': {
        'rd': [('realdebrid.token', 'rd_token'), ('realdebrid.client_id', 'rd_client_id'),
               ('realdebrid.secret', 'rd_client_secret'), ('realdebrid.refresh', 'rd_refresh')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.fen': {
        'rd': [('rd.token', 'rd_token'), ('rd.client_id', 'rd_client_id'),
               ('rd.secret', 'rd_client_secret'), ('rd.refresh', 'rd_refresh')],
        'pm': [('pm.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.fenlight': {
        'rd': [('rd.token', 'rd_token'), ('rd.client_id', 'rd_client_id'),
               ('rd.secret', 'rd_client_secret'), ('rd.refresh', 'rd_refresh')],
        'pm': [('pm.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.fenlightam': {
        'rd': [('rd.token', 'rd_token'), ('rd.client_id', 'rd_client_id'),
               ('rd.secret', 'rd_client_secret'), ('rd.refresh', 'rd_refresh')],
        'pm': [('pm.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.seren': {
        'rd': [('rd.auth', 'rd_token'), ('rd.client_id', 'rd_client_id'),
               ('rd.secret', 'rd_client_secret'), ('rd.refresh', 'rd_refresh')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.apikey', 'ad_token')],
        'trakt': [('trakt.auth', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.thechain': {
        'rd': [('rd.token', 'rd_token'), ('realdebrid.token', 'rd_token')],
        'pm': [('pm.token', 'pm_token'), ('premiumize.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token')]
    },
    'plugin.video.thechains': {
        'rd': [('rd.token', 'rd_token'), ('realdebrid.token', 'rd_token')],
        'pm': [('pm.token', 'pm_token'), ('premiumize.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token')]
    },
    'plugin.video.thecrew': {
        'rd': [('rd.auth', 'rd_token'), ('realdebrid.token', 'rd_token')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token')]
    },
    'plugin.video.ezra': {
        'rd': [('rd.token', 'rd_token')],
        'pm': [('pm.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')]
    },
    'plugin.video.coalition': {
        'rd': [('realdebrid.token', 'rd_token')],
        'pm': [('premiumize.token', 'pm_token')]
    },
    'plugin.video.themoviedb.helper': {
        'tmdb': [('tmdb_api_key', 'tmdb_api_key')]
    },
    # ===== RESOLVEURL (Critical for all addons) =====
    'script.module.resolveurl': {
        'rd': [('RealDebridResolver_token', 'rd_token'), ('RealDebridResolver_client_id', 'rd_client_id'),
               ('RealDebridResolver_client_secret', 'rd_client_secret'), ('RealDebridResolver_refresh', 'rd_refresh')],
        'pm': [('PremiumizeMeResolver_token', 'pm_token')],
        'ad': [('AlldebridResolver_token', 'ad_token')]
    },
}


def sync_to_all_addons(vault):
    """Sync vault credentials to all detected addons"""
    dialog = xbmcgui.DialogProgress()
    dialog.create('The Accountant', 'Detecting installed addons...')

    synced = []
    not_installed = []
    total = len(ADDON_SYNC_MAP)

    for i, (addon_id, mapping) in enumerate(ADDON_SYNC_MAP.items()):
        dialog.update(int((i / total) * 100), f'Syncing {addon_id}...')
        try:
            target = xbmcaddon.Addon(addon_id)
            addon_synced = False
            for service, settings_list in mapping.items():
                for setting_key, vault_key in settings_list:
                    value = vault.get(vault_key, '')
                    if value:
                        target.setSetting(setting_key, value)
                        addon_synced = True
            if addon_synced:
                synced.append(addon_id.split('.')[-1])
        except:
            not_installed.append(addon_id.split('.')[-1])

    dialog.close()

    msg = ''
    if synced:
        msg += f'Synced to: {", ".join(synced)}\n\n'
    if not_installed:
        msg += f'Not installed: {", ".join(not_installed[:10])}'
    xbmcgui.Dialog().ok('Sync Complete', msg or 'No addons found')
    return synced
