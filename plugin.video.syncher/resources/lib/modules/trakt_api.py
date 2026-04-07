# -*- coding: utf-8 -*-
"""Syncher - Trakt API integration"""

import json
import time
from resources.lib.modules import control
from resources.lib.modules import client

def _headers(auth=False):
    h = {
        'Content-Type': 'application/json',
        'trakt-api-key': control.TRAKT_KEY,
        'trakt-api-version': '2'
    }
    if auth:
        token = control.setting('trakt.token')
        if token:
            h['Authorization'] = 'Bearer %s' % token
    return h

def call(path, post=None, auth=False):
    url = control.TRAKT_BASE + path
    h = _headers(auth)

    if auth and control.setting('trakt.token'):
        result = client.request(url, post=json.dumps(post) if post else None, headers=h)
        if result is None:
            # Try token refresh
            refreshed = _refresh_token()
            if refreshed:
                h['Authorization'] = 'Bearer %s' % control.setting('trakt.token')
                result = client.request(url, post=json.dumps(post) if post else None, headers=h)
        if result:
            try:
                return json.loads(result)
            except:
                return result
        return None

    result = client.request(url, post=json.dumps(post) if post else None, headers=h)
    if result:
        try:
            return json.loads(result)
        except:
            return result
    return None

def _refresh_token():
    try:
        refresh = control.setting('trakt.refresh')
        if not refresh:
            return False
        post = {
            'client_id': control.TRAKT_KEY,
            'client_secret': control.TRAKT_SECRET,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'refresh_token',
            'refresh_token': refresh
        }
        result = client.request_json(control.TRAKT_BASE + '/oauth/token', post=post,
                                      headers={'Content-Type': 'application/json'})
        if result and 'access_token' in result:
            control.set_setting('trakt.token', result['access_token'])
            control.set_setting('trakt.refresh', result['refresh_token'])
            return True
    except:
        pass
    return False

def auth():
    try:
        if get_credentials():
            if control.yesnoDialog('Already authorized as [COLOR skyblue]%s[/COLOR]\nDo you want to reset Trakt authorization?' % control.setting('trakt.user')):
                control.set_setting('trakt.user', '')
                control.set_setting('trakt.token', '')
                control.set_setting('trakt.refresh', '')
                control.infoDialog('Trakt authorization cleared')
            return

        result = call('/oauth/device/code', post={'client_id': control.TRAKT_KEY})
        if not result:
            control.infoDialog('Failed to get Trakt device code')
            return

        verification_url = result['verification_url']
        user_code = result['user_code']
        device_code = result['device_code']
        expires_in = int(result['expires_in'])
        interval = int(result['interval'])

        dp = control.progressDialog()
        dp.create('Trakt Authorization',
                   'Go to: [COLOR skyblue]%s[/COLOR]\nEnter code: [COLOR skyblue]%s[/COLOR]' % (verification_url, user_code))

        for i in range(0, expires_in):
            if dp.iscanceled():
                break
            time.sleep(1)
            if not float(i) % interval == 0:
                continue
            try:
                r = call('/oauth/device/token', post={
                    'client_id': control.TRAKT_KEY,
                    'client_secret': control.TRAKT_SECRET,
                    'code': device_code
                })
                if r and 'access_token' in r:
                    token = r['access_token']
                    refresh = r['refresh_token']

                    # Get username
                    h = _headers()
                    h['Authorization'] = 'Bearer %s' % token
                    user_result = client.request_json(control.TRAKT_BASE + '/users/me', headers=h)
                    username = user_result.get('username', '') if user_result else ''

                    control.set_setting('trakt.user', username)
                    control.set_setting('trakt.token', token)
                    control.set_setting('trakt.refresh', refresh)

                    dp.close()
                    control.infoDialog('Trakt authorized as: %s' % username)
                    return
            except:
                pass

        try:
            dp.close()
        except:
            pass
    except Exception as e:
        control.log('Trakt auth error: %s' % e)
        try:
            dp.close()
        except:
            pass

def get_credentials():
    user = control.setting('trakt.user').strip()
    token = control.setting('trakt.token')
    return bool(user and token)

def get_movie_list(path, page=1):
    """Get a list of movies from a Trakt endpoint"""
    sep = '&' if '?' in path else '?'
    url = '%s%slimit=20&page=%s&extended=full' % (path, sep, page)
    result = call(url)
    if not result:
        return [], ''

    items = []
    for entry in result:
        movie = entry.get('movie', entry)
        if not movie.get('ids'):
            continue
        items.append(_parse_movie(movie))

    # Next page
    next_page = ''
    if len(result) >= 20:
        next_page = '%s%slimit=20&page=%s' % (path, sep, page + 1)

    return items, next_page

