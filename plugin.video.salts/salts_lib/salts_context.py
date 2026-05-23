"""
SALTS - Salts-style Context Menu + Metadata Window
(v2.9.52  -  context-menu hardening pass)

Public surface used by default.py:

  * build_context_menu(...)           -> [(label, action), ...] for
                                         ListItem.addContextMenuItems()
  * open_meta_window(...)             -> Fullscreen modal meta viewer
  * play_trailer(...)                 -> Resolve YouTube trailer via TMDB
  * show_cast(...) / show_person_credits(...)
  * trakt_watchlist_toggle(...)       -> TRUE toggle, uses this fork's
                                         trakt_api (plural media_type,
                                         proper {ids:{tmdb:...}} payload)
  * trakt_watched_toggle(...)         -> Mark / unmark as watched on Trakt
  * trakt_rate_dialog(...)            -> 1-10 picker, posts to Trakt
  * refresh_metadata(...)             -> Drop local TMDB cache for title
  * play_then_continue_similar(...)   -> Play title, auto-open SALTS Info
                                         for top similar when playback ends

Persistent cache:
  special://profile/addon_data/<addon>/tmdb_cache/<sha1>.json
  - keyed by endpoint + sorted query params
  - TTL: 7 days (configurable via TMDB_CACHE_TTL)
"""
import hashlib
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from urllib.parse import quote_plus
from urllib.request import Request, urlopen

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ICON = os.path.join(ADDON_PATH, 'icon.png')
ADDON_FANART = os.path.join(ADDON_PATH, 'fanart.jpg')

ADDON_DATA_PATH = xbmcvfs.translatePath(
    f'special://profile/addon_data/{ADDON_ID}/'
)
TMDB_CACHE_DIR = os.path.join(ADDON_DATA_PATH, 'tmdb_cache')
TMDB_CACHE_TTL = 7 * 24 * 60 * 60   # 7 days

TMDB_KEY = '8265bd1679663a7ea12ac168da84d2e8'
TMDB_BASE = 'https://api.themoviedb.org/3'
TMDB_IMG = 'https://image.tmdb.org/t/p'

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

# Control IDs (synced with salts_meta.xml)
C_BACKDROP   = 110
C_POSTER     = 111
C_TITLE      = 120
C_TAGLINE    = 121
C_META_LINE  = 122
C_RATING     = 123
C_GENRES     = 124
C_PLOT       = 130
C_LIST       = 200

T_INFO       = 301
T_CAST       = 302
T_SIMILAR    = 303
T_TRAILERS   = 304

B_PLAY       = 401
B_FAV        = 402
B_WATCHLIST  = 403
B_CLOSE      = 404


# ---------------------------------------------------------------------------
# Local TMDB cache
# ---------------------------------------------------------------------------

def _ensure_cache_dir():
    try:
        if not os.path.isdir(TMDB_CACHE_DIR):
            os.makedirs(TMDB_CACHE_DIR, exist_ok=True)
    except Exception as e:
        xbmc.log(f'SALTS tmdb_cache mkdir: {e}', xbmc.LOGWARNING)


def _cache_key(path, params):
    """Stable sha1 of endpoint + sorted query params."""
    parts = [path]
    if params:
        for k in sorted(params.keys()):
            v = params[k]
            if v is None or v == '':
                continue
            parts.append(f'{k}={v}')
    raw = '|'.join(parts).encode('utf-8')
    return hashlib.sha1(raw).hexdigest()


def _cache_path(key):
    return os.path.join(TMDB_CACHE_DIR, f'{key}.json')


