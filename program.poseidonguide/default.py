# -*- coding: utf-8 -*-
"""
Poseidon Guide v1.1.0
- UK channels first, then USA, then rest
- All categories loaded
- Proper EPG
- Added List View option with popup choice
"""

import sys
import os
import json
import time
import base64
from datetime import datetime, timedelta

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import requests

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
PLAYER_ADDON_ID = 'plugin.video.poseidonplayer'

CACHE_CHANNELS = os.path.join(ADDON_DATA, 'channels_cache.json')
CACHE_EPG = os.path.join(ADDON_DATA, 'epg_cache.json')
CACHE_MAX_AGE = 1800

if not xbmcvfs.exists(ADDON_DATA):
    xbmcvfs.mkdirs(ADDON_DATA)

def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)

def notify(msg, title=ADDON_NAME, icon=xbmcgui.NOTIFICATION_INFO, time=5000):
    xbmcgui.Dialog().notification(title, msg, icon, time)

def format_time(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%H:%M')
    except:
        return ''

def format_duration(s, e):
    try:
        d = int(e) - int(s)
        h, m = d // 3600, (d % 3600) // 60
        return f"{h}h {m}m" if h > 0 else f"{m}m"
    except:
        return ''

def decode_base64(s):
    if not s:
        return ''
    try:
        return base64.b64decode(s).decode('utf-8')
    except:
        return s

def load_cache(filepath):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('timestamp', 0) > time.time() - CACHE_MAX_AGE:
                    return data.get('data')
    except:
        pass
    return None

def save_cache(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({'timestamp': time.time(), 'data': data}, f)
    except:
        pass

def create_texture(filename, r, g, b):
    filepath = os.path.join(ADDON_DATA, filename)
    if os.path.exists(filepath):
        return filepath
    
    w, h = 8, 8
    size = 54 + w * h * 3
    bmp = bytearray(size)
    bmp[0:2] = b'BM'
    bmp[2:6] = size.to_bytes(4, 'little')
    bmp[10:14] = (54).to_bytes(4, 'little')
    bmp[14:18] = (40).to_bytes(4, 'little')
    bmp[18:22] = w.to_bytes(4, 'little')
    bmp[22:26] = h.to_bytes(4, 'little')
    bmp[26:28] = (1).to_bytes(2, 'little')
    bmp[28:30] = (24).to_bytes(2, 'little')
    
    for i in range(w * h):
        off = 54 + i * 3
        bmp[off], bmp[off+1], bmp[off+2] = b, g, r
    
    try:
        with open(filepath, 'wb') as f:
            f.write(bmp)
        return filepath
    except:
        return ''

def get_category_priority(cat_name):
    """
    Returns priority for sorting categories.
    Lower number = higher priority (appears first)
    """
    name = cat_name.upper()
    
    # UK Categories (priority 0-99)
    if 'UK' in name:
        if 'ENTERTAINMENT' in name or 'GENERAL' in name:
            return 1
        elif 'SPORT' in name:
            return 2
        elif 'MOVIE' in name or 'FILM' in name:
            return 3
        elif 'NEWS' in name:
            return 4
        elif 'KIDS' in name or 'CHILD' in name:
            return 5
        elif 'DOCUMENT' in name:
            return 6
        elif 'MUSIC' in name:
            return 7
        elif '+1' in name:
            return 8
        else:
            return 10
    
    # USA Categories (priority 100-199)
    elif 'USA' in name or 'US |' in name or 'US-' in name or name.startswith('US '):
        if 'ENTERTAINMENT' in name or 'GENERAL' in name:
            return 101
        elif 'SPORT' in name:
            return 102
        elif 'MOVIE' in name or 'FILM' in name:
            return 103
        elif 'NEWS' in name:
            return 104
        elif 'KIDS' in name:
            return 105
        else:
            return 110
    
    # Live/PPV events (priority 200-299)
    elif 'LIVE' in name or 'PPV' in name or 'EVENT' in name:
        return 200 + (0 if 'UK' in name else 50)
    
    # International (priority 300+)
    else:
        return 300

class PoseidonBridge:
    def __init__(self):
        self.addon = None
        self.creds = None
        try:
            self.addon = xbmcaddon.Addon(PLAYER_ADDON_ID)
        except:
            pass

    def installed(self):
        return self.addon is not None

    def mode(self):
        """v1.2.0: returns 'xtream' or 'mac' based on player addon's setting."""
        if not self.addon:
            return 'xtream'
        return self.addon.getSetting('portal_mode') or 'xtream'

    def get_creds(self):
        if not self.addon:
            return None
        if self.mode() == 'mac':
            portal = self.addon.getSetting('portal_url')
            mac = self.addon.getSetting('mac_address')
            if portal and mac:
                self.creds = {
                    'mode': 'mac',
                    'portal_url': portal.rstrip('/'),
                    'mac_address': mac.upper(),
                }
                return self.creds
            return None
        dns = self.addon.getSetting('dns')
        user = self.addon.getSetting('username')
        pwd = self.addon.getSetting('password')
        if dns and user and pwd:
            self.creds = {
                'mode': 'xtream',
                'dns': dns.rstrip('/'),
                'user': user,
                'pwd': pwd,
            }
            return self.creds
        return None

    def valid(self):
        return self.get_creds() is not None


# ------------------------------------------------------------------
# v1.2.0 - MAC / Stalker portal adapter
# ------------------------------------------------------------------
# Lightweight in-process state so we reuse the handshake across calls.
_MAC_STATE = {
    'portal': None,       # resolved portal URL (with /portal.php etc.)
    'token': None,
    'mac': None,
    'channels': [],
    'genres': [],
    'cmd_by_id': {},
    'fetched_at': 0,
}

_MAC_PATHS = (
    '/portal.php',
    '/stalker_portal/server/load.php',
    '/server/load.php',
    '/c/portal.php',
)
_MAC_UA = ('Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 '
           '(KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 250 Safari/533.3')


def _mac_headers(mac, token=None):
    h = {
        'User-Agent': _MAC_UA,
        'Cookie': f'mac={mac};stb_lang=en;timezone=Europe/London',
        'X-User-Agent': 'Model: MAG254; Link: WiFi',
        'Accept': 'application/json',
    }
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h


def _mac_get(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=25, verify=False)
        if r.status_code != 200:
            return None
        try:
            return r.json()
        except Exception:
            try:
                return json.loads(r.text)
            except Exception:
                return None
    except Exception:
        return None


def _mac_handshake(creds):
    base = creds['portal_url'].rstrip('/')
    for suffix in ('/portal.php', '/stalker_portal/server/load.php', '/c', '/c/'):
        if base.endswith(suffix):
            base = base[:-len(suffix)].rstrip('/')
    mac = creds['mac_address']
    for path in _MAC_PATHS:
        url = f'{base}{path}?type=stb&action=handshake&JsHttpRequest=1-xml'
        data = _mac_get(url, _mac_headers(mac))
        if data and isinstance(data, dict) and data.get('js', {}).get('token'):
            _MAC_STATE['portal'] = f'{base}{path}'
            _MAC_STATE['token'] = data['js']['token']
            _MAC_STATE['mac'] = mac
            return True
    return False


def _mac_ensure(creds):
    if _MAC_STATE['token'] and _MAC_STATE['mac'] == creds['mac_address']:
        return True
    return _mac_handshake(creds)


def _mac_fetch_channels(creds):
    if _MAC_STATE['channels'] and (time.time() - _MAC_STATE['fetched_at']) < 1800:
        return _MAC_STATE['channels']
    if not _mac_ensure(creds):
        return []
    all_ch = []
    page = 1
    while True:
        url = (f'{_MAC_STATE["portal"]}?type=itv&action=get_all_channels'
               f'&p={page}&JsHttpRequest=1-xml')
        data = _mac_get(url, _mac_headers(_MAC_STATE['mac'], _MAC_STATE['token']))
        if not data:
            break
        js = data.get('js', {})
        batch = js.get('data') if isinstance(js, dict) else None
        if not batch:
            break
        all_ch.extend(batch)
        total_items = js.get('total_items') if isinstance(js, dict) else None
        if not total_items or len(all_ch) >= int(total_items):
            break
        page += 1
        if page > 50:
            break
    _MAC_STATE['channels'] = all_ch
    _MAC_STATE['fetched_at'] = time.time()
    _MAC_STATE['cmd_by_id'] = {str(c.get('id', '')): c.get('cmd', '') for c in all_ch}
    return all_ch


def _mac_get_categories(creds):
    if not _mac_ensure(creds):
        return []
    if _MAC_STATE['genres']:
        return _MAC_STATE['genres']
    url = f'{_MAC_STATE["portal"]}?type=itv&action=get_genres&JsHttpRequest=1-xml'
    data = _mac_get(url, _mac_headers(_MAC_STATE['mac'], _MAC_STATE['token']))
    if not data:
        return []
    raw = data.get('js', data) or []
    genres = []
    for g in raw:
        gid = str(g.get('id', ''))
        if gid and gid != '*':
            genres.append({'category_id': gid,
                           'category_name': g.get('title') or g.get('alias') or f'Genre {gid}'})
    _MAC_STATE['genres'] = genres
    return genres


def _mac_get_streams(creds, cat_id):
    channels = _mac_fetch_channels(creds)
    out = []
    for c in channels:
        gid = str(c.get('tv_genre_id', ''))
        if cat_id and gid != str(cat_id):
            continue
        out.append({
            'stream_id': str(c.get('id', '')),
            'name': c.get('name', ''),
            'stream_icon': c.get('logo', '') or '',
            'epg_channel_id': c.get('xmltv_id', '') or str(c.get('id', '')),
            'category_id': gid,
            'num': c.get('number', ''),
        })
    return out


def _mac_get_epg(creds, stream_id, limit=15):
    if not _mac_ensure(creds):
        return []
    url = (f'{_MAC_STATE["portal"]}?type=itv&action=get_short_epg'
           f'&ch_id={stream_id}&size={int(limit)}&JsHttpRequest=1-xml')
    data = _mac_get(url, _mac_headers(_MAC_STATE['mac'], _MAC_STATE['token']))
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
        })
    return out


