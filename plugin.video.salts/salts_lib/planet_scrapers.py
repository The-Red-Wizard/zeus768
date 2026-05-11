"""
PlanetScrapers - aggregated torrent scrapers for SALTS
Uses native urllib (no external requests module)

Bundles Torrentio (IMDB-based, Stremio public API), Pirate Bay, RARBG,
TorrentGalaxy and 1337x into a single search aggregator. Originally
ported from the C.O.S.M.O.S addon and renamed for SALTS distribution.
"""
import json
import re
import xbmc
import xbmcaddon
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus

ADDON = xbmcaddon.Addon()
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Modern Chrome headers that bypass Cloudflare WAF on 1337x / TPB / TGx /
# RARBG mirrors.  Without these the bare urllib UA is fingerprinted and
# every request returns HTTP 403.
_BROWSER_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
              'application/json;q=0.8,*/*;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'sec-ch-ua': '"Chromium";v="120", "Google Chrome";v="120", "Not?A_Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# Quality detection patterns
QUALITY_PATTERNS = {
    '2160p': r'(?:2160p|4k|uhd)',
    '1080p': r'(?:1080p|1080i|fhd)',
    '720p': r'(?:720p|hd)',
    '480p': r'(?:480p|sd)',
    '360p': r'(?:360p)'
}

QUALITY_ORDER = ['2160p', '1080p', '720p', '480p', '360p']


def extract_hash(magnet):
    """Extract info hash from magnet link"""
    if not magnet:
        return ''
    match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
    if match:
        return match.group(1).lower()
    # Also support base32 encoded hashes (32 chars)
    match = re.search(r'btih:([a-zA-Z2-7]{32})', magnet)
    if match:
        return match.group(1).lower()
    return ''


def _http_get(url, headers=None, timeout=10):
    """HTTP GET request using urllib, returns response text or None"""
    hdrs = dict(_BROWSER_HEADERS)
    if headers:
        hdrs.update(headers)
    
    try:
        req = Request(url, headers=hdrs, method='GET')
        response = urlopen(req, timeout=timeout)
        raw = response.read()
        # Some Cloudflare-fronted sites send gzip even when not requested.
        if raw[:2] == b'\x1f\x8b':
            import gzip
            raw = gzip.decompress(raw)
        return raw.decode('utf-8', errors='replace')
    except HTTPError as e:
        xbmc.log(f'Scraper HTTP Error: {e.code} for {url}', xbmc.LOGWARNING)
        return None
    except URLError as e:
        xbmc.log(f'Scraper URL Error: {e.reason} for {url}', xbmc.LOGERROR)
        return None
    except Exception as e:
        xbmc.log(f'Scraper Request Error: {e} for {url}', xbmc.LOGERROR)
        return None


def _http_get_json(url, headers=None, timeout=10):
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
        self.enabled = ADDON.getSetting('enable_piratebay') != 'false'
    
    def search(self, query, category='video'):
        """Search for torrents"""
        if not self.enabled:
            return []
        
        results = []
        cat_num = '200'  # Video category
        
        for mirror in self.MIRRORS:
            try:
                url = f"{mirror}/q.php?q={quote_plus(query)}&cat={cat_num}"
                res = _http_get_json(url)
                
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
        self.enabled = ADDON.getSetting('enable_rarbg') != 'false'
        self.token = None
    
    def _get_token(self):
        """Get API token"""
        try:
            url = f"{self.API_URL}?get_token=get_token&app_id=PLANET"
            res = _http_get_json(url)
            if res:
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
            url = f"{self.API_URL}?mode=search&search_string={quote_plus(query)}&category=movies;tv&token={self.token}&format=json_extended&app_id=PLANET"
            res = _http_get_json(url)
            
            if res:
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
        self.enabled = ADDON.getSetting('enable_torrentgalaxy') != 'false'
    
    def search(self, query):
        if not self.enabled:
            return []
        
        results = []
        try:
            url = f"{self.BASE_URL}/torrents.php?search={quote_plus(query)}&sort=seeders&order=desc"
            html = _http_get(url)
            
            if html:
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


