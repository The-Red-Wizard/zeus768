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
from resources.lib import tmdb, trakt_auth, trakt_api, player, debrid, discovery, feed

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1
KOFI_URL = 'https://ko-fi.com/zeus768'
FANART = os.path.join(ADDON.getAddonInfo('path'), 'fanart.jpg')
ICON = os.path.join(ADDON.getAddonInfo('path'), 'icon.png')

# TMDB category icons (popular movie posters as visual icons for menus)
TMDB_IMG = 'https://image.tmdb.org/t/p/w500'
CAT_ICONS = {
    'movies': TMDB_IMG + '/qJ2tW6WMUDux911BTUgMEmb9Jmg.jpg',       # Movie reel style
    'tv': TMDB_IMG + '/uDgy6hyPd82kOHh6I95FLtLnj6p.jpg',            # TV style
    'continue': TMDB_IMG + '/7WsyChQLEftFiDhRguUl2HnBurj.jpg',      # Continue
    'feed': TMDB_IMG + '/sv1xJUazXeYqALzczSZ3O6nkH75.jpg',          # Discovery
    'vibes': TMDB_IMG + '/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg',         # AI vibes
    'trakt': TMDB_IMG + '/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg',         # My Trakt
    'stats': TMDB_IMG + '/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg',        # Stats
    'account': TMDB_IMG + '/8UlWHLMpgZm9bx6QYh0NFoq67TZ.jpg',      # Account
    'donate': TMDB_IMG + '/nBNZadXqJSdt05SHLqgT0HuC5Gm.jpg',       # Donate
    'settings': TMDB_IMG + '/6FfCtHuMuyMmCTfORGMjqWo5EDi.jpg',      # Settings
    'trending': TMDB_IMG + '/qJ2tW6WMUDux911BTUgMEmb9Jmg.jpg',
    'popular': TMDB_IMG + '/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg',
    'watched': TMDB_IMG + '/sv1xJUazXeYqALzczSZ3O6nkH75.jpg',
    'boxoffice': TMDB_IMG + '/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg',
    'anticipated': TMDB_IMG + '/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg',
    'recommended': TMDB_IMG + '/uDgy6hyPd82kOHh6I95FLtLnj6p.jpg',
    'genres': TMDB_IMG + '/6FfCtHuMuyMmCTfORGMjqWo5EDi.jpg',
    'calendar': TMDB_IMG + '/nBNZadXqJSdt05SHLqgT0HuC5Gm.jpg',
    'watchlist': TMDB_IMG + '/7WsyChQLEftFiDhRguUl2HnBurj.jpg',
    'collection': TMDB_IMG + '/8UlWHLMpgZm9bx6QYh0NFoq67TZ.jpg',
    'history': TMDB_IMG + '/sv1xJUazXeYqALzczSZ3O6nkH75.jpg',
    'lists': TMDB_IMG + '/qJ2tW6WMUDux911BTUgMEmb9Jmg.jpg',
    'friends': TMDB_IMG + '/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg',
}


def build_url(query):
    return sys.argv[0] + '?' + urlencode(query)


def _menu_item(label, action, icon_key='', is_folder=True, extra_params=None):
    """Create a menu item with addon fanart and TMDB/Trakt icon."""
    q = {'action': action}
    if extra_params:
        q.update(extra_params)
    url = build_url(q)
    li = xbmcgui.ListItem(label=label)
    icon = CAT_ICONS.get(icon_key, ICON)
    li.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'fanart': FANART})
    return url, li, is_folder


# ── Main Menu ─────────────────────────────────────────────────────────────

