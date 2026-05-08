"""
Poseidon Player - STB Stalker Portal (MAC) protocol
---------------------------------------------------
Implements the Stalker middleware protocol used by MAC-based IPTV portals.

Flow:
  1) handshake   -> token
  2) get_profile -> activate session
  3) itv.get_genres / itv.get_all_channels
  4) itv.create_link(cmd) -> real stream URL

Session state (token, used portal base, channel cache) is cached in memory
for a single Kodi process; Xtream Codes mode is unaffected.

Response shapes are normalised to match Xtream Codes so the rest of
main.py does not need to branch on every call.
"""
import json
import time
import random
import urllib.parse
import requests

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
UA = 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 250 Safari/533.3'
TIMEOUT = 20

# Common portal load paths, tried in order.
PORTAL_PATHS = (
    '/portal.php',
    '/stalker_portal/server/load.php',
    '/server/load.php',
    '/c/portal.php',
)


def log(msg, lvl=xbmc.LOGINFO):
    xbmc.log(f'[PoseidonMAC] {msg}', lvl)


# ------------------------------------------------------------------
# Session object (lightweight, rebuilt per-process)
# ------------------------------------------------------------------
class StalkerSession(object):
    def __init__(self):
        self.base = None          # e.g. https://portal.tld
        self.portal = None        # e.g. https://portal.tld/portal.php
        self.mac = None
        self.sn = None
        self.token = None
        self.token_expires = 0
        self._channels = []       # raw channels list (itv get_all_channels)
        self._channels_fetched = 0
        self._cmd_by_id = {}      # stream_id -> cmd
        self._genres = []

    def is_authed(self):
        return bool(self.token) and time.time() < self.token_expires


_SESSION = StalkerSession()


def get_session():
    return _SESSION


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _normalise_portal(dns):
    dns = (dns or '').strip().rstrip('/')
    if not dns:
        return None
    if not dns.startswith('http://') and not dns.startswith('https://'):
        dns = 'http://' + dns
    # Strip any trailing /portal.php etc. - we re-probe.
    for suffix in ('/portal.php', '/stalker_portal/server/load.php', '/c', '/c/'):
        if dns.endswith(suffix):
            dns = dns[: -len(suffix)]
    return dns.rstrip('/')


def _serial_from_mac(mac):
    """Generate a deterministic serial number from a MAC address.
    Many portals accept any 13-char uppercase alphanumeric value; the one
    below matches the pattern used by MAG/Infomir firmware so portals that
    expect it won't reject us."""
    digest = ''.join(ch for ch in mac.replace(':', '').upper() if ch.isalnum())
    # Pad or trim to 13 chars
    return (digest + '000000000000000')[:13]


def _cookie_header(mac):
    return f'mac={mac};stb_lang=en;timezone=Europe/London'


def _headers(mac, token=None):
    h = {
        'User-Agent': UA,
        'Cookie': _cookie_header(mac),
        'X-User-Agent': 'Model: MAG254; Link: WiFi',
        'Accept': 'application/json',
    }
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h


def _http_get(url, headers, timeout=TIMEOUT):
    try:
        r = requests.get(url, headers=headers, timeout=timeout, verify=False)
        if r.status_code != 200:
            log(f'GET {url} -> {r.status_code}', xbmc.LOGWARNING)
            return None
        try:
            return r.json()
        except Exception:
            # Some portals return JSON with text/html content-type.
            try:
                return json.loads(r.text)
            except Exception as e:
                log(f'JSON parse failed for {url}: {e}', xbmc.LOGWARNING)
                return None
    except Exception as e:
        log(f'HTTP error {url}: {e}', xbmc.LOGERROR)
        return None


