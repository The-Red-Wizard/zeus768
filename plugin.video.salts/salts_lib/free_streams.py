"""
SALTS - Free Stream Providers
Extracts direct playable URLs from free embed APIs using TMDB/IMDB IDs.
No debrid required - plays straight in Kodi player.
"""
import re
import json
import time
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus, urlencode

ADDON = xbmcaddon.Addon()
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def _fetch(url, headers=None, timeout=15):
    """Fetch URL and return response text"""
    hdrs = {
        'User-Agent': USER_AGENT,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    if headers:
        hdrs.update(headers)
    try:
        req = Request(url, headers=hdrs)
        resp = urlopen(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        xbmc.log(f'SALTS FreeStream fetch error ({url}): {e}', xbmc.LOGDEBUG)
        return ''


def _fetch_with_redirect(url, headers=None, timeout=15):
    """Fetch URL and return final URL + response text (follows redirects)"""
    hdrs = {
        'User-Agent': USER_AGENT,
        'Accept': '*/*',
    }
    if headers:
        hdrs.update(headers)
    try:
        req = Request(url, headers=hdrs)
        resp = urlopen(req, timeout=timeout)
        return resp.geturl(), resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        xbmc.log(f'SALTS FreeStream redirect fetch error ({url}): {e}', xbmc.LOGDEBUG)
        return url, ''


def _extract_streams_from_html(html):
    """Extract m3u8/mp4 stream URLs from HTML/JS content"""
    streams = []
    
    # Look for m3u8 URLs
    m3u8_pattern = r'(https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*)'
    for match in re.findall(m3u8_pattern, html):
        url = match.rstrip('\\').rstrip('"').rstrip("'")
        if url not in [s['url'] for s in streams]:
            streams.append({
                'url': url,
                'type': 'hls',
                'quality': _guess_quality(url)
            })
    
    # Look for mp4 URLs
    mp4_pattern = r'(https?://[^\s\'"<>]+\.mp4[^\s\'"<>]*)'
    for match in re.findall(mp4_pattern, html):
        url = match.rstrip('\\').rstrip('"').rstrip("'")
        if url not in [s['url'] for s in streams]:
            streams.append({
                'url': url,
                'type': 'mp4',
                'quality': _guess_quality(url)
            })
    
    # Look for file/source patterns in JS
    js_patterns = [
        r'["\']?file["\']?\s*:\s*["\']([^"\']+)["\']',
        r'["\']?source["\']?\s*:\s*["\']([^"\']+)["\']',
        r'["\']?src["\']?\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
        r'sources\s*:\s*\[\{[^}]*["\']?file["\']?\s*:\s*["\']([^"\']+)["\']',
        r'video_url\s*[:=]\s*["\']([^"\']+)["\']',
        r'stream_url\s*[:=]\s*["\']([^"\']+)["\']',
        r'playbackUrl\s*[:=]\s*["\']([^"\']+)["\']',
    ]
    
    for pattern in js_patterns:
        for match in re.findall(pattern, html):
            if ('http' in match) and match not in [s['url'] for s in streams]:
                streams.append({
                    'url': match,
                    'type': 'hls' if '.m3u8' in match else 'mp4',
                    'quality': _guess_quality(match)
                })
    
    return streams


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
    elif '360' in url_lower:
        return 'SD'
    return 'HD'


# ==================== Provider: VidSrc.to ====================

def _vidsrc_to(tmdb_id, media_type='movie', season='', episode=''):
    """VidSrc.to - Free embed streams via TMDB ID"""
    sources = []
    if not tmdb_id:
        return sources
    
    try:
        if media_type == 'movie':
            embed_url = f'https://vidsrc.to/embed/movie/{tmdb_id}'
        else:
            embed_url = f'https://vidsrc.to/embed/tv/{tmdb_id}/{season}/{episode}'
        
        html = _fetch(embed_url, headers={
            'Referer': 'https://vidsrc.to/',
        })
        
        if html:
            streams = _extract_streams_from_html(html)
            for s in streams:
                sources.append({
                    'url': s['url'],
                    'quality': s['quality'],
                    'provider': 'VidSrc.to',
                    'direct': True
                })
            
            # Also look for iframe sources to follow
            iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
            for iframe_url in re.findall(iframe_pattern, html):
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                if 'vidsrc' in iframe_url or 'embed' in iframe_url:
                    iframe_html = _fetch(iframe_url, headers={
                        'Referer': embed_url,
                    })
                    if iframe_html:
                        for s in _extract_streams_from_html(iframe_html):
                            sources.append({
                                'url': s['url'],
                                'quality': s['quality'],
                                'provider': 'VidSrc.to',
                                'direct': True
                            })
    except Exception as e:
        xbmc.log(f'SALTS VidSrc.to error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Provider: VidSrc.me ====================

def _vidsrc_me(tmdb_id, imdb_id='', media_type='movie', season='', episode=''):
    """VidSrc.me alternatives - multiple mirror domains"""
    sources = []
    vid_id = imdb_id or tmdb_id
    if not vid_id:
        return sources
    
    domains = ['vidsrc.xyz', 'vidsrc.in', 'vidsrc.pm', 'vidsrc.net']
    
    for domain in domains:
        try:
            if media_type == 'movie':
                embed_url = f'https://{domain}/embed/movie/{vid_id}'
            else:
                embed_url = f'https://{domain}/embed/tv/{vid_id}/{season}-{episode}'
            
            html = _fetch(embed_url, headers={
                'Referer': f'https://{domain}/',
            }, timeout=10)
            
            if html and len(html) > 500:
                streams = _extract_streams_from_html(html)
                for s in streams:
                    sources.append({
                        'url': s['url'],
                        'quality': s['quality'],
                        'provider': f'VidSrc ({domain})',
                        'direct': True
                    })
                
                if sources:
                    break  # Got results from this domain, stop trying others
                    
        except Exception as e:
            xbmc.log(f'SALTS VidSrc.me ({domain}) error: {e}', xbmc.LOGDEBUG)
            continue
    
    return sources


# ==================== Provider: 2Embed ====================

def _2embed(tmdb_id, imdb_id='', media_type='movie', season='', episode=''):
    """2Embed - Free embed streams"""
    sources = []
    vid_id = tmdb_id or imdb_id
    if not vid_id:
        return sources
    
    try:
        if media_type == 'movie':
            embed_url = f'https://www.2embed.cc/embed/{vid_id}'
        else:
            embed_url = f'https://www.2embed.cc/embedtv/{vid_id}&s={season}&e={episode}'
        
        html = _fetch(embed_url, headers={
            'Referer': 'https://www.2embed.cc/',
        })
        
        if html:
            streams = _extract_streams_from_html(html)
            for s in streams:
                sources.append({
                    'url': s['url'],
                    'quality': s['quality'],
                    'provider': '2Embed',
                    'direct': True
                })
            
            iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
            for iframe_url in re.findall(iframe_pattern, html):
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                iframe_html = _fetch(iframe_url, headers={
                    'Referer': embed_url,
                })
                if iframe_html:
                    for s in _extract_streams_from_html(iframe_html):
                        sources.append({
                            'url': s['url'],
                            'quality': s['quality'],
                            'provider': '2Embed',
                            'direct': True
                        })
    except Exception as e:
        xbmc.log(f'SALTS 2Embed error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Provider: AutoEmbed ====================

def _autoembed(tmdb_id, media_type='movie', season='', episode=''):
    """AutoEmbed - Free embed streams"""
    sources = []
    if not tmdb_id:
        return sources
    
    try:
        if media_type == 'movie':
            embed_url = f'https://autoembed.cc/embed/oplayer.php?id={tmdb_id}'
        else:
            embed_url = f'https://autoembed.cc/embed/oplayer.php?id={tmdb_id}&s={season}&e={episode}'
        
        html = _fetch(embed_url, headers={
            'Referer': 'https://autoembed.cc/',
        })
        
        if html:
            streams = _extract_streams_from_html(html)
            for s in streams:
                sources.append({
                    'url': s['url'],
                    'quality': s['quality'],
                    'provider': 'AutoEmbed',
                    'direct': True
                })
    except Exception as e:
        xbmc.log(f'SALTS AutoEmbed error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Provider: MultiEmbed ====================

def _multiembed(tmdb_id, media_type='movie', season='', episode=''):
    """MultiEmbed - Free embed streams"""
    sources = []
    if not tmdb_id:
        return sources
    
    try:
        if media_type == 'movie':
            embed_url = f'https://multiembed.mov/?video_id={tmdb_id}&tmdb=1'
        else:
            embed_url = f'https://multiembed.mov/?video_id={tmdb_id}&tmdb=1&s={season}&e={episode}'
        
        html = _fetch(embed_url, headers={
            'Referer': 'https://multiembed.mov/',
        })
        
        if html:
            streams = _extract_streams_from_html(html)
            for s in streams:
                sources.append({
                    'url': s['url'],
                    'quality': s['quality'],
                    'provider': 'MultiEmbed',
                    'direct': True
                })
    except Exception as e:
        xbmc.log(f'SALTS MultiEmbed error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Provider: Embed.su ====================

def _embedsu(tmdb_id, media_type='movie', season='', episode=''):
    """Embed.su - Free embed streams"""
    sources = []
    if not tmdb_id:
        return sources
    
    try:
        if media_type == 'movie':
            embed_url = f'https://embed.su/embed/movie/{tmdb_id}'
        else:
            embed_url = f'https://embed.su/embed/tv/{tmdb_id}/{season}/{episode}'
        
        html = _fetch(embed_url, headers={
            'Referer': 'https://embed.su/',
        })
        
        if html:
            streams = _extract_streams_from_html(html)
            for s in streams:
                sources.append({
                    'url': s['url'],
                    'quality': s['quality'],
                    'provider': 'Embed.su',
                    'direct': True
                })
    except Exception as e:
        xbmc.log(f'SALTS Embed.su error: {e}', xbmc.LOGDEBUG)
    
    return sources


# ==================== Provider: VidLink ====================

def _vidlink(tmdb_id, media_type='movie', season='', episode=''):
    """VidLink - Free embed streams"""
    sources = []
    if not tmdb_id:
        return sources
    
    try:
        if media_type == 'movie':
            embed_url = f'https://vidlink.pro/movie/{tmdb_id}'
        else:
            embed_url = f'https://vidlink.pro/tv/{tmdb_id}/{season}/{episode}'
        
        html = _fetch(embed_url, headers={
            'Referer': 'https://vidlink.pro/',
        })
        
        if html:
            streams = _extract_streams_from_html(html)
            for s in streams:
                sources.append({
                    'url': s['url'],
                    'quality': s['quality'],
                    'provider': 'VidLink',
                    'direct': True
                })
    except Exception as e:
        xbmc.log(f'SALTS VidLink error: {e}', xbmc.LOGDEBUG)
    
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
        # Try to get TMDB ID from title search
        tmdb_id = _search_tmdb_id(title, year, media_type)
    
    if not tmdb_id and not imdb_id:
        xbmc.log('SALTS FreeStream: No TMDB/IMDB ID available', xbmc.LOGDEBUG)
        return all_sources
    
    # Query all providers
    providers = [
        ('VidSrc.to', lambda: _vidsrc_to(tmdb_id, media_type, season, episode)),
        ('VidSrc.me', lambda: _vidsrc_me(tmdb_id, imdb_id, media_type, season, episode)),
        ('2Embed', lambda: _2embed(tmdb_id, imdb_id, media_type, season, episode)),
        ('AutoEmbed', lambda: _autoembed(tmdb_id, media_type, season, episode)),
        ('MultiEmbed', lambda: _multiembed(tmdb_id, media_type, season, episode)),
        ('Embed.su', lambda: _embedsu(tmdb_id, media_type, season, episode)),
        ('VidLink', lambda: _vidlink(tmdb_id, media_type, season, episode)),
    ]
    
    for provider_name, provider_func in providers:
        try:
            results = provider_func()
            if results:
                xbmc.log(f'SALTS FreeStream: {provider_name} returned {len(results)} sources', xbmc.LOGDEBUG)
                all_sources.extend(results)
        except Exception as e:
            xbmc.log(f'SALTS FreeStream: {provider_name} failed: {e}', xbmc.LOGDEBUG)
    
    # Deduplicate by URL
    seen_urls = set()
    unique_sources = []
    for s in all_sources:
        if s['url'] not in seen_urls:
            seen_urls.add(s['url'])
            unique_sources.append(s)
    
    xbmc.log(f'SALTS FreeStream: Total {len(unique_sources)} unique free streams found', xbmc.LOGINFO)
    return unique_sources


def _search_tmdb_id(title, year, media_type):
    """Search TMDB for an ID if we don't have one"""
    try:
        api_key = '8265bd1679663a7ea12ac168da84d2e8'
        search_type = 'movie' if media_type == 'movie' else 'tv'
        url = f'https://api.themoviedb.org/3/search/{search_type}?api_key={api_key}&query={quote_plus(title)}'
        if year:
            url += f'&year={year}' if media_type == 'movie' else f'&first_air_date_year={year}'
        
        html = _fetch(url)
        if html:
            data = json.loads(html)
            results = data.get('results', [])
            if results:
                return str(results[0].get('id', ''))
    except Exception as e:
        xbmc.log(f'SALTS FreeStream TMDB search error: {e}', xbmc.LOGDEBUG)
    return ''
