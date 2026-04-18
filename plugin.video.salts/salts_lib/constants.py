"""
SALTS Library - Constants
Revived by zeus768 for Kodi 21+
"""

# Video Types
class VIDEO_TYPES:
 MOVIE = 'movie'
 TVSHOW = 'tvshow'
 SEASON = 'season'
 EPISODE = 'episode'

# Quality definitions
class QUALITIES:
 LOW = 'SD'
 MEDIUM = 'HD'
 HIGH = '1080p'
 HD4K = '4K'

# Quality order for sorting (higher = better)
QUALITY_ORDER = {
 'CAM': 1,
 'TS': 2,
 'TC': 3,
 'SCR': 4,
 'DVDSCR': 5,
 'SD': 6,
 '480p': 7,
 '720p': 8,
 'HD': 9,
 '1080p': 10,
 '2K': 11,
 '4K': 12,
 '2160p': 12,
 'UNKNOWN': 0
}

# Host quality mapping
HOST_Q = {
 QUALITIES.HIGH: ['gvideo', '1fichier', 'uptobox', 'rapidgator'],
 QUALITIES.MEDIUM: ['openload', 'streamango', 'vidoza'],
 QUALITIES.LOW: ['vidlox', 'clipwatching']
}

# User Agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Torrent categories
TORRENT_CATEGORIES = {
 'movies': ['Movies', 'Movie', 'Films'],
 'tv': ['TV', 'Television', 'TV Shows', 'Series'],
 'anime': ['Anime'],
 'xxx': ['XXX', 'Adult']
}

# Quality patterns for parsing
QUALITY_PATTERNS = {
 '4K': [r'4k', r'2160p', r'uhd'],
 '1080p': [r'1080p', r'1080i', r'fhd', r'fullhd'],
 '720p': [r'720p', r'hd'],
 '480p': [r'480p', r'sd'],
 'CAM': [r'cam', r'hdcam', r'camrip'],
 'TS': [r'hdts', r'telesync', r'ts'],
 'TC': [r'tc', r'telecine'],
 'SCR': [r'scr', r'screener', r'dvdscr']
}

# Default timeout for HTTP requests
DEFAULT_TIMEOUT = 30

# Cache settings
CACHE_DURATION = 8 # hours
