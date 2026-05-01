# -*- coding: utf-8 -*-
"""My Lists — aggregates private lists from enabled tracking services
(Trakt, SIMKL, Bingebase).

Only reachable when at least one tracking integration is enabled in settings.
"""
import xbmcgui
import xbmcplugin

from .common import (HANDLE, ICON, FANART, add_dir, end_directory,
                     get_setting_bool, notify, log)
from . import tmdb as T
from . import listing as L
from . import trakt as TR
from . import simkl as SK


# ---------------- gate ----------------

def any_tracking_enabled():
    """True if ANY tracker is enabled in settings (authenticated or not)."""
    return (get_setting_bool('trakt_enabled')
            or get_setting_bool('simkl_enabled')
            or get_setting_bool('bingebase_enabled'))


# ---------------- root ----------------

def my_lists_root():
    art = {'icon': ICON, 'fanart': FANART}

    if get_setting_bool('trakt_enabled'):
        if TR.is_authenticated():
            add_dir('[B]Trakt[/B] — My Lists', {'action': 'trakt_mylists'}, art=art,
                    plot='Your Trakt watchlist, collection, favorites, personal lists and recommendations.')
        else:
            add_dir('[COLOR FFFFA726]Trakt — not authenticated (tap to sign in)[/COLOR]',
                    {'action': 'trakt_auth'}, art=art,
                    plot='Authenticate with Trakt to show your Trakt lists here.')

    if get_setting_bool('simkl_enabled'):
        if SK.is_authenticated():
            add_dir('[B]SIMKL[/B] — My Lists', {'action': 'simkl_mylists'}, art=art,
                    plot='Your SIMKL Plan-to-Watch / Completed / On-Hold / Dropped lists.')
        else:
            add_dir('[COLOR FFFFA726]SIMKL — not authenticated (tap to sign in)[/COLOR]',
                    {'action': 'simkl_auth'}, art=art,
                    plot='Authenticate with SIMKL to show your SIMKL lists here.')

    if get_setting_bool('bingebase_enabled'):
        add_dir('[COLOR FF888888]Bingebase — custom lists not supported by API[/COLOR]',
                {'action': 'bingebase_notice'}, art=art,
                plot='Bingebase currently exposes only watched-history sync — no '
                     'watchlists or personal lists via its public API.')

    end_directory(content='')


# ---------------- ID resolution ----------------

def _resolve_to_tmdb(obj, media):
    """Given a Trakt/SIMKL {ids:{tmdb,imdb,...}} object, return a full TMDB
    details dict (so L.list_movies / L.list_tv can render it with play links)."""
    if not obj:
        return None
    ids = obj.get('ids') or {}
    tmdb_id = ids.get('tmdb')
    imdb_id = ids.get('imdb')
    try:
        if tmdb_id:
            return T.movie_details(tmdb_id) if media == 'movie' else T.tv_details(tmdb_id)
        if imdb_id:
            f = T._get('/find/%s' % imdb_id, {'external_source': 'imdb_id'}, ttl=86400) or {}
            arr = f.get('movie_results' if media == 'movie' else 'tv_results') or []
            if arr:
                first = arr[0].get('id')
                if first:
                    return T.movie_details(first) if media == 'movie' else T.tv_details(first)
    except Exception as e:
        log('mylists resolve error: %s' % e)
    return None


def _render(results, media):
    if media == 'movie':
        L.list_movies({'results': results})
    else:
        L.list_tv({'results': results})


# ---------------- Trakt ----------------

def trakt_mylists():
    if not TR.is_authenticated():
        notify('Trakt: not authenticated')
        end_directory(''); return
    art = {'icon': ICON, 'fanart': FANART}
    add_dir('Watchlist — Movies', {'action': 'trakt_list', 'kind': 'watchlist', 'media': 'movie'}, art=art)
    add_dir('Watchlist — Shows',  {'action': 'trakt_list', 'kind': 'watchlist', 'media': 'tv'}, art=art)
    add_dir('Collection — Movies', {'action': 'trakt_list', 'kind': 'collection', 'media': 'movie'}, art=art)
    add_dir('Collection — Shows',  {'action': 'trakt_list', 'kind': 'collection', 'media': 'tv'}, art=art)
    add_dir('Favorites — Movies', {'action': 'trakt_list', 'kind': 'favorites', 'media': 'movie'}, art=art)
    add_dir('Favorites — Shows',  {'action': 'trakt_list', 'kind': 'favorites', 'media': 'tv'}, art=art)
    add_dir('Recommendations — Movies', {'action': 'trakt_list', 'kind': 'recommendations', 'media': 'movie'}, art=art)
    add_dir('Recommendations — Shows',  {'action': 'trakt_list', 'kind': 'recommendations', 'media': 'tv'}, art=art)
    add_dir('[B]My Personal Lists[/B]', {'action': 'trakt_personal_lists'}, art=art,
            plot='User-created lists on your Trakt account.')
    end_directory(content='')


