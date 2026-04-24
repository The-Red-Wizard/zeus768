# -*- coding: utf-8 -*-
"""
Free Links Scraper for Genesis
Scrapes thechains24.com for free streaming links
Integrates with ResolveURL for link resolution
"""
import re
import json
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import ssl

ADDON = xbmcaddon.Addon()
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Create SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Free links source URL
FREE_LINKS_URL = "https://thechains24.com/ABSOLUTION/MOVIES/newm.NEW.txt"

# Cache for parsed links
_cached_links = None
_cache_time = 0


def _http_get(url, timeout=15):
    """HTTP GET request"""
    try:
        req = Request(url, headers={'User-Agent': USER_AGENT})
        response = urlopen(req, timeout=timeout, context=ssl_context)
        return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        xbmc.log(f'Free Links HTTP Error: {e}', xbmc.LOGERROR)
        return None


def parse_free_links():
    """Parse the free links text file and return structured data"""
    global _cached_links, _cache_time
    import time
    
    # Cache for 30 minutes
    if _cached_links and (time.time() - _cache_time) < 1800:
        return _cached_links
    
    content = _http_get(FREE_LINKS_URL)
    if not content:
        return []
    
    movies = []
    
    # The format is: Title + URLs concatenated
    # Pattern: TitleURL(s)DescriptionPosterFanart
    # We need to parse this carefully
    
    # Split by common patterns - looking for streamtape/luluvid URLs
    entries = re.split(r'(?=https://(?:streamtape\.com|luluvid\.com))', content)
    
    current_title = None
    current_links = []
    current_description = ''
    current_poster = ''
    current_fanart = ''
    
    # Better parsing approach - find all streamtape links with surrounding context
    pattern = r'([A-Z][^https]*?)?(https://(?:streamtape\.com|luluvid\.com)/[^\s]+)'
    
    lines = content.replace('\n', ' ').strip()
    
    # Find all links first
    link_matches = list(re.finditer(r'https://(?:streamtape\.com|luluvid\.com)/[vd]/[^\s]+', lines))
    
    # Find all poster/image URLs
    image_pattern = r'https://(?:www\.themoviedb\.org|m\.media-amazon\.com|image\.tmdb\.org)[^\s]+'
    
    # Process each potential movie entry
    # Format seems to be: Title + link + description + poster + fanart
    
    # Split by known title patterns (capitalized words followed by links)
    movie_entries = re.split(r'(?=[A-Z][a-zA-Z0-9\s:\'!?\-]+https://(?:streamtape|luluvid))', lines)
    
    for entry in movie_entries:
        if not entry.strip():
            continue
            
        # Extract title (text before first URL)
        title_match = re.match(r'^([^h]+?)(?=https://)', entry)
        if not title_match:
            continue
            
        title = title_match.group(1).strip()
        if not title or len(title) < 2:
            continue
        
        # Clean title - remove IMDB IDs
        title = re.sub(r'tt\d+$', '', title).strip()
        
        # Find streaming links
        stream_links = re.findall(r'https://(?:streamtape\.com|luluvid\.com)/[vd]/[^\s]+', entry)
        if not stream_links:
            continue
        
        # Find description (text after first link, before image URLs)
        desc_match = re.search(r'\.(?:mp4|mkv)\s*([A-Z][^h]+?)(?=https://(?:www\.themoviedb|m\.media|image\.tmdb))', entry)
        description = desc_match.group(1).strip() if desc_match else ''
        
        # Find poster images
        posters = re.findall(r'https://(?:www\.themoviedb\.org|m\.media-amazon\.com)/[^\s]+(?:\.jpg|\.png)', entry)
        poster = posters[0] if posters else ''
        fanart = posters[1] if len(posters) > 1 else poster
        
        # Clean poster URLs (remove escapes)
        poster = poster.replace('\\_', '_')
        fanart = fanart.replace('\\_', '_')
        
        movies.append({
            'title': title,
            'links': stream_links,
            'description': description,
            'poster': poster,
            'fanart': fanart,
            'source': 'FreeLinks'
        })
    
    _cached_links = movies
    _cache_time = time.time()
    
    xbmc.log(f'Free Links: Parsed {len(movies)} movies', xbmc.LOGINFO)
    return movies


