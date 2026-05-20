"""
Torrent Scrapers Module for Genesis
10 Unique Torrent Sites (not Stremio/Torrentio)
Uses native urllib (no external requests module)

v1.6 Improvements:
- Parallel scraping across all sites (ThreadPoolExecutor)
- Parallel per-torrent page fetching for 1337x
- Per-site timeout & global timeout
- Dead torrent filtering (skip results with seeds==0 when seeds is reliably reported)
- Deduplication by info hash across sites
- min_seeds + filter_dead user settings
"""
import json
import re
import xbmc
import xbmcaddon
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus, urlencode
import ssl
import concurrent.futures

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

# Sites that reliably report seed counts. For these, seeds==0 means a dead torrent
# and we can safely filter it out. Other sites default seeds to 0 even when alive,
# so we must NOT filter those out by seed count.
# Note: Torrentio/Comet often omit seeds from the description even when the
# torrent is fine on debrid, so they are deliberately excluded here.
RELIABLE_SEED_SOURCES = {'1337x', 'PirateBay', 'YTS', 'EZTV', 'Nyaa', 'Magnetdl', 'SolidTorrents'}

# Create SSL context that doesn't verify certificates (for sites with SSL issues)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


def _setting_bool(key, default=True):
    try:
        val = ADDON.getSetting(key)
        if val == '':
            return default
        return val == 'true'
    except Exception:
        return default


def _setting_int(key, default):
    try:
        val = ADDON.getSetting(key)
        if val == '':
            return default
        return int(val)
    except Exception:
        return default


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


def _http_get(url, headers=None, timeout=10):
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
        xbmc.log(f'Scraper URL Error: {e.reason}', xbmc.LOGDEBUG)
        return None
    except Exception as e:
        xbmc.log(f'Scraper Request Error: {e}', xbmc.LOGDEBUG)
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

    def _fetch_torrent_page(self, mirror, link, seeds):
        """Fetch a single torrent detail page and return parsed result."""
        try:
            torrent_url = f"{mirror}{link}"
            torrent_html = _http_get(torrent_url, timeout=6)
            if not torrent_html:
                return None
            magnet_match = re.search(r'href="(magnet:\?xt=urn:btih:[^"]+)"', torrent_html)
            if not magnet_match:
                return None
            magnet = magnet_match.group(1)
            title_match = re.search(r'<title>([^<]+)', torrent_html)
            if title_match:
                title = title_match.group(1).replace(' | 1337x', '').replace('Download ', '').strip()
            else:
                title = link.split('/')[-2].replace('-', ' ')
            return {
                'title': title,
                'magnet': magnet,
                'seeds': seeds,
                'quality': detect_quality(title),
                'source': '1337x'
            }
        except Exception as e:
            xbmc.log(f"1337x: Error parsing torrent page: {e}", xbmc.LOGDEBUG)
            return None

    def search(self, query):
        if not self.enabled:
            return []

        for mirror in self.MIRRORS:
            try:
                search_url = f"{mirror}/search/{quote_plus(query)}/1/"
                html = _http_get(search_url, timeout=8)
                if not html:
                    continue

                torrent_links = re.findall(r'href="(/torrent/\d+/[^"]+)"', html)
                seeds_matches = re.findall(r'class="coll-2 seeds">(\d+)</td>', html)
                if not torrent_links:
                    continue

                # Limit and de-dup links from listing
                seen = set()
                pairs = []
                for i, link in enumerate(torrent_links):
                    if link in seen:
                        continue
                    seen.add(link)
                    seeds = int(seeds_matches[i]) if i < len(seeds_matches) else 0
                    pairs.append((link, seeds))
                    if len(pairs) >= 10:
                        break

                results = []
                # Fetch detail pages in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                    futures = [ex.submit(self._fetch_torrent_page, mirror, link, seeds)
                               for link, seeds in pairs]
                    for fut in concurrent.futures.as_completed(futures, timeout=15):
                        try:
                            r = fut.result()
                            if r:
                                results.append(r)
                        except Exception:
                            continue

                if results:
                    xbmc.log(f"1337x: Found {len(results)} results from {mirror}", xbmc.LOGINFO)
                    return results
            except Exception as e:
                xbmc.log(f"1337x mirror {mirror} failed: {str(e)}", xbmc.LOGWARNING)
                continue

        return []


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
                res = _http_get_json(url, timeout=8)

                if res and isinstance(res, list) and len(res) > 0 and res[0].get('id') != '0':
                    for item in res[:25]:
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
                data = _http_get_json(url, timeout=8)
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
                html = _http_get(url, timeout=8)
                if html:
                    magnets = re.findall(r'href="(magnet:\?xt=urn:btih:[^"]+)"', html)
                    titles = re.findall(r'class="epinfo">([^<]+)</a>', html)
                    seeds_list = re.findall(r'forum_thread_post_end[^>]*>(\d+)</td>', html)
                    if not magnets:
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
                html = _http_get(url, timeout=8)
                if html:
                    magnets = re.findall(r'href="(magnet:\?[^"]+)"', html)
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
                html = _http_get(url, timeout=8)
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
                html = _http_get(url, timeout=8)
                if html:
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
                first_letter = query[0].lower() if query else 'a'
                if not first_letter.isalpha():
                    first_letter = '0'
                search_query = query.replace(' ', '-').lower()
                url = f"{mirror}/{first_letter}/{search_query}/"
                html = _http_get(url, timeout=8)
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
                data = _http_get_json(url, timeout=8)
                if data and data.get('results'):
                    for item in data['results'][:20]:
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
# SCRAPER 11: Torrentio (Stremio addon)
# ══════════════════════════════════════════════════════════════════════════════

