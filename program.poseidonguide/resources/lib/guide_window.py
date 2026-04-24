"""
Poseidon Guide - Sky / Virgin style full-screen EPG window with PiP.

Implemented as a Kodi xbmcgui.WindowXML so we get a proper TV-grid layout
instead of the default directory listing. One XML covers both themes -
colours are injected via Skin.Strings per theme before showing.
"""
import os
import time
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


class GuideSkinWindow(xbmcgui.WindowXML):
    """Sky/Virgin-style EPG with Picture-in-Picture preview."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channels = kwargs.get('channels', [])
        self.epg_map = kwargs.get('epg_map', {})  # stream_id -> [programs]
        self.theme = kwargs.get('theme', 'sky')
        self.pip_enabled = kwargs.get('pip_enabled', True)
        self.pip_autoplay = kwargs.get('pip_autoplay', True)
        self._player = xbmc.Player()
        self._last_pip_id = None
        self._play_resolver = kwargs.get('play_resolver')  # callable(stream_id) -> url
        self._last_move_ts = 0
        self._pip_debounce = 0.6  # seconds between PiP starts on fast navigation

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
            self._stop_pip()
            self.close()
            return
        # Channel list navigation triggers PiP + grid refresh on a debounce.
        if action_id in (1, 2, 3, 4):   # up/down/left/right
            xbmc.sleep(60)              # let the focus update
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
        # PiP: debounce so rapid scrolling doesn't spam the portal.
        now = time.time()
        if self.pip_enabled and self.pip_autoplay and (now - self._last_move_ts) >= self._pip_debounce:
            self._last_move_ts = now
            self._start_pip(channel)

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
        self._stop_pip()
        li = xbmcgui.ListItem(path=url)
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        # Close the dialog and let Kodi take over with the fullscreen player.
        self.close()
        xbmc.Player().play(url, li)


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