def _cache_read(key, ttl=TMDB_CACHE_TTL):
    fp = _cache_path(key)
    try:
        if not os.path.isfile(fp):
            return None
        if (time.time() - os.path.getmtime(fp)) > ttl:
            return None
        with open(fp, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return None


def _cache_write(key, payload):
    _ensure_cache_dir()
    try:
        with open(_cache_path(key), 'w', encoding='utf-8') as fh:
            json.dump(payload, fh)
    except Exception as e:
        xbmc.log(f'SALTS tmdb_cache write {key}: {e}', xbmc.LOGDEBUG)


def clear_tmdb_cache(tmdb_id=None):
    """Wipe cache for one tmdb_id (best-effort substring match in payload)
    or the entire cache when tmdb_id is None."""
    _ensure_cache_dir()
    try:
        for fn in os.listdir(TMDB_CACHE_DIR):
            if not fn.endswith('.json'):
                continue
            fp = os.path.join(TMDB_CACHE_DIR, fn)
            if tmdb_id is None:
                try:
                    os.remove(fp)
                except Exception:
                    pass
                continue
            # Targeted: peek inside; remove if it references this id.
            try:
                with open(fp, 'r', encoding='utf-8') as fh:
                    blob = fh.read()
                if f'"id":{tmdb_id}' in blob or f'/{tmdb_id}' in blob:
                    os.remove(fp)
            except Exception:
                pass
    except Exception as e:
        xbmc.log(f'SALTS clear_tmdb_cache: {e}', xbmc.LOGWARNING)


# ---------------------------------------------------------------------------
# TMDB helpers
# ---------------------------------------------------------------------------

def _tmdb(path, params=None, use_cache=True, ttl=TMDB_CACHE_TTL):
    """GET against TMDB v3 with on-disk caching (keyed by path + params)."""
    key = _cache_key(path, params)
    if use_cache:
        hit = _cache_read(key, ttl=ttl)
        if hit is not None:
            return hit
    try:
        q = f'api_key={TMDB_KEY}'
        if params:
            for k, v in params.items():
                if v is None or v == '':
                    continue
                q += f'&{k}={quote_plus(str(v))}'
        url = f'{TMDB_BASE}{path}?{q}'
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if use_cache and isinstance(data, (dict, list)):
            _cache_write(key, data)
        return data
    except Exception as e:
        xbmc.log(f'SALTS TMDB error {path}: {e}', xbmc.LOGWARNING)
        return {}


def _tmdb_path(media_type, tmdb_id, sub=''):
    base = 'movie' if media_type == 'movie' else 'tv'
    p = f'/{base}/{tmdb_id}'
    if sub:
        p += f'/{sub}'
    return p


def _norm_media_type(mt):
    """Normalise to 'movie' or 'tvshow' for params; 'movie'/'tv' for TMDB."""
    return 'movie' if mt == 'movie' else 'tvshow'


def _trakt_media_type(mt):
    """Plural form expected by this fork's trakt_api."""
    return 'movies' if mt in ('movie',) else 'shows'


# ---------------------------------------------------------------------------
# build_context_menu
# ---------------------------------------------------------------------------

def build_context_menu(build_url, media_type, title, year, tmdb_id,
                       poster='', fanart='', overview='', rating=0,
                       extras=None):
    """Return a list of (label, action) tuples for ListItem.addContextMenuItems()."""
    mt = _norm_media_type(media_type)
    common = {
        'media_type': mt,
        'title': title,
        'year': year,
        'tmdb_id': tmdb_id,
        'poster': poster,
        'fanart': fanart,
        'overview': (overview or '')[:240],
        'rating': str(rating or 0),
    }

    ctx = list(extras or [])

    info_url = build_url({'mode': 'salts_info', **common})
    ctx.append(('[B][COLOR FFFFD700]SALTS Info[/COLOR][/B]',
                f'RunPlugin({info_url})'))

    trailer_url = build_url({'mode': 'salts_trailer',
                             'media_type': mt, 'title': title,
                             'tmdb_id': tmdb_id})
    ctx.append(('Watch Trailer', f'RunPlugin({trailer_url})'))

    cast_url = build_url({'mode': 'salts_cast',
                          'media_type': mt, 'title': title,
                          'tmdb_id': tmdb_id})
    ctx.append(('Cast & Crew', f'RunPlugin({cast_url})'))

    similar_url = build_url({'mode': 'salts_similar',
                             'media_type': mt, 'tmdb_id': tmdb_id,
                             'title': title})
    ctx.append(('Similar Titles', f'Container.Update({similar_url})'))

    fav_url = build_url({'mode': 'add_favorite', **common})
    ctx.append(('Add to Favorites', f'RunPlugin({fav_url})'))

    trakt_wl_url = build_url({'mode': 'salts_trakt_watchlist',
                              'media_type': mt, 'tmdb_id': tmdb_id,
                              'title': title, 'year': year})
    ctx.append(('Trakt: Toggle Watchlist', f'RunPlugin({trakt_wl_url})'))

    trakt_wd_url = build_url({'mode': 'salts_trakt_watched',
                              'media_type': mt, 'tmdb_id': tmdb_id,
                              'title': title, 'year': year})
    ctx.append(('Trakt: Mark Watched / Unwatched',
                f'RunPlugin({trakt_wd_url})'))

    trakt_rate_url = build_url({'mode': 'salts_trakt_rate',
                                'media_type': mt, 'tmdb_id': tmdb_id,
                                'title': title})
    ctx.append(('Trakt: Rate (1-10)', f'RunPlugin({trakt_rate_url})'))

    if mt == 'movie':
        play_chain_url = build_url({'mode': 'salts_play_continue',
                                    'media_type': mt, 'tmdb_id': tmdb_id,
                                    'title': title, 'year': year,
                                    'poster': poster, 'fanart': fanart})
        ctx.append(('Play + Continue with Similar',
                    f'RunPlugin({play_chain_url})'))

    refresh_url = build_url({'mode': 'salts_refresh_meta',
                             'tmdb_id': tmdb_id, 'title': title})
    ctx.append(('Refresh Metadata Cache', f'RunPlugin({refresh_url})'))

    return ctx


# ---------------------------------------------------------------------------
# The Window
# ---------------------------------------------------------------------------

class SaltsMetaWindow(xbmcgui.WindowXMLDialog):
    """Salts-style fullscreen metadata viewer (Info / Cast / Similar / Trailers)."""

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, 'salts_meta.xml', ADDON_PATH,
                               'Default', '720p')

    def __init__(self, media_type, title, year, tmdb_id,
                 poster='', fanart='', overview='', rating=0):
        super().__init__()
        self.media_type = 'movie' if media_type == 'movie' else 'tv'
        self.title = title or ''
        self.year = year or ''
        self.tmdb_id = str(tmdb_id or '')
        self.poster = poster or ''
        self.fanart = fanart or ''
        self.overview = overview or ''
        self.rating = rating or 0

        self._details = {}
        self._cast = []
        self._similar = []
        self._videos = []
        self._active_tab = T_INFO
        self._action = None

    # ---- lifecycle ------------------------------------------------------

    def onInit(self):
        self._details = _tmdb(_tmdb_path(self.media_type, self.tmdb_id),
                              {'append_to_response':
                               'credits,similar,videos,recommendations'})

        try:
            self.getControl(C_BACKDROP).setImage(
                self.fanart or self._best_backdrop())
        except Exception:
            pass
        try:
            self.getControl(C_POSTER).setImage(
                self.poster or self._best_poster())
        except Exception:
            pass

        for cid, value in (
            (C_TITLE, self._headline_title()),
            (C_TAGLINE, self._details.get('tagline') or ''),
            (C_META_LINE, self._meta_line()),
            (C_RATING, self._rating_line()),
            (C_GENRES, self._genre_line()),
            (C_PLOT, self._details.get('overview') or self.overview or ''),
        ):
            try:
                self.getControl(cid).setLabel(value)
            except Exception:
                pass

        self._cast = (self._details.get('credits') or {}).get('cast') or []
        self._similar = (self._details.get('similar') or {}).get('results') \
            or (self._details.get('recommendations') or {}).get('results') \
            or []
        self._videos = (self._details.get('videos') or {}).get('results') or []

        self._render_tab(T_INFO)
        try:
            self.setFocusId(T_INFO)
        except Exception:
            pass

    # ---- formatters -----------------------------------------------------

    def _headline_title(self):
        if self.year:
            return f'{self.title} ({self.year})'
        rel = self._details.get('release_date') or \
            self._details.get('first_air_date') or ''
        if rel[:4].isdigit():
            return f'{self.title} ({rel[:4]})'
        return self.title

    def _best_poster(self):
        p = self._details.get('poster_path') or ''
        return f'{TMDB_IMG}/w500{p}' if p else ADDON_ICON

    def _best_backdrop(self):
        b = self._details.get('backdrop_path') or ''
        return f'{TMDB_IMG}/original{b}' if b else ADDON_FANART

    def _meta_line(self):
        bits = []
        rel = self._details.get('release_date') or \
            self._details.get('first_air_date') or ''
        if rel:
            bits.append(rel[:10])
        runtime = self._details.get('runtime')
        if not runtime:
            ert = self._details.get('episode_run_time') or []
            if ert:
                runtime = ert[0]
        if runtime:
            bits.append(f'{runtime} min')
        status = self._details.get('status')
        if status:
            bits.append(status)
        return '   |   '.join(bits)

    def _rating_line(self):
        vote = self._details.get('vote_average') or self.rating or 0
        try:
            vote = float(vote)
        except Exception:
            vote = 0.0
        count = self._details.get('vote_count') or 0
        return f'[COLOR FFFFD700]★ {vote:.1f}[/COLOR]  ({count:,} votes)'

    def _genre_line(self):
        genres = self._details.get('genres') or []
        return '  /  '.join([g.get('name', '') for g in genres if g.get('name')])

    # ---- tab rendering --------------------------------------------------

    def _set_list(self, items):
        try:
            lst = self.getControl(C_LIST)
            lst.reset()
            lst.addItems(items)
        except Exception:
            pass

    def _render_tab(self, tab_id):
        self._active_tab = tab_id
        if tab_id == T_INFO:
            self._render_info()
        elif tab_id == T_CAST:
            self._render_cast()
        elif tab_id == T_SIMILAR:
            self._render_similar()
        elif tab_id == T_TRAILERS:
            self._render_trailers()

    def _render_info(self):
        items = []
        prod = self._details.get('production_companies') or []
        if prod:
            items.append(xbmcgui.ListItem(
                '[B]Studio:[/B] ' +
                ', '.join([p.get('name', '') for p in prod if p.get('name')])
            ))
        countries = self._details.get('production_countries') or []
        if countries:
            items.append(xbmcgui.ListItem(
                '[B]Country:[/B] ' +
                ', '.join([c.get('name', '') for c in countries if c.get('name')])
            ))
        langs = self._details.get('spoken_languages') or []
        if langs:
            items.append(xbmcgui.ListItem(
                '[B]Language:[/B] ' +
                ', '.join([l.get('english_name') or l.get('name', '')
                           for l in langs])
            ))
        budget = self._details.get('budget')
        if budget:
            items.append(xbmcgui.ListItem(f'[B]Budget:[/B] ${budget:,}'))
        revenue = self._details.get('revenue')
        if revenue:
            items.append(xbmcgui.ListItem(f'[B]Revenue:[/B] ${revenue:,}'))
        seasons = self._details.get('number_of_seasons')
        if seasons:
            episodes = self._details.get('number_of_episodes') or 0
            items.append(xbmcgui.ListItem(
                f'[B]Seasons:[/B] {seasons}    [B]Episodes:[/B] {episodes}'))
        networks = self._details.get('networks') or []
        if networks:
            items.append(xbmcgui.ListItem(
                '[B]Network:[/B] ' +
                ', '.join([n.get('name', '') for n in networks if n.get('name')])
            ))
        creators = self._details.get('created_by') or []
        if creators:
            items.append(xbmcgui.ListItem(
                '[B]Created by:[/B] ' +
                ', '.join([c.get('name', '') for c in creators if c.get('name')])
            ))
        crew = (self._details.get('credits') or {}).get('crew') or []
        directors = [c.get('name') for c in crew if c.get('job') == 'Director']
        writers = [c.get('name') for c in crew
                   if c.get('department') == 'Writing']
        if directors:
            items.append(xbmcgui.ListItem(
                '[B]Director:[/B] ' + ', '.join(directors[:4])))
        if writers:
            items.append(xbmcgui.ListItem(
                '[B]Writers:[/B] ' + ', '.join(writers[:4])))
        if not items:
            items.append(xbmcgui.ListItem('No additional info available.'))
        self._set_list(items)

    def _render_cast(self):
        items = []
        for c in self._cast[:40]:
            name = c.get('name') or ''
            char = c.get('character') or ''
            label = f'[B]{name}[/B]'
            if char:
                label += f'   [I]as {char}[/I]'
            li = xbmcgui.ListItem(label)
            pp = c.get('profile_path')
            if pp:
                li.setArt({'thumb': f'{TMDB_IMG}/w185{pp}',
                           'icon': f'{TMDB_IMG}/w185{pp}'})
            items.append(li)
        if not items:
            items.append(xbmcgui.ListItem('No cast information available.'))
        self._set_list(items)

    def _render_similar(self):
        items = []
        for s in self._similar[:30]:
            t = s.get('title') or s.get('name') or ''
            rel = s.get('release_date') or s.get('first_air_date') or ''
            year = rel[:4] if rel else ''
            label = f'{t} ({year})' if year else t
            vote = s.get('vote_average') or 0
            try:
                if float(vote) > 0:
                    label += f'   [COLOR FFFFD700]★ {float(vote):.1f}[/COLOR]'
            except Exception:
                pass
            li = xbmcgui.ListItem(label)
            pp = s.get('poster_path')
            if pp:
                li.setArt({'thumb': f'{TMDB_IMG}/w342{pp}',
                           'icon': f'{TMDB_IMG}/w342{pp}'})
            items.append(li)
        if not items:
            items.append(xbmcgui.ListItem('No similar titles found.'))
        self._set_list(items)

    def _render_trailers(self):
        items = []
        ranked = sorted(
            self._videos,
            key=lambda v: (
                0 if v.get('site') == 'YouTube' else 1,
                0 if v.get('type') == 'Trailer' else
                1 if v.get('type') == 'Teaser' else 2
            )
        )
        for v in ranked[:20]:
            label = f'[{v.get("type", "Video")}] {v.get("name", "")}'
            if v.get('site') != 'YouTube':
                label += f'  ({v.get("site", "")})'
            items.append(xbmcgui.ListItem(label))
        if not items:
            items.append(xbmcgui.ListItem('No trailers available.'))
        self._set_list(items)

    # ---- input ----------------------------------------------------------

    def onClick(self, control_id):
        if control_id in (T_INFO, T_CAST, T_SIMILAR, T_TRAILERS):
            self._render_tab(control_id)
            return

        if control_id == C_LIST:
            try:
                pos = self.getControl(C_LIST).getSelectedPosition()
            except Exception:
                pos = -1
            if self._active_tab == T_SIMILAR and 0 <= pos < len(self._similar):
                self._action = ('open_similar', self._similar[pos])
                self.close()
            elif self._active_tab == T_TRAILERS and 0 <= pos < len(self._videos):
                ranked = sorted(
                    self._videos,
                    key=lambda v: (
                        0 if v.get('site') == 'YouTube' else 1,
                        0 if v.get('type') == 'Trailer' else
                        1 if v.get('type') == 'Teaser' else 2
                    )
                )
                if pos < len(ranked):
                    v = ranked[pos]
                    if v.get('site') == 'YouTube' and v.get('key'):
                        self._action = ('play_youtube', v.get('key'))
                        self.close()
            return

        if control_id == B_PLAY:
            self._action = ('play', None)
            self.close()
        elif control_id == B_FAV:
            self._action = ('add_favorite', None)
            self.close()
        elif control_id == B_WATCHLIST:
            self._action = ('trakt_watchlist', None)
            self.close()
        elif control_id == B_CLOSE:
            self.close()

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()

    def pop_action(self):
        a = self._action
        self._action = None
        return a


