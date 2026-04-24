"""
SALTS Scrapers - Additional Torrent Scrapers
More torrent sites for maximum source coverage.
Added by zeus768 for SALTS 2.8
"""
import re
import json
import xbmc
import xbmcaddon
from urllib.request import urlopen, Request
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from .base_scraper import TorrentScraper
from salts_lib import log_utils

ADDON = xbmcaddon.Addon()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


# ==================== ADDITIONAL TORRENT SCRAPERS ====================

class BitSearchScraper(TorrentScraper):
    """BitSearch - Torrent meta search"""
    NAME = 'BitSearch'
    BASE_URL = 'https://bitsearch.to'
    
    def is_enabled(self):
        return ADDON.getSetting('bitsearch_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/search?q={quote_plus(query)}&category=1'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('.search-result .card')
            
            for item in items[:15]:
                try:
                    title_elem = item.select_one('.title a')
                    if not title_elem:
                        continue
                    
                    name = title_elem.get_text(strip=True)
                    link = item.select_one('a[href*="magnet:"]')
                    if not link:
                        continue
                    
                    magnet = link.get('href', '')
                    
                    size_elem = item.select_one('.stats span:nth-child(2)')
                    seeds_elem = item.select_one('.stats span:nth-child(1)')
                    
                    size = size_elem.get_text(strip=True) if size_elem else ''
                    seeds = int(re.sub(r'\D', '', seeds_elem.get_text())) if seeds_elem else 0
                    
                    info_hash = self._extract_hash(magnet)
                    
                    sources.append({
                        'scraper': self.NAME,
                        'name': name,
                        'quality': self._parse_quality(name),
                        'magnet': magnet,
                        'hash': info_hash,
                        'size': size,
                        'seeds': seeds,
                        'type': 'torrent'
                    })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class TorrentDownloads2Scraper(TorrentScraper):
    """TorrentDownloads - General torrents"""
    NAME = 'TorrentDownloads'
    BASE_URL = 'https://torrentdownloads.pro'
    
    def is_enabled(self):
        return ADDON.getSetting('torrentdownloads2_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/search/?search={quote_plus(query)}'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('.table2 tr')[1:16]  # Skip header
            
            for row in rows:
                try:
                    cols = row.select('td')
                    if len(cols) < 4:
                        continue
                    
                    name = cols[0].get_text(strip=True)
                    link = cols[0].select_one('a')
                    if not link:
                        continue
                    
                    detail_url = self.BASE_URL + link.get('href', '')
                    seeds = int(re.sub(r'\D', '', cols[3].get_text())) if cols[3] else 0
                    size = cols[2].get_text(strip=True) if cols[2] else ''
                    
                    # Get magnet from detail page
                    detail_html = self._http_get(detail_url)
                    if detail_html:
                        magnet_match = re.search(r'href="(magnet:\?[^"]+)"', detail_html)
                        if magnet_match:
                            magnet = magnet_match.group(1)
                            info_hash = self._extract_hash(magnet)
                            
                            sources.append({
                                'scraper': self.NAME,
                                'name': name,
                                'quality': self._parse_quality(name),
                                'magnet': magnet,
                                'hash': info_hash,
                                'size': size,
                                'seeds': seeds,
                                'type': 'torrent'
                            })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class TorLockScraper(TorrentScraper):
    """TorLock - Verified torrents"""
    NAME = 'TorLock'
    BASE_URL = 'https://www.torlock2.com'
    
    def is_enabled(self):
        return ADDON.getSetting('torlock_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            category = 'movies' if media_type == 'movie' else 'television'
            url = f'{self.BASE_URL}/{category}/torrents/{quote_plus(query)}.html'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('table tr')[1:16]
            
            for row in rows:
                try:
                    cols = row.select('td')
                    if len(cols) < 6:
                        continue
                    
                    link = cols[0].select_one('a')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    detail_url = self.BASE_URL + link.get('href', '')
                    size = cols[2].get_text(strip=True)
                    seeds = int(re.sub(r'\D', '', cols[3].get_text()))
                    
                    # Get torrent hash from detail page
                    detail_html = self._http_get(detail_url)
                    if detail_html:
                        hash_match = re.search(r'([a-fA-F0-9]{40})', detail_html)
                        if hash_match:
                            info_hash = hash_match.group(1).lower()
                            magnet = self._make_magnet(info_hash, name)
                            
                            sources.append({
                                'scraper': self.NAME,
                                'name': name,
                                'quality': self._parse_quality(name),
                                'magnet': magnet,
                                'hash': info_hash,
                                'size': size,
                                'seeds': seeds,
                                'type': 'torrent'
                            })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class TorrentFunkScraper(TorrentScraper):
    """TorrentFunk - Verified torrents"""
    NAME = 'TorrentFunk'
    BASE_URL = 'https://www.torrentfunk.com'
    
    def is_enabled(self):
        return ADDON.getSetting('torrentfunk_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/all/torrents/{quote_plus(query)}.html'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('.tmain tr')[1:16]
            
            for row in rows:
                try:
                    link = row.select_one('a.tlink')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    cols = row.select('td')
                    
                    size = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                    seeds = int(re.sub(r'\D', '', cols[2].get_text())) if len(cols) > 2 else 0
                    
                    detail_url = self.BASE_URL + link.get('href', '')
                    detail_html = self._http_get(detail_url)
                    
                    if detail_html:
                        magnet_match = re.search(r'href="(magnet:\?[^"]+)"', detail_html)
                        if magnet_match:
                            magnet = magnet_match.group(1)
                            info_hash = self._extract_hash(magnet)
                            
                            sources.append({
                                'scraper': self.NAME,
                                'name': name,
                                'quality': self._parse_quality(name),
                                'magnet': magnet,
                                'hash': info_hash,
                                'size': size,
                                'seeds': seeds,
                                'type': 'torrent'
                            })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class YourBittorrentScraper(TorrentScraper):
    """YourBittorrent - Torrent site"""
    NAME = 'YourBittorrent'
    BASE_URL = 'https://yourbittorrent.com'
    
    def is_enabled(self):
        return ADDON.getSetting('yourbittorrent_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/?q={quote_plus(query)}&category=movies'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('table tr')[1:16]
            
            for row in rows:
                try:
                    link = row.select_one('a.name')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    cols = row.select('td')
                    
                    size = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                    seeds = int(re.sub(r'\D', '', cols[2].get_text())) if len(cols) > 2 else 0
                    
                    magnet_link = row.select_one('a[href*="magnet:"]')
                    if magnet_link:
                        magnet = magnet_link.get('href', '')
                        info_hash = self._extract_hash(magnet)
                        
                        sources.append({
                            'scraper': self.NAME,
                            'name': name,
                            'quality': self._parse_quality(name),
                            'magnet': magnet,
                            'hash': info_hash,
                            'size': size,
                            'seeds': seeds,
                            'type': 'torrent'
                        })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class LeetXScraper(TorrentScraper):
    """LeetX - 1337x alternative"""
    NAME = 'LeetX'
    BASE_URL = 'https://www.1377x.to'
    
    def is_enabled(self):
        return ADDON.getSetting('leetx_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            category = 'Movies' if media_type == 'movie' else 'TV'
            url = f'{self.BASE_URL}/category-search/{quote_plus(query)}/{category}/1/'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('.table-list tbody tr')
            
            for row in rows[:15]:
                try:
                    cols = row.select('td')
                    if len(cols) < 5:
                        continue
                    
                    link = cols[0].select_one('.name a:nth-child(2)')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    detail_url = self.BASE_URL + link.get('href', '')
                    seeds = int(cols[1].get_text(strip=True))
                    size = cols[4].get_text(strip=True)
                    
                    detail_html = self._http_get(detail_url)
                    if detail_html:
                        magnet_match = re.search(r'href="(magnet:\?[^"]+)"', detail_html)
                        if magnet_match:
                            magnet = magnet_match.group(1)
                            info_hash = self._extract_hash(magnet)
                            
                            sources.append({
                                'scraper': self.NAME,
                                'name': name,
                                'quality': self._parse_quality(name),
                                'magnet': magnet,
                                'hash': info_hash,
                                'size': size,
                                'seeds': seeds,
                                'type': 'torrent'
                            })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class TorrentsCSVScraper(TorrentScraper):
    """Torrents.csv - Open database"""
    NAME = 'TorrentsCSV'
    BASE_URL = 'https://torrents-csv.com'
    
    def is_enabled(self):
        return ADDON.getSetting('torrentscsv_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/service/search?q={quote_plus(query)}&size=20'
            resp = self._http_get_json(url)
            
            if resp and isinstance(resp, list):
                for item in resp[:15]:
                    name = item.get('name', '')
                    info_hash = item.get('infohash', '')
                    size = item.get('size_bytes', 0)
                    seeds = item.get('seeders', 0)
                    
                    if info_hash:
                        magnet = self._make_magnet(info_hash, name)
                        
                        size_str = ''
                        if size > 1024**3:
                            size_str = f'{size / 1024**3:.2f} GB'
                        elif size > 1024**2:
                            size_str = f'{size / 1024**2:.2f} MB'
                        
                        sources.append({
                            'scraper': self.NAME,
                            'name': name,
                            'quality': self._parse_quality(name),
                            'magnet': magnet,
                            'hash': info_hash,
                            'size': size_str,
                            'seeds': seeds,
                            'type': 'torrent'
                        })
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class SolidTorrents2Scraper(TorrentScraper):
    """SolidTorrents - Quality torrents"""
    NAME = 'SolidTorrents2'
    BASE_URL = 'https://solidtorrents.to'
    
    def is_enabled(self):
        return ADDON.getSetting('solidtorrents2_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/search?q={quote_plus(query)}&category=video'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('.search-result')
            
            for item in items[:15]:
                try:
                    title_elem = item.select_one('.title a')
                    if not title_elem:
                        continue
                    
                    name = title_elem.get_text(strip=True)
                    
                    stats = item.select('.stats div')
                    size = stats[0].get_text(strip=True) if len(stats) > 0 else ''
                    seeds = int(re.sub(r'\D', '', stats[2].get_text())) if len(stats) > 2 else 0
                    
                    magnet_link = item.select_one('a[href*="magnet:"]')
                    if magnet_link:
                        magnet = magnet_link.get('href', '')
                        info_hash = self._extract_hash(magnet)
                        
                        sources.append({
                            'scraper': self.NAME,
                            'name': name,
                            'quality': self._parse_quality(name),
                            'magnet': magnet,
                            'hash': info_hash,
                            'size': size,
                            'seeds': seeds,
                            'type': 'torrent'
                        })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class AcgTorrentScraper(TorrentScraper):
    """AcgTorrent - Anime torrents"""
    NAME = 'AcgTorrent'
    BASE_URL = 'https://acgrip.com'
    
    def is_enabled(self):
        return ADDON.getSetting('acgtorrent_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/search.php?search={quote_plus(query)}'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('table tr')[1:15]
            
            for row in rows:
                try:
                    link = row.select_one('a.title')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    magnet_link = row.select_one('a[href*="magnet:"]')
                    
                    if magnet_link:
                        magnet = magnet_link.get('href', '')
                        info_hash = self._extract_hash(magnet)
                        
                        sources.append({
                            'scraper': self.NAME,
                            'name': name,
                            'quality': self._parse_quality(name),
                            'magnet': magnet,
                            'hash': info_hash,
                            'size': '',
                            'seeds': 0,
                            'type': 'torrent'
                        })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class Torrent9Scraper(TorrentScraper):
    """Torrent9 - French torrents"""
    NAME = 'Torrent9'
    BASE_URL = 'https://www.torrent9.fm'
    
    def is_enabled(self):
        return ADDON.getSetting('torrent9_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/recherche/{quote_plus(query)}'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('.table-responsive tr')
            
            for item in items[:15]:
                try:
                    link = item.select_one('a')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    detail_url = self.BASE_URL + link.get('href', '')
                    
                    cols = item.select('td')
                    size = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                    seeds = int(re.sub(r'\D', '', cols[2].get_text())) if len(cols) > 2 else 0
                    
                    detail_html = self._http_get(detail_url)
                    if detail_html:
                        magnet_match = re.search(r'href="(magnet:\?[^"]+)"', detail_html)
                        if magnet_match:
                            magnet = magnet_match.group(1)
                            info_hash = self._extract_hash(magnet)
                            
                            sources.append({
                                'scraper': self.NAME,
                                'name': name,
                                'quality': self._parse_quality(name),
                                'magnet': magnet,
                                'hash': info_hash,
                                'size': size,
                                'seeds': seeds,
                                'type': 'torrent'
                            })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class YggTorrentScraper(TorrentScraper):
    """YggTorrent - French torrents (public)"""
    NAME = 'YggTorrent'
    BASE_URL = 'https://www.ygg.re'
    
    def is_enabled(self):
        return ADDON.getSetting('yggtorrent_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/engine/search?name={quote_plus(query)}&do=search'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('.results tbody tr')
            
            for row in rows[:15]:
                try:
                    link = row.select_one('a.torrent-name')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    cols = row.select('td')
                    
                    size = cols[5].get_text(strip=True) if len(cols) > 5 else ''
                    seeds = int(cols[7].get_text(strip=True)) if len(cols) > 7 else 0
                    
                    # Get magnet/hash from detail page
                    detail_url = link.get('href', '')
                    if detail_url:
                        detail_html = self._http_get(detail_url)
                        if detail_html:
                            hash_match = re.search(r'([a-fA-F0-9]{40})', detail_html)
                            if hash_match:
                                info_hash = hash_match.group(1).lower()
                                magnet = self._make_magnet(info_hash, name)
                                
                                sources.append({
                                    'scraper': self.NAME,
                                    'name': name,
                                    'quality': self._parse_quality(name),
                                    'magnet': magnet,
                                    'hash': info_hash,
                                    'size': size,
                                    'seeds': seeds,
                                    'type': 'torrent'
                                })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class EtHDScraper(TorrentScraper):
    """EtHD - HD torrents"""
    NAME = 'EtHD'
    BASE_URL = 'https://ethd.com'
    
    def is_enabled(self):
        return ADDON.getSetting('ethd_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/torrents.php?search={quote_plus(query)}'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('.torrent_list tr')[1:15]
            
            for row in rows:
                try:
                    link = row.select_one('.torrent_name a')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    magnet_link = row.select_one('a[href*="magnet:"]')
                    
                    if magnet_link:
                        magnet = magnet_link.get('href', '')
                        info_hash = self._extract_hash(magnet)
                        
                        cols = row.select('td')
                        size = cols[3].get_text(strip=True) if len(cols) > 3 else ''
                        seeds = int(re.sub(r'\D', '', cols[4].get_text())) if len(cols) > 4 else 0
                        
                        sources.append({
                            'scraper': self.NAME,
                            'name': name,
                            'quality': self._parse_quality(name),
                            'magnet': magnet,
                            'hash': info_hash,
                            'size': size,
                            'seeds': seeds,
                            'type': 'torrent'
                        })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


class SkytorrentScraper(TorrentScraper):
    """SkyTorrent - General torrents"""
    NAME = 'SkyTorrent'
    BASE_URL = 'https://skytorrents.org'
    
    def is_enabled(self):
        return ADDON.getSetting('skytorrent_enabled') != 'false'
    
    def search(self, query, media_type='movie'):
        sources = []
        try:
            url = f'{self.BASE_URL}/?query={quote_plus(query)}'
            html = self._http_get(url)
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('.results tr')[1:15]
            
            for row in rows:
                try:
                    link = row.select_one('a.title')
                    if not link:
                        continue
                    
                    name = link.get_text(strip=True)
                    magnet_link = row.select_one('a[href*="magnet:"]')
                    
                    if magnet_link:
                        magnet = magnet_link.get('href', '')
                        info_hash = self._extract_hash(magnet)
                        
                        cols = row.select('td')
                        size = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                        seeds = int(re.sub(r'\D', '', cols[3].get_text())) if len(cols) > 3 else 0
                        
                        sources.append({
                            'scraper': self.NAME,
                            'name': name,
                            'quality': self._parse_quality(name),
                            'magnet': magnet,
                            'hash': info_hash,
                            'size': size,
                            'seeds': seeds,
                            'type': 'torrent'
                        })
                except Exception:
                    continue
        except Exception as e:
            log_utils.log_error(f'{self.NAME}: Error: {e}')
        return sources


# ==================== ALL ADDITIONAL TORRENT SCRAPERS ====================

ADDITIONAL_TORRENT_SCRAPERS = [
    BitSearchScraper,
    TorrentDownloads2Scraper,
    TorLockScraper,
    TorrentFunkScraper,
    YourBittorrentScraper,
    LeetXScraper,
    TorrentsCSVScraper,
    SolidTorrents2Scraper,
    AcgTorrentScraper,
    Torrent9Scraper,
    YggTorrentScraper,
    EtHDScraper,
    SkytorrentScraper,
]