def main_menu():
    tmdb.prompt_for_api_key()
    items = [
        _menu_item('Movies', 'movie_menu', 'movies'),
        _menu_item('TV Shows', 'tv_menu', 'tv'),
        _menu_item('Continue Watching', 'continue_watching', 'continue'),
        _menu_item('Discovery Feed', 'feed_menu', 'feed'),
        _menu_item('AI Vibes', 'discovery_menu', 'vibes'),
        _menu_item('My Trakt', 'my_trakt', 'trakt'),
        _menu_item('My Stats', 'user_stats', 'stats', is_folder=False),
        _menu_item('Account Status', 'account_status', 'account', is_folder=False),
        _menu_item('Buy Me a Beer', 'donate', 'donate', is_folder=False),
        _menu_item('Settings', 'open_settings', 'settings', is_folder=False),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── Movie Menu ────────────────────────────────────────────────────────────

def movie_menu():
    items = [
        _menu_item('Trending', 'trakt_list', 'trending', extra_params={'path': 'movies/trending', 'media_type': 'movie'}),
        _menu_item('Popular', 'trakt_list', 'popular', extra_params={'path': 'movies/popular', 'media_type': 'movie'}),
        _menu_item('Most Watched (Week)', 'trakt_list', 'watched', extra_params={'path': 'movies/watched/weekly', 'media_type': 'movie'}),
        _menu_item('Most Watched (All Time)', 'trakt_list', 'watched', extra_params={'path': 'movies/watched/all', 'media_type': 'movie'}),
        _menu_item('Box Office', 'trakt_list', 'boxoffice', extra_params={'path': 'movies/boxoffice', 'media_type': 'movie'}),
        _menu_item('Anticipated', 'anticipated', 'anticipated', extra_params={'media_type': 'movie'}),
        _menu_item('Recommended For You', 'recommendations', 'recommended', extra_params={'media_type': 'movie'}),
        _menu_item('Genres', 'list_genres', 'genres', extra_params={'path': 'movie'}),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── TV Menu ───────────────────────────────────────────────────────────────

def tv_menu():
    items = [
        _menu_item('Trending Shows', 'trakt_list', 'trending', extra_params={'path': 'shows/trending', 'media_type': 'show'}),
        _menu_item('Popular Shows', 'trakt_list', 'popular', extra_params={'path': 'shows/popular', 'media_type': 'show'}),
        _menu_item('Most Watched (Week)', 'trakt_list', 'watched', extra_params={'path': 'shows/watched/weekly', 'media_type': 'show'}),
        _menu_item('Most Watched (All Time)', 'trakt_list', 'watched', extra_params={'path': 'shows/watched/all', 'media_type': 'show'}),
        _menu_item('Anticipated', 'anticipated', 'anticipated', extra_params={'media_type': 'show'}),
        _menu_item('Recommended For You', 'recommendations', 'recommended', extra_params={'media_type': 'show'}),
        _menu_item('My Calendar', 'calendar', 'calendar', extra_params={'media_type': 'show'}),
        _menu_item('Genres', 'list_genres', 'genres', extra_params={'path': 'tv'}),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── My Trakt Menu ────────────────────────────────────────────────────────

def my_trakt():
    if ADDON.getSetting('trakt_auth_done') != 'true':
        xbmcgui.Dialog().notification('Trakt', 'Please authorize Trakt first', xbmcgui.NOTIFICATION_WARNING)
        return
    items = [
        _menu_item('Movie Watchlist', 'trakt_list', 'watchlist', extra_params={'path': 'sync/watchlist/movies', 'media_type': 'movie'}),
        _menu_item('Show Watchlist', 'trakt_list', 'watchlist', extra_params={'path': 'sync/watchlist/shows', 'media_type': 'show'}),
        _menu_item('Movie Collection', 'trakt_list', 'collection', extra_params={'path': 'sync/collection/movies', 'media_type': 'movie'}),
        _menu_item('Show Collection', 'trakt_list', 'collection', extra_params={'path': 'sync/collection/shows', 'media_type': 'show'}),
        _menu_item('Recently Watched Movies', 'history', 'history', extra_params={'media_type': 'movie'}),
        _menu_item('Recently Watched Episodes', 'history', 'history', extra_params={'media_type': 'show'}),
        _menu_item('My Calendar', 'calendar', 'calendar', extra_params={'media_type': 'show'}),
        _menu_item('My Custom Lists', 'my_lists', 'lists'),
        _menu_item('Popular Lists', 'popular_lists', 'lists'),
        _menu_item('Friends', 'friends', 'friends'),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
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

    # Discovery Feed (Trailers)
    elif action == 'feed_menu':
        feed.feed_menu()
    elif action == 'feed_trending':
        feed.feed_trending()
    elif action == 'feed_trending_tv':
        feed.feed_trending_tv()
    elif action == 'feed_now_playing':
        feed.feed_now_playing()
    elif action == 'feed_upcoming':
        feed.feed_upcoming()
    elif action == 'feed_shuffle':
        feed.feed_shuffle()
    elif action == 'feed_marathon':
        feed.feed_marathon()
    elif action == 'play_trailer':
        feed.play_trailer(params.get('yt_key', ''), params.get('title', ''))

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
