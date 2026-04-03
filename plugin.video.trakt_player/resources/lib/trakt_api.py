# -*- coding: utf-8 -*-
"""Trakt API - Full-featured: browse, recommendations, calendar, history, scrobble, ratings, related. Native urllib."""
import json
import ssl
import sys
import time
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
SSL_CTX = ssl._create_unverified_context()
CLIENT_ID = trakt_auth.CLIENT_ID


def _handle():
    try:
        return int(sys.argv[1])
    except (IndexError, ValueError):
        return -1
BASE = 'https://api.trakt.tv'


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
    except Exception as e:
        xbmc.log('Trakt GET error: %s' % str(e), xbmc.LOGERROR)
        return 0, []


def _post(url, data):
    hdrs = _headers()
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers=hdrs, method='POST')
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except Exception:
            return e.code, {}
    except Exception as e:
        xbmc.log('Trakt POST error: %s' % str(e), xbmc.LOGERROR)
        return 0, {}


def _delete(url):
    req = urllib.request.Request(url, headers=_headers(), method='DELETE')
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def _authed_get(url, label=''):
    """GET with auto-refresh on 401."""
    status, data = _get(url)
    if status == 401:
        if trakt_auth.refresh_token():
            status, data = _get(url)
        else:
            xbmcgui.Dialog().notification('Trakt', 'Session expired. Re-authorize.', xbmcgui.NOTIFICATION_WARNING)
            return 0, []
    if status != 200:
        if label:
            xbmcgui.Dialog().notification('Trakt', '%s error: %d' % (label, status), xbmcgui.NOTIFICATION_ERROR)
        return status, []
    return status, data


def _require_auth():
    if not trakt_auth.is_authorized():
        xbmcgui.Dialog().notification('Trakt', 'Please authorize Trakt first', xbmcgui.NOTIFICATION_WARNING)
        return False
    return True


# ── Context menu helpers ──────────────────────────────────────────────────

def _add_context_menu(li, media_type, trakt_id, imdb_id=''):
    """Add Rate + More Like This + Add to List to context menu."""
    ctx = []
    if trakt_id:
        ctx.append(('Rate on Trakt',
                     'RunPlugin(plugin://plugin.video.trakt_player/?action=rate&media_type=%s&trakt_id=%s)' % (media_type, trakt_id)))
        ctx.append(('More Like This',
                     'Container.Update(plugin://plugin.video.trakt_player/?action=related&media_type=%s&trakt_id=%s)' % (media_type, trakt_id)))
    if imdb_id:
        ctx.append(('Add to Watchlist',
                     'RunPlugin(plugin://plugin.video.trakt_player/?action=add_watchlist&media_type=%s&imdb_id=%s)' % (media_type, imdb_id)))
        ctx.append(('Add to List...',
                     'RunPlugin(plugin://plugin.video.trakt_player/?action=add_to_list&media_type=%s&imdb_id=%s)' % (media_type, imdb_id)))
    if ctx:
        li.addContextMenuItems(ctx)


# ── List rendering ────────────────────────────────────────────────────────

