"""
SALTS Library - PunchPlay.tv API Integration
Added by zeus768 for SALTS 2.9.1 - parallel tracker to Trakt.

PunchPlay is a Trakt alternative. Only the scrobble + device-code auth
endpoints are publicly documented (see https://github.com/PunchPlay/script.punchplay),
so this client intentionally implements only that surface. It is safe to run
alongside Trakt - calls are best-effort and never raise into the caller.
"""
import base64
import json
import os
import time
import uuid

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from . import log_utils

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_DATA_PATH = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}/')

# Public PunchPlay API base (overridable via addon setting)
DEFAULT_BASE_URL = 'https://punchplay.tv'
USER_AGENT = f'SALTS/{ADDON_VERSION} PunchPlay-Client'

TOKEN_FILE = os.path.join(ADDON_DATA_PATH, 'punchplay_auth.json')
DEVICE_ID_FILE = os.path.join(ADDON_DATA_PATH, 'punchplay_device.json')
QR_FILE = os.path.join(ADDON_DATA_PATH, 'punchplay_qr.png')


def _fresh_addon():
    return xbmcaddon.Addon()


def _ensure_data_path():
    if not xbmcvfs.exists(ADDON_DATA_PATH):
        xbmcvfs.mkdirs(ADDON_DATA_PATH)


def _get_device_id():
    """Stable per-install UUID for PunchPlay scrobble payloads."""
    _ensure_data_path()
    if os.path.exists(DEVICE_ID_FILE):
        try:
            with open(DEVICE_ID_FILE, 'r') as f:
                data = json.load(f)
                did = data.get('device_id')
                if did:
                    return did
        except Exception:
            pass
    did = str(uuid.uuid4())
    try:
        with open(DEVICE_ID_FILE, 'w') as f:
            json.dump({'device_id': did, 'created_at': time.time()}, f)
    except Exception:
        pass
    return did


class PunchPlayError(Exception):
    pass


