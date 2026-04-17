# -*- coding: utf-8 -*-
"""Genesis v1.5.0 - Click-and-Play Kodi addon with Cloud, Local Scanning, Free Links, Plex & Emby.
Based on trakt_player by zeus768."""
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
import xbmcvfs
from resources.lib import tmdb, trakt_auth, trakt_api, debrid, player, live_channels, xray, anime, anime_scrapers, icon_helper
from resources.lib import cloud_browser, local_scanner, free_links_scraper
from resources.lib import plex_server, emby_server, tmdb_artwork

def get_addon():
    return xbmcaddon.Addon()

ADDON_ID = 'plugin.video.genesis'
ADDON_PATH = xbmcvfs.translatePath(f'special://home/addons/{ADDON_ID}/')
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1
KOFI_URL = 'https://ko-fi.com/zeus768'


def get_addon_icon():
    icon_path = os.path.join(ADDON_PATH, 'icon.png')
    if os.path.exists(icon_path):
        return icon_path
    return 'DefaultAddonVideo.png'


def get_addon_fanart():
    fanart_path = os.path.join(ADDON_PATH, 'fanart.jpg')
    if os.path.exists(fanart_path):
        return fanart_path
    return ''


def build_url(query):
    return sys.argv[0] + '?' + urlencode(query)


def _menu_item(label, action, is_folder=True, extra_params=None):
    """Create a menu item with themed icon from Genesis Skins."""
    q = {'action': action}
    if extra_params:
        q.update(extra_params)
    url = build_url(q)
    li = xbmcgui.ListItem(label=label)
    
    # Try to get themed icon from Genesis Skins
    default_icon = get_addon_icon()
    themed_icon = icon_helper.get_icon_for_label(label, default_icon)
    
    icon = themed_icon if themed_icon else default_icon
    fanart = get_addon_fanart()
    li.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'fanart': fanart})
    return url, li, is_folder


# ── Main Menu ─────────────────────────────────────────────────────────────

def main_menu():
    tmdb.prompt_for_api_key()
    items = [
        _menu_item('[B]Live Channels[/B]', 'live_channels'),
        _menu_item('Movies', 'movie_menu'),
        _menu_item('TV Shows', 'tv_menu'),
        _menu_item('[B]Anime & Manga[/B]', 'anime_menu'),
        _menu_item('Latest Releases', 'latest_releases'),
        _menu_item('Trending Movies', 'trakt_list', extra_params={'path': 'movies/trending', 'media_type': 'movie'}),
        _menu_item('Trending TV Shows', 'trakt_list', extra_params={'path': 'shows/trending', 'media_type': 'show'}),
        _menu_item('Latest Episodes', 'calendar'),
        _menu_item('Continue Watching', 'continue_watching'),
        _menu_item('My Trakt', 'my_trakt'),
        _menu_item('Search', 'search_menu'),
    ]
    
    # Add Cloud menu item only if debrid is configured
    if cloud_browser.is_cloud_configured():
        items.append(_menu_item('[B][COLOR cyan]Cloud[/COLOR][/B]', 'cloud_main_menu'))
    
    # Add Locals menu item only if folders are configured
    if local_scanner.is_configured():
        items.append(_menu_item('[B][COLOR lime]Locals[/COLOR][/B]', 'locals_main_menu'))
    
    # Add Plex menu item only if configured and enabled
    if plex_server.is_configured():
        items.append(_menu_item('[B][COLOR orange]Plex[/COLOR][/B]', 'plex_main_menu'))
    
    # Add Emby menu item only if configured and enabled
    if emby_server.is_configured():
        items.append(_menu_item('[B][COLOR purple]Emby[/COLOR][/B]', 'emby_main_menu'))
    
    items.extend([
        _menu_item('Debrid Services', 'debrid_menu'),
        _menu_item('Tools', 'tools_menu'),
        _menu_item('Buy Me a Beer', 'donate', is_folder=False),
    ])
    
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── Movie Menu ────────────────────────────────────────────────────────────