def _trakt_path(kind, media):
    plural = 'movies' if media == 'movie' else 'shows'
    if kind == 'watchlist':
        return '/sync/watchlist/%s' % plural
    if kind == 'collection':
        return '/sync/collection/%s' % plural
    if kind == 'favorites':
        return '/users/me/favorites/%s' % plural
    if kind == 'recommendations':
        return '/recommendations/%s' % plural
    return '/sync/watchlist/%s' % plural


def trakt_list(kind, media):
    data = TR._get(_trakt_path(kind, media)) or []
    results = []
    for it in data:
        # recommendations returns objects at top-level; other endpoints wrap.
        obj = it.get('movie') if media == 'movie' else it.get('show')
        if obj is None and kind == 'recommendations':
            obj = it
        det = _resolve_to_tmdb(obj, media)
        if det:
            results.append(det)
    if not results:
        notify('Trakt: list is empty')
    _render(results, media)


def trakt_personal_lists():
    data = TR._get('/users/me/lists') or []
    if not data:
        notify('Trakt: no personal lists')
        end_directory(''); return
    for lst in data:
        name = lst.get('name') or 'List'
        slug = (lst.get('ids') or {}).get('slug') or lst.get('id')
        count = lst.get('item_count') or 0
        if slug is None:
            continue
        add_dir('%s (%d)' % (name, count),
                {'action': 'trakt_personal_list_view', 'slug': slug},
                plot=lst.get('description') or '')
    end_directory(content='')


def _personal_list_items(slug):
    return TR._get('/users/me/lists/%s/items' % slug) or []


def trakt_personal_list_view(slug):
    data = _personal_list_items(slug)
    movies, shows = [], []
    for it in data:
        t = it.get('type')
        if t == 'movie':
            m = _resolve_to_tmdb(it.get('movie'), 'movie')
            if m: movies.append(m)
        elif t == 'show':
            s = _resolve_to_tmdb(it.get('show'), 'tv')
            if s: shows.append(s)
    if movies and not shows:
        _render(movies, 'movie'); return
    if shows and not movies:
        _render(shows, 'tv'); return
    if not movies and not shows:
        notify('Trakt: list is empty')
        end_directory(''); return
    # mixed list
    art = {'icon': ICON, 'fanart': FANART}
    add_dir('— Movies (%d) —' % len(movies),
            {'action': 'trakt_personal_list_view_type', 'slug': slug, 'media': 'movie'}, art=art)
    add_dir('— Shows (%d) —' % len(shows),
            {'action': 'trakt_personal_list_view_type', 'slug': slug, 'media': 'tv'}, art=art)
    end_directory(content='')


def trakt_personal_list_view_type(slug, media):
    data = _personal_list_items(slug)
    want = 'movie' if media == 'movie' else 'show'
    results = []
    for it in data:
        if it.get('type') != want:
            continue
        det = _resolve_to_tmdb(it.get(want), media)
        if det:
            results.append(det)
    _render(results, media)


# ---------------- SIMKL ----------------

def simkl_mylists():
    if not SK.is_authenticated():
        notify('SIMKL: not authenticated')
        end_directory(''); return
    art = {'icon': ICON, 'fanart': FANART}
    add_dir('Plan to Watch — Movies', {'action': 'simkl_list', 'kind': 'plantowatch', 'media': 'movie'}, art=art)
    add_dir('Plan to Watch — Shows',  {'action': 'simkl_list', 'kind': 'plantowatch', 'media': 'tv'}, art=art)
    add_dir('Plan to Watch — Anime',  {'action': 'simkl_list', 'kind': 'plantowatch', 'media': 'anime'}, art=art)
    add_dir('Completed — Movies', {'action': 'simkl_list', 'kind': 'completed', 'media': 'movie'}, art=art)
    add_dir('Completed — Shows',  {'action': 'simkl_list', 'kind': 'completed', 'media': 'tv'}, art=art)
    add_dir('Completed — Anime',  {'action': 'simkl_list', 'kind': 'completed', 'media': 'anime'}, art=art)
    add_dir('On Hold — Shows',    {'action': 'simkl_list', 'kind': 'hold', 'media': 'tv'}, art=art)
    add_dir('On Hold — Anime',    {'action': 'simkl_list', 'kind': 'hold', 'media': 'anime'}, art=art)
    add_dir('Dropped — Shows',    {'action': 'simkl_list', 'kind': 'dropped', 'media': 'tv'}, art=art)
    add_dir('Dropped — Anime',    {'action': 'simkl_list', 'kind': 'dropped', 'media': 'anime'}, art=art)
    end_directory(content='')