def search_free_links(query):
    """Search free links for a specific movie/show title"""
    movies = parse_free_links()
    if not movies:
        return []
    
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    results = []
    for movie in movies:
        title_lower = movie['title'].lower()
        title_words = set(title_lower.split())
        
        # Check for word overlap
        overlap = query_words & title_words
        if len(overlap) >= min(2, len(query_words)):
            # Good match
            for link in movie['links']:
                results.append({
                    'title': f"[FreeLink] {movie['title']}",
                    'url': link,
                    'quality': detect_quality_from_url(link),
                    'source': 'FreeLinks',
                    'poster': movie.get('poster', ''),
                    'description': movie.get('description', ''),
                    'is_free_link': True
                })
        elif query_lower in title_lower or title_lower in query_lower:
            # Partial match
            for link in movie['links']:
                results.append({
                    'title': f"[FreeLink] {movie['title']}",
                    'url': link,
                    'quality': detect_quality_from_url(link),
                    'source': 'FreeLinks',
                    'poster': movie.get('poster', ''),
                    'description': movie.get('description', ''),
                    'is_free_link': True
                })
    
    return results


def detect_quality_from_url(url):
    """Detect quality from URL filename"""
    url_lower = url.lower()
    if '1080p' in url_lower:
        return '1080p'
    elif '720p' in url_lower:
        return '720p'
    elif '480p' in url_lower:
        return '480p'
    elif '2160p' in url_lower or '4k' in url_lower:
        return '4K'
    return '720p'  # Default


def get_all_free_movies():
    """Get all available free movies"""
    return parse_free_links()


def resolve_free_link(url):
    """
    Resolve free link using Zeus Resolvers first (Streamtape / DDownloads),
    then ResolveURL, then built-in fallbacks.
    """
    # 1. Zeus Resolvers (debrid-free) takes priority for supported hosts
    try:
        from resources.lib.zeus_hook import try_zeus
        zeus_url = try_zeus(url)
        if zeus_url:
            return zeus_url
    except Exception as e:
        xbmc.log(f'Zeus hook error: {e}', xbmc.LOGWARNING)

    try:
        # Try ResolveURL next
        import resolveurl
        resolved = resolveurl.resolve(url)
        if resolved:
            return resolved
    except ImportError:
        xbmc.log('ResolveURL not available, using direct link', xbmc.LOGDEBUG)
    except Exception as e:
        xbmc.log(f'ResolveURL error: {e}', xbmc.LOGWARNING)
    
    # For streamtape, we can try to extract direct link
    if 'streamtape.com' in url:
        return resolve_streamtape(url)
    
    # For luluvid, try direct
    if 'luluvid.com' in url:
        return resolve_luluvid(url)
    
    return url


def resolve_streamtape(url):
    """Resolve streamtape link to direct stream"""
    try:
        html = _http_get(url)
        if not html:
            return url
        
        # Look for the video URL in the page
        # Streamtape uses obfuscated JS, but we can try common patterns
        match = re.search(r"document\.getElementById\('robotlink'\)\.innerHTML\s*=\s*'([^']+)'", html)
        if match:
            partial = match.group(1)
            # Find the token part
            token_match = re.search(r"'([^']+)'\s*\+\s*\('([^']+)'\)", html)
            if token_match:
                final_url = f"https:{partial}{token_match.group(2)}"
                return final_url
        
        # Alternative pattern
        match = re.search(r'(https://[^"\']+\.streamtape\.com/get_video[^"\']+)', html)
        if match:
            return match.group(1)
            
    except Exception as e:
        xbmc.log(f'Streamtape resolve error: {e}', xbmc.LOGWARNING)
    
    return url


def resolve_luluvid(url):
    """Resolve luluvid link to direct stream"""
    try:
        html = _http_get(url)
        if not html:
            return url
        
        # Look for video source
        match = re.search(r'file:\s*["\']([^"\']+)["\']', html)
        if match:
            return match.group(1)
        
        match = re.search(r'source\s+src=["\']([^"\']+)["\']', html)
        if match:
            return match.group(1)
            
    except Exception as e:
        xbmc.log(f'Luluvid resolve error: {e}', xbmc.LOGWARNING)
    
    return url


def clear_cache():
    """Clear the cached links"""
    global _cached_links, _cache_time
    _cached_links = None
    _cache_time = 0
