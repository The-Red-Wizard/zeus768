# -*- coding: utf-8 -*-
"""Vidscr — Kodi addon entry point / router."""
import sys
import datetime
from urllib.parse import quote_plus

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.common import (HANDLE, ICON, FANART, ADDON, ADDON_NAME, build_url,
                                  add_dir, end_directory, parse_params, keyboard, notify,
                                  get_setting_int, log, read_debug_log, clear_debug_log,
                                  DEBUG_LOG_PATH)
from resources.lib import tmdb as T
from resources.lib import tvmaze as TVM
from resources.lib import listing as L
from resources.lib import sources as SRC
from resources.lib import features as F
from resources.lib import franchises as FR
from resources.lib import mylists as ML
from resources.lib import cache as CACHE


# Prune expired TMDB cache files on every plugin invocation. Cheap (a single
# listdir + getmtime per cache file) and prevents the addon-data folder from
# growing forever.
try:
    CACHE.prune()
except Exception:
    pass


# ---------------- ROOT ----------------

def root():
    art_film = {'icon': ICON, 'thumb': ICON, 'fanart': FANART}
    add_dir('[B]Movies[/B]', {'action': 'movies_root'}, art=art_film,
            plot='Browse movies: New releases, Oscar nominees, Genres, Actors, Networks.')
    add_dir('[B]TV Shows[/B]', {'action': 'tv_root'}, art=art_film,
            plot='Browse TV: New episodes calendar, Premiering shows, Genres, Actors.')
    add_dir('[B]Search[/B]', {'action': 'search_root'}, art=art_film,
            plot='Search Movies, TV Shows and People.')
    if ML.any_tracking_enabled():
        add_dir('[B]My Lists[/B]', {'action': 'my_lists'}, art=art_film,
                plot='Your private lists from enabled tracking services — '
                     'Trakt watchlist / collection / favorites / personal lists, '
                     'SIMKL plan-to-watch / completed and more.')
    add_dir('Open Settings', {'action': 'open_settings'}, art=art_film, is_folder=True,
            plot='Configure TMDB key, region, calendar countries and playback options.')
    end_directory(content='', cache_to_disc=True)


# ---------------- MOVIES ----------------

def movies_root():
    add_dir('[COLOR FFFFA726]▶ Continue Watching[/COLOR]',
            {'action': 'continue_movies'}, art={'icon': ICON, 'fanart': FANART},
            plot='Resume movies you started but never finished.')
    h = F.active_holiday()
    if h:
        add_dir('%s (in season)' % h['label_movies'],
                {'action': 'holiday_movies'},
                art={'icon': ICON, 'fanart': FANART},
                plot='Seasonal picks — auto-rotates with the calendar.')
    add_dir('New Releases (Now Playing)', {'action': 'movies_new', 'page': 1}, art={'icon': ICON, 'fanart': FANART})
    add_dir('Trending (Today)', {'action': 'movies_trending', 'period': 'day', 'page': 1},
            plot='Movies trending on TMDB right now (last 24 hours).')
    add_dir('Trending (This Week)', {'action': 'movies_trending', 'period': 'week', 'page': 1},
            plot='Movies trending on TMDB over the last 7 days.')
    add_dir('Popular', {'action': 'movies_popular', 'page': 1})
    add_dir('Top Rated', {'action': 'movies_top', 'page': 1})
    add_dir('Upcoming', {'action': 'movies_upcoming', 'page': 1})
    add_dir('Oscar Nominated', {'action': 'movies_oscars', 'page': 1})
    add_dir('[B]Movie Franchises[/B] (200)', {'action': 'franchises_root', 'page': 1},
            art={'icon': ICON, 'fanart': FANART},
            plot='200 movie franchises — MCU, Bond, Star Wars, Harry Potter, Fast & Furious and many more. Paginated 40 per page.')
    add_dir('Directors', {'action': 'directors_root'},
            plot='Browse movies by acclaimed directors.')
    add_dir('Decades', {'action': 'movies_decades'},
            plot='Browse movies by decade: 1960s through 2020s.')
    add_dir('Themes & Keywords', {'action': 'movies_keywords'},
            plot='Browse by theme: Based on True Story, Time Travel, Heist, Christmas, Zombie and more.')
    add_dir('Genres', {'action': 'movies_genres'})
    add_dir('Actors', {'action': 'people_root', 'target': 'movie'})
    add_dir('Networks (Studios)', {'action': 'movies_studios'})
    add_dir('Ambient Mode (last watched backdrops)',
            {'action': 'ambient_launch'}, is_folder=True,
            art={'icon': ICON, 'fanart': FANART},
            plot='Plays a slow slideshow of fanart from your recently watched titles. Press Back or Stop to exit.')
    end_directory(content='')


