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

# Trakt API - Using SALTS (zeus768) verified credentials - device pairing flow
TRAKT_API = 'https://api.trakt.tv'
# These are the same credentials used by plugin.video.salts (zeus768 repo) and
# are registered as a Trakt API application. They are required because Trakt
# rejects unknown client_ids with HTTP 403 on /oauth/device/code.
TRAKT_CLIENT_ID = '42eba69a18795ae48fc5d6dbdd99396e9e3894dc4f18930e6187d36c8b4346d3'
TRAKT_CLIENT_SECRET = 'e5bc7e20660e73622344ebf93c250a8fc2814a8f7c2b082bdee51545d5f71969'
TRAKT_USER_AGENT = 'SALTS Kodi Addon/2.5.2'


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


def _trakt_request(url, payload, timeout=15):
    """Low-level Trakt POST using raw urllib (salts-style).
    Returns (status_code, parsed_json_or_None, raw_body).
    """
    import urllib.request as _u, urllib.error as _ue
    headers = {
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': TRAKT_CLIENT_ID,
        'User-Agent': TRAKT_USER_AGENT,
    }
    body = json.dumps(payload).encode('utf-8')
    req = _u.Request(url, data=body, headers=headers, method='POST')
    try:
        resp = _u.urlopen(req, timeout=timeout)
        raw = resp.read().decode('utf-8')
        try:
            return resp.getcode(), json.loads(raw), raw
        except Exception:
            return resp.getcode(), None, raw
    except _ue.HTTPError as e:
        raw = ''
        try:
            raw = e.read().decode('utf-8')
        except Exception:
            pass
        return e.code, None, raw
    except Exception as e:
        xbmc.log(f'[Accountant] Trakt urllib error: {e}', xbmc.LOGERROR)
        return 0, None, str(e)


def auth_trakt_device(vault, save_fn):
    """Trakt device code auth - salts-style pairing (fixes 403 on /oauth/device/code)"""
    try:
        # Step 1: Get device code (salts-style)
        status, data, raw = _trakt_request(
            f'{TRAKT_API}/oauth/device/code',
            {'client_id': TRAKT_CLIENT_ID}
        )

        if status != 200 or not data:
            xbmcgui.Dialog().ok(
                'Trakt Error',
                f'Failed to get device code (HTTP {status}).\n\n'
                f'{raw[:200] if raw else ""}\n\nPlease try again later.'
            )
            return False
        device_code = data['device_code']
        user_code = data['user_code']
        verify_url = data.get('verification_url', 'https://trakt.tv/activate')
        interval = data.get('interval', 5)
        expires = data.get('expires_in', 600)

        pDialog = xbmcgui.DialogProgress()
        pDialog.create('Trakt Authorization', 
                      f'Visit: [COLOR cyan]{verify_url}[/COLOR]\n\n'
                      f'Enter code: [COLOR yellow][B]{user_code}[/B][/COLOR]\n\n'
                      f'Waiting for authorization...')

        start = time.time()
        while time.time() - start < expires:
            if pDialog.iscanceled():
                pDialog.close()
                return False
            
            elapsed = int(time.time() - start)
            remaining = expires - elapsed
            progress = int((elapsed / expires) * 100)
            
            pDialog.update(progress, 
                          f'Visit: [COLOR cyan]{verify_url}[/COLOR]\n\n'
                          f'Enter code: [COLOR yellow][B]{user_code}[/B][/COLOR]\n\n'
                          f'Waiting... ({remaining}s remaining)')
            
            xbmc.sleep(interval * 1000)
            
            try:
                token_status, token_data, _ = _trakt_request(
                    f'{TRAKT_API}/oauth/device/token',
                    {
                        'code': device_code,
                        'client_id': TRAKT_CLIENT_ID,
                        'client_secret': TRAKT_CLIENT_SECRET,
                    }
                )

                if token_status == 200 and token_data:
                    vault['trakt_token'] = token_data.get('access_token', '')
                    vault['trakt_refresh'] = token_data.get('refresh_token', '')
                    vault['trakt_expires'] = str(int(time.time()) + token_data.get('expires_in', 7776000))
                    vault['trakt_client_id'] = TRAKT_CLIENT_ID
                    vault['trakt_client_secret'] = TRAKT_CLIENT_SECRET
                    save_fn(vault)
                    pDialog.close()
                    xbmcgui.Dialog().notification('The Accountant', 'Trakt Authorized!', xbmcgui.NOTIFICATION_INFO, 3000)
                    return True
                elif token_status == 400:
                    # Pending - user hasn't authorized yet, continue polling
                    pass
                elif token_status == 404:
                    pDialog.close()
                    xbmcgui.Dialog().ok('Trakt Error', 'Invalid device code. Please try again.')
                    return False
                elif token_status == 409:
                    pDialog.close()
                    xbmcgui.Dialog().ok('Trakt Error', 'Code already used. Please try again.')
                    return False
                elif token_status == 410:
                    pDialog.close()
                    xbmcgui.Dialog().ok('Trakt Error', 'Code expired. Please try again.')
                    return False
                elif token_status == 418:
                    pDialog.close()
                    xbmcgui.Dialog().ok('Trakt Error', 'You denied the authorization request.')
                    return False
                elif token_status == 429:
                    # Rate limited - wait extra time
                    xbmc.sleep(interval * 1000)
            except Exception as poll_err:
                xbmc.log(f'[Accountant] Trakt poll: {poll_err}', xbmc.LOGDEBUG)

        pDialog.close()
        xbmcgui.Dialog().ok('Trakt', 'Authorization timed out.\nPlease try again.')
        return False
        
    except Exception as e:
        xbmc.log(f'[Accountant] Trakt auth error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Trakt Error', f'Connection failed:\n{str(e)}')
        return False


