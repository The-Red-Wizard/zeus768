# -*- coding: utf-8 -*-
"""
PunchPlay.tv integration for Orion
Full Trakt-parity client:
  - Device-code OAuth login (https://punchplay.tv/link)
  - Token refresh on 401
  - Scrobbler (start / pause / resume / progress / stop)
  - Lists: watchlist, collection, watched, custom lists, liked lists,
           recommendations, trending, popular
  - Sync: add/remove watchlist, remove collection, mark/remove history,
          remove list item

The endpoints intentionally mirror the Trakt API shape so the rest of
Orion can treat PunchPlay as a drop-in equivalent.
"""

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
SSL_CONTEXT = ssl._create_unverified_context()
CLIENT_VERSION = "1.1.0"


def _base_url():
    url = ADDON.getSetting('punchplay_url') or 'https://punchplay.tv'
    return url.rstrip('/')


class PunchPlayAPI:
    """Thin HTTP client for the PunchPlay backend"""

    def __init__(self):
        self.token = ADDON.getSetting('punchplay_token') or ''
        self.refresh_token = ADDON.getSetting('punchplay_refresh') or ''
        self.client_id = ADDON.getSetting('punchplay_client_id') or ''
        self.client_secret = ADDON.getSetting('punchplay_client_secret') or ''
        self.device_id = ADDON.getSetting('punchplay_device_id') or ''
        if not self.device_id:
            self.device_id = str(uuid.uuid4())
            ADDON.setSetting('punchplay_device_id', self.device_id)

    # ----------------------------------------------------------- low-level
    def _headers(self, auth=True):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': f'Orion-PunchPlay/{CLIENT_VERSION} Kodi',
            'punchplay-api-version': '1',
        }
        if self.client_id:
            headers['punchplay-api-key'] = self.client_id
        if auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def _request(self, path, payload=None, method='GET', auth=True,
                 retry_on_401=True, timeout=15):
        url = f"{_base_url()}{path}"
        body = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib.request.Request(url, data=body, headers=self._headers(auth), method=method)
        try:
            with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=timeout) as resp:
                raw = resp.read()
                if not raw:
                    return {}
                try:
                    return json.loads(raw.decode('utf-8'))
                except Exception:
                    return {}
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and retry_on_401 and self.refresh_token:
                if self._do_refresh():
                    return self._request(path, payload, method, auth,
                                         retry_on_401=False, timeout=timeout)
            try:
                return json.loads(exc.read().decode('utf-8'))
            except Exception:
                return {'error': f'HTTP {exc.code}'}
        except Exception as e:
            return {'error': str(e)}

    def _do_refresh(self):
        if not self.refresh_token:
            return False
        try:
            url = f"{_base_url()}/api/auth/refresh"
            payload = {'refresh_token': self.refresh_token}
            if self.client_id:
                payload['client_id'] = self.client_id
            if self.client_secret:
                payload['client_secret'] = self.client_secret
            body = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=body,
                headers={'Content-Type': 'application/json',
                         'Accept': 'application/json'},
                method='POST',
            )
            with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            access = data.get('access_token')
            if not access:
                return False
            self.token = access
            self.refresh_token = data.get('refresh_token', self.refresh_token)
            ADDON.setSetting('punchplay_token', self.token)
            ADDON.setSetting('punchplay_refresh', self.refresh_token)
            return True
        except Exception as e:
            xbmc.log(f"[Orion-PunchPlay] refresh failed: {e}", xbmc.LOGWARNING)
            return False

    def is_authorized(self):
        return bool(self.token)

    def logout(self):
        ADDON.setSetting('punchplay_token', '')
        ADDON.setSetting('punchplay_refresh', '')
        self.token = ''
        self.refresh_token = ''
        xbmcgui.Dialog().notification('PunchPlay', 'Logged out',
                                      xbmcgui.NOTIFICATION_INFO, 3000)

    # ---------------------------------------------------------------- login
    def pair(self):
        """Run the full device-code OAuth flow with a Kodi progress dialog."""
        dialog = xbmcgui.Dialog()
        try:
            payload = {'device_id': self.device_id}
            if self.client_id:
                payload['client_id'] = self.client_id
            resp = self._request('/api/auth/device/code', payload=payload,
                                 method='POST', auth=False, retry_on_401=False)
        except Exception as e:
            dialog.ok('PunchPlay', f'Failed to start login:\n{e}')
            return False

        if isinstance(resp, dict) and resp.get('error') and not resp.get('user_code'):
            dialog.ok('PunchPlay', f"Failed to start login:\n{resp.get('error')}")
            return False

        user_code = resp.get('user_code', '')
        verification_uri = resp.get('verification_uri') or resp.get('verification_url') \
            or 'https://punchplay.tv/link'
        device_code = resp.get('device_code', '')
        expires_in = int(resp.get('expires_in', 600))
        interval = int(resp.get('interval', 5))

        if not user_code or not device_code:
            dialog.ok('PunchPlay', 'Server did not return a device code.')
            return False

        progress = xbmcgui.DialogProgress()
        progress.create(
            'PunchPlay Authorization  [BETA]',
            f'[COLOR red]BETA - placeholder integration. Not all endpoints are live yet.[/COLOR]\n'
            f'Visit: [COLOR cyan]{verification_uri}[/COLOR]\n'
            f'Enter Code: [COLOR yellow]{user_code}[/COLOR]\n'
            'Waiting for authorization...'
        )

        start = time.time()
        try:
            while not progress.iscanceled():
                elapsed = time.time() - start
                if elapsed > expires_in:
                    progress.close()
                    dialog.ok('PunchPlay', 'Authorization timed out')
                    return False
                progress.update(int((elapsed / expires_in) * 100))
                time.sleep(max(1, interval))

                token_payload = {
                    'device_code': device_code,
                    'device_id': self.device_id,
                    'device_name': xbmc.getInfoLabel('System.FriendlyName') or 'Kodi',
                }
                if self.client_id:
                    token_payload['client_id'] = self.client_id
                if self.client_secret:
                    token_payload['client_secret'] = self.client_secret

                try:
                    token_url = f"{_base_url()}/api/auth/device/token"
                    token_req = urllib.request.Request(
                        token_url,
                        data=json.dumps(token_payload).encode('utf-8'),
                        headers=self._headers(auth=False),
                        method='POST',
                    )
                    with urllib.request.urlopen(token_req, context=SSL_CONTEXT, timeout=15) as r:
                        token_resp = json.loads(r.read().decode('utf-8'))
                    if token_resp.get('access_token'):
                        self.token = token_resp['access_token']
                        self.refresh_token = token_resp.get('refresh_token', '')
                        ADDON.setSetting('punchplay_token', self.token)
                        ADDON.setSetting('punchplay_refresh', self.refresh_token)
                        progress.close()
                        dialog.ok('PunchPlay', '[COLOR lime]Successfully authorized![/COLOR]')
                        return True
                except urllib.error.HTTPError as exc:
                    err = ''
                    try:
                        err = json.loads(exc.read().decode('utf-8')).get('error', '')
                    except Exception:
                        pass
                    if err in ('expired', 'access_denied'):
                        progress.close()
                        dialog.ok('PunchPlay', f'Authorization {err}')
                        return False
                    # 400 = pending, keep polling
        finally:
            try:
                progress.close()
            except Exception:
                pass
        return False

    # ============================================================== LISTS
    def get_list(self, list_type, media_type):
        """Generic list fetch (trending / popular / watchlist / watched / collection)."""
        if list_type == 'watchlist':
            endpoint = f"/api/users/me/watchlist/{media_type}"
        elif list_type == 'trending':
            endpoint = f"/api/{media_type}/trending"
        elif list_type == 'popular':
            endpoint = f"/api/{media_type}/popular"
        elif list_type == 'watched':
            endpoint = f"/api/users/me/watched/{media_type}"
        elif list_type == 'collected' or list_type == 'collection':
            endpoint = f"/api/users/me/collection/{media_type}"
        else:
            endpoint = f"/api/{media_type}/trending"

        auth_required = list_type in ('watchlist', 'watched', 'collected', 'collection')
        data = self._request(endpoint, auth=auth_required)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get('items'), list):
            return data['items']
        return []

    def _paged_list(self, endpoint, auth=True):
        data = self._request(endpoint, auth=auth)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get('items'), list):
            return data['items']
        return []

    def get_watchlist_movies(self, page=1):
        return self._paged_list(f"/api/users/me/watchlist/movies?page={page}&limit=20")

    def get_watchlist_shows(self, page=1):
        return self._paged_list(f"/api/users/me/watchlist/shows?page={page}&limit=20")

    def get_collection_movies(self, page=1):
        return self._paged_list(f"/api/users/me/collection/movies?page={page}&limit=50")

    def get_collection_shows(self, page=1):
        return self._paged_list(f"/api/users/me/collection/shows?page={page}&limit=50")

    def get_watched_movies(self):
        return self._paged_list("/api/users/me/watched/movies")

    def get_watched_shows(self):
        return self._paged_list("/api/users/me/watched/shows")

    def get_recommendations_movies(self, page=1):
        return self._paged_list(f"/api/recommendations/movies?page={page}&limit=20")

    def get_recommendations_shows(self, page=1):
        return self._paged_list(f"/api/recommendations/shows?page={page}&limit=20")

    def get_user_lists(self, page=1):
        return self._paged_list("/api/users/me/lists")

    def get_liked_lists(self, page=1, limit=20):
        return self._paged_list(f"/api/users/likes/lists?page={page}&limit={limit}")

    def get_list_items(self, username, list_id, page=1, limit=50):
        username = username or 'me'
        return self._paged_list(
            f"/api/users/{username}/lists/{list_id}/items?page={page}&limit={limit}"
        )

    # ============================================================ MUTATE
    def add_to_watchlist(self, media_type, ids):
        key = 'movies' if media_type == 'movie' else 'shows'
        return self._request('/api/sync/watchlist',
                             {key: [{'ids': ids}]}, method='POST')

    def remove_from_watchlist(self, media_type, ids):
        key = 'movies' if media_type == 'movie' else 'shows'
        return self._request('/api/sync/watchlist/remove',
                             {key: [{'ids': ids}]}, method='POST')

    def add_to_collection(self, media_type, ids):
        key = 'movies' if media_type == 'movie' else 'shows'
        return self._request('/api/sync/collection',
                             {key: [{'ids': ids}]}, method='POST')

    def remove_from_collection(self, media_type, ids):
        key = 'movies' if media_type == 'movie' else 'shows'
        return self._request('/api/sync/collection/remove',
                             {key: [{'ids': ids}]}, method='POST')

    def mark_watched(self, media_type, ids):
        key = 'movies' if media_type == 'movie' else 'episodes'
        return self._request('/api/sync/history',
                             {key: [{'ids': ids}]}, method='POST')

    def remove_from_history(self, media_type, ids):
        key = 'movies' if media_type == 'movie' else 'shows'
        return self._request('/api/sync/history/remove',
                             {key: [{'ids': ids}]}, method='POST')

    def remove_from_list(self, username, list_id, media_type, ids):
        username = username or 'me'
        key = 'movies' if media_type == 'movie' else 'shows'
        endpoint = f"/api/users/{username}/lists/{list_id}/items/remove"
        return self._request(endpoint, {key: [{'ids': ids}]}, method='POST')