def movies_new(page=1): L.list_movies(T.movies_now_playing(page))
def movies_popular(page=1): L.list_movies(T.movies_popular(page))
def movies_top(page=1): L.list_movies(T.movies_top_rated(page))
def movies_upcoming(page=1): L.list_movies(T.movies_upcoming(page))
def movies_oscars(page=1): L.list_movies(T.oscar_nominees(page))


def movies_genres():
    for g in T.movie_genres():
        add_dir(g['name'], {'action': 'movies_by_genre', 'genre_id': g['id'], 'genre_name': g['name'], 'page': 1})
    end_directory(content='')


def movies_by_genre(genre_id, page=1):
    L.list_movies(T.discover_movies({'with_genres': str(genre_id)}, page=page),
                  next_action='movies_by_genre',
                  next_params={'genre_id': genre_id})


def movies_studios():
    studios = [
        {'id': 2, 'name': 'Walt Disney Pictures'}, {'id': 3, 'name': 'Pixar'},
        {'id': 4, 'name': 'Paramount'}, {'id': 5, 'name': 'Columbia Pictures'},
        {'id': 7, 'name': 'DreamWorks'}, {'id': 33, 'name': 'Universal Pictures'},
        {'id': 25, 'name': '20th Century Fox'}, {'id': 174, 'name': 'Warner Bros.'},
        {'id': 420, 'name': 'Marvel Studios'}, {'id': 429, 'name': 'DC Comics'},
        {'id': 923, 'name': 'Legendary Entertainment'}, {'id': 1632, 'name': 'Lionsgate'},
        {'id': 6194, 'name': 'Walt Disney Studios'}, {'id': 7505, 'name': 'Marvel Entertainment'},
        {'id': 11073, 'name': 'Sony Pictures TV'}, {'id': 21, 'name': 'Metro-Goldwyn-Mayer'},
        {'id': 41, 'name': 'New Line Cinema'}, {'id': 491, 'name': 'A24'},
        {'id': 1024, 'name': 'Amazon Studios'},
    ]
    for s in studios:
        add_dir(s['name'], {'action': 'movies_by_studio', 'studio_id': s['id'], 'page': 1})
    end_directory(content='')


def movies_by_studio(studio_id, page=1):
    L.list_movies(T.discover_movies({'with_companies': str(studio_id)}, page=page),
                  next_action='movies_by_studio',
                  next_params={'studio_id': studio_id})


# ---------------- TV ----------------

def tv_root():
    add_dir('[COLOR FFFFA726]▶ Continue Watching[/COLOR]',
            {'action': 'continue_tv'}, art={'icon': ICON, 'fanart': FANART},
            plot='Resume the next episode of every show you have in progress.')
    add_dir('On Deck (new episode aired since last watch)',
            {'action': 'on_deck'}, art={'icon': ICON, 'fanart': FANART},
            plot='Shows where a brand-new episode has aired since you last watched.')
    h = F.active_holiday()
    if h:
        add_dir('%s (in season)' % h['label_tv'],
                {'action': 'holiday_tv'},
                art={'icon': ICON, 'fanart': FANART},
                plot='Seasonal picks — auto-rotates with the calendar.')
    add_dir('New Episodes (%s-day Calendar)' % get_setting_int('calendar_days', 7),
            {'action': 'tv_calendar'}, art={'icon': ICON, 'fanart': FANART},
            plot='Upcoming TV episodes for the next few days (TVmaze, US + UK).')
    add_dir('TVmaze Premiering Shows', {'action': 'tv_premieres'},
            plot='Shows premiering soon (TVmaze new series premieres).')
    add_dir('Trending (Today)', {'action': 'tv_trending', 'period': 'day', 'page': 1},
            plot='TV shows trending on TMDB right now (last 24 hours).')
    add_dir('Trending (This Week)', {'action': 'tv_trending', 'period': 'week', 'page': 1},
            plot='TV shows trending on TMDB over the last 7 days.')
    add_dir('Airing Today', {'action': 'tv_airing_today', 'page': 1},
            plot='Shows with an episode airing today.')
    add_dir('On The Air', {'action': 'tv_on_air', 'page': 1})
    add_dir('Popular', {'action': 'tv_popular', 'page': 1})
    add_dir('Top Rated', {'action': 'tv_top', 'page': 1})
    add_dir('[B]TV Collections & Universes[/B]', {'action': 'tv_collections'},
            art={'icon': ICON, 'fanart': FANART},
            plot='Grouped shows that share a universe — Star Trek, Law & Order, Marvel, DC, Doctor Who, Walking Dead and more.')
    add_dir('Genres', {'action': 'tv_genres'})
    add_dir('Actors', {'action': 'people_root', 'target': 'tv'})
    add_dir('Networks', {'action': 'tv_networks'})
    end_directory(content='')


