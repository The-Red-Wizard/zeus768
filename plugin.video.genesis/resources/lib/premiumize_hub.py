# -*- coding: utf-8 -*-
"""
Premiumize Hub - rich UI for the Premiumize.me service
Mirrors the style of torbox_advanced.TorboxAdvanced and exposes the full
Premiumize API surface (folders, items, transfers, ZIP, services).
"""
import os
import sys
import time

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs
from urllib.parse import urlencode

from resources.lib import debrid


# ──────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────
def _fmt_size(num):
    try:
        num = float(num)
    except Exception:
        return '0 B'
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(num) < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} PB"


def _fmt_speed(num):
    return f"{_fmt_size(num)}/s" if num else ''


def _fmt_eta(seconds):
    try:
        s = int(seconds or 0)
    except Exception:
        return ''
    if s <= 0:
        return ''
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    return f"{s // 3600}h {(s % 3600) // 60}m"


def progress_bar(pct, width=15):
    try:
        pct = max(0, min(100, int(pct)))
    except Exception:
        pct = 0
    filled = int(round(pct / 100.0 * width))
    return '[' + '█' * filled + '░' * (width - filled) + f"] {pct}%"


def format_transfer_status(tr):
    """Build a human readable status line for a PM transfer dict."""
    raw = tr.get('status', '') or ''
    msg = tr.get('message', '') or ''
    pct = tr.get('progress', 0) or 0
    try:
        pct = float(pct)
    except Exception:
        pct = 0
    pct = int(pct * 100) if pct <= 1 else int(pct)
    if raw == 'finished':
        return f"[COLOR lime]FINISHED[/COLOR] {progress_bar(100)}"
    if raw in ('running', 'downloading'):
        bits = [f"[COLOR yellow]{progress_bar(pct)}[/COLOR]"]
        if msg:
            bits.append(f"[COLOR grey]{msg}[/COLOR]")
        return ' '.join(bits)
    if raw == 'queued':
        return "[COLOR cyan]QUEUED[/COLOR]"
    if raw == 'waiting':
        return f"[COLOR cyan]WAITING[/COLOR] {progress_bar(pct)}"
    if raw == 'error':
        return f"[COLOR red]ERROR[/COLOR] {msg}"
    if raw == 'timeout':
        return f"[COLOR red]TIMEOUT[/COLOR] {msg}"
    if raw == 'banned':
        return f"[COLOR red]BANNED[/COLOR] {msg}"
    if raw == 'seeding':
        return "[COLOR lime]SEEDING[/COLOR]"
    return f"[COLOR grey]{raw or 'unknown'}[/COLOR] {progress_bar(pct)}"


# ──────────────────────────────────────────────────────────────────────────
# URL builder (kept here so we don't depend on main.build_url)
# ──────────────────────────────────────────────────────────────────────────
def _addon_handle():
    return int(sys.argv[1]) if len(sys.argv) > 1 else -1


def _base_url():
    return sys.argv[0] if len(sys.argv) > 0 else 'plugin://plugin.video.genesis/'


def build_url(params):
    return f"{_base_url()}?{urlencode(params)}"


def _addon_icon():
    addon_path = xbmcvfs.translatePath('special://home/addons/plugin.video.genesis/')
    return os.path.join(addon_path, 'icon.png')


def _addon_fanart():
    addon_path = xbmcvfs.translatePath('special://home/addons/plugin.video.genesis/')
    return os.path.join(addon_path, 'fanart.jpg')


VIDEO_EXTS = ('.mkv', '.mp4', '.avi', '.mov', '.m4v', '.ts', '.m2ts',
              '.wmv', '.flv', '.webm', '.mpg', '.mpeg', '.iso')


def _is_video(name):
    n = (name or '').lower()
    return n.endswith(VIDEO_EXTS)