def api_call(bridge, action, params='', timeout=25):
    """v1.2.0: transparently routes to MAC adapter when portal_mode=mac."""
    c = bridge.get_creds()
    if not c:
        return None

    if c.get('mode') == 'mac':
        # Translate a limited set of player_api actions into Stalker calls.
        if action == 'get_live_categories':
            return _mac_get_categories(c)
        if action == 'get_live_streams':
            # params like "&category_id=123"
            cat_id = ''
            for p in params.split('&'):
                if p.startswith('category_id='):
                    cat_id = p.split('=', 1)[1]
                    break
            return _mac_get_streams(c, cat_id)
        if action == 'get_short_epg':
            stream_id = ''
            for p in params.split('&'):
                if p.startswith('stream_id='):
                    stream_id = p.split('=', 1)[1]
                    break
            listings = _mac_get_epg(c, stream_id)
            return {'epg_listings': listings} if listings else None
        # Unknown action in MAC mode - just return None.
        log(f'MAC adapter: unsupported action {action}', xbmc.LOGWARNING)
        return None

    url = f"{c['dns']}/player_api.php?username={c['user']}&password={c['pwd']}&action={action}{params}"
    try:
        r = requests.get(url, timeout=timeout, headers={'User-Agent': 'Kodi/20.0'})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log(f"API error {action}: {e}", xbmc.LOGERROR)
        return None

