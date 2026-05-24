"""
SALTS - Custom Settings Window (Salts-style)

Renders the addon's settings (from resources/settings.xml) inside a fully
custom xbmcgui.WindowXMLDialog instead of Kodi's built-in addon-settings
dialog. Reads/writes values via xbmcaddon.Addon().getSetting / setSetting.

Launched from default.py via mode=salts_settings.
"""
import os
import re
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcgui


ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')

# Control IDs in salts_settings.xml
CTRL_CATEGORY_LIST = 100
CTRL_SETTINGS_LIST = 200
CTRL_CLOSE_BTN = 300
CTRL_RESET_BTN = 301
CTRL_SEARCH_BTN = 302
CTRL_DESC_BOX = 400
CTRL_PANEL_TITLE = 500
CTRL_SUBTITLE = 501

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_SELECT = 7
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4


def _parse_settings_xml():
    """
    Parse resources/settings.xml into a list of categories. Each category is:
        {
            'label': 'General',
            'settings': [ {raw dict of attrs}, ... ]   # in document order
        }
    """
    path = os.path.join(ADDON_PATH, 'resources', 'settings.xml')
    tree = ET.parse(path)
    root = tree.getroot()
    cats = []
    for cat in root.findall('category'):
        cats.append({
            'label': cat.get('label', 'General'),
            'settings': [dict(s.attrib) for s in cat.findall('setting')]
        })
    return cats


def _get_value(setting):
    """Read the current value for a setting via the addon API."""
    sid = setting.get('id')
    if not sid:
        return ''
    try:
        return ADDON.getSetting(sid)
    except Exception:
        return ''


def _set_value(setting, value):
    sid = setting.get('id')
    if not sid:
        return
    try:
        ADDON.setSetting(sid, '' if value is None else str(value))
    except Exception:
        pass


def _format_value(setting):
    """Human-readable value to show on the right side of the row."""
    stype = setting.get('type', '')
    val = _get_value(setting)

    if stype == 'bool':
        # Encode the toggle visually in Label2 itself, so it can't be
        # hidden by overlapping skin controls. Bright colors + block
        # characters so the "switch" is unmistakable.
        if val not in ('true', 'false'):
            val = (setting.get('default') or 'false').lower()
        if val == 'true':
            return '[B][COLOR FF0d1117]\u2588\u2588[/COLOR][COLOR FF3FB950]\u2588\u2588 ON [/COLOR][/B]'
        return '[B][COLOR FFF85149][ OFF \u2588\u2588[/COLOR][COLOR FF30363d]\u2588\u2588[/COLOR][/B]'
    if stype == 'slider':
        return '[ %s ]' % (val or setting.get('default', '') or '0')
    if stype == 'labelenum':
        values = (setting.get('values') or '').split('|')
        if val == '' or val is None:
            val = setting.get('default', '')
        if val.isdigit() and int(val) < len(values):
            val = values[int(val)]
        return '[ %s \u25BE ]' % val
    if stype == 'text':
        if not val:
            shown = '[COLOR FF8b949e]tap to enter[/COLOR]'
        elif setting.get('option') == 'hidden' or 'password' in (setting.get('id') or '').lower():
            shown = '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022'
        elif len(val) > 28:
            shown = val[:25] + '...'
        else:
            shown = val
        return '[COLOR FFFFD700][[/COLOR] %s [COLOR FFFFD700]][/COLOR]' % shown
    if stype == 'action':
        return '[B][COLOR FFFFD700][ RUN \u25B8 ][/COLOR][/B]'
    return val or ''


# ---------- enable="eq(-N,true)" evaluator (simplified) -----------------

_EQ_RE = re.compile(r'eq\(\s*(-?\d+)\s*,\s*([^)]+?)\s*\)')


def _is_enabled(settings, index):
    """
    Evaluate the `enable` attribute of settings[index] against earlier rows.
    Supports the common form `eq(-N,true)` (and `+` between multiple eq()
    expressions, all of which must be true). Anything we don't understand
    is treated as enabled.
    """
    s = settings[index]
    expr = s.get('enable')
    if not expr:
        return True
    parts = [p.strip() for p in expr.split('+')]
    for p in parts:
        m = _EQ_RE.search(p)
        if not m:
            return True  # don't fail closed on unknown syntax
        offset = int(m.group(1))
        wanted = m.group(2).strip().lower()
        ref_index = index + offset
        if ref_index < 0 or ref_index >= len(settings):
            return False
        ref = settings[ref_index]
        ref_val = _get_value(ref).lower()
        if ref_val != wanted:
            return False
    return True


