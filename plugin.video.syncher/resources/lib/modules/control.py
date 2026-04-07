# -*- coding: utf-8 -*-
"""Syncher - control module: addon helpers, settings, constants"""

import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON = xbmcaddon.Addon
ADDON_ID = 'plugin.video.syncher'

def addon():
    return ADDON(ADDON_ID)

def addonInfo(key):
    return addon().getAddonInfo(key)

def setting(key):
    return addon().getSetting(key)

def set_setting(key, val):
    return addon().setSetting(key, str(val))

def lang(code):
    return addon().getLocalizedString(code)

def addonPath():
    return xbmcvfs.translatePath(addonInfo('path'))

def addonProfile():
    return xbmcvfs.translatePath(addonInfo('profile'))

def addonIcon():
    return os.path.join(addonPath(), 'icon.png')

def addonFanart():
    return os.path.join(addonPath(), 'fanart.jpg')

def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[Syncher] %s' % str(msg), level)

def infoDialog(msg, heading='Syncher', icon='', time=3000):
    if icon == '':
        icon = addonIcon()
    xbmcgui.Dialog().notification(heading, msg, icon, time)

def okDialog(msg, heading='Syncher'):
    return xbmcgui.Dialog().ok(heading, msg)

def yesnoDialog(msg, heading='Syncher', nolabel='', yeslabel=''):
    return xbmcgui.Dialog().yesno(heading, msg, nolabel=nolabel, yeslabel=yeslabel)

def progressDialog():
    return xbmcgui.DialogProgress()

def keyboard(default='', heading=''):
    k = xbmc.Keyboard(default, heading)
    k.doModal()
    if k.isConfirmed():
        return k.getText()
    return None

def openSettings(query='0.0'):
    addon().openSettings()

# API Keys
TRAKT_KEY = 'd32b1053e6d305a8cd2085a2f2356c4f6dfaa4d9d327c1c6fa7a60d7ca6beca9'
TRAKT_SECRET = 'd93ca1563127f22c89f3b703cb94fb7114b493381923111c2ce1c3544b7019eb'
TMDB_KEY = 'f15af109700aab95d564acda15bdcd97'

TRAKT_BASE = 'https://api.trakt.tv'
TMDB_BASE = 'https://api.themoviedb.org/3'
TMDB_POSTER = 'https://image.tmdb.org/t/p/w500'
TMDB_FANART = 'https://image.tmdb.org/t/p/w1280'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