def _probe_portal(base, mac):
    """Try each well-known portal path until one answers a handshake OK."""
    for path in PORTAL_PATHS:
        url = f'{base}{path}?type=stb&action=handshake&JsHttpRequest=1-xml'
        data = _http_get(url, _headers(mac))
        if data and isinstance(data, dict) and data.get('js', {}).get('token'):
            return f'{base}{path}', data['js']['token']
    return None, None


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------
def authenticate(portal_url, mac_address):
    """Configure + handshake + get_profile. Returns True on success."""
    sess = get_session()
    base = _normalise_portal(portal_url)
    if not base:
        log('No portal URL supplied', xbmc.LOGERROR)
        return False
    mac = (mac_address or '').strip().upper()
    if len(mac) < 12:
        log(f'Invalid MAC: {mac}', xbmc.LOGERROR)
        return False

    portal, token = _probe_portal(base, mac)
    if not portal or not token:
        log(f'Handshake failed against {base}', xbmc.LOGERROR)
        return False

    sess.base = base
    sess.portal = portal
    sess.mac = mac
    sess.sn = _serial_from_mac(mac)
    sess.token = token
    sess.token_expires = time.time() + 3600  # 1h sliding

    # Call get_profile - some portals reject subsequent calls without it.
    profile_url = (f'{portal}?type=stb&action=get_profile'
                   f'&hd=1&ver=ImageDescription:%200.2.18-r14;ImageDate:%20Fri%20Jan%2015%202016'
                   f'&num_banks=2&sn={sess.sn}&stb_type=MAG250&client_type=STB'
                   f'&image_version=218&video_out=hdmi&device_id=&device_id2='
                   f'&signature=&auth_second_step=1&hw_version=1.7-BD-00'
                   f'&not_valid_token=0&metrics={{}}&hw_version_2=&timestamp={int(time.time())}'
                   f'&api_signature=263&prehash=&JsHttpRequest=1-xml')
    profile = _http_get(profile_url, _headers(mac, token))
    if not profile:
        log('get_profile returned nothing - continuing with token', xbmc.LOGWARNING)

    return True


def _ensure_auth():
    """Re-handshake silently if the token is gone."""
    sess = get_session()
    if sess.is_authed():
        return True
    portal_url = ADDON.getSetting('portal_url')
    mac = ADDON.getSetting('mac_address')
    if not portal_url or not mac:
        return False
    return authenticate(portal_url, mac)


def get_genres():
    """Return [{category_id, category_name}] - Xtream-shaped."""
    if not _ensure_auth():
        return []
    sess = get_session()
    if sess._genres:
        return sess._genres
    url = f'{sess.portal}?type=itv&action=get_genres&JsHttpRequest=1-xml'
    data = _http_get(url, _headers(sess.mac, sess.token))
    if not data:
        return []
    raw = data.get('js', data) or []
    genres = []
    for g in raw:
        gid = str(g.get('id', ''))
        title = g.get('title') or g.get('alias') or f'Genre {gid}'
        if gid and gid != '*':
            genres.append({'category_id': gid, 'category_name': title})
    sess._genres = genres
    return genres


def _fetch_all_channels():
    """Download the channel list once and cache it on the session."""
    sess = get_session()
    if sess._channels and (time.time() - sess._channels_fetched) < 1800:
        return sess._channels
    channels = []
    page = 1
    while True:
        url = (f'{sess.portal}?type=itv&action=get_all_channels&force_ch_link_check='
               f'&p={page}&JsHttpRequest=1-xml')
        data = _http_get(url, _headers(sess.mac, sess.token))
        if not data:
            break
        js = data.get('js', {})
        batch = js.get('data') if isinstance(js, dict) else None
        if not batch:
            break
        channels.extend(batch)
        total_items = js.get('total_items') if isinstance(js, dict) else None
        if not total_items or len(channels) >= int(total_items):
            break
        page += 1
        if page > 50:  # safety guard
            break
    sess._channels = channels
    sess._channels_fetched = time.time()
    sess._cmd_by_id = {str(c.get('id', '')): c.get('cmd', '') for c in channels}
    return channels


def get_channels_for_category(category_id):
    """Return Xtream-shaped stream list for a given category id."""
    if not _ensure_auth():
        return []
    all_channels = _fetch_all_channels()
    cat_id = str(category_id or '')
    out = []
    for c in all_channels:
        gid = str(c.get('tv_genre_id', ''))
        if cat_id and gid != cat_id:
            continue
        out.append({
            'stream_id': str(c.get('id', '')),
            'name': c.get('name', ''),
            'stream_icon': c.get('logo', '') or c.get('tv_genre_icon', ''),
            'epg_channel_id': c.get('xmltv_id', '') or str(c.get('id', '')),
            'category_id': gid,
            '_cmd': c.get('cmd', ''),
            'num': c.get('number', ''),
        })
    return out


