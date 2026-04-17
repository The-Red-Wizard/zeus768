# -*- coding: utf-8 -*-
"""
Genesis Skins Icon Helper
Provides themed icons + auto-fetched real service logos
"""
import os
import xbmcaddon
import xbmcvfs


def get_genesis_skins_addon():
    """Get Genesis Skins addon if installed"""
    try:
        return xbmcaddon.Addon('script.genesis.skins')
    except:
        return None


def get_current_theme():
    """Get currently selected icon theme"""
    addon = get_genesis_skins_addon()
    if addon:
        theme = addon.getSetting('icon_theme')
        return theme if theme else 'classic'
    return 'classic'


# Services that should use real logos (auto-fetched)
AUTO_FETCH_SERVICES = {
    # Streaming Networks
    'crunchyroll', 'netflix', 'funimation', 'hidive', 'amazon_prime', 'hulu', 'disney_plus',
    # Anime Studios
    'mappa', 'ufotable', 'wit_studio', 'bones', 'madhouse', 'kyoto_animation', 'toei', 
    'sunrise', 'a1_pictures', 'cloverworks',
    # Anime Torrent Sites
    'nyaa', 'subsplease', 'animetosho', 'tokyotosho', 'anidex', 'erairaws',
    # Live TV Channels  
    'sky_cinema', 'sony_movies', 'hallmark', 'film4', 'hbo', 'showtime', 'starz', 
    'amc', 'tcm', 'fx', 'syfy', 'paramount', 'cinemax', 'great_movies', 'movies4men',
    # Debrid Services
    'realdebrid', 'alldebrid', 'premiumize', 'torbox', 'linksnappy',
    # General Torrent Sites
    '1337x', 'piratebay', 'yts', 'eztv', 'limetorrents', 'torrentgalaxy', 
    'magnetdl', 'solidtorrents', 'bitsearch',
    # APIs
    'trakt', 'tmdb', 'omdb', 'myanimelist',
}


def get_icon(icon_name):
    """Get icon path for a specific menu item
    
    Args:
        icon_name: Name of the icon (without .png extension)
        
    Returns:
        Full path to the icon file, or None if not found
    """
    addon = get_genesis_skins_addon()
    if not addon:
        return None
    
    addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
    
    # Normalize icon name
    icon_key = icon_name.lower().replace(' ', '_').replace('-', '_')
    
    # Check if this should use auto-fetched real logo
    if icon_key in AUTO_FETCH_SERVICES:
        try:
            from resources.lib import logo_fetcher
            logo_path = logo_fetcher.get_logo(icon_key)
            if logo_path and os.path.exists(logo_path):
                return logo_path
        except ImportError:
            pass
    
    # Fall back to themed placeholder icons
    theme = get_current_theme()
    media_path = os.path.join(addon_path, 'resources', 'media')
    
    # Try current theme first
    icon_path = os.path.join(media_path, theme, f'{icon_key}.png')
    if os.path.exists(icon_path):
        return icon_path
    
    # Fallback to classic
    icon_path = os.path.join(media_path, 'classic', f'{icon_key}.png')
    if os.path.exists(icon_path):
        return icon_path
    
    return None


def get_all_icons():
    """Get list of all available icon names"""
    addon = get_genesis_skins_addon()
    if not addon:
        return []
    
    addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
    classic_path = os.path.join(addon_path, 'resources', 'media', 'classic')
    
    icons = []
    if os.path.exists(classic_path):
        for f in os.listdir(classic_path):
            if f.endswith('.png'):
                icons.append(f.replace('.png', ''))
    
    return sorted(icons)


def get_available_themes():
    """Get list of all available themes"""
    addon = get_genesis_skins_addon()
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
# ICON NAME MAPPING - Maps menu labels to icon filenames
# Only for CUSTOM icons (services use auto-fetch)
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
    
    # Anime Menu (categories use custom icons)
    'Anime Movies': 'anime_movies',
    'Anime TV Shows': 'anime_tv',
    'Manga': 'manga',
    'Torrent Sites': 'torrent_sites',
    'Trending Anime': 'trending_anime',
    'Currently Airing': 'currently_airing',
    
    # Anime Submenus
    'New Releases': 'new_releases',
    'Top Rated Movies': 'top_rated_movies',
    'Popular Movies': 'popular_movies',
    'Upcoming Movies': 'upcoming_movies',
    'Movies by Genre': 'movies_by_genre',
    'Award Winning Movies': 'award_winning',
    'Classic Movies (Pre-2010)': 'classic_movies',
    'Recent Movies (2020+)': 'recent_movies',
    'Studio Ghibli Collection': 'studio_ghibli',
    
    # Manga Submenu
    'Top Manga': 'top_manga',
    'Popular Manga': 'popular_manga',
    'Publishing Now': 'publishing_now',
    'Manga by Genre': 'manga_by_genre',
    'Light Novels': 'light_novels',
    'One-shots': 'one_shots',
    'Manhwa (Korean)': 'manhwa',
    'Manhua (Chinese)': 'manhua',
    
    # My Trakt (categories)
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
    
    # Debrid Menu (categories - actual services use auto-fetch)
    'Account Status': 'account_status',
    'Debrid Cloud': 'debrid_cloud',
    
    # Tools
    'Clear Cache': 'clear_cache',
    'Settings': 'settings',
    
    # Genres (custom icons)
    'Action': 'genre_action',
    'Adventure': 'genre_adventure',
    'Comedy': 'genre_comedy',
    'Drama': 'genre_drama',
    'Fantasy': 'genre_fantasy',
    'Horror': 'genre_horror',
    'Mystery': 'genre_mystery',
    'Romance': 'genre_romance',
    'Sci-Fi': 'genre_scifi',
    'Thriller': 'genre_thriller',
    
    # Seasons
    'Winter': 'winter',
    'Spring': 'spring', 
    'Summer': 'summer',
    'Fall': 'fall',
    
    # Days
    'Sunday': 'sunday',
    'Monday': 'monday',
    'Tuesday': 'tuesday',
    'Wednesday': 'wednesday',
    'Thursday': 'thursday',
    'Friday': 'friday',
    'Saturday': 'saturday',
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
                '[COLOR cyan]', '[COLOR gray]', '[/COLOR]']:
        clean_label = clean_label.replace(tag, '')
    clean_label = clean_label.strip()
    
    # Look up icon name in mapping
    icon_name = ICON_MAP.get(clean_label)
    if icon_name:
        result = get_icon(icon_name)
        if result:
            return result
    
    # Try direct lookup (for services like "Netflix", "Nyaa", etc.)
    icon_key = clean_label.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('.', '')
    
    # Check if it's an auto-fetch service
    if icon_key in AUTO_FETCH_SERVICES:
        result = get_icon(icon_key)
        if result:
            return result
    
    # Try as regular icon
    result = get_icon(icon_key)
    if result:
        return result
    
    return fallback
