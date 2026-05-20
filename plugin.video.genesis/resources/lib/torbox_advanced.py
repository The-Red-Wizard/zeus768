# -*- coding: utf-8 -*-
"""
TorBox advanced integration for Genesis.

Surfaces the full TorBox v1 API beyond basic magnet -> play:

  * Torrent queue control     (pause/resume/reannounce/stop_seeding/delete)
  * Usenet downloads          (add NZB URL/file, browse, play, control)
  * Web Downloads (DDL)       (add URL, browse, play, control)
  * Built-in search           (/torrents/search)
  * Live progress / ETA       (download_speed, eta, progress, seeds)
  * Multi-file picker         (let user pick which file to stream)
  * Account dashboard         (plan, expiry, totals, server, customer)
  * Re-queue for stalled items
  * Direct stream URL         (requestdl with token)

All calls go through the lightweight HTTP helpers we already use in
debrid.py and reuse the saved API key.
"""

import json
import os
import time
import xbmc
import xbmcgui

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

from . import debrid

USER_AGENT = 'Genesis Kodi Addon'

# ── HTTP helpers (kept local so this module is self-contained) ────────────


def _http(url, method='GET', data=None, headers=None, timeout=30):
    hdrs = {'User-Agent': USER_AGENT}
    if headers:
        hdrs.update(headers)

    post_data = None
    if data is not None:
        if isinstance(data, dict):
            post_data = urlencode(data).encode('utf-8')
            hdrs.setdefault('Content-Type', 'application/x-www-form-urlencoded')
        elif isinstance(data, str):
            post_data = data.encode('utf-8')
        elif isinstance(data, bytes):
            post_data = data

    try:
        req = Request(url, data=post_data, headers=hdrs, method=method)
        resp = urlopen(req, timeout=timeout)
        body = resp.read().decode('utf-8', errors='replace')
        try:
            return resp.getcode(), json.loads(body)
        except json.JSONDecodeError:
            return resp.getcode(), body
    except HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8')
        except Exception:
            pass
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body
    except URLError as e:
        xbmc.log(f'TorboxAdvanced URLError: {e.reason}', xbmc.LOGERROR)
        return 0, None
    except Exception as e:
        xbmc.log(f'TorboxAdvanced HTTP error: {e}', xbmc.LOGERROR)
        return 0, None


def _get(url, params=None, headers=None, timeout=30):
    if params:
        sep = '&' if '?' in url else '?'
        url = f'{url}{sep}{urlencode(params)}'
    return _http(url, 'GET', headers=headers, timeout=timeout)


def _post(url, data=None, params=None, headers=None, timeout=30):
    if params:
        sep = '&' if '?' in url else '?'
        url = f'{url}{sep}{urlencode(params)}'
    return _http(url, 'POST', data=data, headers=headers, timeout=timeout)


def _fmt_size(n):
    try:
        n = float(n or 0)
    except Exception:
        return ''
    for u in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{n:.1f} {u}'
        n /= 1024
    return f'{n:.1f} PB'


def _fmt_eta(seconds):
    try:
        s = int(seconds or 0)
    except Exception:
        return ''
    if s <= 0:
        return ''
    if s < 60:
        return f'{s}s'
    m, s = divmod(s, 60)
    if m < 60:
        return f'{m}m {s}s'
    h, m = divmod(m, 60)
    if h < 24:
        return f'{h}h {m}m'
    d, h = divmod(h, 24)
    return f'{d}d {h}h'


# ── Core ──────────────────────────────────────────────────────────────────