# ---------------------------------------------------------------------------
# Convenience entrypoints called from default.py router
# ---------------------------------------------------------------------------

def open_meta_window(build_url, media_type, title, year, tmdb_id,
                     poster='', fanart='', overview='', rating=0):
    if not tmdb_id:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No TMDB id for this title',
                                      ADDON_ICON)
        return

    win = SaltsMetaWindow(media_type, title, year, tmdb_id,
                          poster=poster, fanart=fanart,
                          overview=overview, rating=rating)
    win.doModal()
    action = win.pop_action()
    del win

    if not action:
        return

    kind, payload = action
    mt = _norm_media_type(media_type)

    if kind == 'play':
        if mt == 'movie':
            url = build_url({'mode': 'get_sources', 'title': title,
                             'year': year, 'media_type': 'movie',
                             'tmdb_id': tmdb_id})
            xbmc.executebuiltin(f'RunPlugin({url})')
        else:
            url = build_url({'mode': 'tv_seasons', 'title': title,
                             'year': year, 'tmdb_id': tmdb_id})
            xbmc.executebuiltin(f'Container.Update({url})')

    elif kind == 'add_favorite':
        url = build_url({'mode': 'add_favorite', 'media_type': mt,
                         'title': title, 'year': year, 'tmdb_id': tmdb_id,
                         'poster': poster, 'overview': (overview or '')[:200],
                         'rating': str(rating or 0)})
        xbmc.executebuiltin(f'RunPlugin({url})')

    elif kind == 'trakt_watchlist':
        trakt_watchlist_toggle(mt, tmdb_id, title=title, year=year)

    elif kind == 'play_youtube':
        play_youtube_key(payload)

    elif kind == 'open_similar':
        sel = payload or {}
        new_title = sel.get('title') or sel.get('name') or ''
        new_year = (sel.get('release_date') or
                    sel.get('first_air_date') or '')[:4]
        new_id = str(sel.get('id') or '')
        new_poster = (f'{TMDB_IMG}/w500{sel.get("poster_path")}'
                      if sel.get('poster_path') else '')
        new_fanart = (f'{TMDB_IMG}/original{sel.get("backdrop_path")}'
                      if sel.get('backdrop_path') else '')
        open_meta_window(build_url, media_type, new_title, new_year, new_id,
                         poster=new_poster, fanart=new_fanart,
                         overview=sel.get('overview') or '',
                         rating=sel.get('vote_average') or 0)