def get_show_list(path, page=1):
    """Get a list of TV shows from a Trakt endpoint"""
    sep = '&' if '?' in path else '?'
    url = '%s%slimit=20&page=%s&extended=full' % (path, sep, page)
    result = call(url)
    if not result:
        return [], ''

    items = []
    for entry in result:
        show = entry.get('show', entry)
        if not show.get('ids'):
            continue
        items.append(_parse_show(show))

    next_page = ''
    if len(result) >= 20:
        next_page = '%s%slimit=20&page=%s' % (path, sep, page + 1)

    return items, next_page

def get_season_list(imdb, tvdb):
    """Get seasons for a show"""
    result = call('/shows/%s/seasons?extended=full' % imdb)
    if not result:
        return []
    seasons = []
    for s in result:
        if s.get('number', -1) == 0:
            continue  # skip specials
        seasons.append({
            'season': str(s['number']),
            'title': s.get('title', 'Season %s' % s['number']),
            'episodes': str(s.get('episode_count', 0)),
            'premiered': s.get('first_aired', ''),
            'rating': str(s.get('rating', 0)),
            'plot': s.get('overview', ''),
        })
    return seasons

def get_episode_list(imdb, season):
    """Get episodes for a show season"""
    result = call('/shows/%s/seasons/%s?extended=full' % (imdb, season))
    if not result:
        return []
    episodes = []
    for ep in result:
        episodes.append({
            'season': str(ep.get('season', season)),
            'episode': str(ep['number']),
            'title': ep.get('title', 'Episode %s' % ep['number']),
            'premiered': ep.get('first_aired', ''),
            'rating': str(ep.get('rating', 0)),
            'votes': str(ep.get('votes', 0)),
            'plot': ep.get('overview', ''),
            'runtime': str(ep.get('runtime', 0)),
        })
    return episodes

def search_movies(query):
    result = call('/search/movie?query=%s&extended=full&limit=40' % query)
    if not result:
        return []
    items = []
    for entry in result:
        movie = entry.get('movie')
        if movie and movie.get('ids'):
            items.append(_parse_movie(movie))
    return items

def search_shows(query):
    result = call('/search/show?query=%s&extended=full&limit=40' % query)
    if not result:
        return []
    items = []
    for entry in result:
        show = entry.get('show')
        if show and show.get('ids'):
            items.append(_parse_show(show))
    return items

def _parse_movie(m):
    ids = m.get('ids', {})
    imdb = ids.get('imdb', '')
    if imdb and not imdb.startswith('tt'):
        imdb = 'tt' + imdb
    return {
        'title': m.get('title', ''),
        'year': str(m.get('year', '')),
        'imdb': imdb or '0',
        'tmdb': str(ids.get('tmdb', '0')),
        'genre': ' / '.join([g.title() for g in m.get('genres', [])]),
        'rating': str(m.get('rating', '0')),
        'votes': str(m.get('votes', '0')),
        'mpaa': m.get('certification', ''),
        'plot': m.get('overview', ''),
        'duration': str(m.get('runtime', '0')),
        'premiered': m.get('released', ''),
        'poster': '0',
        'fanart': '0',
        'banner': '0',
        'mediatype': 'movie',
    }

def _parse_show(s):
    ids = s.get('ids', {})
    imdb = ids.get('imdb', '')
    if imdb and not imdb.startswith('tt'):
        imdb = 'tt' + imdb
    return {
        'title': s.get('title', ''),
        'year': str(s.get('year', '')),
        'imdb': imdb or '0',
        'tmdb': str(ids.get('tmdb', '0')),
        'tvdb': str(ids.get('tvdb', '0')),
        'genre': ' / '.join([g.title() for g in s.get('genres', [])]),
        'rating': str(s.get('rating', '0')),
        'votes': str(s.get('votes', '0')),
        'mpaa': s.get('certification', ''),
        'plot': s.get('overview', ''),
        'duration': str(s.get('runtime', '0')),
        'premiered': s.get('first_aired', ''),
        'studio': s.get('network', ''),
        'poster': '0',
        'fanart': '0',
        'banner': '0',
        'mediatype': 'tvshow',
    }
