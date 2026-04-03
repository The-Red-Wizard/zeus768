# -*- coding: utf-8 -*-
"""TMDB metadata helper. Native urllib only."""
import json
import ssl
import sys
import urllib.request
import urllib.error
from urllib.parse import quote_plus
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

ADDON = xbmcaddon.Addon()
SSL_CTX = ssl._create_unverified_context()
DEFAULT_TMDB_KEY = '8265bd1679663a7ea12ac168da84d2e8'


def _key():
    user_key = ADDON.getSetting('tmdb_api_key')
    return user_key if user_key and len(user_key) > 10 else DEFAULT_TMDB_KEY


def _get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'TraktPlayer/2.0'})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        xbmc.log('TMDB error: %s' % str(e), xbmc.LOGERROR)
        return {}


def prompt_for_api_key():
    if ADDON.getSetting('tmdb_key_prompted') != 'true':
        dlg = xbmcgui.Dialog()
        result = dlg.yesno(
            'TMDB API Key',
            'A default TMDB key is used. For reliability, get your own free key from themoviedb.org\n\nAdd your own key now?',
            nolabel='Use Default', yeslabel='Add My Key')
        if result:
            kb = xbmc.Keyboard('', 'Enter your TMDB API Key')
            kb.doModal()
            if kb.isConfirmed():
                key = kb.getText().strip()
                if key and len(key) > 10:
                    ADDON.setSetting('tmdb_api_key', key)
                    xbmcgui.Dialog().notification('Success', 'TMDB key saved', xbmcgui.NOTIFICATION_INFO)
        ADDON.setSetting('tmdb_key_prompted', 'true')


def get_details(tmdb_id, media_type='movie'):
    if not tmdb_id:
        return {'overview': '', 'poster': '', 'backdrop': '', 'runtime': 0, 'rating': 0, 'genres': [], 'year': ''}
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    data = _get_json('https://api.themoviedb.org/3/%s/%s?api_key=%s' % (endpoint, tmdb_id, _key()))
    if not data:
        return {'overview': '', 'poster': '', 'backdrop': '', 'runtime': 0, 'rating': 0, 'genres': [], 'year': ''}
    poster = ('https://image.tmdb.org/t/p/w500' + data['poster_path']) if data.get('poster_path') else ''
    backdrop = ('https://image.tmdb.org/t/p/original' + data['backdrop_path']) if data.get('backdrop_path') else ''
    return {
        'overview': data.get('overview', ''),
        'poster': poster,
        'backdrop': backdrop,
        'runtime': data.get('runtime', 0) or 0,
        'rating': data.get('vote_average', 0),
        'genres': [g['name'] for g in data.get('genres', [])],
        'year': (data.get('release_date') or data.get('first_air_date', ''))[:4]
    }


def get_genres(media_type):
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    data = _get_json('https://api.themoviedb.org/3/genre/%s/list?api_key=%s' % (endpoint, _key()))
    handle = int(sys.argv[1])
    for g in data.get('genres', []):
        url = '%s?action=trakt_list&path=%ss/popular&genre=%s&media_type=%s' % (
            sys.argv[0], endpoint, g['id'], 'movie' if media_type == 'movie' else 'show')
        xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(label=g['name']), isFolder=True)
    xbmcplugin.endOfDirectory(handle)


def get_tv_seasons(tmdb_id):
    data = _get_json('https://api.themoviedb.org/3/tv/%s?api_key=%s' % (tmdb_id, _key()))
    return data.get('seasons', [])


def get_season_episodes(tmdb_id, season_number):
    data = _get_json('https://api.themoviedb.org/3/tv/%s/season/%s?api_key=%s' % (tmdb_id, season_number, _key()))
    return data.get('episodes', [])