class TorrentioScraper:
    """Torrentio Stremio addon - needs IMDb id for best results.

    Endpoint:
      Movies : {base}/stream/movie/{imdb_id}.json
      Series : {base}/stream/series/{imdb_id}:{season}:{episode}.json

    The base URL can be customised in settings - users can paste their own
    configured Torrentio URL (e.g. one bound to their Real-Debrid token), which
    is the preferred way to bypass Cloudflare challenges on the public host.

    v1.7.7: Mirrors / headers / parsing aligned with script.module.salts_scrapers
    so Comet & Torrentio behave identically across both addon stacks.
    """

    DEFAULT_MIRRORS = [
        "https://torrentio.strem.fun",
        # Salts-style fallbacks (in order) for when the primary 403s or rate-
        # limits behind Cloudflare.
        "https://torrentio.strem.fun/sort=qualitysize",
        "https://knightcrawler.elfhosted.com",
    ]

    def __init__(self):
        self.enabled = ADDON.getSetting('enable_torrentio') == 'true'
        # User-customisable base URL. Accept either a bare host or a full
        # /configure URL (we strip the trailing /configure or /manifest.json).
        custom = (ADDON.getSetting('torrentio_url') or '').strip()
        custom = _normalize_stremio_base(custom)
        mirrors = []
        if custom:
            mirrors.append(custom)
        for m in self.DEFAULT_MIRRORS:
            if m not in mirrors:
                mirrors.append(m)
        self.mirrors = mirrors

    def search(self, query, imdb_id='', media_type='movie', season=None, episode=None):
        if not self.enabled:
            return []
        if not imdb_id or not imdb_id.startswith('tt'):
            # Torrentio is metadata-driven, free-text search won't work here
            xbmc.log('Torrentio: skipping, no IMDb id provided', xbmc.LOGINFO)
            return []

        path = _stremio_stream_path(imdb_id, media_type, season, episode)
        return _stremio_fetch(self.mirrors, path, source_name='Torrentio')


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER 12: Comet (Stremio addon - comet.feels.legal)
# ══════════════════════════════════════════════════════════════════════════════

