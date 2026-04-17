# -*- coding: utf-8 -*-
"""
Icon Helper for Test1 - Genesis Skins Integration
Provides themed icons from script.genesis.skins addon
"""
import os
import xbmcaddon
import xbmcvfs

# Cache for performance
_genesis_addon = None
_icon_cache = {}


def get_genesis_skins():
    """Get Genesis Skins addon if installed"""
    global _genesis_addon
    if _genesis_addon is None:
        try:
            _genesis_addon = xbmcaddon.Addon('script.genesis.skins')
        except:
            _genesis_addon = False
    return _genesis_addon if _genesis_addon else None


def is_enabled():
    """Check if Genesis Skins integration is enabled in Test1 settings"""
    try:
        addon = xbmcaddon.Addon('plugin.video.genesis')
        return addon.getSetting('use_genesis_skins') == 'true'
    except:
        return False


def get_current_theme():
    """Get currently selected icon theme"""
    addon = get_genesis_skins()
    if addon:
        theme = addon.getSetting('icon_theme')
        return theme if theme else 'classic'
    return 'classic'


def get_icon(icon_name, fallback=None):
    """Get themed icon path for a menu item
    
    Args:
        icon_name: Name of the icon (without .png)
        fallback: Fallback path if icon not found
        
    Returns:
        Full path to icon, or fallback if not available
    """
    global _icon_cache
    
    # Check if Genesis Skins is enabled
    if not is_enabled():
        return fallback
    
    addon = get_genesis_skins()
    if not addon:
        return fallback
    
    theme = get_current_theme()
    cache_key = f"{theme}:{icon_name}"
    
    # Check cache first
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]
    
    addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
    media_path = os.path.join(addon_path, 'resources', 'media')
    
    # Try current theme
    icon_path = os.path.join(media_path, theme, f'{icon_name}.png')
    if os.path.exists(icon_path):
        _icon_cache[cache_key] = icon_path
        return icon_path
    
    # Fallback to classic theme
    icon_path = os.path.join(media_path, 'classic', f'{icon_name}.png')
    if os.path.exists(icon_path):
        _icon_cache[cache_key] = icon_path
        return icon_path
    
    # Use fallback
    _icon_cache[cache_key] = fallback
    return fallback


def clear_cache():
    """Clear the icon cache (call when theme changes)"""
    global _icon_cache
    _icon_cache = {}


def get_available_themes():
    """Get list of all available themes"""
    addon = get_genesis_skins()
    if not addon:
        return ['classic']
    
    addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
    media_path = os.path.join(addon_path, 'resources', 'media')
    
    themes = []
    if os.path.exists(media_path):
        for item in os.listdir(media_path):
            item_path = os.path.join(media_path, item)
            if os.path.isdir(item_path):
                themes.append(item)
    
    return sorted(themes) if themes else ['classic']


# ══════════════════════════════════════════════════════════════════════════════
# ICON NAME MAPPING - Maps menu items to icon filenames
# ══════════════════════════════════════════════════════════════════════════════

