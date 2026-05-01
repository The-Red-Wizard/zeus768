# -*- coding: utf-8 -*-
"""Trakt integration — device-code OAuth + scrobble + history sync.

Get your own client_id/secret at:  https://trakt.tv/oauth/applications
(Or leave the addon-bundled defaults in place — the user authenticates
through the universal trakt.tv/activate code flow either way.)
"""
import json
import os
import time

import requests
import xbmc
import xbmcgui

from .common import (ADDON, PROFILE_PATH, log, notify, get_setting, get_setting_bool)

API = 'https://api.trakt.tv'

# Default app credentials (community Trakt app for device code flow).
# Users can override in settings -> Trakt -> Custom Trakt client ID/secret.
DEFAULT_CLIENT_ID = 'c126f684dfaf737638e14c5515bab08b98fad26feba74a3fcb09ebb29f09b41a'
DEFAULT_CLIENT_SECRET = '7c5f32152e2ba2043156b4de989438cb8ae1269c7bcb9237475920e79d28b533'

TOKEN_FILE = os.path.join(PROFILE_PATH, 'trakt_token.json')


def _client_id():
    return get_setting('trakt_client_id') or DEFAULT_CLIENT_ID


def _client_secret():
    return get_setting('trakt_client_secret') or DEFAULT_CLIENT_SECRET


def _headers(auth=False):
    h = {
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': _client_id(),
        'User-Agent': 'Vidscr/1.1.0',
    }
    if auth:
        tok = _load_token()
        if tok and tok.get('access_token'):
            h['Authorization'] = 'Bearer %s' % tok['access_token']
    return h


def _load_token():
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log('Trakt: load token failed %s' % e)
    return None


def _save_token(tok):
    try:
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(tok, f)
    except Exception as e:
        log('Trakt: save token failed %s' % e)


def is_authenticated():
    tok = _load_token()
    if not tok or not tok.get('access_token'):
        return False
    if tok.get('expires_at', 0) < time.time() + 60:
        return _refresh_token(tok)
    return True


def _refresh_token(tok):
    if not tok.get('refresh_token'):
        return False
    try:
        r = requests.post(API + '/oauth/token', headers=_headers(),
                          data=json.dumps({
                              'refresh_token': tok['refresh_token'],
                              'client_id': _client_id(),
                              'client_secret': _client_secret(),
                              'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                              'grant_type': 'refresh_token',
                          }), timeout=20)
        if r.status_code == 200:
            data = r.json()
            data['expires_at'] = time.time() + int(data.get('expires_in', 7776000))
            _save_token(data)
            return True
        log('Trakt refresh failed: %s' % r.status_code)
    except Exception as e:
        log('Trakt refresh exception: %s' % e)
    return False


def authenticate():
    """Device-code OAuth flow. Shows a code + URL to enter at trakt.tv/activate."""
    try:
        r = requests.post(API + '/oauth/device/code', headers=_headers(),
                          data=json.dumps({'client_id': _client_id()}), timeout=20)
        if r.status_code != 200:
            notify('Trakt: device code request failed (%s)' % r.status_code)
            return
        data = r.json()
    except Exception as e:
        notify('Trakt error: %s' % e)
        return

    user_code = data.get('user_code')
    verify_url = data.get('verification_url', 'https://trakt.tv/activate')
    interval = int(data.get('interval', 5))
    expires_in = int(data.get('expires_in', 600))
    device_code = data.get('device_code')

    msg = ('Open [B]%s[/B] in any browser and enter the code:\n\n[B]%s[/B]\n\n'
           'Waiting for authorisation... (this dialog will auto-close)') % (verify_url, user_code)

    pd = xbmcgui.DialogProgress()
    pd.create('Trakt — device authentication', msg)

    elapsed = 0
    poll_interval = max(interval, 3)
    while elapsed < expires_in:
        if pd.iscanceled():
            pd.close()
            return
        xbmc.sleep(poll_interval * 1000)
        elapsed += poll_interval
        try:
            pr = requests.post(API + '/oauth/device/token', headers=_headers(),
                               data=json.dumps({
                                   'code': device_code,
                                   'client_id': _client_id(),
                                   'client_secret': _client_secret(),
                               }), timeout=20)
        except Exception as e:
            log('Trakt poll exception: %s' % e)
            continue

        if pr.status_code == 200:
            tok = pr.json()
            tok['expires_at'] = time.time() + int(tok.get('expires_in', 7776000))
            _save_token(tok)
            pd.close()
            ADDON.setSetting('trakt_status', 'Authenticated')
            notify('Trakt: authentication successful')
            return
        elif pr.status_code == 400:
            # Pending — keep polling
            continue
        elif pr.status_code in (404, 410, 418, 429):
            pd.close()
            notify('Trakt: device code expired / denied (%s)' % pr.status_code)
            return

    pd.close()
    notify('Trakt: authentication timed out')


def logout():
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
    except Exception:
        pass
    ADDON.setSetting('trakt_status', 'Not authenticated')
    notify('Trakt: signed out')


def _post(path, payload):
    if not is_authenticated():
        return None
    try:
        r = requests.post(API + path, headers=_headers(auth=True),
                          data=json.dumps(payload), timeout=20)
        if r.status_code in (200, 201, 204):
            try:
                return r.json()
            except Exception:
                return {}
        log('Trakt %s -> %s' % (path, r.status_code))
    except Exception as e:
        log('Trakt POST %s failed: %s' % (path, e))
    return None


def _get(path, params=None):
    if not is_authenticated():
        return None
    try:
        r = requests.get(API + path, headers=_headers(auth=True),
                         params=params or {}, timeout=20)
        if r.status_code == 200:
            return r.json()
        log('Trakt GET %s -> %s' % (path, r.status_code))
    except Exception as e:
        log('Trakt GET %s failed: %s' % (path, e))
    return None


