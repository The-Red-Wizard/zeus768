# -*- coding: utf-8 -*-
"""Genesis Skins - Icon Theme Manager for Test1
Supports themed placeholder icons + auto-fetched real service logos"""
import os
import sys
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
MEDIA_PATH = os.path.join(ADDON_PATH, 'resources', 'media')


def get_available_themes():
    """Auto-detect all theme folders in media directory"""
    themes = []
    if os.path.exists(MEDIA_PATH):
        for item in os.listdir(MEDIA_PATH):
            item_path = os.path.join(MEDIA_PATH, item)
            if os.path.isdir(item_path):
                themes.append(item)
    return sorted(themes)


def get_icon_path(icon_name, theme=None):
    """Get full path to an icon based on current theme"""
    if theme is None:
        theme = ADDON.getSetting('icon_theme')
    
    if not theme:
        theme = 'classic'
    
    icon_file = f'{icon_name}.png'
    theme_path = os.path.join(MEDIA_PATH, theme, icon_file)
    
    if os.path.exists(theme_path):
        return theme_path
    
    # Fallback to classic
    classic_path = os.path.join(MEDIA_PATH, 'classic', icon_file)
    if os.path.exists(classic_path):
        return classic_path
    
    return None


def show_theme_selector():
    """Show dialog to select icon theme"""
    themes = get_available_themes()
    
    if not themes:
        xbmcgui.Dialog().notification('Genesis Skins', 'No themes found!', xbmcgui.NOTIFICATION_WARNING)
        return
    
    # Format for display
    display_names = [t.replace('_', ' ').title() for t in themes]
    
    current = ADDON.getSetting('icon_theme')
    preselect = themes.index(current) if current in themes else 0
    
    choice = xbmcgui.Dialog().select('Select Icon Theme', display_names, preselect=preselect)
    
    if choice >= 0:
        selected_theme = themes[choice]
        ADDON.setSetting('icon_theme', selected_theme)
        xbmcgui.Dialog().notification(
            'Genesis Skins', 
            f'Theme changed to {display_names[choice]}',
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
        # Refresh Test1 if running
        xbmc.executebuiltin('Container.Refresh')


def list_all_icons():
    """Show all available icon placeholders"""
    icons = []
    classic_path = os.path.join(MEDIA_PATH, 'classic')
    
    if os.path.exists(classic_path):
        for f in os.listdir(classic_path):
            if f.endswith('.png'):
                icons.append(f.replace('.png', ''))
    
    if icons:
        dialog_text = f'Custom Theme Icons ({len(icons)} total):\n\n'
        for icon in sorted(icons)[:50]:  # Show first 50
            dialog_text += f'• {icon}\n'
        if len(icons) > 50:
            dialog_text += f'\n... and {len(icons) - 50} more'
        
        dialog_text += '\n\n═══════════════════════════════════\n'
        dialog_text += 'Auto-Fetched Service Logos:\n\n'
        dialog_text += '• Networks: Netflix, Crunchyroll, HBO, etc.\n'
        dialog_text += '• Studios: MAPPA, ufotable, Bones, etc.\n'
        dialog_text += '• Torrent Sites: Nyaa, SubsPlease, etc.\n'
        dialog_text += '• Debrid: Real-Debrid, AllDebrid, etc.\n'
        dialog_text += '\nThese are fetched automatically from official sources!'
        
        xbmcgui.Dialog().textviewer('Genesis Skins - Icon List', dialog_text)
    else:
        xbmcgui.Dialog().notification('Genesis Skins', 'No icons found', xbmcgui.NOTIFICATION_INFO)


def prefetch_logos():
    """Download all service logos"""
    try:
        from resources.lib import logo_fetcher
        
        progress = xbmcgui.DialogProgress()
        progress.create('Genesis Skins', 'Fetching service logos...')
        
        logos = logo_fetcher.get_all_fetchable_logos()
        total = len(logos)
        
        for i, name in enumerate(logos):
            if progress.iscanceled():
                break
            progress.update(int((i / total) * 100), f'Downloading {name}...')
            logo_fetcher.get_logo(name)
        
        progress.close()
        xbmcgui.Dialog().notification(
            'Genesis Skins',
            f'Downloaded {total} service logos',
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
    except ImportError:
        xbmcgui.Dialog().notification('Genesis Skins', 'Logo fetcher not available', xbmcgui.NOTIFICATION_WARNING)


def clear_logo_cache():
    """Clear cached logos"""
    try:
        from resources.lib import logo_fetcher
        logo_fetcher.clear_logo_cache()
        xbmcgui.Dialog().notification('Genesis Skins', 'Logo cache cleared', xbmcgui.NOTIFICATION_INFO, 2000)
    except ImportError:
        xbmcgui.Dialog().notification('Genesis Skins', 'Logo fetcher not available', xbmcgui.NOTIFICATION_WARNING)


def show_main_menu():
    """Show main options menu"""
    options = [
        '[B]Select Icon Theme[/B]',
        'Download Service Logos (Networks, Studios, etc.)',
        'View All Icon Placeholders',
        'Clear Logo Cache',
    ]
    
    choice = xbmcgui.Dialog().select('Genesis Skins', options)
    
    if choice == 0:
        show_theme_selector()
    elif choice == 1:
        prefetch_logos()
    elif choice == 2:
        list_all_icons()
    elif choice == 3:
        clear_logo_cache()


if __name__ == '__main__':
    # Check for arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if 'list_icons' in args:
        list_all_icons()
    elif 'prefetch' in args:
        prefetch_logos()
    elif 'clear_cache' in args:
        clear_logo_cache()
    else:
        show_main_menu()
