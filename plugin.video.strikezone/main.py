import sys
import os
import json
import urllib.parse
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
sys.path.append(os.path.join(ADDON_PATH, 'resources', 'lib'))

import scraper

# Paths
FANART = os.path.join(ADDON_PATH, 'fanart.jpg')
ICON = os.path.join(ADDON_PATH, 'icon.png')
MEDIA_PATH = os.path.join(ADDON_PATH, 'resources', 'media')
CATEGORY_IMAGES_PATH = os.path.join(ADDON_PATH, 'resources', 'media', 'categories')
FAVOURITES_FILE = os.path.join(ADDON_PROFILE, 'favourites.json')
HISTORY_FILE = os.path.join(ADDON_PROFILE, 'history.json')
MAX_HISTORY = 50  # Keep last 50 watched items

def build_url(query):
    return sys.argv[0] + '?' + urllib.parse.urlencode(query)

def ensure_dir(path):
    """Ensure directory exists"""
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)

def get_category_image(slug):
    """Get category image or return default fanart"""
    # Check for custom category image
    for ext in ['png', 'jpg', 'jpeg']:
        img_path = os.path.join(CATEGORY_IMAGES_PATH, f'{slug}.{ext}')
        if xbmcvfs.exists(img_path):
            return img_path
    # Return fanart as default
    return FANART

def load_favourites():
    """Load favourites from file"""
    ensure_dir(ADDON_PROFILE)
    if xbmcvfs.exists(FAVOURITES_FILE):
        try:
            with xbmcvfs.File(FAVOURITES_FILE, 'r') as f:
                return json.loads(f.read())
        except:
            pass
    return []

def save_favourites(favourites):
    """Save favourites to file"""
    ensure_dir(ADDON_PROFILE)
    try:
        with xbmcvfs.File(FAVOURITES_FILE, 'w') as f:
            f.write(json.dumps(favourites, indent=2))
        return True
    except:
        return False

def add_to_favourites(title, url, icon, category='', description=''):
    """Add a fight to favourites"""
    favourites = load_favourites()
    # Check if already exists
    for fav in favourites:
        if fav.get('url') == url:
            xbmcgui.Dialog().notification('Strike Zone', 'Already in Favourites', xbmcgui.NOTIFICATION_INFO)
            return False
    
    favourites.append({
        'title': title,
        'url': url,
        'icon': icon,
        'category': category,
        'description': description
    })
    
    if save_favourites(favourites):
        xbmcgui.Dialog().notification('Strike Zone', 'Added to Favourites', xbmcgui.NOTIFICATION_INFO)
        return True
    return False