# ──────────────────────────────────────────────────────────────────────────
# HUB MAIN MENU
# ──────────────────────────────────────────────────────────────────────────
def pm_hub():
    """Top-level Premiumize Hub menu."""
    pm = debrid.Premiumize()
    handle = _addon_handle()

    if not pm.is_authorized():
        xbmcgui.Dialog().notification('Premiumize',
                                      'Not authorized - link your account first',
                                      xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(handle)
        return

    info = pm.account_info() or {}
    is_premium = info.get('premium', False)
    days = info.get('days_left', 0)
    used = _fmt_size(info.get('space_used', 0))
    cust = info.get('username', '')

    tag = '[COLOR lime]PREMIUM[/COLOR]' if is_premium else '[COLOR orange]FREE[/COLOR]'
    header = (f"[B]Premiumize Hub[/B]  -  Customer {cust}  -  {tag}  "
              f"-  {days} days left  -  {used} used")

    items = [
        (header, 'pm_account_dashboard'),
        ('[B][COLOR cyan]>> Cloud Files[/COLOR][/B]  (browse, rename, delete, ZIP)', 'pm_cloud_folder'),
        ('[B][COLOR cyan]>> Transfers[/COLOR][/B]  (live progress, manage queue)', 'pm_transfers'),
        ('[B][COLOR lime]+ Add Transfer[/COLOR][/B]  (Magnet · Torrent URL · DDL · NZB)', 'pm_add_transfer_menu'),
        ('[COLOR yellow]Recent Files (all, recursive)[/COLOR]', 'pm_listall'),
        ('[COLOR yellow]Supported Hosters[/COLOR]', 'pm_services'),
        ('[COLOR grey]Clear Finished Transfers[/COLOR]', 'pm_clear_finished'),
        ('[COLOR red]Unlink Premiumize[/COLOR]', 'revoke_pm'),
    ]

    for label, action in items:
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': _addon_icon(), 'thumb': _addon_icon(),
                   'fanart': _addon_fanart()})
        is_folder = action not in ('pm_account_dashboard', 'pm_clear_finished',
                                   'revoke_pm')
        url = build_url({'action': action})
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(handle)


def pm_account_dashboard():
    """Account dialog with detailed info."""
    pm = debrid.Premiumize()
    info = pm.account_info() or {}
    is_premium = info.get('premium', False)
    tag = 'PREMIUM' if is_premium else 'FREE'
    msg = (f"[B]Premiumize Account[/B]\n\n"
           f"Customer ID: {info.get('username', 'n/a')}\n"
           f"Status: {tag}\n"
           f"Expires: {info.get('expiration', 'n/a')}\n"
           f"Days left: {info.get('days_left', 0)}\n"
           f"Space used: {_fmt_size(info.get('space_used', 0))}\n"
           f"Fair-use used: {info.get('limit_used', 0)}\n")
    xbmcgui.Dialog().textviewer('Premiumize Account', msg)