def tv_popular(page=1): L.list_tv(T.tv_popular(page), next_action='tv_popular')
def tv_top(page=1): L.list_tv(T.tv_top_rated(page), next_action='tv_top')
def tv_on_air(page=1): L.list_tv(T.tv_on_the_air(page), next_action='tv_on_air')


def tv_genres():
    for g in T.tv_genres():
        add_dir(g['name'], {'action': 'tv_by_genre', 'genre_id': g['id'], 'page': 1})
    end_directory(content='')


def tv_by_genre(genre_id, page=1):
    L.list_tv(T.discover_tv({'with_genres': str(genre_id)}, page=page),
              next_action='tv_by_genre',
              next_params={'genre_id': genre_id})


def tv_networks():
    for n in T.tv_networks():
        add_dir(n['name'], {'action': 'tv_by_network', 'network_id': n['id'], 'page': 1})
    end_directory(content='')


def tv_by_network(network_id, page=1):
    L.list_tv(T.discover_tv({'with_networks': str(network_id)}, page=page),
             next_action='tv_by_network',
             next_params={'network_id': network_id})


def tv_seasons(tmdb_id):
    L.list_seasons(tmdb_id, T.tv_details(tmdb_id))


def tv_episodes(tmdb_id, season):
    show = T.tv_details(tmdb_id)
    season_data = T.tv_season(tmdb_id, season)
    L.list_episodes(tmdb_id, int(season), show, season_data)


# ---- TV Calendar ----

def tv_calendar():
    xbmcplugin.setContent(HANDLE, 'episodes')
    c1 = ADDON.getSetting('calendar_country_1') or 'US'
    c2 = ADDON.getSetting('calendar_country_2') or 'GB'
    days = get_setting_int('calendar_days', 7) or 7
    countries = tuple(dict.fromkeys([c1, c2]))
    eps = TVM.upcoming_premieres(countries=countries, days=days)
    if not eps:
        notify('No upcoming episodes found')
        end_directory('episodes')
        return
    for ep in eps:
        show = ep.get('show') or (ep.get('_embedded') or {}).get('show') or {}
        show_title = show.get('name') or ''
        ep_name = ep.get('name') or 'Episode'
        season_no = ep.get('season') or 0
        ep_no = ep.get('number') or 0
        airdate = ep.get('_airdate') or ep.get('airdate') or ''
        country = ep.get('_country', '')
        label = '[%s %s] %s — S%02dE%02d - %s' % (airdate, country, show_title, season_no, ep_no, ep_name)
        li = xbmcgui.ListItem(label=label)
        img = ((ep.get('image') or {}).get('original')
               or (show.get('image') or {}).get('original') or ICON)
        li.setArt({'thumb': img, 'poster': img, 'fanart': FANART, 'icon': img})
        try:
            li.setInfo('video', {
                'title': ep_name, 'tvshowtitle': show_title,
                'season': int(season_no) if season_no else 0,
                'episode': int(ep_no) if ep_no else 0,
                'plot': (ep.get('summary') or show.get('summary') or '')
                        .replace('<p>', '').replace('</p>', '\n').replace('<br>', '\n'),
                'aired': airdate, 'mediatype': 'episode',
            })
        except Exception:
            pass
        ext = (show.get('externals') or {})
        imdb = ext.get('imdb')
        if imdb and season_no and ep_no:
            li.setProperty('IsPlayable', 'true')
            url = build_url(action='play_episode_imdb', imdb_id=imdb,
                            season=season_no, episode=ep_no, title=show_title)
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
        else:
            url = build_url(action='search_tv_exec', q=show_title)
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    end_directory('episodes')


def tv_premieres():
    xbmcplugin.setContent(HANDLE, 'tvshows')
    c1 = ADDON.getSetting('calendar_country_1') or 'US'
    c2 = ADDON.getSetting('calendar_country_2') or 'GB'
    days = max(get_setting_int('calendar_days', 7), 14)
    countries = tuple(dict.fromkeys([c1, c2]))
    eps = TVM.upcoming_premieres(countries=countries, days=days)
    seen = set()
    for ep in eps:
        if (ep.get('season') or 0) != 1 or (ep.get('number') or 0) != 1:
            continue
        show = ep.get('show') or {}
        sid = show.get('id')
        if sid in seen:
            continue
        seen.add(sid)
        show_title = show.get('name') or ''
        airdate = ep.get('_airdate') or ep.get('airdate') or ''
        country = ep.get('_country', '')
        label = '[%s %s] %s' % (airdate, country, show_title)
        li = xbmcgui.ListItem(label=label)
        img = ((show.get('image') or {}).get('original') or ICON)
        li.setArt({'thumb': img, 'poster': img, 'fanart': FANART, 'icon': img})
        try:
            li.setInfo('video', {
                'title': show_title, 'tvshowtitle': show_title,
                'plot': (show.get('summary') or '').replace('<p>', '').replace('</p>', '\n'),
                'premiered': airdate, 'mediatype': 'tvshow',
            })
        except Exception:
            pass
        ext = (show.get('externals') or {})
        imdb = ext.get('imdb')
        if imdb:
            url = build_url(action='tv_seasons_imdb', imdb_id=imdb, title=show_title)
        else:
            url = build_url(action='search_tv_exec', q=show_title)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    end_directory('tvshows')


