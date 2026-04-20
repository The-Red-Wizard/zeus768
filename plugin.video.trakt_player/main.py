# -*- coding: utf-8 -*-
"""Trakt Player v2.2.0 - Superpowered Trakt addon.
Click-and-Play, Scrobble, Up Next, Discovery Feed, AI Vibes, Recommendations, Calendar, and more.
Based on zeus768's v2.1.6 fixed build with all custom features merged in."""
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
from resources.lib import tmdb, trakt_auth, trakt_api, filehost, debrid, discovery, feed, player

def get_addon():
    return xbmcaddon.Addon()

ADDON_ID = 'plugin.video.trakt_player'
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
    """Create a menu item with addon icon/fanart."""
    q = {'action': action}
    if extra_params:
        q.update(extra_params)
    url = build_url(q)
    li = xbmcgui.ListItem(label=label)
    icon = get_addon_icon()
    fanart = get_addon_fanart()
    li.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'fanart': fanart})
    return url, li, is_folder


# ── Main Menu ─────────────────────────────────────────────────────────────

def main_menu():
    tmdb.prompt_for_api_key()
    items = [
        _menu_item('Movies', 'movie_menu'),
        _menu_item('TV Shows', 'tv_menu'),
        _menu_item('Search', 'search_menu'),
        _menu_item('Continue Watching', 'continue_watching'),
        _menu_item('Debrid Cloud', 'cloud_menu'),
        _menu_item('Discovery Feed', 'feed_menu'),
        _menu_item('AI Vibes', 'discovery_menu'),
        _menu_item('My Trakt', 'my_trakt'),
        _menu_item('My Stats', 'user_stats', is_folder=False),
        _menu_item('Account Status', 'account_status', is_folder=False),
        _menu_item('Buy Me a Beer', 'donate', is_folder=False),
        _menu_item('Settings', 'open_settings', is_folder=False),
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── Movie Menu ────────────────────────────────────────────────────────────

def movie_menu():
    items = [
        _menu_item('Trending', 'trakt_list', extra_params={'path': 'movies/trending', 'media_type': 'movie'}),
        _menu_item('Popular', 'trakt_list', extra_params={'path': 'movies/popular', 'media_type': 'movie'}),
        _menu_item('Most Watched (Week)', 'trakt_list', extra_params={'path': 'movies/watched/weekly', 'media_type': 'movie'}),
        _menu_item('Most Watched (All Time)', 'trakt_list', extra_params={'path': 'movies/watched/all', 'media_type': 'movie'}),
        _menu_item('Box Office', 'tmdb_list', extra_params={'endpoint': 'now_playing', 'media_type': 'movie'}),
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
    ]
    for url, li, is_folder in items:
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)


# ── My Trakt Menu ────────────────────────────────────────────────────────