def get_categories(bridge):
    data = api_call(bridge, "get_live_categories")
    if isinstance(data, list):
        return sorted(data, key=lambda x: (get_category_priority(x.get('category_name', '')), x.get('category_name', '').lower()))
    return []

def get_streams(bridge, cat_id):
    data = api_call(bridge, "get_live_streams", f"&category_id={cat_id}")
    if isinstance(data, list):
        return data
    return []

def get_all_channels(bridge, progress=None, force_refresh=False):
    if not force_refresh:
        cached = load_cache(CACHE_CHANNELS)
        if cached:
            log(f"Channels from cache: {len(cached)}")
            return cached
    
    channels = []
    cats = get_categories(bridge)
    total_cats = len(cats)
    log(f"Total categories: {total_cats}")
    
    for i, cat in enumerate(cats):
        if progress and progress.iscanceled():
            break
        
        cat_name = cat.get('category_name', 'Unknown')
        cat_id = cat.get('category_id')
        priority = get_category_priority(cat_name)
        
        if progress:
            pct = int((i / max(total_cats, 1)) * 45)
            progress.update(pct, f"[{i+1}/{total_cats}] {cat_name[:40]}")
        
        streams = get_streams(bridge, cat_id)
        log(f"  [{priority}] {cat_name}: {len(streams)} ch")
        
        for idx, s in enumerate(streams):
            s['category_name'] = cat_name
            s['category_priority'] = priority
            s['channel_order'] = idx
            try:
                s['num'] = int(s.get('num', 0) or 0)
            except:
                s['num'] = 0
        
        channels.extend(streams)
    
    channels.sort(key=lambda x: (x.get('category_priority', 999), x.get('num', 0), x.get('channel_order', 0)))
    
    if channels:
        save_cache(CACHE_CHANNELS, channels)
    
    log(f"Total channels loaded: {len(channels)}")
    return channels

def get_epg(bridge, stream_id, limit=15):
    data = api_call(bridge, "get_short_epg", f"&stream_id={stream_id}&limit={limit}", timeout=10)
    if not data:
        return []
    
    listings = data.get('epg_listings', [])
    result = []
    for p in listings:
        item = {
            'title': decode_base64(p.get('title', '')),
            'description': decode_base64(p.get('description', '')),
            'start_timestamp': p.get('start_timestamp', 0),
            'stop_timestamp': p.get('stop_timestamp', 0),
        }
        result.append(item)
    return result

def get_all_epg(bridge, channels, progress=None, force_refresh=False):
    if not force_refresh:
        cached = load_cache(CACHE_EPG)
        if cached:
            log(f"EPG from cache: {len(cached)}")
            return cached
    
    epg_data = {}
    
    priority_channels = [ch for ch in channels if ch.get('category_priority', 999) < 200]
    other_channels = [ch for ch in channels if ch.get('category_priority', 999) >= 200]
    
    epg_channels = priority_channels[:150] + other_channels[:50]
    total = len(epg_channels)
    
    for i, ch in enumerate(epg_channels):
        if progress and progress.iscanceled():
            break
        
        if progress:
            pct = 50 + int((i / max(total, 1)) * 45)
            progress.update(pct, f"EPG [{i+1}/{total}] {ch.get('name', '')[:30]}")
        
        sid = str(ch.get('stream_id', ''))
        if not sid:
            continue
        
        epg = get_epg(bridge, sid, 20)
        if epg:
            epg_data[sid] = epg
    
    if epg_data:
        save_cache(CACHE_EPG, epg_data)
    
    log(f"EPG loaded for {len(epg_data)} channels")
    return epg_data