class CometScraper:
    """Comet Stremio addon - needs IMDb id for best results.

    Endpoint:
      Movies : {base}/stream/movie/{imdb_id}.json
      Series : {base}/stream/series/{imdb_id}:{season}:{episode}.json

    v1.7.7: Mirrors / headers / parsing aligned with script.module.salts_scrapers.
    """

    DEFAULT_MIRRORS = [
        "https://comet.feels.legal",
        # Salts-style fallbacks
        "https://comet.elfhosted.com",
        "https://comet-cf.elfhosted.com",
        "https://comet.fast-stream.com",
    ]

    def __init__(self):
        self.enabled = ADDON.getSetting('enable_comet') == 'true'
        custom = (ADDON.getSetting('comet_url') or '').strip()
        custom = _normalize_stremio_base(custom)
        mirrors = []
        if custom:
            mirrors.append(custom)
        for m in self.DEFAULT_MIRRORS:
            if m not in mirrors:
                mirrors.append(m)
        self.mirrors = mirrors

    def search(self, query, imdb_id='', media_type='movie', season=None, episode=None):
        if not self.enabled:
            return []
        if not imdb_id or not imdb_id.startswith('tt'):
            xbmc.log('Comet: skipping, no IMDb id provided', xbmc.LOGINFO)
            return []

        path = _stremio_stream_path(imdb_id, media_type, season, episode)
        return _stremio_fetch(self.mirrors, path, source_name='Comet')


# ── Stremio helpers ──────────────────────────────────────────────────────────

_SEEDS_RE = re.compile(r'(?:👤|seeders?\s*[:=]?\s*|seeds?\s*[:=]?\s*|\bS\s*[:=]?\s*)\s*(\d+)', re.IGNORECASE)
_SIZE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(TB|GB|MB)', re.IGNORECASE)


def _normalize_stremio_base(url):
    """Accept any Stremio addon URL the user pastes (configure / manifest /
    bare host) and return a clean base URL with no trailing slash.

    Examples:
      'https://torrentio.strem.fun/configure'                 -> '.../strem.fun'
      'https://torrentio.strem.fun/sort=quality/manifest.json' -> '.../sort=quality'
      'https://comet.feels.legal/'                             -> '.../feels.legal'
    """
    if not url:
        return ''
    u = url.strip().rstrip('/')
    # Strip trailing /configure, /manifest.json, /stream/...
    for tail in ('/configure', '/manifest.json'):
        if u.endswith(tail):
            u = u[: -len(tail)].rstrip('/')
    # If user pasted a full stream URL, lop everything from /stream onward
    idx = u.find('/stream/')
    if idx > 0:
        u = u[:idx]
    return u


def _stremio_stream_path(imdb_id, media_type, season, episode):
    if media_type == 'series' or (season is not None and episode is not None):
        s = str(season or 1)
        e = str(episode or 1)
        return f"/stream/series/{imdb_id}:{s}:{e}.json"
    return f"/stream/movie/{imdb_id}.json"