# ──────────────────────────────────────────────────────────────────────────
# CLOUD FILES
# ──────────────────────────────────────────────────────────────────────────
def pm_cloud_folder(folder_id='', breadcrumb=''):
    """Browse a Premiumize folder."""
    pm = debrid.Premiumize()
    handle = _addon_handle()
    if not pm.is_authorized():
        xbmcplugin.endOfDirectory(handle)
        return

    data = pm.folder_list(folder_id or None)
    if not data:
        xbmcgui.Dialog().notification('Premiumize', 'Failed to load folder',
                                      xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(handle)
        return

    parent_id = data.get('parent_id') or ''
    crumbs = data.get('breadcrumbs') or []
    content = data.get('content', [])

    # Crumb header
    if crumbs:
        crumb_text = ' / '.join([c.get('name', '') for c in crumbs])
        li = xbmcgui.ListItem(label=f"[COLOR grey]Path:[/COLOR] [B]{crumb_text}[/B]")
        li.setArt({'icon': _addon_icon()})
        xbmcplugin.addDirectoryItem(handle, '', li, isFolder=False)

    # Parent / Up
    if folder_id:
        up_id = parent_id or ''
        li = xbmcgui.ListItem(label='[COLOR cyan].. (Up)[/COLOR]')
        li.setArt({'icon': _addon_icon()})
        url = build_url({'action': 'pm_cloud_folder', 'folder_id': up_id})
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)

    # Action button: New Folder
    new_folder_url = build_url({'action': 'pm_create_folder',
                                'parent_id': folder_id or '0'})
    li = xbmcgui.ListItem(label='[COLOR lime]+ New Folder[/COLOR]')
    li.setArt({'icon': _addon_icon()})
    xbmcplugin.addDirectoryItem(handle, new_folder_url, li, isFolder=False)

    # Sort: folders first, then files
    folders = [x for x in content if x.get('type') == 'folder']
    files = [x for x in content if x.get('type') != 'folder']

    for f in folders:
        fid = f.get('id', '')
        name = f.get('name', '')
        label = f"[COLOR cyan][FOLDER][/COLOR] {name}"
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': _addon_icon(), 'thumb': _addon_icon(),
                   'fanart': _addon_fanart()})
        url = build_url({'action': 'pm_cloud_folder', 'folder_id': fid})
        ctx = [
            ('Rename folder',
             f"RunPlugin({build_url({'action': 'pm_rename_folder', 'folder_id': fid, 'old_name': name})})"),
            ('Delete folder',
             f"RunPlugin({build_url({'action': 'pm_delete_folder', 'folder_id': fid})})"),
            ('Move to...',
             f"RunPlugin({build_url({'action': 'pm_move_picker', 'folder_id_to_move': fid})})"),
            ('Download as ZIP',
             f"RunPlugin({build_url({'action': 'pm_zip_download', 'folder_ids': fid})})"),
        ]
        li.addContextMenuItems(ctx)
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)

    for it in files:
        iid = it.get('id', '')
        name = it.get('name', '')
        size = _fmt_size(it.get('size', 0))
        link = it.get('link', '') or it.get('stream_link', '') or ''
        playable = _is_video(name)

        icon = '[COLOR lime][VIDEO][/COLOR]' if playable else '[COLOR orange][FILE][/COLOR]'
        label = f"{icon} {name}  [COLOR grey][{size}][/COLOR]"
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': _addon_icon(), 'thumb': _addon_icon(),
                   'fanart': _addon_fanart()})
        if playable:
            li.setProperty('IsPlayable', 'true')
            li.setInfo('video', {'title': name, 'size': it.get('size', 0)})
            url = build_url({'action': 'pm_play_link', 'link': link, 'item_id': iid})
            is_folder = False
        else:
            url = build_url({'action': 'pm_item_details', 'item_id': iid})
            is_folder = False

        ctx = [
            ('Item details',
             f"RunPlugin({build_url({'action': 'pm_item_details', 'item_id': iid})})"),
            ('Rename file',
             f"RunPlugin({build_url({'action': 'pm_rename_item', 'item_id': iid, 'old_name': name})})"),
            ('Delete file',
             f"RunPlugin({build_url({'action': 'pm_delete_item', 'item_id': iid})})"),
            ('Move to...',
             f"RunPlugin({build_url({'action': 'pm_move_picker', 'item_id_to_move': iid})})"),
            ('Download as ZIP',
             f"RunPlugin({build_url({'action': 'pm_zip_download', 'item_ids': iid})})"),
            ('Copy direct URL to clipboard',
             f"RunPlugin({build_url({'action': 'pm_copy_link', 'link': link})})"),
        ]
        li.addContextMenuItems(ctx)
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=is_folder)

    xbmcplugin.setContent(handle, 'files')
    xbmcplugin.endOfDirectory(handle)