# ============================================================================
# LIST VIEW - Simple EPG List
# ============================================================================
class ListViewWindow(xbmcgui.WindowDialog):
    """Simple list view for EPG"""
    W, H = 1920, 1080
    
    def __init__(self, bridge, channels, epg_data):
        super().__init__()
        self.bridge = bridge
        self.channels = channels
        self.epg = epg_data or {}
        self.sel = 0
        self.scroll = 0
        self.rows = 12
        self.should_reopen = False
        
        self.tex_bg = create_texture('list_bg.bmp', 15, 25, 45)
        self.tex_header = create_texture('list_header.bmp', 10, 35, 60)
        self.tex_row = create_texture('list_row.bmp', 20, 40, 70)
        self.tex_sel = create_texture('list_sel.bmp', 0, 100, 140)
        self.tex_now = create_texture('list_now.bmp', 0, 130, 100)
        
        self.row_ctrls = []
        self.build()
    
    def build(self):
        # Background
        if self.tex_bg:
            self.addControl(xbmcgui.ControlImage(0, 0, self.W, self.H, self.tex_bg))
        
        # Header
        if self.tex_header:
            self.addControl(xbmcgui.ControlImage(0, 0, self.W, 60, self.tex_header))
        
        self.addControl(xbmcgui.ControlLabel(20, 15, 400, 30, 'POSEIDON GUIDE - LIST VIEW', font='font13', textColor='FFD4AF37'))
        
        tnow = datetime.now().strftime('%H:%M')
        self.addControl(xbmcgui.ControlLabel(self.W - 100, 18, 85, 25, tnow, font='font12', textColor='FFFFFFFF', alignment=1))
        
        self.addControl(xbmcgui.ControlLabel(450, 18, 300, 25, f'{len(self.channels)} channels', font='font10', textColor='FF90CAF9'))
        
        # Info panel
        y = 65
        if self.tex_header:
            self.addControl(xbmcgui.ControlImage(0, y, self.W, 80, self.tex_header))
        
        self.info_title = xbmcgui.ControlLabel(20, y + 10, self.W - 200, 28, '', font='font13', textColor='FF00E5FF')
        self.addControl(self.info_title)
        self.info_ch = xbmcgui.ControlLabel(20, y + 40, self.W - 200, 22, '', font='font11', textColor='FFFFFFFF')
        self.addControl(self.info_ch)
        self.info_logo = xbmcgui.ControlImage(self.W - 160, y + 5, 140, 70, '')
        self.addControl(self.info_logo)
        
        # Column headers
        y = 150
        if self.tex_header:
            self.addControl(xbmcgui.ControlImage(0, y, self.W, 35, self.tex_header))
        
        self.addControl(xbmcgui.ControlLabel(20, y + 6, 50, 25, '#', font='font11', textColor='FFFFFFFF'))
        self.addControl(xbmcgui.ControlLabel(70, y + 6, 300, 25, 'CHANNEL', font='font11', textColor='FFFFFFFF'))
        self.addControl(xbmcgui.ControlLabel(400, y + 6, 500, 25, 'NOW PLAYING', font='font11', textColor='FF00E5FF'))
        self.addControl(xbmcgui.ControlLabel(920, y + 6, 150, 25, 'TIME', font='font11', textColor='FFFFFFFF'))
        self.addControl(xbmcgui.ControlLabel(1100, y + 6, 500, 25, 'NEXT', font='font11', textColor='FF90CAF9'))
        self.addControl(xbmcgui.ControlLabel(1620, y + 6, 150, 25, 'CATEGORY', font='font11', textColor='FFFFFFFF'))
        
        # Rows
        y_start = 190
        row_h = 65
        self.row_ctrls = []
        
        for r in range(self.rows):
            y = y_start + r * row_h
            
            row_bg = None
            if self.tex_row:
                row_bg = xbmcgui.ControlImage(0, y, self.W, row_h - 2, self.tex_row)
                self.addControl(row_bg)
            
            num = xbmcgui.ControlLabel(20, y + 18, 40, 25, '', font='font11', textColor='FFFFFFFF', alignment=1)
            self.addControl(num)
            
            logo = xbmcgui.ControlImage(70, y + 8, 50, 50, '')
            self.addControl(logo)
            
            name = xbmcgui.ControlLabel(130, y + 18, 260, 25, '', font='font10', textColor='FFB0C4DE')
            self.addControl(name)
            
            now_prog = xbmcgui.ControlLabel(400, y + 18, 510, 25, '', font='font10', textColor='FF00E5FF')
            self.addControl(now_prog)
            
            time_lbl = xbmcgui.ControlLabel(920, y + 18, 170, 25, '', font='font10', textColor='FFFFFFFF')
            self.addControl(time_lbl)
            
            next_prog = xbmcgui.ControlLabel(1100, y + 18, 510, 25, '', font='font10', textColor='FF90CAF9')
            self.addControl(next_prog)
            
            cat = xbmcgui.ControlLabel(1620, y + 18, 280, 25, '', font='font10', textColor='FFB0C4DE')
            self.addControl(cat)
            
            self.row_ctrls.append({
                'bg': row_bg, 'num': num, 'logo': logo, 'name': name,
                'now': now_prog, 'time': time_lbl, 'next': next_prog, 'cat': cat
            })
        
        # Footer
        fy = self.H - 35
        if self.tex_header:
            self.addControl(xbmcgui.ControlImage(0, fy, self.W, 35, self.tex_header))
        self.addControl(xbmcgui.ControlLabel(0, fy + 7, self.W, 22, 
            'UP/DOWN: Navigate | OK: Play | PAGE UP/DOWN: Jump | BACK: Exit', 
            font='font10', textColor='FFB0C4DE', alignment=2))
        
        self.refresh()
    
    def refresh(self):
        now = time.time()
        
        for i, ctrl in enumerate(self.row_ctrls):
            idx = self.scroll + i
            if idx < len(self.channels):
                ch = self.channels[idx]
                sid = str(ch.get('stream_id', ''))
                epg_list = self.epg.get(sid, [])
                
                num = ch.get('num', idx + 1)
                ctrl['num'].setLabel(str(num) if num else str(idx + 1))
                ctrl['logo'].setImage(ch.get('stream_icon', '') or '')
                
                n = ch.get('name', '')
                ctrl['name'].setLabel(n[:28] + '..' if len(n) > 28 else n)
                
                cat_name = ch.get('category_name', '')
                ctrl['cat'].setLabel(cat_name[:28] + '..' if len(cat_name) > 28 else cat_name)
                
                # Find current and next program
                cur_prog = None
                next_prog = None
                for p in epg_list:
                    try:
                        ps = int(p.get('start_timestamp', 0))
                        pe = int(p.get('stop_timestamp', 0))
                        if ps <= now <= pe:
                            cur_prog = p
                        elif ps > now and not next_prog:
                            next_prog = p
                            break
                    except:
                        continue
                
                if cur_prog:
                    t = cur_prog.get('title', '')
                    ctrl['now'].setLabel(t[:55] + '..' if len(t) > 55 else t)
                    st = format_time(cur_prog.get('start_timestamp'))
                    et = format_time(cur_prog.get('stop_timestamp'))
                    ctrl['time'].setLabel(f"{st}-{et}")
                    
                    if ctrl['bg']:
                        ctrl['bg'].setImage(self.tex_now if idx == self.sel else self.tex_row)
                else:
                    ctrl['now'].setLabel('No EPG data')
                    ctrl['time'].setLabel('')
                    if ctrl['bg']:
                        ctrl['bg'].setImage(self.tex_sel if idx == self.sel else self.tex_row)
                
                if next_prog:
                    nt = next_prog.get('title', '')
                    nst = format_time(next_prog.get('start_timestamp'))
                    ctrl['next'].setLabel(f"{nst}: {nt[:45]}" + ('..' if len(nt) > 45 else ''))
                else:
                    ctrl['next'].setLabel('')
                
                # Selection highlight
                if ctrl['bg'] and idx == self.sel:
                    ctrl['bg'].setImage(self.tex_sel)
            else:
                ctrl['num'].setLabel('')
                ctrl['logo'].setImage('')
                ctrl['name'].setLabel('')
                ctrl['now'].setLabel('')
                ctrl['time'].setLabel('')
                ctrl['next'].setLabel('')
                ctrl['cat'].setLabel('')
                if ctrl['bg']:
                    ctrl['bg'].setImage(self.tex_row)
        
        self.refresh_info()
    
    def refresh_info(self):
        if self.sel >= len(self.channels):
            return
        
        ch = self.channels[self.sel]
        sid = str(ch.get('stream_id', ''))
        cname = ch.get('name', '')
        cat = ch.get('category_name', '')
        epg_list = self.epg.get(sid, [])
        now = time.time()
        
        cur = None
        for p in epg_list:
            try:
                ps = int(p.get('start_timestamp', 0))
                pe = int(p.get('stop_timestamp', 0))
                if ps <= now <= pe:
                    cur = p
                    break
            except:
                continue
        
        if cur:
            self.info_title.setLabel(cur.get('title', 'Unknown'))
            st = format_time(cur.get('start_timestamp'))
            et = format_time(cur.get('stop_timestamp'))
            dur = format_duration(cur.get('start_timestamp'), cur.get('stop_timestamp'))
            self.info_ch.setLabel(f"{cname} | {cat} | {st}-{et} ({dur})")
        else:
            self.info_title.setLabel(cname)
            self.info_ch.setLabel(cat)
        
        self.info_logo.setImage(ch.get('stream_icon', '') or '')
    
    def onAction(self, action):
        a = action.getId()
        if a in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, 92]:
            self.should_reopen = False
            self.close()
        elif a == xbmcgui.ACTION_MOVE_UP and self.sel > 0:
            self.sel -= 1
            if self.sel < self.scroll:
                self.scroll = self.sel
            self.refresh()
        elif a == xbmcgui.ACTION_MOVE_DOWN and self.sel < len(self.channels) - 1:
            self.sel += 1
            if self.sel >= self.scroll + self.rows:
                self.scroll = self.sel - self.rows + 1
            self.refresh()
        elif a == xbmcgui.ACTION_SELECT_ITEM:
            self.play()
        elif a == xbmcgui.ACTION_PAGE_UP:
            self.sel = max(0, self.sel - self.rows)
            self.scroll = max(0, self.scroll - self.rows)
            self.refresh()
        elif a == xbmcgui.ACTION_PAGE_DOWN:
            self.sel = min(len(self.channels) - 1, self.sel + self.rows)
            if self.sel >= self.scroll + self.rows:
                self.scroll = self.sel - self.rows + 1
            self.refresh()
    
    def play(self):
        if self.sel >= len(self.channels):
            return
        
        ch = self.channels[self.sel]
        sid = ch.get('stream_id')
        c = self.bridge.get_creds()
        
        if not sid or not c:
            notify("Cannot play", icon=xbmcgui.NOTIFICATION_ERROR)
            return
        
        name = ch.get('name', 'Channel')
        log(f"Playing: {name} (ID: {sid})")
        
        self.should_reopen = True
        self.close()
        
        url = f"{c['dns']}/live/{c['user']}/{c['pwd']}/{sid}.m3u8"
        
        li = xbmcgui.ListItem(path=url)
        li.setInfo('video', {'title': name})
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        li.setMimeType('application/x-mpegURL')
        
        xbmc.Player().play(url, li)