def _parse_seeds(text):
    if not text:
        return 0
    m = _SEEDS_RE.search(text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return 0
    return 0


def _parse_size_bytes(text):
    if not text:
        return 0
    m = _SIZE_RE.search(text)
    if not m:
        return 0
    try:
        val = float(m.group(1))
    except ValueError:
        return 0
    unit = m.group(2).upper()
    mult = {'MB': 1024 ** 2, 'GB': 1024 ** 3, 'TB': 1024 ** 4}.get(unit, 0)
    return int(val * mult)


def _stremio_fetch(mirrors, path, source_name):
    """Fetch a Stremio addon stream endpoint and normalise results.

    v1.7.7: Re-implemented to match the salts_scrapers v1.0.4 approach for
    Comet & Torrentio, which gives us:

      * Cloudflare-friendly browser headers (sec-ch-ua family).
      * Silent gzip decoding (some gateways ignore Accept-Encoding: identity).
      * `[Source Quality] Title` display formatting (the salts look).
      * `fileIdx` propagated into the magnet so debrids pick the right file
        on multi-episode packs.
      * Direct-URL streams kept alongside torrents (debrid-resolved links,
        free providers like CyberFlix etc.).
      * Iterating through every mirror until one returns >0 streams - never
        stopping early on an empty 200.
    """
    # Modern browser headers that bypass most Cloudflare WAF rules used by
    # elfhosted / strem.fun / *.strem.io. Mirrors what salts uses.
    stremio_headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36'),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'sec-ch-ua': ('"Chromium";v="120", "Google Chrome";v="120", '
                      '"Not?A_Brand";v="99"'),
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Referer': 'https://www.stremio.com/',
        'Origin': 'https://www.stremio.com',
    }

    last_err = None
    for base in mirrors:
        try:
            url = base.rstrip('/') + path
            xbmc.log(f'{source_name}: fetching {url}', xbmc.LOGINFO)
            data = _stremio_http_json(url, stremio_headers, timeout=15)
            if not data or not isinstance(data, dict):
                last_err = f'{base} returned empty/invalid body'
                xbmc.log(f'{source_name}: {last_err}', xbmc.LOGWARNING)
                continue
            streams = data.get('streams') or []
            if not streams:
                last_err = f'{base} returned 0 streams'
                xbmc.log(f'{source_name}: {last_err}', xbmc.LOGWARNING)
                continue

            results = []
            for s in streams:
                try:
                    parsed = _parse_stremio_stream(s, source_name)
                except Exception as e:
                    xbmc.log(f'{source_name}: stream parse error: {e}',
                             xbmc.LOGDEBUG)
                    continue
                if parsed:
                    results.append(parsed)

            if results:
                xbmc.log(f'{source_name}: Found {len(results)} results from {base}',
                         xbmc.LOGINFO)
                return results
        except Exception as e:
            last_err = f'{base}: {e}'
            xbmc.log(f'{source_name} mirror {last_err}', xbmc.LOGWARNING)
            continue
    if last_err:
        xbmc.log(f'{source_name}: all mirrors failed - last: {last_err}',
                 xbmc.LOGWARNING)
    return []


def _stremio_http_json(url, headers, timeout=15):
    """GET `url` and return parsed JSON. Transparently decodes gzip bodies
    (some Stremio gateways gzip even when Accept-Encoding wasn't requested)."""
    try:
        req = Request(url, headers=headers, method='GET')
        resp = urlopen(req, timeout=timeout, context=ssl_context)
        raw = resp.read()
        if raw[:2] == b'\x1f\x8b':
            import gzip
            raw = gzip.decompress(raw)
        return json.loads(raw.decode('utf-8', errors='replace'))
    except HTTPError as e:
        xbmc.log(f'Stremio HTTP {e.code} for {url}', xbmc.LOGWARNING)
        return None
    except (URLError, json.JSONDecodeError, Exception) as e:
        xbmc.log(f'Stremio fetch error for {url}: {e}', xbmc.LOGDEBUG)
        return None