# ---------------- PEOPLE ----------------

def people_root(target='movie', page=1): L.list_people(T.popular_people(page))


def person(person_id):
    data = T.person_details(person_id)
    cc = data.get('combined_credits') or {}
    cast = sorted(cc.get('cast', []), key=lambda x: (x.get('popularity') or 0), reverse=True)
    movies = {'results': [c for c in cast if c.get('media_type') == 'movie'][:80]}
    shows = {'results': [c for c in cast if c.get('media_type') == 'tv'][:80]}
    xbmcplugin.setContent(HANDLE, 'videos')
    if movies['results']:
        add_dir('— Movies (%d) —' % len(movies['results']),
                {'action': 'person_movies', 'person_id': person_id},
                art={'icon': ICON, 'fanart': FANART})
    if shows['results']:
        add_dir('— TV Shows (%d) —' % len(shows['results']),
                {'action': 'person_tv', 'person_id': person_id},
                art={'icon': ICON, 'fanart': FANART})
    end_directory(content='')


def person_movies(person_id):
    data = T.person_details(person_id)
    cast = sorted((data.get('combined_credits') or {}).get('cast', []),
                  key=lambda x: (x.get('popularity') or 0), reverse=True)
    L.list_movies({'results': [c for c in cast if c.get('media_type') == 'movie']})


def person_tv(person_id):
    data = T.person_details(person_id)
    cast = sorted((data.get('combined_credits') or {}).get('cast', []),
                  key=lambda x: (x.get('popularity') or 0), reverse=True)
    L.list_tv({'results': [c for c in cast if c.get('media_type') == 'tv']})


def movie_cast(tmdb_id):
    data = T.movie_credits(tmdb_id)
    L.list_people({'results': data.get('cast', [])})


# ---------------- SEARCH ----------------

def search_root():
    add_dir('Search Movies', {'action': 'search_movie'}, art={'icon': ICON, 'fanart': FANART})
    add_dir('Search TV Shows', {'action': 'search_tv'}, art={'icon': ICON, 'fanart': FANART})
    add_dir('Search People', {'action': 'search_person'}, art={'icon': ICON, 'fanart': FANART})
    add_dir('Search All (Multi)', {'action': 'search_multi'}, art={'icon': ICON, 'fanart': FANART})
    end_directory(content='')


def search_movie():
    q = keyboard('Search Movies')
    if not q:
        end_directory(''); return
    L.list_movies(T.search_movie(q))


def search_tv():
    q = keyboard('Search TV Shows')
    if not q:
        end_directory(''); return
    L.list_tv(T.search_tv(q))


def search_tv_exec(q): L.list_tv(T.search_tv(q))


def search_person():
    q = keyboard('Search People')
    if not q:
        end_directory(''); return
    L.list_people(T.search_person(q))


def search_multi():
    q = keyboard('Search Anything')
    if not q:
        end_directory(''); return
    data = T.search_multi(q)
    movies = {'results': [x for x in data.get('results', []) if x.get('media_type') == 'movie']}
    shows = {'results': [x for x in data.get('results', []) if x.get('media_type') == 'tv']}
    people = {'results': [x for x in data.get('results', []) if x.get('media_type') == 'person']}
    if len(movies['results']) >= len(shows['results']) and len(movies['results']) >= len(people['results']):
        L.list_movies(movies)
    elif len(shows['results']) >= len(people['results']):
        L.list_tv(shows)
    else:
        L.list_people(people)


# ---------------- PLAY ----------------

def play_movie(tmdb_id): L.play_movie(tmdb_id)
def play_episode(tmdb_id, season, episode): L.play_episode(tmdb_id, season, episode)


def play_episode_imdb(imdb_id, season, episode, title=''):
    primary, secondary = SRC.resolve('tv', imdb_id, season=season, episode=episode,
                                     imdb_id=imdb_id)
    streams = primary + secondary
    info = {'title': title, 'tvshowtitle': title,
            'season': int(season), 'episode': int(episode), 'mediatype': 'episode'}
    L._pick_and_play(streams, info, {'icon': ICON, 'fanart': FANART},
                     media_type='tv', imdb_id=imdb_id, season=season, episode=episode,
                     memory_key='tv:%s' % imdb_id)