# ============================================================================
# GRID VIEW - Full EPG Grid
# ============================================================================
class EPGWindow(xbmcgui.WindowDialog):
    W, H = 1920, 1080
    
    def __init__(self, bridge, channels, epg_data):
        super().__init__()
        self.bridge = bridge
        self.channels = channels
        self.epg = epg_data or {}
        self.sel = 0
        self.scroll = 0
        self.time_off = 0
        self.rows = 8
        self.cols = 5
        self.ch_w = 280
        self.row_h = 90
        self.header_h = 60
        self.info_h = 90
        self.timebar_h = 35
        self.slot_w = (self.W - self.ch_w) // self.cols
        self.should_reopen = False
        
        now = datetime.now()
        self.base_time = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)
        
        self.tex_bg = create_texture('bg.bmp', 8, 32, 58)
        self.tex_header = create_texture('header.bmp', 6, 24, 42)
        self.tex_cell = create_texture('cell.bmp', 12, 45, 72)
        self.tex_sel = create_texture('sel.bmp', 0, 120, 160)
        self.tex_now = create_texture('now.bmp', 0, 150, 136)
        self.tex_ch = create_texture('ch.bmp', 10, 38, 60)
        
        self.ch_ctrls = []
        self.prog_ctrls = []
        self.time_lbls = []
        
        self.build()
    
    def build(self):
        if self.tex_bg:
            self.addControl(xbmcgui.ControlImage(0, 0, self.W, self.H, self.tex_bg))
        
        if self.tex_header:
            self.addControl(xbmcgui.ControlImage(0, 0, self.W, self.header_h, self.tex_header))
        
        self.addControl(xbmcgui.ControlLabel(15, 15, 350, 30, 'POSEIDON GUIDE', font='font13', textColor='FFD4AF37'))
        
        tnow = datetime.now().strftime('%H:%M')
        self.addControl(xbmcgui.ControlLabel(self.W - 100, 18, 85, 25, tnow, font='font12', textColor='FFFFFFFF', alignment=1))
        
        self.addControl(xbmcgui.ControlLabel(380, 18, 300, 25, f'{len(self.channels)} channels | {len(self.epg)} with EPG', font='font10', textColor='FF90CAF9'))
        
        y = self.header_h
        if self.tex_header:
            self.addControl(xbmcgui.ControlImage(0, y, self.W, self.info_h, self.tex_header))
        
        self.info_title = xbmcgui.ControlLabel(15, y + 8, self.W - 200, 28, '', font='font13', textColor='FF00E5FF')
        self.addControl(self.info_title)
        self.info_ch = xbmcgui.ControlLabel(15, y + 38, self.W - 200, 22, '', font='font11', textColor='FFFFFFFF')
        self.addControl(self.info_ch)
        self.info_desc = xbmcgui.ControlLabel(15, y + 62, self.W - 200, 20, '', font='font10', textColor='FFB0C4DE')
        self.addControl(self.info_desc)
        self.info_logo = xbmcgui.ControlImage(self.W - 170, y + 8, 155, 75, '')
        self.addControl(self.info_logo)
        
        y = self.header_h + self.info_h
        if self.tex_header:
            self.addControl(xbmcgui.ControlImage(0, y, self.W, self.timebar_h, self.tex_header))
        
        self.time_lbls = []
        for i in range(self.cols):
            st = self.base_time + timedelta(minutes=(self.time_off + i) * 30)
            lbl = xbmcgui.ControlLabel(self.ch_w + i * self.slot_w, y + 6, self.slot_w, 24, st.strftime('%H:%M'), font='font11', textColor='FFFFFFFF', alignment=2)
            self.addControl(lbl)
            self.time_lbls.append(lbl)
        
        y_start = self.header_h + self.info_h + self.timebar_h
        self.ch_ctrls = []
        self.prog_ctrls = []
        
        for r in range(self.rows):
            y = y_start + r * self.row_h
            
            ch_bg = None
            if self.tex_ch:
                ch_bg = xbmcgui.ControlImage(0, y, self.ch_w - 2, self.row_h - 2, self.tex_ch)
                self.addControl(ch_bg)
            
            num = xbmcgui.ControlLabel(5, y + 32, 40, 25, '', font='font11', textColor='FFFFFFFF', alignment=1)
            self.addControl(num)
            logo = xbmcgui.ControlImage(50, y + 20, 50, 50, '')
            self.addControl(logo)
            name = xbmcgui.ControlLabel(105, y + 32, 170, 25, '', font='font10', textColor='FFB0C4DE')
            self.addControl(name)
            
            self.ch_ctrls.append({'bg': ch_bg, 'num': num, 'logo': logo, 'name': name})
            
            row_progs = []
            for c in range(self.cols):
                x = self.ch_w + c * self.slot_w
                
                pbg = None
                if self.tex_cell:
                    pbg = xbmcgui.ControlImage(x + 1, y + 1, self.slot_w - 2, self.row_h - 3, self.tex_cell)
                    self.addControl(pbg)
                
                ptitle = xbmcgui.ControlLabel(x + 8, y + 15, self.slot_w - 16, 26, '', font='font11', textColor='FFFFFFFF')
                self.addControl(ptitle)
                psub = xbmcgui.ControlLabel(x + 8, y + 45, self.slot_w - 16, 22, '', font='font10', textColor='FFB0C4DE')
                self.addControl(psub)
                
                row_progs.append({'bg': pbg, 'title': ptitle, 'sub': psub})
            
            self.prog_ctrls.append(row_progs)
        
        fy = self.H - 35
        if self.tex_header:
            self.addControl(xbmcgui.ControlImage(0, fy, self.W, 35, self.tex_header))
        self.addControl(xbmcgui.ControlLabel(0, fy + 7, self.W, 22, 'UP/DOWN: Channel | LEFT/RIGHT: Time | OK: Play | BACK: Exit | PAGE: Jump', font='font10', textColor='FFB0C4DE', alignment=2))
        
        self.refresh()
    
    def refresh(self):
        self.refresh_channels()
        self.refresh_grid()
        self.refresh_info()
    
    def refresh_channels(self):
        for i, ctrl in enumerate(self.ch_ctrls):
            idx = self.scroll + i
            if idx < len(self.channels):
                ch = self.channels[idx]
                num = ch.get('num', idx + 1)
                ctrl['num'].setLabel(str(num) if num else str(idx + 1))
                ctrl['logo'].setImage(ch.get('stream_icon', '') or '')
                n = ch.get('name', '')
                ctrl['name'].setLabel(n[:18] + '..' if len(n) > 18 else n)
                if ctrl['bg']:
                    ctrl['bg'].setImage(self.tex_sel if idx == self.sel else self.tex_ch)
            else:
                ctrl['num'].setLabel('')
                ctrl['logo'].setImage('')
                ctrl['name'].setLabel('')
    
    def refresh_grid(self):
        now = time.time()
        for ri, row in enumerate(self.prog_ctrls):
            idx = self.scroll + ri
            if idx >= len(self.channels):
                for ctrl in row:
                    ctrl['title'].setLabel('')
                    ctrl['sub'].setLabel('')
                    if ctrl['bg']:
                        ctrl['bg'].setImage(self.tex_cell)
                continue
            
            ch = self.channels[idx]
            sid = str(ch.get('stream_id', ''))
            cname = ch.get('name', '')
            epg_list = self.epg.get(sid, [])
            
            for ci, ctrl in enumerate(row):
                slot_s = self.base_time + timedelta(minutes=(self.time_off + ci) * 30)
                slot_e = slot_s + timedelta(minutes=30)
                sts, ets = slot_s.timestamp(), slot_e.timestamp()
                
                prog = None
                for p in epg_list:
                    try:
                        ps = int(p.get('start_timestamp', 0))
                        pe = int(p.get('stop_timestamp', 0))
                        if ps < ets and pe > sts:
                            prog = p
                            break
                    except:
                        continue
                
                if prog:
                    t = prog.get('title', '')
                    ctrl['title'].setLabel(t[:22] + '..' if len(t) > 22 else t)
                    st = format_time(prog.get('start_timestamp'))
                    et = format_time(prog.get('stop_timestamp'))
                    ctrl['sub'].setLabel(f"{st}-{et}")
                    
                    try:
                        ps = int(prog.get('start_timestamp', 0))
                        pe = int(prog.get('stop_timestamp', 0))
                        if ctrl['bg']:
                            if ps <= now <= pe:
                                ctrl['bg'].setImage(self.tex_now)
                            elif idx == self.sel:
                                ctrl['bg'].setImage(self.tex_sel)
                            else:
                                ctrl['bg'].setImage(self.tex_cell)
                    except:
                        if ctrl['bg']:
                            ctrl['bg'].setImage(self.tex_cell)
                else:
                    ctrl['title'].setLabel('No EPG')
                    ctrl['sub'].setLabel(cname[:24] if len(cname) <= 24 else cname[:21] + '..')
                    if ctrl['bg']:
                        ctrl['bg'].setImage(self.tex_sel if idx == self.sel else self.tex_cell)
    
    def refresh_info(self):
        if self.sel >= len(self.channels):
            return
        
        ch = self.channels[self.sel]
        sid = str(ch.get('stream_id', ''))
        cname = ch.get('name', '')
        cat = ch.get('category_name', '')
        epg_list = self.epg.get(sid, [])
        now = time.time()
        
        cur = None
        for p in epg_list:
            try:
                ps = int(p.get('start_timestamp', 0))
                pe = int(p.get('stop_timestamp', 0))
                if ps <= now <= pe:
                    cur = p
                    break
            except:
                continue
        
        if cur:
            self.info_title.setLabel(cur.get('title', 'Unknown'))
            st = format_time(cur.get('start_timestamp'))
            et = format_time(cur.get('stop_timestamp'))
            dur = format_duration(cur.get('start_timestamp'), cur.get('stop_timestamp'))
            self.info_ch.setLabel(f"{cname} | {cat} | {st}-{et} ({dur})")
            d = cur.get('description', '')
            self.info_desc.setLabel(d[:100] + '..' if len(d) > 100 else d)
        else:
            self.info_title.setLabel(cname)
            self.info_ch.setLabel(f"{cat}")
            self.info_desc.setLabel('')
        
        self.info_logo.setImage(ch.get('stream_icon', '') or '')
    
    def refresh_time(self):
        for i, lbl in enumerate(self.time_lbls):
            st = self.base_time + timedelta(minutes=(self.time_off + i) * 30)
            lbl.setLabel(st.strftime('%H:%M'))
    
    def onAction(self, action):
        a = action.getId()
        if a in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, 92]:
            self.should_reopen = False
            self.close()
        elif a == xbmcgui.ACTION_MOVE_UP and self.sel > 0:
            self.sel -= 1
            if self.sel < self.scroll:
                self.scroll = self.sel
            self.refresh()
        elif a == xbmcgui.ACTION_MOVE_DOWN and self.sel < len(self.channels) - 1:
            self.sel += 1
            if self.sel >= self.scroll + self.rows:
                self.scroll = self.sel - self.rows + 1
            self.refresh()
        elif a == xbmcgui.ACTION_MOVE_LEFT and self.time_off > -12:
            self.time_off -= 1
            self.refresh_time()
            self.refresh_grid()
        elif a == xbmcgui.ACTION_MOVE_RIGHT and self.time_off < 24:
            self.time_off += 1
            self.refresh_time()
            self.refresh_grid()
        elif a == xbmcgui.ACTION_SELECT_ITEM:
            self.play()
        elif a == xbmcgui.ACTION_PAGE_UP:
            self.sel = max(0, self.sel - self.rows)
            self.scroll = max(0, self.scroll - self.rows)
            self.refresh()
        elif a == xbmcgui.ACTION_PAGE_DOWN:
            self.sel = min(len(self.channels) - 1, self.sel + self.rows)
            if self.sel >= self.scroll + self.rows:
                self.scroll = self.sel - self.rows + 1
            self.refresh()
    
    def play(self):
        if self.sel >= len(self.channels):
            return
        
        ch = self.channels[self.sel]
        sid = ch.get('stream_id')
        c = self.bridge.get_creds()
        
        if not sid or not c:
            notify("Cannot play", icon=xbmcgui.NOTIFICATION_ERROR)
            return
        
        name = ch.get('name', 'Channel')
        log(f"Playing: {name} (ID: {sid})")
        
        self.should_reopen = True
        self.close()
        
        url = f"{c['dns']}/live/{c['user']}/{c['pwd']}/{sid}.m3u8"
        
        li = xbmcgui.ListItem(path=url)
        li.setInfo('video', {'title': name})
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        li.setMimeType('application/x-mpegURL')
        
        xbmc.Player().play(url, li)