def refresh_trakt_token(vault, save_fn):
    """Silent refresh of Trakt access token using stored refresh_token (salts-style).
    Returns True on success, False otherwise.
    """
    refresh = vault.get('trakt_refresh', '')
    if not refresh:
        return False
    try:
        status, data, raw = _trakt_request(
            f'{TRAKT_API}/oauth/token',
            {
                'refresh_token': refresh,
                'client_id': TRAKT_CLIENT_ID,
                'client_secret': TRAKT_CLIENT_SECRET,
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'grant_type': 'refresh_token',
            }
        )
        if status == 200 and data and data.get('access_token'):
            vault['trakt_token'] = data['access_token']
            vault['trakt_refresh'] = data.get('refresh_token', refresh)
            vault['trakt_expires'] = str(int(time.time()) + data.get('expires_in', 7776000))
            vault['trakt_client_id'] = TRAKT_CLIENT_ID
            vault['trakt_client_secret'] = TRAKT_CLIENT_SECRET
            save_fn(vault)
            xbmc.log(f'[Accountant] Trakt token refreshed (expires in {data.get("expires_in", 0)}s)', xbmc.LOGINFO)
            return True
        xbmc.log(f'[Accountant] Trakt refresh failed HTTP {status}: {raw[:200] if raw else ""}', xbmc.LOGWARNING)
    except Exception as e:
        xbmc.log(f'[Accountant] Trakt refresh error: {e}', xbmc.LOGERROR)
    return False