class PunchPlayScrobbler:
    """Scrobbles playback events to PunchPlay"""

    def __init__(self, api):
        self.api = api
        self.current = None  # dict with media info

    def _payload(self, info, progress):
        duration = int(info.get('duration_seconds', 0))
        position = int(duration * (progress / 100.0)) if duration else 0
        payload = {
            'media_type': info.get('media_type', 'movie'),
            'title': info.get('title', ''),
            'progress': round(progress / 100.0, 4),
            'duration_seconds': duration,
            'position_seconds': position,
            'device_id': self.api.device_id,
            'client_version': CLIENT_VERSION,
        }
        for key in ('year', 'tmdb_id', 'imdb_id', 'tvdb_id', 'season', 'episode'):
            val = info.get(key)
            if val not in (None, '', 0):
                payload[key] = val
        return payload

    def _post(self, endpoint, info, progress):
        if not self.api.is_authorized():
            return
        try:
            self.api._request(endpoint, payload=self._payload(info, progress),
                              method='POST')
        except Exception as e:
            xbmc.log(f"[Orion-PunchPlay] scrobble {endpoint} error: {e}",
                     xbmc.LOGWARNING)

    def start_watching(self, info, progress=0):
        self.current = info
        self._post('/api/scrobble/start', info, progress)
        xbmc.log("[Orion-PunchPlay] scrobble started", xbmc.LOGINFO)

    def pause_watching(self, progress):
        if self.current:
            self._post('/api/scrobble/pause', self.current, progress)

    def resume_watching(self, progress):
        if self.current:
            self._post('/api/scrobble/resume', self.current, progress)

    def progress_watching(self, progress):
        if self.current:
            self._post('/api/scrobble/progress', self.current, progress)

    def stop_watching(self, progress):
        if self.current:
            self._post('/api/scrobble/stop', self.current, progress)
            xbmc.log(f"[Orion-PunchPlay] scrobble stopped at {progress}%",
                     xbmc.LOGINFO)
            # Auto-mark watched at >=80% (Trakt parity)
            try:
                if progress >= 80:
                    info = self.current
                    media_type = info.get('media_type', 'movie')
                    ids = {}
                    if info.get('tmdb_id'):
                        ids['tmdb'] = info['tmdb_id']
                    if info.get('imdb_id'):
                        ids['imdb'] = info['imdb_id']
                    if ids:
                        mt = 'movie' if media_type == 'movie' else 'episode'
                        self.api.mark_watched(mt, ids)
            except Exception as e:
                xbmc.log(f"[Orion-PunchPlay] mark watched error: {e}",
                         xbmc.LOGWARNING)
        self.current = None