# ---------- Scrobble ----------

def _scrobble_payload(media_type, ids, season=None, episode=None, progress=0.0):
    if media_type == 'movie':
        return {'movie': {'ids': ids}, 'progress': float(progress)}
    return {
        'show': {'ids': ids},
        'episode': {'season': int(season or 0), 'number': int(episode or 0)},
        'progress': float(progress),
    }


def scrobble_start(media_type, imdb_id=None, tmdb_id=None, season=None, episode=None, progress=0.0):
    if not (get_setting_bool('trakt_enabled') and get_setting_bool('trakt_scrobble')):
        return
    ids = {}
    if imdb_id:
        ids['imdb'] = imdb_id
    if tmdb_id:
        ids['tmdb'] = int(tmdb_id) if str(tmdb_id).isdigit() else tmdb_id
    if not ids:
        return
    _post('/scrobble/start', _scrobble_payload(media_type, ids, season, episode, progress))


def scrobble_pause(media_type, imdb_id=None, tmdb_id=None, season=None, episode=None, progress=0.0):
    if not (get_setting_bool('trakt_enabled') and get_setting_bool('trakt_scrobble')):
        return
    ids = {}
    if imdb_id:
        ids['imdb'] = imdb_id
    if tmdb_id:
        ids['tmdb'] = int(tmdb_id) if str(tmdb_id).isdigit() else tmdb_id
    if not ids:
        return
    _post('/scrobble/pause', _scrobble_payload(media_type, ids, season, episode, progress))


def scrobble_stop(media_type, imdb_id=None, tmdb_id=None, season=None, episode=None, progress=0.0):
    if not (get_setting_bool('trakt_enabled') and get_setting_bool('trakt_scrobble')):
        return
    ids = {}
    if imdb_id:
        ids['imdb'] = imdb_id
    if tmdb_id:
        ids['tmdb'] = int(tmdb_id) if str(tmdb_id).isdigit() else tmdb_id
    if not ids:
        return
    _post('/scrobble/stop', _scrobble_payload(media_type, ids, season, episode, progress))


# ---------- History sync ----------

def get_watched_movies():
    """Return a set of IMDB ids of movies the user has marked as watched on Trakt."""
    data = _get('/sync/watched/movies') or []
    out = set()
    for it in data:
        ids = (it.get('movie') or {}).get('ids') or {}
        if ids.get('imdb'):
            out.add(ids['imdb'])
        if ids.get('tmdb'):
            out.add('tmdb:%s' % ids['tmdb'])
    return out


def get_watched_shows():
    """Return dict { imdb_or_tmdb_key: { season: set(episodes_watched) } }."""
    data = _get('/sync/watched/shows') or []
    out = {}
    for it in data:
        show_ids = (it.get('show') or {}).get('ids') or {}
        key = show_ids.get('imdb') or ('tmdb:%s' % show_ids['tmdb']) if show_ids.get('tmdb') else None
        if not key:
            continue
        seasons = {}
        for s in it.get('seasons', []):
            sn = s.get('number')
            seasons[sn] = set(e.get('number') for e in s.get('episodes', []) if e.get('number'))
        out[key] = seasons
    return out


def sync_history():
    """Pull Trakt watched lists and persist to addon-local watched store."""
    if not is_authenticated():
        notify('Trakt: not authenticated')
        return
    from . import kodi_db as KDB
    notify('Trakt: syncing watched history...', time=2000)
    movies = get_watched_movies()
    shows = get_watched_shows()
    KDB.bulk_mark_watched_movies(movies)
    KDB.bulk_mark_watched_episodes(shows)

    # Also pull active resume points so Continue Watching is populated.
    pb_movies = _get('/sync/playback/movies') or []
    pb_eps = _get('/sync/playback/episodes') or []
    KDB.bulk_record_resume_movies(pb_movies)
    KDB.bulk_record_resume_episodes(pb_eps)

    notify('Trakt: synced %d movies, %d shows, %d resume points'
           % (len(movies), len(shows), len(pb_movies) + len(pb_eps)))


# ---------- Add / remove from lists ----------

def _ids_payload(media_type, tmdb_id=None, imdb_id=None):
    ids = {}
    if imdb_id:
        ids['imdb'] = imdb_id
    if tmdb_id:
        ids['tmdb'] = int(tmdb_id) if str(tmdb_id).isdigit() else tmdb_id
    if not ids:
        return None
    key = 'movies' if media_type == 'movie' else 'shows'
    return {key: [{'ids': ids}]}


def add_to_list(list_name, media_type, tmdb_id=None, imdb_id=None):
    """list_name: 'watchlist' | 'collection' | 'favorites'"""
    if not is_authenticated():
        notify('Trakt: not authenticated')
        return False
    payload = _ids_payload(media_type, tmdb_id=tmdb_id, imdb_id=imdb_id)
    if not payload:
        return False
    if list_name == 'favorites':
        path = '/users/me/favorites'
    else:
        path = '/sync/%s' % list_name
    return bool(_post(path, payload))


def remove_from_list(list_name, media_type, tmdb_id=None, imdb_id=None):
    if not is_authenticated():
        notify('Trakt: not authenticated')
        return False
    payload = _ids_payload(media_type, tmdb_id=tmdb_id, imdb_id=imdb_id)
    if not payload:
        return False
    if list_name == 'favorites':
        path = '/users/me/favorites/remove'
    else:
        path = '/sync/%s/remove' % list_name
    return bool(_post(path, payload))
