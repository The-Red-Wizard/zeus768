"""
SALTS Library - Utility functions
Revived by zeus768 for Kodi 21+
"""
import re
import os
import xbmcaddon

from .constants import QUALITY_PATTERNS, QUALITY_ORDER

ADDON = xbmcaddon.Addon()

def parse_quality(text):
    """Parse quality from text string"""
    text = text.lower()
    
    for quality, patterns in QUALITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return quality
    
    return 'SD'

def parse_size(size_str):
    """Parse size string to bytes"""
    if not size_str:
        return 0
    
    size_str = size_str.upper().strip()
    
    multipliers = {
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4
    }
    
    for unit, mult in multipliers.items():
        if unit in size_str:
            try:
                num = float(re.sub(r'[^\d.]', '', size_str))
                return int(num * mult)
            except:
                return 0
    
    return 0

def format_size(bytes_size):
    """Format bytes to human readable string"""
    if not bytes_size:
        return 'Unknown'
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f'{bytes_size:.1f} {unit}'
        bytes_size /= 1024
    
    return f'{bytes_size:.1f} PB'

def clean_title(title):
    """Clean title for searching"""
    # Remove year if present at end
    title = re.sub(r'\s*\(\d{4}\)\s*$', '', title)
    # Remove special characters
    title = re.sub(r'[^\w\s]', ' ', title)
    # Normalize whitespace
    title = ' '.join(title.split())
    return title.strip()

def normalize_title(title):
    """Normalize title for comparison"""
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title)
    title = ' '.join(title.split())
    return title

def get_quality_order(quality):
    """Get numeric order for quality"""
    return QUALITY_ORDER.get(quality, 0)

def scraper_enabled(name):
    """Check if a scraper is enabled"""
    setting_id = f'{name.lower()}_enabled'
    return ADDON.getSetting(setting_id) == 'true'

def art(filename):
    """Get path to art file"""
    return os.path.join(ADDON.getAddonInfo('path'), 'art', filename)
