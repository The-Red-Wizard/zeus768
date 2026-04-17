# -*- coding: utf-8 -*-
"""
Anime-Specific Torrent Scrapers for Test1
Sites: Nyaa, SubsPlease, AnimeTosho, TokyoTosho, AniDex, Erai-Raws
"""
import json
import re
import xbmc
import xbmcaddon
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus
import ssl

ADDON = xbmcaddon.Addon()
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

QUALITY_PATTERNS = {
    '2160p': r'(?:2160p|4k|uhd)',
    '1080p': r'(?:1080p|1080i|fhd)',
    '720p': r'(?:720p|hd)',
    '480p': r'(?:480p|sd)',
}

QUALITY_ORDER = ['2160p', '1080p', '720p', '480p']

COMMON_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.bittor.pw:1337/announce",
    "udp://public.popcorn-tracker.org:6969/announce",
    "udp://tracker.dler.org:6969/announce",
    "http://nyaa.tracker.wf:7777/announce",
    "http://anidex.moe:6969/announce"
]

# SSL context
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
    """HTTP GET request using urllib"""
    hdrs = {'User-Agent': USER_AGENT}
    if headers:
        hdrs.update(headers)
    
    try:
        req = Request(url, headers=hdrs, method='GET')
        response = urlopen(req, timeout=timeout, context=ssl_context)
        return response.read().decode('utf-8', errors='replace')
    except HTTPError as e:
        xbmc.log(f'Anime Scraper HTTP Error: {e.code} for {url}', xbmc.LOGWARNING)
        return None
    except URLError as e:
        xbmc.log(f'Anime Scraper URL Error: {e.reason}', xbmc.LOGERROR)
        return None
    except Exception as e:
        xbmc.log(f'Anime Scraper Error: {e}', xbmc.LOGERROR)
        return None


def _http_get_json(url, headers=None, timeout=15):
    """HTTP GET request, returns json"""
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
    """Build a magnet link with anime trackers"""
    magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={quote_plus(name)}"
    for tracker in COMMON_TRACKERS:
        magnet += f"&tr={quote_plus(tracker)}"
    return magnet


def detect_subgroup(title):
    """Detect fansub group from title"""
    match = re.match(r'^\[([^\]]+)\]', title)
    if match:
        return match.group(1)
    return ''


def sort_by_quality(results, preferred_quality='1080p'):
    """Sort results by quality"""
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
# SCRAPER 1: Nyaa.si (Best Anime Site)
# ══════════════════════════════════════════════════════════════════════════════

class NyaaAnimeScraper:
    """Nyaa.si anime torrent scraper"""
    
    MIRRORS = [
        "https://nyaa.si",
        "https://nyaa.land",
        "https://nyaa.ink"
    ]
    
    CATEGORIES = {
        'all': '0_0',
        'anime': '1_0',
        'anime_amv': '1_1',
        'anime_english': '1_2',
        'anime_non_english': '1_3',
        'anime_raw': '1_4',
    }
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_nyaa') == 'true'
    
    def search(self, query, category='anime'):
        if not self.enabled:
            return []
        
        results = []
        cat = self.CATEGORIES.get(category, '1_0')
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/?f=0&c={cat}&q={quote_plus(query)}&s=seeders&o=desc"
                html = _http_get(url)
                
                if not html:
                    continue
                
                # Parse torrent rows
                rows = re.findall(r'<tr class="(?:default|success|danger)">(.*?)</tr>', html, re.DOTALL)
                
                for row in rows[:20]:
                    # Extract magnet
                    magnet_match = re.search(r'href="(magnet:\?[^"]+)"', row)
                    if not magnet_match:
                        continue
                    magnet = magnet_match.group(1)
                    
                    # Extract title
                    title_match = re.search(r'<a[^>]*title="([^"]+)"[^>]*class="[^"]*"[^>]*>', row)
                    if not title_match:
                        title_match = re.search(r'<a[^>]+>([^<]+)</a>', row)
                    title = title_match.group(1) if title_match else 'Unknown'
                    title = title.strip()
                    
                    # Extract seeds/leechers
                    seeds_match = re.findall(r'<td[^>]*>(\d+)</td>', row)
                    seeds = int(seeds_match[-2]) if len(seeds_match) >= 2 else 0
                    
                    # Extract size
                    size_match = re.search(r'<td[^>]*>(\d+(?:\.\d+)?\s*[GMK]iB)</td>', row)
                    size = size_match.group(1) if size_match else ''
                    
                    results.append({
                        'title': title,
                        'magnet': magnet,
                        'seeds': seeds,
                        'size': size,
                        'quality': detect_quality(title),
                        'subgroup': detect_subgroup(title),
                        'source': 'Nyaa'
                    })
                
                if results:
                    xbmc.log(f"Nyaa: Found {len(results)} results", xbmc.LOGINFO)
                    break
                    
            except Exception as e:
                xbmc.log(f"Nyaa failed: {str(e)}", xbmc.LOGWARNING)
                continue
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 2: SubsPlease (Daily Subbed Episodes)
# ══════════════════════════════════════════════════════════════════════════════

