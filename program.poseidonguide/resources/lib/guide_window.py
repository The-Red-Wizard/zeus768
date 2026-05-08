"""
Poseidon Guide v1.4.0 - Sky / Virgin style full-screen EPG window with PiP.

Changes vs 1.3.x:
  * Single OK = play in PiP within the guide.
    Double OK (within 600 ms) on the same channel = full-screen play.
  * First-launch tutorial dialog explaining the controls.
  * Sky skin redesigned to match the real Sky Q on-screen guide
    (gradient hero + duration/synopsis + time-ruler grid + pill
    highlight). PiP moved to the LEFT side of the hero per user request.
  * Faster perceived load: only the first 50 channels' EPG is fetched
    synchronously; the rest streams in on a background thread so the
    window can open immediately.
"""
import os
import time
import threading
from datetime import datetime

import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = os.path.join(ADDON_PATH, 'icon.png')
SKY_LOGO = os.path.join(ADDON_PATH, 'resources', 'skins', 'default',
                        'media', 'sky_logo.png')
DIRECTV_LOGO = os.path.join(ADDON_PATH, 'resources', 'skins', 'default',
                            'media', 'directv_logo.png')
SPECTRUM_LOGO = os.path.join(ADDON_PATH, 'resources', 'skins', 'default',
                             'media', 'spectrum_logo.png')
REDW_LOGO = os.path.join(ADDON_PATH, 'resources', 'skins', 'default',
                         'media', 'redw_logo.png')

# Double-click window in seconds. Two OK presses within this on the same
# channel = full-screen; otherwise it's just PiP.
DOUBLE_CLICK_WINDOW = 0.6


# ------------------------------------------------------------------
# Theme palettes.  FFAARRGGBB hex like Kodi expects.
# ------------------------------------------------------------------
THEMES = {
    'sky': {
        'PG_BG':       'FF1A1A6B',   # deep sky purple - matches the sky icon bg
        'PG_BG2':      'FF2A2AA0',   # lighter purple band -> fakes a vertical gradient
        'PG_Accent':   'FF4FB1FF',
        'PG_Label':    'FFFFFFFF',
        'PG_SubLabel': 'FFC9CCF2',
        'PG_Logo':     ADDON_ICON,
        'PG_SkyLogo':  SKY_LOGO,
        'hint':        'OK once: preview in PiP  |  OK twice: full screen  |  C: pin favourite',
    },
    'virgin': {
        'PG_BG':       'FF111111',
        'PG_BG2':      'FF1F1F1F',
        'PG_Accent':   'FFDB0032',
        'PG_Label':    'FFFFFFFF',
        'PG_SubLabel': 'FFE8E8E8',
        'PG_Logo':     ADDON_ICON,
        'PG_SkyLogo':  SKY_LOGO,
        'hint':        'OK once: preview in PiP  |  OK twice: full screen  |  C: pin favourite',
    },
    'classic': {
        'PG_BG':       'FF1A1A1A',
        'PG_BG2':      'FF222222',
        'PG_Accent':   'FF4CAF50',
        'PG_Label':    'FFFFFFFF',
        'PG_SubLabel': 'FFA0A0A0',
        'PG_Logo':     ADDON_ICON,
        'PG_SkyLogo':  SKY_LOGO,
        'hint':        'OK once: preview in PiP  |  OK twice: full screen  |  C: pin favourite',
    },
    'directv': {
        # DirecTV on-screen guide palette - deep navy + signature DirecTV blue.
        'PG_BG':       'FF0D1929',   # deep navy, matches DirecTV chassis
        'PG_BG2':      'FF132A47',   # slightly lighter band for the hero highlight
        'PG_Accent':   'FF1989F0',   # DirecTV blue (focus pill / highlights)
        'PG_Label':    'FFFFFFFF',
        'PG_SubLabel': 'FFB8C2D1',
        'PG_Logo':     ADDON_ICON,
        'PG_SkyLogo':  DIRECTV_LOGO,  # Re-uses the wordmark slot in the XML
        'hint':        'OK once: preview in PiP  |  OK twice: full screen  |  C: pin favourite',
    },
    'spectrum': {
        # Spectrum (Charter) on-screen guide palette - pure black chassis +
        # signature Spectrum cyan-teal accent.  Sort order is USA -> CAN -> UK.
        'PG_BG':       'FF000000',   # pure black, matches Spectrum guide chassis
        'PG_BG2':      'FF111111',   # subtle near-black band for hero
        'PG_Accent':   'FF00B0E5',   # Spectrum cyan/teal (focus pill / title)
        'PG_Label':    'FFFFFFFF',
        'PG_SubLabel': 'FFB8C2D1',
        'PG_Logo':     ADDON_ICON,
        'PG_SkyLogo':  SPECTRUM_LOGO,  # Re-uses the wordmark slot in the XML
        'hint':        'OK once: preview in PiP  |  OK twice: full screen  |  C: pin favourite',
    },
    'redw': {
        # Red W Media (UK) palette - black chassis with bright red accent.
        # Channel sort prioritises UK first, then USA, then the rest.
        'PG_BG':       'FF000000',
        'PG_BG2':      'FF1E2530',   # slate panel colour for channel cells
        'PG_Accent':   'FFE21B25',   # Red W signature red
        'PG_Label':    'FFFFFFFF',
        'PG_SubLabel': 'FFB8B8B8',
        'PG_Logo':     ADDON_ICON,
        'PG_SkyLogo':  REDW_LOGO,    # Re-uses the wordmark slot in the XML
        'hint':        'OK once: preview in PiP  |  OK twice: full screen  |  C: pin favourite',
    },
}