def play_trailer(media_type, tmdb_id, title=''):
    if not tmdb_id:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No TMDB id', ADDON_ICON)
        return
    mt = 'movie' if media_type == 'movie' else 'tv'
    data = _tmdb(_tmdb_path(mt, tmdb_id, 'videos'))
    results = data.get('results') or []
    ranked = sorted(
        results,
        key=lambda v: (
            0 if v.get('site') == 'YouTube' else 1,
            0 if v.get('type') == 'Trailer' else
            1 if v.get('type') == 'Teaser' else 2
        )
    )
    for v in ranked:
        if v.get('site') == 'YouTube' and v.get('key'):
            play_youtube_key(v['key'], title=title)
            return
    xbmcgui.Dialog().notification(ADDON_NAME, 'No trailer found', ADDON_ICON)


def play_youtube_key(key, title=''):
    yt_url = f'plugin://plugin.video.youtube/play/?video_id={key}'
    li = xbmcgui.ListItem(label=title or 'Trailer', path=yt_url)
    li.setProperty('IsPlayable', 'true')
    xbmc.Player().play(yt_url, li)


def show_cast(media_type, tmdb_id, title=''):
    if not tmdb_id:
        return
    mt = 'movie' if media_type == 'movie' else 'tv'
    data = _tmdb(_tmdb_path(mt, tmdb_id, 'credits'))
    cast = (data.get('cast') or [])[:60]
    if not cast:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No cast data', ADDON_ICON)
        return
    labels = []
    for c in cast:
        nm = c.get('name') or ''
        ch = c.get('character') or ''
        labels.append(f'{nm}   —   {ch}' if ch else nm)
    sel = xbmcgui.Dialog().select(f'Cast - {title}'.strip(' -'), labels)
    if sel < 0:
        return
    person = cast[sel]
    show_person_credits(person.get('id'), person.get('name', ''))


