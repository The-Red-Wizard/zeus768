"""
File Host Resolver Module
Uses native urllib (no external requests module)
FIXED: Auto-play with proper quality fallback + retries
"""
import json
import re
import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon
import xbmcvfs
import sys
import time
import random
import string
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin, quote, quote_plus
from . import scrapers
from . import debrid

def get_addon():
    return xbmcaddon.Addon()

ADDON_ID = 'plugin.video.trakt_player'
ADDON_PATH = xbmcvfs.translatePath(f'special://home/addons/{ADDON_ID}/')

# Quality priorities
QUALITY_ORDER = ['2160p', '1080p', '720p', '480p', '360p']

# DoodStream domains (updated list - they change frequently)
DOOD_DOMAINS = [
    'myvidplay.com', 'doodstream.com', 'd0000d.com', 'ds2play.com',
    'dood.watch', 'dood.to', 'dood.so', 'dood.cx', 'dood.la', 'dood.ws',
    'dood.sh', 'doodstream.co', 'dood.pm', 'dood.wf', 'dood.re', 'dood.yt', 
    'doood.com', 'dood.stream', 'doods.pro', 'ds2video.com', 'd0o0d.com', 
    'do0od.com', 'd000d.com', 'dood.li', 'dood.work', 'dooodster.com', 
    'vidply.com', 'all3do.com', 'do7go.com', 'doodcdn.io', 'doply.net', 
    'vide0.net', 'vvide0.com', 'd-s.io', 'dsvplay.com'
]

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


class HTTPSession:
    """Simple session-like class for urllib"""
    def __init__(self):
        self.cookies = {}
    
    def get(self, url, headers=None, timeout=15, allow_redirects=True):
        hdrs = {'User-Agent': USER_AGENT}
        if headers:
            hdrs.update(headers)
        
        try:
            req = Request(url, headers=hdrs, method='GET')
            response = urlopen(req, timeout=timeout)
            return HTTPResponse(response, response.read().decode('utf-8', errors='replace'), response.geturl())
        except HTTPError as e:
            body = ''
            try:
                body = e.read().decode('utf-8', errors='replace')
            except:
                pass
            return HTTPResponse(e, body, url, e.code)
        except Exception as e:
            return HTTPResponse(None, '', url, 0)


class HTTPResponse:
    """Simple response class"""
    def __init__(self, response, text, url, status_code=200):
        self.text = text
        self.url = url
        self.status_code = status_code if response is None else (status_code or response.getcode())


def _http_get(url, headers=None, timeout=10):
    """HTTP GET request using urllib"""
    hdrs = {'User-Agent': USER_AGENT}
    if headers:
        hdrs.update(headers)
    
    try:
        req = Request(url, headers=hdrs, method='GET')
        response = urlopen(req, timeout=timeout)
        return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        xbmc.log(f'HTTP GET Error: {e}', xbmc.LOGWARNING)
        return None


def get_preferred_quality():
    """Get user's preferred quality setting"""
    addon = get_addon()
    quality_setting = addon.getSetting('preferred_quality')
    quality_map = {'0': '2160p', '1': '1080p', '2': '720p', '3': '480p'}
    return quality_map.get(quality_setting, '1080p')


def dood_decode(data):
    """Generate random string to append to token - matches ResolveURL method"""
    t = string.ascii_letters + string.digits
    return data + ''.join([random.choice(t) for _ in range(10)])


