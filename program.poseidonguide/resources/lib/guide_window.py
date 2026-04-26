"""
Poseidon Guide - Sky / Virgin style full-screen EPG window with PiP.

Implemented as a Kodi xbmcgui.WindowXML so we get a proper TV-grid layout
instead of the default directory listing. One XML covers both themes -
colours are injected via Skin.Strings per theme before showing.
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


# ------------------------------------------------------------------
# Theme palettes.  FFAARRGGBB hex like Kodi expects.
# ------------------------------------------------------------------
THEMES = {
    'sky': {
        'PG_BG':       'FF0B2B57',   # deep Sky blue
        'PG_Accent':   'FF4CB4FF',   # Sky light-blue highlight
        'PG_Label':    'FFFFFFFF',
        'PG_SubLabel': 'FFBCD4FF',
        'PG_Logo':     ADDON_ICON,
        'hint':        'Sky TV style - left/right: channels  |  up/down: programmes  |  OK: watch',
    },
    'virgin': {
        'PG_BG':       'FF111111',   # near-black
        'PG_Accent':   'FFDB0032',   # Virgin red
        'PG_Label':    'FFFFFFFF',
        'PG_SubLabel': 'FFE8E8E8',
        'PG_Logo':     ADDON_ICON,
        'hint':        'Virgin TV style - left/right: channels  |  up/down: programmes  |  OK: watch',
    },
    'classic': {
        'PG_BG':       'FF1A1A1A',
        'PG_Accent':   'FF4CAF50',
        'PG_Label':    'FFFFFFFF',
        'PG_SubLabel': 'FFA0A0A0',
        'PG_Logo':     ADDON_ICON,
        'hint':        'Classic - left/right: channels  |  up/down: programmes  |  OK: watch',
    },
}


def _apply_theme(theme_key):
    """Push the chosen palette into Skin.Strings so the XML can read them."""
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
        return datetime.fromtimestamp(int(ts)).strftime('%H:%M')
    except Exception:
        return ''


def _short_plot(text, length=140):
    text = (text or '').strip().replace('\n', ' ')
    return text if len(text) <= length else text[:length - 1] + '...'


class _PipScheduler:
    """Defer PiP starts until the user stops scrolling.

    Channel-list focus changes fire fast on key-repeat. Spinning up a fresh
    HLS stream on every key event is what made the previous build feel
    laggy. This helper batches them: every focus change resets a 250 ms
    timer, and only the *last* request actually triggers the play.
    """

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
    """xbmc.Player subclass that calls back into the dialog window when
    full-screen playback ends, so the dialog can resume PiP for whichever
    channel is currently focused.
    """

    def __init__(self, on_full_stop):
        super().__init__()
        self._on_full_stop = on_full_stop

    def onPlayBackStopped(self):  # noqa: N802 - Kodi API
        try:
            self._on_full_stop()
        except Exception:
            pass

    def onPlayBackEnded(self):  # noqa: N802 - Kodi API
        try:
            self._on_full_stop()
        except Exception:
            pass


class GuideSkinWindow(xbmcgui.WindowXML):
    """Sky/Virgin-style EPG with Picture-in-Picture preview."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channels = kwargs.get('channels', [])
        self.epg_map = kwargs.get('epg_map', {})  # stream_id -> [programs]
        self.theme = kwargs.get('theme', 'sky')
        self.pip_enabled = kwargs.get('pip_enabled', True)
        self.pip_autoplay = kwargs.get('pip_autoplay', True)
        self._player = _PipPlayer(self._restart_pip_for_focused)
        self._last_pip_id = None
        self._play_resolver = kwargs.get('play_resolver')  # callable(stream_id) -> url
        self._pip_scheduler = _PipScheduler(self._start_pip_now, delay=0.25)
        self._closing = False

    # ---- Kodi callbacks -----------------------------------------------------
    def onInit(self):
        theme = _apply_theme(self.theme)
        self.setProperty('theme_hint', theme['hint'])
        self.setProperty('pip_channel', '')
        # Hide PiP box if user disabled it
        xbmc.executebuiltin(
            'Skin.SetString(PG_PiP_Hidden,%s)' % ('false' if self.pip_enabled else 'true')
        )
        self._populate_channels()
        if self.channels:
            self._refresh_program_grid(self.channels[0])

    def onAction(self, action):
        action_id = action.getId()
        # Escape / Back / Stop closes the window AND stops PiP playback.
        if action_id in (9, 10, 13, 92):  # PreviousMenu/Stop/Back/NavBack
            self._closing = True
            self._pip_scheduler.cancel()
            self._stop_pip()
            self.close()
            return
        # "I" (Info) key -> toggle to the time-ruler grid view.
        if action_id == 11:
            self._closing = True
            self._pip_scheduler.cancel()
            self._stop_pip()
            self.close()
            xbmcgui.Window(10000).setProperty('pg_switch_to_grid', '1')
            return
        # Channel list navigation triggers PiP + grid refresh on a debounce.
        if action_id in (1, 2, 3, 4):   # up/down/left/right
            xbmc.sleep(40)              # let the focus update
            self._on_channel_moved()

    def onClick(self, control_id):
        if control_id == 9000:  # channel list clicked -> play full screen
            idx = self.getControl(9000).getSelectedPosition()
            if 0 <= idx < len(self.channels):
                self._full_play(self.channels[idx])
        elif control_id == 9001:  # programme clicked -> play that channel
            idx = self.getControl(9000).getSelectedPosition()
            if 0 <= idx < len(self.channels):
                self._full_play(self.channels[idx])

    # ---- Helpers -----------------------------------------------------------
    def _populate_channels(self):
        ctl = self.getControl(9000)
        items = []
        for ch in self.channels:
            li = xbmcgui.ListItem(label=ch.get('name', ''))
            li.setArt({'icon': ch.get('stream_icon', '') or ADDON_ICON,
                       'thumb': ch.get('stream_icon', '') or ADDON_ICON})
            progs = self.epg_map.get(str(ch.get('stream_id')), [])
            now_title = progs[0].get('title', '') if progs else ''
            li.setProperty('now_title', now_title)
            items.append(li)
        ctl.addItems(items)

    def _refresh_program_grid(self, channel):
        grid = self.getControl(9001)
        grid.reset()
        progs = self.epg_map.get(str(channel.get('stream_id')), [])
        now_ts = time.time()
        items = []
        for p in progs[:20]:
            title = p.get('title', '')
            start = p.get('start_timestamp') or p.get('start') or 0
            stop = p.get('stop_timestamp') or p.get('end') or 0
            tlabel = f"{_format_time(start)} - {_format_time(stop)}"
            li = xbmcgui.ListItem(label=title)
            li.setLabel2(tlabel)
            li.setProperty('plot_short', _short_plot(p.get('description', '')))
            # Mark "now playing" for visual distinction later if needed
            if start <= now_ts <= stop:
                li.setProperty('is_now', '1')
            items.append(li)
        grid.addItems(items)

        # Update the header with the selected (first) programme's details.
        if progs:
            head = progs[0]
            self.setProperty('selected_title', head.get('title', ''))
            self.setProperty('selected_time',
                             f"{_format_time(head.get('start_timestamp'))} - "
                             f"{_format_time(head.get('stop_timestamp'))}")
            self.setProperty('selected_desc',
                             _short_plot(head.get('description', ''), length=200))
        else:
            self.setProperty('selected_title', channel.get('name', ''))
            self.setProperty('selected_time', '')
            self.setProperty('selected_desc', 'No programme data available')

    def _on_channel_moved(self):
        idx = self.getControl(9000).getSelectedPosition()
        if idx < 0 or idx >= len(self.channels):
            return
        channel = self.channels[idx]
        self._refresh_program_grid(channel)
        self.setProperty('pip_channel', channel.get('name', ''))
        # PiP: defer start until the user stops scrolling.
        if self.pip_enabled and self.pip_autoplay:
            self._pip_scheduler.schedule(channel)

    def _start_pip_now(self, channel):
        self._start_pip(channel)

    def _restart_pip_for_focused(self):
        """Called by _PipPlayer when full-screen playback ends. Resumes PiP
        on whichever channel is currently focused so the user lands back
        in the guide WITH PiP active."""
        if self._closing or not self.pip_enabled:
            return
        try:
            idx = self.getControl(9000).getSelectedPosition()
        except Exception:
            return
        if idx < 0 or idx >= len(self.channels):
            return
        # Force a fresh start (clear last id so _start_pip doesn't bail).
        self._last_pip_id = None
        self._pip_scheduler.schedule(self.channels[idx])

    def _start_pip(self, channel):
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
        # Cancel any pending PiP starts so we don't race the full-screen play.
        self._pip_scheduler.cancel()
        # Tell the resume handler this is the channel we just kicked off, so
        # when the user stops the stream the PiP comes back on the same one.
        self._last_pip_id = stream_id
        li = xbmcgui.ListItem(path=url)
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        # Do NOT close the window. xbmc.Player().play() takes the foreground
        # full-screen automatically; the dialog stays modal underneath, so
        # when the user stops/exits the stream they land back in the guide
        # and _PipPlayer.onPlayBackStopped restarts PiP.
        self._player.play(url, li)