class SubsPleaseScraper:
    """SubsPlease daily fansub scraper"""
    
    BASE_URL = "https://subsplease.org"
    API_URL = "https://subsplease.org/api"
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_subsplease') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # Use API endpoint
            url = f"{self.API_URL}/?f=search&tz=UTC&s={quote_plus(query)}"
            data = _http_get_json(url)
            
            if data and isinstance(data, dict):
                for show_name, episodes in data.items():
                    if not isinstance(episodes, list):
                        continue
                    
                    for ep in episodes[:10]:
                        if not isinstance(ep, dict):
                            continue
                        
                        ep_num = ep.get('episode', '')
                        downloads = ep.get('downloads', [])
                        
                        for dl in downloads:
                            if not isinstance(dl, dict):
                                continue
                            
                            magnet = dl.get('magnet', '')
                            if not magnet:
                                continue
                            
                            res = dl.get('res', '720p')
                            title = f"[SubsPlease] {show_name}"
                            if ep_num:
                                title += f" - {ep_num}"
                            title += f" ({res})"
                            
                            results.append({
                                'title': title,
                                'magnet': magnet,
                                'seeds': 0,
                                'quality': res,
                                'subgroup': 'SubsPlease',
                                'source': 'SubsPlease'
                            })
            
            # Also try RSS/HTML scrape
            if not results:
                html = _http_get(f"{self.BASE_URL}/shows/{quote_plus(query.lower().replace(' ', '-'))}/")
                if html:
                    magnets = re.findall(r'href="(magnet:\?[^"]+)"', html)
                    for i, magnet in enumerate(magnets[:15]):
                        results.append({
                            'title': f'[SubsPlease] {query} - Result {i+1}',
                            'magnet': magnet,
                            'seeds': 0,
                            'quality': '1080p',
                            'subgroup': 'SubsPlease',
                            'source': 'SubsPlease'
                        })
            
            if results:
                xbmc.log(f"SubsPlease: Found {len(results)} results", xbmc.LOGINFO)
                
        except Exception as e:
            xbmc.log(f"SubsPlease failed: {str(e)}", xbmc.LOGWARNING)
        
        return results
    
    def get_latest(self):
        """Get latest releases from SubsPlease"""
        results = []
        
        try:
            url = f"{self.API_URL}/?f=latest&tz=UTC"
            data = _http_get_json(url)
            
            if data and isinstance(data, list):
                for item in data[:30]:
                    if not isinstance(item, dict):
                        continue
                    
                    show = item.get('show', '')
                    episode = item.get('episode', '')
                    downloads = item.get('downloads', [])
                    
                    for dl in downloads:
                        if not isinstance(dl, dict):
                            continue
                        
                        magnet = dl.get('magnet', '')
                        if not magnet:
                            continue
                        
                        res = dl.get('res', '720p')
                        title = f"[SubsPlease] {show}"
                        if episode:
                            title += f" - {episode}"
                        title += f" ({res})"
                        
                        results.append({
                            'title': title,
                            'magnet': magnet,
                            'seeds': 0,
                            'quality': res,
                            'subgroup': 'SubsPlease',
                            'source': 'SubsPlease'
                        })
            
            xbmc.log(f"SubsPlease Latest: Found {len(results)} results", xbmc.LOGINFO)
            
        except Exception as e:
            xbmc.log(f"SubsPlease latest failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 3: AnimeTosho (Ad-Free P2P)
# ══════════════════════════════════════════════════════════════════════════════

class AnimeToshoScraper:
    """AnimeTosho ad-free anime torrent scraper"""
    
    MIRRORS = [
        "https://animetosho.org",
        "https://animetosho.xyz"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_animetosho') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/search?q={quote_plus(query)}&order=size-d"
                html = _http_get(url)
                
                if not html:
                    continue
                
                # Parse entries
                entries = re.findall(r'<div class="home_list_entry">(.*?)</div>\s*</div>', html, re.DOTALL)
                
                for entry in entries[:20]:
                    # Title
                    title_match = re.search(r'<a[^>]*class="link"[^>]*>([^<]+)</a>', entry)
                    title = title_match.group(1).strip() if title_match else 'Unknown'
                    
                    # Magnet
                    magnet_match = re.search(r'href="(magnet:\?[^"]+)"', entry)
                    if not magnet_match:
                        # Try to get torrent hash
                        hash_match = re.search(r'/view/([a-f0-9]+)', entry)
                        if hash_match:
                            magnet = _build_magnet(hash_match.group(1), title)
                        else:
                            continue
                    else:
                        magnet = magnet_match.group(1)
                    
                    # Size
                    size_match = re.search(r'(\d+(?:\.\d+)?\s*[GMK]B)', entry)
                    size = size_match.group(1) if size_match else ''
                    
                    results.append({
                        'title': title,
                        'magnet': magnet,
                        'seeds': 0,
                        'size': size,
                        'quality': detect_quality(title),
                        'subgroup': detect_subgroup(title),
                        'source': 'AnimeTosho'
                    })
                
                if results:
                    xbmc.log(f"AnimeTosho: Found {len(results)} results", xbmc.LOGINFO)
                    break
                    
            except Exception as e:
                xbmc.log(f"AnimeTosho failed: {str(e)}", xbmc.LOGWARNING)
                continue
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 4: TokyoTosho (Japanese Media)
# ══════════════════════════════════════════════════════════════════════════════

class TokyoToshoScraper:
    """TokyoTosho Japanese media scraper"""
    
    BASE_URL = "https://www.tokyotosho.info"
    
    CATEGORIES = {
        'all': 0,
        'anime': 1,
        'music': 2,
        'manga': 3,
        'hentai': 4,
        'other': 5,
        'drama': 8,
        'music_video': 9,
        'raw': 7
    }
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_tokyotosho') == 'true'
    
    def search(self, query, category='anime'):
        if not self.enabled:
            return []
        
        results = []
        cat = self.CATEGORIES.get(category, 1)
        
        try:
            url = f"{self.BASE_URL}/search.php?terms={quote_plus(query)}&type={cat}&searchName=true&searchComment=false&size_min=&size_max=&username="
            html = _http_get(url)
            
            if not html:
                return results
            
            # Parse table rows
            rows = re.findall(r'<tr class="category_\d+">(.*?)</tr>', html, re.DOTALL)
            
            for row in rows[:20]:
                # Title
                title_match = re.search(r'<a rel="nofollow"[^>]*>([^<]+)</a>', row)
                title = title_match.group(1).strip() if title_match else 'Unknown'
                
                # Magnet
                magnet_match = re.search(r'href="(magnet:\?[^"]+)"', row)
                if not magnet_match:
                    continue
                magnet = magnet_match.group(1)
                
                # Size
                size_match = re.search(r'Size:\s*(\d+(?:\.\d+)?\s*[GMK]B)', row)
                size = size_match.group(1) if size_match else ''
                
                # Seeds
                seeds_match = re.search(r'S:\s*(\d+)', row)
                seeds = int(seeds_match.group(1)) if seeds_match else 0
                
                results.append({
                    'title': title,
                    'magnet': magnet,
                    'seeds': seeds,
                    'size': size,
                    'quality': detect_quality(title),
                    'subgroup': detect_subgroup(title),
                    'source': 'TokyoTosho'
                })
            
            if results:
                xbmc.log(f"TokyoTosho: Found {len(results)} results", xbmc.LOGINFO)
                
        except Exception as e:
            xbmc.log(f"TokyoTosho failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 5: AniDex (Multi-Language)
# ══════════════════════════════════════════════════════════════════════════════

class AniDexScraper:
    """AniDex multi-language anime torrent scraper"""
    
    BASE_URL = "https://anidex.info"
    
    LANGUAGES = {
        'english': 1,
        'japanese': 2,
        'polish': 3,
        'french': 5,
        'german': 6,
        'spanish': 8,
        'italian': 9,
        'korean': 10,
        'chinese': 11
    }
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_anidex') == 'true'
    
    def search(self, query, language=None):
        if not self.enabled:
            return []
        
        results = []
        
        try:
            url = f"{self.BASE_URL}/?q={quote_plus(query)}&s=seeders&o=desc"
            if language and language in self.LANGUAGES:
                url += f"&lang_id={self.LANGUAGES[language]}"
            
            html = _http_get(url)
            
            if not html:
                return results
            
            # Parse torrent rows
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
            
            for row in rows[:20]:
                # Skip header
                if '<th' in row:
                    continue
                
                # Magnet
                magnet_match = re.search(r'href="(magnet:\?[^"]+)"', row)
                if not magnet_match:
                    continue
                magnet = magnet_match.group(1)
                
                # Title
                title_match = re.search(r'<a[^>]*span="[^"]*"[^>]*>([^<]+)</a>', row)
                if not title_match:
                    title_match = re.search(r'class="torrent"[^>]*>([^<]+)</a>', row)
                title = title_match.group(1).strip() if title_match else 'Unknown'
                
                # Size
                size_match = re.search(r'<td[^>]*>(\d+(?:\.\d+)?\s*[GMK]iB)</td>', row)
                size = size_match.group(1) if size_match else ''
                
                # Seeds
                seeds_match = re.search(r'text-success[^>]*>(\d+)</span>', row)
                seeds = int(seeds_match.group(1)) if seeds_match else 0
                
                results.append({
                    'title': title,
                    'magnet': magnet,
                    'seeds': seeds,
                    'size': size,
                    'quality': detect_quality(title),
                    'subgroup': detect_subgroup(title),
                    'source': 'AniDex'
                })
            
            if results:
                xbmc.log(f"AniDex: Found {len(results)} results", xbmc.LOGINFO)
                
        except Exception as e:
            xbmc.log(f"AniDex failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 6: Erai-Raws (Raw Episodes)
# ══════════════════════════════════════════════════════════════════════════════

class EraiRawsScraper:
    """Erai-Raws multi-sub anime scraper"""
    
    BASE_URL = "https://www.erai-raws.info"
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_erairaws') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # Erai-Raws doesn't have a search, scrape RSS or use Nyaa for Erai-Raws releases
            # Fall back to Nyaa with [Erai-raws] filter
            nyaa = NyaaAnimeScraper()
            nyaa.enabled = True  # Force enable for this search
            
            search_query = f"[Erai-raws] {query}"
            nyaa_results = nyaa.search(search_query, 'anime')
            
            for r in nyaa_results:
                r['source'] = 'Erai-Raws'
                r['subgroup'] = 'Erai-raws'
                results.append(r)
            
            if results:
                xbmc.log(f"Erai-Raws: Found {len(results)} results", xbmc.LOGINFO)
                
        except Exception as e:
            xbmc.log(f"Erai-Raws failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 7: BakaBT (Private Tracker - Public Search)
# ══════════════════════════════════════════════════════════════════════════════

class BakaBTScraper:
    """BakaBT public search scraper"""
    
    BASE_URL = "https://bakabt.me"
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_bakabt') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        try:
            url = f"{self.BASE_URL}/browse.php?q={quote_plus(query)}"
            html = _http_get(url)
            
            if not html:
                return results
            
            # Parse table rows
            rows = re.findall(r'<tr class="torrent[^"]*"[^>]*>(.*?)</tr>', html, re.DOTALL)
            
            for row in rows[:15]:
                # Title
                title_match = re.search(r'<a class="title"[^>]*>([^<]+)</a>', row)
                title = title_match.group(1).strip() if title_match else 'Unknown'
                
                # Hash for magnet
                hash_match = re.search(r'/torrent/(\d+)/', row)
                if not hash_match:
                    continue
                
                # Note: BakaBT requires login for magnets, so we create a reference
                torrent_id = hash_match.group(1)
                
                # Size
                size_match = re.search(r'class="size">([^<]+)</td>', row)
                size = size_match.group(1).strip() if size_match else ''
                
                results.append({
                    'title': f'{title} [BakaBT ID: {torrent_id}]',
                    'magnet': '',  # BakaBT requires login
                    'seeds': 0,
                    'size': size,
                    'quality': detect_quality(title),
                    'source': 'BakaBT',
                    'note': 'Requires BakaBT account'
                })
            
            if results:
                xbmc.log(f"BakaBT: Found {len(results)} results (login required)", xbmc.LOGINFO)
                
        except Exception as e:
            xbmc.log(f"BakaBT failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 8: Shana Project
# ══════════════════════════════════════════════════════════════════════════════

class ShanaProjectScraper:
    """Shana Project anime scraper"""
    
    BASE_URL = "https://www.shanaproject.com"
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_shanaproject') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        
        try:
            url = f"{self.BASE_URL}/search/?title={quote_plus(query)}&subber="
            html = _http_get(url)
            
            if not html:
                return results
            
            # Parse releases
            releases = re.findall(r'<tr class="release[^"]*"[^>]*>(.*?)</tr>', html, re.DOTALL)
            
            for release in releases[:20]:
                # Title
                title_match = re.search(r'<a[^>]*>([^<]+)</a>', release)
                title = title_match.group(1).strip() if title_match else 'Unknown'
                
                # Magnet
                magnet_match = re.search(r'href="(magnet:\?[^"]+)"', release)
                if not magnet_match:
                    continue
                magnet = magnet_match.group(1)
                
                results.append({
                    'title': title,
                    'magnet': magnet,
                    'seeds': 0,
                    'quality': detect_quality(title),
                    'subgroup': detect_subgroup(title),
                    'source': 'ShanaProject'
                })
            
            if results:
                xbmc.log(f"ShanaProject: Found {len(results)} results", xbmc.LOGINFO)
                
        except Exception as e:
            xbmc.log(f"ShanaProject failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ANIME SEARCH FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def search_all_anime(query, preferred_quality='1080p'):
    """Search all enabled anime scrapers and return sorted results"""
    all_results = []
    
    scrapers = [
        NyaaAnimeScraper(),
        SubsPleaseScraper(),
        AnimeToshoScraper(),
        TokyoToshoScraper(),
        AniDexScraper(),
        EraiRawsScraper(),
        ShanaProjectScraper(),
    ]
    
    for scraper in scrapers:
        try:
            results = scraper.search(query)
            if results:
                all_results.extend(results)
                xbmc.log(f"Anime Scraper {scraper.__class__.__name__}: Found {len(results)} results", xbmc.LOGINFO)
            else:
                xbmc.log(f"Anime Scraper {scraper.__class__.__name__}: No results", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"Anime Scraper {scraper.__class__.__name__} failed: {str(e)}", xbmc.LOGWARNING)
    
    xbmc.log(f"Total anime results from all scrapers: {len(all_results)}", xbmc.LOGINFO)
    
    return sort_by_quality(all_results, preferred_quality)


def get_latest_anime_releases():
    """Get latest anime releases from SubsPlease and Nyaa"""
    all_results = []
    
    # SubsPlease latest
    try:
        sp = SubsPleaseScraper()
        sp.enabled = True
        latest = sp.get_latest()
        all_results.extend(latest)
    except Exception as e:
        xbmc.log(f"SubsPlease latest failed: {e}", xbmc.LOGWARNING)
    
    # Nyaa latest (search for recent popular subs)
    try:
        nyaa = NyaaAnimeScraper()
        nyaa.enabled = True
        # Search for popular subgroups
        for group in ['[SubsPlease]', '[Erai-raws]', '[ASW]', '[Judas]']:
            results = nyaa.search(group, 'anime')
            all_results.extend(results[:5])
    except Exception as e:
        xbmc.log(f"Nyaa latest failed: {e}", xbmc.LOGWARNING)
    
    return all_results[:50]