def _apply_theme(theme_key):
    theme = THEMES.get(theme_key, THEMES['sky'])
    for k, v in theme.items():
        if k == 'hint':
            continue
        xbmc.executebuiltin(f'Skin.SetString({k},{v})')
    return theme


def _format_time(ts):
    if not ts:
        return ''
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%H:%M').lstrip('0').lower() or '0:00'
    except Exception:
        return ''


def _format_clock(ts):
    """12-hour 'h:mmpm' style used in the Sky meta line."""
    if not ts:
        return ''
    try:
        d = datetime.fromtimestamp(int(ts))
        return d.strftime('%I:%M%p').lstrip('0').lower()
    except Exception:
        return ''


def _short_plot(text, length=240):
    text = (text or '').strip().replace('\n', ' ')
    return text if len(text) <= length else text[:length - 1] + '...'


def _duration_minutes(start, stop):
    try:
        d = (int(stop) - int(start)) // 60
        return f'{d}m' if d > 0 else ''
    except Exception:
        return ''


def show_first_run_tutorial():
    """Show a one-time popup explaining the controls. Tracks dismissal in
    addon settings so it never reopens unless the user re-enables it."""
    try:
        if ADDON.getSetting('show_help').lower() == 'false':
            return
    except Exception:
        pass
    msg = (
        '[B]Welcome to the Sky-style TV Guide[/B][CR][CR]'
        '[COLOR FF4FB1FF]OK once[/COLOR] on a channel  ->  preview it in the PiP window[CR]'
        '[COLOR FF4FB1FF]OK twice[/COLOR] (quick double-tap)  ->  watch full screen[CR][CR]'
        'Up / Down  ->  change channel[CR]'
        'Left / Right  ->  pan the time ruler[CR]'
        'I  ->  toggle list view[CR]'
        'C  ->  pin / unpin a favourite[CR]'
        'Back / Esc  ->  exit the guide'
    )
    xbmcgui.Dialog().ok('Poseidon Guide - How it works', msg)
    try:
        ADDON.setSetting('show_help', 'false')
    except Exception:
        pass


# ----------------------------------------------------------------------
# PiP infrastructure (debounced player)
# ----------------------------------------------------------------------
class _PipScheduler:
    def __init__(self, callback, delay=0.25):
        self._cb = callback
        self._delay = delay
        self._timer = None
        self._lock = threading.Lock()

    def schedule(self, payload):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._fire, args=(payload,))
            self._timer.daemon = True
            self._timer.start()

    def cancel(self):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _fire(self, payload):
        try:
            self._cb(payload)
        except Exception as e:
            xbmc.log(f'[PoseidonGuide] pip scheduler error: {e}', xbmc.LOGWARNING)


