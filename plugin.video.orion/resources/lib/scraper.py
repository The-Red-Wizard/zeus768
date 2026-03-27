# -*- coding: utf-8 -*-
"""
Torrent Scraper for Orion v3.0
Supports: Orionoid, Torrentio, MediaFusion, Jackettio, 1337x, TorrentDownloads, RARBG
"""

import urllib.request
import urllib.parse
import re
import ssl
import json
import base64
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
SSL_CONTEXT = ssl._create_unverified_context()

def _fetch_page(url, timeout=15, headers=None):
    """Fetch HTML page with better error handling"""
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    if headers:
        default_headers.update(headers)
    
    try:
        req = urllib.request.Request(url, headers=default_headers)
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=timeout) as response:
            data = response.read()
            if response.info().get('Content-Encoding') == 'gzip':
                import gzip
                data = gzip.decompress(data)
            return data.decode('utf-8', errors='ignore')
    except Exception as e:
        xbmc.log(f"Scraper error fetching {url}: {e}", xbmc.LOGWARNING)
        return ""

def _fetch_json(url, timeout=15, headers=None):
    """Fetch JSON from API"""
    default_headers = {
        'User-Agent': 'Orion Kodi Addon/3.0',
        'Accept': 'application/json',
    }
    if headers:
        default_headers.update(headers)
    
    try:
        req = urllib.request.Request(url, headers=default_headers)
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        xbmc.log(f"API error: {e}", xbmc.LOGWARNING)
        return None

def _detect_quality(name):
    """Detect video quality from torrent name"""
    name_lower = name.lower()
    
    if any(q in name_lower for q in ['2160p', '4k', 'uhd', 'ultra.hd']):
        return '4K'
    elif any(q in name_lower for q in ['1080p', '1080i', 'fhd', 'fullhd', 'full.hd']):
        return '1080p'
    elif any(q in name_lower for q in ['720p', 'hd', 'hdtv', 'bdrip', 'brrip']):
        return '720p'
    elif any(q in name_lower for q in ['480p', 'dvdrip', 'dvd', 'sd', 'webrip', 'hdcam', 'cam']):
        return 'SD'
    else:
        if 'bluray' in name_lower or 'blu-ray' in name_lower:
            return '1080p'
        elif 'web-dl' in name_lower or 'webdl' in name_lower:
            return '1080p'
        return 'Unknown'

def _create_magnet(info_hash, name):
    """Create magnet link from info hash"""
    trackers = [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://open.stealth.si:80/announce",
        "udp://tracker.torrent.eu.org:451/announce",
        "udp://tracker.bittor.pw:1337/announce",
        "udp://public.popcorn-tracker.org:6969/announce",
        "udp://tracker.dler.org:6969/announce",
        "udp://exodus.desync.com:6969",
    ]
    
    encoded_name = urllib.parse.quote(name)
    tracker_params = "&".join([f"tr={urllib.parse.quote(t)}" for t in trackers])
    
    return f"magnet:?xt=urn:btih:{info_hash}&dn={encoded_name}&{tracker_params}"

def _parse_size(size_str):
    """Parse size string to bytes for comparison"""
    try:
        size_str = size_str.upper().replace(' ', '')
        if 'GB' in size_str:
            return float(size_str.replace('GB', '')) * 1073741824
        elif 'MB' in size_str:
            return float(size_str.replace('MB', '')) * 1048576
        elif 'KB' in size_str:
            return float(size_str.replace('KB', '')) * 1024
    except:
        pass
    return 0

# ============== ORIONOID ==============

