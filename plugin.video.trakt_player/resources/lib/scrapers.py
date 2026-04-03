import requests
import re
import xbmc
import xbmcaddon
from urllib.parse import quote_plus

ADDON = xbmcaddon.Addon()

# Quality detection patterns
QUALITY_PATTERNS = {
    '2160p': r'(?:2160p|4k|uhd)',
    '1080p': r'(?:1080p|1080i|fhd)',
    '720p': r'(?:720p|hd)',
    '480p': r'(?:480p|sd)',
    '360p': r'(?:360p)'
}

QUALITY_ORDER = ['2160p', '1080p', '720p', '480p', '360p']


def detect_quality(title):
    """Detect quality from torrent title"""
    title_lower = title.lower()
    for quality, pattern in QUALITY_PATTERNS.items():
        if re.search(pattern, title_lower):
            return quality
    return '480p'  # Default if not detected


def sort_by_quality(results, preferred_quality='1080p'):
    """Sort results by quality, prioritizing preferred and falling back to lower"""
    if not results:
        return []
    
    # Find the index of preferred quality
    try:
        pref_idx = QUALITY_ORDER.index(preferred_quality)
    except ValueError:
        pref_idx = 1  # Default to 1080p index
    
    # Create quality groups
    quality_groups = {q: [] for q in QUALITY_ORDER}
    unknown = []
    
    for result in results:
        quality = result.get('quality', detect_quality(result.get('title', '')))
        result['quality'] = quality
        if quality in quality_groups:
            quality_groups[quality].append(result)
        else:
            unknown.append(result)
    
    # Build sorted list: preferred quality first, then lower qualities
    sorted_results = []
    
    # Start from preferred quality and go down
    for i in range(pref_idx, len(QUALITY_ORDER)):
        quality = QUALITY_ORDER[i]
        # Sort by seeds within same quality
        sorted_results.extend(sorted(quality_groups[quality], 
                                     key=lambda x: x.get('seeds', 0), reverse=True))
    
    # Add higher qualities at the end (user might want them too)
    for i in range(pref_idx):
        quality = QUALITY_ORDER[i]
        sorted_results.extend(sorted(quality_groups[quality], 
                                     key=lambda x: x.get('seeds', 0), reverse=True))
    
    sorted_results.extend(unknown)
    return sorted_results


class PirateBayScraper:
    """The Pirate Bay torrent scraper"""
    
    # Multiple mirrors for redundancy
    MIRRORS = [
        "https://apibay.org",
        "https://piratebay.party",
        "https://thepiratebay.org"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_piratebay') == 'true'
    
    def search(self, query, category='video'):
        """Search for torrents"""
        if not self.enabled:
            return []
        
        results = []
        cat_num = '200'  # Video category
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/q.php?q={quote_plus(query)}&cat={cat_num}"
                res = requests.get(url, timeout=10).json()
                
                if res and res[0].get('id') != '0':  # Valid results
                    for item in res[:20]:  # Limit results
                        if item.get('id') == '0':
                            continue
                        
                        name = item.get('name', '')
                        info_hash = item.get('info_hash', '')
                        seeds = int(item.get('seeders', 0))
                        size = int(item.get('size', 0))
                        
                        # Build magnet link
                        magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={quote_plus(name)}"
                        
                        # Add common trackers
                        trackers = [
                            "udp://tracker.opentrackr.org:1337/announce",
                            "udp://open.stealth.si:80/announce",
                            "udp://tracker.torrent.eu.org:451/announce",
                            "udp://tracker.bittor.pw:1337/announce",
                            "udp://public.popcorn-tracker.org:6969/announce"
                        ]
                        for tracker in trackers:
                            magnet += f"&tr={quote_plus(tracker)}"
                        
                        results.append({
                            'title': name,
                            'magnet': magnet,
                            'seeds': seeds,
                            'size': size,
                            'quality': detect_quality(name),
                            'source': 'PirateBay'
                        })
                    
                    break  # Success, no need to try other mirrors
                    
            except Exception as e:
                xbmc.log(f"PirateBay mirror {mirror} failed: {str(e)}", xbmc.LOGWARNING)
                continue
        
        return results


class Rarbg:
    """RARBG-style torrent scraper (using TorrentAPI)"""
    
    API_URL = "https://torrentapi.org/pubapi_v2.php"
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_rarbg') == 'true'
        self.token = None
    
    def _get_token(self):
        """Get API token"""
        try:
            res = requests.get(
                self.API_URL,
                params={"get_token": "get_token", "app_id": "TraktPlayer"},
                timeout=10
            ).json()
            self.token = res.get('token')
        except:
            pass
    
    def search(self, query):
        if not self.enabled:
            return []
        
        if not self.token:
            self._get_token()
        
        if not self.token:
            return []
        
        results = []
        try:
            res = requests.get(
                self.API_URL,
                params={
                    "mode": "search",
                    "search_string": query,
                    "category": "movies;tv",
                    "token": self.token,
                    "format": "json_extended",
                    "app_id": "TraktPlayer"
                },
                timeout=10
            ).json()
            
            for item in res.get('torrent_results', []):
                results.append({
                    'title': item.get('title', ''),
                    'magnet': item.get('download', ''),
                    'seeds': item.get('seeders', 0),
                    'size': item.get('size', 0),
                    'quality': detect_quality(item.get('title', '')),
                    'source': 'RARBG'
                })
        except:
            pass
        
        return results


class TorrentGalaxy:
    """TorrentGalaxy scraper"""
    
    BASE_URL = "https://torrentgalaxy.to"
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_torrentgalaxy') == 'true'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        try:
            url = f"{self.BASE_URL}/torrents.php?search={quote_plus(query)}&sort=seeders&order=desc"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            html = requests.get(url, headers=headers, timeout=10).text
            
            # Parse magnet links
            magnets = re.findall(r'href="(magnet:\?xt=urn:btih:[^"]+)"', html)
            titles = re.findall(r'class="txlight">([^<]+)</a>', html)
            
            for i, magnet in enumerate(magnets[:20]):
                title = titles[i] if i < len(titles) else f"Result {i+1}"
                results.append({
                    'title': title,
                    'magnet': magnet,
                    'seeds': 0,
                    'quality': detect_quality(title),
                    'source': 'TorrentGalaxy'
                })
        except Exception as e:
            xbmc.log(f"TorrentGalaxy failed: {str(e)}", xbmc.LOGWARNING)
        
        return results


def search_all(query, preferred_quality='1080p'):
    """Search all enabled scrapers and return sorted results"""
    all_results = []
    
    scrapers = [
        PirateBayScraper(),
        Rarbg(),
        TorrentGalaxy()
    ]
    
    for scraper in scrapers:
        try:
            results = scraper.search(query)
            all_results.extend(results)
        except Exception as e:
            xbmc.log(f"Scraper failed: {str(e)}", xbmc.LOGWARNING)
    
    # Sort by quality with fallback
    return sort_by_quality(all_results, preferred_quality)