class TorboxAdvanced:
    """Wrapper around the TorBox client offering everything the API exposes."""

    BASE_URL = 'https://api.torbox.app/v1/api'

    def __init__(self):
        self.client = debrid.Torbox()

    # ---- guards & helpers --------------------------------------------------
    @property
    def token(self):
        return self.client.token

    def is_authorized(self):
        return self.client.is_authorized()

    def _auth_headers(self, json_body=False):
        h = {'Authorization': f'Bearer {self.token}'}
        if json_body:
            h['Content-Type'] = 'application/json'
        return h

    @staticmethod
    def _ok(result):
        return isinstance(result, dict) and result.get('success')

    # ---- account / dashboard ----------------------------------------------
    def me(self):
        if not self.is_authorized():
            return {}
        _, res = _get(f'{self.BASE_URL}/user/me', headers=self._auth_headers())
        return res if isinstance(res, dict) else {}

    def stats(self):
        """Returns the global TorBox stats (cached torrents, queue, etc.)."""
        _, res = _get(f'{self.BASE_URL}/stats', headers=self._auth_headers())
        return res if isinstance(res, dict) else {}

    def dashboard(self):
        """Aggregated account snapshot used by the dashboard UI."""
        info = self.me()
        if not self._ok(info):
            return None
        data = info.get('data') or {}
        plans = {0: 'Free', 1: 'Essential', 2: 'Pro', 3: 'Standard'}
        plan_id = data.get('plan', 0) or 0
        premium_until = (data.get('premium_expires_at')
                         or data.get('plan_active_until') or '')
        days_left = 0
        exp_str = 'Unknown'
        if premium_until:
            try:
                from datetime import datetime
                exp_date = datetime.strptime(str(premium_until)[:19],
                                             '%Y-%m-%dT%H:%M:%S')
                delta = exp_date - datetime.utcnow()
                days_left = max(0, delta.days)
                exp_str = exp_date.strftime('%Y-%m-%d')
            except Exception:
                exp_str = str(premium_until)[:10]
        return {
            'email': data.get('email', ''),
            'plan': plans.get(plan_id, str(plan_id)),
            'plan_id': plan_id,
            'is_premium': bool(plan_id),
            'expiration': exp_str,
            'days_left': days_left,
            'total_downloaded': _fmt_size(data.get('total_downloaded', 0)),
            'server': data.get('server', ''),
            'customer': data.get('customer', ''),
            'is_subscribed': bool(data.get('is_subscribed')),
            'created_at': str(data.get('created_at', ''))[:10],
        }

    # ---- torrents: list / control -----------------------------------------
    def torrent_list(self, bypass_cache=True):
        params = {'bypass_cache': 'true' if bypass_cache else 'false'}
        _, res = _get(f'{self.BASE_URL}/torrents/mylist', params=params,
                      headers=self._auth_headers())
        if not self._ok(res):
            return []
        data = res.get('data') or []
        if isinstance(data, dict):
            data = [data]
        return data

    def torrent_info(self, torrent_id):
        _, res = _get(f'{self.BASE_URL}/torrents/mylist',
                      params={'id': torrent_id, 'bypass_cache': 'true'},
                      headers=self._auth_headers())
        if not self._ok(res):
            return None
        data = res.get('data') or {}
        if isinstance(data, list) and data:
            data = data[0]
        return data

    def torrent_control(self, torrent_id, operation):
        """operation: delete | pause | resume | reannounce | stop_seeding |
        resume_seeding | queue_top | queue_bottom"""
        return _post(
            f'{self.BASE_URL}/torrents/controltorrent',
            data=json.dumps({'torrent_id': torrent_id, 'operation': operation}),
            headers=self._auth_headers(json_body=True),
        )

    def queue_torrent(self, magnet, seed=3, allow_zip=False, as_queued=True):
        """Submit a magnet to TorBox even if not cached - used when the user
        opts to "Add to TorBox Cloud" from the uncached-source dialog."""
        data = {
            'magnet': magnet,
            'seed': str(seed),
            'allow_zip': 'true' if allow_zip else 'false',
            'as_queued': 'true' if as_queued else 'false',
        }
        _, res = _post(f'{self.BASE_URL}/torrents/createtorrent',
                       data=data, headers=self._auth_headers())
        return res if isinstance(res, dict) else None

    # ---- usenet -----------------------------------------------------------
    def usenet_list(self, bypass_cache=True):
        _, res = _get(f'{self.BASE_URL}/usenet/mylist',
                      params={'bypass_cache': 'true' if bypass_cache else 'false'},
                      headers=self._auth_headers())
        if not self._ok(res):
            return []
        data = res.get('data') or []
        if isinstance(data, dict):
            data = [data]
        return data

    def add_nzb_url(self, url, name=''):
        data = {'link': url}
        if name:
            data['name'] = name
        _, res = _post(f'{self.BASE_URL}/usenet/createusenetdownload',
                       data=data, headers=self._auth_headers())
        return res

    def usenet_control(self, usenet_id, operation):
        return _post(
            f'{self.BASE_URL}/usenet/controlusenetdownload',
            data=json.dumps({'usenet_id': usenet_id, 'operation': operation}),
            headers=self._auth_headers(json_body=True),
        )

    def usenet_requestdl(self, usenet_id, file_id=0):
        _, res = _get(
            f'{self.BASE_URL}/usenet/requestdl',
            params={'token': self.token, 'usenet_id': usenet_id,
                    'file_id': file_id},
            headers=self._auth_headers(),
        )
        if self._ok(res):
            return res.get('data')
        return None

    # ---- web downloads (DDL hosters) --------------------------------------
    def webdl_list(self, bypass_cache=True):
        _, res = _get(f'{self.BASE_URL}/webdl/mylist',
                      params={'bypass_cache': 'true' if bypass_cache else 'false'},
                      headers=self._auth_headers())
        if not self._ok(res):
            return []
        data = res.get('data') or []
        if isinstance(data, dict):
            data = [data]
        return data

    def add_webdl(self, url, name=''):
        data = {'link': url}
        if name:
            data['name'] = name
        _, res = _post(f'{self.BASE_URL}/webdl/createwebdownload',
                       data=data, headers=self._auth_headers())
        return res

    def webdl_control(self, webdl_id, operation):
        return _post(
            f'{self.BASE_URL}/webdl/controlwebdownload',
            data=json.dumps({'webdl_id': webdl_id, 'operation': operation}),
            headers=self._auth_headers(json_body=True),
        )

    def webdl_requestdl(self, webdl_id, file_id=0):
        _, res = _get(
            f'{self.BASE_URL}/webdl/requestdl',
            params={'token': self.token, 'web_id': webdl_id,
                    'file_id': file_id},
            headers=self._auth_headers(),
        )
        if self._ok(res):
            return res.get('data')
        return None

    # ---- search -----------------------------------------------------------
    def search(self, query, category='', season='', episode=''):
        """TorBox built-in scraped search. Returns a list of result dicts
        with keys: title, magnet, hash, size, seeders, leechers, source.

        Falls back gracefully to [] if TorBox doesn't return data."""
        if not query:
            return []
        params = {'search': query, 'metadata': 'true'}
        if category:
            params['category'] = category
        if season:
            params['season'] = season
        if episode:
            params['episode'] = episode
        # Endpoint shape: GET /torrents/search?search=...
        _, res = _get(f'{self.BASE_URL}/torrents/search', params=params,
                      headers=self._auth_headers(), timeout=20)
        if not self._ok(res):
            return []
        out = []
        for item in (res.get('data') or []):
            try:
                magnet = item.get('magnet') or ''
                if not magnet and item.get('hash'):
                    magnet = f"magnet:?xt=urn:btih:{item['hash']}"
                out.append({
                    'title': item.get('title') or item.get('raw_title') or '',
                    'magnet': magnet,
                    'hash': (item.get('hash') or '').lower(),
                    'size': int(item.get('size') or 0),
                    'seeds': int(item.get('seeders') or item.get('seeds') or 0),
                    'leechers': int(item.get('leechers') or 0),
                    'source': 'TorBox',
                    'category': item.get('category', ''),
                    'raw': item,
                })
            except Exception:
                continue
        return out

    # ---- direct stream link -----------------------------------------------
    def requestdl(self, torrent_id, file_id):
        """Returns a direct CDN URL playable by Kodi."""
        _, res = _get(
            f'{self.BASE_URL}/torrents/requestdl',
            params={'token': self.token, 'torrent_id': torrent_id,
                    'file_id': file_id},
            headers=self._auth_headers(),
        )
        if self._ok(res):
            return res.get('data')
        return None

    # ---- multi-file helper ------------------------------------------------
    VIDEO_EXTS = ('.mkv', '.mp4', '.avi', '.mov', '.m4v', '.ts', '.m2ts',
                  '.wmv', '.flv', '.webm', '.mpg', '.mpeg')

    def pick_file_from_torrent(self, torrent_id, prompt=True):
        """Return (file_id, filename) - either auto-picks the largest video
        or shows a selection dialog when prompt=True and there are >1 video
        files."""
        info = self.torrent_info(torrent_id)
        if not info:
            return None, None
        files = info.get('files') or []
        videos = []
        for f in files:
            name = (f.get('short_name') or f.get('name') or '').strip()
            if name.lower().endswith(self.VIDEO_EXTS):
                videos.append({
                    'id': f.get('id', 0),
                    'name': name,
                    'size': int(f.get('size', 0) or 0),
                })
        if not videos:
            return None, None
        videos.sort(key=lambda x: x['size'], reverse=True)
        if not prompt or len(videos) == 1:
            return videos[0]['id'], videos[0]['name']
        labels = [f"{v['name']}  [COLOR silver]({_fmt_size(v['size'])})[/COLOR]"
                  for v in videos]
        idx = xbmcgui.Dialog().select('Pick a file to play', labels)
        if idx < 0:
            return None, None
        return videos[idx]['id'], videos[idx]['name']


# ── Convenience formatters used by the UI ────────────────────────────────


def format_torrent_progress(item):
    """Return a one-line status string for a queued/downloading torrent."""
    try:
        prog = float(item.get('progress') or 0)
    except Exception:
        prog = 0
    if prog <= 1:  # API returns 0..1
        prog *= 100
    state = item.get('download_state') or item.get('state') or ''
    speed = item.get('download_speed') or 0
    eta = _fmt_eta(item.get('eta'))
    seeds = item.get('seeds') or 0
    peers = item.get('peers') or 0
    parts = [f'{prog:0.1f}%']
    if state:
        parts.append(state)
    if speed:
        parts.append(f'{_fmt_size(speed)}/s')
    if eta:
        parts.append(f'ETA {eta}')
    if seeds or peers:
        parts.append(f'S{seeds}/P{peers}')
    return ' • '.join(parts)


def progress_bar(progress, width=20):
    """ASCII-ish progress bar for menu labels."""
    try:
        p = float(progress or 0)
    except Exception:
        p = 0
    if p <= 1:
        p *= 100
    p = max(0, min(100, p))
    filled = int(width * p / 100)
    return '[' + '█' * filled + '░' * (width - filled) + f'] {p:0.1f}%'