def _search_orionoid(query, media_type='movie', imdb_id=None):
    """Search Orionoid API with user's API key"""
    results = []
    
    api_key = ADDON.getSetting('orionoid_api_key')
    if not api_key:
        xbmc.log("Orionoid: No API key configured", xbmc.LOGINFO)
        return results
    
    try:
        params = {
            'keyapp': api_key,
            'mode': 'stream',
            'action': 'retrieve',
            'type': media_type,
            'streamtype': 'torrent',
            'limitcount': 30,
        }
        
        if imdb_id:
            params['idimdb'] = imdb_id.replace('tt', '')
        else:
            params['query'] = query
        
        url = f"https://api.orionoid.com?{urllib.parse.urlencode(params)}"
        
        xbmc.log(f"Orionoid search: {query}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=20)
        
        if not data:
            return results
        
        if data.get('result', {}).get('status') != 'success':
            error = data.get('result', {}).get('message', 'Unknown error')
            xbmc.log(f"Orionoid API error: {error}", xbmc.LOGWARNING)
            return results
        
        streams = data.get('data', {}).get('streams', [])
        
        for stream in streams:
            try:
                file_info = stream.get('file', {})
                video_info = stream.get('video', {})
                
                name = file_info.get('name', 'Unknown')
                
                links = stream.get('links', [])
                magnet = None
                for link in links:
                    if link.startswith('magnet:'):
                        magnet = link
                        break
                
                if not magnet:
                    file_hash = file_info.get('hash')
                    if file_hash:
                        magnet = _create_magnet(file_hash, name)
                
                if not magnet:
                    continue
                
                quality = video_info.get('quality', '').upper()
                if quality in ['HD1080', 'FHD']:
                    quality = '1080p'
                elif quality in ['HD720', 'HD']:
                    quality = '720p'
                elif quality in ['UHD', 'UHD4K', '4K']:
                    quality = '4K'
                elif quality in ['SD', 'CAM', 'SCR']:
                    quality = 'SD'
                else:
                    quality = _detect_quality(name)
                
                size_bytes = file_info.get('size', 0)
                if size_bytes > 1073741824:
                    size = f"{size_bytes / 1073741824:.1f} GB"
                elif size_bytes > 1048576:
                    size = f"{size_bytes / 1048576:.0f} MB"
                else:
                    size = ''
                
                seeds = stream.get('stream', {}).get('seeds', 0)
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': 'Orionoid',
                    'source_type': 'orionoid',
                    'debrid': True
                })
                
            except Exception as e:
                xbmc.log(f"Error parsing Orionoid stream: {e}", xbmc.LOGWARNING)
                continue
        
        xbmc.log(f"Orionoid found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"Orionoid search error: {e}", xbmc.LOGERROR)
    
    return results

# ============== TORRENTIO ==============

def _search_torrentio(imdb_id, media_type='movie', season=None, episode=None):
    """Search Torrentio public API"""
    results = []
    
    if not imdb_id:
        return results
    
    try:
        # Build Torrentio stream URL
        if media_type == 'movie':
            url = f"https://torrentio.strem.fun/stream/movie/{imdb_id}.json"
        else:
            url = f"https://torrentio.strem.fun/stream/series/{imdb_id}:{season}:{episode}.json"
        
        xbmc.log(f"Torrentio search: {url}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=20)
        
        if not data or 'streams' not in data:
            return results
        
        for stream in data.get('streams', []):
            try:
                title = stream.get('title', '')
                info_hash = stream.get('infoHash', '')
                
                if not info_hash:
                    # Try to extract from behaviorHints
                    behavior = stream.get('behaviorHints', {})
                    info_hash = behavior.get('bingeGroup', '').split('|')[-1] if behavior.get('bingeGroup') else ''
                
                if not info_hash:
                    continue
                
                # Parse title for name and metadata
                lines = title.split('\n')
                name = lines[0] if lines else 'Unknown'
                
                # Extract quality, size, seeds from title
                quality = _detect_quality(name)
                size = ''
                seeds = 0
                
                for line in lines:
                    if 'GB' in line or 'MB' in line:
                        size_match = re.search(r'([\d.]+\s*[GM]B)', line)
                        if size_match:
                            size = size_match.group(1)
                    if '👤' in line or 'Seeds' in line.lower():
                        seeds_match = re.search(r'(\d+)', line)
                        if seeds_match:
                            seeds = int(seeds_match.group(1))
                
                magnet = _create_magnet(info_hash, name)
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': 'Torrentio',
                    'source_type': 'torrentio',
                    'debrid': True
                })
                
            except Exception as e:
                xbmc.log(f"Error parsing Torrentio stream: {e}", xbmc.LOGWARNING)
                continue
        
        xbmc.log(f"Torrentio found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"Torrentio search error: {e}", xbmc.LOGERROR)
    
    return results

# ============== MEDIAFUSION ==============

def _search_mediafusion(imdb_id, media_type='movie', season=None, episode=None):
    """Search MediaFusion with user's manifest"""
    results = []
    
    manifest_url = ADDON.getSetting('mediafusion_manifest')
    if not manifest_url:
        return results
    
    try:
        # Extract base URL from manifest
        base_url = manifest_url.rsplit('/manifest.json', 1)[0]
        if not base_url:
            base_url = manifest_url.rsplit('/configure', 1)[0]
        
        # Build stream URL
        if media_type == 'movie':
            url = f"{base_url}/stream/movie/{imdb_id}.json"
        else:
            url = f"{base_url}/stream/series/{imdb_id}:{season}:{episode}.json"
        
        xbmc.log(f"MediaFusion search: {url}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=25)
        
        if not data or 'streams' not in data:
            return results
        
        for stream in data.get('streams', []):
            try:
                title = stream.get('title', stream.get('name', ''))
                info_hash = stream.get('infoHash', '')
                
                if not info_hash:
                    # Try to get from URL or behaviorHints
                    url_field = stream.get('url', '')
                    if 'magnet:' in url_field:
                        hash_match = re.search(r'btih:([a-fA-F0-9]{40})', url_field, re.IGNORECASE)
                        if hash_match:
                            info_hash = hash_match.group(1)
                
                if not info_hash:
                    continue
                
                lines = title.split('\n')
                name = lines[0] if lines else 'Unknown'
                
                quality = _detect_quality(name)
                size = ''
                seeds = 0
                
                for line in lines:
                    if 'GB' in line or 'MB' in line:
                        size_match = re.search(r'([\d.]+\s*[GM]B)', line)
                        if size_match:
                            size = size_match.group(1)
                    if '👤' in line or 'seed' in line.lower():
                        seeds_match = re.search(r'(\d+)', line)
                        if seeds_match:
                            seeds = int(seeds_match.group(1))
                
                magnet = _create_magnet(info_hash, name)
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': 'MediaFusion',
                    'source_type': 'mediafusion',
                    'debrid': True
                })
                
            except Exception as e:
                xbmc.log(f"Error parsing MediaFusion stream: {e}", xbmc.LOGWARNING)
                continue
        
        xbmc.log(f"MediaFusion found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"MediaFusion search error: {e}", xbmc.LOGERROR)
    
    return results

# ============== JACKETTIO ==============

def _search_jackettio(imdb_id, media_type='movie', season=None, episode=None):
    """Search Jackettio with user's manifest"""
    results = []
    
    manifest_url = ADDON.getSetting('jackettio_manifest')
    if not manifest_url:
        # Use public instance as fallback
        manifest_url = "https://jackettio.elfhosted.com/manifest.json"
    
    try:
        # Extract base URL from manifest
        base_url = manifest_url.rsplit('/manifest.json', 1)[0]
        
        # Build stream URL
        if media_type == 'movie':
            url = f"{base_url}/stream/movie/{imdb_id}.json"
        else:
            url = f"{base_url}/stream/series/{imdb_id}:{season}:{episode}.json"
        
        xbmc.log(f"Jackettio search: {url}", xbmc.LOGINFO)
        
        data = _fetch_json(url, timeout=25)
        
        if not data or 'streams' not in data:
            return results
        
        for stream in data.get('streams', []):
            try:
                title = stream.get('title', stream.get('name', ''))
                info_hash = stream.get('infoHash', '')
                
                if not info_hash:
                    url_field = stream.get('url', '')
                    if 'magnet:' in url_field:
                        hash_match = re.search(r'btih:([a-fA-F0-9]{40})', url_field, re.IGNORECASE)
                        if hash_match:
                            info_hash = hash_match.group(1)
                
                if not info_hash:
                    continue
                
                lines = title.split('\n')
                name = lines[0] if lines else 'Unknown'
                
                quality = _detect_quality(name)
                size = ''
                seeds = 0
                
                for line in lines:
                    if 'GB' in line or 'MB' in line:
                        size_match = re.search(r'([\d.]+\s*[GM]B)', line)
                        if size_match:
                            size = size_match.group(1)
                    if '👤' in line or 'seed' in line.lower():
                        seeds_match = re.search(r'(\d+)', line)
                        if seeds_match:
                            seeds = int(seeds_match.group(1))
                
                magnet = _create_magnet(info_hash, name)
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': quality,
                    'size': size,
                    'seeds': seeds,
                    'source': 'Jackettio',
                    'source_type': 'jackettio',
                    'debrid': True
                })
                
            except Exception as e:
                xbmc.log(f"Error parsing Jackettio stream: {e}", xbmc.LOGWARNING)
                continue
        
        xbmc.log(f"Jackettio found {len(results)} results", xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f"Jackettio search error: {e}", xbmc.LOGERROR)
    
    return results