def pm_listall():
    """Recursive flat list of all files in the cloud."""
    pm = debrid.Premiumize()
    handle = _addon_handle()
    files = pm.item_listall()
    if not files:
        xbmcgui.Dialog().notification('Premiumize', 'No files',
                                      xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(handle)
        return
    # Most recent first if created_at present
    try:
        files.sort(key=lambda x: x.get('created_at', 0) or 0, reverse=True)
    except Exception:
        pass
    for it in files[:500]:
        iid = it.get('id', '')
        name = it.get('name') or it.get('path') or ''
        size = _fmt_size(it.get('size', 0))
        link = it.get('link', '') or ''
        playable = _is_video(name)
        icon = '[COLOR lime][V][/COLOR]' if playable else '[COLOR orange][F][/COLOR]'
        label = f"{icon} {name}  [COLOR grey][{size}][/COLOR]"
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': _addon_icon(), 'thumb': _addon_icon()})
        if playable:
            li.setProperty('IsPlayable', 'true')
            url = build_url({'action': 'pm_play_link', 'link': link, 'item_id': iid})
        else:
            url = build_url({'action': 'pm_item_details', 'item_id': iid})
        li.addContextMenuItems([
            ('Delete', f"RunPlugin({build_url({'action': 'pm_delete_item', 'item_id': iid})})"),
            ('Rename', f"RunPlugin({build_url({'action': 'pm_rename_item', 'item_id': iid, 'old_name': name})})"),
        ])
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=False)
    xbmcplugin.setContent(handle, 'files')
    xbmcplugin.endOfDirectory(handle)


def pm_item_details(item_id):
    pm = debrid.Premiumize()
    info = pm.item_details(item_id)
    if not info:
        xbmcgui.Dialog().notification('Premiumize', 'No details',
                                      xbmcgui.NOTIFICATION_ERROR)
        return
    msg = (f"[B]{info.get('name', '')}[/B]\n\n"
           f"ID: {info.get('id', '')}\n"
           f"Type: {info.get('type', '')}\n"
           f"Size: {_fmt_size(info.get('size', 0))}\n"
           f"Created: {info.get('created_at', '')}\n"
           f"MIME: {info.get('mime_type', '')}\n"
           f"Transcode status: {info.get('transcode_status', '')}\n"
           f"Virus scan: {info.get('virus_scan', '')}\n"
           f"Link: {info.get('link', '')}\n"
           f"Stream link: {info.get('stream_link', '')}\n")
    xbmcgui.Dialog().textviewer('Premiumize Item', msg)


# ──────────────────────────────────────────────────────────────────────────
# TRANSFERS
# ──────────────────────────────────────────────────────────────────────────
def pm_transfers():
    pm = debrid.Premiumize()
    handle = _addon_handle()
    transfers = pm.transfer_list() or []
    if not transfers:
        xbmcgui.Dialog().notification('Premiumize', 'No transfers',
                                      xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(handle)
        return

    # Order: running first, then queued/waiting, then finished, then errors
    order = {'running': 0, 'downloading': 0, 'waiting': 1, 'queued': 2,
             'seeding': 3, 'finished': 4, 'error': 5, 'timeout': 6, 'banned': 7}
    transfers.sort(key=lambda t: order.get((t.get('status') or '').lower(), 9))

    for tr in transfers:
        tid = tr.get('id', '')
        name = tr.get('name', '') or '(unnamed)'
        status_line = format_transfer_status(tr)
        size_txt = ''
        if tr.get('size'):
            size_txt = f"[COLOR grey][{_fmt_size(tr.get('size'))}][/COLOR]"
        label = f"{status_line}  [B]{name}[/B]  {size_txt}".strip()
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': _addon_icon(), 'thumb': _addon_icon()})

        folder_id = tr.get('folder_id', '') or ''
        file_id = tr.get('file_id', '') or ''
        status = (tr.get('status') or '').lower()

        # Default action: if finished and we have a folder, browse it; else show details
        if status == 'finished' and folder_id:
            url = build_url({'action': 'pm_cloud_folder', 'folder_id': folder_id})
            is_folder = True
        elif status == 'finished' and file_id:
            url = build_url({'action': 'pm_item_details', 'item_id': file_id})
            is_folder = False
        else:
            url = build_url({'action': 'pm_transfers'})
            is_folder = False

        ctx = [
            ('Refresh',
             "Container.Refresh"),
            ('Delete transfer',
             f"RunPlugin({build_url({'action': 'pm_delete_transfer', 'transfer_id': tid})})"),
        ]
        if folder_id:
            ctx.insert(1, ('Open destination folder',
                           f"Container.Update({build_url({'action': 'pm_cloud_folder', 'folder_id': folder_id})})"))
        if file_id:
            ctx.insert(1, ('Play resulting file',
                           f"PlayMedia({build_url({'action': 'pm_play_item', 'item_id': file_id})})"))
        li.addContextMenuItems(ctx)
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(handle)


def pm_add_transfer_menu():
    """Submenu: choose what type of transfer to add."""
    handle = _addon_handle()
    items = [
        ('[COLOR lime]+ Add Magnet Link[/COLOR]', 'pm_add_magnet'),
        ('[COLOR lime]+ Add Torrent URL or DDL[/COLOR]', 'pm_add_url'),
        ('[COLOR lime]+ Add NZB URL[/COLOR]', 'pm_add_nzb'),
    ]
    for label, action in items:
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': _addon_icon()})
        url = build_url({'action': action})
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder=False)
    xbmcplugin.endOfDirectory(handle)