def tv_seasons_imdb(imdb_id, title=''):
    data = T._get('/find/%s' % imdb_id, {'external_source': 'imdb_id'}, ttl=86400)
    tv = (data.get('tv_results') or [])
    if not tv:
        notify('Show not found on TMDB: %s' % title)
        end_directory(''); return
    tmdb_id = tv[0]['id']
    L.list_seasons(tmdb_id, T.tv_details(tmdb_id))


# ---------------- TRAKT ----------------

def trakt_auth():
    from resources.lib import trakt as TR
    TR.authenticate()


def trakt_logout():
    from resources.lib import trakt as TR
    TR.logout()


def trakt_sync():
    from resources.lib import trakt as TR
    TR.sync_history()


def trakt_mark_watched(media_type, tmdb_id=None, imdb_id=None, season=None, episode=None):
    from resources.lib import trakt as TR
    if not TR.is_authenticated():
        notify('Trakt: please authenticate first')
        return
    ids = {}
    if imdb_id: ids['imdb'] = imdb_id
    if tmdb_id: ids['tmdb'] = int(tmdb_id) if str(tmdb_id).isdigit() else tmdb_id
    if media_type == 'movie':
        payload = {'movies': [{'ids': ids}]}
    else:
        payload = {'shows': [{'ids': ids, 'seasons': [{
            'number': int(season or 0),
            'episodes': [{'number': int(episode or 0)}]
        }]}]}
    res = TR._post('/sync/history', payload)
    if res:
        notify('Trakt: marked as watched')
    else:
        notify('Trakt: failed to mark watched')


# ---------------- BINGEBASE ----------------

def bingebase_auth():
    from resources.lib import bingebase as BB
    BB.authenticate()


def bingebase_logout():
    from resources.lib import bingebase as BB
    BB.logout()


def bingebase_sync():
    from resources.lib import bingebase as BB
    BB.sync_history()


def bingebase_mark_watched(media_type, tmdb_id=None, imdb_id=None,
                           season=None, episode=None, title=''):
    from resources.lib import bingebase as BB
    ok = BB.mark_watched(media_type,
                         imdb_id=imdb_id, tmdb_id=tmdb_id,
                         season=season, episode=episode,
                         title=title, tv_show_title=title)
    if ok:
        notify('Bingebase: marked as watched')


# ---------------- SIMKL ----------------

def simkl_auth():
    from resources.lib import simkl as SK
    SK.authenticate()


def simkl_logout():
    from resources.lib import simkl as SK
    SK.logout()


def simkl_sync():
    from resources.lib import simkl as SK
    SK.sync_history()


def simkl_mark_watched(media_type, tmdb_id=None, imdb_id=None, season=None, episode=None):
    from resources.lib import simkl as SK
    ok = SK.mark_watched(media_type, imdb_id=imdb_id, tmdb_id=tmdb_id,
                         season=season, episode=episode)
    if ok:
        notify('SIMKL: marked as watched')
    else:
        notify('SIMKL: failed to mark watched')


# ---------------- RESUME / WATCHED ----------------

def clear_watched():
    from resources.lib import kodi_db as KDB
    KDB.clear_all()
    notify('Watched store cleared')


def clear_cache():
    n = CACHE.clear_all()
    notify('TMDB cache cleared (%d file%s)' % (n, '' if n == 1 else 's'))


# ---------------- DEBUG ----------------

def view_log():
    content = read_debug_log() or '(debug log is empty — enable "Debug logging" in settings and try playing something)'
    lines = content.splitlines()
    if len(lines) > 2000:
        lines = lines[-2000:]
    xbmcgui.Dialog().textviewer('Vidscr Debug Log', '\n'.join(lines))


def clear_log():
    clear_debug_log()
    notify('Debug log cleared')