# ============================================================================
# GUIDE MANAGER
# ============================================================================
class GuideManager:
    def __init__(self):
        self.bridge = None
        self.channels = None
        self.epg_data = None
        self.running = True
        self.last_sel = 0
        self.last_scroll = 0
        self.view_mode = 'grid'  # 'grid' or 'list'
    
    def run(self):
        log("GuideManager v1.1.0")
        self.bridge = PoseidonBridge()
        
        if not self.bridge.installed():
            xbmcgui.Dialog().ok("Error", "Poseidon Player not installed")
            return
        
        if not self.bridge.valid():
            xbmcgui.Dialog().ok("Error", "No IPTV credentials.\nConfigure Poseidon Player first.")
            xbmc.executebuiltin(f'Addon.OpenSettings({PLAYER_ADDON_ID})')
            return
        
        # Show choice popup
        dialog = xbmcgui.Dialog()
        options = [
            "List View (Simple EPG List)",
            "Grid View (Full EPG Grid)"
        ]
        
        choice = dialog.select("Poseidon Guide - Choose View", options)
        
        if choice < 0:
            return
        
        self.view_mode = 'list' if choice == 0 else 'grid'
        
        # Load data
        self.channels = load_cache(CACHE_CHANNELS)
        self.epg_data = load_cache(CACHE_EPG)
        
        if self.channels and self.epg_data:
            log("Using cached data")
            notify("Loaded from cache")
        else:
            prog = xbmcgui.DialogProgress()
            prog.create("Poseidon Guide", "Loading all channels...")
            
            self.channels = get_all_channels(self.bridge, prog, force_refresh=True)
            
            if not self.channels:
                prog.close()
                notify("No channels found", icon=xbmcgui.NOTIFICATION_ERROR)
                return
            
            self.epg_data = get_all_epg(self.bridge, self.channels, prog, force_refresh=True)
            prog.close()
        
        log(f"Ready: {len(self.channels)} ch, {len(self.epg_data or {})} epg")
        
        # Run selected view
        while self.running:
            if self.view_mode == 'list':
                win = ListViewWindow(self.bridge, self.channels, self.epg_data)
            else:
                win = EPGWindow(self.bridge, self.channels, self.epg_data)
            
            win.sel = self.last_sel
            win.scroll = self.last_scroll
            win.refresh()
            win.doModal()
            
            self.last_sel = win.sel
            self.last_scroll = win.scroll
            should_reopen = win.should_reopen
            del win
            
            if should_reopen:
                xbmc.sleep(1000)
                player = xbmc.Player()
                monitor = xbmc.Monitor()
                while player.isPlaying() and not monitor.abortRequested():
                    xbmc.sleep(500)
                xbmc.sleep(500)
            else:
                self.running = False