def pm_add_transfer(prompt_text, default=''):
    """Generic prompt + transfer/create."""
    pm = debrid.Premiumize()
    src = xbmcgui.Dialog().input(prompt_text, defaultt=default,
                                 type=xbmcgui.INPUT_ALPHANUM)
    if not src:
        return
    res = pm.transfer_create(src.strip())
    if res:
        name = res.get('name') or src[:60]
        xbmcgui.Dialog().notification('Premiumize',
                                      f"Added: {name}",
                                      xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Premiumize',
                                      'Failed to add transfer',
                                      xbmcgui.NOTIFICATION_ERROR)


def pm_add_magnet():
    pm_add_transfer('Paste magnet link (magnet:?xt=...)')


def pm_add_url():
    pm_add_transfer('Paste torrent .torrent URL or hoster URL')


def pm_add_nzb():
    pm_add_transfer('Paste NZB URL')


def pm_delete_transfer(transfer_id):
    if not xbmcgui.Dialog().yesno('Premiumize', 'Delete this transfer?'):
        return
    pm = debrid.Premiumize()
    if pm.transfer_delete(transfer_id):
        xbmcgui.Dialog().notification('Premiumize', 'Transfer deleted',
                                      xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Premiumize',
                                      'Delete failed',
                                      xbmcgui.NOTIFICATION_ERROR)


def pm_clear_finished():
    if not xbmcgui.Dialog().yesno('Premiumize',
                                  'Clear ALL finished transfers from the list?'):
        return
    pm = debrid.Premiumize()
    if pm.transfer_clearfinished():
        xbmcgui.Dialog().notification('Premiumize', 'Finished transfers cleared',
                                      xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Premiumize',
                                      'Clear failed',
                                      xbmcgui.NOTIFICATION_ERROR)


# ──────────────────────────────────────────────────────────────────────────
# FOLDER & ITEM MANAGEMENT (interactive)
# ──────────────────────────────────────────────────────────────────────────
def pm_create_folder(parent_id='0'):
    name = xbmcgui.Dialog().input('Folder name', type=xbmcgui.INPUT_ALPHANUM)
    if not name:
        return
    pm = debrid.Premiumize()
    pid = None if parent_id in ('', '0') else parent_id
    if pm.folder_create(name, pid):
        xbmcgui.Dialog().notification('Premiumize', f"Folder created: {name}",
                                      xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Premiumize', 'Create folder failed',
                                      xbmcgui.NOTIFICATION_ERROR)


def pm_rename_folder(folder_id, old_name=''):
    new_name = xbmcgui.Dialog().input('New folder name', defaultt=old_name,
                                      type=xbmcgui.INPUT_ALPHANUM)
    if not new_name or new_name == old_name:
        return
    pm = debrid.Premiumize()
    if pm.folder_rename(folder_id, new_name):
        xbmcgui.Dialog().notification('Premiumize', 'Folder renamed',
                                      xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Premiumize', 'Rename failed',
                                      xbmcgui.NOTIFICATION_ERROR)


