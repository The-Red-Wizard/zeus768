# -*- coding: utf-8 -*-
"""
Bento-style Link Searcher Dialog for Genesis
=============================================
A live source-finder UI shown while scrapers run in parallel.
Each scraper gets a "card" tile arranged in a bento grid. Tiles
update in real-time:

    pending  -> grey card, "Queued"
    running  -> amber accent + spinner dot, "Searching..."
    done     -> green accent, count + top quality
    failed   -> red accent, "No results"

The dialog also has a footer with totals and a Continue/Cancel pair.
Designed to be driven from scrapers.search_all(..., progress_cb=...).
"""
import os
import time
import threading
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
MEDIA = os.path.join(ADDON_PATH, 'resources', 'media', 'bento')

# Layout - Kodi WindowDialog uses the skin's reference resolution (default
# Estuary = 1280x720). Sizes/positions here are in that reference grid and
# get auto-scaled to the real display by the skin engine.
COLS = 4
TILE_W = 200
TILE_H = 120
GAP_X = 16
GAP_Y = 16

# Card dimensions (centered on a 1280x720 reference grid)
_REF_W = 1280
_REF_H = 720
_GRID_W = COLS * TILE_W + (COLS - 1) * GAP_X        # 848
_CARD_W = _GRID_W + 80                              # 928
_CARD_H = 600
_CARD_X = (_REF_W - _CARD_W) // 2                   # 176
_CARD_Y = (_REF_H - _CARD_H) // 2                   # 60

GRID_LEFT = _CARD_X + 40                            # 216
GRID_TOP = _CARD_Y + 130                            # 190

# Action codes (Kodi remote)
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_STOP = 13

STATUS_COLORS = {
    'pending': ('[COLOR FF9aa0b4]', 'Queued'),
    'running': ('[COLOR FFffc400]', 'Searching...'),
    'done':    ('[COLOR FF40dc80]', 'Found'),
    'failed':  ('[COLOR FFe85060]', 'No results'),
}


def _media(name):
    return os.path.join(MEDIA, name)