# ============== COCO SCRAPERS (1337x, TorrentDownloads, RARBG) ==============

def _parse_1337x(html, search_title):
    """Parse 1337x results"""
    results = []
    clean_search = search_title.lower()
    
    pattern = r'<a href="(/torrent/\d+/[^"]+)"[^>]*>([^<]+)</a>'
    matches = re.findall(pattern, html)
    
    for link, name in matches[:15]:
        if not any(word in name.lower() for word in clean_search.split()[:2]):
            continue
        
        results.append({
            'name': name.strip(),
            'quality': _detect_quality(name),
            'size': '',
            'seeds': 0,
            'source': '1337x',
            'source_type': 'coco',
            'debrid': True,
            'page_url': f"https://1337x.to{link}"
        })
    
    return results

def _get_magnet_from_1337x(page_url):
    """Get magnet link from 1337x torrent page"""
    html = _fetch_page(page_url)
    if html:
        match = re.search(r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)', html)
        if match:
            return match.group(1)
    return None

def _parse_torrentdownloads(html, search_title):
    """Parse TorrentDownloads results"""
    results = []
    clean_search = search_title.lower()
    
    magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
    magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
    
    for magnet in magnets[:20]:
        dn_match = re.search(r'dn=([^&]+)', magnet)
        if dn_match:
            name = urllib.parse.unquote_plus(dn_match.group(1))
        else:
            continue
        
        if not any(word in name.lower() for word in clean_search.split()[:2]):
            continue
        
        results.append({
            'name': name,
            'magnet': magnet,
            'quality': _detect_quality(name),
            'size': '',
            'seeds': 0,
            'source': 'TorrentDownloads',
            'source_type': 'coco',
            'debrid': True
        })
    
    return results