class _PipPlayer(xbmc.Player):
    def __init__(self, on_full_stop):
        super().__init__()
        self._on_full_stop = on_full_stop

    def onPlayBackStopped(self):  # noqa: N802
        try:
            self._on_full_stop()
        except Exception:
            pass

    def onPlayBackEnded(self):  # noqa: N802
        try:
            self._on_full_stop()
        except Exception:
            pass


# ----------------------------------------------------------------------
# Common click-tracking mixin so list & grid windows share the
# single = PiP / double = fullscreen behaviour.
# ----------------------------------------------------------------------
class _ClickTracker:
    def __init__(self):
        self._last_click_ts = 0.0
        self._last_click_id = None

    def _is_double_click(self, channel_id):
        now = time.time()
        same = (channel_id == self._last_click_id)
        within = (now - self._last_click_ts) <= DOUBLE_CLICK_WINDOW
        if same and within:
            self._last_click_ts = 0.0
            self._last_click_id = None
            return True
        self._last_click_ts = now
        self._last_click_id = channel_id
        return False


class GuideSkinWindow(xbmcgui.WindowXML, _ClickTracker):
    """Sky/Virgin-style EPG with Picture-in-Picture preview (list layout).

    The list view now shares the Sky-style layout with the grid view: each
    channel row carries 5 inline EPG time-slot tabs to the right of the
    channel name. Left/Right pans the time ruler one slot at a time."""

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        _ClickTracker.__init__(self)
        self.channels = kwargs.get('channels', [])
        self.epg_map = kwargs.get('epg_map', {})
        self.theme = kwargs.get('theme', 'sky')
        self.pip_enabled = kwargs.get('pip_enabled', True)
        self.pip_autoplay = kwargs.get('pip_autoplay', True)
        self._player = _PipPlayer(self._restart_pip_for_focused)
        self._last_pip_id = None
        self._play_resolver = kwargs.get('play_resolver')
        self._pip_scheduler = _PipScheduler(self._start_pip_now, delay=0.25)
        self._closing = False
        self._cursor = _slot_start(time.time())

    def onInit(self):
        theme = _apply_theme(self.theme)
        self.setProperty('theme_hint', theme['hint'])
        self.setProperty('pip_channel', '')
        xbmc.executebuiltin(
            'Skin.SetString(PG_PiP_Hidden,%s)' % ('false' if self.pip_enabled else 'true')
        )
        self._refresh_ruler_and_rows()
        if self.channels:
            self._update_hero(self.channels[0])

    def onAction(self, action):
        action_id = action.getId()
        if action_id in (9, 10, 13, 92):
            self._closing = True
            self._pip_scheduler.cancel()
            self._stop_pip()
            self.close()
            return
        if action_id == 11:  # Info -> grid view
            self._closing = True
            self._pip_scheduler.cancel()
            self._stop_pip()
            self.close()
            xbmcgui.Window(10000).setProperty('pg_switch_to_grid', '1')
            return
        if action_id == 1:  # left
            # Only pan the time-ruler when the channel list is focused,
            # otherwise let D-pad nav reach other controls (Favourites btn).
            if self.getFocusId() == 9000:
                self._cursor -= SLOT_MINUTES * 60
                self._refresh_ruler_and_rows(rebuild=False)
            return
        if action_id == 2:  # right
            if self.getFocusId() == 9000:
                self._cursor += SLOT_MINUTES * 60
                self._refresh_ruler_and_rows(rebuild=False)
            return
        if action_id in (3, 4):
            xbmc.sleep(40)
            self._on_channel_moved()
            return
        if action_id == 117:
            self._toggle_favourite_focused()
            return

    def onClick(self, control_id):
        if control_id == 9000:
            idx = self.getControl(9000).getSelectedPosition()
            if 0 <= idx < len(self.channels):
                self._on_select(self.channels[idx])
        elif control_id == 9100:
            # FAVOURITES button (RedW skin) -> close and reopen the guide
            # filtered to the user's pinned favourites channel list.
            self._closing = True
            self._pip_scheduler.cancel()
            self._stop_pip()
            xbmcgui.Window(10000).setProperty('pg_open_favourites', '1')
            self.close()

    def _on_select(self, channel):
        sid = str(channel.get('stream_id'))
        if self._is_double_click(sid):
            self._full_play(channel)
        else:
            self._last_pip_id = None
            self._pip_scheduler.cancel()
            self._start_pip(channel)
            self.setProperty('pip_channel', channel.get('name', ''))

    def _update_hero(self, channel):
        progs = self.epg_map.get(str(channel.get('stream_id')), [])
        now_ts = time.time()
        cur = _find_now(progs, now_ts) or (progs[0] if progs else None)
        self.setProperty('hero_logo', channel.get('stream_icon', '') or ADDON_ICON)
        ch_num = channel.get('num', '') or ''
        ch_name = channel.get('name', '') or ''
        self.setProperty('selected_channel',
                         (f'{ch_num} {ch_name}'.strip() if ch_num else ch_name))
        if not cur:
            self.setProperty('selected_title', channel.get('name', ''))
            self.setProperty('selected_meta', '')
            self.setProperty('selected_desc', 'No programme data available')
            return
        title = cur.get('title', channel.get('name', ''))
        start = cur.get('start_timestamp') or cur.get('start') or 0
        stop = cur.get('stop_timestamp') or cur.get('end') or 0
        dur = _duration_minutes(start, stop)
        meta_bits = []
        if dur:
            meta_bits.append(dur)
        meta_bits.append('HD')
        meta_bits.append('S')
        if start:
            try:
                if int(start) <= now_ts <= int(stop):
                    meta_bits.append(f'Started at {_format_clock(start)}')
                else:
                    meta_bits.append(f'Starts at {_format_clock(start)}')
            except Exception:
                pass
        self.setProperty('selected_title', title)
        self.setProperty('selected_meta', '   '.join(meta_bits))
        self.setProperty('selected_desc', _short_plot(cur.get('description', ''), length=240))

    def _refresh_ruler_and_rows(self, rebuild=True):
        for i in range(SLOT_COUNT):
            ts = self._cursor + i * SLOT_MINUTES * 60
            self.setProperty(f'slot{i + 1}', _format_clock(ts))

        end_ts = self._cursor + SLOT_COUNT * SLOT_MINUTES * 60
        now_ts = time.time()
        if self._cursor <= now_ts < end_ts:
            frac = (now_ts - self._cursor) / (SLOT_COUNT * SLOT_MINUTES * 60)
            x_px = 360 + int(frac * (1880 - 360))
            self.setProperty('now_x', str(x_px))
        else:
            self.setProperty('now_x', '')

        ctl = self.getControl(9000)
        if rebuild:
            ctl.reset()
            items = []
            for ch in self.channels:
                li = xbmcgui.ListItem(label=ch.get('name', ''))
                li.setArt({'icon': ch.get('stream_icon', '') or ADDON_ICON,
                           'thumb': ch.get('stream_icon', '') or ADDON_ICON})
                li.setProperty('num', str(ch.get('num', '')))
                progs = self.epg_map.get(str(ch.get('stream_id')), [])
                for i in range(SLOT_COUNT):
                    slot_ts = self._cursor + i * SLOT_MINUTES * 60
                    prog = _find_block(progs, slot_ts)
                    li.setProperty(f'b{i + 1}t', (prog.get('title', '') if prog else ''))
                    li.setProperty(
                        f'b{i + 1}s',
                        _format_clock(prog.get('start_timestamp') or prog.get('start') or 0)
                        if prog else ''
                    )
                items.append(li)
            ctl.addItems(items)
        else:
            try:
                size = ctl.size()
            except Exception:
                size = 0
            for row in range(size):
                try:
                    li = ctl.getListItem(row)
                except Exception:
                    continue
                if row >= len(self.channels):
                    continue
                ch = self.channels[row]
                progs = self.epg_map.get(str(ch.get('stream_id')), [])
                for i in range(SLOT_COUNT):
                    slot_ts = self._cursor + i * SLOT_MINUTES * 60
                    prog = _find_block(progs, slot_ts)
                    li.setProperty(f'b{i + 1}t', (prog.get('title', '') if prog else ''))
                    li.setProperty(
                        f'b{i + 1}s',
                        _format_clock(prog.get('start_timestamp') or prog.get('start') or 0)
                        if prog else ''
                    )

    def _on_channel_moved(self):
        idx = self.getControl(9000).getSelectedPosition()
        if idx < 0 or idx >= len(self.channels):
            return
        ch = self.channels[idx]
        self.setProperty('pip_channel', ch.get('name', ''))
        self._update_hero(ch)

    def _start_pip_now(self, channel):
        self._start_pip(channel)

    def _restart_pip_for_focused(self):
        if self._closing or not self.pip_enabled:
            return
        try:
            idx = self.getControl(9000).getSelectedPosition()
        except Exception:
            return
        if idx < 0 or idx >= len(self.channels):
            return
        self._last_pip_id = None
        self._pip_scheduler.schedule(self.channels[idx])

    def _start_pip(self, channel):
        if not self.pip_enabled:
            return
        stream_id = str(channel.get('stream_id'))
        if not stream_id or stream_id == self._last_pip_id:
            return
        if not self._play_resolver:
            return
        try:
            url = self._play_resolver(stream_id)
        except Exception as e:
            xbmc.log(f'[PoseidonGuide] pip resolve failed: {e}', xbmc.LOGWARNING)
            return
        if not url:
            return
        li = xbmcgui.ListItem(path=url)
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        try:
            self._player.play(url, li, windowed=True)
            self._last_pip_id = stream_id
        except Exception as e:
            xbmc.log(f'[PoseidonGuide] pip play failed: {e}', xbmc.LOGWARNING)

    def _stop_pip(self):
        try:
            if self._player.isPlaying():
                self._player.stop()
        except Exception:
            pass
        self._last_pip_id = None

    def _full_play(self, channel):
        stream_id = str(channel.get('stream_id'))
        if not stream_id or not self._play_resolver:
            return
        try:
            url = self._play_resolver(stream_id)
        except Exception:
            url = None
        if not url:
            xbmcgui.Dialog().notification('Poseidon Guide', 'Stream unavailable',
                                          xbmcgui.NOTIFICATION_ERROR, 3000)
            return
        self._pip_scheduler.cancel()
        self._last_pip_id = stream_id
        li = xbmcgui.ListItem(path=url)
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        self._player.play(url, li)

    def _toggle_favourite_focused(self):
        idx = self.getControl(9000).getSelectedPosition()
        if idx < 0 or idx >= len(self.channels):
            return
        ch = self.channels[idx]
        sid = str(ch.get('stream_id'))
        name = ch.get('name', 'channel')
        from resources.lib import favourites as _fav
        added = _fav.toggle(sid)
        msg = (f'Pinned: {name}' if added else f'Unpinned: {name}')
        xbmcgui.Dialog().notification('Favourites', msg,
                                      xbmcgui.NOTIFICATION_INFO, 1500)


