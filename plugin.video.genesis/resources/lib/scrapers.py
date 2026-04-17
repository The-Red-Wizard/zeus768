"""
Torrent Scrapers Module for Test1
10 Unique Torrent Sites (not Stremio/Torrentio)
Uses native urllib (no external requests module)
Updated with better error handling and multiple mirrors
"""
import json
import re
import xbmc
import xbmcaddon
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus, urlencode
import ssl

ADDON = xbmcaddon.Addon()
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

QUALITY_PATTERNS = {
    '2160p': r'(?:2160p|4k|uhd)',
    '1080p': r'(?:1080p|1080i|fhd)',
    '720p': r'(?:720p|hd)',
    '480p': r'(?:480p|sd)',
    '360p': r'(?:360p)'
}

QUALITY_ORDER = ['2160p', '1080p', '720p', '480p', '360p']

COMMON_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.bittor.pw:1337/announce",
    "udp://public.popcorn-tracker.org:6969/announce",
    "udp://tracker.dler.org:6969/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://open.demonii.com:1337/announce"
]

# Create SSL context that doesn't verify certificates (for sites with SSL issues)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


def extract_hash(magnet):
    """Extract info hash from magnet link"""
    if not magnet:
        return ''
    match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
    if match:
        return match.group(1).lower()
    match = re.search(r'btih:([a-zA-Z2-7]{32})', magnet)
    if match:
        return match.group(1).lower()
    return ''


def _http_get(url, headers=None, timeout=15):
    """HTTP GET request using urllib, returns response text or None"""
    hdrs = {'User-Agent': USER_AGENT}
    if headers:
        hdrs.update(headers)
    
    try:
        req = Request(url, headers=hdrs, method='GET')
        response = urlopen(req, timeout=timeout, context=ssl_context)
        return response.read().decode('utf-8', errors='replace')
    except HTTPError as e:
        xbmc.log(f'Scraper HTTP Error: {e.code} for {url}', xbmc.LOGWARNING)
        return None
    except URLError as e:
        xbmc.log(f'Scraper URL Error: {e.reason}', xbmc.LOGERROR)
        return None
    except Exception as e:
        xbmc.log(f'Scraper Request Error: {e}', xbmc.LOGERROR)
        return None


def _http_get_json(url, headers=None, timeout=15):
    """HTTP GET request using urllib, returns json data or None"""
    body = _http_get(url, headers, timeout)
    if body:
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None
    return None


def detect_quality(title):
    """Detect quality from torrent title"""
    title_lower = title.lower()
    for quality, pattern in QUALITY_PATTERNS.items():
        if re.search(pattern, title_lower):
            return quality
    return '720p'


def _build_magnet(info_hash, name):
    """Build a magnet link with trackers"""
    magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={quote_plus(name)}"
    for tracker in COMMON_TRACKERS:
        magnet += f"&tr={quote_plus(tracker)}"
    return magnet


def sort_by_quality(results, preferred_quality='1080p'):
    """Sort results by quality, prioritizing preferred and falling back to lower"""
    if not results:
        return []
    
    try:
        pref_idx = QUALITY_ORDER.index(preferred_quality)
    except ValueError:
        pref_idx = 1
    
    quality_groups = {q: [] for q in QUALITY_ORDER}
    unknown = []
    
    for result in results:
        quality = result.get('quality', detect_quality(result.get('title', '')))
        result['quality'] = quality
        if quality in quality_groups:
            quality_groups[quality].append(result)
        else:
            unknown.append(result)
    
    sorted_results = []
    
    for i in range(pref_idx, len(QUALITY_ORDER)):
        quality = QUALITY_ORDER[i]
        sorted_results.extend(sorted(quality_groups[quality], 
                                     key=lambda x: x.get('seeds', 0), reverse=True))
    
    for i in range(pref_idx):
        quality = QUALITY_ORDER[i]
        sorted_results.extend(sorted(quality_groups[quality], 
                                     key=lambda x: x.get('seeds', 0), reverse=True))
    
    sorted_results.extend(unknown)
    return sorted_results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 1: 1337x