def my_trakt():
    if not trakt_auth.is_authorized():
        xbmcgui.Dialog().notification('Trakt', 'Please authorize Trakt first', xbmcgui.NOTIFICATION_WARNING)
        return
    items = [
        _menu_item('Movie Watchlist', 'trakt_list', extra_params={'path': 'sync/watchlist/movies', 'media_type': 'movie'}),
        _menu_item('Show Watchlist', 'trakt_list', extra_params={'path': 'sync/watchlist/shows', 'media_type': 'show'}),
        _menu_item('Movie Collection', 'trakt_list', extra_params={'path': 'sync/collection/movies', 'media_type': 'movie'}),
        _menu_item('Show Collection', 'trakt_list', extra_params={'path': 'sync/collection/shows', 'media_type': 'show'}),
        _menu_item('Watched Movies', 'trakt_list', extra_params={'path': 'sync/watched/movies', 'media_type': 'movie'}),
        _menu_item('Watched Shows', 'trakt_list', extra_params={'path': 'sync/watched/shows', 'media_type': 'show'}),
        _menu_item('Recently Watched Movies', 'history', extra_params={'media_type': 'movie'}),
        _menu_item('Recently Watched Episodes', 'history', extra_params={'media_type': 'show'}),
        _menu_item('My Calendar', 'calendar', extra_params={'media_type': 'show'}),
        _menu_item('My Custom Lists', 'my_lists'),
        _menu_item('Popular Lists', 'popular_lists'),
        _menu_item('Friends', 'friends'),
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
    qr_path = os.path.join(tempfile.gettempdir(), 'trakt_player_qr.png')
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
        # Real-Debrid: Show torrents and download history
        items.append(_menu_item('[COLOR cyan]📁 My Torrents[/COLOR]', 'cloud_rd_torrents'))
        items.append(_menu_item('[COLOR cyan]📥 Download History[/COLOR]', 'cloud_rd_downloads'))
    
    elif service == 'pm':
        # Premiumize: Show cloud files and transfers
        items.append(_menu_item('[COLOR cyan]📁 My Cloud Files[/COLOR]', 'cloud_pm_files'))
        items.append(_menu_item('[COLOR cyan]📥 Transfers[/COLOR]', 'cloud_pm_transfers'))
    
    elif service == 'tb':
        # Torbox: Show torrents
        items.append(_menu_item('[COLOR cyan]📁 My Torrents[/COLOR]', 'cloud_tb_torrents'))
    
    elif service == 'ad':
        # AllDebrid: Show magnets
        items.append(_menu_item('[COLOR cyan]📁 My Magnets[/COLOR]', 'cloud_ad_magnets'))
    
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
        
        # Format label with status
        if status == 'downloaded':
            label = f"[COLOR lime]✓[/COLOR] {item['name']} [{item['size']}]"
        elif status == 'downloading':
            label = f"[COLOR yellow]↓ {progress}%[/COLOR] {item['name']}"
        else:
            label = f"[COLOR gray]{status}[/COLOR] {item['name']}"
        
        url = build_url({'action': 'cloud_rd_torrent_files', 'torrent_id': item['id']})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': get_addon_icon(), 'thumb': get_addon_icon()})
        
        # Add context menu for delete
        li.addContextMenuItems([
            ('Delete', f"RunPlugin(plugin://plugin.video.trakt_player/?action=cloud_delete&service=rd&item_id={item['id']})")
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


def cloud_pm_files(folder_id=None):
    """List Premiumize cloud files"""
    items = debrid.pm_get_cloud_files(folder_id)
    
    if not items:
        xbmcgui.Dialog().notification('Premiumize', 'No files found', 
                                       xbmcgui.NOTIFICATION_INFO, 3000)
        return
    
    for item in items:
        if item.get('type') == 'folder':
            label = f"[COLOR cyan]📁[/COLOR] {item['name']}"
            url = build_url({'action': 'cloud_pm_files', 'folder_id': item['id']})
            is_folder = True
        else:
            label = f"{item['name']}"
            if item.get('size'):
                label += f" [{item['size']}]"
            url = build_url({'action': 'cloud_play_direct', 'link': item['link']})
            is_folder = False
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': get_addon_icon(), 'thumb': get_addon_icon()})
        
        if not is_folder and item.get('is_video'):
            li.setProperty('IsPlayable', 'true')
        
        # Add context menu for delete
        li.addContextMenuItems([
            ('Delete', f"RunPlugin(plugin://plugin.video.trakt_player/?action=cloud_delete&service=pm&item_id={item['id']})")
        ])
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_pm_transfers():
    """List Premiumize transfers"""
    items = debrid.pm_get_transfers()
    
    if not items:
        xbmcgui.Dialog().notification('Premiumize', 'No active transfers', 
                                       xbmcgui.NOTIFICATION_INFO, 3000)
        return
    
    for item in items:
        status = item.get('status', '')
        progress = item.get('progress', 0)
        
        if status == 'finished':
            label = f"[COLOR lime]✓[/COLOR] {item['name']}"
        else:
            label = f"[COLOR yellow]{progress}%[/COLOR] {item['name']} [{status}]"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': get_addon_icon(), 'thumb': get_addon_icon()})
        
        xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_tb_torrents():
    """List Torbox torrents"""
    items = debrid.tb_get_torrents()
    
    if not items:
        xbmcgui.Dialog().notification('Torbox', 'No torrents found', 
                                       xbmcgui.NOTIFICATION_INFO, 3000)
        return
    
    for item in items:
        status = item.get('status', '')
        progress = item.get('progress', 0)
        
        if status in ['completed', 'cached', 'seeding']:
            label = f"[COLOR lime]✓[/COLOR] {item['name']} [{item['size']}]"
        elif status == 'downloading':
            label = f"[COLOR yellow]↓ {progress}%[/COLOR] {item['name']}"
        else:
            label = f"[COLOR gray]{status}[/COLOR] {item['name']}"
        
        url = build_url({'action': 'cloud_tb_torrent_files', 'torrent_id': item['id']})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': get_addon_icon(), 'thumb': get_addon_icon()})
        
        # Add context menu for delete
        li.addContextMenuItems([
            ('Delete', f"RunPlugin(plugin://plugin.video.trakt_player/?action=cloud_delete&service=tb&item_id={item['id']})")
        ])
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_tb_torrent_files(torrent_id):
    """List files in a Torbox torrent"""
    files = debrid.tb_get_torrent_files(torrent_id)
    
    if not files:
        xbmcgui.Dialog().notification('Torbox', 'No files found', 
                                       xbmcgui.NOTIFICATION_INFO, 3000)
        return
    
    for f in files:
        label = f"{f['name']}"
        if f.get('size'):
            label += f" [{f['size']}]"
        
        url = build_url({'action': 'cloud_play_tb', 'torrent_id': torrent_id, 'file_id': str(f['id'])})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': get_addon_icon(), 'thumb': get_addon_icon()})
        
        if f.get('is_video'):
            li.setProperty('IsPlayable', 'true')
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_ad_magnets():
    """List AllDebrid magnets"""
    items = debrid.ad_get_magnets()
    
    if not items:
        xbmcgui.Dialog().notification('AllDebrid', 'No magnets found', 
                                       xbmcgui.NOTIFICATION_INFO, 3000)
        return
    
    for item in items:
        status = item.get('status', '')
        
        if status == 'Ready':
            label = f"[COLOR lime]✓[/COLOR] {item['name']} [{item['size']}]"
        else:
            label = f"[COLOR yellow]{status}[/COLOR] {item['name']}"
        
        url = build_url({'action': 'cloud_ad_magnet_files', 'magnet_id': item['id']})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': get_addon_icon(), 'thumb': get_addon_icon()})
        
        # Add context menu for delete
        li.addContextMenuItems([
            ('Delete', f"RunPlugin(plugin://plugin.video.trakt_player/?action=cloud_delete&service=ad&item_id={item['id']})")
        ])
        
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def cloud_ad_magnet_files(magnet_id):
    """List files in an AllDebrid magnet"""
    files = debrid.ad_get_magnet_files(magnet_id)
    
    if not files:
        xbmcgui.Dialog().notification('AllDebrid', 'No files found', 
                                       xbmcgui.NOTIFICATION_INFO, 3000)
        return
    
    for f in files:
        label = f"{f['name']}"
        if f.get('size'):
            label += f" [{f['size']}]"
        
        url = build_url({'action': 'cloud_play_ad', 'link': f['link']})
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': get_addon_icon(), 'thumb': get_addon_icon()})
        
        if f.get('is_video'):
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


def cloud_play_ad(link):
    """Play an AllDebrid link (unrestrict first)"""
    ad = debrid.AllDebrid()
    direct_url = ad.unrestrict_link(link)
    
    if direct_url:
        li = xbmcgui.ListItem(path=direct_url)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        xbmcgui.Dialog().notification('Error', 'Failed to get download link', 
                                       xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def cloud_play_tb(torrent_id, file_id):
    """Play a Torbox file"""
    direct_url = debrid.tb_get_download_link(torrent_id, int(file_id))
    
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
    elif action == 'open_settings':
        get_addon().openSettings()
    elif action == 'donate':
        show_donation()
    elif action == 'account_status':
        show_account_status()

    # Content - with pagination support
    elif action == 'list_genres':
        tmdb.get_genres(params.get('path'))
    elif action == 'trakt_list':
        page = params.get('page', '1')
        trakt_api.get_list(params.get('path'), params.get('media_type', 'movie'), page)
    elif action == 'tmdb_list':
        tmdb.show_tmdb_list(
            params.get('endpoint', 'now_playing'),
            params.get('media_type', 'movie'),
            params.get('page', '1')
        )
    elif action == 'tmdb_discover':
        tmdb.show_genre_discover(
            params.get('media_type', 'movie'),
            params.get('genre_id', ''),
            params.get('label', ''),
            params.get('page', '1')
        )
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
        trakt_api.rate_item(
            params.get('media_type', 'movie'),
            trakt_id=params.get('trakt_id') or None,
            imdb_id=params.get('imdb_id') or None,
        )
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

    # Playback - Use filehost (user's v2.1.6 engine) for main play, player.py for click-and-play
    elif action == 'play':
        # Try player.py first (our debrid click-and-play with cache check)
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
    elif action == 'cloud_pm_files':
        cloud_pm_files(params.get('folder_id'))
    elif action == 'cloud_pm_transfers':
        cloud_pm_transfers()
    elif action == 'cloud_tb_torrents':
        cloud_tb_torrents()
    elif action == 'cloud_tb_torrent_files':
        cloud_tb_torrent_files(params.get('torrent_id', ''))
    elif action == 'cloud_ad_magnets':
        cloud_ad_magnets()
    elif action == 'cloud_ad_magnet_files':
        cloud_ad_magnet_files(params.get('magnet_id', ''))
    elif action == 'cloud_play_rd':
        cloud_play_rd(params.get('link', ''))
    elif action == 'cloud_play_ad':
        cloud_play_ad(params.get('link', ''))
    elif action == 'cloud_play_tb':
        cloud_play_tb(params.get('torrent_id', ''), params.get('file_id', '0'))
    elif action == 'cloud_play_direct':
        cloud_play_direct(params.get('link', ''))
    elif action == 'cloud_delete':
        cloud_delete_item(params.get('service', ''), params.get('item_id', ''))
