"""
SALTS - Salts-style fullscreen Source Search + Source Picker windows.

Two classes:
  * SaltsSourceProgressWindow  -- replaces xbmcgui.DialogProgress() while scraping.
                                  Non-modal: caller .show()s it, updates label
                                  text and progress fill via update(), checks
                                  is_canceled, then .close()s.
  * SaltsSourcePickerWindow    -- replaces xbmcgui.Dialog().select() for source
                                  selection. Modal via doModal(); selected row
                                  index is in .selected_index (-1 = cancelled).

Both windows use the SALTS gold + dark visual language and a fullscreen
fanart backdrop. They live under resources/skins/Default/720p.
"""
import os
import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')

# Progress-window control IDs (kept in sync with salts_source_progress.xml)
P_BACKDROP    = 110
P_POSTER      = 111
P_TITLE       = 120
P_SUBTITLE    = 121
P_SCRAPER     = 130
P_STATS       = 131
P_PERCENT     = 140
P_BAR         = 150
P_CANCEL_BTN  = 160

# Picker-window control IDs (kept in sync with salts_source_picker.xml)
S_BACKDROP    = 110
S_POSTER      = 111
S_TITLE       = 120
S_SUMMARY     = 121
S_LIST        = 200
S_CANCEL_BTN  = 300
S_COUNTER     = 400

# Progress fill is anchored at left=420 in the skin, max width=780.
_BAR_MAX = 780

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK      = 92


class SaltsSourceProgressWindow(xbmcgui.WindowXMLDialog):
    """Fullscreen scraping-progress dialog."""

    def __new__(cls, xml='salts_source_progress.xml', path=ADDON_PATH,
                title='', fanart='', poster=''):
        return super().__new__(cls, xml, path, 'Default', '720p')

    def __init__(self, xml='salts_source_progress.xml', path=ADDON_PATH,
                 title='', fanart='', poster=''):
        super().__init__()
        self._title = title or ''
        self._fanart = fanart or ''
        self._poster = poster or ''
        self.is_canceled = False

    def onInit(self):
        try:
            if self._fanart:
                self.getControl(P_BACKDROP).setImage(self._fanart)
            if self._poster:
                self.getControl(P_POSTER).setImage(self._poster)
            if self._title:
                self.getControl(P_TITLE).setLabel(self._title)
        except Exception:
            pass
        try:
            self.setFocusId(P_CANCEL_BTN)
        except Exception:
            pass

    # --- public API used by default.py -------------------------------

    def update(self, percent, scraper_line='', stats_line='', subtitle=''):
        """Update progress percentage (0..100) and the three label lines."""
        try:
            pct = max(0, min(100, int(percent)))
            try:
                self.getControl(P_PERCENT).setLabel(f'{pct}%')
            except Exception:
                pass
            try:
                # Bar fill width = pct% of _BAR_MAX. 1px minimum so the
                # control stays visible at 0%.
                w = max(1, int(_BAR_MAX * pct / 100))
                self.getControl(P_BAR).setWidth(w)
            except Exception:
                pass
            if scraper_line:
                try:
                    self.getControl(P_SCRAPER).setLabel(scraper_line)
                except Exception:
                    pass
            if stats_line:
                try:
                    self.getControl(P_STATS).setLabel(stats_line)
                except Exception:
                    pass
            if subtitle:
                try:
                    self.getControl(P_SUBTITLE).setLabel(subtitle)
                except Exception:
                    pass
        except Exception:
            pass

    def iscanceled(self):
        """Drop-in replacement for xbmcgui.DialogProgress.iscanceled()."""
        return self.is_canceled

    # --- input handlers ---------------------------------------------

    def onClick(self, control_id):
        if control_id == P_CANCEL_BTN:
            self.is_canceled = True
            self.close()

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.is_canceled = True
            self.close()


class SaltsSourcePickerWindow(xbmcgui.WindowXMLDialog):
    """Fullscreen source-picker dialog (replaces Dialog().select())."""

    def __new__(cls, xml='salts_source_picker.xml', path=ADDON_PATH,
                title='', summary='', fanart='', poster='', items=None):
        return super().__new__(cls, xml, path, 'Default', '720p')

    def __init__(self, xml='salts_source_picker.xml', path=ADDON_PATH,
                 title='', summary='', fanart='', poster='', items=None):
        super().__init__()
        self._title = title or ''
        self._summary = summary or ''
        self._fanart = fanart or ''
        self._poster = poster or ''
        self._items = list(items or [])
        self.selected_index = -1

    def onInit(self):
        try:
            if self._fanart:
                self.getControl(S_BACKDROP).setImage(self._fanart)
            if self._poster:
                self.getControl(S_POSTER).setImage(self._poster)
            if self._title:
                self.getControl(S_TITLE).setLabel(self._title)
            if self._summary:
                self.getControl(S_SUMMARY).setLabel(self._summary)
        except Exception:
            pass

        # Populate the list. Each entry in _items is a BBCode-formatted string
        # (matching the original Dialog().select() display_list lines).
        try:
            lst = self.getControl(S_LIST)
            li_objs = []
            for label in self._items:
                li = xbmcgui.ListItem(label=label)
                li_objs.append(li)
            lst.reset()
            lst.addItems(li_objs)
        except Exception:
            pass

        try:
            self.getControl(S_COUNTER).setLabel(f'{len(self._items)} items')
        except Exception:
            pass

        try:
            self.setFocusId(S_LIST)
        except Exception:
            pass

    # --- input handlers ---------------------------------------------

    def onClick(self, control_id):
        if control_id == S_LIST:
            try:
                self.selected_index = self.getControl(S_LIST).getSelectedPosition()
            except Exception:
                self.selected_index = -1
            self.close()
        elif control_id == S_CANCEL_BTN:
            self.selected_index = -1
            self.close()

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.selected_index = -1
            self.close()


# ---------------------------------------------------------------------------
# Convenience factories used by default.py
# ---------------------------------------------------------------------------

def open_progress(title='', fanart='', poster=''):
    """Create + show the progress dialog (non-modal). Returns the window."""
    win = SaltsSourceProgressWindow(title=title, fanart=fanart, poster=poster)
    win.show()
    # Give Kodi a moment to render the window before the caller starts
    # firing update() calls (matches the behaviour of DialogProgress.create()).
    xbmc.sleep(80)
    return win


def pick_source(title='', summary='', fanart='', poster='', items=None):
    """Show the picker modally. Returns the selected index (-1 on cancel)."""
    win = SaltsSourcePickerWindow(title=title, summary=summary,
                                  fanart=fanart, poster=poster, items=items)
    win.doModal()
    idx = win.selected_index
    del win
    return idx
