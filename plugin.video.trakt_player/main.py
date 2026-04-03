# -*- coding: utf-8 -*-
"""Trakt Player v2.0.0 - Superpowered Trakt addon. Click-and-Play, Scrobble, Up Next, Recommendations, Calendar, and more."""
import sys
import ssl
import json
import os
import tempfile
import urllib.request
from urllib.parse import parse_qsl, urlencode, quote_plus
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
from resources.lib import tmdb, trakt_auth, trakt_api, player, debrid, discovery

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
KOFI_URL = 'https://ko-fi.com/zeus768'


def build_url(query):
    return sys.argv[0] + '?' + urlencode(query)


# ── Main Menu ─────────────────────────────────────────────────────────────

def main_menu():
    tmdb.prompt_for_api_key()
    items = [
        ('Movies', 'movie_menu', 'DefaultMovies.png'),
        ('TV Shows', 'tv_menu', 'DefaultTVShows.png'),
        ('Continue Watching', 'continue_watching', 'DefaultInProgressShows.png'),
        ('Discovery (AI Vibes)', 'discovery_menu', 'DefaultMusicSearch.png'),
        ('My Trakt', 'my_trakt', 'DefaultAddonProgram.png'),
        ('My Stats', 'user_stats', 'DefaultIconInfo.png'),
        ('Account Status', 'account_status', 'DefaultIconInfo.png'),
        ('Buy Me a Beer', 'donate', 'DefaultAddonService.png'),
        ('Settings', 'open_settings', 'DefaultAddonService.png'),
    ]
    for label, action, icon in items:
        url = build_url({'action': action})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': icon})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=(action not in ('donate', 'account_status', 'open_settings', 'user_stats')))
    xbmcplugin.endOfDirectory(HANDLE)


# ── Movie Menu ────────────────────────────────────────────────────────────

def movie_menu():
    items = [
        ('Trending', 'trakt_list', 'movies/trending'),
        ('Popular', 'trakt_list', 'movies/popular'),
        ('Most Watched (Week)', 'trakt_list', 'movies/watched/weekly'),
        ('Most Watched (All Time)', 'trakt_list', 'movies/watched/all'),
        ('Box Office', 'trakt_list', 'movies/boxoffice'),
        ('Anticipated', 'anticipated', ''),
        ('Recommended For You', 'recommendations', ''),
        ('Genres', 'list_genres', 'movie'),
    ]
    for label, action, path in items:
        q = {'action': action, 'media_type': 'movie'}
        if path:
            q['path'] = path
        url = build_url(q)
        xbmcplugin.addDirectoryItem(HANDLE, url, xbmcgui.ListItem(label=label), isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)


# ── TV Menu ───────────────────────────────────────────────────────────────

def tv_menu():
    items = [
        ('Trending Shows', 'trakt_list', 'shows/trending'),
        ('Popular Shows', 'trakt_list', 'shows/popular'),
        ('Most Watched (Week)', 'trakt_list', 'shows/watched/weekly'),
        ('Most Watched (All Time)', 'trakt_list', 'shows/watched/all'),
        ('Anticipated', 'anticipated', ''),
        ('Recommended For You', 'recommendations', ''),
        ('My Calendar', 'calendar', ''),
        ('Genres', 'list_genres', 'tv'),
    ]
    for label, action, path in items:
        q = {'action': action, 'media_type': 'show'}
        if path:
            q['path'] = path
        url = build_url(q)
        xbmcplugin.addDirectoryItem(HANDLE, url, xbmcgui.ListItem(label=label), isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)


# ── My Trakt Menu ────────────────────────────────────────────────────────