def pm_rename_item(item_id, old_name=''):
    new_name = xbmcgui.Dialog().input('New file name', defaultt=old_name,
                                      type=xbmcgui.INPUT_ALPHANUM)
    if not new_name or new_name == old_name:
        return
    pm = debrid.Premiumize()
    if pm.item_rename(item_id, new_name):
        xbmcgui.Dialog().notification('Premiumize', 'File renamed',
                                      xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Premiumize', 'Rename failed',
                                      xbmcgui.NOTIFICATION_ERROR)


def pm_delete_folder(folder_id):
    if not xbmcgui.Dialog().yesno('Premiumize',
                                  'Delete this folder and ALL its contents?'):
        return
    pm = debrid.Premiumize()
    if pm.folder_delete(folder_id):
        xbmcgui.Dialog().notification('Premiumize', 'Folder deleted',
                                      xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Premiumize', 'Delete failed',
                                      xbmcgui.NOTIFICATION_ERROR)


def pm_delete_item(item_id):
    if not xbmcgui.Dialog().yesno('Premiumize', 'Delete this file?'):
        return
    pm = debrid.Premiumize()
    if pm.item_delete(item_id):
        xbmcgui.Dialog().notification('Premiumize', 'File deleted',
                                      xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Premiumize', 'Delete failed',
                                      xbmcgui.NOTIFICATION_ERROR)