def resolve_doodstream(url):
    """
    Custom DoodStream resolver - based on ResolveURL's working implementation
    This is a standalone resolver that doesn't require ResolveURL addon
    """
    try:
        # Extract video ID
        video_id = None
        match = re.search(r'(?://|\.)([\w.-]+)/(?:d|e)/([0-9a-zA-Z]+)', url)
        if match:
            video_id = match.group(2)
        else:
            match = re.search(r'/(?:d|e)/([0-9a-zA-Z]+)', url)
            if match:
                video_id = match.group(1)
        
        if not video_id:
            xbmc.log(f"DoodStream: Could not extract video ID from {url}", xbmc.LOGERROR)
            return None
        
        xbmc.log(f"DoodStream: Extracted video ID: {video_id}", xbmc.LOGINFO)
        
        # Try working hosts
        for host in DOOD_DOMAINS[:8]:  # Try first 8 most reliable hosts
            try:
                # Build URL - use /d/ format for direct page
                web_url = f"https://{host}/d/{video_id}"
                
                headers = {
                    'User-Agent': USER_AGENT,
                    'Referer': f'https://{host}/',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5'
                }
                
                xbmc.log(f"DoodStream: Trying {web_url}", xbmc.LOGINFO)
                
                session = HTTPSession()
                response = session.get(web_url, headers=headers, timeout=15)
                
                # Handle redirects
                final_url = response.url
                if final_url != web_url:
                    redirect_match = re.search(r'(?://|\.)([\w.-]+)/', final_url)
                    if redirect_match:
                        host = redirect_match.group(1)
                        web_url = f"https://{host}/d/{video_id}"
                        headers['Referer'] = web_url
                        xbmc.log(f"DoodStream: Redirected to {host}", xbmc.LOGINFO)
                
                html = response.text
                
                if response.status_code != 200 or 'File not found' in html or 'Video not found' in html:
                    xbmc.log(f"DoodStream: {host} - File not found or error", xbmc.LOGWARNING)
                    continue
                
                # Method 1: Extract pass_md5 URL and token (primary method from ResolveURL)
                match = re.search(r"dsplayer\.hotkeys[^']+'/([^']+).+?function\s*makePlay.+?return[^?]+(\?[^\"]+)", html, re.DOTALL)
                
                if match:
                    pass_md5_path = match.group(1)
                    token = match.group(2)
                    pass_md5_url = f"https://{host}/{pass_md5_path}"
                    
                    xbmc.log(f"DoodStream: Found pass_md5 URL", xbmc.LOGINFO)
                    
                    headers['Referer'] = web_url
                    token_response = _http_get(pass_md5_url, headers=headers, timeout=15)
                    
                    if token_response:
                        token_data = token_response.strip()
                        
                        if 'cloudflarestorage.' in token_data:
                            stream_url = token_data
                        else:
                            stream_url = dood_decode(token_data) + token + str(int(time.time() * 1000))
                        
                        xbmc.log(f"DoodStream: Successfully resolved!", xbmc.LOGINFO)
                        return f"{stream_url}|User-Agent={quote(USER_AGENT)}&Referer={quote(web_url)}"
                
                # Method 2: Alternate pattern
                match = re.search(r"\$.get\('(/pass_md5/[^']+)'[^)]+\)\s*\.done\(function\(data\)\s*\{[^}]+return\s+data\s*\+\s*['\"]([^'\"]+)", html, re.DOTALL)
                if match:
                    pass_md5_path = match.group(1)
                    token = match.group(2)
                    pass_md5_url = f"https://{host}{pass_md5_path}"
                    
                    xbmc.log(f"DoodStream: Found alternate pass_md5 URL", xbmc.LOGINFO)
                    
                    headers['Referer'] = web_url
                    token_response = _http_get(pass_md5_url, headers=headers, timeout=15)
                    
                    if token_response:
                        token_data = token_response.strip()
                        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        timestamp = str(int(time.time() * 1000))
                        
                        stream_url = f"{token_data}{random_str}{token}{timestamp}"
                        xbmc.log(f"DoodStream: Resolved via alternate method!", xbmc.LOGINFO)
                        return f"{stream_url}|User-Agent={quote(USER_AGENT)}&Referer={quote(web_url)}"
                
                # Method 3: Simple pass_md5 extraction
                match = re.search(r"(/pass_md5/[^'\"<>\s]+)", html)
                if match:
                    pass_md5_url = f"https://{host}{match.group(1)}"
                    xbmc.log(f"DoodStream: Found simple pass_md5: {pass_md5_url}", xbmc.LOGINFO)
                    
                    headers['Referer'] = web_url
                    token_response = _http_get(pass_md5_url, headers=headers, timeout=15)
                    
                    if token_response:
                        token_data = token_response.strip()
                        stream_url = dood_decode(token_data) + '?token=' + video_id + '&expiry=' + str(int(time.time() * 1000))
                        xbmc.log(f"DoodStream: Resolved via simple method!", xbmc.LOGINFO)
                        return f"{stream_url}|User-Agent={quote(USER_AGENT)}&Referer={quote(web_url)}"
                
                xbmc.log(f"DoodStream: No video source found on {host}", xbmc.LOGWARNING)
                
            except Exception as e:
                xbmc.log(f"DoodStream: Error with {host}: {str(e)}", xbmc.LOGWARNING)
                continue
        
        xbmc.log("DoodStream: All hosts failed to resolve", xbmc.LOGERROR)
        return None
        
    except Exception as e:
        xbmc.log(f"DoodStream resolver error: {str(e)}", xbmc.LOGERROR)
        return None