def check_trakt_expiry(vault, save_fn, warn_days=7, autoclose_ms=15000):
    """Check Trakt token expiry.
    - Within `warn_days` of expiry -> attempt silent refresh.
    - If refresh fails (or token already expired with no refresh) -> show a
      yes/no countdown dialog letting the user Re-pair now or Ignore.
    Returns one of: 'ok', 'refreshed', 'repaired', 'ignored', 'expired_no_action', 'not_configured'.
    """
    if not vault.get('trakt_token'):
        return 'not_configured'

    try:
        expires_ts = int(float(vault.get('trakt_expires', 0) or 0))
    except Exception:
        expires_ts = 0

    now = int(time.time())
    seconds_left = expires_ts - now
    warn_window = warn_days * 86400

    # Plenty of time left
    if expires_ts and seconds_left > warn_window:
        return 'ok'

    # Try silent refresh first
    if refresh_trakt_token(vault, save_fn):
        return 'refreshed'

    # Refresh failed (or no refresh token). Prompt the user with countdown.
    days_left = max(0, seconds_left // 86400)
    if seconds_left <= 0:
        headline = 'Your Trakt authorization has expired.'
    else:
        headline = f'Trakt authorization expires in {days_left} day{"s" if days_left != 1 else ""}.'

    message = (
        f'{headline}\n\n'
        'Automatic refresh failed.\n'
        'Re-pair now, or ignore this reminder.'
    )

    try:
        choice = xbmcgui.Dialog().yesno(
            'The Accountant - Trakt',
            message,
            yeslabel='Re-pair now',
            nolabel='Ignore',
            autoclose=autoclose_ms
        )
    except Exception:
        choice = False

    if choice:
        ok = auth_trakt_device(vault, save_fn)
        return 'repaired' if ok else 'expired_no_action'
    return 'ignored' if seconds_left > 0 else 'expired_no_action'


def _is_addon_installed(addon_id):
    """Safely check if a Kodi addon is installed WITHOUT triggering any
    install / dependency-resolution prompt from Kodi. Using
    xbmcaddon.Addon(id) on an uninstalled id can, on Kodi 20/21 (Omega),
    pop the 'Install addon?' dialog before raising. System.HasAddon is
    a pure visibility check with no side effects.
    """
    try:
        return bool(xbmc.getCondVisibility('System.HasAddon(%s)' % addon_id))
    except Exception:
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
    """Fetch Trakt account and stats (extended: collection, watchlist, lists)."""
    try:
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': TRAKT_CLIENT_ID,
            'User-Agent': TRAKT_USER_AGENT,
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
            # Stats endpoint already returns collected counts - use them if present
            collected_movies = stats.get('movies', {}).get('collected', 0)
            collected_shows = stats.get('shows', {}).get('collected', 0)
            # Total watch time in minutes (movies + episodes)
            total_minutes = (stats.get('movies', {}).get('minutes', 0) +
                             stats.get('episodes', {}).get('minutes', 0))
        except:
            movies_watched = shows_watched = episodes_watched = ratings = 0
            collected_movies = collected_shows = 0
            total_minutes = 0

        # Watchlist counts
        try:
            wl_m = requests.get(f'{TRAKT_API}/sync/watchlist/movies', headers=headers, timeout=10).json()
            watchlist_movies = len(wl_m) if isinstance(wl_m, list) else 0
        except:
            watchlist_movies = 0
        try:
            wl_s = requests.get(f'{TRAKT_API}/sync/watchlist/shows', headers=headers, timeout=10).json()
            watchlist_shows = len(wl_s) if isinstance(wl_s, list) else 0
        except:
            watchlist_shows = 0

        # Personal lists count
        try:
            lists_resp = requests.get(f'{TRAKT_API}/users/{username}/lists', headers=headers, timeout=10).json()
            lists_count = len(lists_resp) if isinstance(lists_resp, list) else 0
        except:
            lists_count = 0

        # Top genre (tally over watched shows with extended metadata, weighted by play count)
        top_genre = ''
        try:
            ws_resp = requests.get(f'{TRAKT_API}/users/{username}/watched/shows',
                                   params={'extended': 'full'}, headers=headers, timeout=15)
            watched_shows = ws_resp.json() if ws_resp.status_code == 200 else []
            counts = {}
            if isinstance(watched_shows, list):
                for entry in watched_shows:
                    show = entry.get('show', {}) or {}
                    plays = entry.get('plays', 1) or 1
                    for g in (show.get('genres') or []):
                        if not g:
                            continue
                        counts[g] = counts.get(g, 0) + plays
            if counts:
                top = max(counts.items(), key=lambda kv: kv[1])
                top_genre = top[0].title()
        except:
            top_genre = ''

        return {
            'username': username,
            'vip': 'VIP' if vip else 'Standard',
            'joined': joined,
            'movies_watched': movies_watched,
            'shows_watched': shows_watched,
            'episodes_watched': episodes_watched,
            'ratings': ratings,
            'collected_movies': collected_movies,
            'collected_shows': collected_shows,
            'watchlist_movies': watchlist_movies,
            'watchlist_shows': watchlist_shows,
            'lists_count': lists_count,
            'total_minutes': total_minutes,
            'top_genre': top_genre
        }
    except:
        return None


def get_tmdb_info(api_key):
    """Validate a TMDB v3 API key and return light metadata.
    TMDB v3 doesn't expose per-user stats without a session id, so we just
    confirm the key works against /configuration and report change-date
    coverage as a sanity check."""
    try:
        resp = requests.get('https://api.themoviedb.org/3/configuration',
                            params={'api_key': api_key}, timeout=10)
        data = resp.json()
        if 'images' not in data:
            return {'valid': False, 'status': 'Invalid Key'}
        # Pull a small change window to show the key is live
        try:
            changes = requests.get('https://api.themoviedb.org/3/movie/changes',
                                   params={'api_key': api_key, 'page': 1},
                                   timeout=10).json()
            tracked = changes.get('total_results', 0)
        except:
            tracked = 0
        return {
            'valid': True,
            'status': 'API Key Valid',
            'api_version': 'v3',
            'tracked_changes': tracked
        }
    except:
        return {'valid': False, 'status': 'Validation Failed'}


# Addon sync mappings - comprehensive list of known Kodi addons
ADDON_SYNC_MAP = {
    # ===== TWISTED NUTZ REPO ADDONS =====
    'plugin.video.twisted': {
        'name': 'Twisted',
        'rd': [('rd.auth', 'rd_token'), ('rd.refresh', 'rd_refresh'),
               ('rd.client_id', 'rd_client_id'), ('rd.secret', 'rd_client_secret'),
               ('rd.expiry', 'rd_expires')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.token', 'ad_token')],
        'trakt': [('trakt_access_token', 'trakt_token'), ('trakt_refresh_token', 'trakt_refresh'),
                  ('trakt_expires_at', 'trakt_expires')]
    },
    'plugin.video.blueballs': {
        'name': 'Blueballs',
        'rd': [('rd.auth', 'rd_token'), ('rd.refresh', 'rd_refresh'),
               ('rd.client_id', 'rd_client_id'), ('rd.secret', 'rd_client_secret'),
               ('rd.expiry', 'rd_expires')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.token', 'ad_token')],
        'trakt': [('trakt_access_token', 'trakt_token'), ('trakt_refresh_token', 'trakt_refresh'),
                  ('trakt_expires_at', 'trakt_expires')]
    },
    'plugin.video.twistedtv': {
        'name': 'Twisted 247 TV',
        'rd': [('rd.auth', 'rd_token'), ('rd.refresh', 'rd_refresh'),
               ('rd.client_id', 'rd_client_id'), ('rd.secret', 'rd_client_secret')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.token', 'ad_token')]
    },
    # ===== ZEUS768 REPO ADDONS =====
    'plugin.video.genesis': {
        'name': 'Genesis',
        'rd': [('rd_access_token', 'rd_token'), ('rd_refresh_token', 'rd_refresh')],
        'pm': [('pm_access_token', 'pm_token')],
        'ad': [('ad_api_key', 'ad_token')],
        'tb': [('tb_api_key', 'tb_token')],
        'trakt': [('trakt_access_token', 'trakt_token'), ('trakt_refresh_token', 'trakt_refresh'), ('trakt_expires', 'trakt_expires')]
    },
    'plugin.video.orion': {
        'name': 'Orion',
        'rd': [('rd_token', 'rd_token'), ('rd_refresh', 'rd_refresh')],
        'pm': [('pm_token', 'pm_token')],
        'ad': [('ad_token', 'ad_token')],
        'tb': [('tb_token', 'tb_token')],
        'trakt': [('trakt_token', 'trakt_token'), ('trakt_refresh', 'trakt_refresh')]
    },
    'plugin.video.salts': {
        'name': 'SALTS',
        'rd': [('realdebrid_token', 'rd_token'), ('realdebrid_refresh', 'rd_refresh'),
               ('realdebrid_client_id', 'rd_client_id'), ('realdebrid_client_secret', 'rd_client_secret'),
               ('realdebrid_expires', 'rd_expires')],
        'pm': [('premiumize_token', 'pm_token')],
        'ad': [('alldebrid_token', 'ad_token')],
        'tb': [('torbox_token', 'tb_token')],
        'trakt': [('trakt_access_token', 'trakt_token'), ('trakt_refresh_token', 'trakt_refresh')]
    },
    'plugin.video.tinklepad': {
        'name': 'Tinklepad',
        'rd': [('rd.token', 'rd_token'), ('rd.refresh', 'rd_refresh'),
               ('rd.client_id', 'rd_client_id'), ('rd.secret', 'rd_client_secret')],
        'pm': [('pm.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')]
    },
    'plugin.video.trakt_player': {
        'name': 'Trakt Player',
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
        'name': 'Syncher',
        'rd': [('realdebrid.token', 'rd_token')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.poseidonplayer': {
        'name': 'Poseidon Player',
        'rd': [('rd_token', 'rd_token')],
        'trakt': [('trakt_token', 'trakt_token')]
    },
    # ===== POPULAR THIRD-PARTY ADDONS =====
    'plugin.video.umbrella': {
        'name': 'Umbrella',
        'rd': [('realdebrid.token', 'rd_token'), ('realdebrid.client_id', 'rd_client_id'),
               ('realdebrid.secret', 'rd_client_secret'), ('realdebrid.refresh', 'rd_refresh')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.fen': {
        'name': 'Fen',
        'rd': [('rd.token', 'rd_token'), ('rd.client_id', 'rd_client_id'),
               ('rd.secret', 'rd_client_secret'), ('rd.refresh', 'rd_refresh')],
        'pm': [('pm.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.fenlight': {
        'name': 'FenLight',
        'rd': [('rd.token', 'rd_token'), ('rd.client_id', 'rd_client_id'),
               ('rd.secret', 'rd_client_secret'), ('rd.refresh', 'rd_refresh')],
        'pm': [('pm.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.fenlightam': {
        'name': 'FenLight AM',
        'rd': [('rd.token', 'rd_token'), ('rd.client_id', 'rd_client_id'),
               ('rd.secret', 'rd_client_secret'), ('rd.refresh', 'rd_refresh')],
        'pm': [('pm.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.seren': {
        'name': 'Seren',
        'rd': [('rd.auth', 'rd_token'), ('rd.client_id', 'rd_client_id'),
               ('rd.secret', 'rd_client_secret'), ('rd.refresh', 'rd_refresh')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.apikey', 'ad_token')],
        'trakt': [('trakt.auth', 'trakt_token'), ('trakt.refresh', 'trakt_refresh')]
    },
    'plugin.video.thechain': {
        'name': 'The Chain',
        'rd': [('rd.token', 'rd_token'), ('realdebrid.token', 'rd_token')],
        'pm': [('pm.token', 'pm_token'), ('premiumize.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token')]
    },
    'plugin.video.thechains': {
        'name': 'The Chains',
        'rd': [('rd.token', 'rd_token'), ('realdebrid.token', 'rd_token')],
        'pm': [('pm.token', 'pm_token'), ('premiumize.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token')]
    },
    'plugin.video.gears': {
        'name': 'The Gears',
        'rd': [('gears.rd.token', 'rd_token'), ('gears.rd.refresh', 'rd_refresh'),
               ('gears.rd.client_id', 'rd_client_id'), ('gears.rd.secret', 'rd_client_secret')],
        'pm': [('gears.pm.token', 'pm_token')],
        'ad': [('gears.ad.token', 'ad_token')],
        'tb': [('gears.tb.token', 'tb_token')],
        'trakt': [('gears.trakt.token', 'trakt_token'), ('gears.trakt.refresh', 'trakt_refresh'),
                  ('gears.trakt.expires', 'trakt_expires')]
    },
    'plugin.video.thecrew': {
        'name': 'The Crew',
        'rd': [('rd.auth', 'rd_token'), ('realdebrid.token', 'rd_token')],
        'pm': [('premiumize.token', 'pm_token')],
        'ad': [('alldebrid.token', 'ad_token')],
        'trakt': [('trakt.token', 'trakt_token')]
    },
    'plugin.video.ezra': {
        'name': 'Ezra',
        'rd': [('rd.token', 'rd_token')],
        'pm': [('pm.token', 'pm_token')],
        'ad': [('ad.token', 'ad_token')]
    },
    'plugin.video.coalition': {
        'name': 'Coalition',
        'rd': [('realdebrid.token', 'rd_token')],
        'pm': [('premiumize.token', 'pm_token')]
    },
    'plugin.video.themoviedb.helper': {
        'name': 'TMDB Helper',
        'tmdb': [('tmdb_api_key', 'tmdb_api_key')]
    },
    # ===== RESOLVEURL (Critical for all addons) =====
    'script.module.resolveurl': {
        'name': 'ResolveURL',
        'rd': [('RealDebridResolver_token', 'rd_token'), ('RealDebridResolver_client_id', 'rd_client_id'),
               ('RealDebridResolver_client_secret', 'rd_client_secret'), ('RealDebridResolver_refresh', 'rd_refresh')],
        'pm': [('PremiumizeMeResolver_token', 'pm_token')],
        'ad': [('AlldebridResolver_token', 'ad_token')]
    },
}

# Settings key for storing addon sync preferences
SYNC_PREFS_KEY = 'addon_sync_prefs'


def get_installed_addons_for_service(service_type):
    """Get list of installed addons that support a specific service type (rd, pm, ad, tb, trakt, tmdb)"""
    installed = []
    for addon_id, mapping in ADDON_SYNC_MAP.items():
        if service_type in mapping:
            # Pre-check with System.HasAddon so Kodi never prompts to
            # install addons that aren't already on the device.
            if not _is_addon_installed(addon_id):
                continue
            try:
                xbmcaddon.Addon(addon_id)
                installed.append({
                    'id': addon_id,
                    'name': mapping.get('name', addon_id.split('.')[-1].title())
                })
            except Exception:
                pass  # Not installed / unavailable - skip silently
    return installed


def load_sync_preferences(vault):
    """Load saved sync preferences from vault"""
    return vault.get(SYNC_PREFS_KEY, {})


def save_sync_preferences(vault, prefs, save_fn):
    """Save sync preferences to vault"""
    vault[SYNC_PREFS_KEY] = prefs
    save_fn(vault)


def select_addons_for_sync(vault, save_fn, service_type, service_name):
    """Show dialog to select which addons to sync for a service
    Returns list of selected addon IDs, or None if cancelled
    """
    installed = get_installed_addons_for_service(service_type)
    
    if not installed:
        xbmcgui.Dialog().ok('No Addons Found', 
                           f'No installed addons support {service_name}.\n\n'
                           'Install compatible addons first.')
        return None
    
    # Load existing preferences
    prefs = load_sync_preferences(vault)
    service_prefs = prefs.get(service_type, {})
    
    # Build list with checkboxes
    addon_names = [addon['name'] for addon in installed]
    addon_ids = [addon['id'] for addon in installed]
    
    # Determine which are pre-selected (default: all enabled)
    preselect = []
    for i, addon_id in enumerate(addon_ids):
        # Default to enabled if no preference saved, or if explicitly enabled
        if service_prefs.get(addon_id, True):
            preselect.append(i)
    
    # Show multiselect dialog
    dialog = xbmcgui.Dialog()
    selected_indices = dialog.multiselect(
        f'Select addons to sync {service_name}',
        addon_names,
        preselect=preselect
    )
    
    if selected_indices is None:
        return None  # User cancelled
    
    # Update preferences
    selected_addon_ids = []
    for i, addon_id in enumerate(addon_ids):
        enabled = i in selected_indices
        service_prefs[addon_id] = enabled
        if enabled:
            selected_addon_ids.append(addon_id)
    
    prefs[service_type] = service_prefs
    save_sync_preferences(vault, prefs, save_fn)
    
    return selected_addon_ids


def sync_service_to_selected_addons(vault, save_fn, service_type, service_name):
    """Sync a specific service to user-selected addons"""
    # Let user select addons
    selected_addons = select_addons_for_sync(vault, save_fn, service_type, service_name)
    
    if selected_addons is None:
        return []  # Cancelled
    
    if not selected_addons:
        xbmcgui.Dialog().notification('The Accountant', 'No addons selected', 
                                      xbmcgui.NOTIFICATION_INFO, 2000)
        return []
    
    # Sync to selected addons
    synced = []
    for addon_id in selected_addons:
        mapping = ADDON_SYNC_MAP.get(addon_id, {})
        if service_type not in mapping:
            continue
        # Skip silently if addon is no longer installed - don't let Kodi
        # trigger an install prompt.
        if not _is_addon_installed(addon_id):
            continue
        try:
            target = xbmcaddon.Addon(addon_id)
            for setting_key, vault_key in mapping[service_type]:
                value = vault.get(vault_key, '')
                if value:
                    target.setSetting(setting_key, value)
            synced.append(mapping.get('name', addon_id.split('.')[-1]))
        except Exception as e:
            xbmc.log(f'[Accountant] Sync error for {addon_id}: {e}', xbmc.LOGWARNING)
    
    if synced:
        xbmcgui.Dialog().notification('The Accountant', 
                                      f'Synced to: {", ".join(synced[:3])}{"..." if len(synced) > 3 else ""}',
                                      xbmcgui.NOTIFICATION_INFO, 3000)
    
    return synced


def sync_to_all_addons(vault, save_fn=None):
    """Sync vault credentials to all detected addons with addon selection"""
    dialog = xbmcgui.Dialog()
    
    # First, let user choose what to sync
    services_available = []
    if vault.get('rd_token'):
        services_available.append(('rd', 'Real-Debrid'))
    if vault.get('pm_token'):
        services_available.append(('pm', 'Premiumize'))
    if vault.get('ad_token'):
        services_available.append(('ad', 'AllDebrid'))
    if vault.get('tb_token'):
        services_available.append(('tb', 'TorBox'))
    if vault.get('trakt_token'):
        services_available.append(('trakt', 'Trakt'))
    if vault.get('tmdb_api_key'):
        services_available.append(('tmdb', 'TMDB'))
    
    if not services_available:
        dialog.ok('No Credentials', 'No services authorized yet.\n\nAuthorize RD, PM, AD, Trakt, or TMDB first.')
        return []
    
    # Ask how to sync
    choice = dialog.select('Sync Options', [
        'Sync All Services (Auto)',
        'Select Addons Per Service',
        'Manage Addon Preferences'
    ])
    
    if choice == -1:
        return []
    
    all_synced = []
    
    if choice == 0:
        # Auto sync to all installed addons
        pDialog = xbmcgui.DialogProgress()
        pDialog.create('The Accountant', 'Syncing to all addons...')
        
        total = len(ADDON_SYNC_MAP)
        for i, (addon_id, mapping) in enumerate(ADDON_SYNC_MAP.items()):
            pDialog.update(int((i / total) * 100), f'Syncing {mapping.get("name", addon_id)}...')
            # Pre-check installation state so Kodi never prompts the user
            # to install addons that aren't part of their setup.
            if not _is_addon_installed(addon_id):
                continue
            try:
                target = xbmcaddon.Addon(addon_id)
                addon_synced = False
                for service, settings_list in mapping.items():
                    if service == 'name':
                        continue
                    for setting_key, vault_key in settings_list:
                        value = vault.get(vault_key, '')
                        if value:
                            target.setSetting(setting_key, value)
                            addon_synced = True
                if addon_synced:
                    all_synced.append(mapping.get('name', addon_id.split('.')[-1]))
            except Exception:
                pass
        
        pDialog.close()
        
        if all_synced:
            dialog.ok('Sync Complete', f'Synced to {len(all_synced)} addons:\n\n{", ".join(all_synced[:10])}{"..." if len(all_synced) > 10 else ""}')
        else:
            dialog.ok('Sync Complete', 'No compatible addons found.')
    
    elif choice == 1:
        # Select addons per service
        for service_type, service_name in services_available:
            synced = sync_service_to_selected_addons(vault, save_fn, service_type, service_name)
            all_synced.extend(synced)
    
    elif choice == 2:
        # Manage preferences - show current settings
        manage_sync_preferences(vault, save_fn)
    
    return all_synced


def manage_sync_preferences(vault, save_fn):
    """Manage addon sync preferences"""
    dialog = xbmcgui.Dialog()
    prefs = load_sync_preferences(vault)
    
    options = [
        'View Current Settings',
        'Reset All to Default (Enable All)',
        'Configure Real-Debrid Addons',
        'Configure Premiumize Addons',
        'Configure AllDebrid Addons',
        'Configure TorBox Addons',
        'Configure Trakt Addons',
        'Configure TMDB Addons'
    ]
    
    choice = dialog.select('Manage Sync Preferences', options)
    
    if choice == 0:
        # View current settings
        lines = ['[COLOR cyan]Current Sync Preferences[/COLOR]\n']
        for service, service_prefs in prefs.items():
            enabled = [k.split('.')[-1] for k, v in service_prefs.items() if v]
            disabled = [k.split('.')[-1] for k, v in service_prefs.items() if not v]
            lines.append(f'[COLOR yellow]{service.upper()}[/COLOR]')
            if enabled:
                lines.append(f'  Enabled: {", ".join(enabled)}')
            if disabled:
                lines.append(f'  Disabled: {", ".join(disabled)}')
            lines.append('')
        dialog.textviewer('Sync Preferences', '\n'.join(lines) if len(lines) > 1 else 'No preferences saved yet.')
    
    elif choice == 1:
        # Reset all
        if dialog.yesno('Reset Preferences', 'Reset all addon sync preferences to default (all enabled)?'):
            vault[SYNC_PREFS_KEY] = {}
            if save_fn:
                save_fn(vault)
            dialog.notification('The Accountant', 'Preferences reset', xbmcgui.NOTIFICATION_INFO, 2000)
    
    elif choice >= 2:
        # Configure specific service
        service_map = {
            2: ('rd', 'Real-Debrid'),
            3: ('pm', 'Premiumize'),
            4: ('ad', 'AllDebrid'),
            5: ('tb', 'TorBox'),
            6: ('trakt', 'Trakt'),
            7: ('tmdb', 'TMDB')
        }
        if choice in service_map:
            service_type, service_name = service_map[choice]
            select_addons_for_sync(vault, save_fn, service_type, service_name)