def my_trakt():
    if ADDON.getSetting('trakt_auth_done') != 'true':
        xbmcgui.Dialog().notification('Trakt', 'Please authorize Trakt first', xbmcgui.NOTIFICATION_WARNING)
        return
    items = [
        ('Movie Watchlist', 'trakt_list', 'sync/watchlist/movies', 'movie'),
        ('Show Watchlist', 'trakt_list', 'sync/watchlist/shows', 'show'),
        ('Movie Collection', 'trakt_list', 'sync/collection/movies', 'movie'),
        ('Show Collection', 'trakt_list', 'sync/collection/shows', 'show'),
        ('Recently Watched Movies', 'history', '', 'movie'),
        ('Recently Watched Episodes', 'history', '', 'show'),
        ('My Calendar', 'calendar', '', 'show'),
        ('My Custom Lists', 'my_lists', '', ''),
        ('Popular Lists', 'popular_lists', '', ''),
        ('Friends', 'friends', '', ''),
    ]
    for label, action, path, media in items:
        q = {'action': action, 'media_type': media}
        if path:
            q['path'] = path
        url = build_url(q)
        xbmcplugin.addDirectoryItem(HANDLE, url, xbmcgui.ListItem(label=label), isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)


# ── Donation ──────────────────────────────────────────────────────────────