def show_person_credits(person_id, name=''):
    if not person_id:
        return
    data = _tmdb(f'/person/{person_id}/combined_credits')
    items = (data.get('cast') or []) + (data.get('crew') or [])
    items.sort(key=lambda x: (x.get('release_date') or
                              x.get('first_air_date') or ''),
               reverse=True)
    labels = []
    for it in items[:80]:
        t = it.get('title') or it.get('name') or ''
        rel = it.get('release_date') or it.get('first_air_date') or ''
        y = rel[:4] if rel else ''
        ch = it.get('character') or it.get('job') or ''
        line = f'{t} ({y})' if y else t
        if ch:
            line += f'   — {ch}'
        labels.append(line)
    if not labels:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No credits', ADDON_ICON)
        return
    xbmcgui.Dialog().select(f'Credits - {name}'.strip(' -'), labels)


# ---------------------------------------------------------------------------
# Trakt actions (locked to this fork's trakt_api surface)
# ---------------------------------------------------------------------------

def _get_trakt():
    """Return an authorised TraktAPI() or None (with user notice)."""
    try:
        from salts_lib.trakt_api import TraktAPI
    except Exception as e:
        xbmc.log(f'SALTS trakt import: {e}', xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(ADDON_NAME, 'Trakt module unavailable',
                                      ADDON_ICON)
        return None
    try:
        trakt = TraktAPI()
        if hasattr(trakt, 'is_authorized') and not trakt.is_authorized():
            xbmcgui.Dialog().notification(ADDON_NAME,
                                          'Connect Trakt first (Tools)',
                                          ADDON_ICON)
            return None
        return trakt
    except Exception as e:
        xbmc.log(f'SALTS trakt init: {e}', xbmc.LOGWARNING)
        return None


def _trakt_item_payload(tmdb_id):
    return [{'ids': {'tmdb': int(tmdb_id)}}]


def _in_trakt_list(items, tmdb_id, plural):
    """Return True if a watchlist/watched response contains this tmdb_id."""
    if not items or not isinstance(items, list):
        return False
    sub = 'movie' if plural == 'movies' else 'show'
    try:
        target = int(tmdb_id)
    except Exception:
        return False
    for it in items:
        node = (it.get(sub) if isinstance(it, dict) else None) or {}
        ids = node.get('ids') or {}
        if ids.get('tmdb') == target:
            return True
    return False


def trakt_watchlist_toggle(media_type, tmdb_id, title='', year=''):
    """TRUE toggle: check current watchlist, then add or remove."""
    if not tmdb_id:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No TMDB id', ADDON_ICON)
        return
    trakt = _get_trakt()
    if not trakt:
        return

    plural = _trakt_media_type(_norm_media_type(media_type))
    payload = _trakt_item_payload(tmdb_id)

    try:
        current = trakt.get_watchlist(media_type=plural)
        already_in = _in_trakt_list(current, tmdb_id, plural)
        if already_in:
            trakt.remove_from_watchlist(plural, payload)
            msg = f'Trakt: removed "{title}" from watchlist'
        else:
            trakt.add_to_watchlist(plural, payload)
            msg = f'Trakt: added "{title}" to watchlist'
        xbmcgui.Dialog().notification(ADDON_NAME, msg, ADDON_ICON, 4000)
    except Exception as e:
        xbmc.log(f'SALTS trakt_watchlist_toggle: {e}', xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(ADDON_NAME,
                                      'Trakt watchlist update failed',
                                      ADDON_ICON)


def trakt_watched_toggle(media_type, tmdb_id, title='', year=''):
    """TRUE toggle for /sync/history (movies/shows)."""
    if not tmdb_id:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No TMDB id', ADDON_ICON)
        return
    trakt = _get_trakt()
    if not trakt:
        return

    plural = _trakt_media_type(_norm_media_type(media_type))
    payload = _trakt_item_payload(tmdb_id)

    try:
        watched = trakt.get_watched(media_type=plural)
        already_in = _in_trakt_list(watched, tmdb_id, plural)
        if already_in:
            trakt.mark_unwatched(plural, payload)
            msg = f'Trakt: "{title}" marked UNwatched'
        else:
            trakt.mark_watched(plural, payload)
            msg = f'Trakt: "{title}" marked watched'
        xbmcgui.Dialog().notification(ADDON_NAME, msg, ADDON_ICON, 4000)
    except Exception as e:
        xbmc.log(f'SALTS trakt_watched_toggle: {e}', xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(ADDON_NAME,
                                      'Trakt watched update failed',
                                      ADDON_ICON)


def trakt_rate_dialog(media_type, tmdb_id, title=''):
    """Ask the user for a 1-10 rating and post it via /sync/ratings."""
    if not tmdb_id:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No TMDB id', ADDON_ICON)
        return
    trakt = _get_trakt()
    if not trakt:
        return

    labels = [str(n) for n in range(1, 11)]
    sel = xbmcgui.Dialog().select(f'Rate "{title}" 1-10', labels)
    if sel < 0:
        return
    rating = sel + 1

    plural = _trakt_media_type(_norm_media_type(media_type))
    sub = 'movie' if plural == 'movies' else 'show'
    data = {plural: [{'ids': {'tmdb': int(tmdb_id)}, 'rating': rating}]}
    try:
        # Use the underlying _call_api so we don't depend on rate()'s
        # trakt-id requirement.
        trakt._call_api('/sync/ratings', method='POST', data=data)
        xbmcgui.Dialog().notification(ADDON_NAME,
                                      f'Trakt: rated "{title}" {rating}/10',
                                      ADDON_ICON, 4000)
    except Exception as e:
        xbmc.log(f'SALTS trakt_rate_dialog: {e}', xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(ADDON_NAME,
                                      'Trakt rating failed', ADDON_ICON)
    # Touch the sub var so linters don't whine about it being unused
    _ = sub


# ---------------------------------------------------------------------------
# Refresh / cache helpers
# ---------------------------------------------------------------------------

def refresh_metadata(tmdb_id, title=''):
    """Drop local TMDB cache for the given tmdb_id."""
    clear_tmdb_cache(tmdb_id or None)
    xbmcgui.Dialog().notification(ADDON_NAME,
                                  f'Metadata cache cleared: {title}'.strip(': '),
                                  ADDON_ICON, 3000)


# ---------------------------------------------------------------------------
# Play + Continue with Similar
# ---------------------------------------------------------------------------

def play_then_continue_similar(build_url, media_type, tmdb_id, title='',
                               year='', poster='', fanart=''):
    """
    Movies only: kick off playback via the normal SALTS sources flow, then
    sit on a Player monitor and, when the file ends, open the SALTS Info
    window for the top-rated similar title (highest vote_average that
    SALTS has not just played).
    """
    if _norm_media_type(media_type) != 'movie':
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            'Continue-with-Similar is movies only (for now)',
            ADDON_ICON)
        return

    if not tmdb_id:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No TMDB id', ADDON_ICON)
        return

    data = _tmdb(_tmdb_path('movie', tmdb_id),
                 {'append_to_response': 'similar,recommendations'})
    pool = ((data.get('similar') or {}).get('results') or []) + \
           ((data.get('recommendations') or {}).get('results') or [])
    # Highest-rated (require non-zero vote_count to skip ghosts)
    pool = [p for p in pool if (p.get('vote_count') or 0) >= 50
            and str(p.get('id')) != str(tmdb_id)]
    pool.sort(key=lambda x: (float(x.get('vote_average') or 0),
                             int(x.get('vote_count') or 0)),
              reverse=True)
    nxt = pool[0] if pool else None

    play_url = build_url({'mode': 'get_sources', 'title': title,
                          'year': year, 'media_type': 'movie',
                          'tmdb_id': tmdb_id})
    xbmcgui.Dialog().notification(
        ADDON_NAME,
        f'Playing "{title}" - next up: {nxt.get("title") if nxt else "n/a"}',
        ADDON_ICON, 3000
    )
    xbmc.executebuiltin(f'RunPlugin({play_url})')

    if not nxt:
        return

    # Wait for playback to actually start, then for it to end.
    monitor = xbmc.Monitor()
    player = xbmc.Player()
    waited = 0
    while not monitor.abortRequested() and waited < 60:
        if player.isPlayingVideo():
            break
        if monitor.waitForAbort(1):
            return
        waited += 1
    else:
        # Playback never started; bail cleanly.
        return

    # Now wait for the player to stop.
    while not monitor.abortRequested():
        if not player.isPlayingVideo():
            break
        if monitor.waitForAbort(2):
            return

    # Open SALTS Info for the next title.
    nxt_title = nxt.get('title') or nxt.get('name') or ''
    nxt_year = (nxt.get('release_date') or '')[:4]
    nxt_id = str(nxt.get('id') or '')
    nxt_poster = (f'{TMDB_IMG}/w500{nxt.get("poster_path")}'
                  if nxt.get('poster_path') else '')
    nxt_fanart = (f'{TMDB_IMG}/original{nxt.get("backdrop_path")}'
                  if nxt.get('backdrop_path') else '')
    info_url = build_url({'mode': 'salts_info', 'media_type': 'movie',
                          'title': nxt_title, 'year': nxt_year,
                          'tmdb_id': nxt_id, 'poster': nxt_poster,
                          'fanart': nxt_fanart,
                          'overview': (nxt.get('overview') or '')[:240],
                          'rating': str(nxt.get('vote_average') or 0)})
    xbmc.executebuiltin(f'RunPlugin({info_url})')
