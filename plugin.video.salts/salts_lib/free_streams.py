"""
SALTS - Free Stream Providers
Extracts playable stream URLs from free embed APIs using TMDB/IMDB IDs.
No debrid required - plays straight in Kodi player.

Approach: Follow request chains from embed pages to find actual video URLs.
These providers use JavaScript to load streams, so we follow the known
API/redirect chains that the JS would normally call.
"""
import re
import json
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus, urljoin

ADDON = xbmcaddon.Addon()
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'


def _fetch(url, headers=None, timeout=12):
    """Fetch URL, return response text"""
    hdrs = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    if headers:
        hdrs.update(headers)
    try:
        req = Request(url, headers=hdrs)
        resp = urlopen(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        xbmc.log(f'SALTS FreeStream fetch error ({url[:80]}): {e}', xbmc.LOGDEBUG)
        return ''


def _fetch_json(url, headers=None, timeout=12):
    """Fetch URL, return parsed JSON or None"""
    hdrs = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
    }
    if headers:
        hdrs.update(headers)
    try:
        req = Request(url, headers=hdrs)
        resp = urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode('utf-8', errors='replace'))
    except Exception as e:
        xbmc.log(f'SALTS FreeStream JSON error ({url[:80]}): {e}', xbmc.LOGDEBUG)
        return None


def _is_video_url(url):
    """Check if URL looks like an actual video stream (not a webpage/script)"""
    if not url or not url.startswith('http'):
        return False
    # Must contain video indicators
    video_exts = ['.m3u8', '.mp4', '.mkv', '.avi', '.ts', '.mpd']
    video_hosts = ['cdn', 'stream', 'video', 'play', 'hls', 'vod', 'media', 'deliver']
    
    url_lower = url.lower()
    # Reject obvious non-video URLs
    reject = ['.js', '.css', '.html', '.php', '.json', 'github.com', 'googleapis.com/ajax',
              'jquery', 'bootstrap', '.png', '.jpg', '.gif', '.svg', '.ico', 'font']
    if any(r in url_lower for r in reject):
        return False
    
    # Accept if has video extension
    if any(ext in url_lower for ext in video_exts):
        return True
    
    # Accept if host looks like a CDN/stream server
    if any(h in url_lower for h in video_hosts):
        return True
    
    return False


def _guess_quality(url):
    """Guess quality from URL"""
    url_lower = url.lower()
    if '4k' in url_lower or '2160' in url_lower:
        return '4K'
    elif '1080' in url_lower:
        return '1080p'
    elif '720' in url_lower:
        return '720p'
    elif '480' in url_lower:
        return '480p'
    return 'HD'


# ==================== Provider: VidSrc.to ====================

