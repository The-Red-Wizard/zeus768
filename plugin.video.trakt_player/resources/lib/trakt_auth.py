"""
Trakt.tv API Authentication Module
Uses native urllib (no external requests module)
FIXED: Token persistence using file-based storage as primary
"""
import json
import time
import os
import xbmcgui
import xbmcaddon
import xbmc
import xbmcvfs

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# Get fresh addon instance
def get_addon():
    return xbmcaddon.Addon()

ADDON_ID = 'plugin.video.trakt_player'
ADDON_DATA_PATH = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')

# Trakt API v2 settings
CLIENT_ID = 'd2a8e820fec0d46079cbbceaca851648df9431cbc73ede2c10d35dfb1c7a36e2'
CLIENT_SECRET = '9c7c29e76166465882ba6723d578e97fce466cf466414a76c36184540b31e9a6'
API_URL = 'https://api.trakt.tv'
USER_AGENT = 'TraktPlayer Kodi Addon'

# Token file for persistent storage (PRIMARY storage method)
TOKEN_FILE = os.path.join(ADDON_DATA_PATH, 'trakt_token.json')


def _ensure_data_path():
    """Ensure addon data directory exists"""
    if not xbmcvfs.exists(ADDON_DATA_PATH):
        xbmcvfs.mkdirs(ADDON_DATA_PATH)
    # Double check with os.path for reliability
    if not os.path.exists(ADDON_DATA_PATH):
        os.makedirs(ADDON_DATA_PATH, exist_ok=True)


def _http_request(url, method='GET', data=None, headers=None, timeout=30):
    """Make HTTP request using urllib, returns (status_code, response_body)"""
    hdrs = {
        'Content-Type': 'application/json',
        'User-Agent': USER_AGENT,
        'trakt-api-version': '2',
        'trakt-api-key': CLIENT_ID
    }
    if headers:
        hdrs.update(headers)
    
    post_data = None
    if data is not None:
        post_data = json.dumps(data).encode('utf-8')
    
    req = Request(url, data=post_data, headers=hdrs, method=method)
    
    try:
        response = urlopen(req, timeout=timeout)
        body = response.read().decode('utf-8')
        return response.getcode(), body
    except HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8')
        except Exception:
            pass
        xbmc.log(f'Trakt HTTP Error: {e.code} - {body[:200]}', xbmc.LOGWARNING)
        return e.code, body
    except URLError as e:
        xbmc.log(f'Trakt URL Error: {e.reason}', xbmc.LOGERROR)
        return 0, str(e.reason)
    except Exception as e:
        xbmc.log(f'Trakt Request Error: {e}', xbmc.LOGERROR)
        return 0, str(e)


def _load_tokens():
    """Load tokens from file (PRIMARY method)"""
    _ensure_data_path()
    
    # Primary: Load from file
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
                tokens = {
                    'access_token': data.get('access_token', ''),
                    'refresh_token': data.get('refresh_token', ''),
                    'expires': float(data.get('expires', 0))
                }
                if tokens['access_token']:
                    xbmc.log(f'Trakt: Loaded tokens from file', xbmc.LOGDEBUG)
                    return tokens
        except Exception as e:
            xbmc.log(f'Trakt: Failed to load tokens from file: {e}', xbmc.LOGWARNING)
    
    # Fallback: Try addon settings (but these are less reliable)
    addon = get_addon()
    access = addon.getSetting('trakt_access_token')
    if access:
        tokens = {
            'access_token': access,
            'refresh_token': addon.getSetting('trakt_refresh_token'),
            'expires': float(addon.getSetting('trakt_expires') or 0)
        }
        # If found in settings, also save to file for reliability
        if tokens['access_token']:
            _save_tokens_to_file(tokens['access_token'], tokens['refresh_token'], 
                                 tokens['expires'] - time.time())
        return tokens
    
    return {'access_token': '', 'refresh_token': '', 'expires': 0}