# ---------- editors for each setting type -------------------------------


def _edit_bool(setting):
    current = _get_value(setting) == 'true'
    _set_value(setting, 'false' if current else 'true')


def _edit_slider(setting):
    rng = (setting.get('range') or '').split(',')
    try:
        mn = float(rng[0]); step = float(rng[1]); mx = float(rng[2])
    except (IndexError, ValueError):
        mn, step, mx = 0, 1, 100
    current = _get_value(setting) or setting.get('default', '0')
    try:
        cur = float(current)
    except ValueError:
        cur = mn
    label = setting.get('label', 'Value')
    prompt = '%s (min %g, max %g, step %g)' % (label, mn, mx, step)
    raw = xbmcgui.Dialog().input(prompt, str(cur), type=xbmcgui.INPUT_NUMERIC)
    if raw == '' or raw is None:
        return
    try:
        val = float(raw)
    except ValueError:
        return
    val = max(mn, min(mx, val))
    # snap to step
    if step:
        val = round((val - mn) / step) * step + mn
    # int-ify if step is integral
    if step == int(step) and mn == int(mn):
        val = int(round(val))
    _set_value(setting, val)


def _edit_labelenum(setting):
    values = (setting.get('values') or '').split('|')
    current = _get_value(setting) or setting.get('default', '')
    preselect = -1
    if current.isdigit() and int(current) < len(values):
        preselect = int(current)
    elif current in values:
        preselect = values.index(current)
    idx = xbmcgui.Dialog().select(setting.get('label', 'Select'), values, preselect=preselect)
    if idx < 0:
        return
    # Save as the label (more portable for SALTS); fall back to index if value
    # looks numeric in defaults.
    if setting.get('default', '').isdigit():
        _set_value(setting, idx)
    else:
        _set_value(setting, values[idx])


def _edit_text(setting):
    current = _get_value(setting)
    is_secret = setting.get('option') == 'hidden' or 'password' in (setting.get('id') or '').lower()
    if is_secret:
        new = xbmcgui.Dialog().input(setting.get('label', 'Value'),
                                     current,
                                     type=xbmcgui.INPUT_ALPHANUM,
                                     option=xbmcgui.ALPHANUM_HIDE_INPUT)
    else:
        new = xbmcgui.Dialog().input(setting.get('label', 'Value'),
                                     current,
                                     type=xbmcgui.INPUT_ALPHANUM)
    if new is None:
        return
    _set_value(setting, new)


def _run_action(setting):
    action = setting.get('action') or ''
    if not action:
        return
    xbmc.executebuiltin(action)


def _edit_setting(setting):
    stype = setting.get('type', '')
    if stype == 'bool':
        _edit_bool(setting)
    elif stype == 'slider':
        _edit_slider(setting)
    elif stype == 'labelenum':
        _edit_labelenum(setting)
    elif stype == 'text':
        _edit_text(setting)
    elif stype == 'action':
        _run_action(setting)


# ---------- the window --------------------------------------------------


class SaltsSettingsWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super(SaltsSettingsWindow, self).__init__(*args, **kwargs)
        self.categories = _parse_settings_xml()
        self.active_cat = 0
        # Maps row index in the settings list -> index in the category's
        # raw `settings` array (so headers/hidden rows are accounted for).
        self.row_to_setting_index = []

    # -- lifecycle --

    def onInit(self):
        try:
            self.getControl(CTRL_SUBTITLE).setLabel(
                'Settings  |  v%s' % ADDON_VERSION
            )
        except Exception:
            pass
        self._populate_categories()
        self._populate_settings()
        self.setFocusId(CTRL_CATEGORY_LIST)

    # -- categories --

    def _populate_categories(self):
        items = []
        for cat in self.categories:
            li = xbmcgui.ListItem(cat['label'])
            items.append(li)
        ctrl = self.getControl(CTRL_CATEGORY_LIST)
        ctrl.reset()
        ctrl.addItems(items)
        ctrl.selectItem(self.active_cat)

    # -- settings list --

    def _populate_settings(self):
        cat = self.categories[self.active_cat]
        settings = cat['settings']

        try:
            self.getControl(CTRL_PANEL_TITLE).setLabel(cat['label'].upper())
        except Exception:
            pass

        items = []
        self.row_to_setting_index = []

        for idx, s in enumerate(settings):
            stype = s.get('type', '')
            # Hidden persistence-only settings (tokens, etc.)
            if s.get('visible') == 'false':
                continue
            # Section headers - format the look directly into the label
            # text via BBCode, so we don't rely on per-row visible
            # conditions inside the skin (which are unreliable across
            # Kodi builds).
            if stype == 'lsep':
                label = s.get('label', '')
                pretty = '[B][COLOR FFFFD700]--  %s  --[/COLOR][/B]' % label.upper()
                li = xbmcgui.ListItem(pretty)
                li.setLabel2('')
                li.setProperty('is_section', '1')
                items.append(li)
                self.row_to_setting_index.append(-1)
                continue

            label = s.get('label', s.get('id', ''))
            enabled = _is_enabled(settings, idx)
            value = _format_value(s)
            if not enabled:
                label = '[COLOR FF555c66]%s[/COLOR]' % label
                value = '[COLOR FF555c66]%s[/COLOR]' % re.sub(r'\[/?COLOR[^\]]*\]', '', value)
            li = xbmcgui.ListItem(label)
            li.setLabel2(value)
            # Properties so the skin can draw the right widget per row
            if stype == 'bool':
                li.setProperty('is_bool', '1')
                raw = _get_value(s)
                if raw not in ('true', 'false'):
                    raw = (s.get('default') or 'false').lower()
                if raw == 'true':
                    li.setProperty('bool_on', '1')
            elif stype == 'text':
                li.setProperty('is_text', '1')
                if not _get_value(s):
                    li.setProperty('text_empty', '1')
            elif stype == 'action':
                li.setProperty('is_action', '1')
            elif stype == 'slider':
                li.setProperty('is_slider', '1')
            elif stype == 'labelenum':
                li.setProperty('is_enum', '1')
            if not enabled:
                li.setProperty('is_disabled', '1')
            items.append(li)
            self.row_to_setting_index.append(idx)

        ctrl = self.getControl(CTRL_SETTINGS_LIST)
        ctrl.reset()
        ctrl.addItems(items)
        # Try to focus first non-header row
        for row, mapped in enumerate(self.row_to_setting_index):
            if mapped >= 0:
                ctrl.selectItem(row)
                break
        self._update_description()

    def _refresh_settings_keep_position(self):
        ctrl = self.getControl(CTRL_SETTINGS_LIST)
        pos = ctrl.getSelectedPosition()
        self._populate_settings()
        try:
            ctrl.selectItem(pos)
        except Exception:
            pass

    def _update_description(self):
        row = self.getControl(CTRL_SETTINGS_LIST).getSelectedPosition()
        text = 'Select a setting to edit it.'
        if 0 <= row < len(self.row_to_setting_index):
            idx = self.row_to_setting_index[row]
            if idx >= 0:
                s = self.categories[self.active_cat]['settings'][idx]
                stype = s.get('type', '')
                hint = {
                    'bool':      'Toggle on/off',
                    'slider':    'Numeric value within the allowed range',
                    'labelenum': 'Choose one of the listed values',
                    'text':      'Enter a text value',
                    'action':    'Run this action',
                }.get(stype, '')
                desc = s.get('label', '')
                if hint:
                    desc = '%s  |  %s' % (desc, hint)
                text = desc
            else:
                # section row
                s = None
                # find the lsep at that position
                cat_settings = self.categories[self.active_cat]['settings']
                seen = 0
                for i, item in enumerate(cat_settings):
                    if item.get('visible') == 'false':
                        continue
                    if seen == row:
                        s = item
                        break
                    seen += 1
                if s is not None:
                    text = '-- %s --' % s.get('label', '')
        try:
            self.getControl(CTRL_DESC_BOX).setText(text)
        except Exception:
            pass

    # -- input handlers --

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()
            return
        # Update description as the user moves through the right panel
        if self.getFocusId() == CTRL_SETTINGS_LIST and aid in (
            ACTION_MOVE_UP, ACTION_MOVE_DOWN, ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT
        ):
            self._update_description()
        # If user is in the categories list, refresh right panel as selection moves
        if self.getFocusId() == CTRL_CATEGORY_LIST and aid in (ACTION_MOVE_UP, ACTION_MOVE_DOWN):
            new_cat = self.getControl(CTRL_CATEGORY_LIST).getSelectedPosition()
            if 0 <= new_cat < len(self.categories) and new_cat != self.active_cat:
                self.active_cat = new_cat
                self._populate_settings()

    def onClick(self, controlId):
        if controlId == CTRL_CATEGORY_LIST:
            new_cat = self.getControl(CTRL_CATEGORY_LIST).getSelectedPosition()
            if 0 <= new_cat < len(self.categories):
                self.active_cat = new_cat
                self._populate_settings()
            self.setFocusId(CTRL_SETTINGS_LIST)
            return
        if controlId == CTRL_SETTINGS_LIST:
            row = self.getControl(CTRL_SETTINGS_LIST).getSelectedPosition()
            if not (0 <= row < len(self.row_to_setting_index)):
                return
            idx = self.row_to_setting_index[row]
            if idx < 0:
                return  # section header, ignore
            settings = self.categories[self.active_cat]['settings']
            s = settings[idx]
            if not _is_enabled(settings, idx):
                xbmcgui.Dialog().notification(
                    ADDON_NAME,
                    'This option is disabled by a parent setting.',
                    ADDON.getAddonInfo('icon'), 2500
                )
                return
            _edit_setting(s)
            self._refresh_settings_keep_position()
            return
        if controlId == CTRL_CLOSE_BTN:
            self.close()
            return
        if controlId == CTRL_RESET_BTN:
            self._reset_current_category()
            return
        if controlId == CTRL_SEARCH_BTN:
            self._search_settings()
            return

    # -- extras --

    def _reset_current_category(self):
        cat = self.categories[self.active_cat]
        if not xbmcgui.Dialog().yesno(
            ADDON_NAME,
            'Reset all settings in "%s" to defaults?' % cat['label']
        ):
            return
        for s in cat['settings']:
            if s.get('type') in ('lsep', 'action'):
                continue
            if 'default' in s and s.get('id'):
                _set_value(s, s.get('default'))
        self._populate_settings()
        xbmcgui.Dialog().notification(
            ADDON_NAME, 'Category reset to defaults.',
            ADDON.getAddonInfo('icon'), 2000
        )

    def _search_settings(self):
        q = xbmcgui.Dialog().input('Search settings', type=xbmcgui.INPUT_ALPHANUM)
        if not q:
            return
        q = q.lower()
        hits = []
        for ci, cat in enumerate(self.categories):
            for s in cat['settings']:
                if s.get('type') == 'lsep':
                    continue
                if s.get('visible') == 'false':
                    continue
                label = s.get('label', '')
                if q in label.lower() or q in (s.get('id') or '').lower():
                    hits.append((ci, label, s.get('id', '')))
        if not hits:
            xbmcgui.Dialog().notification(
                ADDON_NAME, 'No matching settings.',
                ADDON.getAddonInfo('icon'), 2000
            )
            return
        display = [
            '[%s]  %s' % (self.categories[ci]['label'], label)
            for ci, label, _ in hits
        ]
        idx = xbmcgui.Dialog().select('Search results', display)
        if idx < 0:
            return
        target_cat, _, target_id = hits[idx]
        self.active_cat = target_cat
        self._populate_categories()
        self._populate_settings()
        # focus the matching setting
        for row, sidx in enumerate(self.row_to_setting_index):
            if sidx < 0:
                continue
            if self.categories[target_cat]['settings'][sidx].get('id') == target_id:
                try:
                    self.getControl(CTRL_SETTINGS_LIST).selectItem(row)
                except Exception:
                    pass
                break
        self.setFocusId(CTRL_SETTINGS_LIST)
        self._update_description()


def open_settings():
    """Entrypoint called from default.py (mode=salts_settings)."""
    w = SaltsSettingsWindow(
        'salts_settings.xml',
        ADDON_PATH,
        'Default',
        '720p'
    )
    w.doModal()
    del w
