"""
Tinklepad Scrapers v1.5 - Extended Edition
Multi-source scraper with DDL, Torrent, Free streaming, and External Scraper Pack support
Now with EZTV, RARBG, Nyaa, LimeTorrents, Torlock, Comet, CocoScrapers & GearsScrapers
"""
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import requests
import re
import sys
import urllib.parse
import hashlib
import json
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except:
    HAS_BS4 = False

try:
    import resolveurl
    HAS_RESOLVEURL = True
except:
    HAS_RESOLVEURL = False

from resources.lib.debrid import debrid_manager

ADDON = xbmcaddon.Addon()

# ==================== EXTERNAL SCRAPER DETECTION ====================

def detect_cocoscrapers():
    """Check if CocoScrapers module is installed"""
    try:
        import importlib.util
        spec = importlib.util.find_spec('script.module.cocoscrapers')
        if spec:
            return True
        # Try direct import
        from cocoscrapers import sources_cocoscrapers
        return True
    except:
        pass
    
    try:
        # Alternative check via xbmcaddon
        xbmcaddon.Addon('script.module.cocoscrapers')
        return True
    except:
        return False

def detect_gearsscrapers():
    """Check if GearsScrapers module is installed"""
    try:
        import importlib.util
        spec = importlib.util.find_spec('script.module.gearsscrapers')
        if spec:
            return True
        from gearsscrapers import sources_gearsscrapers
        return True
    except:
        pass
    
    try:
        xbmcaddon.Addon('script.module.gearsscrapers')
        return True
    except:
        return False

HAS_COCOSCRAPERS = detect_cocoscrapers()
HAS_GEARSSCRAPERS = detect_gearsscrapers()

xbmc.log(f'[Tinklepad] CocoScrapers available: {HAS_COCOSCRAPERS}', xbmc.LOGINFO)
xbmc.log(f'[Tinklepad] GearsScrapers available: {HAS_GEARSSCRAPERS}', xbmc.LOGINFO)

# Supported file hosts for debrid resolution
DEBRID_HOSTS = [
    'nitroflare', 'rapidgator', 'clicknupload', 'usersdrive', 'uploaded',
    'turbobit', 'filefactory', 'uploadgig', 'megaup', 'mediafire',
    'katfile', 'ddownload', 'filestore', 'hexupload', 'drop.download',
    '1fichier', 'uptobox', 'mega.nz', 'mega.co', 'zippyshare', 'sendcm'
]

# Hosts that require download-first approach for reliable playback
DOWNLOAD_FIRST_HOSTS = ['nitroflare', 'rapidgator']

# User agent
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}


def is_provider_enabled(provider_key):
    try:
        val = ADDON.getSetting(provider_key)
        return val == 'true' or val == ''  # Default to enabled
    except:
        return True


def clean_title(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def extract_quality(text):
    text = text.upper()
    if '2160P' in text or '4K' in text or 'UHD' in text:
        return '4K'
    elif '1080P' in text or 'FULLHD' in text or 'FHD' in text:
        return '1080p'
    elif '720P' in text or 'HD' in text:
        return '720p'
    elif '480P' in text or 'SD' in text:
        return '480p'
    elif 'CAM' in text or 'TS' in text:
        return 'CAM'
    return 'HD'


def extract_size(text):
    match = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB|GiB|MiB)', text, re.IGNORECASE)
    if match:
        size = float(match.group(1))
        unit = match.group(2).upper()
        if 'G' in unit:
            return f'{size:.1f} GB'
        return f'{size:.0f} MB'
    return ''


def identify_host(url):
    url_lower = url.lower()
    for host in DEBRID_HOSTS:
        if host in url_lower:
            return host.capitalize()
    if 'magnet:' in url_lower:
        return 'Magnet'
    return 'Direct'


def needs_download_first(url):
    """Check if URL is from a host that needs download-first approach"""
    url_lower = url.lower()
    for host in DOWNLOAD_FIRST_HOSTS:
        if host in url_lower:
            return True
    return False


def download_and_play(url, title='', progress_callback=None):
    """Download file to temp location and return path for playback"""
    import xbmcvfs
    import os
    
    try:
        download_dir = ADDON.getSetting('download_path')
        if not download_dir or not xbmcvfs.exists(download_dir):
            download_dir = xbmcvfs.translatePath('special://temp/tinklepad_downloads/')
            if not xbmcvfs.exists(download_dir):
                xbmcvfs.mkdirs(download_dir)
        
        filename = title.replace(' ', '_').replace(':', '').replace('/', '_')[:50] if title else 'download'
        
        try:
            head_response = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
            content_disp = head_response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disp:
                match = re.search(r'filename[*]?=["\']?([^"\';\s]+)', content_disp)
                if match:
                    filename = match.group(1)
        except:
            pass
        
        if not any(filename.lower().endswith(ext) for ext in ['.mkv', '.mp4', '.avi', '.mov', '.wmv']):
            filename += '.mp4'
        
        filepath = os.path.join(download_dir, filename)
        
        if xbmcvfs.exists(filepath):
            file_stat = xbmcvfs.Stat(filepath)
            if file_stat.st_size() > 1024 * 1024:
                xbmc.log(f'[Tinklepad] Using cached download: {filepath}', xbmc.LOGINFO)
                return filepath
        
        xbmc.log(f'[Tinklepad] Downloading to: {filepath}', xbmc.LOGINFO)
        
        response = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        total_size = int(response.headers.get('content-length', 0))
        
        dialog = xbmcgui.DialogProgress()
        dialog.create('Tinklepad Download', f'Downloading: {filename}\nThis ensures smooth playback...')
        
        downloaded = 0
        chunk_size = 1024 * 1024
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if dialog.iscanceled():
                    dialog.close()
                    try:
                        os.remove(filepath)
                    except:
                        pass
                    return None
                
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        speed = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        dialog.update(percent, f'Downloading: {filename}\n{speed:.1f} MB / {total_mb:.1f} MB ({percent}%)')
                    else:
                        dialog.update(50, f'Downloading: {filename}\n{downloaded / (1024*1024):.1f} MB downloaded...')
        
        dialog.close()
        xbmc.log(f'[Tinklepad] Download complete: {filepath}', xbmc.LOGINFO)
        return filepath
        
    except Exception as e:
        xbmc.log(f'[Tinklepad] Download error: {e}', xbmc.LOGERROR)
        return None


def make_request(url, timeout=15):
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        xbmc.log(f'[Tinklepad] Request error: {e}', xbmc.LOGDEBUG)
    return None


# ==================== EXTERNAL SCRAPER PACKS ====================