ICON_MAP = {
    # Main Menu
    'Live Channels': 'live_channels',
    'Movies': 'movies',
    'TV Shows': 'tv_shows',
    'Anime & Manga': 'anime_manga',
    'Latest Releases': 'latest_releases',
    'Trending Movies': 'trending_movies',
    'Trending TV Shows': 'trending_tv',
    'Latest Episodes': 'latest_episodes',
    'Continue Watching': 'continue_watching',
    'My Trakt': 'my_trakt',
    'Search': 'search',
    'Debrid Services': 'debrid_services',
    'Tools': 'tools',
    'Buy Me a Beer': 'donate',
    
    # Cloud Menu
    'Cloud': 'cloud',
    'All Downloaded': 'downloaded',
    'Currently Downloading': 'downloading',
    'Cached/History': 'cached',
    'Real-Debrid Cloud': 'debrid_cloud',
    'AllDebrid Cloud': 'debrid_cloud',
    'Premiumize Cloud': 'debrid_cloud',
    'TorBox Cloud': 'debrid_cloud',
    
    # Locals Menu
    'Locals': 'local_media',
    'Configure Local Folders': 'folder',
    'Configure Folders': 'folder',
    'Add Folder': 'add',
    'Rescan Library': 'refresh',
    
    # Plex Menu
    'Plex': 'plex',
    'On Deck': 'continue_watching',
    'Recently Added': 'new_releases',
    'Search Plex': 'search',
    'Search Plex Library': 'search',
    'Disable Plex': 'delete',
    'Configure Plex Server': 'plex',
    
    # Emby Menu
    'Emby': 'emby',
    'Continue Watching': 'continue_watching',
    'Next Up': 'new_episodes',
    'Search Emby': 'search',
    'Search Emby Library': 'search',
    'Disable Emby': 'delete',
    'Configure Emby Server': 'emby',
    
    # Movie Menu
    'Latest Releases (In Cinemas)': 'latest_releases_cinema',
    'Trending': 'trending',
    'Popular': 'popular',
    'Most Watched (Week)': 'most_watched_week',
    'Most Watched (All Time)': 'most_watched_all',
    'Box Office': 'box_office',
    'Anticipated': 'anticipated',
    'Recommended For You': 'recommendations',
    'Genres': 'genres',
    
    # TV Menu
    'Trending Shows': 'trending_shows',
    'Popular Shows': 'popular_shows',
    'My Calendar': 'my_calendar',
    
    # Search Menu
    'Search Movies': 'search_movies',
    'Search TV Shows': 'search_tv',
    'Search Anime': 'search_anime',
    'Search Manga': 'search_manga',
    
    # Anime Menu
    'Anime Movies': 'anime_movies',
    'Anime TV Shows': 'anime_tv',
    'Manga': 'manga',
    'Torrent Sites': 'torrent_sites',
    'Trending Anime': 'trending_anime',
    'Currently Airing': 'currently_airing',
    'New Episodes (Calendar)': 'new_episodes_calendar',
    
    # Anime Movies Submenu
    'New Releases': 'new_releases',
    'Top Rated Movies': 'top_rated_movies',
    'Popular Movies': 'popular_movies',
    'Upcoming Movies': 'upcoming_movies',
    'Movies by Genre': 'movies_by_genre',
    'Award Winning Movies': 'award_winning',
    'Classic Movies (Pre-2010)': 'classic_movies',
    'Recent Movies (2020+)': 'recent_movies',
    'Studio Ghibli Collection': 'studio_ghibli',
    'Search Anime Movies': 'search_anime_movies',
    
    # Anime TV Submenu
    'New Episodes (Calendar)': 'new_episodes',
    'Show Premieres (Brand New)': 'show_premieres',
    'Currently Airing': 'currently_airing_anime',
    'Top Rated Shows': 'top_rated_shows',
    'Popular Shows': 'popular_anime_shows',
    'Upcoming Shows': 'upcoming_shows',
    'Shows by Genre': 'shows_by_genre',
    'By Network/Studio': 'by_network_studio',
    'Seasonal Anime': 'seasonal_anime',
    'Complete Series': 'complete_series',
    'Search Anime Shows': 'search_anime_shows',
    
    # Manga Submenu
    'Top Manga': 'top_manga',
    'Popular Manga': 'popular_manga',
    'Publishing Now': 'publishing_now',
    'Manga by Genre': 'manga_by_genre',
    'Light Novels': 'light_novels',
    'One-shots': 'one_shots',
    'Manhwa (Korean)': 'manhwa',
    'Manhua (Chinese)': 'manhua',
    
    # Anime Torrent Sites
    'Nyaa.si (Best Overall)': 'nyaa',
    'SubsPlease (Daily Subs)': 'subsplease',
    'AnimeTosho (Ad-Free)': 'animetosho',
    'TokyoTosho (Japanese Media)': 'tokyotosho',
    'Erai-Raws (Raw Episodes)': 'erairaws',
    'AniDex (Multi-Language)': 'anidex',
    'Search All Anime Sites': 'search_all_anime',
    
    # My Trakt Menu
    'Movie Watchlist': 'movie_watchlist',
    'Show Watchlist': 'show_watchlist',
    'Movie Collection': 'movie_collection',
    'Show Collection': 'show_collection',
    'Watched Movies': 'watched_movies',
    'Watched Shows': 'watched_shows',
    'My Custom Lists': 'my_custom_lists',
    'Popular Lists': 'popular_lists',
    'Friends': 'friends',
    'My Stats': 'my_stats',
    
    # Debrid Services
    'Account Status': 'account_status',
    'Debrid Cloud': 'debrid_cloud',
    'Authorize Real-Debrid': 'authorize_realdebrid',
    'Authorize AllDebrid': 'authorize_alldebrid',
    'Authorize Premiumize': 'authorize_premiumize',
    'Authorize TorBox': 'authorize_torbox',
    'Login to LinkSnappy': 'login_linksnappy',
    
    # Tools
    'Clear Cache': 'clear_cache',
    'Settings': 'settings',
    
    # Networks/Studios
    'Crunchyroll': 'crunchyroll',
    'Netflix': 'netflix',
    'Funimation': 'funimation',
    'HIDIVE': 'hidive',
    'Amazon Prime Video': 'amazon_prime',
    'Hulu': 'hulu',
    'Disney+': 'disney_plus',
    'MAPPA Studio': 'mappa',
    'ufotable': 'ufotable',
    'Wit Studio': 'wit_studio',
    'Bones': 'bones',
    'Madhouse': 'madhouse',
    'Kyoto Animation': 'kyoto_animation',
    'Toei Animation': 'toei',
    'Sunrise': 'sunrise',
    'A-1 Pictures': 'a1_pictures',
    'CloverWorks': 'cloverworks',
}


def get_icon_for_label(label, fallback=None):
    """Get icon based on menu item label
    
    Args:
        label: Menu item label text
        fallback: Fallback icon path
        
    Returns:
        Icon path or fallback
    """
    # Strip Kodi formatting tags
    clean_label = label
    for tag in ['[B]', '[/B]', '[COLOR yellow]', '[COLOR red]', '[COLOR lime]', 
                '[COLOR cyan]', '[COLOR gray]', '[COLOR orange]', '[COLOR purple]',
                '[COLOR white]', '[/COLOR]']:
        clean_label = clean_label.replace(tag, '')
    clean_label = clean_label.strip()
    
    # Look up icon name
    icon_name = ICON_MAP.get(clean_label)
    if icon_name:
        return get_icon(icon_name, fallback)
    
    # Try direct icon name lookup
    icon_key = clean_label.lower().replace(' ', '_').replace('(', '').replace(')', '')
    return get_icon(icon_key, fallback)