def debug_test(imdb_id=None, tmdb_id=None, season=None, episode=None):
    media_type = 'tv' if season else 'movie'
    log('=== Resolver test: type=%s tmdb=%s imdb=%s s=%s e=%s ==='
        % (media_type, tmdb_id, imdb_id, season, episode))
    try:
        primary, secondary = SRC.resolve(media_type, tmdb_id or imdb_id,
                                         season=season, episode=episode, imdb_id=imdb_id)
        streams = primary + secondary
    except Exception as e:
        import traceback
        log('Resolver exception: %s\n%s' % (e, traceback.format_exc()))
        streams = []
    lines = ['Resolver test result', '=' * 40]
    if streams:
        lines.append('STATUS : SUCCESS — %d candidate(s) (%d primary, %d secondary)'
                     % (len(streams), len(primary), len(secondary)))
        for i, s in enumerate(streams, 1):
            lines.append('%d. [%s] %s' % (i, s.get('provider', '?'), s.get('label', '')))
            lines.append('   URL : %s' % s.get('url', '')[:200])
    else:
        lines.append('STATUS : FAILED — no playable URL returned')
    lines.append('')
    lines.append('-- last 80 log lines --')
    log_text = read_debug_log()
    lines.extend(log_text.splitlines()[-80:])
    xbmcgui.Dialog().textviewer('Vidscr Resolver Test', '\n'.join(lines))


def debug_test_prompt():
    imdb = keyboard('Enter IMDb ID (e.g. tt17048514)')
    if imdb:
        debug_test(imdb_id=imdb)


# ---------------- FRANCHISES / DIRECTORS / DECADES / KEYWORDS / TRENDING ----------------

FRANCHISES_PER_PAGE = 40


def _resolve_collection_id(name):
    """Return TMDB collection id for a franchise name, using seed first then search."""
    if name in FR.FRANCHISE_SEED_IDS:
        return FR.FRANCHISE_SEED_IDS[name]
    data = T.search_collection(name) or {}
    results = data.get('results') or []
    if results:
        return results[0].get('id')
    return None


def franchises_root(page=1):
    page = int(page)
    total = len(FR.FRANCHISES)
    total_pages = (total + FRANCHISES_PER_PAGE - 1) // FRANCHISES_PER_PAGE
    start = (page - 1) * FRANCHISES_PER_PAGE
    end = start + FRANCHISES_PER_PAGE
    chunk = FR.FRANCHISES[start:end]
    for name in chunk:
        add_dir(name, {'action': 'franchise_view', 'name': name},
                plot='All movies in the %s franchise.' % name)
    if page < total_pages:
        add_dir('[COLOR FFFFA726]Next page (%d of %d) »[/COLOR]' % (page + 1, total_pages),
                {'action': 'franchises_root', 'page': page + 1})
    if page > 1:
        add_dir('[COLOR FFFFA726]« Previous page (%d of %d)[/COLOR]' % (page - 1, total_pages),
                {'action': 'franchises_root', 'page': page - 1})
    end_directory(content='')


def franchise_view(name):
    cid = _resolve_collection_id(name)
    if not cid:
        notify('Franchise not found: %s' % name)
        end_directory(''); return
    data = T.collection_details(cid) or {}
    parts = data.get('parts') or []
    # Sort chronologically by release_date
    parts.sort(key=lambda m: (m.get('release_date') or '9999'))
    L.list_movies({'results': parts})


def directors_root():
    for pid, name in FR.DIRECTORS:
        add_dir(name, {'action': 'director_view', 'person_id': pid, 'name': name})
    end_directory(content='')


def director_view(person_id, name=''):
    data = T.person_details(person_id) or {}
    crew = (data.get('combined_credits') or {}).get('crew') or []
    directed = [c for c in crew if (c.get('job') or '').lower() == 'director'
                and c.get('media_type') == 'movie']
    # Dedup by id and sort by release date desc
    seen = set(); out = []
    for c in directed:
        mid = c.get('id')
        if mid in seen: continue
        seen.add(mid); out.append(c)
    out.sort(key=lambda m: (m.get('release_date') or ''), reverse=True)
    L.list_movies({'results': out})


def movies_decades():
    for label, _a, _b in FR.DECADES:
        add_dir(label, {'action': 'movies_by_decade', 'decade': label, 'page': 1})
    end_directory(content='')


def movies_by_decade(decade, page=1):
    spec = next((d for d in FR.DECADES if d[0] == decade), None)
    if not spec:
        end_directory(''); return
    _, gte, lte = spec
    L.list_movies(
        T.discover_movies({
            'primary_release_date.gte': gte,
            'primary_release_date.lte': lte,
            'sort_by': 'popularity.desc',
            'vote_count.gte': '100',
        }, page=page),
        next_action='movies_by_decade',
        next_params={'decade': decade},
    )


def movies_keywords():
    for kid, kname in FR.KEYWORDS:
        add_dir(kname, {'action': 'movies_by_keyword', 'keyword_id': kid,
                        'keyword_name': kname, 'page': 1})
    end_directory(content='')


def movies_by_keyword(keyword_id, page=1):
    L.list_movies(
        T.discover_movies({'with_keywords': str(keyword_id)}, page=page),
        next_action='movies_by_keyword',
        next_params={'keyword_id': keyword_id},
    )