def _parse_stremio_stream(s, source_name):
    """Convert a single Stremio stream object into the Genesis source dict.

    Mirrors salts_scrapers' `_parse_stremio_stream` so titles look identical:
    `[Torrentio 4K] Movie.2024.2160p.WEB-DL.x265`. Direct-URL streams are
    kept and flagged so the player can dispatch them straight to Kodi.
    """
    name = (s.get('name') or source_name or '').strip()
    desc = s.get('title') or s.get('description') or ''
    bh = s.get('behaviorHints') or {}
    filename = (bh.get('filename') or '').strip()

    info_hash = (s.get('infoHash') or '').lower()
    direct_url = (s.get('url') or '').strip()

    full_text = f'{name} {desc} {filename}'
    quality = detect_quality(full_text)

    seeds = _parse_seeds(desc) or _parse_seeds(name)
    size_bytes = bh.get('videoSize') or _parse_size_bytes(desc)

    # Salts-style display title: "[Torrentio 4K] filename or first desc line"
    clean_name = name.replace('\n', ' ').strip()
    if desc:
        clean_title = desc.split('\n', 1)[0].strip()
    else:
        clean_title = ''
    body = filename or clean_title or name.replace('\n', ' ')
    title_display = f'[{clean_name}] {body}' if clean_name else body
    title_display = title_display.strip() or filename or name or 'Unknown'

    base = {
        'title': title_display,
        'quality': quality,
        'source': source_name,
        'seeds': seeds,
        'size': size_bytes,
    }

    if info_hash:
        # Build magnet with the project's common trackers + any trackers the
        # Stremio addon advertised in `sources[]` (salts behaviour).
        magnet = _build_magnet(info_hash, filename or clean_title or info_hash)
        for src in (s.get('sources') or []):
            if isinstance(src, str) and src.startswith('tracker:'):
                magnet += f"&tr={quote_plus(src[len('tracker:'):])}"

        # Propagate fileIdx so debrids pick the right episode in packs.
        file_idx = s.get('fileIdx')
        if file_idx is not None:
            magnet += f'&fileIndex={file_idx}'

        if not seeds:
            base['seeds'] = 1  # at least one peer assumed for torrent rows

        base.update({
            'magnet': magnet,
            'hash': info_hash,
            'direct': False,
        })
        return base

    if direct_url:
        # Direct stream (debrid-resolved or free provider)
        base.update({
            'url': direct_url,
            'direct': True,
            'seeds': base['seeds'] or 9999,
        })
        return base

    return None


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
                html = _http_get(url, timeout=8)
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

def _dedupe_and_filter(results, min_seeds, filter_dead):
    """Deduplicate by info hash and apply dead-torrent filter.

    Dead-torrent filter only applies when the source reliably reports seeds.
    For sites that always return seeds=0 (LimeTorrents, TorrentGalaxy, BitSearch),
    we never drop them by seed count.
    """
    seen = {}
    for r in results:
        h = extract_hash(r.get('magnet', ''))
        if not h:
            # Keep entries without a hash if they look usable
            seen[id(r)] = r
            continue
        r['hash'] = h
        existing = seen.get(h)
        if existing is None:
            seen[h] = r
        else:
            # Prefer the entry with more seed info / higher seeds
            if r.get('seeds', 0) > existing.get('seeds', 0):
                seen[h] = r

    out = []
    for r in seen.values():
        src = r.get('source', '')
        seeds = r.get('seeds', 0) or 0
        if filter_dead and src in RELIABLE_SEED_SOURCES and seeds <= 0:
            continue
        if min_seeds > 0 and src in RELIABLE_SEED_SOURCES and seeds < min_seeds:
            continue
        out.append(r)
    return out


def _run_scraper(scraper, query, timeout, imdb_id='', media_type='movie', season=None, episode=None):
    """Run scraper.search with a per-site timeout via ThreadPoolExecutor."""
    name = scraper.__class__.__name__
    try:
        # Build call kwargs so legacy scrapers (search(query) only) still work
        def _call():
            try:
                return scraper.search(query, imdb_id=imdb_id, media_type=media_type,
                                      season=season, episode=episode)
            except TypeError:
                return scraper.search(query)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_call)
            try:
                return name, fut.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                xbmc.log(f"Scraper {name} timed out after {timeout}s", xbmc.LOGWARNING)
                return name, []
    except Exception as e:
        xbmc.log(f"Scraper {name} crashed: {e}", xbmc.LOGWARNING)
        return name, []