class L337xScraper:
    """1337x torrent scraper"""
    
    # Multiple mirrors for redundancy
    MIRRORS = [
        "https://1337x.to",
        "https://www.1337x.tw",
        "https://1337x.st",
        "https://x1337x.ws",
        "https://x1337x.eu",
        "https://x1337x.se",
        "https://1337x.unblockit.kim",
        "https://1337x.gd"
    ]
    
    def __init__(self):
        self.enabled = ADDON.getSetting('enable_1337x') != 'false'
    
    def search(self, query):
        """Search 1337x for torrents"""
        if not self.enabled:
            return []
        
        results = []
        
        for mirror in self.MIRRORS:
            try:
                # 1337x search URL format
                search_url = f"{mirror}/search/{quote_plus(query)}/1/"
                html = _http_get(search_url, timeout=15)
                
                if not html:
                    continue
                
                # Parse search results - get torrent page links
                # Pattern: /torrent/123456/torrent-name/
                torrent_links = re.findall(r'href="(/torrent/\d+/[^"]+)"', html)
                
                # Also try to extract seeds from search results
                # Pattern: <td class="coll-2 seeds">123</td>
                seeds_matches = re.findall(r'class="coll-2 seeds">(\d+)</td>', html)
                
                # Pattern for names from search results
                name_matches = re.findall(r'class="coll-1 name"[^>]*>.*?<a href="/torrent/[^"]+">([^<]+)</a>', html, re.DOTALL)
                
                if not torrent_links:
                    xbmc.log(f"1337x: No results from {mirror}", xbmc.LOGDEBUG)
                    continue
                
                xbmc.log(f"1337x: Found {len(torrent_links)} results from {mirror}", xbmc.LOGINFO)
                
                # Limit to first 15 results to avoid too many requests
                for i, link in enumerate(torrent_links[:15]):
                    try:
                        # Get the torrent page to extract magnet link
                        torrent_url = f"{mirror}{link}"
                        torrent_html = _http_get(torrent_url, timeout=10)
                        
                        if not torrent_html:
                            continue
                        
                        # Extract magnet link
                        magnet_match = re.search(r'href="(magnet:\?xt=urn:btih:[^"]+)"', torrent_html)
                        if not magnet_match:
                            continue
                        
                        magnet = magnet_match.group(1)
                        
                        # Extract title from page
                        title_match = re.search(r'<title>([^<]+)', torrent_html)
                        if title_match:
                            title = title_match.group(1).replace(' | 1337x', '').replace('Download ', '').strip()
                        elif i < len(name_matches):
                            title = name_matches[i].strip()
                        else:
                            title = link.split('/')[-2].replace('-', ' ')
                        
                        # Get seeds
                        seeds = 0
                        if i < len(seeds_matches):
                            try:
                                seeds = int(seeds_matches[i])
                            except:
                                pass
                        
                        # Also try to get seeds from torrent page
                        if seeds == 0:
                            seeds_page_match = re.search(r'Seeders.*?<span[^>]*>(\d+)</span>', torrent_html, re.DOTALL)
                            if seeds_page_match:
                                try:
                                    seeds = int(seeds_page_match.group(1))
                                except:
                                    pass
                        
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
                    break  # Success, no need to try other mirrors
                    
            except Exception as e:
                xbmc.log(f"1337x mirror {mirror} failed: {str(e)}", xbmc.LOGWARNING)
                continue
        
        return results


class TorrentioScraper:
    """Torrentio (Stremio-style public community API) scraper.

    Docs: https://torrentio.strem.fun/
    Endpoint pattern:
        /stream/movie/{imdb_id}.json
        /stream/series/{imdb_id}:{season}:{episode}.json
    """

    BASE_URL = "https://torrentio.strem.fun"

    def __init__(self):
        self.enabled = ADDON.getSetting('enable_torrentio') != 'false'

    def _parse_stream(self, stream):
        """Convert a Torrentio stream record into a standard result dict."""
        title = stream.get('title', '') or stream.get('name', '')
        info_hash = stream.get('infoHash', '') or stream.get('info_hash', '')
        if not info_hash:
            return None

        # Title often contains filename with quality info
        quality = detect_quality(title)

        # Extract seeders if present in title like "<U+1F464> 123" (Torrentio bust icon)
        seeds = 0
        m = re.search(u'\\b([0-9]+)\\b\\s*\U0001F464', title)
        if m:
            try:
                seeds = int(m.group(1))
            except ValueError:
                pass

        # Name of provider (shown by Torrentio)
        provider = stream.get('name', '').split('\n')[0].strip() or 'Torrentio'

        # Build magnet link
        trackers = [
            "udp://tracker.opentrackr.org:1337/announce",
            "udp://open.stealth.si:80/announce",
            "udp://tracker.torrent.eu.org:451/announce",
            "udp://tracker.bittor.pw:1337/announce",
        ]
        tr_query = '&'.join(f'tr={quote_plus(t)}' for t in trackers)
        magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={quote_plus(title.split(chr(10))[0])}&{tr_query}"

        return {
            'title': title.replace('\n', ' | '),
            'magnet': magnet,
            'seeds': seeds,
            'quality': quality,
            'source': f'Torrentio/{provider}',
        }

    def search_imdb(self, imdb_id, content='movie', season=None, episode=None):
        """Primary search method using IMDB id (preferred by Torrentio)."""
        if not self.enabled or not imdb_id:
            return []
        if not imdb_id.startswith('tt'):
            imdb_id = f'tt{imdb_id}'

        if content == 'movie':
            url = f"{self.BASE_URL}/stream/movie/{imdb_id}.json"
        else:
            if season is None or episode is None:
                return []
            url = f"{self.BASE_URL}/stream/series/{imdb_id}:{season}:{episode}.json"

        data = _http_get_json(url, timeout=15)
        if not data or 'streams' not in data:
            return []

        results = []
        for stream in data.get('streams', [])[:40]:
            r = self._parse_stream(stream)
            if r:
                results.append(r)
        return results

    def search(self, query):
        """Torrentio requires IMDB id - this text search fallback returns nothing."""
        return []