def movies_trending(period='week', page=1):
    L.list_movies(
        T.trending_movies(period=period, page=page),
        next_action='movies_trending',
        next_params={'period': period},
    )


def tv_trending(period='week', page=1):
    L.list_tv(
        T.trending_tv(period=period, page=page),
        next_action='tv_trending',
        next_params={'period': period},
    )


def tv_airing_today(page=1):
    L.list_tv(T.tv_airing_today(page), next_action='tv_airing_today')


def tv_collections():
    for i, (uname, _ids) in enumerate(FR.TV_COLLECTIONS):
        add_dir(uname, {'action': 'tv_collection_view', 'idx': i})
    end_directory(content='')


def tv_collection_view(idx):
    try:
        idx = int(idx)
        uname, ids = FR.TV_COLLECTIONS[idx]
    except (ValueError, IndexError):
        end_directory(''); return
    # Build a results list by fetching each show's details (cached)
    results = []
    seen = set()
    for sid in ids:
        if sid in seen:
            continue
        seen.add(sid)
        s = T.tv_details(sid)
        if s and s.get('id'):
            results.append(s)
    # Sort by popularity desc
    results.sort(key=lambda s: (s.get('popularity') or 0), reverse=True)
    L.list_tv({'results': results})


# ---------------- ROUTER ----------------