def scrape_cocoscrapers(title, year, content_type='movie', tmdb_id=None, imdb_id=None, season=None, episode=None):
    """Use CocoScrapers if installed and enabled"""
    sources = []
    if not is_provider_enabled('provider.cocoscrapers') or not HAS_COCOSCRAPERS:
        return sources
    
    try:
        from cocoscrapers import sources_cocoscrapers
        coco = sources_cocoscrapers.sources()
        
        # Get list of available scrapers
        scraper_list = coco.get_sources() if hasattr(coco, 'get_sources') else []
        
        if content_type == 'movie':
            data = {
                'title': title,
                'year': year,
                'imdb': imdb_id or '',
                'tmdb': tmdb_id or ''
            }
        else:
            data = {
                'title': title,
                'year': year,
                'imdb': imdb_id or '',
                'tmdb': tmdb_id or '',
                'season': season,
                'episode': episode
            }
        
        # Run scrapers
        coco_sources = coco.scrape(data) if hasattr(coco, 'scrape') else []
        
        for src in coco_sources:
            quality = src.get('quality', 'HD')
            host = src.get('source', 'Unknown')
            url = src.get('url', '')
            
            if url:
                sources.append({
                    'label': f'[CocoScrapers] [{host}] [{quality}]',
                    'url': url,
                    'quality': quality,
                    'host': host,
                    'provider': 'CocoScrapers',
                    'debrid': src.get('debrid', False),
                    'external_pack': True
                })
        
        xbmc.log(f'[Tinklepad] CocoScrapers found {len(sources)} sources', xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f'[Tinklepad] CocoScrapers error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_gearsscrapers(title, year, content_type='movie', tmdb_id=None, imdb_id=None, season=None, episode=None):
    """Use GearsScrapers if installed and enabled"""
    sources = []
    if not is_provider_enabled('provider.gearsscrapers') or not HAS_GEARSSCRAPERS:
        return sources
    
    try:
        from gearsscrapers import sources_gearsscrapers
        gears = sources_gearsscrapers.sources()
        
        if content_type == 'movie':
            data = {
                'title': title,
                'year': year,
                'imdb': imdb_id or '',
                'tmdb': tmdb_id or ''
            }
        else:
            data = {
                'title': title,
                'year': year,
                'imdb': imdb_id or '',
                'tmdb': tmdb_id or '',
                'season': season,
                'episode': episode
            }
        
        gears_sources = gears.scrape(data) if hasattr(gears, 'scrape') else []
        
        for src in gears_sources:
            quality = src.get('quality', 'HD')
            host = src.get('source', 'Unknown')
            url = src.get('url', '')
            
            if url:
                sources.append({
                    'label': f'[GearsScrapers] [{host}] [{quality}]',
                    'url': url,
                    'quality': quality,
                    'host': host,
                    'provider': 'GearsScrapers',
                    'debrid': src.get('debrid', False),
                    'external_pack': True
                })
        
        xbmc.log(f'[Tinklepad] GearsScrapers found {len(sources)} sources', xbmc.LOGINFO)
        
    except Exception as e:
        xbmc.log(f'[Tinklepad] GearsScrapers error: {e}', xbmc.LOGERROR)
    
    return sources


# ==================== COMET SCRAPER ====================

def scrape_comet(title, year, content_type='movie', tmdb_id=None, imdb_id=None, season=None, episode=None):
    """Scrape from Comet (Stremio-style torrent indexer)"""
    sources = []
    if not is_provider_enabled('provider.comet'):
        return sources
    
    try:
        # Comet API endpoints - try multiple instances
        comet_instances = [
            'https://comet.elfhosted.com',
            'https://comet.aiostreams.com',
            'https://comet.hackerspace.sh'
        ]
        
        for base_url in comet_instances:
            try:
                if content_type == 'movie' and tmdb_id:
                    api_url = f'{base_url}/stream/movie/{tmdb_id}.json'
                elif content_type == 'tv' and tmdb_id and season and episode:
                    api_url = f'{base_url}/stream/series/{tmdb_id}:{season}:{episode}.json'
                else:
                    continue
                
                response = requests.get(api_url, headers=HEADERS, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    streams = data.get('streams', [])
                    
                    for stream in streams:
                        stream_title = stream.get('title', '')
                        info_hash = stream.get('infoHash', '')
                        
                        if info_hash:
                            # Build magnet link
                            magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={urllib.parse.quote(title)}"
                            trackers = [
                                'udp://tracker.opentrackr.org:1337/announce',
                                'udp://open.stealth.si:80/announce',
                                'udp://tracker.torrent.eu.org:451/announce'
                            ]
                            for tracker in trackers:
                                magnet += f"&tr={urllib.parse.quote(tracker)}"
                            
                            quality = extract_quality(stream_title)
                            size = extract_size(stream_title)
                            
                            label = f'[Comet] [Magnet] [{quality}]'
                            if size:
                                label += f' [{size}]'
                            
                            sources.append({
                                'label': label,
                                'url': magnet,
                                'quality': quality,
                                'host': 'Magnet',
                                'provider': 'Comet',
                                'debrid': True,
                                'torrent': True
                            })
                    
                    if sources:
                        xbmc.log(f'[Tinklepad] Comet found {len(sources)} sources from {base_url}', xbmc.LOGINFO)
                        break
                        
            except Exception as e:
                xbmc.log(f'[Tinklepad] Comet instance {base_url} error: {e}', xbmc.LOGDEBUG)
                continue
                
    except Exception as e:
        xbmc.log(f'[Tinklepad] Comet error: {e}', xbmc.LOGERROR)
    
    return sources


# ==================== FREE STREAMING ====================

def scrape_vidsrc(title, year, content_type='movie', tmdb_id=None, season=None, episode=None):
    """VidSrc.to - Very reliable free streaming"""
    sources = []
    if not is_provider_enabled('provider.vidsrc'):
        return sources
    
    try:
        if tmdb_id:
            if content_type == 'movie':
                embed_url = f'https://vidsrc.to/embed/movie/{tmdb_id}'
            else:
                s = season or 1
                e = episode or 1
                embed_url = f'https://vidsrc.to/embed/tv/{tmdb_id}/{s}/{e}'
            
            sources.append({
                'label': '[VidSrc.to] [FREE] [Multi-Quality]',
                'url': embed_url,
                'quality': '1080p',
                'host': 'VidSrc',
                'provider': 'VidSrc.to',
                'debrid': False,
                'free': True,
                'direct_play': True
            })
    except Exception as e:
        xbmc.log(f'[Tinklepad] VidSrc error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_vidsrcme(title, year, content_type='movie', tmdb_id=None, imdb_id=None, season=None, episode=None):
    """VidSrc.me - Another reliable source"""
    sources = []
    if not is_provider_enabled('provider.vidsrcme'):
        return sources
    
    try:
        if tmdb_id:
            if content_type == 'movie':
                embed_url = f'https://vidsrc.me/embed/movie?tmdb={tmdb_id}'
            else:
                s = season or 1
                e = episode or 1
                embed_url = f'https://vidsrc.me/embed/tv?tmdb={tmdb_id}&season={s}&episode={e}'
            
            sources.append({
                'label': '[VidSrc.me] [FREE] [Auto]',
                'url': embed_url,
                'quality': '1080p',
                'host': 'VidSrc.me',
                'provider': 'VidSrc.me',
                'debrid': False,
                'free': True,
                'direct_play': True
            })
    except Exception as e:
        xbmc.log(f'[Tinklepad] VidSrc.me error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_2embed(title, year, content_type='movie', tmdb_id=None, season=None, episode=None):
    """2Embed - Reliable free streaming"""
    sources = []
    if not is_provider_enabled('provider.2embed'):
        return sources
    
    try:
        if tmdb_id:
            if content_type == 'movie':
                embed_url = f'https://www.2embed.cc/embed/{tmdb_id}'
            else:
                s = season or 1
                e = episode or 1
                embed_url = f'https://www.2embed.cc/embedtv/{tmdb_id}&s={s}&e={e}'
            
            sources.append({
                'label': '[2Embed] [FREE] [HD]',
                'url': embed_url,
                'quality': 'HD',
                'host': '2Embed',
                'provider': '2Embed',
                'debrid': False,
                'free': True,
                'direct_play': True
            })
    except Exception as e:
        xbmc.log(f'[Tinklepad] 2Embed error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_superembed(title, year, content_type='movie', tmdb_id=None, season=None, episode=None):
    """SuperEmbed - Multi-source embedder"""
    sources = []
    if not is_provider_enabled('provider.superembed'):
        return sources
    
    try:
        if tmdb_id:
            if content_type == 'movie':
                embed_url = f'https://multiembed.mov/?video_id={tmdb_id}&tmdb=1'
            else:
                s = season or 1
                e = episode or 1
                embed_url = f'https://multiembed.mov/?video_id={tmdb_id}&tmdb=1&s={s}&e={e}'
            
            sources.append({
                'label': '[SuperEmbed] [FREE] [Multi]',
                'url': embed_url,
                'quality': '1080p',
                'host': 'SuperEmbed',
                'provider': 'SuperEmbed',
                'debrid': False,
                'free': True,
                'direct_play': True
            })
    except Exception as e:
        xbmc.log(f'[Tinklepad] SuperEmbed error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_losmovies(title, year, content_type='movie', tmdb_id=None, season=None, episode=None):
    """LosMovies.mx - Free streaming with embeds"""
    sources = []
    if not is_provider_enabled('provider.losmovies'):
        return sources
    
    try:
        if tmdb_id:
            if content_type == 'movie':
                watch_url = f'https://losmovies.mx/movie/{tmdb_id}'
            else:
                s = season or 1
                e = episode or 1
                watch_url = f'https://losmovies.mx/tv/{tmdb_id}/season/{s}/episode/{e}'
            
            sources.append({
                'label': '[LosMovies] [FREE] [HD]',
                'url': watch_url,
                'quality': '1080p',
                'host': 'LosMovies',
                'provider': 'LosMovies',
                'debrid': False,
                'free': True,
                'direct_play': True
            })
                
    except Exception as e:
        xbmc.log(f'[Tinklepad] LosMovies error: {e}', xbmc.LOGERROR)
    
    return sources


# ==================== DDL SCRAPERS ====================

def scrape_tinklepad(title, year, content_type='movie'):
    """Scrape from Tinklepad Provider"""
    sources = []
    if not is_provider_enabled('provider.tinklepad'):
        return sources
    
    try:
        base = 'http://162.245.85.19'
        search_term = urllib.parse.quote(f'{title} {year}')
        
        for search_url in [f'{base}/?s={search_term}', f'{base}/search/{search_term}']:
            html = make_request(search_url)
            if html and HAS_BS4:
                soup = BeautifulSoup(html, 'html.parser')
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text() + ' ' + str(link.get('title', ''))
                    
                    for host in DEBRID_HOSTS:
                        if host in href.lower():
                            quality = extract_quality(text + ' ' + href)
                            size = extract_size(text)
                            host_name = identify_host(href)
                            
                            label = f'[Tinklepad] [{host_name}] [{quality}]'
                            if size:
                                label += f' [{size}]'
                            
                            sources.append({
                                'label': label,
                                'url': href,
                                'quality': quality,
                                'host': host_name,
                                'provider': 'Tinklepad',
                                'debrid': True
                            })
                break
    except Exception as e:
        xbmc.log(f'[Tinklepad] Tinklepad Provider error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_1ddl(title, year, content_type='movie'):
    """Scrape from 1DDL.org"""
    sources = []
    if not is_provider_enabled('provider.ddl1'):
        return sources
    
    try:
        search_term = urllib.parse.quote(f'{title} {year}')
        search_url = f'https://1ddl.org/?s={search_term}'
        
        html = make_request(search_url)
        if html and HAS_BS4:
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all(['article', 'div'], class_=re.compile(r'post|entry|item'))
            
            for article in articles[:5]:
                detail_link = article.find('a', href=True)
                if detail_link:
                    detail_url = detail_link.get('href')
                    detail_html = make_request(detail_url, timeout=10)
                    
                    if detail_html:
                        detail_soup = BeautifulSoup(detail_html, 'html.parser')
                        all_links = detail_soup.find_all('a', href=True)
                        
                        for link in all_links:
                            href = link.get('href', '')
                            text = link.get_text()
                            
                            for host in DEBRID_HOSTS:
                                if host in href.lower():
                                    quality = extract_quality(text + ' ' + href)
                                    size = extract_size(text)
                                    host_name = identify_host(href)
                                    
                                    label = f'[1DDL] [{host_name}] [{quality}]'
                                    if size:
                                        label += f' [{size}]'
                                    
                                    sources.append({
                                        'label': label,
                                        'url': href,
                                        'quality': quality,
                                        'host': host_name,
                                        'provider': '1DDL',
                                        'debrid': True
                                    })
    except Exception as e:
        xbmc.log(f'[Tinklepad] 1DDL error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_ddlvalley(title, year, content_type='movie'):
    """Scrape from DDLValley.me"""
    sources = []
    if not is_provider_enabled('provider.ddlvalley'):
        return sources
    
    try:
        search_term = urllib.parse.quote(f'{title} {year}')
        search_url = f'https://www.ddlvalley.me/?s={search_term}'
        
        html = make_request(search_url)
        if html and HAS_BS4:
            soup = BeautifulSoup(html, 'html.parser')
            posts = soup.find_all(['article', 'div'], class_=re.compile(r'post|hentry'))
            
            for post in posts[:5]:
                link = post.find('a', href=True)
                if link:
                    post_url = link.get('href')
                    post_html = make_request(post_url, timeout=10)
                    
                    if post_html:
                        post_soup = BeautifulSoup(post_html, 'html.parser')
                        content = post_soup.find(['div', 'section'], class_=re.compile(r'content|entry'))
                        
                        if content:
                            dl_links = content.find_all('a', href=True)
                            for dl_link in dl_links:
                                href = dl_link.get('href', '')
                                text = dl_link.get_text()
                                
                                for host in DEBRID_HOSTS:
                                    if host in href.lower():
                                        quality = extract_quality(text + ' ' + href)
                                        size = extract_size(text)
                                        host_name = identify_host(href)
                                        
                                        label = f'[DDLValley] [{host_name}] [{quality}]'
                                        if size:
                                            label += f' [{size}]'
                                        
                                        sources.append({
                                            'label': label,
                                            'url': href,
                                            'quality': quality,
                                            'host': host_name,
                                            'provider': 'DDLValley',
                                            'debrid': True
                                        })
    except Exception as e:
        xbmc.log(f'[Tinklepad] DDLValley error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_rlsbb(title, year, content_type='movie'):
    """Scrape from RlsBB.to"""
    sources = []
    if not is_provider_enabled('provider.rlsbb'):
        return sources
    
    try:
        search_term = urllib.parse.quote(f'{title} {year}')
        search_url = f'https://rlsbb.to/?s={search_term}'
        
        html = make_request(search_url)
        if html and HAS_BS4:
            soup = BeautifulSoup(html, 'html.parser')
            posts = soup.find_all('div', class_=re.compile(r'post'))
            
            for post in posts[:5]:
                link = post.find('a', href=True)
                if link:
                    post_url = link.get('href')
                    post_html = make_request(post_url, timeout=10)
                    
                    if post_html:
                        post_soup = BeautifulSoup(post_html, 'html.parser')
                        links = post_soup.find_all('a', href=True)
                        
                        for dl_link in links:
                            href = dl_link.get('href', '')
                            text = dl_link.get_text()
                            
                            for host in DEBRID_HOSTS:
                                if host in href.lower():
                                    quality = extract_quality(text + ' ' + href)
                                    size = extract_size(text)
                                    host_name = identify_host(href)
                                    
                                    label = f'[RlsBB] [{host_name}] [{quality}]'
                                    if size:
                                        label += f' [{size}]'
                                    
                                    sources.append({
                                        'label': label,
                                        'url': href,
                                        'quality': quality,
                                        'host': host_name,
                                        'provider': 'RlsBB',
                                        'debrid': True
                                    })
    except Exception as e:
        xbmc.log(f'[Tinklepad] RlsBB error: {e}', xbmc.LOGERROR)
    
    return sources


# ==================== TORRENT SCRAPERS ====================

def scrape_yts(title, year, content_type='movie'):
    """Scrape from YTS.mx"""
    sources = []
    if not is_provider_enabled('provider.yts') or content_type != 'movie':
        return sources
    
    try:
        mirrors = ['yts.mx', 'yts.torrentbay.to', 'yts.rs']
        
        for mirror in mirrors:
            try:
                search_term = urllib.parse.quote(title)
                api_url = f'https://{mirror}/api/v2/list_movies.json?query_term={search_term}&limit=10'
                
                response = requests.get(api_url, headers=HEADERS, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    movies = data.get('data', {}).get('movies', [])
                    
                    for movie in movies:
                        if str(movie.get('year')) == str(year) or clean_title(movie.get('title', '')) == clean_title(title):
                            torrents = movie.get('torrents', [])
                            for torrent in torrents:
                                quality = torrent.get('quality', 'HD')
                                size = torrent.get('size', '')
                                magnet_hash = torrent.get('hash', '')
                                
                                if magnet_hash:
                                    magnet = f"magnet:?xt=urn:btih:{magnet_hash}&dn={urllib.parse.quote(movie.get('title', ''))}"
                                    trackers = [
                                        'udp://tracker.opentrackr.org:1337/announce',
                                        'udp://open.stealth.si:80/announce',
                                        'udp://tracker.torrent.eu.org:451/announce'
                                    ]
                                    for tracker in trackers:
                                        magnet += f"&tr={urllib.parse.quote(tracker)}"
                                    
                                    label = f'[YTS] [Magnet] [{quality}]'
                                    if size:
                                        label += f' [{size}]'
                                    
                                    sources.append({
                                        'label': label,
                                        'url': magnet,
                                        'quality': quality,
                                        'host': 'Magnet',
                                        'provider': 'YTS',
                                        'debrid': True,
                                        'torrent': True
                                    })
                    if sources:
                        break
            except:
                continue
                
    except Exception as e:
        xbmc.log(f'[Tinklepad] YTS error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_eztv(title, year, content_type='movie', season=None, episode=None):
    """Scrape from EZTV.re - TV Shows"""
    sources = []
    if not is_provider_enabled('provider.eztv') or content_type != 'tv':
        return sources
    
    try:
        mirrors = ['eztv.re', 'eztv.wf', 'eztv.tf']
        
        for mirror in mirrors:
            try:
                search_term = urllib.parse.quote(title)
                api_url = f'https://{mirror}/api/get-torrents?imdb_id=0&limit=50&page=1'
                search_url = f'https://{mirror}/search/{search_term}'
                
                html = make_request(search_url, timeout=10)
                if html and HAS_BS4:
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('tr.forum_header_border')
                    
                    for row in rows[:15]:
                        magnet_link = row.select_one('a.magnet[href^="magnet:"]')
                        name_elem = row.select_one('a.epinfo')
                        size_elem = row.select_one('td:nth-child(4)')
                        
                        if magnet_link and name_elem:
                            torrent_name = name_elem.get_text()
                            magnet = magnet_link.get('href')
                            
                            # Filter by season/episode if specified
                            if season and episode:
                                se_pattern = f'S{int(season):02d}E{int(episode):02d}'
                                if se_pattern.upper() not in torrent_name.upper():
                                    continue
                            
                            quality = extract_quality(torrent_name)
                            size = size_elem.get_text().strip() if size_elem else ''
                            
                            label = f'[EZTV] [Magnet] [{quality}]'
                            if size:
                                label += f' [{size}]'
                            
                            sources.append({
                                'label': label,
                                'url': magnet,
                                'quality': quality,
                                'host': 'Magnet',
                                'provider': 'EZTV',
                                'debrid': True,
                                'torrent': True
                            })
                    
                    if sources:
                        break
            except:
                continue
                
    except Exception as e:
        xbmc.log(f'[Tinklepad] EZTV error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_rarbg(title, year, content_type='movie'):
    """Scrape from RARBG mirrors/clones"""
    sources = []
    if not is_provider_enabled('provider.rarbg'):
        return sources
    
    try:
        # RARBG clones/mirrors
        mirrors = [
            'rargb.to',
            'rarbgmirror.org', 
            'rarbgproxy.org',
            'rarbgunblock.com'
        ]
        
        for mirror in mirrors:
            try:
                search_term = urllib.parse.quote(f'{title} {year}')
                search_url = f'https://{mirror}/search/?search={search_term}'
                
                html = make_request(search_url, timeout=10)
                if html and HAS_BS4:
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('tr.lista2')
                    
                    for row in rows[:10]:
                        link = row.select_one('a[href*="/torrent/"]')
                        magnet_link = row.select_one('a[href^="magnet:"]')
                        
                        if link:
                            torrent_name = link.get_text()
                            detail_url = f'https://{mirror}' + link.get('href', '')
                            
                            # Get magnet from detail page if not in listing
                            if not magnet_link:
                                detail_html = make_request(detail_url, timeout=10)
                                if detail_html:
                                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                                    magnet_link = detail_soup.select_one('a[href^="magnet:"]')
                            
                            if magnet_link:
                                magnet = magnet_link.get('href')
                                quality = extract_quality(torrent_name)
                                size = extract_size(torrent_name)
                                
                                label = f'[RARBG] [Magnet] [{quality}]'
                                if size:
                                    label += f' [{size}]'
                                
                                sources.append({
                                    'label': label,
                                    'url': magnet,
                                    'quality': quality,
                                    'host': 'Magnet',
                                    'provider': 'RARBG',
                                    'debrid': True,
                                    'torrent': True
                                })
                    
                    if sources:
                        break
            except:
                continue
                
    except Exception as e:
        xbmc.log(f'[Tinklepad] RARBG error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_nyaa(title, year, content_type='movie'):
    """Scrape from Nyaa.si - Anime"""
    sources = []
    if not is_provider_enabled('provider.nyaa'):
        return sources
    
    try:
        mirrors = ['nyaa.si', 'nyaa.land']
        
        for mirror in mirrors:
            try:
                search_term = urllib.parse.quote(f'{title} {year}')
                search_url = f'https://{mirror}/?f=0&c=1_2&q={search_term}'
                
                html = make_request(search_url, timeout=10)
                if html and HAS_BS4:
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('table.torrent-list tbody tr')
                    
                    for row in rows[:15]:
                        name_elem = row.select_one('td:nth-child(2) a:last-child')
                        magnet_link = row.select_one('a[href^="magnet:"]')
                        size_elem = row.select_one('td:nth-child(4)')
                        
                        if name_elem and magnet_link:
                            torrent_name = name_elem.get_text().strip()
                            magnet = magnet_link.get('href')
                            
                            quality = extract_quality(torrent_name)
                            size = size_elem.get_text().strip() if size_elem else ''
                            
                            label = f'[Nyaa] [Magnet] [{quality}]'
                            if size:
                                label += f' [{size}]'
                            
                            sources.append({
                                'label': label,
                                'url': magnet,
                                'quality': quality,
                                'host': 'Magnet',
                                'provider': 'Nyaa',
                                'debrid': True,
                                'torrent': True
                            })
                    
                    if sources:
                        break
            except:
                continue
                
    except Exception as e:
        xbmc.log(f'[Tinklepad] Nyaa error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_limetorrents(title, year, content_type='movie'):
    """Scrape from LimeTorrents"""
    sources = []
    if not is_provider_enabled('provider.limetorrents'):
        return sources
    
    try:
        mirrors = ['limetorrents.lol', 'limetorrents.co', 'limetor.com']
        
        for mirror in mirrors:
            try:
                search_term = urllib.parse.quote(f'{title} {year}')
                category = 'movies' if content_type == 'movie' else 'tv'
                search_url = f'https://{mirror}/search/{category}/{search_term}/'
                
                html = make_request(search_url, timeout=10)
                if html and HAS_BS4:
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('table.table2 tr')
                    
                    for row in rows[1:11]:  # Skip header
                        name_elem = row.select_one('td.tdleft div.tt-name a')
                        size_elem = row.select_one('td.tdnormal:nth-child(3)')
                        
                        if name_elem:
                            torrent_name = name_elem.get_text().strip()
                            detail_url = name_elem.get('href', '')
                            
                            if not detail_url.startswith('http'):
                                detail_url = f'https://{mirror}{detail_url}'
                            
                            # Get magnet from detail page
                            detail_html = make_request(detail_url, timeout=10)
                            if detail_html:
                                detail_soup = BeautifulSoup(detail_html, 'html.parser')
                                magnet_link = detail_soup.select_one('a.csprite_dltorrent[href^="magnet:"]')
                                
                                if magnet_link:
                                    magnet = magnet_link.get('href')
                                    quality = extract_quality(torrent_name)
                                    size = size_elem.get_text().strip() if size_elem else ''
                                    
                                    label = f'[LimeTorrents] [Magnet] [{quality}]'
                                    if size:
                                        label += f' [{size}]'
                                    
                                    sources.append({
                                        'label': label,
                                        'url': magnet,
                                        'quality': quality,
                                        'host': 'Magnet',
                                        'provider': 'LimeTorrents',
                                        'debrid': True,
                                        'torrent': True
                                    })
                    
                    if sources:
                        break
            except:
                continue
                
    except Exception as e:
        xbmc.log(f'[Tinklepad] LimeTorrents error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_torlock(title, year, content_type='movie'):
    """Scrape from Torlock"""
    sources = []
    if not is_provider_enabled('provider.torlock'):
        return sources
    
    try:
        mirrors = ['torlock.com', 'torlock2.com']
        
        for mirror in mirrors:
            try:
                search_term = urllib.parse.quote(f'{title} {year}')
                category = 'movies' if content_type == 'movie' else 'television'
                search_url = f'https://www.{mirror}/{category}/torrents/{search_term}.html'
                
                html = make_request(search_url, timeout=10)
                if html and HAS_BS4:
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('table tbody tr')
                    
                    for row in rows[:10]:
                        name_elem = row.select_one('td a b')
                        link_elem = row.select_one('td a')
                        size_elem = row.select_one('td:nth-child(3)')
                        
                        if name_elem and link_elem:
                            torrent_name = name_elem.get_text().strip()
                            detail_url = link_elem.get('href', '')
                            
                            if not detail_url.startswith('http'):
                                detail_url = f'https://www.{mirror}{detail_url}'
                            
                            # Get magnet from detail page
                            detail_html = make_request(detail_url, timeout=10)
                            if detail_html:
                                detail_soup = BeautifulSoup(detail_html, 'html.parser')
                                magnet_link = detail_soup.select_one('a[href^="magnet:"]')
                                
                                if magnet_link:
                                    magnet = magnet_link.get('href')
                                    quality = extract_quality(torrent_name)
                                    size = size_elem.get_text().strip() if size_elem else ''
                                    
                                    label = f'[Torlock] [Magnet] [{quality}]'
                                    if size:
                                        label += f' [{size}]'
                                    
                                    sources.append({
                                        'label': label,
                                        'url': magnet,
                                        'quality': quality,
                                        'host': 'Magnet',
                                        'provider': 'Torlock',
                                        'debrid': True,
                                        'torrent': True
                                    })
                    
                    if sources:
                        break
            except:
                continue
                
    except Exception as e:
        xbmc.log(f'[Tinklepad] Torlock error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_1337x(title, year, content_type='movie'):
    """Scrape from 1337x.to"""
    sources = []
    if not is_provider_enabled('provider.1337x'):
        return sources
    
    try:
        mirrors = ['1337x.to', '1337x.st', '1337xx.to']
        
        for mirror in mirrors:
            try:
                search_term = urllib.parse.quote(f'{title} {year}')
                search_url = f'https://{mirror}/search/{search_term}/1/'
                
                html = make_request(search_url, timeout=10)
                if html and HAS_BS4:
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('table.table-list tbody tr')
                    
                    for row in rows[:10]:
                        name_cell = row.select_one('td.name a:nth-child(2)')
                        size_cell = row.select_one('td.size')
                        
                        if name_cell:
                            torrent_name = name_cell.get_text()
                            torrent_url = f'https://{mirror}' + name_cell.get('href', '')
                            
                            detail_html = make_request(torrent_url, timeout=10)
                            if detail_html:
                                detail_soup = BeautifulSoup(detail_html, 'html.parser')
                                magnet_link = detail_soup.select_one('a[href^="magnet:"]')
                                
                                if magnet_link:
                                    magnet = magnet_link.get('href')
                                    quality = extract_quality(torrent_name)
                                    size = size_cell.get_text().split()[0] if size_cell else ''
                                    
                                    label = f'[1337x] [Magnet] [{quality}]'
                                    if size:
                                        label += f' [{size}]'
                                    
                                    sources.append({
                                        'label': label,
                                        'url': magnet,
                                        'quality': quality,
                                        'host': 'Magnet',
                                        'provider': '1337x',
                                        'debrid': True,
                                        'torrent': True
                                    })
                    if sources:
                        break
            except:
                continue
                
    except Exception as e:
        xbmc.log(f'[Tinklepad] 1337x error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_piratebay(title, year, content_type='movie'):
    """Scrape from The Pirate Bay API"""
    sources = []
    if not is_provider_enabled('provider.piratebay'):
        return sources
    
    try:
        search_term = urllib.parse.quote(f'{title} {year}')
        api_url = f'https://apibay.org/q.php?q={search_term}'
        
        response = requests.get(api_url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            results = response.json()
            
            for item in results[:10]:
                if item.get('id') == '0':
                    continue
                    
                name = item.get('name', '')
                info_hash = item.get('info_hash', '')
                size_bytes = int(item.get('size', 0))
                
                if info_hash:
                    magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={urllib.parse.quote(name)}"
                    trackers = [
                        'udp://tracker.opentrackr.org:1337/announce',
                        'udp://tracker.openbittorrent.com:6969/announce'
                    ]
                    for tracker in trackers:
                        magnet += f"&tr={urllib.parse.quote(tracker)}"
                    
                    quality = extract_quality(name)
                    size = f'{size_bytes / (1024**3):.1f} GB' if size_bytes > 1024**3 else f'{size_bytes / (1024**2):.0f} MB'
                    
                    label = f'[TPB] [Magnet] [{quality}]'
                    if size:
                        label += f' [{size}]'
                    
                    sources.append({
                        'label': label,
                        'url': magnet,
                        'quality': quality,
                        'host': 'Magnet',
                        'provider': 'ThePirateBay',
                        'debrid': True,
                        'torrent': True
                    })
    except Exception as e:
        xbmc.log(f'[Tinklepad] TPB error: {e}', xbmc.LOGERROR)
    
    return sources


def scrape_torrentgalaxy(title, year, content_type='movie'):
    """Scrape from TorrentGalaxy"""
    sources = []
    if not is_provider_enabled('provider.torrentgalaxy'):
        return sources
    
    try:
        mirrors = ['torrentgalaxy.to', 'tgx.rs']
        
        for mirror in mirrors:
            try:
                search_term = urllib.parse.quote(f'{title} {year}')
                search_url = f'https://{mirror}/torrents.php?search={search_term}'
                
                html = make_request(search_url, timeout=10)
                if html and HAS_BS4:
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('div.tgxtablerow')
                    
                    for row in rows[:10]:
                        name_elem = row.select_one('a.txlight')
                        magnet_elem = row.select_one('a[href^="magnet:"]')
                        size_elem = row.select_one('span.badge-secondary')
                        
                        if name_elem and magnet_elem:
                            torrent_name = name_elem.get_text()
                            magnet = magnet_elem.get('href')
                            quality = extract_quality(torrent_name)
                            size = size_elem.get_text() if size_elem else ''
                            
                            label = f'[TGx] [Magnet] [{quality}]'
                            if size:
                                label += f' [{size}]'
                            
                            sources.append({
                                'label': label,
                                'url': magnet,
                                'quality': quality,
                                'host': 'Magnet',
                                'provider': 'TorrentGalaxy',
                                'debrid': True,
                                'torrent': True
                            })
                    if sources:
                        break
            except:
                continue
                
    except Exception as e:
        xbmc.log(f'[Tinklepad] TorrentGalaxy error: {e}', xbmc.LOGERROR)
    
    return sources


# ==================== MAIN SCRAPER ====================

def get_sources(title, year, content_type='movie', tmdb_id=None, imdb_id=None, season=None, episode=None, 
                fanart='', plot='', poster='', rating='', runtime='', genres='',
                progress_callback=None, cancel_check=None):
    """
    Get all sources from enabled providers with enhanced progress dialog
    Shows metadata while searching with custom golden XML window
    """
    from resources.lib.gui import create_search_dialog, TinklepadSearchWindow
    
    all_sources = []
    search_cancelled = False
    using_custom_window = False
    search_dialog = None
    
    xbmc.log(f'[Tinklepad] Searching for: {title} ({year}) - {content_type} - TMDB: {tmdb_id}', xbmc.LOGINFO)
    
    # If callbacks provided, we're running in threaded mode from WindowXML
    if progress_callback and cancel_check:
        update_func = progress_callback
        is_cancelled_func = cancel_check
    else:
        search_dialog = create_search_dialog(
            title=title,
            year=year,
            fanart=fanart,
            poster=poster,
            plot=plot,
            rating=rating,
            runtime=runtime,
            genres=genres,
            content_type=content_type
        )
        
        using_custom_window = isinstance(search_dialog, TinklepadSearchWindow)
        
        if using_custom_window:
            search_dialog.show()
        
        update_func = search_dialog.update_progress if hasattr(search_dialog, 'update_progress') else search_dialog.update
        is_cancelled_func = search_dialog.is_cancelled
    
    # Provider configuration - organized by category
    free_providers = [
        ('VidSrc.to', scrape_vidsrc),
        ('VidSrc.me', scrape_vidsrcme),
        ('2Embed', scrape_2embed),
        ('SuperEmbed', scrape_superembed),
        ('LosMovies', scrape_losmovies)
    ]
    
    ddl_providers = [
        ('Tinklepad DDL', scrape_tinklepad),
        ('1DDL', scrape_1ddl),
        ('DDLValley', scrape_ddlvalley),
        ('RlsBB', scrape_rlsbb)
    ]
    
    torrent_providers = [
        ('YTS', scrape_yts),
        ('EZTV', scrape_eztv),
        ('RARBG', scrape_rarbg),
        ('Nyaa', scrape_nyaa),
        ('LimeTorrents', scrape_limetorrents),
        ('Torlock', scrape_torlock),
        ('ThePirateBay', scrape_piratebay),
        ('1337x', scrape_1337x),
        ('TorrentGalaxy', scrape_torrentgalaxy),
        ('Comet', scrape_comet)
    ]
    
    # External scraper packs
    external_providers = []
    if HAS_COCOSCRAPERS and is_provider_enabled('provider.cocoscrapers'):
        external_providers.append(('CocoScrapers', scrape_cocoscrapers))
    if HAS_GEARSSCRAPERS and is_provider_enabled('provider.gearsscrapers'):
        external_providers.append(('GearsScrapers', scrape_gearsscrapers))
    
    all_providers = free_providers + ddl_providers + torrent_providers + external_providers
    total_providers = len(all_providers)
    completed = 0
    
    # Track counts by type
    free_count = 0
    ddl_count = 0
    torrent_count = 0
    external_count = 0
    
    def run_scraper(provider_name, scraper_func, is_free=False, is_torrent=False, is_external=False):
        """Run individual scraper and return results"""
        try:
            if is_free and tmdb_id:
                return scraper_func(title, year, content_type, tmdb_id, season, episode)
            elif is_torrent and provider_name in ['EZTV']:
                return scraper_func(title, year, content_type, season, episode)
            elif is_torrent and provider_name == 'Comet':
                return scraper_func(title, year, content_type, tmdb_id, imdb_id, season, episode)
            elif is_external:
                return scraper_func(title, year, content_type, tmdb_id, imdb_id, season, episode)
            else:
                return scraper_func(title, year, content_type)
        except Exception as e:
            xbmc.log(f'[Tinklepad] {provider_name} error: {e}', xbmc.LOGDEBUG)
            return []
    
    # Process free streaming providers first (most reliable)
    for provider_name, scraper_func in free_providers:
        if is_cancelled_func():
            search_cancelled = True
            break
        
        update_func(
            progress=int((completed / total_providers) * 100),
            current_provider=provider_name,
            sources_count=len(all_sources),
            free_count=free_count,
            ddl_count=ddl_count,
            torrent_count=torrent_count,
            free_progress=50
        )
        
        if tmdb_id:
            results = run_scraper(provider_name, scraper_func, is_free=True)
            if results:
                all_sources.extend(results)
                free_count += len(results)
                xbmc.log(f'[Tinklepad] {provider_name} found {len(results)} sources', xbmc.LOGINFO)
        
        completed += 1
        xbmc.sleep(100)
    
    # Update free complete
    update_func(
        progress=int((completed / total_providers) * 100),
        current_provider='DDL Sources...',
        sources_count=len(all_sources),
        free_count=free_count,
        ddl_count=ddl_count,
        torrent_count=torrent_count,
        free_progress=100
    )
    
    # Process DDL providers
    for provider_name, scraper_func in ddl_providers:
        if is_cancelled_func():
            search_cancelled = True
            break
        
        update_func(
            progress=int((completed / total_providers) * 100),
            current_provider=provider_name,
            sources_count=len(all_sources),
            free_count=free_count,
            ddl_count=ddl_count,
            torrent_count=torrent_count,
            ddl_progress=50
        )
        
        results = run_scraper(provider_name, scraper_func, is_free=False)
        if results:
            all_sources.extend(results)
            ddl_count += len(results)
            xbmc.log(f'[Tinklepad] {provider_name} found {len(results)} sources', xbmc.LOGINFO)
        
        completed += 1
        xbmc.sleep(100)
    
    # Update DDL complete
    update_func(
        progress=int((completed / total_providers) * 100),
        current_provider='Torrent Sources...',
        sources_count=len(all_sources),
        free_count=free_count,
        ddl_count=ddl_count,
        torrent_count=torrent_count,
        ddl_progress=100
    )
    
    # Process torrent providers
    for provider_name, scraper_func in torrent_providers:
        if is_cancelled_func():
            search_cancelled = True
            break
        
        update_func(
            progress=int((completed / total_providers) * 100),
            current_provider=provider_name,
            sources_count=len(all_sources),
            free_count=free_count,
            ddl_count=ddl_count,
            torrent_count=torrent_count,
            torrent_progress=50
        )
        
        results = run_scraper(provider_name, scraper_func, is_free=False, is_torrent=True)
        if results:
            all_sources.extend(results)
            torrent_count += len(results)
            xbmc.log(f'[Tinklepad] {provider_name} found {len(results)} sources', xbmc.LOGINFO)
        
        completed += 1
        xbmc.sleep(100)
    
    # Process external scraper packs
    if external_providers:
        update_func(
            progress=int((completed / total_providers) * 100),
            current_provider='External Scrapers...',
            sources_count=len(all_sources),
            free_count=free_count,
            ddl_count=ddl_count,
            torrent_count=torrent_count,
            torrent_progress=100
        )
        
        for provider_name, scraper_func in external_providers:
            if is_cancelled_func():
                search_cancelled = True
                break
            
            update_func(
                progress=int((completed / total_providers) * 100),
                current_provider=provider_name,
                sources_count=len(all_sources),
                free_count=free_count,
                ddl_count=ddl_count,
                torrent_count=torrent_count
            )
            
            results = run_scraper(provider_name, scraper_func, is_external=True)
            if results:
                all_sources.extend(results)
                external_count += len(results)
                xbmc.log(f'[Tinklepad] {provider_name} found {len(results)} sources', xbmc.LOGINFO)
            
            completed += 1
            xbmc.sleep(100)
    
    # Final update
    update_func(
        progress=100,
        current_provider='Search Complete!',
        sources_count=len(all_sources),
        free_count=free_count,
        ddl_count=ddl_count,
        torrent_count=torrent_count,
        free_progress=100,
        ddl_progress=100,
        torrent_progress=100
    )
    
    # Close dialog if we created one
    if search_dialog:
        xbmc.sleep(500)
        search_dialog.close()
    
    if search_cancelled:
        xbmc.log('[Tinklepad] Search was cancelled by user', xbmc.LOGINFO)
        return []
    
    # Remove duplicates
    seen_urls = set()
    unique_sources = []
    for source in all_sources:
        url_hash = hashlib.md5(source['url'].encode()).hexdigest()
        if url_hash not in seen_urls:
            seen_urls.add(url_hash)
            unique_sources.append(source)
    
    # Sort: Free first (direct play), then debrid by quality
    quality_order = {'4K': 0, '1080p': 1, '720p': 2, 'HD': 2, '480p': 3, 'CAM': 5, 'Unknown': 4}
    
    unique_sources.sort(key=lambda x: (
        0 if x.get('free') else 1,
        0 if x.get('direct_play') else 1,
        quality_order.get(x.get('quality', 'Unknown'), 4),
        x.get('provider', 'ZZZ')
    ))
    
    xbmc.log(f'[Tinklepad] Total unique sources found: {len(unique_sources)} (Free: {free_count}, DDL: {ddl_count}, Torrent: {torrent_count}, External: {external_count})', xbmc.LOGINFO)
    return unique_sources


def play_source(sources, title='', year='', fanart='', poster=''):
    """Display source selection dialog and play selected source"""
    from resources.lib.gui import show_source_select
    
    if not sources:
        xbmcgui.Dialog().notification('Tinklepad', 'No sources found', xbmcgui.NOTIFICATION_WARNING, 3000)
        return
    
    debrid_status = debrid_manager.get_status()
    
    selected = show_source_select(
        sources=sources,
        title=title,
        year=year,
        fanart=fanart,
        poster=poster,
        debrid_status=debrid_status
    )
    
    if selected < 0:
        return
    
    source = sources[selected]
    url = source['url']
    
    xbmc.log(f'[Tinklepad] Selected source: {source.get("label", "Unknown")}', xbmc.LOGINFO)
    
    _play_resolved_source(source, url, title)


def _play_resolved_source(source, url, title=''):
    """Resolve and play the selected source"""
    dialog = xbmcgui.Dialog()
    stream_url = None
    use_download_first = False
    
    # Free direct play sources - use directly
    if source.get('free') and source.get('direct_play'):
        stream_url = url
        xbmc.log(f'[Tinklepad] Using direct free stream: {url}', xbmc.LOGINFO)
    
    # Debrid/Torrent sources - resolve through debrid
    elif source.get('debrid') or source.get('torrent'):
        resolved, service = debrid_manager.resolve(url)
        if resolved:
            if needs_download_first(url):
                xbmc.log(f'[Tinklepad] Using download-first for {source["host"]}', xbmc.LOGINFO)
                use_download_first = True
                
                download_pref = ADDON.getSetting('download_first_mode')
                if download_pref == '0':
                    choice = dialog.yesno(
                        'Download First?',
                        f'{source["host"]} links work better when downloaded first.\n\n'
                        'Download before playing for smooth playback?',
                        nolabel='Stream Directly',
                        yeslabel='Download First'
                    )
                    use_download_first = choice
                elif download_pref == '1':
                    use_download_first = True
                else:
                    use_download_first = False
                
                if use_download_first:
                    downloaded_path = download_and_play(resolved, title)
                    if downloaded_path:
                        stream_url = downloaded_path
                    else:
                        xbmcgui.Dialog().notification('Tinklepad', 'Download failed, trying direct stream...', xbmcgui.NOTIFICATION_WARNING, 3000)
                        stream_url = resolved
                else:
                    stream_url = resolved
            else:
                stream_url = resolved
            
            xbmc.log(f'[Tinklepad] Resolved through {service}', xbmc.LOGINFO)
        elif source.get('torrent'):
            xbmcgui.Dialog().notification('Tinklepad', 'Debrid required for torrents! Enable & authorize in settings.', xbmcgui.NOTIFICATION_WARNING, 5000)
            return
        else:
            xbmcgui.Dialog().notification('Tinklepad', 'Debrid resolution failed. Check authorization in settings.', xbmcgui.NOTIFICATION_WARNING, 5000)
    
    # Try ResolveURL as fallback
    if not stream_url and HAS_RESOLVEURL and not source.get('torrent'):
        try:
            stream_url = resolveurl.resolve(url)
        except:
            pass
    
    # Last resort for free sources
    if not stream_url and source.get('free'):
        stream_url = url
    
    if stream_url:
        try:
            li = xbmcgui.ListItem(path=stream_url)
            li.setProperty('IsPlayable', 'true')
            
            if title:
                li.setInfo('video', {'title': title})
            
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
            xbmc.log(f'[Tinklepad] Playing: {stream_url[:80]}...', xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f'[Tinklepad] Playback error: {e}', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Tinklepad', 'Playback failed', xbmcgui.NOTIFICATION_ERROR, 3000)
    else:
        xbmcgui.Dialog().notification('Tinklepad', 'Could not resolve link', xbmcgui.NOTIFICATION_ERROR, 3000)