def pm_move_picker(item_id_to_move='', folder_id_to_move=''):
    """Pick a destination folder, then call folder/paste."""
    pm = debrid.Premiumize()
    # Show a flat list of folders to move into
    data = pm.folder_list()
    if not data:
        xbmcgui.Dialog().notification('Premiumize', 'Could not load folders',
                                      xbmcgui.NOTIFICATION_ERROR)
        return
    folders = [('(Root)', '0')]
    for it in data.get('content', []):
        if it.get('type') == 'folder':
            folders.append((it.get('name', ''), it.get('id', '')))
    if len(folders) == 1:
        xbmcgui.Dialog().notification('Premiumize',
                                      'No folders to move into',
                                      xbmcgui.NOTIFICATION_WARNING)
        return
    idx = xbmcgui.Dialog().select('Move to folder',
                                  [f[0] for f in folders])
    if idx < 0:
        return
    target = folders[idx][1]
    item_ids = [item_id_to_move] if item_id_to_move else []
    folder_ids = [folder_id_to_move] if folder_id_to_move else []
    if pm.folder_paste(target, item_ids=item_ids, folder_ids=folder_ids):
        xbmcgui.Dialog().notification('Premiumize', 'Moved',
                                      xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
    else:
        xbmcgui.Dialog().notification('Premiumize', 'Move failed',
                                      xbmcgui.NOTIFICATION_ERROR)


# ──────────────────────────────────────────────────────────────────────────
# ZIP DOWNLOAD
# ──────────────────────────────────────────────────────────────────────────
def pm_zip_download(item_ids='', folder_ids=''):
    pm = debrid.Premiumize()
    items = [x for x in item_ids.split(',') if x] if item_ids else []
    folders = [x for x in folder_ids.split(',') if x] if folder_ids else []
    if not items and not folders:
        xbmcgui.Dialog().notification('Premiumize', 'Nothing selected',
                                      xbmcgui.NOTIFICATION_WARNING)
        return
    url = pm.zip_generate(item_ids=items, folder_ids=folders)
    if not url:
        xbmcgui.Dialog().notification('Premiumize', 'ZIP creation failed',
                                      xbmcgui.NOTIFICATION_ERROR)
        return
    xbmcgui.Dialog().textviewer(
        'Premiumize ZIP',
        f"Your ZIP is ready.\n\nDownload URL:\n\n{url}\n\n"
        "(URL copied below - long-press to copy in skins that support it.)"
    )


# ──────────────────────────────────────────────────────────────────────────
# SUPPORTED HOSTERS
# ──────────────────────────────────────────────────────────────────────────
def pm_services():
    pm = debrid.Premiumize()
    handle = _addon_handle()
    info = pm.services_list() or {}
    if not info:
        xbmcgui.Dialog().notification('Premiumize',
                                      'Could not load services list',
                                      xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(handle)
        return
    # services/list returns dicts keyed by hoster, with regexpresions etc.
    direct = info.get('directdl', []) or []
    cache = info.get('cache', []) or []
    queue = info.get('queue', []) or []
    fairuse = info.get('fairuse_factor', {}) or {}
    aliases = info.get('aliases', {}) or {}

    li = xbmcgui.ListItem(label=f"[B]Direct download hosters[/B]  "
                                 f"[COLOR grey]({len(direct)})[/COLOR]")
    li.setArt({'icon': _addon_icon()})
    xbmcplugin.addDirectoryItem(handle, '', li, isFolder=False)
    for host in sorted(direct):
        fu = fairuse.get(host, 1.0)
        in_cache = host in cache
        in_queue = host in queue
        badges = []
        if in_cache:
            badges.append('[COLOR lime]CACHE[/COLOR]')
        if in_queue:
            badges.append('[COLOR yellow]QUEUE[/COLOR]')
        if fu and fu != 1.0:
            badges.append(f"[COLOR orange]FU x{fu}[/COLOR]")
        alias_list = aliases.get(host, []) or []
        alias_str = ''
        if alias_list:
            alias_str = f"  [COLOR grey]({', '.join(alias_list[:3])})[/COLOR]"
        label = f"{host} {' '.join(badges)}{alias_str}"
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': _addon_icon()})
        xbmcplugin.addDirectoryItem(handle, '', li, isFolder=False)
    xbmcplugin.endOfDirectory(handle)


# ──────────────────────────────────────────────────────────────────────────
# PLAYBACK
# ──────────────────────────────────────────────────────────────────────────
def pm_play_link(link, item_id=''):
    """Play a direct Premiumize link. Uses the link directly (already direct)."""
    handle = _addon_handle()
    if not link and item_id:
        pm = debrid.Premiumize()
        info = pm.item_details(item_id)
        link = info.get('stream_link') or info.get('link') or ''
    if not link:
        xbmcgui.Dialog().notification('Premiumize',
                                      'Could not resolve link',
                                      xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return
    li = xbmcgui.ListItem(path=link)
    li.setProperty('IsPlayable', 'true')
    xbmcplugin.setResolvedUrl(handle, True, li)


def pm_play_item(item_id):
    """Play a cloud item by id - resolves to direct link first."""
    pm = debrid.Premiumize()
    info = pm.item_details(item_id)
    link = info.get('stream_link') or info.get('link') or ''
    pm_play_link(link, item_id)


def pm_copy_link(link):
    """Show the direct URL in a dialog (xbmc has no native clipboard)."""
    if not link:
        xbmcgui.Dialog().notification('Premiumize', 'No link to copy',
                                      xbmcgui.NOTIFICATION_WARNING)
        return
    xbmcgui.Dialog().textviewer('Premiumize Direct Link', link)


# ──────────────────────────────────────────────────────────────────────────
# "Send to Premiumize Cloud" - generic from source picker
# ──────────────────────────────────────────────────────────────────────────
def send_to_pm(src, label=''):
    """Public helper that other modules can call to push a magnet/URL into PM."""
    pm = debrid.Premiumize()
    if not pm.is_authorized():
        xbmcgui.Dialog().notification('Premiumize',
                                      'Authorize Premiumize first',
                                      xbmcgui.NOTIFICATION_WARNING)
        return False
    res = pm.transfer_create(src)
    if res:
        xbmcgui.Dialog().notification('Premiumize',
                                      f"Sent: {label or res.get('name','')}",
                                      xbmcgui.NOTIFICATION_INFO)
        return True
    xbmcgui.Dialog().notification('Premiumize',
                                  'Failed to send to cloud',
                                  xbmcgui.NOTIFICATION_ERROR)
    return False