def main():
    params = parse_params()
    action = params.get('action')
    log('action=%s params=%s' % (action, params), level=xbmc.LOGDEBUG)
    try:
        if action is None: root()
        elif action == 'open_settings':
            ADDON.openSettings()
            # Cancel navigation so Kodi stays on the previous screen and does
            # not show "Playback Failed" / an empty folder after settings close.
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False, updateListing=False, cacheToDisc=False)
        elif action == 'movies_root': movies_root()
        elif action == 'movies_new': movies_new(int(params.get('page', 1)))
        elif action == 'movies_popular': movies_popular(int(params.get('page', 1)))
        elif action == 'movies_top': movies_top(int(params.get('page', 1)))
        elif action == 'movies_upcoming': movies_upcoming(int(params.get('page', 1)))
        elif action == 'movies_oscars': movies_oscars(int(params.get('page', 1)))
        elif action == 'movies_genres': movies_genres()
        elif action == 'movies_by_genre': movies_by_genre(params['genre_id'], int(params.get('page', 1)))
        elif action == 'movies_studios': movies_studios()
        elif action == 'movies_by_studio': movies_by_studio(params['studio_id'], int(params.get('page', 1)))
        elif action == 'movies_trending': movies_trending(params.get('period', 'week'), int(params.get('page', 1)))
        elif action == 'franchises_root': franchises_root(int(params.get('page', 1)))
        elif action == 'franchise_view': franchise_view(params.get('name', ''))
        elif action == 'directors_root': directors_root()
        elif action == 'director_view': director_view(params['person_id'], params.get('name', ''))
        elif action == 'movies_decades': movies_decades()
        elif action == 'movies_by_decade': movies_by_decade(params['decade'], int(params.get('page', 1)))
        elif action == 'movies_keywords': movies_keywords()
        elif action == 'movies_by_keyword': movies_by_keyword(params['keyword_id'], int(params.get('page', 1)))
        elif action == 'tv_trending': tv_trending(params.get('period', 'week'), int(params.get('page', 1)))
        elif action == 'tv_airing_today': tv_airing_today(int(params.get('page', 1)))
        elif action == 'tv_collections': tv_collections()
        elif action == 'tv_collection_view': tv_collection_view(params.get('idx', 0))
        elif action == 'tv_root': tv_root()
        elif action == 'tv_popular': tv_popular(int(params.get('page', 1)))
        elif action == 'tv_top': tv_top(int(params.get('page', 1)))
        elif action == 'tv_on_air': tv_on_air(int(params.get('page', 1)))
        elif action == 'tv_genres': tv_genres()
        elif action == 'tv_by_genre': tv_by_genre(params['genre_id'], int(params.get('page', 1)))
        elif action == 'tv_networks': tv_networks()
        elif action == 'tv_by_network': tv_by_network(params['network_id'], int(params.get('page', 1)))
        elif action == 'tv_seasons': tv_seasons(params['tmdb_id'])
        elif action == 'tv_episodes': tv_episodes(params['tmdb_id'], params['season'])
        elif action == 'tv_calendar': tv_calendar()
        elif action == 'tv_premieres': tv_premieres()
        elif action == 'tv_seasons_imdb': tv_seasons_imdb(params['imdb_id'], params.get('title', ''))
        elif action == 'people_root': people_root(params.get('target', 'movie'), int(params.get('page', 1)))
        elif action == 'person': person(params['person_id'])
        elif action == 'person_movies': person_movies(params['person_id'])
        elif action == 'person_tv': person_tv(params['person_id'])
        elif action == 'movie_cast': movie_cast(params['tmdb_id'])
        elif action == 'search_root': search_root()
        elif action == 'search_movie': search_movie()
        elif action == 'search_tv': search_tv()
        elif action == 'search_tv_exec': search_tv_exec(params.get('q', ''))
        elif action == 'search_person': search_person()
        elif action == 'search_multi': search_multi()
        elif action == 'play_movie': play_movie(params['tmdb_id'])
        elif action == 'play_episode': play_episode(params['tmdb_id'], params['season'], params['episode'])
        elif action == 'play_episode_imdb': play_episode_imdb(params['imdb_id'], params['season'], params['episode'], params.get('title', ''))
        elif action == 'continue_movies': L.list_continue_movies()
        elif action == 'continue_tv': L.list_continue_tv()
        elif action == 'on_deck': F.on_deck()
        elif action == 'holiday_movies': F.holiday_movies(int(params.get('page', 1)))
        elif action == 'holiday_tv': F.holiday_tv(int(params.get('page', 1)))
        elif action == 'ambient_launch': F.ambient_launch()
        elif action == 'trakt_auth': trakt_auth()
        elif action == 'trakt_logout': trakt_logout()
        elif action == 'trakt_sync': trakt_sync()
        elif action == 'trakt_mark_watched':
            trakt_mark_watched(params.get('media_type', 'movie'),
                               tmdb_id=params.get('tmdb_id'),
                               imdb_id=params.get('imdb_id'),
                               season=params.get('season'),
                               episode=params.get('episode'))
        elif action == 'bingebase_auth': bingebase_auth()
        elif action == 'bingebase_logout': bingebase_logout()
        elif action == 'bingebase_sync': bingebase_sync()
        elif action == 'bingebase_mark_watched':
            bingebase_mark_watched(params.get('media_type', 'movie'),
                                   tmdb_id=params.get('tmdb_id'),
                                   imdb_id=params.get('imdb_id'),
                                   season=params.get('season'),
                                   episode=params.get('episode'),
                                   title=params.get('title', ''))
        elif action == 'simkl_auth': simkl_auth()
        elif action == 'simkl_logout': simkl_logout()
        elif action == 'simkl_sync': simkl_sync()
        elif action == 'simkl_mark_watched':
            simkl_mark_watched(params.get('media_type', 'movie'),
                               tmdb_id=params.get('tmdb_id'),
                               imdb_id=params.get('imdb_id'),
                               season=params.get('season'),
                               episode=params.get('episode'))
        elif action == 'clear_watched': clear_watched()
        elif action == 'clear_cache': clear_cache()
        elif action == 'my_lists': ML.my_lists_root()
        elif action == 'trakt_mylists': ML.trakt_mylists()
        elif action == 'trakt_list':
            ML.trakt_list(params.get('kind', 'watchlist'), params.get('media', 'movie'))
        elif action == 'trakt_personal_lists': ML.trakt_personal_lists()
        elif action == 'trakt_personal_list_view':
            ML.trakt_personal_list_view(params.get('slug', ''))
        elif action == 'trakt_personal_list_view_type':
            ML.trakt_personal_list_view_type(params.get('slug', ''),
                                             params.get('media', 'movie'))
        elif action == 'simkl_mylists': ML.simkl_mylists()
        elif action == 'simkl_list':
            ML.simkl_list(params.get('kind', 'plantowatch'), params.get('media', 'movie'))
        elif action == 'bingebase_notice': ML.bingebase_notice()
        elif action == 'tracker_add':
            ML.tracker_add_dialog(params.get('media_type', 'movie'),
                                  tmdb_id=params.get('tmdb_id'),
                                  imdb_id=params.get('imdb_id'),
                                  title=params.get('title', ''))
        elif action == 'tracker_remove':
            ML.tracker_remove_dialog(params.get('media_type', 'movie'),
                                     tmdb_id=params.get('tmdb_id'),
                                     imdb_id=params.get('imdb_id'),
                                     title=params.get('title', ''))
        elif action == 'view_log': view_log()
        elif action == 'clear_log': clear_log()
        elif action == 'debug_test':
            debug_test(imdb_id=params.get('imdb_id'), tmdb_id=params.get('tmdb_id'),
                       season=params.get('season'), episode=params.get('episode'))
        elif action == 'debug_test_prompt': debug_test_prompt()
        else:
            notify('Unknown action: %s' % action); root()
    except Exception as e:
        import traceback
        log('Exception: %s\n%s' % (e, traceback.format_exc()), level=xbmc.LOGERROR)
        notify('Error: %s' % e, time=5000)


if __name__ == '__main__':
    main()