# ══════════════════════════════════════════════════════════════════════════════

class L337xScraper:
    """1337x torrent scraper"""
    
    MIRRORS = [
        "https://1337x.to",
        "https://1337x.st",
        "https://x1337x.ws",
        "https://1337x.gd",
        "https://1337x.wtf"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_1337x') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        for mirror in self.MIRRORS:
            try:
                search_url = f"{mirror}/search/{quote_plus(query)}/1/"
                html = _http_get(search_url)
                
                if not html:
                    continue
                
                torrent_links = re.findall(r'href="(/torrent/\d+/[^"]+)"', html)
                seeds_matches = re.findall(r'class="coll-2 seeds">(\d+)</td>', html)
                
                if not torrent_links:
                    continue
                
                xbmc.log(f"1337x: Found {len(torrent_links)} results from {mirror}", xbmc.LOGINFO)
                
                for i, link in enumerate(torrent_links[:10]):
                    try:
                        torrent_url = f"{mirror}{link}"
                        torrent_html = _http_get(torrent_url, timeout=10)
                        
                        if not torrent_html:
                            continue
                        
                        magnet_match = re.search(r'href="(magnet:\?xt=urn:btih:[^"]+)"', torrent_html)
                        if not magnet_match:
                            continue
                        
                        magnet = magnet_match.group(1)
                        
                        title_match = re.search(r'<title>([^<]+)', torrent_html)
                        if title_match:
                            title = title_match.group(1).replace(' | 1337x', '').replace('Download ', '').strip()
                        else:
                            title = link.split('/')[-2].replace('-', ' ')
                        
                        seeds = int(seeds_matches[i]) if i < len(seeds_matches) else 0
                        
                        results.append({
                            'title': title,
                            'magnet': magnet,
                            'seeds': seeds,
                            'quality': detect_quality(title),
                            'source': '1337x'
                        })
                        
                    except Exception as e:
                        xbmc.log(f"1337x: Error parsing torrent page: {e}", xbmc.LOGDEBUG)
                        continue
                
                if results:
                    break
                    
            except Exception as e:
                xbmc.log(f"1337x mirror {mirror} failed: {str(e)}", xbmc.LOGWARNING)
                continue
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 2: The Pirate Bay
# ══════════════════════════════════════════════════════════════════════════════

class PirateBayScraper:
    """The Pirate Bay torrent scraper"""
    
    MIRRORS = [
        "https://apibay.org",
        "https://piratebay.party/api",
        "https://tpb.party/api"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_piratebay') == 'true'
    
    def search(self, query, category='video'):
        if not self.enabled:
            return []
        
        results = []
        cat_num = '200'
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/q.php?q={quote_plus(query)}&cat={cat_num}"
                res = _http_get_json(url)
                
                if res and isinstance(res, list) and len(res) > 0 and res[0].get('id') != '0':
                    for item in res[:15]:
                        if item.get('id') == '0':
                            continue
                        
                        name = item.get('name', '')
                        info_hash = item.get('info_hash', '')
                        seeds = int(item.get('seeders', 0))
                        size = int(item.get('size', 0))
                        
                        magnet = _build_magnet(info_hash, name)
                        
                        results.append({
                            'title': name,
                            'magnet': magnet,
                            'seeds': seeds,
                            'size': size,
                            'quality': detect_quality(name),
                            'source': 'PirateBay'
                        })
                    
                    xbmc.log(f"PirateBay: Found {len(results)} results", xbmc.LOGINFO)
                    break
                    
            except Exception as e:
                xbmc.log(f"PirateBay mirror {mirror} failed: {str(e)}", xbmc.LOGWARNING)
                continue
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 3: YTS (YIFY)
# ══════════════════════════════════════════════════════════════════════════════

class YTSScraper:
    """YTS (YIFY) movie torrent scraper"""
    
    MIRRORS = [
        "https://yts.mx/api/v2",
        "https://yts.torrentbay.to/api/v2",
        "https://yts.rs/api/v2"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_yts') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        for base_url in self.MIRRORS:
            try:
                url = f"{base_url}/list_movies.json?query_term={quote_plus(query)}&limit=20"
                data = _http_get_json(url)
                
                if data and data.get('status') == 'ok':
                    movies = data.get('data', {}).get('movies', [])
                    
                    for movie in movies:
                        title = movie.get('title', '')
                        year = movie.get('year', '')
                        
                        for torrent in movie.get('torrents', []):
                            quality = torrent.get('quality', '720p')
                            seeds = torrent.get('seeds', 0)
                            hash_val = torrent.get('hash', '')
                            size = torrent.get('size', '')
                            
                            if hash_val:
                                full_title = f"{title} ({year}) [{quality}] - YTS"
                                magnet = _build_magnet(hash_val, full_title)
                                
                                results.append({
                                    'title': full_title,
                                    'magnet': magnet,
                                    'seeds': seeds,
                                    'quality': quality,
                                    'size': size,
                                    'source': 'YTS'
                                })
                    
                    if results:
                        xbmc.log(f"YTS: Found {len(results)} results", xbmc.LOGINFO)
                        break
                        
            except Exception as e:
                xbmc.log(f"YTS failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 4: EZTV (TV Shows)
# ══════════════════════════════════════════════════════════════════════════════

class EZTVScraper:
    """EZTV TV show torrent scraper"""
    
    MIRRORS = [
        "https://eztvx.to",
        "https://eztv.re",
        "https://eztv.wf"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_eztv') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/search/{quote_plus(query)}"
                html = _http_get(url)
                
                if html:
                    # Parse magnet links from HTML
                    magnets = re.findall(r'href="(magnet:\?xt=urn:btih:[^"]+)"', html)
                    titles = re.findall(r'class="epinfo">([^<]+)</a>', html)
                    seeds_list = re.findall(r'forum_thread_post_end[^>]*>(\d+)</td>', html)
                    
                    if not magnets:
                        # Try alternative pattern
                        magnets = re.findall(r'href="(magnet:[^"]+)"', html)
                    
                    for i, magnet in enumerate(magnets[:15]):
                        title = titles[i] if i < len(titles) else f"EZTV Result {i+1}"
                        seeds = int(seeds_list[i]) if i < len(seeds_list) else 0
                        
                        results.append({
                            'title': title,
                            'magnet': magnet,
                            'seeds': seeds,
                            'quality': detect_quality(title),
                            'source': 'EZTV'
                        })
                    
                    if results:
                        xbmc.log(f"EZTV: Found {len(results)} results", xbmc.LOGINFO)
                        break
                        
            except Exception as e:
                xbmc.log(f"EZTV failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 5: LimeTorrents
# ══════════════════════════════════════════════════════════════════════════════

class LimeTorrentsScraper:
    """LimeTorrents scraper"""
    
    MIRRORS = [
        "https://www.limetorrents.lol",
        "https://www.limetorrents.info",
        "https://limetorrents.unblockit.tv"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_limetorrents') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/search/all/{quote_plus(query)}/seeds/1/"
                html = _http_get(url)
                
                if html:
                    # Parse magnet links
                    magnets = re.findall(r'href="(magnet:\?[^"]+)"', html)
                    # Parse titles
                    titles = re.findall(r'<div class="tt-name"><a[^>]*>([^<]+)</a>', html)
                    
                    if not titles:
                        titles = re.findall(r'class="tt-name"[^>]*>([^<]+)', html)
                    
                    for i, magnet in enumerate(magnets[:15]):
                        title = titles[i] if i < len(titles) else f"LimeTorrents Result {i+1}"
                        
                        results.append({
                            'title': title.strip(),
                            'magnet': magnet,
                            'seeds': 0,
                            'quality': detect_quality(title),
                            'source': 'LimeTorrents'
                        })
                    
                    if results:
                        xbmc.log(f"LimeTorrents: Found {len(results)} results", xbmc.LOGINFO)
                        break
                        
            except Exception as e:
                xbmc.log(f"LimeTorrents failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 6: TorrentGalaxy
# ══════════════════════════════════════════════════════════════════════════════

class TorrentGalaxyScraper:
    """TorrentGalaxy scraper"""
    
    MIRRORS = [
        "https://torrentgalaxy.to",
        "https://torrentgalaxy.mx",
        "https://tgx.rs"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_torrentgalaxy') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/torrents.php?search={quote_plus(query)}&sort=seeders&order=desc"
                html = _http_get(url)
                
                if html:
                    magnets = re.findall(r'href="(magnet:\?xt=urn:btih:[^"]+)"', html)
                    titles = re.findall(r'<a[^>]*title="([^"]+)"[^>]*class="txlight"', html)
                    
                    if not titles:
                        titles = re.findall(r'class="txlight">([^<]+)</a>', html)
                    
                    for i, magnet in enumerate(magnets[:15]):
                        title = titles[i] if i < len(titles) else f"TorrentGalaxy Result {i+1}"
                        
                        results.append({
                            'title': title.strip(),
                            'magnet': magnet,
                            'seeds': 0,
                            'quality': detect_quality(title),
                            'source': 'TorrentGalaxy'
                        })
                    
                    if results:
                        xbmc.log(f"TorrentGalaxy: Found {len(results)} results", xbmc.LOGINFO)
                        break
                        
            except Exception as e:
                xbmc.log(f"TorrentGalaxy failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 7: Nyaa (Anime)
# ══════════════════════════════════════════════════════════════════════════════

class NyaaScraper:
    """Nyaa anime torrent scraper"""
    
    MIRRORS = [
        "https://nyaa.si",
        "https://nyaa.land"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_nyaa') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/?f=0&c=0_0&q={quote_plus(query)}&s=seeders&o=desc"
                html = _http_get(url)
                
                if html:
                    # Parse torrent rows
                    magnets = re.findall(r'href="(magnet:\?[^"]+)"', html)
                    titles = re.findall(r'<td colspan="2">\s*<a[^>]*title="([^"]+)"', html)
                    seeds_list = re.findall(r'<td class="text-center">(\d+)</td>', html)
                    
                    for i, magnet in enumerate(magnets[:15]):
                        title = titles[i] if i < len(titles) else f"Nyaa Result {i+1}"
                        seeds = int(seeds_list[i*2]) if i*2 < len(seeds_list) else 0
                        
                        results.append({
                            'title': title.strip(),
                            'magnet': magnet,
                            'seeds': seeds,
                            'quality': detect_quality(title),
                            'source': 'Nyaa'
                        })
                    
                    if results:
                        xbmc.log(f"Nyaa: Found {len(results)} results", xbmc.LOGINFO)
                        break
                        
            except Exception as e:
                xbmc.log(f"Nyaa failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 8: Magnetdl
# ══════════════════════════════════════════════════════════════════════════════

class MagnetdlScraper:
    """Magnetdl scraper"""
    
    MIRRORS = [
        "https://www.magnetdl.com",
        "https://magnetdl.unblockit.tv"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_magnetdl') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        for mirror in self.MIRRORS:
            try:
                # Magnetdl uses first letter of query in URL
                first_letter = query[0].lower() if query else 'a'
                if not first_letter.isalpha():
                    first_letter = '0'
                
                search_query = query.replace(' ', '-').lower()
                url = f"{mirror}/{first_letter}/{search_query}/"
                html = _http_get(url)
                
                if html:
                    magnets = re.findall(r'href="(magnet:\?xt=urn:btih:[^"]+)"', html)
                    titles = re.findall(r'class="n"[^>]*><a[^>]*title="([^"]+)"', html)
                    seeds_list = re.findall(r'class="s">(\d+)</td>', html)
                    
                    for i, magnet in enumerate(magnets[:15]):
                        title = titles[i] if i < len(titles) else f"Magnetdl Result {i+1}"
                        seeds = int(seeds_list[i]) if i < len(seeds_list) else 0
                        
                        results.append({
                            'title': title.strip(),
                            'magnet': magnet,
                            'seeds': seeds,
                            'quality': detect_quality(title),
                            'source': 'Magnetdl'
                        })
                    
                    if results:
                        xbmc.log(f"Magnetdl: Found {len(results)} results", xbmc.LOGINFO)
                        break
                        
            except Exception as e:
                xbmc.log(f"Magnetdl failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 9: SolidTorrents
# ══════════════════════════════════════════════════════════════════════════════

class SolidTorrentsScraper:
    """SolidTorrents scraper"""
    
    MIRRORS = [
        "https://solidtorrents.to",
        "https://solidtorrents.net"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_solidtorrents') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/api/v1/search?q={quote_plus(query)}&category=Video&sort=seeders"
                data = _http_get_json(url)
                
                if data and data.get('results'):
                    for item in data['results'][:15]:
                        title = item.get('title', '')
                        info_hash = item.get('infohash', '')
                        seeds = item.get('swarm', {}).get('seeders', 0)
                        size = item.get('size', 0)
                        
                        if info_hash:
                            magnet = _build_magnet(info_hash, title)
                            
                            results.append({
                                'title': title,
                                'magnet': magnet,
                                'seeds': seeds,
                                'size': size,
                                'quality': detect_quality(title),
                                'source': 'SolidTorrents'
                            })
                    
                    if results:
                        xbmc.log(f"SolidTorrents: Found {len(results)} results", xbmc.LOGINFO)
                        break
                        
            except Exception as e:
                xbmc.log(f"SolidTorrents failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 10: BitSearch
# ══════════════════════════════════════════════════════════════════════════════

class BitSearchScraper:
    """BitSearch torrent scraper"""
    
    MIRRORS = [
        "https://bitsearch.to",
        "https://bitsearch.unblockit.tv"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_bitsearch') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/search?q={quote_plus(query)}&category=1&subcat=2&sort=seeders"
                html = _http_get(url)
                
                if html:
                    magnets = re.findall(r'href="(magnet:\?xt=urn:btih:[^"]+)"', html)
                    titles = re.findall(r'class="title"[^>]*>\s*<a[^>]*>([^<]+)</a>', html)
                    
                    if not titles:
                        titles = re.findall(r'<h5[^>]*class="title"[^>]*>([^<]+)</h5>', html)
                    
                    for i, magnet in enumerate(magnets[:15]):
                        title = titles[i].strip() if i < len(titles) else f"BitSearch Result {i+1}"
                        
                        results.append({
                            'title': title,
                            'magnet': magnet,
                            'seeds': 0,
                            'quality': detect_quality(title),
                            'source': 'BitSearch'
                        })
                    
                    if results:
                        xbmc.log(f"BitSearch: Found {len(results)} results", xbmc.LOGINFO)
                        break
                        
            except Exception as e:
                xbmc.log(f"BitSearch failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SEARCH FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def search_all(query, preferred_quality='1080p'):
    """Search all enabled scrapers and return sorted results"""
    all_results = []
    
    scrapers = [
        L337xScraper(),
        PirateBayScraper(),
        YTSScraper(),
        EZTVScraper(),
        LimeTorrentsScraper(),
        TorrentGalaxyScraper(),
        NyaaScraper(),
        MagnetdlScraper(),
        SolidTorrentsScraper(),
        BitSearchScraper()
    ]
    
    for scraper in scrapers:
        try:
            results = scraper.search(query)
            if results:
                all_results.extend(results)
                xbmc.log(f"Scraper {scraper.__class__.__name__}: Found {len(results)} results", xbmc.LOGINFO)
            else:
                xbmc.log(f"Scraper {scraper.__class__.__name__}: No results", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"Scraper {scraper.__class__.__name__} failed: {str(e)}", xbmc.LOGWARNING)
    
    xbmc.log(f"Total results from all scrapers: {len(all_results)}", xbmc.LOGINFO)
    
    return sort_by_quality(all_results, preferred_quality)