def _is_tv_match(title, season, episode):
    """Return True if a torrent title matches the requested season+episode
    (single episode OR a valid season pack / complete series pack).

    Accepts patterns like:
        S01E01, s01.e01, s01 e01, 1x01, Season 1 Episode 1
        Season 1, S01 (pack), Complete Series / Complete Season
    """
    if not title:
        return False
    t = title.lower()

    try:
        s = int(season)
        e = int(episode)
    except (TypeError, ValueError):
        return True  # Can't validate - keep it

    # Exact episode patterns
    ep_patterns = [
        rf's0*{s}\s*[\.\-_ ]?\s*e0*{e}\b',
        rf's0*{s}e0*{e}\b',
        rf'\b{s}\s*x\s*0*{e}\b',
        rf'season[\s\.\-_]*0*{s}[\s\.\-_]*episode[\s\.\-_]*0*{e}\b',
    ]
    for pat in ep_patterns:
        if re.search(pat, t):
            return True

    # Season-pack / complete-series patterns (no episode marker in title)
    has_episode_marker = re.search(r's\d{1,2}\s*[\.\-_ ]?\s*e\d{1,3}|\d{1,2}x\d{1,3}|episode\s*\d+', t)
    if not has_episode_marker:
        # If the title mentions an explicit season number, it must match.
        season_nums = [int(n) for n in re.findall(r's(\d{1,2})(?!\d)', t)]
        season_nums += [int(n) for n in re.findall(r'season[\s\.\-_]*(\d{1,2})', t)]
        season_nums += [int(n) for n in re.findall(r'(\d{1,2})(?:st|nd|rd|th)[\s\.\-_]*season', t)]
        if season_nums:
            return s in season_nums
        # No explicit season -> accept only complete-series packs
        if re.search(r'\bcomplete[\s\.\-_]*(series|collection|seasons?)\b', t) or \
           re.search(r'\bseasons?\b[\s\.\-_]*\bcomplete\b', t) or \
           re.search(r'\ball[\s\.\-_]*seasons?\b', t):
            return True

    return False


def search_all(query, preferred_quality='1080p', imdb_id=None, content='movie', season=None, episode=None):
    """Search all enabled scrapers and return sorted results.

    If imdb_id is provided, Torrentio (IMDB based) is used as the primary source.
    Pirate Bay / 1337x / TorrentGalaxy / RARBG are used by text query.

    For TV content, text-scraper results are filtered to only keep torrents
    that match the requested season+episode (or a valid season/complete pack).
    """
    all_results = []
    is_tv = content and str(content).lower() != 'movie'

    torrentio_hashes = set()
    if imdb_id:
        try:
            torrentio_results = TorrentioScraper().search_imdb(imdb_id, content, season, episode)
            all_results.extend(torrentio_results)
            for r in torrentio_results:
                h = extract_hash(r.get('magnet', ''))
                if h:
                    torrentio_hashes.add(h)
        except Exception as e:
            xbmc.log(f"Torrentio failed: {str(e)}", xbmc.LOGWARNING)

    scrapers = [
        PirateBayScraper(),
        Rarbg(),
        TorrentGalaxy(),
        L337xScraper()
    ]

    text_results = []
    for scraper in scrapers:
        try:
            results = scraper.search(query)
            text_results.extend(results)
        except Exception as e:
            xbmc.log(f"Scraper failed: {str(e)}", xbmc.LOGWARNING)

    # For TV, filter text-scraper results by season+episode (Torrentio is
    # already IMDB+S+E accurate and is kept as-is).
    if is_tv and season is not None and episode is not None:
        filtered = []
        for r in text_results:
            h = extract_hash(r.get('magnet', ''))
            if h and h in torrentio_hashes:
                continue  # Already have it from Torrentio
            if _is_tv_match(r.get('title', ''), season, episode):
                filtered.append(r)
            else:
                xbmc.log(
                    f"PLANETSCRAPERS: skip wrong-episode torrent: {r.get('title', '')[:80]}",
                    xbmc.LOGDEBUG,
                )
        text_results = filtered

    all_results.extend(text_results)

    # Deduplicate by info hash
    seen = set()
    unique = []
    for r in all_results:
        h = extract_hash(r.get('magnet', ''))
        if h and h in seen:
            continue
        if h:
            seen.add(h)
        unique.append(r)

    # Sort by quality with fallback
    return sort_by_quality(unique, preferred_quality)