def _resolve_stream_url(bridge, stream_id):
    """Return a playable URL for the given stream_id, mode-aware."""
    c = bridge.get_creds()
    if not c:
        return None
    if c.get('mode') == 'mac':
        if not _mac_ensure(c):
            return None
        _mac_fetch_channels(c)
        cmd = _MAC_STATE['cmd_by_id'].get(str(stream_id))
        if not cmd:
            return None
        import urllib.parse as _up
        encoded = _up.quote(cmd, safe='')
        url = (f'{_MAC_STATE["portal"]}?type=itv&action=create_link&cmd={encoded}'
               f'&forced_storage=undefined&disable_ad=0&download=0'
               f'&JsHttpRequest=1-xml')
        data = _mac_get(url, _mac_headers(_MAC_STATE['mac'], _MAC_STATE['token']))
        js = (data or {}).get('js', {})
        raw = js.get('cmd') or js.get('url') or ''
        for pref in ('ffmpeg ', 'ffrt ', 'ffrt3 ', 'auto '):
            if raw.startswith(pref):
                raw = raw[len(pref):]
                break
        return raw.strip() or None
    fmt = 'm3u8'
    return f"{c['dns']}/live/{c['user']}/{c['pwd']}/{stream_id}.{fmt}"


def _collect_channels_for_window(bridge, progress=None, max_channels=300):
    """Gather all channels + their short EPG, ready for the Sky/Virgin window."""
    channels = get_all_channels(bridge, progress=progress)
    if not channels:
        return [], {}
    channels = channels[:max_channels]
    epg_map = {}
    total = max(1, len(channels))
    for i, ch in enumerate(channels):
        if progress:
            try:
                progress.update(
                    min(95, int((i / total) * 95)),
                    f"Loading EPG {i + 1}/{total}",
                )
                if progress.iscanceled():
                    break
            except Exception:
                pass
        sid = str(ch.get('stream_id'))
        progs = get_epg(bridge, sid, limit=15) or []
        # Normalise timestamp fields: XC gives 'start_timestamp'/'stop_timestamp',
        # MAC already returns that shape from the adapter.
        epg_map[sid] = progs
    return channels, epg_map