def _search_rarbg_alternatives(query):
    """Search RARBG alternative mirrors"""
    results = []
    
    mirrors = [
        'https://rargb.to',
        'https://therarbg.to',
    ]
    
    for mirror in mirrors:
        try:
            url = f"{mirror}/search/?search={urllib.parse.quote_plus(query)}"
            html = _fetch_page(url, timeout=10)
            
            if not html:
                continue
            
            # Parse magnet links
            magnet_pattern = r'(magnet:\?xt=urn:btih:[^"\'<>\s]+)'
            magnets = re.findall(magnet_pattern, html, re.IGNORECASE)
            
            for magnet in magnets[:15]:
                dn_match = re.search(r'dn=([^&]+)', magnet)
                name = urllib.parse.unquote_plus(dn_match.group(1)) if dn_match else 'Unknown'
                
                results.append({
                    'name': name,
                    'magnet': magnet,
                    'quality': _detect_quality(name),
                    'size': '',
                    'seeds': 0,
                    'source': 'RARBG',
                    'source_type': 'coco',
                    'debrid': True
                })
            
            if results:
                break
                
        except Exception as e:
            xbmc.log(f"RARBG mirror error: {e}", xbmc.LOGWARNING)
            continue
    
    return results

# ============== MAIN SEARCH FUNCTIONS ==============

def get_imdb_from_tmdb(tmdb_id, media_type='movie'):
    """Get IMDB ID from TMDB ID"""
    from resources.lib import tmdb
    
    try:
        ids = tmdb.get_external_ids(media_type, tmdb_id)
        return ids.get('imdb_id', '')
    except:
        return ''