class BentoSearchDialog(xbmcgui.WindowDialog):
    """Live, bento-style search progress dialog.

    Usage:
        dlg = BentoSearchDialog(query='Inception (2010)')
        dlg.show()
        results = scrapers.search_all(query, '1080p',
                                      imdb_id=..., progress_cb=dlg.on_progress)
        dlg.finish(len(results))
        if dlg.cancelled:
            return
        dlg.close()
    """

    def __init__(self, query='', subtitle=''):
        super().__init__()
        self.query = query or 'Search'
        self.subtitle = subtitle or ''
        self.cancelled = False
        self._tiles = {}  # name -> dict(controls, status)
        self._tile_order = []
        self._lock = threading.Lock()
        self._start_ts = time.time()
        self._total_found = 0
        self._done_count = 0
        self._finished = False
        self._build_chrome()

    # ── Chrome (backdrop / header / footer) ──────────────────────────────────
    def _build_chrome(self):
        # Full-screen darkening backdrop sized for the 1280x720 reference grid
        self.addControl(xbmcgui.ControlImage(0, 0, _REF_W, _REF_H, _media('backdrop.png')))
        # Solid dim layer so underlying view is fully blocked
        self.addControl(xbmcgui.ControlImage(
            0, 0, _REF_W, _REF_H, '', colorDiffuse='EE0A0C12'))

        # Centered card panel
        self.addControl(xbmcgui.ControlImage(
            _CARD_X, _CARD_Y, _CARD_W, _CARD_H, '',
            colorDiffuse='FF131722'))

        # Header bar (inside the card)
        self.addControl(xbmcgui.ControlImage(
            _CARD_X + 16, _CARD_Y + 16, _CARD_W - 32, 86, _media('header.png')))
        self.title_lbl = xbmcgui.ControlLabel(
            _CARD_X + 30, _CARD_Y + 26, _CARD_W - 60, 32,
            '[B]Link Searcher[/B]',
            font='font14', textColor='FFFFFFFF',
        )
        self.addControl(self.title_lbl)
        self.query_lbl = xbmcgui.ControlLabel(
            _CARD_X + 30, _CARD_Y + 62, _CARD_W - 60, 28,
            f'[COLOR FF8ab4ff]{self.query}[/COLOR]' + (f'   [COLOR FF7a8095]{self.subtitle}[/COLOR]' if self.subtitle else ''),
            font='font12', textColor='FFc7cce0',
        )
        self.addControl(self.query_lbl)

        # Footer placeholders (will be updated)
        _footer_y = _CARD_Y + _CARD_H - 60
        self.stats_lbl = xbmcgui.ControlLabel(
            _CARD_X + 30, _footer_y, _CARD_W - 380, 30,
            '[COLOR FF8ab4ff]Initializing scrapers...[/COLOR]',
            font='font12',
        )
        self.addControl(self.stats_lbl)

        # Buttons (Cancel + Continue) - sized to fit inside the card
        _btn_y = _footer_y - 6
        _continue_x = _CARD_X + _CARD_W - 30 - 160
        _cancel_x = _continue_x - 16 - 120
        self.cancel_btn = xbmcgui.ControlButton(
            _cancel_x, _btn_y, 120, 44, 'Cancel',
            focusTexture=_media('btn_secondary.png'),
            noFocusTexture=_media('btn_secondary.png'),
            font='font12', textColor='FFffffff',
            alignment=2 + 4,  # center
        )
        self.continue_btn = xbmcgui.ControlButton(
            _continue_x, _btn_y, 160, 44, '[B]Continue[/B]',
            focusTexture=_media('btn_primary.png'),
            noFocusTexture=_media('btn_primary.png'),
            font='font12', textColor='FFffffff',
            alignment=2 + 4,
        )
        self.addControl(self.cancel_btn)
        self.addControl(self.continue_btn)
        self.setFocus(self.cancel_btn)
        self.cancel_btn.controlRight(self.continue_btn)
        self.continue_btn.controlLeft(self.cancel_btn)

    # ── Tile creation / update ───────────────────────────────────────────────
    def _tile_pos(self, idx):
        col = idx % COLS
        row = idx // COLS
        x = GRID_LEFT + col * (TILE_W + GAP_X)
        y = GRID_TOP + row * (TILE_H + GAP_Y)
        return x, y

    def _create_tile(self, name):
        idx = len(self._tile_order)
        x, y = self._tile_pos(idx)

        bg = xbmcgui.ControlImage(x, y, TILE_W, TILE_H, _media('tile_idle.png'))
        accent = xbmcgui.ControlImage(x, y, TILE_W, 5, _media('accent_idle.png'))
        name_lbl = xbmcgui.ControlLabel(
            x + 12, y + 10, TILE_W - 24, 24,
            f'[B]{name}[/B]', font='font12', textColor='FFffffff',
        )
        status_lbl = xbmcgui.ControlLabel(
            x + 12, y + 36, TILE_W - 24, 22,
            '[COLOR FF9aa0b4]Queued[/COLOR]', font='font11',
        )
        count_lbl = xbmcgui.ControlLabel(
            x + 12, y + 58, TILE_W - 24, 42,
            '[COLOR FF7a8095]—[/COLOR]', font='font24', textColor='FFffffff',
        )
        quality_lbl = xbmcgui.ControlLabel(
            x + 12, y + 100, TILE_W - 24, 18,
            '', font='font10', textColor='FFc7cce0',
        )

        self.addControls([bg, accent, name_lbl, status_lbl, count_lbl, quality_lbl])
        self._tiles[name] = {
            'bg': bg, 'accent': accent,
            'name_lbl': name_lbl,
            'status_lbl': status_lbl,
            'count_lbl': count_lbl,
            'quality_lbl': quality_lbl,
            'status': 'pending',
            'count': 0,
        }
        self._tile_order.append(name)

    def _update_tile(self, name, status, count, top_quality):
        t = self._tiles.get(name)
        if not t:
            return
        color_tag, status_text = STATUS_COLORS.get(status, STATUS_COLORS['pending'])

        # Background + accent
        bg_map = {
            'pending': 'tile_idle.png',
            'running': 'tile_running.png',
            'done':    'tile_done.png',
            'failed':  'tile_failed.png',
        }
        accent_map = {
            'pending': 'accent_idle.png',
            'running': 'accent_running.png',
            'done':    'accent_done.png',
            'failed':  'accent_failed.png',
        }
        t['bg'].setImage(_media(bg_map[status]))
        t['accent'].setImage(_media(accent_map[status]))

        # Status text
        suffix = ''
        if status == 'done':
            suffix = f' • {count}'
        t['status_lbl'].setLabel(f'{color_tag}{status_text}{suffix}[/COLOR]')

        # Big number / dots
        if status == 'done':
            t['count_lbl'].setLabel(f'[B]{count}[/B]')
        elif status == 'running':
            t['count_lbl'].setLabel('[COLOR FFffc400]•••[/COLOR]')
        elif status == 'failed':
            t['count_lbl'].setLabel('[COLOR FFe85060]0[/COLOR]')
        else:
            t['count_lbl'].setLabel('[COLOR FF7a8095]—[/COLOR]')

        # Top quality badge
        if top_quality:
            q_color = {
                '2160p': 'FFffd54f', '1080p': 'FF40dc80',
                '720p': 'FFffc400', '480p': 'FFe89060'
            }.get(top_quality, 'FFc7cce0')
            t['quality_lbl'].setLabel(f'[COLOR {q_color}]Top: {top_quality}[/COLOR]')
        else:
            t['quality_lbl'].setLabel('')

        t['status'] = status
        t['count'] = count

    def _refresh_stats(self):
        elapsed = time.time() - self._start_ts
        done = sum(1 for t in self._tiles.values() if t['status'] in ('done', 'failed'))
        total = len(self._tiles)
        found = sum(t['count'] for t in self._tiles.values() if t['status'] == 'done')
        self._total_found = found
        self._done_count = done
        progress = f'[COLOR FF40dc80]{found}[/COLOR] sources found  •  ' \
                   f'[COLOR FF8ab4ff]{done}/{total}[/COLOR] scrapers  •  ' \
                   f'[COLOR FFc7cce0]{elapsed:0.1f}s[/COLOR]'
        self.stats_lbl.setLabel(progress)

    # ── Public API ──────────────────────────────────────────────────────────
    def on_progress(self, name, status, count, top_quality):
        """Called from scrapers (main thread - safe to touch controls).

        Thread-safety: as_completed iteration in search_all runs on the same
        thread that called search_all (i.e. our caller), so we update controls
        directly. A lock guards parallel emits just in case.
        """
        with self._lock:
            if name not in self._tiles:
                self._create_tile(name)
            self._update_tile(name, status, count, top_quality or '')
            self._refresh_stats()

    def finish(self, total_results=None):
        """Mark the search complete and update the footer."""
        self._finished = True
        elapsed = time.time() - self._start_ts
        if total_results is None:
            total_results = self._total_found
        summary = (
            f'[B][COLOR FF40dc80]{total_results}[/COLOR][/B] unique sources after dedupe  •  '
            f'[COLOR FFc7cce0]{elapsed:0.1f}s[/COLOR]'
        )
        self.stats_lbl.setLabel(summary)
        self.setFocus(self.continue_btn)

    def wait_for_user(self, auto_close_seconds=0):
        """Block until user clicks Continue / Cancel (or auto-close timer hits).

        Returns True if user wants to continue, False if cancelled.
        """
        # Auto-close countdown if requested
        deadline = time.time() + auto_close_seconds if auto_close_seconds > 0 else None

        monitor = xbmc.Monitor()
        while True:
            if monitor.waitForAbort(0.1):
                self.cancelled = True
                return False
            # Check button focus / click via Window's onAction not available on WindowDialog,
            # we use onControl + onAction overrides (set below). Just sleep and exit when set.
            if getattr(self, '_user_done', False):
                return not self.cancelled
            if deadline and time.time() >= deadline and self._finished:
                return True

    # ── Kodi event hooks ────────────────────────────────────────────────────
    def onControl(self, control):
        if control == self.cancel_btn:
            self.cancelled = True
            self._user_done = True
        elif control == self.continue_btn:
            self.cancelled = False
            self._user_done = True

    def onAction(self, action):
        try:
            aid = action.getId()
        except Exception:
            return
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK, ACTION_STOP):
            self.cancelled = True
            self._user_done = True


def is_enabled():
    """Honor the user setting (default = on)."""
    try:
        val = ADDON.getSetting('bento_search')
        return val != 'false'
    except Exception:
        return True