def remove_from_favourites(url):
    """Remove a fight from favourites"""
    favourites = load_favourites()
    favourites = [f for f in favourites if f.get('url') != url]
    if save_favourites(favourites):
        xbmcgui.Dialog().notification('Strike Zone', 'Removed from Favourites', xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')
        return True
    return False

def load_history():
    """Load watch history from file"""
    ensure_dir(ADDON_PROFILE)
    if xbmcvfs.exists(HISTORY_FILE):
        try:
            with xbmcvfs.File(HISTORY_FILE, 'r') as f:
                return json.loads(f.read())
        except:
            pass
    return []

def save_history(history):
    """Save watch history to file"""
    ensure_dir(ADDON_PROFILE)
    try:
        with xbmcvfs.File(HISTORY_FILE, 'w') as f:
            f.write(json.dumps(history, indent=2))
        return True
    except:
        return False

def add_to_history(title, url, icon, category=''):
    """Add a fight to watch history"""
    history = load_history()
    
    # Remove if already exists (will be re-added at top)
    history = [h for h in history if h.get('url') != url]
    
    # Add to beginning
    history.insert(0, {
        'title': title,
        'url': url,
        'icon': icon,
        'category': category,
        'timestamp': str(int(__import__('time').time()))
    })
    
    # Keep only MAX_HISTORY items
    history = history[:MAX_HISTORY]
    
    save_history(history)

def clear_history():
    """Clear all watch history"""
    if save_history([]):
        xbmcgui.Dialog().notification('Strike Zone', 'History Cleared', xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')

def clear_favourites():
    """Clear all favourites"""
    if save_favourites([]):
        xbmcgui.Dialog().notification('Strike Zone', 'Favourites Cleared', xbmcgui.NOTIFICATION_INFO)
        xbmc.executebuiltin('Container.Refresh')

def create_list_item(title, icon='', fanart='', info=None, is_folder=True, is_playable=False):
    """Create a list item with proper art and info"""
    li = xbmcgui.ListItem(title)
    
    # Set art
    art = {
        'thumb': icon if icon else ICON,
        'icon': icon if icon else ICON,
        'fanart': fanart if fanart else FANART,
        'poster': icon if icon else ICON
    }
    li.setArt(art)
    
    # Set info
    if info:
        li.setInfo('video', info)
    
    if is_playable:
        li.setProperty('IsPlayable', 'true')
    
    return li

def run():
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    action = params.get('action')

    if not action:
        # Main Menu
        xbmcplugin.setContent(HANDLE, 'videos')
        
        # Categories
        li = create_list_item('[B]Categories[/B]', icon=ICON, fanart=FANART)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'list_cats'}), li, True)
        
        # Search
        li = create_list_item('[B]Search[/B]', icon=ICON, fanart=FANART)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'search'}), li, True)
        
        # Favourites
        li = create_list_item('[COLOR gold][B]⭐ Favourites[/B][/COLOR]', icon=ICON, fanart=FANART)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'favourites'}), li, True)
        
        # Recently Watched (History)
        li = create_list_item('[COLOR cyan][B]🕐 Recently Watched[/B][/COLOR]', icon=ICON, fanart=FANART)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'history'}), li, True)
        
        # Donate/Support
        li = create_list_item('[COLOR lime][B]🍺 Support zeus768 (Buy Me a Beer)[/B][/COLOR]', icon=os.path.join(MEDIA_PATH, 'qrcode.png'), fanart=FANART)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'donate'}), li, False)
        
        xbmcplugin.endOfDirectory(HANDLE)

    elif action == 'list_cats':
        # List all categories
        xbmcplugin.setContent(HANDLE, 'videos')
        categories = scraper.get_categories()
        
        for cat in categories:
            # Use custom category image or fanart
            cat_image = get_category_image(cat.get('slug', cat['title'].lower()))
            
            li = create_list_item(
                f"[B]{cat['title']}[/B]",
                icon=cat_image,
                fanart=FANART,
                info={'title': cat['title'], 'plot': f"Browse {cat['title']} fights"}
            )
            xbmcplugin.addDirectoryItem(
                HANDLE,
                build_url({'action': 'list_fights', 'url': cat['url'], 'page': '1', 'cat_title': cat['title']}),
                li, True
            )
        
        xbmcplugin.endOfDirectory(HANDLE)

    elif action == 'list_fights':
        # List fights with infinite scroll (pagination)
        xbmcplugin.setContent(HANDLE, 'videos')
        url = params.get('url', '')
        page = int(params.get('page', 1))
        cat_title = params.get('cat_title', '')
        
        fights, next_page = scraper.get_fights(url, page)
        
        for f in fights:
            # Create context menu for favourites
            context_menu = [
                ('Add to Favourites', f"RunPlugin({build_url({'action': 'add_fav', 'title': f['title'], 'url': f['url'], 'icon': f['icon'], 'category': f.get('category', ''), 'description': f.get('description', '')})})")
            ]
            
            li = create_list_item(
                f['title'],
                icon=f['icon'],
                fanart=FANART,
                info={
                    'title': f['title'],
                    'plot': f.get('description', f"Views: {f.get('views', 'N/A')} | Rating: {f.get('rating', 'N/A')}"),
                    'genre': f.get('category', ''),
                    'rating': float(f.get('rating', 0)) if f.get('rating') else 0
                }
            )
            li.addContextMenuItems(context_menu)
            
            xbmcplugin.addDirectoryItem(
                HANDLE,
                build_url({'action': 'get_links', 'url': f['url'], 'title': f['title'], 'icon': f['icon']}),
                li, True
            )
        
        # Infinite scroll - Next page
        if next_page:
            li = create_list_item(
                f'[COLOR yellow][B]>>> Load More (Page {next_page}) >>>[/B][/COLOR]',
                icon=ICON,
                fanart=FANART
            )
            xbmcplugin.addDirectoryItem(
                HANDLE,
                build_url({'action': 'list_fights', 'url': url, 'page': str(next_page), 'cat_title': cat_title}),
                li, True
            )
        
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

    elif action == 'get_links':
        # Get video links for a fight
        xbmcplugin.setContent(HANDLE, 'videos')
        url = params.get('url', '')
        title = params.get('title', 'Fight')
        icon = params.get('icon', '')
        
        # Get fight details
        details = scraper.get_fight_details(url)
        
        # Get video links
        links = scraper.get_video_links(url)
        
        if not links:
            xbmcgui.Dialog().notification('Strike Zone', 'No video links found', xbmcgui.NOTIFICATION_WARNING)
            xbmcplugin.endOfDirectory(HANDLE)
            return
        
        # Group links by section for display
        current_section = None
        
        for link in links:
            section = link.get('section', 'Main Event')
            server_num = link.get('server_num', 1)
            host = link.get('host', 'Video')
            
            # Add section header if new section
            if section != current_section:
                current_section = section
                # Add a non-playable header item
                header_li = xbmcgui.ListItem(f"[B][COLOR white]--- {section} ---[/COLOR][/B]")
                header_li.setProperty('IsPlayable', 'false')
                xbmcplugin.addDirectoryItem(HANDLE, '', header_li, False)
            
            # Color coding: Server 1 = dodgerblue, Server 2 = gold, others = white
            if server_num == 1:
                color = 'dodgerblue'
            elif server_num == 2:
                color = 'gold'
            else:
                color = 'lime'
            
            # Format label with colors
            label = f"[COLOR {color}]Server #{server_num}[/COLOR] [{host}]"
            
            # Handle parts (like Dailymotion)
            if link.get('part'):
                label = f"[COLOR {color}]{link['part']}[/COLOR] [{host}]"
            
            li = create_list_item(
                label,
                icon=details.get('image', icon) if details else icon,
                fanart=FANART,
                info={
                    'title': f"{section} - Server #{server_num} [{host}]",
                    'plot': details.get('description', '') if details else ''
                },
                is_playable=True
            )
            
            xbmcplugin.addDirectoryItem(
                HANDLE,
                build_url({'action': 'play', 'url': link['url'], 'title': f"{section} Server #{server_num}", 'fight_url': url, 'icon': details.get('image', icon) if details else icon}),
                li, False
            )
        
        xbmcplugin.endOfDirectory(HANDLE)

    elif action == 'search':
        # Search functionality
        kb = xbmcgui.Dialog().input('Search Fights', type=xbmcgui.INPUT_ALPHANUM)
        if kb:
            xbmcplugin.setContent(HANDLE, 'videos')
            fights, _ = scraper.search_fights(kb)
            
            if not fights:
                xbmcgui.Dialog().notification('Strike Zone', 'No results found', xbmcgui.NOTIFICATION_INFO)
                xbmcplugin.endOfDirectory(HANDLE)
                return
            
            for f in fights:
                context_menu = [
                    ('Add to Favourites', f"RunPlugin({build_url({'action': 'add_fav', 'title': f['title'], 'url': f['url'], 'icon': f['icon'], 'category': f.get('category', ''), 'description': f.get('description', '')})})")
                ]
                
                li = create_list_item(
                    f['title'],
                    icon=f['icon'],
                    fanart=FANART,
                    info={'title': f['title'], 'plot': f.get('description', '')}
                )
                li.addContextMenuItems(context_menu)
                
                xbmcplugin.addDirectoryItem(
                    HANDLE,
                    build_url({'action': 'get_links', 'url': f['url'], 'title': f['title'], 'icon': f['icon']}),
                    li, True
                )
            
            xbmcplugin.endOfDirectory(HANDLE)

    elif action == 'favourites':
        # List favourites
        xbmcplugin.setContent(HANDLE, 'videos')
        favourites = load_favourites()
        
        if not favourites:
            xbmcgui.Dialog().notification('Strike Zone', 'No favourites yet', xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(HANDLE)
            return
        
        # Add clear favourites option at top
        clear_li = xbmcgui.ListItem('[COLOR red][B]🗑️ Clear All Favourites[/B][/COLOR]')
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'clear_favourites'}), clear_li, False)
        
        for fav in favourites:
            context_menu = [
                ('Remove from Favourites', f"RunPlugin({build_url({'action': 'remove_fav', 'url': fav['url']})})")
            ]
            
            li = create_list_item(
                fav['title'],
                icon=fav.get('icon', ''),
                fanart=FANART,
                info={
                    'title': fav['title'],
                    'plot': fav.get('description', ''),
                    'genre': fav.get('category', '')
                }
            )
            li.addContextMenuItems(context_menu)
            
            xbmcplugin.addDirectoryItem(
                HANDLE,
                build_url({'action': 'get_links', 'url': fav['url'], 'title': fav['title'], 'icon': fav.get('icon', '')}),
                li, True
            )
        
        xbmcplugin.endOfDirectory(HANDLE)

    elif action == 'add_fav':
        # Add to favourites
        title = params.get('title', '')
        url = params.get('url', '')
        icon = params.get('icon', '')
        category = params.get('category', '')
        description = params.get('description', '')
        add_to_favourites(title, url, icon, category, description)

    elif action == 'remove_fav':
        # Remove from favourites
        url = params.get('url', '')
        remove_from_favourites(url)

    elif action == 'history':
        # List watch history
        xbmcplugin.setContent(HANDLE, 'videos')
        history = load_history()
        
        if not history:
            xbmcgui.Dialog().notification('Strike Zone', 'No watch history', xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(HANDLE)
            return
        
        # Add clear history option at top
        clear_li = xbmcgui.ListItem('[COLOR red][B]🗑️ Clear All History[/B][/COLOR]')
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'clear_history'}), clear_li, False)
        
        for item in history:
            context_menu = [
                ('Add to Favourites', f"RunPlugin({build_url({'action': 'add_fav', 'title': item['title'], 'url': item['url'], 'icon': item.get('icon', ''), 'category': item.get('category', '')})})")
            ]
            
            li = create_list_item(
                item['title'],
                icon=item.get('icon', ''),
                fanart=FANART,
                info={
                    'title': item['title'],
                    'genre': item.get('category', '')
                }
            )
            li.addContextMenuItems(context_menu)
            
            xbmcplugin.addDirectoryItem(
                HANDLE,
                build_url({'action': 'get_links', 'url': item['url'], 'title': item['title'], 'icon': item.get('icon', '')}),
                li, True
            )
        
        xbmcplugin.endOfDirectory(HANDLE)

    elif action == 'clear_history':
        # Clear watch history
        if xbmcgui.Dialog().yesno('Strike Zone', 'Clear all watch history?'):
            clear_history()

    elif action == 'clear_favourites':
        # Clear all favourites
        if xbmcgui.Dialog().yesno('Strike Zone', 'Clear all favourites?'):
            clear_favourites()

    elif action == 'play':
        # Play video using ResolveURL
        url = params.get('url', '')
        title = params.get('title', 'Fight')
        icon = params.get('icon', '')
        fight_url = params.get('fight_url', '')
        
        # Add to history if we have fight info
        if fight_url:
            add_to_history(title, fight_url, icon)
        
        try:
            import resolveurl
            
            # Try to resolve the URL
            resolved = resolveurl.resolve(url)
            
            if resolved:
                li = xbmcgui.ListItem(path=resolved)
                li.setInfo('video', {'title': title})
                xbmcplugin.setResolvedUrl(HANDLE, True, li)
            else:
                xbmcgui.Dialog().notification('Strike Zone', 'Could not resolve link', xbmcgui.NOTIFICATION_ERROR)
                xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        except Exception as e:
            xbmcgui.Dialog().notification('Strike Zone', f'Error: {str(e)[:50]}', xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

    elif action == 'donate':
        # Show QR code for donation
        qr_path = os.path.join(MEDIA_PATH, 'qrcode.png')
        dialog = xbmcgui.Dialog()
        dialog.textviewer(
            'Support zeus768 - Buy Me a Beer!',
            'Thank you for using Strike Zone!\n\n'
            'If you enjoy this addon and want to support development,\n'
            'please scan the QR code or visit the link below.\n\n'
            'Your support helps keep this addon updated!\n\n'
            f'QR Code location: {qr_path}'
        )
        # Show the image
        xbmcgui.Dialog().notification('Strike Zone', 'Check QR code in resources/media/', xbmcgui.NOTIFICATION_INFO, 5000)

if __name__ == '__main__':
    import xbmc
    run()