def search_doodstream(title, year):
    """Search for DoodStream links using multiple methods"""
    results = []
    
    # Clean title for search
    clean_title = re.sub(r'[^\w\s]', '', title).strip()
    
    # Try multiple search queries
    search_queries = [
        f"{clean_title} {year} doodstream",
        f"{clean_title} {year} dood",
        f"{clean_title} doodstream",
        f"{clean_title} {year} site:doodstream.com",
    ]
    
    headers = {'User-Agent': USER_AGENT}
    all_links = []
    
    for query in search_queries[:2]:  # Try first 2 queries
        try:
            search_url = f"https://www.google.com/search?q={quote(query)}"
            xbmc.log(f"DoodStream search: {query}", xbmc.LOGINFO)
            
            html = _http_get(search_url, headers=headers, timeout=10)
            
            if html:
                # Match various dood domains
                links = re.findall(r'(?:dood(?:stream)?|myvidplay|ds2play|d0+d|vidply)\.(?:com|watch|to|so|cx|la|ws|sh|pm|wf|re|yt|stream|pro|work|net|li)/[de]/([a-zA-Z0-9]+)', html)
                all_links.extend(links)
                
                if links:
                    xbmc.log(f"DoodStream: Found {len(links)} links from search", xbmc.LOGINFO)
                    break  # Found links, stop searching
                
        except Exception as e:
            xbmc.log(f"DoodStream search error: {str(e)}", xbmc.LOGWARNING)
            continue
    
    # Remove duplicates
    unique_links = list(dict.fromkeys(all_links))
    
    if not unique_links:
        xbmc.log(f"DoodStream: No links found for '{title} ({year})'", xbmc.LOGWARNING)
    
    for link_id in unique_links[:5]:
        results.append({
            'title': f"{title} - DoodStream",
            'url': f"https://doodstream.com/e/{link_id}",
            'quality': '720p',
            'source': 'DoodStream',
            'direct': True
        })
    
    return results


def build_source_list(title, year, imdb_id=None):
    """Build list of available sources"""
    all_sources = []
    preferred_quality = get_preferred_quality()
    addon = get_addon()
    use_torrents = addon.getSetting('enable_torrent_scrapers') == 'true'
    debrid_services = debrid.get_debrid_services()
    use_debrid = len(debrid_services) > 0
    
    xbmc.log(f"Searching sources for: {title} ({year})", xbmc.LOGINFO)
    xbmc.log(f"Debrid services available: {len(debrid_services)}", xbmc.LOGINFO)
    
    # Search DoodStream
    dood_results = search_doodstream(title, year)
    all_sources.extend(dood_results)
    xbmc.log(f"DoodStream returned {len(dood_results)} sources", xbmc.LOGINFO)
    
    # Torrent sources (if enabled and debrid available)
    if use_torrents and use_debrid:
        xbmc.log("Searching torrent sources...", xbmc.LOGINFO)
        search_query = f"{title} {year}"
        torrent_results = scrapers.search_all(search_query, preferred_quality)
        
        # Check cache status for all torrents
        if torrent_results:
            hashes = []
            for r in torrent_results:
                magnet = r.get('magnet', '')
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
                if hash_match:
                    hashes.append(hash_match.group(1).lower())
            
            # Check cache with first available debrid service
            if hashes and debrid_services:
                _, service = debrid_services[0]
                try:
                    cached = service.check_cache(hashes)
                    for r in torrent_results:
                        magnet = r.get('magnet', '')
                        hash_match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
                        if hash_match:
                            h = hash_match.group(1).lower()
                            if h in cached:
                                r['cached'] = True
                                r['title'] = '[CACHED] ' + r.get('title', '')
                except Exception as e:
                    xbmc.log(f'Cache check failed: {e}', xbmc.LOGWARNING)
        
        # Prioritize cached torrents
        cached_results = [r for r in torrent_results if r.get('cached')]
        uncached_results = [r for r in torrent_results if not r.get('cached')]
        torrent_results = cached_results + uncached_results
        
        all_sources.extend(torrent_results)
        xbmc.log(f"Torrent scrapers returned {len(torrent_results)} sources ({len(cached_results)} cached)", xbmc.LOGINFO)
    elif use_torrents and not use_debrid:
        xbmc.log("Torrents enabled but no debrid service authorized - skipping torrent search", xbmc.LOGWARNING)
    
    xbmc.log(f"Total sources found: {len(all_sources)}", xbmc.LOGINFO)
    return all_sources