def show_donation():
    """Show donation dialog with QR code."""
    # Try to download QR code
    qr_shown = False
    try:
        qr_api = 'https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=%s' % quote_plus(KOFI_URL)
        qr_path = os.path.join(tempfile.gettempdir(), 'trakt_player_qr.png')
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(qr_api, headers={'User-Agent': 'TraktPlayer/2.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            with open(qr_path, 'wb') as f:
                f.write(resp.read())
        if os.path.exists(qr_path) and os.path.getsize(qr_path) > 100:
            xbmcgui.Dialog().ok(
                'Buy Me a Beer',
                'Thanks for using Trakt Player!\n\n'
                'Scan the QR code or visit:\n'
                '[COLOR skyblue]%s[/COLOR]\n\n'
                'Your support keeps this addon alive!' % KOFI_URL)
            xbmc.executebuiltin('ShowPicture(%s)' % qr_path)
            qr_shown = True
    except Exception as e:
        xbmc.log('QR code download failed: %s' % str(e), xbmc.LOGWARNING)

    if not qr_shown:
        xbmcgui.Dialog().ok(
            'Buy Me a Beer',
            'Thanks for using Trakt Player!\n\n'
            'Visit: [COLOR skyblue]%s[/COLOR]\n\n'
            'Your support keeps this addon alive!' % KOFI_URL)


# ── Account Status ────────────────────────────────────────────────────────

def show_account_status():
    """Show debrid account status with renewal info."""
    progress = xbmcgui.DialogProgress()
    progress.create('Account Status', 'Checking debrid accounts...')

    accounts = debrid.get_all_account_info()
    progress.close()

    lines = []
    lines.append('[B][COLOR skyblue]--- Debrid Account Status ---[/COLOR][/B]\n')

    for acct in accounts:
        name = acct.get('name', 'Unknown')
        if acct.get('configured') is False:
            lines.append('[COLOR gray]%s: Not configured[/COLOR]\n' % name)
            continue
        if acct.get('error'):
            lines.append('[COLOR red]%s: Error - %s[/COLOR]\n' % (name, acct['error']))
            continue

        username = acct.get('username', '')
        acct_type = acct.get('type', 'unknown')
        premium = acct.get('premium', False)
        expires = acct.get('expires', 'Unknown')
        days_left = acct.get('days_left', 0)
        auto_renew = acct.get('auto_renew', 'Unknown')

        if premium:
            if days_left <= 7:
                color = 'red'
                status = 'EXPIRING SOON'
            elif days_left <= 30:
                color = 'yellow'
                status = 'Active'
            else:
                color = 'lime'
                status = 'Active'
        else:
            color = 'red'
            status = 'FREE/Expired'

        line = '[COLOR %s][B]%s[/B][/COLOR]' % (color, name)
        line += '\n  User: %s' % username if username else ''
        line += '\n  Status: [COLOR %s]%s (%s)[/COLOR]' % (color, status, acct_type)
        line += '\n  Expires: %s' % expires
        if premium and days_left > 0:
            line += ' ([B]%d days left[/B])' % days_left
        line += '\n  Auto-Renew: %s' % auto_renew
        if acct.get('points'):
            line += '\n  Fidelity Points: %d' % acct['points']
        line += '\n'
        lines.append(line)

    # Trakt status
    lines.append('\n[B][COLOR skyblue]--- Trakt Account ---[/COLOR][/B]\n')
    if trakt_auth.is_authorized():
        lines.append('[COLOR lime]Trakt: Authorized[/COLOR]')
    else:
        lines.append('[COLOR red]Trakt: Not authorized[/COLOR]')

    xbmcgui.Dialog().textviewer('Account Status', '\n'.join(lines))


# ── Router ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get('action')

    if not action:
        main_menu()

    # Navigation
    elif action == 'movie_menu':
        movie_menu()
    elif action == 'tv_menu':
        tv_menu()
    elif action == 'my_trakt':
        my_trakt()
    elif action == 'open_settings':
        ADDON.openSettings()
    elif action == 'donate':
        show_donation()
    elif action == 'account_status':
        show_account_status()

    # Trakt Browse
    elif action == 'list_genres':
        tmdb.get_genres(params.get('path'))
    elif action == 'trakt_list':
        trakt_api.get_list(params.get('path'), params.get('media_type', 'movie'))
    elif action == 'show_seasons':
        trakt_api.show_seasons(params.get('tmdb_id'), params.get('title'))
    elif action == 'show_episodes':
        trakt_api.show_episodes(params.get('tmdb_id'), params.get('season'), params.get('title'))

    # Trakt Superpower Features
    elif action == 'recommendations':
        trakt_api.get_recommendations(params.get('media_type', 'movie'))
    elif action == 'calendar':
        trakt_api.get_calendar()
    elif action == 'history':
        trakt_api.get_history(params.get('media_type', 'movie'))
    elif action == 'anticipated':
        trakt_api.get_anticipated(params.get('media_type', 'movie'))
    elif action == 'popular_lists':
        trakt_api.get_popular_lists()
    elif action == 'list_items':
        trakt_api.get_list_items(params.get('user', ''), params.get('list_slug', ''))
    elif action == 'related':
        trakt_api.get_related(params.get('media_type', 'movie'), params.get('trakt_id', ''))
    elif action == 'continue_watching':
        trakt_api.get_playback_progress()
    elif action == 'rate':
        trakt_api.rate_item(params.get('media_type', 'movie'), params.get('trakt_id', ''))
    elif action == 'add_watchlist':
        trakt_api.add_to_watchlist(params.get('media_type', 'movie'), params.get('imdb_id', ''))

    # Friends, Stats, Custom Lists
    elif action == 'friends':
        trakt_api.get_friends()
    elif action == 'friend_activity':
        trakt_api.get_friend_activity(params.get('user', ''))
    elif action == 'user_stats':
        trakt_api.show_user_stats()
    elif action == 'my_lists':
        trakt_api.get_my_lists()
    elif action == 'create_list':
        trakt_api.create_list()
    elif action == 'delete_list':
        trakt_api.delete_list(params.get('list_slug', ''))
    elif action == 'add_to_list':
        trakt_api.add_to_list(params.get('media_type', 'movie'), params.get('imdb_id', ''))

    # Discovery (AI Vibes)
    elif action == 'discovery_menu':
        discovery.mood_presets()
    elif action == 'vibe_custom':
        discovery.vibe_discovery()
    elif action == 'vibe_play':
        discovery.vibe_play(params.get('vibe', ''))

    # Click-and-Play
    elif action == 'play':
        player.play(params.get('title', ''), params.get('year', ''), params.get('imdb_id', ''))
    elif action == 'play_episode':
        player.play_episode(
            params.get('title', ''),
            params.get('season', '0'),
            params.get('episode', '0'),
            params.get('imdb_id', ''),
            params.get('tmdb_id', ''))

    # Auth - Trakt
    elif action == 'auth_trakt':
        trakt_auth.authorize()
    elif action == 'revoke_trakt':
        trakt_auth.revoke()

    # Auth - Debrid
    elif action == 'auth_rd':
        debrid.RealDebrid().authorize()
    elif action == 'revoke_rd':
        debrid.RealDebrid().revoke()
    elif action == 'auth_ad':
        debrid.AllDebrid().authorize()
    elif action == 'revoke_ad':
        debrid.AllDebrid().revoke()
    elif action == 'auth_pm':
        debrid.Premiumize().authorize()
    elif action == 'revoke_pm':
        debrid.Premiumize().revoke()
    elif action == 'auth_tb':
        debrid.TorBox().authorize()
    elif action == 'revoke_tb':
        debrid.TorBox().revoke()