def _vidsrc_to(tmdb_id, media_type='movie', season='', episode=''):
    """VidSrc.to - Follow the AJAX source chain"""
    sources = []
    if not tmdb_id:
        return sources
    
    try:
        # Step 1: Get embed page to find source IDs
        if media_type == 'movie':
            embed_url = f'https://vidsrc.to/embed/movie/{tmdb_id}'
        else:
            embed_url = f'https://vidsrc.to/embed/tv/{tmdb_id}/{season}/{episode}'
        
        html = _fetch(embed_url, headers={'Referer': 'https://vidsrc.to/'})
        if not html:
            return sources
        
        # Find data-id attributes for source buttons
        source_ids = re.findall(r'data-id=["\']([^"\']+)["\']', html)
        if not source_ids:
            # Try alternate patterns
            source_ids = re.findall(r'/ajax/embed/episode/([^/\s"\']+)', html)
        
        for src_id in source_ids[:3]:  # Limit to first 3 sources
            try:
                # Step 2: Get sources for this embed
                ajax_url = f'https://vidsrc.to/ajax/embed/episode/{src_id}/sources'
                data = _fetch_json(ajax_url, headers={
                    'Referer': embed_url,
                })
                
                if not data or data.get('status') != 200:
                    continue
                
                for source in data.get('result', []):
                    source_id = source.get('id', '')
                    source_title = source.get('title', 'Unknown')
                    
                    if not source_id:
                        continue
                    
                    # Step 3: Get the actual URL for this source
                    source_url = f'https://vidsrc.to/ajax/embed/source/{source_id}'
                    source_data = _fetch_json(source_url, headers={
                        'Referer': embed_url,
                    })
                    
                    if source_data and source_data.get('status') == 200:
                        result_url = source_data.get('result', {}).get('url', '')
                        if result_url and _is_video_url(result_url):
                            sources.append({
                                'url': result_url,
                                'quality': _guess_quality(result_url),
                                'provider': f'VidSrc.to ({source_title})',
                                'direct': True
                            })
                        elif result_url:
                            # May be an encrypted/encoded URL - still try it
                            sources.append({
                                'url': result_url,
                                'quality': 'HD',
                                'provider': f'VidSrc.to ({source_title})',
                                'direct': True
                            })
                            
            except Exception as e:
                xbmc.log(f'SALTS VidSrc.to source {src_id}: {e}', xbmc.LOGDEBUG)
                
    except Exception as e:
        xbmc.log(f'SALTS VidSrc.to error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Provider: VidSrc.icu ====================

def _vidsrc_icu(tmdb_id, imdb_id='', media_type='movie', season='', episode=''):
    """VidSrc.icu - Embed provider with simpler chain"""
    sources = []
    vid_id = imdb_id or tmdb_id
    if not vid_id:
        return sources
    
    domains = ['vidsrc.icu', 'vidsrc.cc']
    
    for domain in domains:
        try:
            if media_type == 'movie':
                embed_url = f'https://{domain}/embed/movie/{vid_id}'
            else:
                embed_url = f'https://{domain}/embed/tv/{vid_id}/{season}/{episode}'
            
            html = _fetch(embed_url, headers={'Referer': f'https://{domain}/'})
            if not html or len(html) < 200:
                continue
            
            # Look for source/file URLs in the page
            # These providers sometimes have the m3u8 URL in a JS variable
            patterns = [
                r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'playbackUrl["\s:]+["\']([^"\']+)["\']',
                r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            ]
            
            for pattern in patterns:
                for match in re.findall(pattern, html):
                    if _is_video_url(match):
                        sources.append({
                            'url': match,
                            'quality': _guess_quality(match),
                            'provider': f'VidSrc ({domain})',
                            'direct': True
                        })
            
            # Also look for iframe sources to follow
            iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
            for iframe_url in iframes[:2]:
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                if not iframe_url.startswith('http'):
                    continue
                    
                iframe_html = _fetch(iframe_url, headers={'Referer': embed_url})
                if iframe_html:
                    for pattern in patterns:
                        for match in re.findall(pattern, iframe_html):
                            if _is_video_url(match):
                                sources.append({
                                    'url': match,
                                    'quality': _guess_quality(match),
                                    'provider': f'VidSrc ({domain})',
                                    'direct': True
                                })
            
            if sources:
                break
                
        except Exception as e:
            xbmc.log(f'SALTS VidSrc ({domain}) error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Provider: 2Embed ====================

def _2embed(tmdb_id, imdb_id='', media_type='movie', season='', episode=''):
    """2Embed - Follow iframe chain"""
    sources = []
    vid_id = imdb_id or tmdb_id
    if not vid_id:
        return sources
    
    domains = ['www.2embed.cc', '2embed.skin']
    
    for domain in domains:
        try:
            if media_type == 'movie':
                embed_url = f'https://{domain}/embed/{vid_id}'
            else:
                embed_url = f'https://{domain}/embedtv/{vid_id}&s={season}&e={episode}'
            
            html = _fetch(embed_url, headers={'Referer': f'https://{domain}/'})
            if not html or len(html) < 200:
                continue
            
            # Find server sources
            server_ids = re.findall(r'data-id=["\']([^"\']+)["\']', html)
            iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
            
            # Follow iframes
            for iframe_url in iframes[:3]:
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                if not iframe_url.startswith('http'):
                    continue
                
                iframe_html = _fetch(iframe_url, headers={'Referer': embed_url})
                if not iframe_html:
                    continue
                
                # Extract video URLs from iframe content
                video_patterns = [
                    r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                    r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
                ]
                
                for pattern in video_patterns:
                    for match in re.findall(pattern, iframe_html):
                        if _is_video_url(match):
                            sources.append({
                                'url': match,
                                'quality': _guess_quality(match),
                                'provider': '2Embed',
                                'direct': True
                            })
            
            if sources:
                break
                
        except Exception as e:
            xbmc.log(f'SALTS 2Embed ({domain}) error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Provider: Embed.su ====================

def _embedsu(tmdb_id, media_type='movie', season='', episode=''):
    """Embed.su - Follow embed chain"""
    sources = []
    if not tmdb_id:
        return sources
    
    try:
        if media_type == 'movie':
            embed_url = f'https://embed.su/embed/movie/{tmdb_id}'
        else:
            embed_url = f'https://embed.su/embed/tv/{tmdb_id}/{season}/{episode}'
        
        html = _fetch(embed_url, headers={'Referer': 'https://embed.su/'})
        if not html:
            return sources
        
        # Embed.su uses atob (base64) encoded source URLs in script tags
        b64_pattern = r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)'
        for b64_match in re.findall(b64_pattern, html):
            try:
                import base64
                decoded = base64.b64decode(b64_match).decode('utf-8', errors='replace')
                if _is_video_url(decoded):
                    sources.append({
                        'url': decoded,
                        'quality': _guess_quality(decoded),
                        'provider': 'Embed.su',
                        'direct': True
                    })
            except Exception:
                pass
        
        # Also check for direct video URLs
        patterns = [
            r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]
        for pattern in patterns:
            for match in re.findall(pattern, html):
                if _is_video_url(match):
                    sources.append({
                        'url': match,
                        'quality': _guess_quality(match),
                        'provider': 'Embed.su',
                        'direct': True
                    })
                    
    except Exception as e:
        xbmc.log(f'SALTS Embed.su error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Provider: VidLink ====================

def _vidlink(tmdb_id, media_type='movie', season='', episode=''):
    """VidLink.pro - Follow redirect/embed chain"""
    sources = []
    if not tmdb_id:
        return sources
    
    try:
        if media_type == 'movie':
            embed_url = f'https://vidlink.pro/movie/{tmdb_id}'
        else:
            embed_url = f'https://vidlink.pro/tv/{tmdb_id}/{season}/{episode}'
        
        html = _fetch(embed_url, headers={'Referer': 'https://vidlink.pro/'})
        if not html:
            return sources
        
        patterns = [
            r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'src\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
        ]
        
        for pattern in patterns:
            for match in re.findall(pattern, html):
                if _is_video_url(match):
                    sources.append({
                        'url': match,
                        'quality': _guess_quality(match),
                        'provider': 'VidLink',
                        'direct': True
                    })
        
        # Follow iframes
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
        for iframe_url in iframes[:2]:
            if iframe_url.startswith('//'):
                iframe_url = 'https:' + iframe_url
            if not iframe_url.startswith('http'):
                continue
            iframe_html = _fetch(iframe_url, headers={'Referer': embed_url})
            if iframe_html:
                for pattern in patterns:
                    for match in re.findall(pattern, iframe_html):
                        if _is_video_url(match):
                            sources.append({
                                'url': match,
                                'quality': _guess_quality(match),
                                'provider': 'VidLink',
                                'direct': True
                            })
                            
    except Exception as e:
        xbmc.log(f'SALTS VidLink error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Provider: SuperEmbed ====================

def _superembed(tmdb_id, imdb_id='', media_type='movie', season='', episode=''):
    """SuperEmbed - Aggregator that combines multiple sources"""
    sources = []
    vid_id = imdb_id or tmdb_id
    if not vid_id:
        return sources
    
    try:
        if media_type == 'movie':
            embed_url = f'https://multiembed.mov/?video_id={vid_id}&tmdb=1'
        else:
            embed_url = f'https://multiembed.mov/?video_id={vid_id}&tmdb=1&s={season}&e={episode}'
        
        html = _fetch(embed_url, headers={'Referer': 'https://multiembed.mov/'})
        if not html:
            return sources
        
        patterns = [
            r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
        ]
        
        for pattern in patterns:
            for match in re.findall(pattern, html):
                if _is_video_url(match):
                    sources.append({
                        'url': match,
                        'quality': _guess_quality(match),
                        'provider': 'MultiEmbed',
                        'direct': True
                    })
        
        # Follow iframes
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
        for iframe_url in iframes[:3]:
            if iframe_url.startswith('//'):
                iframe_url = 'https:' + iframe_url
            if not iframe_url.startswith('http'):
                continue
            iframe_html = _fetch(iframe_url, headers={'Referer': embed_url})
            if iframe_html:
                for pattern in patterns:
                    for match in re.findall(pattern, iframe_html):
                        if _is_video_url(match):
                            sources.append({
                                'url': match,
                                'quality': _guess_quality(match),
                                'provider': 'MultiEmbed',
                                'direct': True
                            })
                            
    except Exception as e:
        xbmc.log(f'SALTS MultiEmbed error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Main Entry ====================

def get_free_streams(tmdb_id='', imdb_id='', title='', year='',
                     media_type='movie', season='', episode=''):
    """
    Get free streams from all providers.
    Returns list of dicts: {url, quality, provider, direct}
    """
    all_sources = []
    
    if not tmdb_id and not imdb_id:
        tmdb_id = _search_tmdb_id(title, year, media_type)
    
    if not tmdb_id and not imdb_id:
        xbmc.log('SALTS FreeStream: No TMDB/IMDB ID available', xbmc.LOGDEBUG)
        return all_sources
    
    providers = [
        ('VidSrc.to', lambda: _vidsrc_to(tmdb_id, media_type, season, episode)),
        ('VidSrc.icu', lambda: _vidsrc_icu(tmdb_id, imdb_id, media_type, season, episode)),
        ('2Embed', lambda: _2embed(tmdb_id, imdb_id, media_type, season, episode)),
        ('Embed.su', lambda: _embedsu(tmdb_id, media_type, season, episode)),
        ('VidLink', lambda: _vidlink(tmdb_id, media_type, season, episode)),
        ('MultiEmbed', lambda: _superembed(tmdb_id, imdb_id, media_type, season, episode)),
    ]
    
    for provider_name, provider_func in providers:
        try:
            results = provider_func()
            if results:
                xbmc.log(f'SALTS FreeStream: {provider_name} returned {len(results)} sources', xbmc.LOGINFO)
                all_sources.extend(results)
        except Exception as e:
            xbmc.log(f'SALTS FreeStream: {provider_name} failed: {e}', xbmc.LOGDEBUG)
    
    # Deduplicate by URL and validate
    seen_urls = set()
    unique_sources = []
    for s in all_sources:
        url = s.get('url', '')
        if url and url not in seen_urls and _is_video_url(url):
            seen_urls.add(url)
            unique_sources.append(s)
    
    xbmc.log(f'SALTS FreeStream: Total {len(unique_sources)} valid free streams found', xbmc.LOGINFO)
    return unique_sources


def _search_tmdb_id(title, year, media_type):
    """Search TMDB for an ID"""
    try:
        api_key = '8265bd1679663a7ea12ac168da84d2e8'
        search_type = 'movie' if media_type == 'movie' else 'tv'
        url = f'https://api.themoviedb.org/3/search/{search_type}?api_key={api_key}&query={quote_plus(title)}'
        if year:
            url += f'&year={year}' if media_type == 'movie' else f'&first_air_date_year={year}'
        
        data = _fetch_json(url)
        if data:
            results = data.get('results', [])
            if results:
                return str(results[0].get('id', ''))
    except Exception as e:
        xbmc.log(f'SALTS FreeStream TMDB search error: {e}', xbmc.LOGDEBUG)
    return ''