def open_guide_window(theme, channels, epg_map, play_resolver,
                      pip_enabled=True, pip_autoplay=True):
    show_first_run_tutorial()
    xml_file = 'script-poseidonguide-main.xml'
    if theme == 'directv':
        xml_file = 'script-poseidonguide-directv-main.xml'
    elif theme == 'spectrum':
        xml_file = 'script-poseidonguide-spectrum-main.xml'
    elif theme == 'redw':
        xml_file = 'script-poseidonguide-redw-main.xml'
    w = GuideSkinWindow(
        xml_file,
        ADDON_PATH,
        'default',
        '1080i',
        channels=channels,
        epg_map=epg_map,
        theme=theme,
        pip_enabled=pip_enabled,
        pip_autoplay=pip_autoplay,
        play_resolver=play_resolver,
    )
    w.doModal()
    del w


# ======================================================================
# TIME-RULER GRID VIEW (Sky-style)
# ======================================================================
SLOT_MINUTES = 30
SLOT_COUNT = 5  # 5 visible slots = 2.5h, matches the Sky reference


def _slot_start(now_ts):
    secs = int(now_ts)
    return secs - (secs % (SLOT_MINUTES * 60))


def _find_block(programs, slot_start_ts):
    slot_end_ts = slot_start_ts + SLOT_MINUTES * 60
    for p in programs:
        s = int(p.get('start_timestamp') or p.get('start') or 0)
        e = int(p.get('stop_timestamp') or p.get('end') or 0)
        if s == 0 and e == 0:
            continue
        if s < slot_end_ts and e > slot_start_ts:
            return p
    return None