def open_guide_window(theme, channels, epg_map, play_resolver,
                      pip_enabled=True, pip_autoplay=True):
    """Show the EPG window modally. Caller supplies a resolver callable that
    turns a stream_id into a playable URL (mode-aware)."""
    w = GuideSkinWindow(
        'script-poseidonguide-main.xml',
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
# TIME-RULER GRID VIEW (v1.3.0 upgrade)
# ======================================================================
SLOT_MINUTES = 30   # each column = 30 min
SLOT_COUNT = 6      # 6 slots visible -> matches grid XML


def _slot_start(now_ts):
    """Round down to the nearest 30 minute slot."""
    secs = int(now_ts)
    return secs - (secs % (SLOT_MINUTES * 60))


def _find_block(programs, slot_start_ts):
    """Return the programme whose timespan overlaps this slot, or None."""
    slot_end_ts = slot_start_ts + SLOT_MINUTES * 60
    for p in programs:
        s = int(p.get('start_timestamp') or p.get('start') or 0)
        e = int(p.get('stop_timestamp') or p.get('end') or 0)
        if s == 0 and e == 0:
            continue
        if s < slot_end_ts and e > slot_start_ts:
            return p
    return None


class GuideGridWindow(xbmcgui.WindowXML):
    """Time-ruler grid view - channels x time slots with PiP."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        # Time cursor - programmes starting at this slot fill Block1.
        self._cursor = _slot_start(time.time())

    def onInit(self):
        _apply_theme(self.theme)
        xbmc.executebuiltin(
            'Skin.SetString(PG_PiP_Hidden,%s)' % ('false' if self.pip_enabled else 'true')
        )
        self._refresh_ruler_and_rows()
        self.setProperty('pip_channel', '')

    def onAction(self, action):
        aid = action.getId()
        if aid in (9, 10, 13, 92):  # back / stop
            self._closing = True
            self._pip_scheduler.cancel()
            self._stop_pip()
            self.close()
            return
        # Left/Right pan the time window
        if aid == 1:  # left
            self._cursor -= SLOT_MINUTES * 60
            self._refresh_ruler_and_rows()
            return
        if aid == 2:  # right
            self._cursor += SLOT_MINUTES * 60
            self._refresh_ruler_and_rows()
            return
        # "I" (Info) key -> toggle back to list view.
        if aid == 11:
            self._closing = True
            self._pip_scheduler.cancel()
            self._stop_pip()
            self.close()
            xbmcgui.Window(10000).setProperty('pg_switch_to_list', '1')
            return
        # Up/Down let Kodi handle focus change in the list; after the frame,
        # refresh PiP.
        if aid in (3, 4):
            xbmc.sleep(40)
            self._on_channel_moved()

    def onClick(self, control_id):
        if control_id == 9000:
            idx = self.getControl(9000).getSelectedPosition()
            if 0 <= idx < len(self.channels):
                self._full_play(self.channels[idx])

    # ---- rendering ----
    def _refresh_ruler_and_rows(self):
        # Labels for the 6 slot columns
        for i in range(SLOT_COUNT):
            ts = self._cursor + i * SLOT_MINUTES * 60
            self.setProperty(f'slot{i + 1}', _format_time(ts))

        # Window label shows the viewport time range
        end_ts = self._cursor + SLOT_COUNT * SLOT_MINUTES * 60
        self.setProperty(
            'window_label',
            f'{_format_time(self._cursor)} - {_format_time(end_ts)}'
        )

        # Position the "now" indicator if current time falls inside the window.
        now_ts = time.time()
        if self._cursor <= now_ts < end_ts:
            # Columns live at x=260..1400 (1140 px wide, 6 slots)
            frac = (now_ts - self._cursor) / (SLOT_COUNT * SLOT_MINUTES * 60)
            x_px = 40 + 260 + int(frac * (1400 - 260))
            self.setProperty('now_x', str(x_px))
        else:
            self.setProperty('now_x', '')

        # Build one ListItem per channel with Block1..Block6 properties.
        ctl = self.getControl(9000)
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
                if prog:
                    li.setProperty(f'b{i + 1}t', prog.get('title', '')[:26])
                    start = prog.get('start_timestamp') or prog.get('start') or 0
                    li.setProperty(f'b{i + 1}s', _format_time(start))
                else:
                    li.setProperty(f'b{i + 1}t', '--')
                    li.setProperty(f'b{i + 1}s', '')
            items.append(li)
        ctl.addItems(items)

    # ---- PiP reuses same strategy as list view ----
    def _on_channel_moved(self):
        idx = self.getControl(9000).getSelectedPosition()
        if idx < 0 or idx >= len(self.channels):
            return
        ch = self.channels[idx]
        self.setProperty('pip_channel', ch.get('name', ''))
        if self.pip_enabled and self.pip_autoplay:
            self._pip_scheduler.schedule(ch)

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
        # Don't close - keep dialog modal underneath so player exit returns
        # to the guide and _PipPlayer auto-restarts PiP.
        self._player.play(url, li)


def open_grid_window(theme, channels, epg_map, play_resolver,
                     pip_enabled=True, pip_autoplay=True):
    """Modal time-ruler grid view."""
    w = GuideGridWindow(
        'script-poseidonguide-grid.xml',
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