def show_source_dialog(sources, title):
    """Show dialog to select source"""
    if not sources:
        xbmcgui.Dialog().notification("No Sources", "No playable links found", xbmcgui.NOTIFICATION_WARNING)
        return None
    
    display_items = []
    for s in sources:
        quality = s.get('quality', 'Unknown')
        source_name = s.get('source', 'Unknown')
        seeds = s.get('seeds', '')
        cached = s.get('cached', False)
        
        if cached:
            label = f"[B][COLOR lime][CACHED][/COLOR][/B] [{quality}] {source_name}"
        elif seeds:
            label = f"[{quality}] {source_name} ({seeds} seeds)"
        else:
            label = f"[{quality}] {source_name}"
        
        if s.get('magnet') and not cached:
            label += " [Debrid]"
        
        display_items.append(label)
    
    dialog = xbmcgui.Dialog()
    selected = dialog.select(f"Select Source - {title}", display_items)
    
    if selected >= 0:
        return sources[selected]
    return None


def play_source(source):
    """Resolve and play selected source"""
    try:
        stream_url = None
        
        if source.get('magnet'):
            xbmcgui.Dialog().notification("Processing", "Resolving via Debrid...", xbmcgui.NOTIFICATION_INFO, 2000)
            stream_url, service_name = debrid.resolve_with_debrid(source['magnet'], is_magnet=True)
            
            if stream_url:
                xbmcgui.Dialog().notification(service_name, "Link resolved!", xbmcgui.NOTIFICATION_INFO, 1500)
        
        elif source.get('url'):
            url = source['url']
            
            # Zeus Resolvers first for supported hosts (Streamtape / DDownloads, no debrid)
            try:
                from resources.lib.zeus_hook import try_zeus
                zeus_url = try_zeus(url)
                if zeus_url:
                    stream_url = zeus_url
                    xbmcgui.Dialog().notification("Zeus Resolvers", "Link resolved (no debrid)", xbmcgui.NOTIFICATION_INFO, 1500)
            except Exception as e:
                xbmc.log(f'Zeus hook error: {e}', xbmc.LOGWARNING)
            
            # Check if it's a DoodStream URL
            if not stream_url and any(domain in url.lower() for domain in ['dood', 'myvidplay', 'ds2play', 'vidply']):
                xbmcgui.Dialog().notification("Processing", "Resolving DoodStream...", xbmcgui.NOTIFICATION_INFO, 2000)
                stream_url = resolve_doodstream(url)
            elif not stream_url:
                stream_url = url
        
        if stream_url:
            # Parse stream URL and headers if present
            if '|' in stream_url:
                url_parts = stream_url.split('|', 1)
                actual_url = url_parts[0]
                header_string = url_parts[1]
                
                li = xbmcgui.ListItem(path=actual_url)
                li.setMimeType('video/mp4')
                li.setContentLookup(False)
                li.setProperty('inputstream.adaptive.stream_headers', header_string)
            else:
                li = xbmcgui.ListItem(path=stream_url)
            
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
            return True
        else:
            xbmc.log(f"Failed to resolve source: {source}", xbmc.LOGWARNING)
            return False
            
    except Exception as e:
        xbmc.log(f"Play error: {str(e)}", xbmc.LOGERROR)
        return False