def _find_now(programs, now_ts):
    for p in programs:
        s = int(p.get('start_timestamp') or p.get('start') or 0)
        e = int(p.get('stop_timestamp') or p.get('end') or 0)
        if s <= now_ts <= e:
            return p
    return None


class GuideGridWindow(xbmcgui.WindowXML, _ClickTracker):
    """Sky-style time-ruler grid view."""

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        _ClickTracker.__init__(self)
        self.channels = kwargs.get('channels', [])
        self.epg_map = kwargs.get('epg_map', {})
        self.theme = kwargs.get('theme', 'sky')
        self.pip_enabled = kwargs.get('pip_enabled', True)
        self.pip_autoplay = kwargs.get('pip_autoplay', True)
        self._player = _PipPlayer(self._restart_pip_for_focused)
        self._play_resolver = kwargs.get('play_resolver')
        self._last_pip_id = None
        self._pip_scheduler = _PipScheduler(self._start_pip_now, delay=0.25)
        self._closing = False
        self._cursor = _slot_start(time.time())

    def onInit(self):
        _apply_theme(self.theme)
        xbmc.executebuiltin(
            'Skin.SetString(PG_PiP_Hidden,%s)' % ('false' if self.pip_enabled else 'true')
        )
        self._refresh_ruler_and_rows()
        self.setProperty('pip_channel', '')
        if self.channels:
            self._update_hero(self.channels[0])

    def onAction(self, action):
        aid = action.getId()
        if aid in (9, 10, 13, 92):
            self._closing = True
            self._pip_scheduler.cancel()
            self._stop_pip()
            self.close()
            return
        if aid == 1:  # left
            # Only pan the time-ruler when the channel list is focused,
            # otherwise let D-pad nav reach other controls (Favourites btn).
            if self.getFocusId() == 9000:
                self._cursor -= SLOT_MINUTES * 60
                self._refresh_ruler_and_rows(rebuild=False)
            return
        if aid == 2:  # right
            if self.getFocusId() == 9000:
                self._cursor += SLOT_MINUTES * 60
                self._refresh_ruler_and_rows(rebuild=False)
            return
        if aid == 11:  # Info -> list view
            self._closing = True
            self._pip_scheduler.cancel()
            self._stop_pip()
            self.close()
            xbmcgui.Window(10000).setProperty('pg_switch_to_list', '1')
            return
        if aid in (3, 4):
            xbmc.sleep(40)
            self._on_channel_moved()
            return
        if aid == 117:
            self._toggle_favourite_focused()
            return

    def onClick(self, control_id):
        if control_id == 9000:
            idx = self.getControl(9000).getSelectedPosition()
            if 0 <= idx < len(self.channels):
                self._on_select(self.channels[idx])
        elif control_id == 9100:
            # FAVOURITES button (RedW skin) -> close and reopen the guide
            # filtered to the user's pinned favourites channel list.
            self._closing = True
            self._pip_scheduler.cancel()
            self._stop_pip()
            xbmcgui.Window(10000).setProperty('pg_open_favourites', '1')
            self.close()

    def _on_select(self, channel):
        sid = str(channel.get('stream_id'))
        if self._is_double_click(sid):
            self._full_play(channel)
        else:
            self._last_pip_id = None
            self._pip_scheduler.cancel()
            self._start_pip(channel)
            self.setProperty('pip_channel', channel.get('name', ''))

    # ---- rendering ----
    def _update_hero(self, channel):
        """Populate the upper hero panel - the channel chip + programme
        title + Sky-style meta line + synopsis."""
        progs = self.epg_map.get(str(channel.get('stream_id')), [])
        now_ts = time.time()
        cur = _find_now(progs, now_ts) or (progs[0] if progs else None)
        self.setProperty('hero_logo', channel.get('stream_icon', '') or ADDON_ICON)
        ch_num = channel.get('num', '') or ''
        ch_name = channel.get('name', '') or ''
        self.setProperty('selected_channel',
                         (f'{ch_num} {ch_name}'.strip() if ch_num else ch_name))
        if not cur:
            self.setProperty('selected_title', channel.get('name', ''))
            self.setProperty('selected_meta', '')
            self.setProperty('selected_desc', 'No programme data available')
            return
        title = cur.get('title', channel.get('name', ''))
        start = cur.get('start_timestamp') or cur.get('start') or 0
        stop = cur.get('stop_timestamp') or cur.get('end') or 0
        dur = _duration_minutes(start, stop)
        meta_bits = []
        if dur:
            meta_bits.append(dur)
        meta_bits.append('HD')
        meta_bits.append('S')
        if start:
            try:
                if int(start) <= now_ts <= int(stop):
                    meta_bits.append(f'Started at {_format_clock(start)}')
                else:
                    meta_bits.append(f'Starts at {_format_clock(start)}')
            except Exception:
                pass
        self.setProperty('selected_title', title)
        self.setProperty('selected_meta', '   '.join(meta_bits))
        self.setProperty('selected_desc', _short_plot(cur.get('description', ''), length=240))

    def _refresh_ruler_and_rows(self, rebuild=True):
        for i in range(SLOT_COUNT):
            ts = self._cursor + i * SLOT_MINUTES * 60
            self.setProperty(f'slot{i + 1}', _format_clock(ts))

        end_ts = self._cursor + SLOT_COUNT * SLOT_MINUTES * 60
        self.setProperty(
            'window_label',
            f'{_format_clock(self._cursor)} - {_format_clock(end_ts)}'
        )

        # "Now" indicator over the ruler
        now_ts = time.time()
        if self._cursor <= now_ts < end_ts:
            # 5 columns live at x=360..1880 (1520 px wide). Anchor=40 (list left edge)
            frac = (now_ts - self._cursor) / (SLOT_COUNT * SLOT_MINUTES * 60)
            x_px = 360 + int(frac * (1880 - 360))
            self.setProperty('now_x', str(x_px))
        else:
            self.setProperty('now_x', '')

        ctl = self.getControl(9000)
        if rebuild:
            ctl.reset()
            items = []
            for ch in self.channels:
                li = xbmcgui.ListItem(label=ch.get('name', ''))
                li.setArt({'icon': ch.get('stream_icon', '') or ADDON_ICON,
                           'thumb': ch.get('stream_icon', '') or ADDON_ICON})
                li.setProperty('num', str(ch.get('num', '')))
                progs = self.epg_map.get(str(ch.get('stream_id')), [])
                for i in range(SLOT_COUNT):
                    slot_ts = self._cursor + i * SLOT_MINUTES * 60
                    prog = _find_block(progs, slot_ts)
                    li.setProperty(f'b{i + 1}t', (prog.get('title', '') if prog else ''))
                    li.setProperty(
                        f'b{i + 1}s',
                        _format_clock(prog.get('start_timestamp') or prog.get('start') or 0)
                        if prog else ''
                    )
                items.append(li)
            ctl.addItems(items)
        else:
            # Pan only -> mutate existing ListItems' Block properties.
            try:
                size = ctl.size()
            except Exception:
                size = 0
            for row in range(size):
                try:
                    li = ctl.getListItem(row)
                except Exception:
                    continue
                if row >= len(self.channels):
                    continue
                ch = self.channels[row]
                progs = self.epg_map.get(str(ch.get('stream_id')), [])
                for i in range(SLOT_COUNT):
                    slot_ts = self._cursor + i * SLOT_MINUTES * 60
                    prog = _find_block(progs, slot_ts)
                    li.setProperty(f'b{i + 1}t', (prog.get('title', '') if prog else ''))
                    li.setProperty(
                        f'b{i + 1}s',
                        _format_clock(prog.get('start_timestamp') or prog.get('start') or 0)
                        if prog else ''
                    )

    def _on_channel_moved(self):
        idx = self.getControl(9000).getSelectedPosition()
        if idx < 0 or idx >= len(self.channels):
            return
        ch = self.channels[idx]
        self.setProperty('pip_channel', ch.get('name', ''))
        self._update_hero(ch)
        # PiP only starts on explicit OK now (single click).

    def _start_pip_now(self, channel):
        self._start_pip(channel)

    def _restart_pip_for_focused(self):
        if self._closing or not self.pip_enabled:
            return
        try:
            idx = self.getControl(9000).getSelectedPosition()
        except Exception:
            return
        if idx < 0 or idx >= len(self.channels):
            return
        self._last_pip_id = None
        self._pip_scheduler.schedule(self.channels[idx])

    def _start_pip(self, channel):
        if not self.pip_enabled:
            return
        stream_id = str(channel.get('stream_id'))
        if not stream_id or stream_id == self._last_pip_id:
            return
        if not self._play_resolver:
            return
        try:
            url = self._play_resolver(stream_id)
        except Exception:
            return
        if not url:
            return
        li = xbmcgui.ListItem(path=url)
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        try:
            self._player.play(url, li, windowed=True)
            self._last_pip_id = stream_id
        except Exception:
            pass

    def _stop_pip(self):
        try:
            if self._player.isPlaying():
                self._player.stop()
        except Exception:
            pass
        self._last_pip_id = None

    def _full_play(self, channel):
        stream_id = str(channel.get('stream_id'))
        if not stream_id or not self._play_resolver:
            return
        try:
            url = self._play_resolver(stream_id)
        except Exception:
            url = None
        if not url:
            xbmcgui.Dialog().notification('Poseidon Guide', 'Stream unavailable',
                                          xbmcgui.NOTIFICATION_ERROR, 3000)
            return
        self._pip_scheduler.cancel()
        self._last_pip_id = stream_id
        li = xbmcgui.ListItem(path=url)
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        self._player.play(url, li)

    def _toggle_favourite_focused(self):
        idx = self.getControl(9000).getSelectedPosition()
        if idx < 0 or idx >= len(self.channels):
            return
        ch = self.channels[idx]
        sid = str(ch.get('stream_id'))
        name = ch.get('name', 'channel')
        from resources.lib import favourites as _fav
        added = _fav.toggle(sid)
        msg = (f'Pinned: {name}' if added else f'Unpinned: {name}')
        xbmcgui.Dialog().notification('Favourites', msg,
                                      xbmcgui.NOTIFICATION_INFO, 1500)


def open_grid_window(theme, channels, epg_map, play_resolver,
                     pip_enabled=True, pip_autoplay=True):
    show_first_run_tutorial()
    xml_file = 'script-poseidonguide-grid.xml'
    if theme == 'directv':
        xml_file = 'script-poseidonguide-directv-grid.xml'
    elif theme == 'spectrum':
        xml_file = 'script-poseidonguide-spectrum-grid.xml'
    elif theme == 'redw':
        # Red W Media has no dedicated grid XML; reuse its main list view
        # which already shows three time-columns (CURRENT / FUTURE / FUTURE).
        xml_file = 'script-poseidonguide-redw-main.xml'
    w = GuideGridWindow(
        xml_file,
        ADDON_PATH,
        'default',
        '1080i',
        channels=channels,
        epg_map=epg_map,
        theme=theme,
        pip_enabled=pip_enabled,
        pip_autoplay=pip_autoplay,
        play_resolver=play_resolver,
    )
    w.doModal()
    del w