def simkl_list(kind, media):
    # media: movie | tv | anime   (anime rendered as tv)
    if media == 'movie':
        plural = 'movies'
    elif media == 'anime':
        plural = 'anime'
    else:
        plural = 'shows'
    data = SK._get('/sync/all-items/%s' % plural,
                   params={'extended': 'full', 'status': kind}) or {}
    arr = data.get(plural) or []
    render_media = 'movie' if media == 'movie' else 'tv'
    results = []
    for it in arr:
        obj = it.get('movie') or it.get('show') or it.get('anime')
        det = _resolve_to_tmdb(obj, render_media)
        if det:
            results.append(det)
    if not results:
        notify('SIMKL: list is empty')
    _render(results, render_media)


# ---------------- Bingebase ----------------

def bingebase_notice():
    xbmcgui.Dialog().ok(
        'Bingebase — custom lists',
        'Bingebase\'s public API currently only exposes watched-history '
        'import/export. Watchlists and personal lists are not yet available '
        'through the API.\n\n'
        'You can still use Bingebase to scrobble your playback activity '
        '(enable "Scrobble playback to Bingebase" in settings).')
    # Cancel navigation so Kodi stays on the previous screen.
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False,
                              updateListing=False, cacheToDisc=False)


# ---------------- Context-menu add / remove ----------------

def _trackers_enabled_and_auth():
    """Returns dict of available trackers: trakt, simkl."""
    out = {}
    if get_setting_bool('trakt_enabled') and TR.is_authenticated():
        out['trakt'] = True
    if get_setting_bool('simkl_enabled') and SK.is_authenticated():
        out['simkl'] = True
    return out


def _list_options(action):
    """Return list of (label, service, key) pairs for add/remove dialogs."""
    avail = _trackers_enabled_and_auth()
    opts = []
    if 'trakt' in avail:
        opts.append(('Trakt — Watchlist', 'trakt', 'watchlist'))
        opts.append(('Trakt — Collection', 'trakt', 'collection'))
        opts.append(('Trakt — Favorites', 'trakt', 'favorites'))
    if 'simkl' in avail:
        opts.append(('SIMKL — Plan to Watch', 'simkl', 'plantowatch'))
        opts.append(('SIMKL — Completed', 'simkl', 'completed'))
        opts.append(('SIMKL — On Hold', 'simkl', 'hold'))
        opts.append(('SIMKL — Dropped', 'simkl', 'dropped'))
    return opts


def tracker_add_dialog(media_type, tmdb_id=None, imdb_id=None, title=''):
    opts = _list_options('add')
    if not opts:
        notify('No authenticated trackers enabled')
        return
    labels = ['Add "%s" to…' % (title[:40] if title else '')] + [o[0] for o in opts]
    # dialog returns index into 'opts' array, but we added a header; use select()
    idx = xbmcgui.Dialog().select('Add to list', [o[0] for o in opts])
    if idx < 0:
        return
    _label, service, key = opts[idx]
    ok = False
    if service == 'trakt':
        ok = TR.add_to_list(key, media_type, tmdb_id=tmdb_id, imdb_id=imdb_id)
    elif service == 'simkl':
        ok = SK.add_to_list(key, media_type, tmdb_id=tmdb_id, imdb_id=imdb_id)
    notify('Added to %s' % _label if ok else 'Failed to add to %s' % _label)


def tracker_remove_dialog(media_type, tmdb_id=None, imdb_id=None, title=''):
    opts = _list_options('remove')
    if not opts:
        notify('No authenticated trackers enabled')
        return
    idx = xbmcgui.Dialog().select('Remove from list', [o[0] for o in opts])
    if idx < 0:
        return
    _label, service, key = opts[idx]
    ok = False
    if service == 'trakt':
        ok = TR.remove_from_list(key, media_type, tmdb_id=tmdb_id, imdb_id=imdb_id)
    elif service == 'simkl':
        ok = SK.remove_from_list(key, media_type, tmdb_id=tmdb_id, imdb_id=imdb_id)
    notify('Removed from %s' % _label if ok else 'Failed to remove from %s' % _label)


def context_menu_entries(media_type, tmdb_id=None, imdb_id=None, title=''):
    """Build context-menu tuples for movie / show rows.
    Returns empty list when no tracker is enabled+authenticated."""
    from .common import build_url
    if not _trackers_enabled_and_auth():
        return []
    entries = []
    params = {'action': 'tracker_add', 'media_type': media_type}
    if tmdb_id is not None:
        params['tmdb_id'] = tmdb_id
    if imdb_id:
        params['imdb_id'] = imdb_id
    if title:
        params['title'] = title
    entries.append(('[B]+ Add to list…[/B]', 'RunPlugin(%s)' % build_url(**params)))
    params['action'] = 'tracker_remove'
    entries.append(('[B]− Remove from list…[/B]', 'RunPlugin(%s)' % build_url(**params)))
    return entries