def launch_skin_window(bridge):
    """Open the Sky/Virgin/Classic full-screen EPG window."""
    addon = xbmcaddon.Addon()
    theme = addon.getSetting('guide_skin') or 'sky'
    if theme == 'classic':
        # Classic = directory view (original behaviour). Drop straight through.
        return False
    pip_enabled = addon.getSetting('pip_enabled').lower() != 'false'
    pip_autoplay = addon.getSetting('pip_autoplay').lower() != 'false'

    progress = xbmcgui.DialogProgress()
    progress.create('Poseidon Guide', 'Preparing TV guide...')
    channels, epg_map = _collect_channels_for_window(bridge, progress=progress)
    progress.close()

    if not channels:
        xbmcgui.Dialog().notification(
            'Poseidon Guide', 'No channels available', xbmcgui.NOTIFICATION_WARNING, 3000)
        return True

    from resources.lib.guide_window import open_guide_window
    open_guide_window(
        theme=theme,
        channels=channels,
        epg_map=epg_map,
        play_resolver=lambda sid: _resolve_stream_url(bridge, sid),
        pip_enabled=pip_enabled,
        pip_autoplay=pip_autoplay,
    )
    return True


def main():
    log("Poseidon Guide v1.2.0")
    bridge = PoseidonBridge()
    if not bridge.valid():
        xbmcgui.Dialog().ok('Poseidon Guide',
                            'Open Poseidon Player first and enter your credentials.')
        return

    # Allow ?action=settings to jump straight to settings
    params = {}
    try:
        if len(sys.argv) > 1:
            import urllib.parse as _up
            q = sys.argv[1] if sys.argv[1].startswith('?') else ''
            if q:
                params = dict(_up.parse_qsl(q.lstrip('?')))
    except Exception:
        pass
    if params.get('action') == 'settings':
        xbmcaddon.Addon().openSettings()
        return

    # Respect the user's skin choice.
    if launch_skin_window(bridge):
        return
    GuideManager().run()


if __name__ == '__main__':
    main()
