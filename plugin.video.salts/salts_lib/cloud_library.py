"""
SALTS - Cloud smart library.

Scans every connected cloud provider (GDrive + MEGA), parses each video
filename to detect Movie vs TV episode, matches against TMDB for poster /
fanart / overview, and caches the result for fast re-rendering.

Rendering helpers split the library into Movies / TV Shows / Recently Added
in the Plex/Salts style.
"""
import json
import re
import time
import os
import sqlite3
import xbmc
import xbmcaddon
import xbmcgui
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

ADDON = xbmcaddon.Addon()
ADDON_NAME = 'SALTS'
ADDON_ICON = ADDON.getAddonInfo('icon')

TMDB_KEY = '8265bd1679663a7ea12ac168da84d2e8'
TMDB_BASE = 'https://api.themoviedb.org/3'
TMDB_IMG = 'https://image.tmdb.org/t/p'

# --- filename parsing -----------------------------------------------

_TV_RE = re.compile(r'(.+?)[. _-]+[Ss](\d{1,2})[. _-]?[Ee](\d{1,2})', re.I)
_YEAR_RE = re.compile(r'(.+?)[. _\-(\[]+(19\d{2}|20\d{2})')


def parse_filename(name):
    """Return (kind, title, year_or_season, episode_or_None).
    kind ∈ {'movie','tv','unknown'}.
    """
    base = os.path.splitext(name)[0]
    base = base.replace('.', ' ').replace('_', ' ').strip()
    m = _TV_RE.search(base)
    if m:
        title = m.group(1).strip(' .-_[(')
        return 'tv', title, int(m.group(2)), int(m.group(3))
    m = _YEAR_RE.search(base)
    if m:
        title = m.group(1).strip(' .-_[(')
        return 'movie', title, int(m.group(2)), None
    return 'unknown', base, None, None


# --- TMDB match -----------------------------------------------------

def _tmdb(path, params):
    p = {'api_key': TMDB_KEY, **params}
    q = '&'.join(f'{k}={quote_plus(str(v))}' for k, v in p.items())
    try:
        req = Request(f'{TMDB_BASE}{path}?{q}',
                      headers={'User-Agent': 'Mozilla/5.0'})
        return json.loads(urlopen(req, timeout=15).read().decode('utf-8'))
    except Exception:
        return None


def tmdb_lookup(kind, title, year=None):
    if kind == 'movie':
        params = {'query': title}
        if year:
            params['year'] = year
        d = _tmdb('/search/movie', params)
    elif kind == 'tv':
        d = _tmdb('/search/tv', {'query': title})
    else:
        return None
    if not d or not d.get('results'):
        return None
    return d['results'][0]


# --- cache (SQLite alongside the existing salts DB) -----------------

def _db_path():
    prof = xbmc.translatePath('special://profile/addon_data/plugin.video.salts/') \
        if hasattr(xbmc, 'translatePath') else \
        ADDON.getAddonInfo('profile')
    try:
        os.makedirs(prof, exist_ok=True)
    except Exception:
        pass
    return os.path.join(prof, 'cloud_library.db')


def _conn():
    c = sqlite3.connect(_db_path())
    c.execute('''CREATE TABLE IF NOT EXISTS cloud_items (
        provider TEXT, file_id TEXT, name TEXT, size INTEGER,
        kind TEXT, title TEXT, year INTEGER, season INTEGER, episode INTEGER,
        tmdb_id INTEGER, poster TEXT, backdrop TEXT, overview TEXT,
        rating REAL, added INTEGER,
        PRIMARY KEY (provider, file_id))''')
    return c


def cache_age_hours():
    try:
        c = _conn()
        row = c.execute('SELECT MAX(added) FROM cloud_items').fetchone()
        c.close()
        if row and row[0]:
            return (time.time() - row[0]) / 3600.0
    except Exception:
        pass
    return None


def save_items(provider, items):
    c = _conn()
    now = int(time.time())
    c.execute('DELETE FROM cloud_items WHERE provider = ?', (provider,))
    rows = []
    for it in items:
        rows.append((provider, it['file_id'], it['name'], it.get('size', 0),
                     it['kind'], it['title'], it.get('year') or 0,
                     it.get('season') or 0, it.get('episode') or 0,
                     it.get('tmdb_id') or 0, it.get('poster', ''),
                     it.get('backdrop', ''), it.get('overview', ''),
                     it.get('rating') or 0.0, now))
    c.executemany('INSERT OR REPLACE INTO cloud_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', rows)
    c.commit()
    c.close()