def movie_menu():
    items = [
        _menu_item('Latest Releases (In Cinemas)', 'latest_releases'),
        _menu_item('Trending', 'trakt_list', extra_params={'path': 'movies/trending', 'media_type': 'movie'}),
        _menu_item('Popular', 'trakt_list', extra_params={'path': 'movies/popular', 'media_type': 'movie'}),
        _menu_item('Most Watched (Week)', 'trakt_list', extra_params={'path': 'movies/watched/weekly', 'media_type': 'movie'}),
        _menu_item('Most Watched (All Time)', 'trakt_list', extra_params={'path': 'movies/watched/all', 'media_type': 'movie'}),
        _menu_item('Box Office', 'trakt_list', extra_params={'path': 'movies/boxoffice', 'media_type': 'movie'}),
        _menu_item('Anticipated', 'anticipated', extra_params={'media_type': 'movie'}),
        _menu_item('Recommended For You', 'recommendations', extra_params={'media_type': 'movie'}),
        _menu_item('Genres', 'list_genres', extra_params={'path': 'movie'}),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── TV Menu ───────────────────────────────────────────────────────────────

def tv_menu():
    items = [
        _menu_item('Trending Shows', 'trakt_list', extra_params={'path': 'shows/trending', 'media_type': 'show'}),
        _menu_item('Popular Shows', 'trakt_list', extra_params={'path': 'shows/popular', 'media_type': 'show'}),
        _menu_item('Most Watched (Week)', 'trakt_list', extra_params={'path': 'shows/watched/weekly', 'media_type': 'show'}),
        _menu_item('Most Watched (All Time)', 'trakt_list', extra_params={'path': 'shows/watched/all', 'media_type': 'show'}),
        _menu_item('Anticipated', 'anticipated', extra_params={'media_type': 'show'}),
        _menu_item('Recommended For You', 'recommendations', extra_params={'media_type': 'show'}),
        _menu_item('My Calendar', 'calendar', extra_params={'media_type': 'show'}),
        _menu_item('Genres', 'list_genres', extra_params={'path': 'tv'}),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── Search Menu ───────────────────────────────────────────────────────────

def search_menu():
    items = [
        _menu_item('Search Movies', 'search_dialog', extra_params={'media_type': 'movie'}),
        _menu_item('Search TV Shows', 'search_dialog', extra_params={'media_type': 'show'}),
        _menu_item('Search Anime', 'anime_search', extra_params={'media_type': 'tv'}),
        _menu_item('Search Manga', 'manga_search'),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── Anime & Manga Menu ────────────────────────────────────────────────────

def anime_menu():
    """Main Anime & Manga menu"""
    items = [
        _menu_item('[B]Anime Movies[/B]', 'anime_movies_menu'),
        _menu_item('[B]Anime TV Shows[/B]', 'anime_tv_menu'),
        _menu_item('[B]Manga[/B]', 'manga_menu'),
        _menu_item('[B]Torrent Sites[/B]', 'anime_torrent_menu'),
        _menu_item('Trending Anime', 'anime_tv_popular'),
        _menu_item('Currently Airing', 'anime_tv_airing'),
        _menu_item('New Episodes (Calendar)', 'anime_calendar'),
        _menu_item('Search Anime', 'anime_search', extra_params={'media_type': 'tv'}),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── My Trakt Menu ────────────────────────────────────────────────────────

def my_trakt():
    trakt_status = "[COLOR lime](Connected)[/COLOR]" if trakt_auth.is_authorized() else "[COLOR red](Not Connected)[/COLOR]"
    items = [
        _menu_item(f'My Trakt {trakt_status}', 'trakt_status', is_folder=False),
        _menu_item('Movie Watchlist', 'trakt_list', extra_params={'path': 'sync/watchlist/movies', 'media_type': 'movie'}),
        _menu_item('Show Watchlist', 'trakt_list', extra_params={'path': 'sync/watchlist/shows', 'media_type': 'show'}),
        _menu_item('Movie Collection', 'trakt_list', extra_params={'path': 'sync/collection/movies', 'media_type': 'movie'}),
        _menu_item('Show Collection', 'trakt_list', extra_params={'path': 'sync/collection/shows', 'media_type': 'show'}),
        _menu_item('Continue Watching', 'continue_watching'),
        _menu_item('Watched Movies', 'trakt_list', extra_params={'path': 'sync/watched/movies', 'media_type': 'movie'}),
        _menu_item('Watched Shows', 'trakt_list', extra_params={'path': 'sync/watched/shows', 'media_type': 'show'}),
        _menu_item('My Calendar', 'calendar'),
        _menu_item('My Custom Lists', 'my_lists'),
        _menu_item('Popular Lists', 'popular_lists'),
        _menu_item('Friends', 'friends'),
        _menu_item('My Stats', 'user_stats', is_folder=False),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── Debrid Services Menu ──────────────────────────────────────────────────

def debrid_menu():
    items = [
        _menu_item('Account Status', 'account_status', is_folder=False),
        _menu_item('Debrid Cloud', 'cloud_menu'),
        _menu_item('[COLOR yellow]Authorize Real-Debrid[/COLOR]', 'auth_rd', is_folder=False),
        _menu_item('[COLOR yellow]Authorize AllDebrid[/COLOR]', 'auth_ad', is_folder=False),
        _menu_item('[COLOR yellow]Authorize Premiumize[/COLOR]', 'auth_pm', is_folder=False),
        _menu_item('[COLOR yellow]Authorize TorBox[/COLOR]', 'auth_tb', is_folder=False),
        _menu_item('[COLOR yellow]Login to LinkSnappy[/COLOR]', 'auth_ls', is_folder=False),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── Tools Menu ────────────────────────────────────────────────────────────

def tools_menu():
    items = [
        _menu_item('Account Status', 'account_status', is_folder=False),
        _menu_item('[COLOR yellow]Configure Local Folders[/COLOR]', 'locals_configure'),
        _menu_item('[COLOR orange]Configure Plex Server[/COLOR]', 'plex_configure', is_folder=False),
        _menu_item('[COLOR purple]Configure Emby Server[/COLOR]', 'emby_configure', is_folder=False),
        _menu_item('Clear Cache', 'clear_cache', is_folder=False),
        _menu_item('Settings', 'open_settings', is_folder=False),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


def search_dialog(media_type):
    keyboard = xbmc.Keyboard('', f'Search {"Movies" if media_type == "movie" else "TV Shows"}')
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            trakt_api.search(query, media_type)


# ── Donation ──────────────────────────────────────────────────────────────

def show_donation():
    qr_path = os.path.join(tempfile.gettempdir(), 'test1_qr.png')
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=%s&bgcolor=0-0-0&color=255-255-255' % quote_plus(KOFI_URL),
            headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            with open(qr_path, 'wb') as f:
                f.write(resp.read())
        xbmc.executebuiltin('ShowPicture(%s)' % qr_path)
        xbmc.sleep(300)
    except:
        pass
    xbmcgui.Dialog().ok('Support zeus768', 'Scan QR or visit:\n[COLOR cyan]%s[/COLOR]' % KOFI_URL)
    try:
        xbmc.executebuiltin('Action(Back)')
    except:
        pass


# ── Account Status ────────────────────────────────────────────────────────

def show_account_status():
    progress = xbmcgui.DialogProgress()
    progress.create('Account Status', 'Checking debrid accounts...')

    accounts = debrid.get_all_account_info()
    progress.close()

    lines = ['[B][COLOR skyblue]--- Debrid Account Status ---[/COLOR][/B]\n']
    for acct in accounts:
        name = acct.get('name', 'Unknown')
        if acct.get('configured') is False:
            lines.append('[COLOR gray]%s: Not configured[/COLOR]\n' % name)
            continue
        if acct.get('error'):
            lines.append('[COLOR red]%s: Error - %s[/COLOR]\n' % (name, acct['error']))
            continue

        username = acct.get('username', '')
        email = acct.get('email', '')
        acct_type = acct.get('type', 'unknown')
        premium = acct.get('premium', False)
        expires = acct.get('expires', 'Unknown')
        days_left = acct.get('days_left', 0)

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
        if username:
            line += '\n  User: %s' % username
        if email:
            line += '\n  Email: %s' % email
        line += '\n  Status: [COLOR %s]%s (%s)[/COLOR]' % (color, status, acct_type)
        line += '\n  Expires: %s' % expires
        if premium and days_left > 0:
            line += '  ([B][COLOR %s]%d days left[/COLOR][/B])' % (color, days_left)
        elif not premium and acct_type != 'unknown':
            line += '  [COLOR red](Account expired or free tier)[/COLOR]'
        if acct.get('points'):
            line += '\n  Fidelity Points: %d' % acct['points']
        line += '\n'
        lines.append(line)

    lines.append('\n[B][COLOR skyblue]--- Trakt Account ---[/COLOR][/B]\n')
    if trakt_auth.is_authorized():
        lines.append('[COLOR lime]Trakt: Authorized[/COLOR]')
    else:
        lines.append('[COLOR red]Trakt: Not authorized[/COLOR]')

    xbmcgui.Dialog().textviewer('Account Status', '\n'.join(lines))


# ══════════════════════════════════════════════════════════════════════════════
# ██████  DEBRID CLOUD BROWSER  ████████████████████████████████████████████████
# ══════════════════════════════════════════════════════════════════════════════

def cloud_menu():
    """Main cloud browser menu - shows available debrid services"""
    services = debrid.get_cloud_services()
    
    if not services:
        xbmcgui.Dialog().notification('No Debrid', 'Please configure a debrid service first', 
                                       xbmcgui.NOTIFICATION_WARNING, 4000)
        return
    
    items = []
    for name, _, svc_code in services:
        items.append(_menu_item(f'[B]{name}[/B] Cloud', 'cloud_service', 
                                extra_params={'service': svc_code}))
    
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_service_menu(service):
    """Show cloud items for a specific debrid service"""
    items = []
    
    if service == 'rd':
        items.append(_menu_item('[COLOR cyan]My Torrents[/COLOR]', 'cloud_rd_torrents'))
        items.append(_menu_item('[COLOR cyan]Download History[/COLOR]', 'cloud_rd_downloads'))
    
    elif service == 'pm':
        items.append(_menu_item('[COLOR cyan]My Cloud Files[/COLOR]', 'cloud_pm_files'))
        items.append(_menu_item('[COLOR cyan]Transfers[/COLOR]', 'cloud_pm_transfers'))
    
    elif service == 'tb':
        items.append(_menu_item('[COLOR cyan]My Torrents[/COLOR]', 'cloud_tb_torrents'))
    
    elif service == 'ad':
        items.append(_menu_item('[COLOR cyan]My Magnets[/COLOR]', 'cloud_ad_magnets'))
    
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_rd_torrents():
    """List Real-Debrid torrents"""
    items = debrid.rd_get_torrents()
    
    if not items:
        xbmcgui.Dialog().notification('Real-Debrid', 'No torrents found', 
                                       xbmcgui.NOTIFICATION_INFO, 3000)
        return
    
    for item in items:
        status = item.get('status', '')
        progress = item.get('progress', 0)
        
        if status == 'downloaded':
            label = f"[COLOR lime][OK][/COLOR] {item['name']} [{item['size']}]"
        elif status == 'downloading':
            label = f"[COLOR yellow]v {progress}%[/COLOR] {item['name']}"
        else:
            label = f"[COLOR gray]{status}[/COLOR] {item['name']}"
        
        url = build_url({'action': 'cloud_rd_torrent_files', 'torrent_id': item['id']})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': get_addon_icon(), 'thumb': get_addon_icon()})
        
        li.addContextMenuItems([
            ('Delete', f"RunPlugin(plugin://plugin.video.genesis/?action=cloud_delete&service=rd&item_id={item['id']})")
        ])
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_rd_torrent_files(torrent_id):
    """List files in a Real-Debrid torrent"""
    files = debrid.rd_get_torrent_files(torrent_id)
    
    if not files:
        xbmcgui.Dialog().notification('Real-Debrid', 'No files found', 
                                       xbmcgui.NOTIFICATION_INFO, 3000)
        return
    
    for f in files:
        label = f"{f['name']}"
        if f.get('size'):
            label += f" [{f['size']}]"
        
        url = build_url({'action': 'cloud_play_rd', 'link': f['link']})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': get_addon_icon(), 'thumb': get_addon_icon()})
        li.setProperty('IsPlayable', 'true')
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_rd_downloads():
    """List Real-Debrid download history"""
    items = debrid.rd_get_downloads()
    
    if not items:
        xbmcgui.Dialog().notification('Real-Debrid', 'No downloads found', 
                                       xbmcgui.NOTIFICATION_INFO, 3000)
        return
    
    for item in items:
        label = f"{item['name']} [{item['size']}]"
        if item.get('date'):
            label = f"[COLOR gray]{item['date']}[/COLOR] {label}"
        
        url = build_url({'action': 'cloud_play_direct', 'link': item['link']})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': get_addon_icon(), 'thumb': get_addon_icon()})
        
        if item.get('is_video'):
            li.setProperty('IsPlayable', 'true')
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_play_rd(link):
    """Play a Real-Debrid link (unrestrict first)"""
    rd = debrid.RealDebrid()
    direct_url = rd.unrestrict_link(link)
    
    if direct_url:
        li = xbmcgui.ListItem(path=direct_url)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        xbmcgui.Dialog().notification('Error', 'Failed to get download link', 
                                       xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def cloud_play_direct(link):
    """Play a direct link"""
    if link:
        li = xbmcgui.ListItem(path=link)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        xbmcgui.Dialog().notification('Error', 'No link available', 
                                       xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def cloud_delete_item(service, item_id):
    """Delete an item from cloud"""
    if xbmcgui.Dialog().yesno('Delete', 'Are you sure you want to delete this item?'):
        success = debrid.delete_cloud_item(service, item_id)
        if success:
            xbmcgui.Dialog().notification('Deleted', 'Item removed from cloud', 
                                           xbmcgui.NOTIFICATION_INFO, 2000)
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcgui.Dialog().notification('Error', 'Failed to delete item', 
                                           xbmcgui.NOTIFICATION_ERROR, 3000)


def clear_cache():
    """Clear addon cache"""
    xbmcgui.Dialog().notification('Cache', 'Cache cleared', xbmcgui.NOTIFICATION_INFO)


# ══════════════════════════════════════════════════════════════════════════════
# ANIME PLAYBACK FUNCTIONS (DEFINED BEFORE ROUTER)
# ══════════════════════════════════════════════════════════════════════════════

def play_anime(title, year='', mal_id='', media_type='movie'):
    """Play anime movie via anime torrent scrapers"""
    services = debrid.get_active_services()
    if not services:
        xbmcgui.Dialog().notification('No Debrid', 'Configure a Debrid service in Settings', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    search_query = f'{title} {year}' if year else title
    
    progress = xbmcgui.DialogProgress()
    progress.create('Test1', f'Searching anime sites for {title}...')
    
    try:
        results = anime_scrapers.search_all_anime(search_query, '1080p')
    except Exception as e:
        xbmc.log(f'Anime scraper error: {e}', xbmc.LOGERROR)
        results = []
    
    if not results:
        progress.close()
        xbmcgui.Dialog().notification('No Sources', f'No anime torrents found for {title}', xbmcgui.NOTIFICATION_WARNING, 4000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    progress.update(40, f'Found {len(results)} sources. Checking cache...')
    
    # Extract hashes
    hashes = []
    for r in results:
        h = anime_scrapers.extract_hash(r.get('magnet', ''))
        if h:
            hashes.append(h)
            r['hash'] = h
    
    # Check cache
    cached_set = set()
    if hashes:
        try:
            cached_set = debrid.check_cache_all(hashes)
        except Exception:
            pass
    
    progress.close()
    
    # Import source picker
    from resources.lib import source_picker
    selected = source_picker.show_source_picker(results, cached_set, title)
    
    if not selected:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    magnet = selected.get('magnet', '')
    if not magnet:
        xbmcgui.Dialog().notification('Error', 'No magnet link', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    progress = xbmcgui.DialogProgress()
    progress.create('Test1', 'Resolving anime source via debrid...')
    
    url, svc_name = debrid.resolve_magnet(magnet)
    progress.close()
    
    if url:
        xbmcgui.Dialog().notification(svc_name, f'Playing {title}', xbmcgui.NOTIFICATION_INFO, 3000)
        li = xbmcgui.ListItem(path=url)
        if '|' in url:
            parts = url.split('|', 1)
            li = xbmcgui.ListItem(path=parts[0])
            li.setProperty('inputstream.adaptive.stream_headers', parts[1])
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        xbmcgui.Dialog().notification('Failed', 'Could not resolve source', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def play_anime_episode(title, episode, mal_id=''):
    """Play anime episode via anime torrent scrapers"""
    services = debrid.get_active_services()
    if not services:
        xbmcgui.Dialog().notification('No Debrid', 'Configure a Debrid service in Settings', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    # Format episode number
    ep_num = str(episode).zfill(2)
    search_query = f'{title} {ep_num}'
    
    progress = xbmcgui.DialogProgress()
    progress.create('Test1', f'Searching for {title} Episode {episode}...')
    
    try:
        results = anime_scrapers.search_all_anime(search_query, '1080p')
    except Exception as e:
        xbmc.log(f'Anime scraper error: {e}', xbmc.LOGERROR)
        results = []
    
    if not results:
        progress.close()
        xbmcgui.Dialog().notification('No Sources', f'No torrents found for {title} E{ep_num}', xbmcgui.NOTIFICATION_WARNING, 4000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    progress.update(40, f'Found {len(results)} sources. Checking cache...')
    
    # Extract hashes
    hashes = []
    for r in results:
        h = anime_scrapers.extract_hash(r.get('magnet', ''))
        if h:
            hashes.append(h)
            r['hash'] = h
    
    # Check cache
    cached_set = set()
    if hashes:
        try:
            cached_set = debrid.check_cache_all(hashes)
        except Exception:
            pass
    
    progress.close()
    
    from resources.lib import source_picker
    selected = source_picker.show_source_picker(results, cached_set, f'{title} E{ep_num}')
    
    if not selected:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    magnet = selected.get('magnet', '')
    if not magnet:
        xbmcgui.Dialog().notification('Error', 'No magnet link', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    progress = xbmcgui.DialogProgress()
    progress.create('Test1', 'Resolving source via debrid...')
    
    url, svc_name = debrid.resolve_magnet(magnet)
    progress.close()
    
    if url:
        xbmcgui.Dialog().notification(svc_name, f'Playing {title} E{ep_num}', xbmcgui.NOTIFICATION_INFO, 3000)
        li = xbmcgui.ListItem(path=url)
        if '|' in url:
            parts = url.split('|', 1)
            li = xbmcgui.ListItem(path=parts[0])
            li.setProperty('inputstream.adaptive.stream_headers', parts[1])
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        xbmcgui.Dialog().notification('Failed', 'Could not resolve source', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def show_anime_torrent_site(site):
    """Show latest releases from specific anime torrent site"""
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    progress = xbmcgui.DialogProgress()
    progress.create('Test1', f'Loading {site} latest releases...')
    
    results = []
    
    try:
        if site == 'nyaa':
            scraper = anime_scrapers.NyaaAnimeScraper()
            scraper.enabled = True
            results = scraper.search('', 'anime')
        elif site == 'subsplease':
            scraper = anime_scrapers.SubsPleaseScraper()
            scraper.enabled = True
            results = scraper.get_latest()
        elif site == 'animetosho':
            scraper = anime_scrapers.AnimeToshoScraper()
            scraper.enabled = True
            results = scraper.search('')
        elif site == 'tokyotosho':
            scraper = anime_scrapers.TokyoToshoScraper()
            scraper.enabled = True
            results = scraper.search('', 'anime')
        elif site == 'erairaws':
            scraper = anime_scrapers.EraiRawsScraper()
            scraper.enabled = True
            results = scraper.search('')
        elif site == 'anidex':
            scraper = anime_scrapers.AniDexScraper()
            scraper.enabled = True
            results = scraper.search('')
    except Exception as e:
        xbmc.log(f'Torrent site error: {e}', xbmc.LOGWARNING)
    
    progress.close()
    
    if not results:
        xbmcgui.Dialog().notification(site.capitalize(), 'No results found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for r in results:
        title = r.get('title', 'Unknown')
        quality = r.get('quality', '')
        seeds = r.get('seeds', 0)
        size = r.get('size', '')
        subgroup = r.get('subgroup', '')
        
        label = title
        if subgroup:
            label = f'[{subgroup}] {label}'
        
        info_parts = []
        if quality:
            info_parts.append(quality)
        if seeds:
            info_parts.append(f'{seeds} seeds')
        if size:
            info_parts.append(size)
        
        if info_parts:
            label += f' | {" | ".join(info_parts)}'
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({
            'action': 'play_anime_torrent',
            'magnet': r.get('magnet', ''),
            'title': title
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, li, False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def search_anime_torrents_dialog():
    """Show search dialog for anime torrents"""
    keyboard = xbmc.Keyboard('', 'Search Anime Torrents')
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            search_anime_torrents(query)


def search_anime_torrents(query):
    """Search all anime torrent sites"""
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    progress = xbmcgui.DialogProgress()
    progress.create('Test1', f'Searching anime sites for "{query}"...')
    
    try:
        results = anime_scrapers.search_all_anime(query, '1080p')
    except Exception as e:
        xbmc.log(f'Anime search error: {e}', xbmc.LOGWARNING)
        results = []
    
    progress.close()
    
    if not results:
        xbmcgui.Dialog().notification('Search', 'No results found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    for r in results:
        title = r.get('title', 'Unknown')
        quality = r.get('quality', '')
        seeds = r.get('seeds', 0)
        size = r.get('size', '')
        source = r.get('source', '')
        subgroup = r.get('subgroup', '')
        
        label = title
        
        info_parts = []
        if source:
            info_parts.append(source)
        if quality:
            info_parts.append(quality)
        if seeds:
            info_parts.append(f'{seeds}S')
        if size:
            info_parts.append(size)
        
        if info_parts:
            label += f' [{" | ".join(info_parts)}]'
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({
            'action': 'play_anime_torrent',
            'magnet': r.get('magnet', ''),
            'title': title
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, li, False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def play_anime_torrent(magnet, title):
    """Play a specific anime torrent directly"""
    if not magnet:
        xbmcgui.Dialog().notification('Error', 'No magnet link provided', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    services = debrid.get_active_services()
    if not services:
        xbmcgui.Dialog().notification('No Debrid', 'Configure a Debrid service in Settings', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    
    progress = xbmcgui.DialogProgress()
    progress.create('Test1', f'Resolving {title}...')
    
    url, svc_name = debrid.resolve_magnet(magnet)
    progress.close()
    
    if url:
        xbmcgui.Dialog().notification(svc_name, f'Playing {title}', xbmcgui.NOTIFICATION_INFO, 3000)
        li = xbmcgui.ListItem(path=url)
        if '|' in url:
            parts = url.split('|', 1)
            li = xbmcgui.ListItem(path=parts[0])
            li.setProperty('inputstream.adaptive.stream_headers', parts[1])
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        xbmcgui.Dialog().notification('Failed', 'Could not resolve magnet', xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())






# ══════════════════════════════════════════════════════════════════════════════
# CLOUD BROWSER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def cloud_main_menu():
    """Main Cloud menu - shows all services and categories"""
    services = cloud_browser.get_available_services()
    
    if not services:
        xbmcgui.Dialog().notification('Cloud', 'No debrid services configured', 
                                       xbmcgui.NOTIFICATION_WARNING)
        return
    
    items = []
    
    # Add unified view options
    items.append(_menu_item('[B][COLOR lime]All Downloaded[/COLOR][/B]', 'cloud_downloaded'))
    items.append(_menu_item('[B][COLOR yellow]Currently Downloading[/COLOR][/B]', 'cloud_downloading'))
    items.append(_menu_item('[B][COLOR cyan]Cached/History[/COLOR][/B]', 'cloud_cached'))
    
    # Add per-service options
    for svc in services:
        items.append(_menu_item(f'[COLOR white]{svc["name"]} Cloud[/COLOR]', 
                                'cloud_service_browser', 
                                extra_params={'service': svc['code']}))
    
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_service_browser(service):
    """Browse specific service cloud"""
    items = [
        _menu_item('[COLOR lime]Downloaded[/COLOR]', 'cloud_downloaded', extra_params={'service': service}),
        _menu_item('[COLOR yellow]Downloading[/COLOR]', 'cloud_downloading', extra_params={'service': service}),
        _menu_item('[COLOR cyan]History/Cached[/COLOR]', 'cloud_cached', extra_params={'service': service}),
    ]
    
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_show_downloaded(service=''):
    """Show downloaded items from cloud"""
    progress = xbmcgui.DialogProgress()
    progress.create('Cloud', 'Loading downloaded items...')
    
    items = cloud_browser.get_all_cloud_items(service if service else None)
    progress.close()
    
    if not items['downloaded']:
        xbmcgui.Dialog().notification('Cloud', 'No downloaded items', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for item in items['downloaded']:
        svc = item.get('service', 'unknown').upper()
        label = f"[COLOR lime][OK][/COLOR] [{svc}] {item['name']}"
        if item.get('size'):
            label += f" [{item['size']}]"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        
        # Build URL for playback
        if item.get('links'):
            link = item['links'][0] if isinstance(item['links'], list) else item['links']
            url = build_url({
                'action': 'cloud_play_item',
                'service': item['service'],
                'link': link,
                'item_id': item.get('id', '')
            })
            li.setProperty('IsPlayable', 'true')
        elif item.get('link'):
            url = build_url({
                'action': 'cloud_play_item',
                'service': item['service'],
                'link': item['link']
            })
            li.setProperty('IsPlayable', 'true')
        else:
            url = build_url({
                'action': 'cloud_play_item',
                'service': item['service'],
                'item_id': item.get('id', '')
            })
        
        # Add context menu
        li.addContextMenuItems([
            ('Delete', f"RunPlugin(plugin://plugin.video.genesis/?action=cloud_delete_item&service={item['service']}&item_id={item.get('id', '')})")
        ])
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_show_downloading(service=''):
    """Show currently downloading items"""
    progress = xbmcgui.DialogProgress()
    progress.create('Cloud', 'Loading downloads in progress...')
    
    items = cloud_browser.get_all_cloud_items(service if service else None)
    progress.close()
    
    if not items['downloading']:
        xbmcgui.Dialog().notification('Cloud', 'No active downloads', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for item in items['downloading']:
        svc = item.get('service', 'unknown').upper()
        prog = item.get('progress', 0)
        status = item.get('status', 'downloading')
        
        label = f"[COLOR yellow]v {prog}%[/COLOR] [{svc}] {item['name']}"
        if status != 'downloading':
            label += f" ({status})"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        
        url = build_url({'action': 'cloud_downloading', 'service': service})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_show_cached(service=''):
    """Show cached/history items"""
    progress = xbmcgui.DialogProgress()
    progress.create('Cloud', 'Loading history...')
    
    items = cloud_browser.get_all_cloud_items(service if service else None)
    progress.close()
    
    if not items['cached']:
        xbmcgui.Dialog().notification('Cloud', 'No history items', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for item in items['cached']:
        svc = item.get('service', 'unknown').upper()
        label = f"[COLOR cyan]*[/COLOR] [{svc}] {item['name']}"
        if item.get('size'):
            label += f" [{item['size']}]"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        
        if item.get('link'):
            url = build_url({
                'action': 'cloud_play_item',
                'service': item['service'],
                'link': item['link']
            })
            li.setProperty('IsPlayable', 'true')
        else:
            url = build_url({'action': 'cloud_cached', 'service': service})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_play_item(service, link='', item_id=''):
    """Play a cloud item"""
    resolved_url = None
    
    if link:
        resolved_url = cloud_browser.resolve_cloud_link(service, link)
    elif item_id:
        resolved_url = cloud_browser.resolve_cloud_link(service, item_id, 'torrent')
    
    if resolved_url:
        li = xbmcgui.ListItem(path=resolved_url)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        xbmcgui.Dialog().notification('Error', 'Failed to resolve link', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def cloud_delete_item_action(service, item_id):
    """Delete cloud item with confirmation"""
    if xbmcgui.Dialog().yesno('Delete', 'Are you sure you want to delete this item?'):
        if cloud_browser.delete_cloud_item(service, item_id):
            xbmcgui.Dialog().notification('Deleted', 'Item removed', xbmcgui.NOTIFICATION_INFO)
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmcgui.Dialog().notification('Error', 'Failed to delete', xbmcgui.NOTIFICATION_ERROR)


def cloud_pm_folder(folder_id):
    """Browse Premiumize folder"""
    items = cloud_browser.pm_get_folder_contents(folder_id)
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for item in items:
        if item.get('is_folder'):
            label = f"[FOLDER] {item['name']}"
            url = build_url({'action': 'cloud_pm_folder', 'folder_id': item['id']})
            is_folder = True
        else:
            label = f"{item['name']}"
            if item.get('size'):
                label += f" [{item['size']}]"
            url = build_url({
                'action': 'cloud_play_item',
                'service': 'pm',
                'link': item.get('link', '')
            })
            is_folder = False
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        
        if not is_folder:
            li.setProperty('IsPlayable', 'true')
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    
    xbmcplugin.endOfDirectory(HANDLE)


# ══════════════════════════════════════════════════════════════════════════════
# LOCAL SCANNER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def locals_main_menu():
    """Main Locals menu"""
    items = [
        _menu_item('[B][COLOR lime]Movies[/COLOR][/B]', 'locals_movies'),
        _menu_item('[B][COLOR cyan]TV Shows[/COLOR][/B]', 'locals_tv_shows'),
        _menu_item('[COLOR yellow]Configure Folders[/COLOR]', 'locals_configure'),
        _menu_item('[COLOR orange]Rescan Library[/COLOR]', 'locals_rescan', is_folder=False),
    ]
    
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


def locals_show_movies():
    """Show local movies"""
    # Try cached results first
    results = local_scanner.get_cached_scan()
    
    if not results:
        progress = xbmcgui.DialogProgress()
        progress.create('Local Scanner', 'Scanning for movies...')
        results = local_scanner.scan_all_folders(progress)
        local_scanner.save_scan_cache(results)
        progress.close()
    
    movies = results.get('movies', [])
    
    if not movies:
        xbmcgui.Dialog().notification('Locals', 'No movies found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    # Sort by title
    movies.sort(key=lambda x: x.get('title', '').lower())
    
    for movie in movies:
        title = movie.get('title', 'Unknown')
        year = movie.get('year', '')
        quality = movie.get('quality', '')
        
        label = title
        if year:
            label += f" ({year})"
        if quality and quality != 'Unknown':
            label += f" [{quality}]"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({'action': 'locals_play', 'path': movie['path']})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def locals_show_tv_shows():
    """Show local TV shows grouped by series"""
    results = local_scanner.get_cached_scan()
    
    if not results:
        progress = xbmcgui.DialogProgress()
        progress.create('Local Scanner', 'Scanning for TV shows...')
        results = local_scanner.scan_all_folders(progress)
        local_scanner.save_scan_cache(results)
        progress.close()
    
    episodes = results.get('tv_shows', [])
    
    if not episodes:
        xbmcgui.Dialog().notification('Locals', 'No TV shows found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    # Group by show
    shows = local_scanner.group_tv_shows(episodes)
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for show_name, show_data in sorted(shows.items()):
        season_count = len(show_data['seasons'])
        episode_count = sum(len(eps) for eps in show_data['seasons'].values())
        
        label = f"{show_name} ({season_count} Seasons, {episode_count} Episodes)"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        
        url = build_url({'action': 'locals_tv_show', 'show': show_name})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def locals_show_tv_show(show_name):
    """Show seasons for a TV show"""
    results = local_scanner.get_cached_scan()
    if not results:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    episodes = results.get('tv_shows', [])
    shows = local_scanner.group_tv_shows(episodes)
    
    show_data = shows.get(show_name)
    if not show_data:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for season_num in sorted(show_data['seasons'].keys()):
        season_eps = show_data['seasons'][season_num]
        label = f"Season {season_num} ({len(season_eps)} Episodes)"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        
        url = build_url({
            'action': 'locals_tv_season',
            'show': show_name,
            'season': str(season_num)
        })
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def locals_show_tv_season(show_name, season):
    """Show episodes for a TV season"""
    results = local_scanner.get_cached_scan()
    if not results:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    episodes = results.get('tv_shows', [])
    shows = local_scanner.group_tv_shows(episodes)
    
    show_data = shows.get(show_name)
    if not show_data:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    season_num = int(season)
    season_eps = show_data['seasons'].get(season_num, [])
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for ep in season_eps:
        ep_num = ep.get('episode', 0)
        quality = ep.get('quality', '')
        
        label = f"Episode {ep_num}"
        if quality and quality != 'Unknown':
            label += f" [{quality}]"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({'action': 'locals_play', 'path': ep['path']})
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def locals_configure_menu():
    """Show configuration menu for local folders"""
    folders = local_scanner.get_configured_folders()
    
    items = [
        _menu_item('[COLOR lime]+ Add Folder[/COLOR]', 'locals_add_folder', is_folder=False),
    ]
    
    addon_icon = get_addon_icon()
    addon_fanart = get_addon_fanart()
    
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    
    # Show configured folders with remove option
    for folder in folders:
        folder_name = os.path.basename(folder.rstrip('/\\')) or folder
        label = f"[COLOR white]{folder_name}[/COLOR]"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': addon_icon, 'thumb': addon_icon, 'fanart': addon_fanart})
        li.addContextMenuItems([
            ('Remove Folder', f"RunPlugin(plugin://plugin.video.genesis/?action=locals_remove_folder&path={quote_plus(folder)})")
        ])
        
        url = build_url({'action': 'locals_configure'})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def locals_add_folder():
    """Add a local folder"""
    if local_scanner.add_folder():
        local_scanner.clear_cache()
        xbmc.executebuiltin('Container.Refresh')


def locals_remove_folder(path):
    """Remove a local folder"""
    if local_scanner.remove_folder(path):
        local_scanner.clear_cache()
        xbmcgui.Dialog().notification('Removed', 'Folder removed', xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')


def locals_rescan():
    """Force rescan of local folders"""
    local_scanner.clear_cache()
    progress = xbmcgui.DialogProgress()
    progress.create('Local Scanner', 'Rescanning all folders...')
    results = local_scanner.scan_all_folders(progress)
    local_scanner.save_scan_cache(results)
    progress.close()
    
    movies = len(results.get('movies', []))
    shows = len(results.get('tv_shows', []))
    xbmcgui.Dialog().notification('Scan Complete', f'{movies} movies, {shows} episodes', 
                                   xbmcgui.NOTIFICATION_INFO, 3000)


def locals_play_file(path):
    """Play a local file"""
    if path and xbmcvfs.exists(path):
        li = xbmcgui.ListItem(path=path)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        xbmcgui.Dialog().notification('Error', 'File not found', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())



# ══════════════════════════════════════════════════════════════════════════════
# PLEX SERVER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def plex_main_menu():
    """Main Plex menu"""
    if not plex_server.is_configured():
        xbmcgui.Dialog().notification('Plex', 'Server not configured', xbmcgui.NOTIFICATION_WARNING)
        return
    
    items = [
        _menu_item('[B][COLOR yellow]On Deck[/COLOR][/B]', 'plex_on_deck'),
        _menu_item('[B][COLOR lime]Recently Added[/COLOR][/B]', 'plex_recently_added'),
        _menu_item('Search Plex', 'plex_search'),
    ]
    
    # Get libraries
    libraries = plex_server.get_libraries()
    for lib in libraries:
        lib_type = lib.get('type', '')
        if lib_type == 'movie':
            color = 'cyan'
        elif lib_type == 'show':
            color = 'orange'
        else:
            color = 'white'
        
        items.append(_menu_item(
            f'[COLOR {color}]{lib["title"]}[/COLOR]',
            'plex_library',
            extra_params={'library_key': lib['key']}
        ))
    
    items.append(_menu_item('[COLOR red]Disable Plex[/COLOR]', 'plex_disable', is_folder=False))
    
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


def plex_show_library(library_key):
    """Show items from a Plex library"""
    items = plex_server.get_library_items(library_key)
    addon_fanart = get_addon_fanart()
    
    for item in items:
        item_type = item.get('type')
        title = item.get('title', 'Unknown')
        year = item.get('year', '')
        
        label = f"{title} ({year})" if year else title
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': item.get('thumb', ''),
            'thumb': item.get('thumb', ''),
            'fanart': item.get('art', '') or addon_fanart
        })
        
        info = {
            'title': title,
            'year': year,
            'plot': item.get('summary', ''),
            'rating': item.get('rating', 0)
        }
        
        if item_type == 'movie':
            info['mediatype'] = 'movie'
            li.setInfo('video', info)
            li.setProperty('IsPlayable', 'true')
            url = build_url({'action': 'plex_play', 'item_key': item['key']})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
        elif item_type == 'show':
            info['mediatype'] = 'tvshow'
            li.setInfo('video', info)
            url = build_url({'action': 'plex_show_seasons', 'show_key': item['key']})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        else:
            li.setProperty('IsPlayable', 'true')
            url = build_url({'action': 'plex_play', 'item_key': item['key']})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def plex_show_recently_added(library_key=''):
    """Show recently added items from Plex"""
    items = plex_server.get_recently_added(library_key if library_key else None)
    addon_fanart = get_addon_fanart()
    
    for item in items:
        item_type = item.get('type')
        title = item.get('title', 'Unknown')
        
        if item_type == 'episode':
            label = f"{item.get('show_title', '')} - {title}"
        else:
            year = item.get('year', '')
            label = f"{title} ({year})" if year else title
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': item.get('thumb', ''),
            'thumb': item.get('thumb', ''),
            'fanart': item.get('art', '') or addon_fanart
        })
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({'action': 'plex_play', 'item_key': item['key']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def plex_show_on_deck():
    """Show On Deck items from Plex"""
    items = plex_server.get_on_deck()
    addon_fanart = get_addon_fanart()
    
    for item in items:
        item_type = item.get('type')
        title = item.get('title', 'Unknown')
        
        if item_type == 'episode':
            show = item.get('show_title', '')
            season = item.get('season_index', 0)
            episode = item.get('episode_index', 0)
            label = f"{show} S{season:02d}E{episode:02d} - {title}"
        else:
            label = title
        
        # Add progress indicator
        offset = item.get('view_offset', 0)
        duration = item.get('duration', 1)
        if offset and duration:
            progress = int((offset / duration) * 100)
            label = f"[COLOR yellow]{progress}%[/COLOR] {label}"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': item.get('thumb', ''),
            'thumb': item.get('thumb', ''),
            'fanart': item.get('art', '') or addon_fanart
        })
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({'action': 'plex_play', 'item_key': item['key']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def plex_show_seasons(show_key):
    """Show seasons for a Plex TV show"""
    seasons = plex_server.get_show_seasons(show_key)
    addon_fanart = get_addon_fanart()
    
    for season in seasons:
        title = season.get('title', f"Season {season.get('index', 0)}")
        label = f"{title} ({season.get('leaf_count', 0)} episodes)"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': season.get('thumb', ''),
            'thumb': season.get('thumb', ''),
            'fanart': season.get('art', '') or addon_fanart
        })
        
        url = build_url({'action': 'plex_show_episodes', 'season_key': season['key']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'seasons')
    xbmcplugin.endOfDirectory(HANDLE)


def plex_show_episodes(season_key):
    """Show episodes for a Plex season"""
    episodes = plex_server.get_season_episodes(season_key)
    addon_fanart = get_addon_fanart()
    
    for ep in episodes:
        title = ep.get('title', 'Unknown')
        ep_num = ep.get('episode_index', 0)
        label = f"E{ep_num:02d} - {title}"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': ep.get('thumb', ''),
            'thumb': ep.get('thumb', ''),
            'fanart': ep.get('art', '') or addon_fanart
        })
        li.setInfo('video', {
            'title': title,
            'plot': ep.get('summary', ''),
            'episode': ep_num,
            'mediatype': 'episode'
        })
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({'action': 'plex_play', 'item_key': ep['key']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)


def plex_play_item(item_key):
    """Play a Plex item"""
    playback_url = plex_server.get_playback_url(item_key)
    
    if playback_url:
        li = xbmcgui.ListItem(path=playback_url)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        xbmcgui.Dialog().notification('Plex', 'Failed to get playback URL', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def plex_search_dialog():
    """Show Plex search dialog"""
    keyboard = xbmc.Keyboard('', 'Search Plex Library')
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            plex_show_search_results(query)


def plex_show_search_results(query):
    """Show Plex search results"""
    items = plex_server.search(query)
    addon_fanart = get_addon_fanart()
    
    for item in items:
        item_type = item.get('type')
        title = item.get('title', 'Unknown')
        year = item.get('year', '')
        
        label = f"[{item_type.upper()}] {title}"
        if year:
            label += f" ({year})"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': item.get('thumb', ''),
            'thumb': item.get('thumb', ''),
            'fanart': item.get('art', '') or addon_fanart
        })
        
        if item_type == 'show':
            url = build_url({'action': 'plex_show_seasons', 'show_key': item['key']})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        else:
            li.setProperty('IsPlayable', 'true')
            url = build_url({'action': 'plex_play', 'item_key': item['key']})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


# ══════════════════════════════════════════════════════════════════════════════
# EMBY SERVER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def emby_main_menu():
    """Main Emby menu"""
    if not emby_server.is_configured():
        xbmcgui.Dialog().notification('Emby', 'Server not configured', xbmcgui.NOTIFICATION_WARNING)
        return
    
    items = [
        _menu_item('[B][COLOR yellow]Continue Watching[/COLOR][/B]', 'emby_continue'),
        _menu_item('[B][COLOR cyan]Next Up[/COLOR][/B]', 'emby_next_up'),
        _menu_item('[B][COLOR lime]Recently Added[/COLOR][/B]', 'emby_recently_added'),
        _menu_item('Search Emby', 'emby_search'),
    ]
    
    # Get libraries
    libraries = emby_server.get_libraries()
    for lib in libraries:
        lib_type = lib.get('type', '')
        if lib_type == 'movies':
            color = 'cyan'
        elif lib_type == 'tvshows':
            color = 'orange'
        else:
            color = 'white'
        
        items.append(_menu_item(
            f'[COLOR {color}]{lib["name"]}[/COLOR]',
            'emby_library',
            extra_params={'library_id': lib['id']}
        ))
    
    items.append(_menu_item('[COLOR red]Disable Emby[/COLOR]', 'emby_disable', is_folder=False))
    
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


def emby_show_library(library_id):
    """Show items from an Emby library"""
    items = emby_server.get_library_items(library_id)
    addon_fanart = get_addon_fanart()
    
    for item in items:
        item_type = item.get('type', '')
        name = item.get('name', 'Unknown')
        year = item.get('year', '')
        
        label = f"{name} ({year})" if year else name
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': item.get('thumb', ''),
            'thumb': item.get('thumb', ''),
            'fanart': item.get('backdrop', '') or addon_fanart
        })
        
        info = {
            'title': name,
            'year': year,
            'plot': item.get('overview', ''),
            'rating': item.get('rating', 0)
        }
        
        if item_type == 'movie':
            info['mediatype'] = 'movie'
            li.setInfo('video', info)
            li.setProperty('IsPlayable', 'true')
            url = build_url({'action': 'emby_play', 'item_id': item['id']})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
        elif item_type == 'series':
            info['mediatype'] = 'tvshow'
            li.setInfo('video', info)
            url = build_url({'action': 'emby_show_seasons', 'show_id': item['id']})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        else:
            li.setProperty('IsPlayable', 'true')
            url = build_url({'action': 'emby_play', 'item_id': item['id']})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def emby_show_recently_added(library_id=''):
    """Show recently added items from Emby"""
    items = emby_server.get_recently_added(library_id if library_id else None)
    addon_fanart = get_addon_fanart()
    
    for item in items:
        item_type = item.get('type', '')
        name = item.get('name', 'Unknown')
        
        if item_type == 'episode':
            label = f"{item.get('show_name', '')} - {name}"
        else:
            year = item.get('year', '')
            label = f"{name} ({year})" if year else name
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': item.get('thumb', ''),
            'thumb': item.get('thumb', ''),
            'fanart': item.get('backdrop', '') or addon_fanart
        })
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({'action': 'emby_play', 'item_id': item['id']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def emby_show_continue_watching():
    """Show Continue Watching items from Emby"""
    items = emby_server.get_continue_watching()
    addon_fanart = get_addon_fanart()
    
    for item in items:
        item_type = item.get('type', '')
        name = item.get('name', 'Unknown')
        
        if item_type == 'episode':
            show = item.get('show_name', '')
            season = item.get('season_index', 0)
            episode = item.get('episode_index', 0)
            label = f"{show} S{season:02d}E{episode:02d} - {name}"
        else:
            label = name
        
        # Add progress indicator
        position = item.get('resume_position', 0)
        duration = item.get('duration', 1)
        if position and duration:
            progress = int((position / duration) * 100)
            label = f"[COLOR yellow]{progress}%[/COLOR] {label}"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': item.get('thumb', ''),
            'thumb': item.get('thumb', ''),
            'fanart': item.get('backdrop', '') or addon_fanart
        })
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({'action': 'emby_play', 'item_id': item['id']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def emby_show_next_up():
    """Show Next Up episodes from Emby"""
    items = emby_server.get_next_up()
    addon_fanart = get_addon_fanart()
    
    for item in items:
        name = item.get('name', 'Unknown')
        show = item.get('show_name', '')
        season = item.get('season_index', 0)
        episode = item.get('episode_index', 0)
        
        label = f"{show} S{season:02d}E{episode:02d} - {name}"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': item.get('thumb', ''),
            'thumb': item.get('thumb', ''),
            'fanart': item.get('backdrop', '') or addon_fanart
        })
        li.setInfo('video', {
            'title': name,
            'plot': item.get('overview', ''),
            'episode': episode,
            'season': season,
            'mediatype': 'episode'
        })
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({'action': 'emby_play', 'item_id': item['id']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)


def emby_show_seasons(show_id):
    """Show seasons for an Emby TV show"""
    seasons = emby_server.get_show_seasons(show_id)
    addon_fanart = get_addon_fanart()
    
    for season in seasons:
        name = season.get('name', f"Season {season.get('index', 0)}")
        label = f"{name} ({season.get('episode_count', 0)} episodes)"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': season.get('thumb', ''),
            'thumb': season.get('thumb', ''),
            'fanart': season.get('backdrop', '') or addon_fanart
        })
        
        url = build_url({'action': 'emby_show_episodes', 'season_id': season['id']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'seasons')
    xbmcplugin.endOfDirectory(HANDLE)


def emby_show_episodes(season_id):
    """Show episodes for an Emby season"""
    episodes = emby_server.get_season_episodes(season_id)
    addon_fanart = get_addon_fanart()
    
    for ep in episodes:
        name = ep.get('name', 'Unknown')
        ep_num = ep.get('episode_index', 0)
        label = f"E{ep_num:02d} - {name}"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': ep.get('thumb', ''),
            'thumb': ep.get('thumb', ''),
            'fanart': ep.get('backdrop', '') or addon_fanart
        })
        li.setInfo('video', {
            'title': name,
            'plot': ep.get('overview', ''),
            'episode': ep_num,
            'mediatype': 'episode'
        })
        li.setProperty('IsPlayable', 'true')
        
        url = build_url({'action': 'emby_play', 'item_id': ep['id']})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)


def emby_play_item(item_id):
    """Play an Emby item"""
    playback_url = emby_server.get_playback_url(item_id)
    
    if playback_url:
        li = xbmcgui.ListItem(path=playback_url)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        xbmcgui.Dialog().notification('Emby', 'Failed to get playback URL', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def emby_search_dialog():
    """Show Emby search dialog"""
    keyboard = xbmc.Keyboard('', 'Search Emby Library')
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            emby_show_search_results(query)


def emby_show_search_results(query):
    """Show Emby search results"""
    items = emby_server.search(query)
    addon_fanart = get_addon_fanart()
    
    for item in items:
        item_type = item.get('type', '')
        name = item.get('name', 'Unknown')
        year = item.get('year', '')
        
        label = f"[{item_type.upper()}] {name}"
        if year:
            label += f" ({year})"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': item.get('thumb', ''),
            'thumb': item.get('thumb', ''),
            'fanart': item.get('backdrop', '') or addon_fanart
        })
        
        if item_type == 'series':
            url = build_url({'action': 'emby_show_seasons', 'show_id': item['id']})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        else:
            li.setProperty('IsPlayable', 'true')
            url = build_url({'action': 'emby_play', 'item_id': item['id']})
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)



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
    elif action == 'search_menu':
        search_menu()
    elif action == 'my_trakt':
        my_trakt()
    elif action == 'debrid_menu':
        debrid_menu()
    elif action == 'tools_menu':
        tools_menu()
    elif action == 'open_settings':
        get_addon().openSettings()
    elif action == 'donate':
        show_donation()
    elif action == 'account_status':
        show_account_status()
    elif action == 'clear_cache':
        clear_cache()
    elif action == 'trakt_status':
        if not trakt_auth.is_authorized():
            trakt_auth.authorize()

    # Content - with pagination support
    elif action == 'list_genres':
        tmdb.get_genres(params.get('path'))
    elif action == 'genre_discover':
        page = int(params.get('page', '1'))
        tmdb.discover_by_genre(params.get('media_type', 'movie'), params.get('genre_id', ''), page)
    elif action == 'trakt_list':
        page = params.get('page', '1')
        trakt_api.get_list(params.get('path'), params.get('media_type', 'movie'), page)
    elif action == 'search_dialog':
        search_dialog(params.get('media_type', 'movie'))
    elif action == 'search_results':
        trakt_api.search(params.get('query', ''), params.get('media_type', 'movie'), params.get('page', '1'))
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

    # Playback
    elif action == 'play':
        player.play(params.get('title', ''), params.get('year', ''), params.get('imdb_id', ''), params.get('tmdb_id', ''))
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
        debrid.Torbox().authorize()
    elif action == 'revoke_tb':
        debrid.Torbox().revoke()
    elif action == 'auth_ls':
        debrid.LinkSnappy().authorize()
    elif action == 'revoke_ls':
        debrid.LinkSnappy().revoke()
    
    # Debrid Cloud Browser
    elif action == 'cloud_menu':
        cloud_menu()
    elif action == 'cloud_service':
        cloud_service_menu(params.get('service', 'rd'))
    elif action == 'cloud_rd_torrents':
        cloud_rd_torrents()
    elif action == 'cloud_rd_torrent_files':
        cloud_rd_torrent_files(params.get('torrent_id', ''))
    elif action == 'cloud_rd_downloads':
        cloud_rd_downloads()
    elif action == 'cloud_play_rd':
        cloud_play_rd(params.get('link', ''))
    elif action == 'cloud_play_direct':
        cloud_play_direct(params.get('link', ''))
    elif action == 'cloud_delete':
        cloud_delete_item(params.get('service', ''), params.get('item_id', ''))
    
    # Live Channels with EPG
    elif action == 'live_channels':
        live_channels.show_live_channels()
    elif action == 'channel_epg':
        live_channels.show_channel_epg(params.get('channel_id', ''))
    elif action == 'channel_play_dialog':
        live_channels.show_play_dialog(params.get('channel_id', ''))
    elif action == 'play_channel_movie':
        live_channels.play_channel_movie(params.get('channel_id', ''), params.get('mode', 'beginning'))
    elif action == 'play_epg_movie':
        live_channels.play_epg_movie(params.get('tmdb_id', ''), params.get('title', ''), params.get('year', ''))
    
    # Latest Releases (In Cinemas Now)
    elif action == 'latest_releases':
        page = int(params.get('page', '1'))
        tmdb.get_latest_releases(page)
    
    # X-Ray Metadata
    elif action == 'xray':
        xray.show_xray_dialog(
            params.get('tmdb_id', ''),
            params.get('media_type', 'movie'),
            params.get('season'),
            params.get('episode'),
            params.get('title', ''),
            params.get('imdb_id', '')
        )
    elif action == 'xray_filmography':
        xray.show_cast_filmography(params.get('person_id', ''), params.get('person_name', ''))
    
    # Extras Menu (Similar Movies + Cast Options)
    elif action == 'extras_menu':
        xray.show_extras_menu(
            params.get('tmdb_id', ''),
            params.get('media_type', 'movie'),
            params.get('title', ''),
            params.get('imdb_id', '')
        )
    
    # Similar Movies (navigable list)
    elif action == 'similar_movies':
        xray.show_similar_movies(params.get('tmdb_id', ''), params.get('title', ''))
    
    # Cast Movies (movies by a specific actor)
    elif action == 'cast_movies':
        xray.show_cast_movies(params.get('person_id', ''), params.get('person_name', ''))
    
    # ══════════════════════════════════════════════════════════════════════════
    # ANIME & MANGA ROUTES
    # ══════════════════════════════════════════════════════════════════════════
    
    # Anime Main Menu
    elif action == 'anime_menu':
        anime_menu()
    
    # Anime Movies Menu
    elif action == 'anime_movies_menu':
        anime.anime_movies_menu()
    elif action == 'anime_movies_new':
        page = int(params.get('page', '1'))
        anime.get_anime_movies_new(page)
    elif action == 'anime_movies_top':
        page = int(params.get('page', '1'))
        anime.get_anime_movies_top(page)
    elif action == 'anime_movies_popular':
        page = int(params.get('page', '1'))
        anime.get_anime_movies_popular(page)
    elif action == 'anime_movies_upcoming':
        page = int(params.get('page', '1'))
        anime.get_anime_movies_upcoming(page)
    elif action == 'anime_movies_award':
        page = int(params.get('page', '1'))
        anime.get_anime_movies_award(page)
    elif action == 'anime_movies_classic':
        page = int(params.get('page', '1'))
        anime.get_anime_movies_classic(page)
    elif action == 'anime_movies_recent':
        page = int(params.get('page', '1'))
        anime.get_anime_movies_recent(page)
    elif action == 'anime_movies_ghibli':
        page = int(params.get('page', '1'))
        anime.get_anime_movies_ghibli(page)
    
    # Anime TV Menu
    elif action == 'anime_tv_menu':
        anime.anime_tv_menu()
    elif action == 'anime_tv_airing':
        page = int(params.get('page', '1'))
        anime.get_anime_tv_airing(page)
    elif action == 'anime_tv_top':
        page = int(params.get('page', '1'))
        anime.get_anime_tv_top(page)
    elif action == 'anime_tv_popular':
        page = int(params.get('page', '1'))
        anime.get_anime_tv_popular(page)
    elif action == 'anime_tv_upcoming':
        page = int(params.get('page', '1'))
        anime.get_anime_tv_upcoming(page)
    elif action == 'anime_tv_complete':
        page = int(params.get('page', '1'))
        anime.get_anime_tv_complete(page)
    elif action == 'anime_premieres':
        page = int(params.get('page', '1'))
        anime.get_anime_premieres(page)
    
    # Anime Calendar
    elif action == 'anime_calendar':
        anime.get_anime_calendar()
    elif action == 'anime_calendar_day':
        anime.get_anime_calendar_day(params.get('day', 'monday'))
    
    # Anime Seasonal
    elif action == 'anime_seasonal_menu':
        anime.anime_seasonal_menu()
    elif action == 'anime_seasonal':
        page = int(params.get('page', '1'))
        anime.get_anime_seasonal(params.get('year'), params.get('season'), page)
    
    # Anime Genres
    elif action == 'anime_movie_genres':
        anime.anime_movie_genres()
    elif action == 'anime_tv_genres':
        anime.anime_tv_genres()
    elif action == 'anime_by_genre':
        page = int(params.get('page', '1'))
        anime.get_anime_by_genre(params.get('genre_id'), params.get('media_type', 'tv'), page)
    
    # Anime Networks/Studios
    elif action == 'anime_networks':
        anime.anime_networks_menu()
    elif action == 'anime_by_network':
        page = int(params.get('page', '1'))
        anime.get_anime_by_studio(params.get('network'), page)
    elif action == 'anime_by_studio':
        page = int(params.get('page', '1'))
        anime.get_anime_by_studio(params.get('studio'), page)
    
    # Anime Search
    elif action == 'anime_search':
        anime.search_anime_dialog(params.get('media_type', 'tv'))
    elif action == 'anime_search_results':
        page = int(params.get('page', '1'))
        anime.search_anime(params.get('query', ''), params.get('media_type', 'tv'), page)
    
    # Anime Episodes/Details
    elif action == 'anime_show_episodes':
        anime.show_anime_episodes(params.get('mal_id'), params.get('title', ''))
    elif action == 'anime_info':
        anime.show_anime_info(params.get('mal_id'))
    
    # Anime Playback
    elif action == 'play_anime':
        play_anime(
            params.get('title', ''),
            params.get('year', ''),
            params.get('mal_id', ''),
            params.get('media_type', 'movie')
        )
    elif action == 'play_anime_episode':
        play_anime_episode(
            params.get('title', ''),
            params.get('episode', '1'),
            params.get('mal_id', '')
        )
    
    # ══════════════════════════════════════════════════════════════════════════
    # MANGA ROUTES
    # ══════════════════════════════════════════════════════════════════════════
    
    elif action == 'manga_menu':
        anime.manga_menu()
    elif action == 'manga_top':
        page = int(params.get('page', '1'))
        anime.get_manga_top(page)
    elif action == 'manga_popular':
        page = int(params.get('page', '1'))
        anime.get_manga_popular(page)
    elif action == 'manga_publishing':
        page = int(params.get('page', '1'))
        anime.get_manga_publishing(page)
    elif action == 'manga_lightnovel':
        page = int(params.get('page', '1'))
        anime.get_manga_lightnovel(page)
    elif action == 'manga_oneshot':
        page = int(params.get('page', '1'))
        anime.get_manga_oneshot(page)
    elif action == 'manga_manhwa':
        page = int(params.get('page', '1'))
        anime.get_manga_manhwa(page)
    elif action == 'manga_manhua':
        page = int(params.get('page', '1'))
        anime.get_manga_manhua(page)
    elif action == 'manga_genres':
        anime.manga_genres()
    elif action == 'manga_by_genre':
        page = int(params.get('page', '1'))
        anime.get_manga_by_genre(params.get('genre_id'), page)
    elif action == 'manga_search':
        anime.search_manga_dialog()
    elif action == 'manga_search_results':
        page = int(params.get('page', '1'))
        anime.search_manga(params.get('query', ''), page)
    elif action == 'manga_info':
        anime.show_manga_info(params.get('mal_id'))
    
    # ══════════════════════════════════════════════════════════════════════════
    # ANIME TORRENT SITES ROUTES
    # ══════════════════════════════════════════════════════════════════════════
    
    elif action == 'anime_torrent_menu':
        anime.torrent_sites_menu()
    elif action == 'anime_torrent_site':
        show_anime_torrent_site(params.get('site', 'nyaa'))
    elif action == 'anime_torrent_search':
        search_anime_torrents_dialog()
    elif action == 'anime_torrent_search_results':
        search_anime_torrents(params.get('query', ''))
    elif action == 'play_anime_torrent':
        play_anime_torrent(params.get('magnet', ''), params.get('title', ''))
    
    # ══════════════════════════════════════════════════════════════════════════
    # CLOUD BROWSER ROUTES
    # ══════════════════════════════════════════════════════════════════════════
    
    elif action == 'cloud_main_menu':
        cloud_main_menu()
    elif action == 'cloud_service_browser':
        cloud_service_browser(params.get('service', 'rd'))
    elif action == 'cloud_downloaded':
        cloud_show_downloaded(params.get('service', ''))
    elif action == 'cloud_downloading':
        cloud_show_downloading(params.get('service', ''))
    elif action == 'cloud_cached':
        cloud_show_cached(params.get('service', ''))
    elif action == 'cloud_play_item':
        cloud_play_item(params.get('service', ''), params.get('link', ''), params.get('item_id', ''))
    elif action == 'cloud_delete_item':
        cloud_delete_item_action(params.get('service', ''), params.get('item_id', ''))
    elif action == 'cloud_pm_folder':
        cloud_pm_folder(params.get('folder_id', ''))
    
    # ══════════════════════════════════════════════════════════════════════════
    # LOCAL SCANNER ROUTES
    # ══════════════════════════════════════════════════════════════════════════
    
    elif action == 'locals_main_menu':
        locals_main_menu()
    elif action == 'locals_movies':
        locals_show_movies()
    elif action == 'locals_tv_shows':
        locals_show_tv_shows()
    elif action == 'locals_tv_show':
        locals_show_tv_show(params.get('show', ''))
    elif action == 'locals_tv_season':
        locals_show_tv_season(params.get('show', ''), params.get('season', '1'))
    elif action == 'locals_configure':
        locals_configure_menu()
    elif action == 'locals_add_folder':
        locals_add_folder()
    elif action == 'locals_remove_folder':
        locals_remove_folder(params.get('path', ''))
    elif action == 'locals_rescan':
        locals_rescan()
    elif action == 'locals_play':
        locals_play_file(params.get('path', ''))
    
    # ══════════════════════════════════════════════════════════════════════════
    # PLEX SERVER ROUTES
    # ══════════════════════════════════════════════════════════════════════════
    
    elif action == 'plex_main_menu':
        plex_main_menu()
    elif action == 'plex_configure':
        plex_server.configure_server()
        xbmc.executebuiltin('Container.Refresh')
    elif action == 'plex_disable':
        plex_server.disable_server()
        xbmc.executebuiltin('Container.Refresh')
    elif action == 'plex_library':
        plex_show_library(params.get('library_key', ''))
    elif action == 'plex_recently_added':
        plex_show_recently_added(params.get('library_key', ''))
    elif action == 'plex_on_deck':
        plex_show_on_deck()
    elif action == 'plex_show_seasons':
        plex_show_seasons(params.get('show_key', ''))
    elif action == 'plex_show_episodes':
        plex_show_episodes(params.get('season_key', ''))
    elif action == 'plex_play':
        plex_play_item(params.get('item_key', ''))
    elif action == 'plex_search':
        plex_search_dialog()
    elif action == 'plex_search_results':
        plex_show_search_results(params.get('query', ''))
    
    # ══════════════════════════════════════════════════════════════════════════
    # EMBY SERVER ROUTES
    # ══════════════════════════════════════════════════════════════════════════
    
    elif action == 'emby_main_menu':
        emby_main_menu()
    elif action == 'emby_configure':
        emby_server.configure_server()
        xbmc.executebuiltin('Container.Refresh')
    elif action == 'emby_disable':
        emby_server.disable_server()
        xbmc.executebuiltin('Container.Refresh')
    elif action == 'emby_library':
        emby_show_library(params.get('library_id', ''))
    elif action == 'emby_recently_added':
        emby_show_recently_added(params.get('library_id', ''))
    elif action == 'emby_continue':
        emby_show_continue_watching()
    elif action == 'emby_next_up':
        emby_show_next_up()
    elif action == 'emby_show_seasons':
        emby_show_seasons(params.get('show_id', ''))
    elif action == 'emby_show_episodes':
        emby_show_episodes(params.get('season_id', ''))
    elif action == 'emby_play':
        emby_play_item(params.get('item_id', ''))
    elif action == 'emby_search':
        emby_search_dialog()
    elif action == 'emby_search_results':
        emby_show_search_results(params.get('query', ''))