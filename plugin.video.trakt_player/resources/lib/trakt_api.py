# -*- coding: utf-8 -*-
"""Trakt API - Browse lists, seasons, episodes. Native urllib. No search."""
import json
import ssl
import sys
import urllib.request
import urllib.error
from urllib.parse import urlencode, quote_plus
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from . import trakt_auth
from . import tmdb

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
SSL_CTX = ssl._create_unverified_context()

CLIENT_ID = trakt_auth.CLIENT_ID


def _headers():
    h = {
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': CLIENT_ID
    }
    token = trakt_auth.get_token()
    if token:
        h['Authorization'] = 'Bearer ' + token
    return h


def _get(url):
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, []


def get_list(path, media_type='movie'):
    needs_auth = 'sync/' in path or 'users/' in path
    if needs_auth and not trakt_auth.is_authorized():
        xbmcgui.Dialog().notification('Trakt', 'Please authorize Trakt first', xbmcgui.NOTIFICATION_WARNING)
        trakt_auth.authorize()
        return

    url = 'https://api.trakt.tv/' + path + '?extended=full&limit=50'
    xbmc.log('Trakt API: ' + url, xbmc.LOGINFO)

    status, data = _get(url)

    if status == 401:
        if trakt_auth.refresh_token():
            status, data = _get(url)
        else:
            xbmcgui.Dialog().notification('Trakt', 'Session expired. Re-authorize.', xbmcgui.NOTIFICATION_WARNING)
            trakt_auth.authorize()
            return

    if status != 200:
        xbmcgui.Dialog().notification('Trakt', 'API error: %d' % status, xbmcgui.NOTIFICATION_ERROR)
        return

    if not data:
        xbmcgui.Dialog().notification('Trakt', 'No results', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    for item in data:
        if media_type == 'show':
            content = item.get('show', item)
        else:
            content = item.get('movie', item)

        title = content.get('title', 'Unknown')
        year = content.get('year', '')
        ids = content.get('ids', {})
        tmdb_id = ids.get('tmdb')
        imdb_id = ids.get('imdb', '')

        meta = tmdb.get_details(tmdb_id, 'movie' if media_type == 'movie' else 'tv')

        label = '%s (%s)' % (title, year) if year else title
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': meta.get('poster', ''),
            'fanart': meta.get('backdrop', ''),
            'thumb': meta.get('poster', '')
        })

        info = {
            'title': title,
            'year': year,
            'plot': meta.get('overview', content.get('overview', '')),
            'rating': meta.get('rating', content.get('rating', 0)),
            'genre': ', '.join(meta.get('genres', []))
        }

        if media_type == 'movie':
            info['mediatype'] = 'movie'
            info['duration'] = meta.get('runtime', 0) * 60
            li.setInfo('video', info)
            li.setProperty('IsPlayable', 'true')
            play_url = '%s?action=play&title=%s&year=%s&imdb_id=%s' % (
                sys.argv[0], quote_plus(title), year, imdb_id)
            xbmcplugin.addDirectoryItem(HANDLE, play_url, li, False)
        else:
            info['mediatype'] = 'tvshow'
            li.setInfo('video', info)
            show_url = '%s?action=show_seasons&tmdb_id=%s&title=%s' % (
                sys.argv[0], tmdb_id, quote_plus(title))
            xbmcplugin.addDirectoryItem(HANDLE, show_url, li, True)

    xbmcplugin.setContent(HANDLE, 'movies' if media_type == 'movie' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)


def show_seasons(tmdb_id, show_title):
    seasons = tmdb.get_tv_seasons(tmdb_id)
    for season in seasons:
        season_num = season.get('season_number', 0)
        if season_num == 0:
            continue
        name = season.get('name', 'Season %d' % season_num)
        poster = ('https://image.tmdb.org/t/p/w500' + season['poster_path']) if season.get('poster_path') else ''
        li = xbmcgui.ListItem(label=name)
        li.setArt({'poster': poster, 'thumb': poster})
        li.setInfo('video', {'title': name, 'season': season_num})
        url = '%s?action=show_episodes&tmdb_id=%s&season=%d&title=%s' % (
            sys.argv[0], tmdb_id, season_num, quote_plus(show_title))
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)
    xbmcplugin.setContent(HANDLE, 'seasons')
    xbmcplugin.endOfDirectory(HANDLE)


def show_episodes(tmdb_id, season_number, show_title):
    episodes = tmdb.get_season_episodes(tmdb_id, season_number)
    for ep in episodes:
        ep_num = ep.get('episode_number', 0)
        name = ep.get('name', 'Episode %d' % ep_num)
        still = ('https://image.tmdb.org/t/p/w500' + ep['still_path']) if ep.get('still_path') else ''
        label = '%d. %s' % (ep_num, name)
        li = xbmcgui.ListItem(label=label)
        li.setArt({'thumb': still, 'fanart': still})
        li.setInfo('video', {
            'title': name,
            'episode': ep_num,
            'season': int(season_number),
            'plot': ep.get('overview', ''),
            'mediatype': 'episode'
        })
        li.setProperty('IsPlayable', 'true')
        url = '%s?action=play_episode&title=%s&season=%s&episode=%d&imdb_id=' % (
            sys.argv[0], quote_plus(show_title), season_number, ep_num)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, False)
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)