class PunchPlayAPI:
    """PunchPlay.tv scrobble + device-code auth client.

    All non-auth calls are fire-and-forget: any error is logged and swallowed
    so playback logic never breaks when PunchPlay is down or unauthorized.
    """

    def __init__(self):
        self.base_url = (_fresh_addon().getSetting('punchplay_base_url') or DEFAULT_BASE_URL).rstrip('/')
        self.device_id = _get_device_id()
        self._load_tokens()

    # -------------------------------------------------- token storage

    def _load_tokens(self):
        _ensure_data_path()
        self.access_token = ''
        self.refresh_token = ''
        self.expires = 0.0

        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                self.access_token = data.get('access_token', '')
                self.refresh_token = data.get('refresh_token', '')
                self.expires = float(data.get('expires', 0))
                return
            except Exception as e:
                log_utils.log(f'PunchPlay: token file load failed: {e}', xbmc.LOGWARNING)

        addon = _fresh_addon()
        self.access_token = addon.getSetting('punchplay_access_token')
        self.refresh_token = addon.getSetting('punchplay_refresh_token')
        try:
            self.expires = float(addon.getSetting('punchplay_expires') or 0)
        except Exception:
            self.expires = 0.0

    def _save_tokens(self, result):
        _ensure_data_path()
        self.access_token = result.get('access_token', '')
        self.refresh_token = result.get('refresh_token', self.refresh_token)
        expires_in = int(result.get('expires_in', 7776000))  # default 90d
        self.expires = time.time() + expires_in

        try:
            with open(TOKEN_FILE, 'w') as f:
                json.dump({
                    'access_token': self.access_token,
                    'refresh_token': self.refresh_token,
                    'expires': self.expires,
                    'created_at': time.time(),
                }, f, indent=2)
        except Exception as e:
            log_utils.log(f'PunchPlay: token file save failed: {e}', xbmc.LOGWARNING)

        addon = _fresh_addon()
        addon.setSetting('punchplay_access_token', self.access_token)
        addon.setSetting('punchplay_refresh_token', self.refresh_token)
        addon.setSetting('punchplay_expires', str(self.expires))
        addon.setSetting('punchplay_enabled', 'true')

    def clear_authorization(self):
        self.access_token = ''
        self.refresh_token = ''
        self.expires = 0.0
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
            except Exception:
                pass
        addon = _fresh_addon()
        addon.setSetting('punchplay_access_token', '')
        addon.setSetting('punchplay_refresh_token', '')
        addon.setSetting('punchplay_expires', '0')
        addon.setSetting('punchplay_enabled', 'false')

    def is_authorized(self):
        if not self.access_token:
            return False
        if time.time() > self.expires - 3600:
            return self._refresh_access_token()
        return True

    # -------------------------------------------------- http

    def _http(self, path, method='GET', data=None, auth=True, timeout=20):
        url = path if path.startswith('http') else f'{self.base_url}{path}'
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
        }
        if auth and self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'

        body = None
        if data is not None:
            body = json.dumps(data).encode('utf-8')

        req = Request(url, data=body, headers=headers, method=method)
        try:
            resp = urlopen(req, timeout=timeout)
            return resp.getcode(), resp.read().decode('utf-8')
        except HTTPError as e:
            try:
                err_body = e.read().decode('utf-8')
            except Exception:
                err_body = ''
            return e.code, err_body
        except URLError as e:
            raise PunchPlayError(f'network: {e.reason}')
        except Exception as e:
            raise PunchPlayError(f'request failed: {e}')

    def _refresh_access_token(self):
        if not self.refresh_token:
            return False
        try:
            status, body = self._http(
                '/api/auth/token/refresh',
                method='POST',
                data={'refresh_token': self.refresh_token},
                auth=False,
            )
            if status == 200 and body:
                result = json.loads(body)
                if result.get('access_token'):
                    self._save_tokens(result)
                    log_utils.log('PunchPlay: token refreshed', xbmc.LOGINFO)
                    return True
            log_utils.log(f'PunchPlay: refresh failed ({status})', xbmc.LOGWARNING)
        except Exception as e:
            log_utils.log(f'PunchPlay refresh error: {e}', xbmc.LOGWARNING)
        return False

    # -------------------------------------------------- device-code auth

    def authorize(self):
        """Show a device-code dialog and poll for an access token."""
        try:
            status, body = self._http(
                '/api/auth/device/code', method='POST', data={}, auth=False
            )
            if status != 200 or not body:
                xbmcgui.Dialog().ok('PunchPlay Error', f'Failed to start login (HTTP {status}).')
                return False
            info = json.loads(body)
        except Exception as e:
            xbmcgui.Dialog().ok('PunchPlay Error', f'Connection error: {e}')
            return False

        device_code = info.get('device_code')
        user_code = info.get('user_code')
        verification_uri = info.get('verification_uri') or f'{self.base_url}/link'
        interval = int(info.get('interval', 5))
        expires_in = int(info.get('expires_in', 600))

        # Optional: decode QR image if server returned one
        qr_png = info.get('verification_uri_qr')
        if qr_png:
            try:
                _ensure_data_path()
                raw = qr_png
                if ',' in raw:  # data URI prefix
                    raw = raw.split(',', 1)[1]
                with open(QR_FILE, 'wb') as f:
                    f.write(base64.b64decode(raw))
            except Exception:
                pass

        if not device_code or not user_code:
            xbmcgui.Dialog().ok('PunchPlay Error', 'Invalid response from PunchPlay.')
            return False

        dialog = xbmcgui.DialogProgress()
        dialog.create(
            'PunchPlay Authorization',
            f'Visit: {verification_uri}\n\n'
            f'Enter Code: [B]{user_code}[/B]\n\n'
            'Waiting for authorization...'
        )

        start = time.time()
        poll = 0
        while time.time() - start < expires_in:
            if dialog.iscanceled():
                dialog.close()
                return False
            elapsed = time.time() - start
            percent = int(elapsed / expires_in * 100)
            dialog.update(
                percent,
                f'Visit: {verification_uri}\n\n'
                f'Enter Code: [B]{user_code}[/B]\n\n'
                f'Time remaining: {int(expires_in - elapsed)} seconds'
            )
            time.sleep(interval)
            poll += 1

            try:
                status, body = self._http(
                    '/api/auth/device/token',
                    method='POST',
                    data={'device_code': device_code},
                    auth=False,
                )
            except Exception:
                continue

            if status == 200 and body:
                try:
                    result = json.loads(body)
                except Exception:
                    continue
                if result.get('access_token'):
                    self._save_tokens(result)
                    dialog.close()
                    username = ''
                    try:
                        me = self.get_me()
                        if me:
                            username = me.get('username') or me.get('name') or ''
                    except Exception:
                        pass
                    msg = f'Authorized as: {username}' if username else 'Authorization successful!'
                    xbmcgui.Dialog().ok('PunchPlay Authorization', msg)
                    return True

            # 400 = authorization_pending, 428 = slow_down, keep polling
            if status == 429 or status == 428:
                interval = min(interval + 1, 10)
                continue
            if status in (404, 410):
                dialog.close()
                xbmcgui.Dialog().ok('PunchPlay Error', 'Code expired or invalid. Please try again.')
                return False
            if status == 418:
                dialog.close()
                xbmcgui.Dialog().ok('PunchPlay', 'Authorization was denied.')
                return False

        dialog.close()
        xbmcgui.Dialog().ok('PunchPlay', 'Authorization timeout. Please try again.')
        return False

    def get_me(self):
        """Best-effort current-user fetch (may not exist on all servers)."""
        try:
            status, body = self._http('/api/me', method='GET')
            if status == 200 and body:
                return json.loads(body)
        except Exception:
            pass
        return None

    # -------------------------------------------------- scrobble

    def _payload(self, media_type, title, year, tmdb_id, imdb_id,
                 progress, duration_seconds, position_seconds,
                 season=None, episode=None, watched=None):
        payload = {
            'media_type': media_type,  # 'movie' or 'episode'
            'title': title or '',
            'progress': max(0.0, min(1.0, float(progress or 0))),
            'duration_seconds': int(duration_seconds or 0),
            'position_seconds': int(position_seconds or 0),
            'device_id': self.device_id,
            'client_version': ADDON_VERSION,
        }
        if year:
            try:
                payload['year'] = int(str(year)[:4])
            except Exception:
                pass
        if tmdb_id:
            try:
                payload['tmdb_id'] = int(tmdb_id)
            except Exception:
                pass
        if imdb_id:
            payload['imdb_id'] = str(imdb_id)
        if media_type == 'episode':
            if season is not None:
                try:
                    payload['season'] = int(season)
                except Exception:
                    pass
            if episode is not None:
                try:
                    payload['episode'] = int(episode)
                except Exception:
                    pass
        if watched is not None:
            payload['watched'] = bool(watched)
        return payload

    def _post_scrobble(self, endpoint, payload):
        if not self.is_authorized():
            return False
        try:
            status, body = self._http(endpoint, method='POST', data=payload)
            if status == 401 and self._refresh_access_token():
                status, body = self._http(endpoint, method='POST', data=payload)
            if 200 <= status < 300:
                return True
            log_utils.log(f'PunchPlay {endpoint} -> {status} {body[:200]}', xbmc.LOGDEBUG)
        except Exception as e:
            log_utils.log(f'PunchPlay {endpoint} error: {e}', xbmc.LOGDEBUG)
        return False

    def scrobble_start(self, media_type, title, year, tmdb_id, imdb_id,
                       progress, duration_seconds, position_seconds,
                       season=None, episode=None):
        return self._post_scrobble('/api/scrobble/start', self._payload(
            media_type, title, year, tmdb_id, imdb_id,
            progress, duration_seconds, position_seconds, season, episode))

    def scrobble_pause(self, media_type, title, year, tmdb_id, imdb_id,
                       progress, duration_seconds, position_seconds,
                       season=None, episode=None):
        return self._post_scrobble('/api/scrobble/pause', self._payload(
            media_type, title, year, tmdb_id, imdb_id,
            progress, duration_seconds, position_seconds, season, episode))

    def scrobble_resume(self, media_type, title, year, tmdb_id, imdb_id,
                        progress, duration_seconds, position_seconds,
                        season=None, episode=None):
        return self._post_scrobble('/api/scrobble/resume', self._payload(
            media_type, title, year, tmdb_id, imdb_id,
            progress, duration_seconds, position_seconds, season, episode))

    def scrobble_progress(self, media_type, title, year, tmdb_id, imdb_id,
                          progress, duration_seconds, position_seconds,
                          season=None, episode=None):
        return self._post_scrobble('/api/scrobble/progress', self._payload(
            media_type, title, year, tmdb_id, imdb_id,
            progress, duration_seconds, position_seconds, season, episode))

    def scrobble_stop(self, media_type, title, year, tmdb_id, imdb_id,
                      progress, duration_seconds, position_seconds,
                      season=None, episode=None, watched=None):
        return self._post_scrobble('/api/scrobble/stop', self._payload(
            media_type, title, year, tmdb_id, imdb_id,
            progress, duration_seconds, position_seconds,
            season, episode, watched=watched))

    def mark_watched(self, media_type, title, year, tmdb_id, imdb_id,
                     duration_seconds=0, season=None, episode=None):
        """Explicit full watch mark - modeled as scrobble_stop at 100% with watched=True."""
        return self.scrobble_stop(
            media_type, title, year, tmdb_id, imdb_id,
            progress=1.0,
            duration_seconds=duration_seconds,
            position_seconds=duration_seconds,
            season=season, episode=episode,
            watched=True,
        )

    # -------------------------------------------------- playback / resume (stub)
    #
    # The /api/playback endpoint is not part of PunchPlay's currently documented
    # public surface. This block ships as a best-effort client that activates
    # automatically the moment the endpoint becomes available server-side. Until
    # then every call is silent and returns an empty list / False so that SALTS
    # behaves identically to a build without this feature.

    def is_playback_api_available(self, timeout=3):
        """HEAD/GET probe of /api/playback. Returns True only on HTTP 200.

        Any network error, 401/403/404 or non-200 is treated as "not available"
        so the SALTS main menu silently hides the Continue Watching row.
        """
        try:
            status, _ = self._http('/api/playback', method='GET', timeout=timeout)
            return status == 200
        except PunchPlayError:
            return False
        except Exception:
            return False

    def get_continue_watching(self, limit=30, timeout=8):
        """Return the user's in-progress items from PunchPlay.

        Expected response shape (array):
            [{"title": "...", "type": "movie"|"episode", "tmdb_id": ...,
              "imdb_id": "...", "year": ..., "season": ..., "episode": ...,
              "position": <seconds>, "duration": <seconds>,
              "poster": "...", "fanart": "...", "overview": "...",
              "updated_at": "ISO-8601"}]

        Returns [] on any failure (unauthenticated, endpoint missing, bad JSON).
        Never raises into the caller.
        """
        if not self.is_authorized():
            return []
        try:
            status, body = self._http(
                f'/api/playback?limit={int(limit)}',
                method='GET',
                timeout=timeout,
            )
            if status == 401 and self._refresh_access_token():
                status, body = self._http(
                    f'/api/playback?limit={int(limit)}',
                    method='GET',
                    timeout=timeout,
                )
            if status != 200 or not body:
                return []
            data = json.loads(body)
            if isinstance(data, dict):
                # tolerate {"items": [...]} wrappers
                data = data.get('items') or data.get('results') or []
            if not isinstance(data, list):
                return []
            out = []
            for it in data:
                if not isinstance(it, dict):
                    continue
                try:
                    duration = float(it.get('duration') or 0)
                    position = float(it.get('position') or 0)
                except Exception:
                    duration, position = 0.0, 0.0
                # Skip finished items (>= 95%) and items with no meaningful progress.
                if duration > 0 and position / duration >= 0.95:
                    continue
                if position <= 0:
                    continue
                out.append({
                    'title': it.get('title') or '',
                    'type': it.get('type') or it.get('media_type') or 'movie',
                    'tmdb_id': it.get('tmdb_id') or '',
                    'imdb_id': it.get('imdb_id') or '',
                    'year': it.get('year') or '',
                    'season': it.get('season'),
                    'episode': it.get('episode'),
                    'position': position,
                    'duration': duration,
                    'poster': it.get('poster') or '',
                    'fanart': it.get('fanart') or '',
                    'overview': it.get('overview') or '',
                    'updated_at': it.get('updated_at') or '',
                })
            return out
        except PunchPlayError:
            return []
        except Exception as e:
            log_utils.log(f'PunchPlay continue_watching error: {e}', xbmc.LOGDEBUG)
            return []