def get_short_epg(stream_id, limit=10):
    """Return Xtream-shaped EPG listing for one channel."""
    if not _ensure_auth():
        return []
    sess = get_session()
    url = (f'{sess.portal}?type=itv&action=get_short_epg&ch_id={stream_id}'
           f'&size={int(limit)}&JsHttpRequest=1-xml')
    data = _http_get(url, _headers(sess.mac, sess.token))
    if not data:
        return []
    raw = data.get('js', []) or []
    out = []
    for p in raw:
        out.append({
            'title': p.get('name', ''),
            'description': p.get('descr', ''),
            'start': p.get('start_timestamp', 0),
            'end': p.get('stop_timestamp', 0),
            'start_timestamp': p.get('start_timestamp', 0),
            'stop_timestamp': p.get('stop_timestamp', 0),
            'has_archive': p.get('has_archive', 0),
        })
    return out


def create_link(stream_id, epg_start=None):
    """Resolve a channel's `cmd` into a playable URL.

    v2.6.1: If epg_start is given, also append an archive request so the
    portal returns the catch-up (archive) stream instead of live.
    """
    if not _ensure_auth():
        return None
    sess = get_session()
    # Make sure the channel list is cached so we can look up cmd.
    _fetch_all_channels()
    cmd = sess._cmd_by_id.get(str(stream_id))
    if not cmd:
        log(f'No cmd for stream_id={stream_id}', xbmc.LOGWARNING)
        return None
    encoded = urllib.parse.quote(cmd, safe='')
    archive_param = f'&archive={int(epg_start)}' if epg_start else ''
    url = (f'{sess.portal}?type=itv&action=create_link&cmd={encoded}'
           f'&forced_storage=undefined&disable_ad=0&download=0'
           f'{archive_param}'
           f'&JsHttpRequest=1-xml')
    data = _http_get(url, _headers(sess.mac, sess.token))
    if not data:
        return None
    js = data.get('js', {}) or {}
    raw = js.get('cmd') or js.get('url') or ''
    # Portals prefix the stream command with "ffmpeg " or "auto "
    for prefix in ('ffmpeg ', 'ffrt ', 'ffrt3 ', 'auto '):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    return raw.strip() or None


def get_catchup_programs(stream_id):
    """Return EPG listings from the archive window that are marked has_archive.

    Uses the portal's get_simple_data_table which covers the catch-up period
    (typically 1-7 days depending on the portal).
    """
    if not _ensure_auth():
        return []
    sess = get_session()
    url = (f'{sess.portal}?type=itv&action=get_simple_data_table'
           f'&genre=*&type=itv&force_ch_link_check=&fav=0&sortby=number'
           f'&hd=0&p=1&ch_id={stream_id}&JsHttpRequest=1-xml')
    data = _http_get(url, _headers(sess.mac, sess.token))
    if not data:
        return []
    js = data.get('js', {})
    raw = js.get('data') if isinstance(js, dict) else None
    if not raw:
        return []
    out = []
    now = time.time()
    for p in raw:
        if not p.get('has_archive'):
            continue
        start = int(p.get('start_timestamp') or 0)
        stop = int(p.get('stop_timestamp') or 0)
        if stop > now:
            continue  # only past programs have replayable archive
        out.append({
            'title': p.get('name', ''),
            'description': p.get('descr', ''),
            'start_timestamp': start,
            'stop_timestamp': stop,
            'has_archive': 1,
        })
    return out


def account_info():
    """Return a dict similar to Xtream's user_info for UI display."""
    if not _ensure_auth():
        return {}
    sess = get_session()
    url = (f'{sess.portal}?type=account_info&action=get_main_info'
           f'&JsHttpRequest=1-xml')
    data = _http_get(url, _headers(sess.mac, sess.token)) or {}
    js = data.get('js', {}) or {}
    phone = js.get('phone') or js.get('mac') or sess.mac
    return {
        'username': phone,
        'status': 'Active' if sess.token else 'Inactive',
        'exp_date': js.get('end_date') or js.get('expiry') or '',
        'is_trial': '0',
        'active_cons': 1,
        'max_connections': 1,
        'created_at': js.get('created_at', ''),
    }


def suggest_random_mac():
    """Generate a random MAG-style MAC (prefix 00:1A:79)."""
    return '00:1A:79:' + ':'.join(
        '{:02X}'.format(random.randint(0, 255)) for _ in range(3)
    )


def portal_mode():
    """Helper: true if addon currently configured for MAC mode."""
    return ADDON.getSetting('portal_mode') == 'mac'