def auto_play(sources):
    """
    Auto-play best available source based on quality preference.
    Implements proper fallback: if 1080p fails, try next 1080p, then 720p, etc.
    """
    if not sources:
        return False
    
    addon = get_addon()
    preferred = get_preferred_quality()
    enable_fallback = addon.getSetting('quality_fallback') == 'true'
    
    try:
        pref_idx = QUALITY_ORDER.index(preferred)
    except ValueError:
        pref_idx = 1  # Default to 1080p
    
    def quality_score(source):
        """
        Score sources by:
        1. Cached status (cached first)
        2. Quality match (starting from preferred, then lower)
        3. Seeds (higher is better)
        """
        q = source.get('quality', '480p')
        try:
            q_idx = QUALITY_ORDER.index(q)
        except ValueError:
            q_idx = 4  # Unknown quality treated as 480p
        
        cached = 0 if source.get('cached') else 1  # Cached sources first
        
        # If quality is at or below preferred, keep as is
        # If quality is above preferred (better than requested), push to back
        if q_idx >= pref_idx:
            quality_priority = (0, q_idx)  # Primary group: at or below preferred
        else:
            quality_priority = (1, q_idx)  # Secondary: higher than preferred
        
        seeds = source.get('seeds', 0) or 0
        return (cached, quality_priority[0], quality_priority[1], -seeds)
    
    # Sort sources
    sorted_sources = sorted(sources, key=quality_score)
    
    xbmc.log(f"Auto-play: Starting with {len(sorted_sources)} sources, preferred quality: {preferred}", xbmc.LOGINFO)
    
    # Group sources by quality for fallback
    quality_groups = {}
    for source in sorted_sources:
        q = source.get('quality', '480p')
        if q not in quality_groups:
            quality_groups[q] = []
        quality_groups[q].append(source)
    
    # Build ordered list of qualities to try
    if enable_fallback:
        # Start from preferred and go down, then go up
        qualities_to_try = QUALITY_ORDER[pref_idx:] + QUALITY_ORDER[:pref_idx]
    else:
        # Only try preferred quality
        qualities_to_try = [preferred]
    
    tried_count = 0
    max_tries = 10  # Maximum sources to try
    
    for quality in qualities_to_try:
        if quality not in quality_groups:
            continue
        
        for source in quality_groups[quality]:
            if tried_count >= max_tries:
                xbmc.log(f"Auto-play: Max tries ({max_tries}) reached", xbmc.LOGWARNING)
                return False
            
            tried_count += 1
            source_name = source.get('source', 'Unknown')
            source_quality = source.get('quality', 'Unknown')
            is_cached = '[CACHED]' if source.get('cached') else ''
            
            xbmc.log(f"Auto-play: Trying source {tried_count}/{max_tries} - {source_name} [{source_quality}] {is_cached}", xbmc.LOGINFO)
            
            if play_source(source):
                xbmc.log(f"Auto-play: Successfully playing {source_name}", xbmc.LOGINFO)
                return True
            else:
                xbmc.log(f"Auto-play: Source {source_name} failed, trying next...", xbmc.LOGWARNING)
                # Brief pause before trying next
                time.sleep(0.5)
    
    xbmc.log("Auto-play: All sources failed", xbmc.LOGERROR)
    return False


def play_video(title, year, imdb_id=None, auto=True):
    """Main entry point for playing video"""
    dialog = xbmcgui.DialogProgress()
    dialog.create("Finding Sources", f"Searching for {title} ({year})...")
    
    try:
        sources = build_source_list(title, year, imdb_id)
        dialog.close()
        
        if not sources:
            xbmcgui.Dialog().notification("No Sources", f"No links found for {title}", xbmcgui.NOTIFICATION_WARNING, 5000)
            xbmc.log(f"No sources found for: {title} ({year}) - IMDB: {imdb_id}", xbmc.LOGWARNING)
            # Mark as failed so Kodi doesn't keep trying
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
            return
        
        # Count cached sources
        cached_count = len([s for s in sources if s.get('cached')])
        if cached_count > 0:
            xbmcgui.Dialog().notification("Sources Found", f"Found {len(sources)} source(s) ({cached_count} cached)", xbmcgui.NOTIFICATION_INFO, 2000)
        else:
            xbmcgui.Dialog().notification("Sources Found", f"Found {len(sources)} source(s)", xbmcgui.NOTIFICATION_INFO, 2000)
        
        addon = get_addon()
        auto_select = addon.getSetting('auto_play') == 'true'
        
        if auto_select and auto:
            if not auto_play(sources):
                # Auto-play failed, show source selection
                xbmcgui.Dialog().notification("Auto-Play Failed", "Please select a source manually", xbmcgui.NOTIFICATION_WARNING)
                source = show_source_dialog(sources, title)
                if source:
                    if not play_source(source):
                        xbmcgui.Dialog().notification("Error", "Could not play selected source", xbmcgui.NOTIFICATION_ERROR)
                        xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
                else:
                    xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
        else:
            source = show_source_dialog(sources, title)
            if source:
                if not play_source(source):
                    xbmcgui.Dialog().notification("Error", "Could not play selected source", xbmcgui.NOTIFICATION_ERROR)
                    xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
            else:
                xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
                
    except Exception as e:
        dialog.close()
        xbmc.log(f"Play video error: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Error", str(e), xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