def _save_tokens_to_file(access_token, refresh_token, expires_in):
    """Save tokens to file only"""
    _ensure_data_path()
    
    expires = time.time() + expires_in
    token_data = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires': expires,
        'created_at': time.time()
    }
    
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        xbmc.log('Trakt: Tokens saved to file successfully', xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log(f'Trakt: Failed to save tokens to file: {e}', xbmc.LOGERROR)
        return False


def _save_tokens(access_token, refresh_token, expires_in):
    """Save tokens to BOTH file (primary) and addon settings (backup)"""
    _ensure_data_path()
    
    expires = time.time() + expires_in
    
    # Save to file (PRIMARY storage) - most reliable
    _save_tokens_to_file(access_token, refresh_token, expires_in)
    
    # Also save to addon settings (backup) - may help with some Kodi versions
    try:
        addon = get_addon()
        addon.setSetting('trakt_access_token', access_token)
        addon.setSetting('trakt_refresh_token', refresh_token)
        addon.setSetting('trakt_expires', str(expires))
        addon.setSetting('trakt_auth_done', 'true')
        xbmc.log('Trakt: Tokens also saved to addon settings', xbmc.LOGDEBUG)
    except Exception as e:
        xbmc.log(f'Trakt: Failed to save to addon settings: {e}', xbmc.LOGWARNING)


def _clear_tokens():
    """Clear all stored tokens"""
    # Clear file
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            xbmc.log('Trakt: Token file removed', xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f'Trakt: Failed to remove token file: {e}', xbmc.LOGWARNING)
    
    # Clear addon settings
    try:
        addon = get_addon()
        addon.setSetting('trakt_access_token', '')
        addon.setSetting('trakt_refresh_token', '')
        addon.setSetting('trakt_expires', '0')
        addon.setSetting('trakt_auth_done', 'false')
    except Exception:
        pass


def is_authorized():
    """Check if Trakt is authorized - uses file-based tokens"""
    tokens = _load_tokens()
    if not tokens['access_token']:
        xbmc.log('Trakt: No access token found', xbmc.LOGDEBUG)
        return False
    
    # Check if token needs refresh (1 hour buffer)
    if tokens['expires'] > 0 and time.time() > tokens['expires'] - 3600:
        xbmc.log('Trakt: Token near expiry, refreshing...', xbmc.LOGINFO)
        return refresh_token()
    
    xbmc.log('Trakt: Authorization valid', xbmc.LOGDEBUG)
    return True


def get_token():
    """Get Trakt access token from file"""
    tokens = _load_tokens()
    return tokens['access_token']


def authorize():
    """Trakt device authentication - sends user to trakt.tv/activate"""
    try:
        # Step 1: Get device code
        xbmc.log('Trakt: Requesting device code...', xbmc.LOGINFO)
        
        data = {'client_id': CLIENT_ID}
        status, body = _http_request(
            f'{API_URL}/oauth/device/code',
            method='POST',
            data=data
        )
        
        xbmc.log(f'Trakt: Device code response - Status: {status}', xbmc.LOGINFO)
        
        if status != 200:
            error_msg = f'Failed to get device code (HTTP {status})'
            try:
                error_data = json.loads(body)
                error_msg = error_data.get('error_description', error_data.get('error', error_msg))
            except Exception:
                pass
            xbmc.log(f'Trakt: {error_msg}', xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Trakt Error', error_msg)
            return False
        
        try:
            result = json.loads(body)
        except Exception as json_err:
            xbmc.log(f'Trakt JSON parse error: {json_err}', xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Trakt Error', 'Invalid response from Trakt API')
            return False
        
        device_code = result.get('device_code')
        user_code = result.get('user_code')
        verification_url = result.get('verification_url', 'https://trakt.tv/activate')
        interval = result.get('interval', 5)
        expires_in = result.get('expires_in', 600)
        
        if not device_code or not user_code:
            xbmc.log('Trakt: Invalid device code response - missing fields', xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Trakt Error', 'Invalid response from Trakt. Please try again.')
            return False
        
        xbmc.log(f'Trakt: Got device code, user_code: {user_code}', xbmc.LOGINFO)
        
        # Step 2: Show dialog with instructions
        progress = xbmcgui.DialogProgress()
        progress.create(
            'Trakt Authorization',
            f'Go to: [B][COLOR skyblue]{verification_url}[/COLOR][/B]\n\n'
            f'Enter code: [B][COLOR yellow]{user_code}[/COLOR][/B]\n\n'
            f'Waiting for authorization...'
        )
        
        # Step 3: Poll for authorization
        start_time = time.time()
        poll_count = 0
        
        while time.time() - start_time < expires_in:
            if progress.iscanceled():
                progress.close()
                xbmc.log('Trakt: Authorization cancelled by user', xbmc.LOGINFO)
                xbmcgui.Dialog().notification('Cancelled', 'Authorization cancelled', xbmcgui.NOTIFICATION_INFO)
                return False
            
            # Update progress
            elapsed = time.time() - start_time
            remaining = expires_in - elapsed
            percent = int((elapsed / expires_in) * 100)
            progress.update(
                percent,
                f'Go to: [B][COLOR skyblue]{verification_url}[/COLOR][/B]\n\n'
                f'Enter code: [B][COLOR yellow]{user_code}[/COLOR][/B]\n\n'
                f'Time remaining: {int(remaining)} seconds'
            )
            
            # Wait for interval
            time.sleep(interval)
            poll_count += 1
            
            # Poll for token
            token_data = {
                'code': device_code,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET
            }
            
            token_status, token_body = _http_request(
                f'{API_URL}/oauth/device/token',
                method='POST',
                data=token_data
            )
            
            xbmc.log(f'Trakt: Poll #{poll_count} - Status: {token_status}', xbmc.LOGDEBUG)
            
            if token_status == 200:
                # Success! Save tokens
                try:
                    tokens = json.loads(token_body)
                    access_token = tokens['access_token']
                    refresh_tok = tokens.get('refresh_token', '')
                    expires = tokens.get('expires_in', 7776000)
                    
                    _save_tokens(access_token, refresh_tok, expires)
                    
                    progress.close()
                    xbmcgui.Dialog().notification('Success!', 'Trakt account authorized!', xbmcgui.NOTIFICATION_INFO, 3000)
                    xbmc.log('Trakt: Authorization completed successfully', xbmc.LOGINFO)
                    return True
                except Exception as e:
                    xbmc.log(f'Trakt: Failed to parse token response: {e}', xbmc.LOGERROR)
                    continue
            
            elif token_status == 400:
                # Pending - user hasn't authorized yet, continue polling
                continue
            
            elif token_status == 404:
                progress.close()
                xbmc.log('Trakt: Invalid device code', xbmc.LOGERROR)
                xbmcgui.Dialog().notification('Error', 'Invalid device code', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            elif token_status == 409:
                progress.close()
                xbmc.log('Trakt: Device code already used', xbmc.LOGERROR)
                xbmcgui.Dialog().notification('Error', 'Code already used', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            elif token_status == 410:
                progress.close()
                xbmc.log('Trakt: Device code expired', xbmc.LOGERROR)
                xbmcgui.Dialog().notification('Error', 'Code expired', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            elif token_status == 418:
                progress.close()
                xbmc.log('Trakt: User denied authorization', xbmc.LOGINFO)
                xbmcgui.Dialog().notification('Error', 'User denied authorization', xbmcgui.NOTIFICATION_ERROR)
                return False
            
            elif token_status == 429:
                # Rate limited - slow down
                interval = min(interval + 1, 10)
                xbmc.log(f'Trakt: Rate limited, increasing interval to {interval}s', xbmc.LOGWARNING)
                time.sleep(interval * 2)
                continue
        
        progress.close()
        xbmc.log('Trakt: Authorization timeout', xbmc.LOGWARNING)
        xbmcgui.Dialog().notification('Timeout', 'Authorization timed out', xbmcgui.NOTIFICATION_WARNING)
        return False
        
    except Exception as e:
        xbmc.log(f'Trakt auth error: {str(e)}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', f'Auth failed: {str(e)}', xbmcgui.NOTIFICATION_ERROR)
        return False


def refresh_token():
    """Refresh Trakt access token"""
    tokens = _load_tokens()
    refresh = tokens['refresh_token']
    
    if not refresh:
        xbmc.log('Trakt: No refresh token available', xbmc.LOGWARNING)
        return False
    
    try:
        data = {
            'refresh_token': refresh,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'refresh_token'
        }
        
        status, body = _http_request(
            f'{API_URL}/oauth/token',
            method='POST',
            data=data
        )
        
        if status == 200:
            result = json.loads(body)
            _save_tokens(
                result['access_token'],
                result.get('refresh_token', refresh),
                result.get('expires_in', 7776000)
            )
            xbmc.log('Trakt: Token refreshed successfully', xbmc.LOGINFO)
            return True
        else:
            xbmc.log(f'Trakt: Token refresh failed with status {status}', xbmc.LOGWARNING)
        
    except Exception as e:
        xbmc.log(f'Token refresh error: {str(e)}', xbmc.LOGERROR)
    
    return False


def revoke():
    """Revoke Trakt authorization"""
    tokens = _load_tokens()
    token = tokens['access_token']
    
    if token:
        try:
            _http_request(
                f'{API_URL}/oauth/revoke',
                method='POST',
                data={
                    'token': token,
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET
                },
                timeout=10
            )
        except Exception:
            pass
    
    _clear_tokens()
    xbmcgui.Dialog().notification('Trakt', 'Account unlinked', xbmcgui.NOTIFICATION_INFO)