def search_all(query, preferred_quality='1080p', imdb_id='', media_type='movie',
               season=None, episode=None, progress_cb=None):
    """Search all enabled scrapers (in parallel) and return sorted, filtered results.

    Args:
        query: free-text search string
        preferred_quality: desired resolution ('2160p'/'1080p'/...)
        imdb_id: e.g. 'tt0111161' - required for Torrentio/Comet
        media_type: 'movie' or 'series'
        season, episode: ints for series
        progress_cb: callable(scraper_label, status, count, top_quality)
                     status in {'pending','running','done','failed'}
    """
    parallel = _setting_bool('scrape_parallel', True)
    per_site_timeout = _setting_int('scrape_timeout_per_site', 12)
    min_seeds = _setting_int('min_seeds', 0)
    filter_dead = _setting_bool('filter_dead', True)

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
        BitSearchScraper(),
        TorrentioScraper(),
        CometScraper(),
    ]
    enabled = [s for s in scrapers if getattr(s, 'enabled', True)]

    # Pretty labels for progress UI
    label_map = {
        'L337xScraper': '1337x',
        'PirateBayScraper': 'Pirate Bay',
        'YTSScraper': 'YTS',
        'EZTVScraper': 'EZTV',
        'LimeTorrentsScraper': 'LimeTorrents',
        'TorrentGalaxyScraper': 'TorrentGalaxy',
        'NyaaScraper': 'Nyaa',
        'MagnetdlScraper': 'Magnetdl',
        'SolidTorrentsScraper': 'SolidTorrents',
        'BitSearchScraper': 'BitSearch',
        'TorrentioScraper': 'Torrentio',
        'CometScraper': 'Comet',
    }

    def _emit(name, status, results=None):
        if not progress_cb:
            return
        label = label_map.get(name, name)
        count = len(results) if results else 0
        top_q = ''
        if results:
            # Pick the best resolution present
            for q in QUALITY_ORDER:
                if any(r.get('quality') == q for r in results):
                    top_q = q
                    break
        try:
            progress_cb(label, status, count, top_q)
        except Exception as e:
            xbmc.log(f'progress_cb error: {e}', xbmc.LOGDEBUG)

    # initial "pending" tiles so the UI can render immediately
    for s in enabled:
        _emit(s.__class__.__name__, 'pending', None)

    all_results = []
    if parallel and len(enabled) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(12, len(enabled))) as pool:
            futures = {}
            for s in enabled:
                _emit(s.__class__.__name__, 'running', None)
                f = pool.submit(_run_scraper, s, query, per_site_timeout,
                                imdb_id, media_type, season, episode)
                futures[f] = s
            try:
                for fut in concurrent.futures.as_completed(futures, timeout=per_site_timeout * 2 + 5):
                    try:
                        name, results = fut.result()
                        if results:
                            all_results.extend(results)
                            _emit(name, 'done', results)
                            xbmc.log(f"Scraper {name}: Found {len(results)} results", xbmc.LOGINFO)
                        else:
                            _emit(name, 'failed', None)
                    except Exception as e:
                        xbmc.log(f"Scraper future failed: {e}", xbmc.LOGWARNING)
            except concurrent.futures.TimeoutError:
                # Mark remaining as failed
                for fut, s in futures.items():
                    if not fut.done():
                        _emit(s.__class__.__name__, 'failed', None)
    else:
        for s in enabled:
            _emit(s.__class__.__name__, 'running', None)
            name, results = _run_scraper(s, query, per_site_timeout,
                                         imdb_id, media_type, season, episode)
            if results:
                all_results.extend(results)
                _emit(name, 'done', results)
            else:
                _emit(name, 'failed', None)

    xbmc.log(f"Total raw results: {len(all_results)}", xbmc.LOGINFO)
    filtered = _dedupe_and_filter(all_results, min_seeds, filter_dead)
    xbmc.log(f"After dedup/dead-filter: {len(filtered)} results (min_seeds={min_seeds}, filter_dead={filter_dead})", xbmc.LOGINFO)

    return sort_by_quality(filtered, preferred_quality)
