# -*- coding: utf-8 -*-
"""Common helpers for Vidscr addon."""
import sys
import os
import json
from urllib.parse import urlencode, parse_qsl, quote_plus

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

if not xbmcvfs.exists(PROFILE_PATH):
    xbmcvfs.mkdirs(PROFILE_PATH)

HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1
BASE_URL = sys.argv[0] if sys.argv else 'plugin://plugin.video.vidscr/'

ICON = os.path.join(ADDON_PATH, 'icon.png')
FANART = os.path.join(ADDON_PATH, 'fanart.jpg')


def get_setting(key, default=''):
    val = ADDON.getSetting(key)
    return val if val else default


def get_setting_bool(key, default=False):
    val = ADDON.getSetting(key)
    if not val:
        return default
    return val.lower() in ('true', '1', 'yes')


def get_setting_int(key, default=0):
    try:
        return int(ADDON.getSetting(key))
    except (ValueError, TypeError):
        return default


DEBUG_LOG_PATH = os.path.join(PROFILE_PATH, 'vidscr_debug.log')
_MAX_LOG_BYTES = 256 * 1024  # 256 KB rolling


def log(msg, level=xbmc.LOGINFO):
    try:
        xbmc.log('[Vidscr] %s' % msg, level)
    except Exception:
        pass
    # Also mirror to an addon-local debug log when debug_log is enabled,
    # so the user can view it directly from the addon settings without
    # hunting through kodi.log.
    try:
        if get_setting_bool('debug_log'):
            import datetime
            ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            line = '[%s] %s\n' % (ts, msg)
            # Rotate if too big
            if os.path.exists(DEBUG_LOG_PATH) and os.path.getsize(DEBUG_LOG_PATH) > _MAX_LOG_BYTES:
                try:
                    with open(DEBUG_LOG_PATH, 'rb') as f:
                        f.seek(-_MAX_LOG_BYTES // 2, 2)
                        tail = f.read()
                    with open(DEBUG_LOG_PATH, 'wb') as f:
                        f.write(tail)
                except Exception:
                    pass
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(line)
    except Exception:
        pass


def clear_debug_log():
    try:
        if os.path.exists(DEBUG_LOG_PATH):
            os.remove(DEBUG_LOG_PATH)
    except Exception:
        pass


def read_debug_log():
    try:
        if not os.path.exists(DEBUG_LOG_PATH):
            return ''
        with open(DEBUG_LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        return 'Error reading log: %s' % e


def build_url(**kwargs):
    return '%s?%s' % (BASE_URL, urlencode({k: v for k, v in kwargs.items() if v is not None}))


def parse_params():
    qs = sys.argv[2][1:] if len(sys.argv) > 2 else ''
    return dict(parse_qsl(qs))


def notify(message, heading=None, icon=None, time=4000):
    xbmcgui.Dialog().notification(heading or ADDON_NAME, message, icon or ICON, time)


def keyboard(heading='Search'):
    kb = xbmc.Keyboard('', heading)
    kb.doModal()
    if kb.isConfirmed():
        return kb.getText()
    return ''


def end_directory(content='videos', sort_methods=None, cache_to_disc=True):
    if content:
        xbmcplugin.setContent(HANDLE, content)
    if sort_methods:
        for sm in sort_methods:
            xbmcplugin.addSortMethod(HANDLE, sm)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=cache_to_disc)


def add_dir(label, params, info=None, art=None, is_folder=True, context=None, plot=None):
    li = xbmcgui.ListItem(label=label)
    item_art = {'icon': ICON, 'thumb': ICON, 'fanart': FANART}
    if art:
        item_art.update({k: v for k, v in art.items() if v})
    li.setArt(item_art)
    info_dict = {'title': label}
    if plot:
        info_dict['plot'] = plot
    if info:
        info_dict.update(info)
    try:
        li.setInfo('video', info_dict)
    except Exception:
        pass
    if not is_folder:
        li.setProperty('IsPlayable', 'true')
    if context:
        li.addContextMenuItems(context, replaceItems=False)
    url = build_url(**params)
    xbmcplugin.addDirectoryItem(HANDLE, url, li, is_folder)


def cache_path(name):
    return os.path.join(PROFILE_PATH, name)