def load_items(kind=None):
    c = _conn()
    if kind:
        cur = c.execute('SELECT provider,file_id,name,size,kind,title,year,season,episode,tmdb_id,poster,backdrop,overview,rating,added FROM cloud_items WHERE kind=? ORDER BY added DESC',
                        (kind,))
    else:
        cur = c.execute('SELECT provider,file_id,name,size,kind,title,year,season,episode,tmdb_id,poster,backdrop,overview,rating,added FROM cloud_items ORDER BY added DESC')
    cols = ['provider','file_id','name','size','kind','title','year','season','episode','tmdb_id','poster','backdrop','overview','rating','added']
    out = [dict(zip(cols, r)) for r in cur.fetchall()]
    c.close()
    return out


# --- scanner --------------------------------------------------------

def scan_all(force=False):
    """Scan every enabled provider, parse, TMDB-match, persist.
    Returns total number of indexed video files."""
    cache_h = float(ADDON.getSetting('cloud_library_cache_hours') or 24)
    age = cache_age_hours()
    if not force and age is not None and age < cache_h:
        return None  # cache is fresh

    pd = xbmcgui.DialogProgress()
    pd.create(ADDON_NAME, 'Scanning cloud library...')

    total = 0
    if ADDON.getSetting('gdrive_enabled') == 'true':
        try:
            from salts_lib import cloud_gdrive
            if cloud_gdrive.is_authed():
                pd.update(5, 'Google Drive: listing videos...')
                files = cloud_gdrive.list_all_videos(
                    progress_cb=lambda s, f: pd.update(min(40, 5 + s // 50),
                                                       f'Google Drive: {f} videos found'))
                total += _enrich_and_save('gdrive', files, pd, base_pct=40)
        except Exception as e:
            xbmc.log(f'cloud_library: gdrive scan error: {e}', xbmc.LOGWARNING)

    if ADDON.getSetting('mega_enabled') == 'true':
        try:
            from salts_lib import cloud_mega
            if cloud_mega.is_authed():
                pd.update(50, 'MEGA.nz: listing videos...')
                files = cloud_mega.list_all_videos(
                    progress_cb=lambda s, f: pd.update(min(80, 50 + s // 50),
                                                       f'MEGA: {f} videos found'))
                total += _enrich_and_save('mega', files, pd, base_pct=80)
        except Exception as e:
            xbmc.log(f'cloud_library: mega scan error: {e}', xbmc.LOGWARNING)

    if ADDON.getSetting('pcloud_enabled') == 'true':
        try:
            from salts_lib import cloud_pcloud
            if cloud_pcloud.is_authed():
                pd.update(82, 'pCloud: listing videos...')
                files = cloud_pcloud.list_all_videos(
                    progress_cb=lambda s, f: pd.update(min(88, 82 + s // 200),
                                                       f'pCloud: {f} videos found'))
                total += _enrich_and_save('pcloud', files, pd, base_pct=88)
        except Exception as e:
            xbmc.log(f'cloud_library: pcloud scan error: {e}', xbmc.LOGWARNING)

    if ADDON.getSetting('mediafire_enabled') == 'true':
        try:
            from salts_lib import cloud_mediafire
            if cloud_mediafire.is_authed():
                pd.update(89, 'MediaFire: listing videos...')
                files = cloud_mediafire.list_all_videos(
                    progress_cb=lambda s, f: pd.update(min(94, 89 + s // 200),
                                                       f'MediaFire: {f} videos found'))
                total += _enrich_and_save('mediafire', files, pd, base_pct=94)
        except Exception as e:
            xbmc.log(f'cloud_library: mediafire scan error: {e}', xbmc.LOGWARNING)

    # iDrive: account mode (WebDAV / iDrive e2 S3) takes precedence over
    # shared links.  If both are configured, account mode wins for the
    # `idrive` provider key; shared links can still be used by leaving the
    # account fields blank.
    if ADDON.getSetting('idrive_enabled') == 'true':
        try:
            from salts_lib import cloud_idrive
            if cloud_idrive.is_authed():
                mode = (ADDON.getSetting('idrive_mode') or 'webdav').upper()
                pd.update(95, f'iDrive ({mode}): listing videos...')
                files = cloud_idrive.list_all_videos(
                    progress_cb=lambda s, f: pd.update(
                        min(97, 95 + s // 50),
                        f'iDrive ({mode}): {f} videos found'))
                total += _enrich_and_save('idrive', files, pd, base_pct=97)
            else:
                # Fallback: shared-link mode for iDrive
                from salts_lib import cloud_sharedlinks
                if cloud_sharedlinks.is_authed('idrive'):
                    pd.update(95, 'iDrive: resolving share links...')
                    files = cloud_sharedlinks.list_all_videos(
                        'idrive',
                        progress_cb=lambda s, f:
                            pd.update(min(97, 95 + s),
                                      f'iDrive: {f} link(s)'))
                    total += _enrich_and_save('idrive', files, pd, base_pct=97)
        except Exception as e:
            xbmc.log(f'cloud_library: idrive scan error: {e}',
                     xbmc.LOGWARNING)

    if ADDON.getSetting('sync_enabled') == 'true':
        try:
            from salts_lib import cloud_sharedlinks
            if cloud_sharedlinks.is_authed('sync'):
                pd.update(97, 'Sync.com: resolving share links...')
                files = cloud_sharedlinks.list_all_videos(
                    'sync',
                    progress_cb=lambda s, f:
                        pd.update(min(99, 97 + s),
                                  f'Sync.com: {f} link(s)'))
                total += _enrich_and_save('sync', files, pd, base_pct=99)
        except Exception as e:
            xbmc.log(f'cloud_library: sync scan error: {e}',
                     xbmc.LOGWARNING)

    pd.update(100, f'Done. {total} videos indexed.')
    xbmc.sleep(400)
    pd.close()
    return total


def _enrich_and_save(provider, files, pd, base_pct):
    """Parse + TMDB-match each file and save into the library cache."""
    out = []
    n = len(files) or 1
    for i, f in enumerate(files):
        if pd.iscanceled():
            break
        kind, title, y_or_s, ep = parse_filename(f.get('name', ''))
        item = {
            'file_id': f.get('id', ''),
            'name': f.get('name', ''),
            'size': int(f.get('size', 0) or 0),
            'kind': kind, 'title': title, 'year': None, 'season': None, 'episode': None,
            'tmdb_id': 0, 'poster': '', 'backdrop': '', 'overview': '', 'rating': 0.0,
        }
        if kind == 'movie':
            item['year'] = y_or_s
            md = tmdb_lookup('movie', title, y_or_s)
            if md:
                item['tmdb_id'] = md.get('id', 0)
                if md.get('poster_path'):
                    item['poster'] = f'{TMDB_IMG}/w500{md["poster_path"]}'
                if md.get('backdrop_path'):
                    item['backdrop'] = f'{TMDB_IMG}/original{md["backdrop_path"]}'
                item['overview'] = md.get('overview', '')
                item['rating'] = md.get('vote_average', 0.0)
                # Re-fix display title to the canonical one TMDB returns.
                if md.get('title'):
                    item['title'] = md['title']
                if md.get('release_date'):
                    yr = md['release_date'][:4]
                    if yr.isdigit():
                        item['year'] = int(yr)
        elif kind == 'tv':
            item['season'] = y_or_s
            item['episode'] = ep
            md = tmdb_lookup('tv', title)
            if md:
                item['tmdb_id'] = md.get('id', 0)
                if md.get('poster_path'):
                    item['poster'] = f'{TMDB_IMG}/w500{md["poster_path"]}'
                if md.get('backdrop_path'):
                    item['backdrop'] = f'{TMDB_IMG}/original{md["backdrop_path"]}'
                item['overview'] = md.get('overview', '')
                item['rating'] = md.get('vote_average', 0.0)
                if md.get('name'):
                    item['title'] = md['name']
        out.append(item)
        if i % 5 == 0:
            pct = base_pct - 10 + int(10 * i / n)
            pd.update(max(0, min(99, pct)), f'{provider}: matching {i+1}/{n}')
    save_items(provider, out)
    return len(out)


# --- send-to-debrid -------------------------------------------------

def get_stream_url(provider, file_id):
    if provider == 'gdrive':
        from salts_lib import cloud_gdrive
        return cloud_gdrive.get_stream_url(file_id)
    if provider == 'mega':
        from salts_lib import cloud_mega
        return cloud_mega.get_stream_url(file_id)
    if provider == 'pcloud':
        from salts_lib import cloud_pcloud
        return cloud_pcloud.get_stream_url(file_id)
    if provider == 'mediafire':
        from salts_lib import cloud_mediafire
        return cloud_mediafire.get_stream_url(file_id)
    if provider == 'idrive':
        # Prefer account mode when configured, fall back to share links.
        from salts_lib import cloud_idrive
        if cloud_idrive.is_authed():
            return cloud_idrive.get_stream_url(file_id)
        from salts_lib import cloud_sharedlinks
        return cloud_sharedlinks.get_stream_url('idrive', file_id)
    if provider == 'sync':
        from salts_lib import cloud_sharedlinks
        return cloud_sharedlinks.get_stream_url('sync', file_id)
    return None


def get_share_url(provider, file_id):
    """Public/share URL suitable for handing off to a debrid service."""
    if provider == 'gdrive':
        from salts_lib import cloud_gdrive
        return cloud_gdrive.get_share_url(file_id)
    if provider == 'mega':
        from salts_lib import cloud_mega
        return cloud_mega.get_stream_url(file_id)  # MEGA shared link is public
    if provider == 'pcloud':
        from salts_lib import cloud_pcloud
        return cloud_pcloud.get_share_url(file_id)
    if provider == 'mediafire':
        from salts_lib import cloud_mediafire
        return cloud_mediafire.get_share_url(file_id)
    if provider == 'idrive':
        from salts_lib import cloud_idrive
        if cloud_idrive.is_authed():
            return cloud_idrive.get_share_url(file_id)
        from salts_lib import cloud_sharedlinks
        return cloud_sharedlinks.get_share_url('idrive', file_id)
    if provider == 'sync':
        from salts_lib import cloud_sharedlinks
        return cloud_sharedlinks.get_share_url('sync', file_id)
    return None


# --- debrid push ---------------------------------------------------

def send_to_debrid(target, url, name=''):
    """Send a direct URL to a debrid service.
    target ∈ {'torbox','realdebrid','alldebrid','premiumize'}.
    Returns True on success.
    """
    try:
        if target == 'torbox':
            tok = ADDON.getSetting('torbox_token').strip()
            if not tok:
                return False
            from urllib.parse import urlencode
            data = urlencode({'link': url, 'name': name}).encode()
            req = Request('https://api.torbox.app/v1/api/webdl/createwebdownload',
                          data=data,
                          headers={'Authorization': f'Bearer {tok}'})
            urlopen(req, timeout=20).read()
            return True
        if target == 'realdebrid':
            tok = ADDON.getSetting('realdebrid_token').strip()
            if not tok:
                return False
            from urllib.parse import urlencode
            data = urlencode({'link': url}).encode()
            req = Request('https://api.real-debrid.com/rest/1.0/unrestrict/link',
                          data=data,
                          headers={'Authorization': f'Bearer {tok}'})
            urlopen(req, timeout=20).read()
            return True
        if target == 'alldebrid':
            tok = ADDON.getSetting('alldebrid_token').strip()
            if not tok:
                return False
            from urllib.parse import quote_plus as _q
            full = f'https://api.alldebrid.com/v4/link/unlock?agent=SALTS&apikey={tok}&link={_q(url)}'
            urlopen(Request(full), timeout=20).read()
            return True
        if target == 'premiumize':
            tok = ADDON.getSetting('premiumize_token').strip()
            if not tok:
                return False
            from urllib.parse import urlencode
            data = urlencode({'apikey': tok, 'src': url}).encode()
            req = Request('https://www.premiumize.me/api/transfer/create', data=data)
            urlopen(req, timeout=20).read()
            return True
    except Exception as e:
        xbmc.log(f'send_to_debrid({target}) error: {e}', xbmc.LOGWARNING)
        return False
    return False


def send_to_debrid_prompt(provider, file_id, name=''):
    """Ask the user which enabled debrid to push to, then push."""
    targets = []
    if ADDON.getSetting('torbox_enabled') == 'true':
        targets.append(('torbox', 'TorBox'))
    if ADDON.getSetting('realdebrid_enabled') == 'true':
        targets.append(('realdebrid', 'Real-Debrid'))
    if ADDON.getSetting('alldebrid_enabled') == 'true':
        targets.append(('alldebrid', 'AllDebrid'))
    if ADDON.getSetting('premiumize_enabled') == 'true':
        targets.append(('premiumize', 'Premiumize'))
    if not targets:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No debrid services enabled', ADDON_ICON)
        return
    idx = xbmcgui.Dialog().select('Send to Debrid', [t[1] for t in targets])
    if idx < 0:
        return
    url = get_share_url(provider, file_id)
    if not url:
        xbmcgui.Dialog().notification(ADDON_NAME, 'Could not resolve share URL', ADDON_ICON)
        return
    ok = send_to_debrid(targets[idx][0], url, name)
    xbmcgui.Dialog().notification(ADDON_NAME,
        f'{"Sent" if ok else "Failed"}: {targets[idx][1]}', ADDON_ICON)