def search_movie(title, year='', tmdb_id=None, progress=None):
    """Search for movie sources across all enabled scrapers"""
    results = []
    seen_hashes = set()
    
    search_query = f"{title} {year}".strip() if year else title
    
    # Get IMDB ID for stremio-based scrapers
    imdb_id = None
    if tmdb_id:
        imdb_id = get_imdb_from_tmdb(tmdb_id, 'movie')
    
    scraper_mode = int(ADDON.getSetting('scraper_mode') or 0)
    
    # ORION SCRAPERS MODE
    if scraper_mode == 0:
        # 1. Orionoid
        if ADDON.getSetting('orionoid_enabled') == 'true':
            if progress:
                progress.update(10, "Searching Orionoid...")
            
            orion_results = _search_orionoid(search_query, 'movie', imdb_id)
            for r in orion_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 2. Torrentio
        if ADDON.getSetting('torrentio_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(30, "Searching Torrentio...")
            
            torrentio_results = _search_torrentio(imdb_id, 'movie')
            for r in torrentio_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 3. MediaFusion
        if ADDON.getSetting('mediafusion_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(50, "Searching MediaFusion...")
            
            mf_results = _search_mediafusion(imdb_id, 'movie')
            for r in mf_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 4. Jackettio
        if ADDON.getSetting('jackettio_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(70, "Searching Jackettio...")
            
            jk_results = _search_jackettio(imdb_id, 'movie')
            for r in jk_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
    
    # COCO SCRAPERS MODE
    else:
        # 1. 1337x
        if ADDON.getSetting('coco_1337x') == 'true':
            if progress:
                progress.update(20, "Searching 1337x...")
            
            try:
                query = urllib.parse.quote_plus(search_query)
                url = f"https://1337x.to/search/{query}/1/"
                html = _fetch_page(url)
                if html:
                    found = _parse_1337x(html, search_query)
                    for r in found:
                        results.append(r)
            except Exception as e:
                xbmc.log(f"1337x error: {e}", xbmc.LOGWARNING)
        
        # 2. TorrentDownloads
        if ADDON.getSetting('coco_torrentdownloads') == 'true':
            if progress:
                progress.update(50, "Searching TorrentDownloads...")
            
            try:
                query = urllib.parse.quote_plus(search_query)
                url = f"https://www.torrentdownloads.pro/search/?search={query}"
                html = _fetch_page(url)
                if html:
                    found = _parse_torrentdownloads(html, search_query)
                    for r in found:
                        if 'magnet' in r:
                            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r['magnet'], re.IGNORECASE)
                            if hash_match:
                                h = hash_match.group(1).upper()
                                if h in seen_hashes:
                                    continue
                                seen_hashes.add(h)
                        results.append(r)
            except Exception as e:
                xbmc.log(f"TorrentDownloads error: {e}", xbmc.LOGWARNING)
        
        # 3. RARBG
        if ADDON.getSetting('coco_rarbg') == 'true':
            if progress:
                progress.update(70, "Searching RARBG...")
            
            rarbg_results = _search_rarbg_alternatives(search_query)
            for r in rarbg_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
    
    # Get magnets for results that need them (1337x)
    if progress:
        progress.update(85, "Fetching magnet links...")
    
    for r in results:
        if 'magnet' not in r and 'page_url' in r:
            magnet = _get_magnet_from_1337x(r['page_url'])
            if magnet:
                r['magnet'] = magnet
    
    # Filter out results without magnets
    results = [r for r in results if r.get('magnet')]
    
    if progress:
        progress.update(95, f"Found {len(results)} sources")
    
    return results

def search_episode(title, season, episode, tmdb_id=None, progress=None):
    """Search for TV episode sources across all enabled scrapers"""
    results = []
    seen_hashes = set()
    
    search_query = f"{title} S{int(season):02d}E{int(episode):02d}"
    
    # Get IMDB ID for stremio-based scrapers
    imdb_id = None
    if tmdb_id:
        imdb_id = get_imdb_from_tmdb(tmdb_id, 'tv')
    
    scraper_mode = int(ADDON.getSetting('scraper_mode') or 0)
    
    # ORION SCRAPERS MODE
    if scraper_mode == 0:
        # 1. Orionoid
        if ADDON.getSetting('orionoid_enabled') == 'true':
            if progress:
                progress.update(10, "Searching Orionoid...")
            
            orion_results = _search_orionoid(search_query, 'show', imdb_id)
            for r in orion_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 2. Torrentio
        if ADDON.getSetting('torrentio_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(30, "Searching Torrentio...")
            
            torrentio_results = _search_torrentio(imdb_id, 'tv', season, episode)
            for r in torrentio_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 3. MediaFusion
        if ADDON.getSetting('mediafusion_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(50, "Searching MediaFusion...")
            
            mf_results = _search_mediafusion(imdb_id, 'tv', season, episode)
            for r in mf_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
        
        # 4. Jackettio
        if ADDON.getSetting('jackettio_enabled') == 'true' and imdb_id:
            if progress:
                progress.update(70, "Searching Jackettio...")
            
            jk_results = _search_jackettio(imdb_id, 'tv', season, episode)
            for r in jk_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
    
    # COCO SCRAPERS MODE
    else:
        # 1. 1337x
        if ADDON.getSetting('coco_1337x') == 'true':
            if progress:
                progress.update(20, "Searching 1337x...")
            
            try:
                query = urllib.parse.quote_plus(search_query)
                url = f"https://1337x.to/search/{query}/1/"
                html = _fetch_page(url)
                if html:
                    found = _parse_1337x(html, search_query)
                    for r in found:
                        results.append(r)
            except Exception as e:
                xbmc.log(f"1337x error: {e}", xbmc.LOGWARNING)
        
        # 2. TorrentDownloads
        if ADDON.getSetting('coco_torrentdownloads') == 'true':
            if progress:
                progress.update(50, "Searching TorrentDownloads...")
            
            try:
                query = urllib.parse.quote_plus(search_query)
                url = f"https://www.torrentdownloads.pro/search/?search={query}"
                html = _fetch_page(url)
                if html:
                    found = _parse_torrentdownloads(html, search_query)
                    for r in found:
                        if 'magnet' in r:
                            hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r['magnet'], re.IGNORECASE)
                            if hash_match:
                                h = hash_match.group(1).upper()
                                if h in seen_hashes:
                                    continue
                                seen_hashes.add(h)
                        results.append(r)
            except Exception as e:
                xbmc.log(f"TorrentDownloads error: {e}", xbmc.LOGWARNING)
        
        # 3. RARBG
        if ADDON.getSetting('coco_rarbg') == 'true':
            if progress:
                progress.update(70, "Searching RARBG...")
            
            rarbg_results = _search_rarbg_alternatives(search_query)
            for r in rarbg_results:
                hash_match = re.search(r'btih:([a-fA-F0-9]{40})', r.get('magnet', ''), re.IGNORECASE)
                if hash_match:
                    h = hash_match.group(1).upper()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        results.append(r)
    
    # Get magnets for results that need them
    if progress:
        progress.update(85, "Fetching magnet links...")
    
    for r in results:
        if 'magnet' not in r and 'page_url' in r:
            magnet = _get_magnet_from_1337x(r['page_url'])
            if magnet:
                r['magnet'] = magnet
    
    results = [r for r in results if r.get('magnet')]
    
    if progress:
        progress.update(95, f"Found {len(results)} sources")
    
    return results

def sort_sources(sources, quality_filter=None):
    """Sort sources by quality and type, with optional filtering"""
    
    quality_order = {'4K': 0, '2160p': 0, '1080p': 1, '720p': 2, 'SD': 3, '480p': 3, 'Unknown': 4}
    
    if quality_filter and quality_filter != 'all':
        filter_map = {
            '4k': ['4K', '2160p'],
            '1080p': ['1080p'],
            '720p': ['720p'],
            'sd': ['SD', '480p']
        }
        allowed = filter_map.get(quality_filter.lower(), [])
        if allowed:
            sources = [s for s in sources if s.get('quality') in allowed]
    
    sorted_sources = sorted(
        sources,
        key=lambda x: (
            quality_order.get(x.get('quality', 'Unknown'), 4),
            -x.get('seeds', 0)
        )
    )
    
    return sorted_sources

def filter_sources_by_type(sources, source_type=None):
    """Filter sources by type"""
    if not source_type or source_type == 'all':
        return sources
    
    if source_type == 'debrid':
        return [s for s in sources if s.get('debrid')]
    elif source_type == 'orionoid':
        return [s for s in sources if s.get('source_type') == 'orionoid']
    elif source_type == 'torrentio':
        return [s for s in sources if s.get('source_type') == 'torrentio']
    elif source_type == 'mediafusion':
        return [s for s in sources if s.get('source_type') == 'mediafusion']
    elif source_type == 'jackettio':
        return [s for s in sources if s.get('source_type') == 'jackettio']
    elif source_type == 'coco':
        return [s for s in sources if s.get('source_type') == 'coco']
    
    return sources
