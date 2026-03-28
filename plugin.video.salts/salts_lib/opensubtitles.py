"""
SALTS - OpenSubtitles Integration
Downloads subtitles automatically using OpenSubtitles REST API.
Uses native urllib - no external dependencies.
"""
import os
import json
import gzip
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus

ADDON = xbmcaddon.Addon()
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
SUBS_DIR = os.path.join(ADDON_DATA, 'subtitles')

# OpenSubtitles REST API (free tier)
OS_API_URL = 'https://api.opensubtitles.com/api/v1'
OS_API_KEY = 'iej1OB1FIm0eao8RaLqSMkjSRrhzQqOx'  # Free API key for SALTS
USER_AGENT = 'SALTS v2.1.1'


def _os_request(endpoint, params=None, method='GET'):
    """Make request to OpenSubtitles API"""
    url = f'{OS_API_URL}{endpoint}'
    if params and method == 'GET':
        query = '&'.join(f'{k}={quote_plus(str(v))}' for k, v in params.items() if v)
        url = f'{url}?{query}'
    
    headers = {
        'Api-Key': OS_API_KEY,
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    # Add auth token if available
    token = ADDON.getSetting('opensubtitles_token')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        req = Request(url, headers=headers, method=method)
        resp = urlopen(req, timeout=15)
        return json.loads(resp.read().decode('utf-8', errors='replace'))
    except HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8')
        except Exception:
            pass
        xbmc.log(f'SALTS OpenSubs API error {e.code}: {body[:200]}', xbmc.LOGDEBUG)
        return None
    except Exception as e:
        xbmc.log(f'SALTS OpenSubs request error: {e}', xbmc.LOGDEBUG)
        return None


def search_subtitles(title='', year='', season='', episode='', tmdb_id='',
                     imdb_id='', media_type='movie', languages=None):
    """
    Search for subtitles on OpenSubtitles.
    Returns list of subtitle results.
    """
    if not languages:
        lang_setting = ADDON.getSetting('subtitle_languages') or 'en'
        languages = lang_setting.split(',')
    
    params = {
        'languages': ','.join(languages),
    }
    
    # Prefer ID-based search (more accurate)
    if tmdb_id:
        params['tmdb_id'] = tmdb_id
    elif imdb_id:
        params['imdb_id'] = imdb_id.replace('tt', '')
    else:
        params['query'] = title
        if year:
            params['year'] = year
    
    if media_type != 'movie' and season and episode:
        params['season_number'] = season
        params['episode_number'] = episode
    
    data = _os_request('/subtitles', params)
    if not data:
        return []
    
    results = []
    for item in data.get('data', []):
        attrs = item.get('attributes', {})
        files = attrs.get('files', [])
        
        if not files:
            continue
        
        file_info = files[0]
        
        results.append({
            'file_id': file_info.get('file_id', 0),
            'file_name': file_info.get('file_name', 'subtitle.srt'),
            'language': attrs.get('language', 'en'),
            'release': attrs.get('release', ''),
            'download_count': attrs.get('download_count', 0),
            'ratings': attrs.get('ratings', 0),
            'hearing_impaired': attrs.get('hearing_impaired', False),
            'machine_translated': attrs.get('machine_translated', False),
        })
    
    # Sort by download count (most popular first)
    results.sort(key=lambda x: x.get('download_count', 0), reverse=True)
    
    return results


def download_subtitle(file_id, filename='subtitle.srt'):
    """
    Download a subtitle file from OpenSubtitles.
    Returns local file path or None.
    """
    # Create subtitle directory
    if not os.path.exists(SUBS_DIR):
        os.makedirs(SUBS_DIR)
    
    # Request download link
    data = _os_request('/download', {'file_id': file_id}, method='POST')
    if not data:
        return None
    
    download_url = data.get('link', '')
    if not download_url:
        return None
    
    try:
        req = Request(download_url, headers={'User-Agent': USER_AGENT})
        resp = urlopen(req, timeout=30)
        content = resp.read()
        
        # Save subtitle file
        local_path = os.path.join(SUBS_DIR, filename)
        with open(local_path, 'wb') as f:
            f.write(content)
        
        xbmc.log(f'SALTS: Subtitle downloaded to {local_path}', xbmc.LOGINFO)
        return local_path
        
    except Exception as e:
        xbmc.log(f'SALTS: Subtitle download error: {e}', xbmc.LOGERROR)
        return None


def auto_download_subtitle(title='', year='', season='', episode='',
                           tmdb_id='', imdb_id='', media_type='movie'):
    """
    Automatically search and download the best subtitle.
    Returns local file path or None.
    """
    if ADDON.getSetting('auto_subtitles') != 'true':
        return None
    
    results = search_subtitles(title, year, season, episode,
                                tmdb_id, imdb_id, media_type)
    
    if not results:
        xbmc.log(f'SALTS: No subtitles found for {title}', xbmc.LOGDEBUG)
        return None
    
    # Pick the best one (highest download count, non-machine-translated)
    best = None
    for r in results:
        if not r.get('machine_translated'):
            best = r
            break
    
    if not best:
        best = results[0]
    
    file_path = download_subtitle(best['file_id'], best.get('file_name', 'subtitle.srt'))
    
    if file_path:
        xbmc.log(f'SALTS: Auto-subtitle loaded: {best.get("file_name")} ({best.get("language")})', xbmc.LOGINFO)
    
    return file_path


def show_subtitle_dialog(title='', year='', season='', episode='',
                          tmdb_id='', imdb_id='', media_type='movie'):
    """Show subtitle selection dialog"""
    results = search_subtitles(title, year, season, episode,
                                tmdb_id, imdb_id, media_type)
    
    if not results:
        xbmcgui.Dialog().notification('SALTS', 'No subtitles found', xbmcgui.NOTIFICATION_INFO)
        return None
    
    # Build display list
    display = []
    for r in results:
        lang = r.get('language', '??').upper()
        name = r.get('file_name', 'Unknown')[:60]
        downloads = r.get('download_count', 0)
        hi = ' [HI]' if r.get('hearing_impaired') else ''
        mt = ' [MT]' if r.get('machine_translated') else ''
        
        label = f'[{lang}]{hi}{mt} {name} ({downloads} downloads)'
        display.append(label)
    
    selected = xbmcgui.Dialog().select('SALTS - Subtitles', display)
    
    if selected < 0:
        return None
    
    chosen = results[selected]
    return download_subtitle(chosen['file_id'], chosen.get('file_name', 'subtitle.srt'))