def _render_items(data, media_type, key=None):
    """Render a list of Trakt items. key = wrapper key like 'movie', 'show', or None."""
    if not data:
        xbmcgui.Dialog().notification('Trakt', 'No results', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(_handle())
        return

    for item in data:
        if key:
            content = item.get(key, item)
        elif media_type == 'show':
            content = item.get('show', item)
        else:
            content = item.get('movie', item)

        title = content.get('title', 'Unknown')
        year = content.get('year', '')
        ids = content.get('ids', {})
        tmdb_id = ids.get('tmdb')
        imdb_id = ids.get('imdb', '')
        trakt_id = ids.get('trakt', '')

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

        _add_context_menu(li, media_type, trakt_id, imdb_id)

        if media_type == 'movie':
            info['mediatype'] = 'movie'
            info['duration'] = meta.get('runtime', 0) * 60
            li.setInfo('video', info)
            li.setProperty('IsPlayable', 'true')
            play_url = '%s?action=play&title=%s&year=%s&imdb_id=%s' % (
                sys.argv[0], quote_plus(title), year, imdb_id)
            xbmcplugin.addDirectoryItem(_handle(), play_url, li, False)
        else:
            info['mediatype'] = 'tvshow'
            li.setInfo('video', info)
            show_url = '%s?action=show_seasons&tmdb_id=%s&title=%s&imdb_id=%s' % (
                sys.argv[0], tmdb_id, quote_plus(title), imdb_id)
            xbmcplugin.addDirectoryItem(_handle(), show_url, li, True)

    content_type = 'movies' if media_type == 'movie' else 'tvshows'
    xbmcplugin.setContent(_handle(), content_type)
    xbmcplugin.endOfDirectory(_handle())


# ── Browse: Lists ─────────────────────────────────────────────────────────

def get_list(path, media_type='movie'):
    needs_auth = 'sync/' in path or 'users/' in path or 'calendars/' in path or 'recommendations' in path
    if needs_auth and not _require_auth():
        trakt_auth.authorize()
        return

    url = '%s/%s?extended=full&limit=50' % (BASE, path)
    xbmc.log('Trakt API: %s' % url, xbmc.LOGINFO)
    status, data = _authed_get(url, 'List')
    if status != 200:
        return
    _render_items(data, media_type)


# ── Recommendations ───────────────────────────────────────────────────────

def get_recommendations(media_type='movie'):
    if not _require_auth():
        return
    endpoint = 'movies' if media_type == 'movie' else 'shows'
    url = '%s/recommendations/%s?extended=full&limit=40' % (BASE, endpoint)
    status, data = _authed_get(url, 'Recommendations')
    if status != 200:
        return
    # Recommendations return items directly (no wrapper key)
    _render_items(data, media_type, key=None)


# ── Calendar ──────────────────────────────────────────────────────────────

def get_calendar():
    if not _require_auth():
        return
    today = time.strftime('%Y-%m-%d')
    url = '%s/calendars/my/shows/%s/30?extended=full' % (BASE, today)
    status, data = _authed_get(url, 'Calendar')
    if status != 200:
        return

    if not data:
        xbmcgui.Dialog().notification('Trakt', 'No upcoming episodes', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(_handle())
        return

    for item in data:
        show = item.get('show', {})
        episode = item.get('episode', {})
        air_date = item.get('first_aired', '')[:10]
        show_title = show.get('title', 'Unknown')
        ep_title = episode.get('title', '')
        season = episode.get('season', 0)
        ep_num = episode.get('number', 0)
        ids = show.get('ids', {})
        tmdb_id = ids.get('tmdb')
        imdb_id = ids.get('imdb', '')

        label = '[%s] %s - S%02dE%02d - %s' % (air_date, show_title, season, ep_num, ep_title)
        li = xbmcgui.ListItem(label=label)

        meta = tmdb.get_details(tmdb_id, 'tv')
        li.setArt({'poster': meta.get('poster', ''), 'fanart': meta.get('backdrop', ''), 'thumb': meta.get('poster', '')})
        li.setInfo('video', {
            'title': ep_title, 'tvshowtitle': show_title,
            'season': season, 'episode': ep_num,
            'plot': episode.get('overview', ''), 'mediatype': 'episode'
        })
        li.setProperty('IsPlayable', 'true')

        url = '%s?action=play_episode&title=%s&season=%d&episode=%d&imdb_id=%s' % (
            sys.argv[0], quote_plus(show_title), season, ep_num, imdb_id)
        xbmcplugin.addDirectoryItem(_handle(), url, li, False)

    xbmcplugin.setContent(_handle(), 'episodes')
    xbmcplugin.endOfDirectory(_handle())


# ── History ───────────────────────────────────────────────────────────────

def get_history(media_type='movie'):
    if not _require_auth():
        return
    endpoint = 'movies' if media_type == 'movie' else 'episodes'
    url = '%s/sync/history/%s?extended=full&limit=50' % (BASE, endpoint)
    status, data = _authed_get(url, 'History')
    if status != 200:
        return

    if media_type == 'movie':
        _render_items(data, 'movie')
    else:
        # Episodes have a different structure
        if not data:
            xbmcgui.Dialog().notification('Trakt', 'No history', xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(_handle())
            return
        for item in data:
            show = item.get('show', {})
            episode = item.get('episode', {})
            show_title = show.get('title', 'Unknown')
            ep_title = episode.get('title', '')
            season = episode.get('season', 0)
            ep_num = episode.get('number', 0)
            ids = show.get('ids', {})
            tmdb_id = ids.get('tmdb')
            imdb_id = ids.get('imdb', '')
            watched_at = item.get('watched_at', '')[:10]

            label = '[%s] %s - S%02dE%02d - %s' % (watched_at, show_title, season, ep_num, ep_title)
            li = xbmcgui.ListItem(label=label)
            meta = tmdb.get_details(tmdb_id, 'tv')
            li.setArt({'poster': meta.get('poster', ''), 'fanart': meta.get('backdrop', '')})
            li.setInfo('video', {
                'title': ep_title, 'tvshowtitle': show_title,
                'season': season, 'episode': ep_num, 'mediatype': 'episode'
            })
            li.setProperty('IsPlayable', 'true')
            url = '%s?action=play_episode&title=%s&season=%d&episode=%d&imdb_id=%s' % (
                sys.argv[0], quote_plus(show_title), season, ep_num, imdb_id)
            xbmcplugin.addDirectoryItem(_handle(), url, li, False)

        xbmcplugin.setContent(_handle(), 'episodes')
        xbmcplugin.endOfDirectory(_handle())


# ── Anticipated ───────────────────────────────────────────────────────────

def get_anticipated(media_type='movie'):
    endpoint = 'movies' if media_type == 'movie' else 'shows'
    url = '%s/%s/anticipated?extended=full&limit=40' % (BASE, endpoint)
    status, data = _authed_get(url, 'Anticipated')
    if status != 200:
        return
    _render_items(data, media_type)


# ── Popular Community Lists ───────────────────────────────────────────────

def get_popular_lists():
    url = '%s/lists/popular?limit=30' % BASE
    status, data = _authed_get(url, 'Lists')
    if status != 200:
        return

    if not data:
        xbmcgui.Dialog().notification('Trakt', 'No lists found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(_handle())
        return

    for item in data:
        lst = item if 'name' in item else item.get('list', item)
        name = lst.get('name', 'Unknown List')
        desc = lst.get('description', '')
        item_count = lst.get('item_count', 0)
        likes = lst.get('likes', item.get('like_count', 0))
        user = lst.get('user', {}).get('ids', {}).get('slug', '')
        list_ids = lst.get('ids', {})
        list_trakt = list_ids.get('trakt', '')
        list_slug = list_ids.get('slug', '')

        label = '%s (%d items, %d likes)' % (name, item_count, likes)
        li = xbmcgui.ListItem(label=label)
        li.setInfo('video', {'title': name, 'plot': desc})

        url = '%s?action=list_items&user=%s&list_slug=%s' % (
            sys.argv[0], quote_plus(user), quote_plus(list_slug))
        xbmcplugin.addDirectoryItem(_handle(), url, li, True)

    xbmcplugin.endOfDirectory(_handle())


def get_list_items(user, list_slug):
    """Fetch items from a specific Trakt user list."""
    url = '%s/users/%s/lists/%s/items?extended=full&limit=100' % (BASE, user, list_slug)
    status, data = _authed_get(url, 'List Items')
    if status != 200:
        return

    if not data:
        xbmcgui.Dialog().notification('Trakt', 'Empty list', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(_handle())
        return

    for item in data:
        item_type = item.get('type', '')
        if item_type == 'movie':
            content = item.get('movie', {})
            media_type = 'movie'
        elif item_type == 'show':
            content = item.get('show', {})
            media_type = 'show'
        else:
            continue

        title = content.get('title', 'Unknown')
        year = content.get('year', '')
        ids = content.get('ids', {})
        tmdb_id = ids.get('tmdb')
        imdb_id = ids.get('imdb', '')
        trakt_id = ids.get('trakt', '')

        meta = tmdb.get_details(tmdb_id, 'movie' if media_type == 'movie' else 'tv')
        label = '%s (%s)' % (title, year) if year else title
        li = xbmcgui.ListItem(label=label)
        li.setArt({'poster': meta.get('poster', ''), 'fanart': meta.get('backdrop', ''), 'thumb': meta.get('poster', '')})
        info = {
            'title': title, 'year': year,
            'plot': meta.get('overview', content.get('overview', '')),
            'rating': meta.get('rating', 0)
        }
        _add_context_menu(li, media_type, trakt_id, imdb_id)

        if media_type == 'movie':
            info['mediatype'] = 'movie'
            li.setInfo('video', info)
            li.setProperty('IsPlayable', 'true')
            play_url = '%s?action=play&title=%s&year=%s&imdb_id=%s' % (
                sys.argv[0], quote_plus(title), year, imdb_id)
            xbmcplugin.addDirectoryItem(_handle(), play_url, li, False)
        else:
            info['mediatype'] = 'tvshow'
            li.setInfo('video', info)
            show_url = '%s?action=show_seasons&tmdb_id=%s&title=%s&imdb_id=%s' % (
                sys.argv[0], tmdb_id, quote_plus(title), imdb_id)
            xbmcplugin.addDirectoryItem(_handle(), show_url, li, True)

    xbmcplugin.setContent(_handle(), 'videos')
    xbmcplugin.endOfDirectory(_handle())


# ── Related Content ───────────────────────────────────────────────────────

def get_related(media_type, trakt_id):
    endpoint = 'movies' if media_type == 'movie' else 'shows'
    url = '%s/%s/%s/related?extended=full&limit=20' % (BASE, endpoint, trakt_id)
    status, data = _authed_get(url, 'Related')
    if status != 200:
        return
    # Related returns items directly (no wrapper)
    _render_items(data, media_type, key=None)


# ── Continue Watching ─────────────────────────────────────────────────────

def get_playback_progress():
    """Show items the user started but didn't finish."""
    if not _require_auth():
        return
    url = '%s/sync/playback?extended=full&limit=50' % BASE
    status, data = _authed_get(url, 'Continue Watching')
    if status != 200:
        return

    if not data:
        xbmcgui.Dialog().notification('Trakt', 'Nothing to continue', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(_handle())
        return

    for item in data:
        item_type = item.get('type', '')
        progress = item.get('progress', 0)
        paused_at = item.get('paused_at', '')[:10]

        if item_type == 'movie':
            content = item.get('movie', {})
            title = content.get('title', 'Unknown')
            year = content.get('year', '')
            ids = content.get('ids', {})
            tmdb_id = ids.get('tmdb')
            imdb_id = ids.get('imdb', '')
            trakt_id = ids.get('trakt', '')

            meta = tmdb.get_details(tmdb_id, 'movie')
            label = '[%.0f%%] %s (%s)' % (progress, title, year)
            li = xbmcgui.ListItem(label=label)
            li.setArt({'poster': meta.get('poster', ''), 'fanart': meta.get('backdrop', '')})
            li.setInfo('video', {'title': title, 'year': year, 'mediatype': 'movie',
                                 'plot': meta.get('overview', '')})
            li.setProperty('IsPlayable', 'true')
            _add_context_menu(li, 'movie', trakt_id, imdb_id)
            play_url = '%s?action=play&title=%s&year=%s&imdb_id=%s' % (
                sys.argv[0], quote_plus(title), year, imdb_id)
            xbmcplugin.addDirectoryItem(_handle(), play_url, li, False)

        elif item_type == 'episode':
            show = item.get('show', {})
            episode = item.get('episode', {})
            show_title = show.get('title', 'Unknown')
            ep_title = episode.get('title', '')
            season = episode.get('season', 0)
            ep_num = episode.get('number', 0)
            ids = show.get('ids', {})
            tmdb_id = ids.get('tmdb')
            imdb_id = ids.get('imdb', '')

            meta = tmdb.get_details(tmdb_id, 'tv')
            label = '[%.0f%%] %s - S%02dE%02d - %s' % (progress, show_title, season, ep_num, ep_title)
            li = xbmcgui.ListItem(label=label)
            li.setArt({'poster': meta.get('poster', ''), 'fanart': meta.get('backdrop', '')})
            li.setInfo('video', {
                'title': ep_title, 'tvshowtitle': show_title,
                'season': season, 'episode': ep_num, 'mediatype': 'episode'
            })
            li.setProperty('IsPlayable', 'true')
            url = '%s?action=play_episode&title=%s&season=%d&episode=%d&imdb_id=%s' % (
                sys.argv[0], quote_plus(show_title), season, ep_num, imdb_id)
            xbmcplugin.addDirectoryItem(_handle(), url, li, False)

    xbmcplugin.setContent(_handle(), 'videos')
    xbmcplugin.endOfDirectory(_handle())


# ── Rating ────────────────────────────────────────────────────────────────

def rate_item(media_type, trakt_id):
    """Show rating dialog and submit to Trakt."""
    if not _require_auth():
        return
    ratings = ['1 - Awful', '2 - Terrible', '3 - Bad', '4 - Poor', '5 - Meh',
               '6 - Fair', '7 - Good', '8 - Great', '9 - Superb', '10 - Masterpiece']
    dlg = xbmcgui.Dialog()
    selected = dlg.select('Rate on Trakt', ratings)
    if selected < 0:
        return
    rating = selected + 1

    key = 'movies' if media_type == 'movie' else 'shows'
    body = {key: [{'ids': {'trakt': int(trakt_id)}, 'rating': rating}]}
    status, resp = _post('%s/sync/ratings' % BASE, body)
    if status in (200, 201):
        added = resp.get('added', {}).get(key, 0)
        if added:
            xbmcgui.Dialog().notification('Trakt', 'Rated %d/10' % rating, xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification('Trakt', 'Rating updated', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('Trakt', 'Rating failed', xbmcgui.NOTIFICATION_ERROR)


# ── Watchlist ─────────────────────────────────────────────────────────────

def add_to_watchlist(media_type, imdb_id):
    if not _require_auth():
        return
    key = 'movies' if media_type == 'movie' else 'shows'
    body = {key: [{'ids': {'imdb': imdb_id}}]}
    status, resp = _post('%s/sync/watchlist' % BASE, body)
    if status in (200, 201):
        xbmcgui.Dialog().notification('Trakt', 'Added to watchlist', xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('Trakt', 'Failed to add', xbmcgui.NOTIFICATION_ERROR)


# ── Scrobble ──────────────────────────────────────────────────────────────

def scrobble(action, media_type, imdb_id='', season=0, episode=0, progress=0.0):
    """Send scrobble start/pause/stop to Trakt. action = 'start', 'pause', or 'stop'."""
    if not trakt_auth.is_authorized():
        return False
    if media_type == 'movie':
        body = {'movie': {'ids': {'imdb': imdb_id}}, 'progress': progress}
    else:
        body = {
            'show': {'ids': {'imdb': imdb_id}},
            'episode': {'season': int(season), 'number': int(episode)},
            'progress': progress
        }
    url = '%s/scrobble/%s' % (BASE, action)
    status, _ = _post(url, body)
    xbmc.log('Scrobble %s: status=%d, type=%s, progress=%.1f' % (action, status, media_type, progress), xbmc.LOGINFO)
    return status in (200, 201)


# ── Seasons / Episodes ───────────────────────────────────────────────────

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
        xbmcplugin.addDirectoryItem(_handle(), url, li, True)
    xbmcplugin.setContent(_handle(), 'seasons')
    xbmcplugin.endOfDirectory(_handle())


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
            'title': name, 'episode': ep_num,
            'season': int(season_number),
            'plot': ep.get('overview', ''), 'mediatype': 'episode'
        })
        li.setProperty('IsPlayable', 'true')
        url = '%s?action=play_episode&title=%s&season=%s&episode=%d&imdb_id=' % (
            sys.argv[0], quote_plus(show_title), season_number, ep_num)
        xbmcplugin.addDirectoryItem(_handle(), url, li, False)
    xbmcplugin.setContent(_handle(), 'episodes')
    xbmcplugin.endOfDirectory(_handle())


# ── Friends Activity ──────────────────────────────────────────────────────

def get_friends():
    """Show list of Trakt friends with option to see what they're watching."""
    if not _require_auth():
        return
    url = '%s/users/me/friends?extended=full' % BASE
    status, data = _authed_get(url, 'Friends')
    if status != 200:
        return

    if not data:
        xbmcgui.Dialog().notification('Trakt', 'No friends found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(_handle())
        return

    for item in data:
        user = item.get('user', {})
        username = user.get('username', 'Unknown')
        name = user.get('name', username)
        slug = user.get('ids', {}).get('slug', username)
        avatar = user.get('images', {}).get('avatar', {}).get('full', '')
        joined = user.get('joined_at', '')[:10]

        label = '%s (@%s)' % (name, username) if name != username else '@%s' % username
        li = xbmcgui.ListItem(label=label)
        if avatar:
            li.setArt({'icon': avatar, 'thumb': avatar})
        li.setInfo('video', {'title': label, 'plot': 'Joined: %s' % joined})

        url = '%s?action=friend_activity&user=%s' % (sys.argv[0], quote_plus(slug))
        xbmcplugin.addDirectoryItem(_handle(), url, li, True)

    xbmcplugin.endOfDirectory(_handle())


def get_friend_activity(user_slug):
    """Show what a friend is watching and their recent activity."""
    # Check if currently watching
    url_watching = '%s/users/%s/watching?extended=full' % (BASE, user_slug)
    status, watching = _get(url_watching)

    items_added = False

    if status == 200 and watching:
        media_type = watching.get('type', '')
        if media_type == 'movie':
            content = watching.get('movie', {})
            title = content.get('title', 'Unknown')
            year = content.get('year', '')
            label = '[COLOR lime]NOW WATCHING:[/COLOR] %s (%s)' % (title, year)
            li = xbmcgui.ListItem(label=label)
            ids = content.get('ids', {})
            meta = tmdb.get_details(ids.get('tmdb'), 'movie')
            li.setArt({'poster': meta.get('poster', ''), 'fanart': meta.get('backdrop', '')})
            li.setInfo('video', {'title': title, 'year': year, 'mediatype': 'movie'})
            li.setProperty('IsPlayable', 'true')
            play_url = '%s?action=play&title=%s&year=%s&imdb_id=%s' % (
                sys.argv[0], quote_plus(title), year, ids.get('imdb', ''))
            xbmcplugin.addDirectoryItem(_handle(), play_url, li, False)
            items_added = True
        elif media_type == 'episode':
            show = watching.get('show', {})
            episode = watching.get('episode', {})
            label = '[COLOR lime]NOW WATCHING:[/COLOR] %s S%02dE%02d - %s' % (
                show.get('title', ''), episode.get('season', 0),
                episode.get('number', 0), episode.get('title', ''))
            li = xbmcgui.ListItem(label=label)
            ids = show.get('ids', {})
            meta = tmdb.get_details(ids.get('tmdb'), 'tv')
            li.setArt({'poster': meta.get('poster', ''), 'fanart': meta.get('backdrop', '')})
            li.setInfo('video', {'title': label, 'mediatype': 'episode'})
            li.setProperty('IsPlayable', 'true')
            play_url = '%s?action=play_episode&title=%s&season=%d&episode=%d&imdb_id=%s' % (
                sys.argv[0], quote_plus(show.get('title', '')),
                episode.get('season', 0), episode.get('number', 0), ids.get('imdb', ''))
            xbmcplugin.addDirectoryItem(_handle(), play_url, li, False)
            items_added = True

    # Recent watched history
    url_history = '%s/users/%s/history?limit=20&extended=full' % (BASE, user_slug)
    status, history = _get(url_history)
    if status == 200 and history:
        for item in history:
            item_type = item.get('type', '')
            watched_at = item.get('watched_at', '')[:10]
            if item_type == 'movie':
                content = item.get('movie', {})
                title = content.get('title', '')
                year = content.get('year', '')
                ids = content.get('ids', {})
                meta = tmdb.get_details(ids.get('tmdb'), 'movie')
                label = '[%s] %s (%s)' % (watched_at, title, year)
                li = xbmcgui.ListItem(label=label)
                li.setArt({'poster': meta.get('poster', ''), 'fanart': meta.get('backdrop', '')})
                li.setInfo('video', {'title': title, 'year': year, 'mediatype': 'movie'})
                li.setProperty('IsPlayable', 'true')
                play_url = '%s?action=play&title=%s&year=%s&imdb_id=%s' % (
                    sys.argv[0], quote_plus(title), year, ids.get('imdb', ''))
                xbmcplugin.addDirectoryItem(_handle(), play_url, li, False)
                items_added = True
            elif item_type == 'episode':
                show = item.get('show', {})
                ep = item.get('episode', {})
                ids = show.get('ids', {})
                meta = tmdb.get_details(ids.get('tmdb'), 'tv')
                label = '[%s] %s S%02dE%02d' % (watched_at, show.get('title', ''),
                                                  ep.get('season', 0), ep.get('number', 0))
                li = xbmcgui.ListItem(label=label)
                li.setArt({'poster': meta.get('poster', ''), 'fanart': meta.get('backdrop', '')})
                li.setInfo('video', {'title': label, 'mediatype': 'episode'})
                li.setProperty('IsPlayable', 'true')
                play_url = '%s?action=play_episode&title=%s&season=%d&episode=%d&imdb_id=%s' % (
                    sys.argv[0], quote_plus(show.get('title', '')),
                    ep.get('season', 0), ep.get('number', 0), ids.get('imdb', ''))
                xbmcplugin.addDirectoryItem(_handle(), play_url, li, False)
                items_added = True

    if not items_added:
        xbmcgui.Dialog().notification('Trakt', 'No activity for this friend', xbmcgui.NOTIFICATION_INFO)

    xbmcplugin.setContent(_handle(), 'videos')
    xbmcplugin.endOfDirectory(_handle())


# ── User Stats ────────────────────────────────────────────────────────────

def show_user_stats():
    """Display user watch stats in a dialog."""
    if not _require_auth():
        return
    url = '%s/users/me/stats' % BASE
    status, data = _authed_get(url, 'Stats')
    if status != 200 or not data:
        return

    movies = data.get('movies', {})
    episodes = data.get('episodes', {})
    shows = data.get('shows', {})
    network = data.get('network', {})
    ratings = data.get('ratings', {})

    movie_mins = movies.get('minutes', 0)
    movie_hrs = movie_mins // 60
    movie_days = movie_hrs // 24
    ep_mins = episodes.get('minutes', 0)
    ep_hrs = ep_mins // 60
    ep_days = ep_hrs // 24
    total_mins = movie_mins + ep_mins
    total_hrs = total_mins // 60
    total_days = total_hrs // 24

    lines = []
    lines.append('[B][COLOR skyblue]--- Your Trakt Stats ---[/COLOR][/B]\n')

    lines.append('[B]Movies[/B]')
    lines.append('  Watched: %d movies' % movies.get('watched', 0))
    lines.append('  Collected: %d' % movies.get('collected', 0))
    lines.append('  Ratings: %d' % movies.get('ratings', 0))
    lines.append('  Time: %d hours (%d days)' % (movie_hrs, movie_days))
    lines.append('')

    lines.append('[B]TV Shows[/B]')
    lines.append('  Shows Watched: %d' % shows.get('watched', 0))
    lines.append('  Episodes Watched: %d' % episodes.get('watched', 0))
    lines.append('  Collected: %d episodes' % episodes.get('collected', 0))
    lines.append('  Time: %d hours (%d days)' % (ep_hrs, ep_days))
    lines.append('')

    lines.append('[B]Total Watch Time[/B]')
    lines.append('  [COLOR lime]%d hours (%d days)[/COLOR]' % (total_hrs, total_days))
    lines.append('')

    lines.append('[B]Ratings Given[/B]')
    dist = ratings.get('distribution', {})
    if dist:
        bar_items = []
        for r in range(10, 0, -1):
            count = dist.get(str(r), 0)
            bar = '#' * min(count, 30)
            bar_items.append('  %2d/10: %s (%d)' % (r, bar, count))
        lines.extend(bar_items)
    total_ratings = ratings.get('total', 0)
    lines.append('  Total ratings: %d' % total_ratings)
    lines.append('')

    lines.append('[B]Network[/B]')
    lines.append('  Friends: %d' % network.get('friends', 0))
    lines.append('  Followers: %d' % network.get('followers', 0))
    lines.append('  Following: %d' % network.get('following', 0))

    xbmcgui.Dialog().textviewer('Your Trakt Stats', '\n'.join(lines))


# ── Custom Lists ──────────────────────────────────────────────────────────

def get_my_lists():
    """Show user's custom Trakt lists with option to create new."""
    if not _require_auth():
        return

    # Add "Create New List" item
    create_url = '%s?action=create_list' % sys.argv[0]
    li = xbmcgui.ListItem(label='[COLOR yellow]+ Create New List[/COLOR]')
    xbmcplugin.addDirectoryItem(_handle(), create_url, li, False)

    url = '%s/users/me/lists' % BASE
    status, data = _authed_get(url, 'My Lists')
    if status != 200:
        xbmcplugin.endOfDirectory(_handle())
        return

    for lst in (data or []):
        name = lst.get('name', 'Untitled')
        item_count = lst.get('item_count', 0)
        likes = lst.get('likes', 0)
        list_ids = lst.get('ids', {})
        list_slug = list_ids.get('slug', '')
        desc = lst.get('description', '')
        privacy = lst.get('privacy', 'private')

        label = '%s (%d items) [%s]' % (name, item_count, privacy)
        li = xbmcgui.ListItem(label=label)
        li.setInfo('video', {'title': name, 'plot': desc})

        # Context menu for delete
        li.addContextMenuItems([
            ('Delete List', 'RunPlugin(plugin://plugin.video.trakt_player/?action=delete_list&list_slug=%s)' % quote_plus(list_slug))
        ])

        url = '%s?action=list_items&user=me&list_slug=%s' % (sys.argv[0], quote_plus(list_slug))
        xbmcplugin.addDirectoryItem(_handle(), url, li, True)

    xbmcplugin.endOfDirectory(_handle())


def create_list():
    """Create a new Trakt list."""
    if not _require_auth():
        return
    kb = xbmc.Keyboard('', 'Enter list name')
    kb.doModal()
    if not kb.isConfirmed():
        return
    name = kb.getText().strip()
    if not name:
        return

    # Ask for privacy
    dlg = xbmcgui.Dialog()
    privacy_opts = ['Private', 'Friends', 'Public']
    selected = dlg.select('List Privacy', privacy_opts)
    if selected < 0:
        return
    privacy = privacy_opts[selected].lower()

    # Optional description
    kb2 = xbmc.Keyboard('', 'Description (optional)')
    kb2.doModal()
    desc = kb2.getText().strip() if kb2.isConfirmed() else ''

    body = {'name': name, 'description': desc, 'privacy': privacy, 'display_numbers': True, 'allow_comments': True}
    status, resp = _post('%s/users/me/lists' % BASE, body)
    if status in (200, 201):
        xbmcgui.Dialog().notification('Trakt', 'List "%s" created!' % name, xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Trakt', 'Failed to create list', xbmcgui.NOTIFICATION_ERROR)


def delete_list(list_slug):
    """Delete a Trakt list."""
    if not _require_auth():
        return
    dlg = xbmcgui.Dialog()
    if not dlg.yesno('Delete List', 'Are you sure you want to delete this list?\n\nThis cannot be undone.'):
        return
    status = _delete('%s/users/me/lists/%s' % (BASE, list_slug))
    if status in (200, 204):
        xbmcgui.Dialog().notification('Trakt', 'List deleted', xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Trakt', 'Failed to delete', xbmcgui.NOTIFICATION_ERROR)


def add_to_list(media_type, imdb_id):
    """Add an item to one of user's custom lists."""
    if not _require_auth():
        return
    url = '%s/users/me/lists' % BASE
    status, lists = _authed_get(url, 'Lists')
    if status != 200 or not lists:
        xbmcgui.Dialog().notification('Trakt', 'No lists found. Create one first.', xbmcgui.NOTIFICATION_WARNING)
        return

    names = [l.get('name', 'Untitled') for l in lists]
    dlg = xbmcgui.Dialog()
    selected = dlg.select('Add to List', names)
    if selected < 0:
        return

    list_slug = lists[selected].get('ids', {}).get('slug', '')
    key = 'movies' if media_type == 'movie' else 'shows'
    body = {key: [{'ids': {'imdb': imdb_id}}]}
    status, resp = _post('%s/users/me/lists/%s/items' % (BASE, list_slug), body)
    if status in (200, 201):
        added = resp.get('added', {}).get(key, 0)
        xbmcgui.Dialog().notification('Trakt', 'Added to "%s"' % names[selected], xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification('Trakt', 'Failed to add', xbmcgui.NOTIFICATION_ERROR)
