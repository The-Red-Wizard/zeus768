"""
SALTS Scrapers - International Sites
Russian, Chinese, Korean, and more international sources
By zeus768 for Kodi 21+
"""
import re
import json
from urllib.parse import urljoin, quote_plus, quote
from bs4 import BeautifulSoup

from .base_scraper import TorrentScraper, BaseScraper
from salts_lib import log_utils


class RuTorScraper(TorrentScraper):
    """RuTor - Russian torrent site"""
    
    BASE_URL = 'https://rutor.info'
    NAME = 'RuTor'
    
    def search(self, query, media_type='movie'):
        results = []
        try:
            search_url = f'{self.BASE_URL}/search/0/0/010/0/{quote_plus(query)}'
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            for row in soup.select('tr.gai, tr.tum')[:30]:
                try:
                    links = row.select('a')
                    title = ''
                    magnet = ''
                    
                    for link in links:
                        href = link.get('href', '')
                        if href.startswith('magnet:'):
                            magnet = href
                        elif '/torrent/' in href:
                            title = link.get_text(strip=True)
                    
                    if not title or not magnet:
                        continue
                    
                    cells = row.select('td')
                    size = cells[-2].get_text(strip=True) if len(cells) > 2 else 'Unknown'
                    
                    seed_match = re.search(r'(\d+)', cells[-1].get_text() if cells else '')
                    seeds = int(seed_match.group(1)) if seed_match else 0
                    
                    results.append({
                        'title': title,
                        'magnet': magnet,
                        'quality': self._parse_quality(title),
                        'size': size,
                        'seeds': seeds,
                        'host': 'RuTor'
                    })
                except:
                    continue
        except Exception as e:
            log_utils.log_error(f'RuTor error: {e}')
        return results


class NNMClubScraper(TorrentScraper):
    """NNM-Club - Russian torrent tracker"""
    
    BASE_URL = 'https://nnmclub.to'
    NAME = 'NNM-Club'
    
    def search(self, query, media_type='movie'):
        results = []
        try:
            search_url = f'{self.BASE_URL}/forum/tracker.php?nm={quote(query)}'
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            for row in soup.select('tr.prow1, tr.prow2')[:30]:
                try:
                    title_link = row.select_one('a.genmed')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    
                    magnet_link = row.select_one('a[href^="magnet:"]')
                    if magnet_link:
                        magnet = magnet_link['href']
                    else:
                        # Try to get from download link
                        dl_link = row.select_one('a.genmed[href*="download"]')
                        if dl_link:
                            topic_match = re.search(r't=(\d+)', title_link.get('href', ''))
                            if topic_match:
                                magnet = self._get_magnet_from_page(topic_match.group(1))
                            else:
                                continue
                        else:
                            continue
                    
                    if not magnet:
                        continue
                    
                    size_el = row.select_one('td.gensmall u')
                    size = size_el.get_text(strip=True) if size_el else 'Unknown'
                    
                    seed_el = row.select_one('b.seedmed')
                    seeds = int(seed_el.get_text(strip=True)) if seed_el else 0
                    
                    results.append({
                        'title': title,
                        'magnet': magnet,
                        'quality': self._parse_quality(title),
                        'size': size,
                        'seeds': seeds,
                        'host': 'NNM-Club'
                    })
                except:
                    continue
        except Exception as e:
            log_utils.log_error(f'NNM-Club error: {e}')
        return results
    
    def _get_magnet_from_page(self, topic_id):
        try:
            url = f'{self.BASE_URL}/forum/viewtopic.php?t={topic_id}'
            html = self._http_get(url, cache_limit=24)
            match = re.search(r'magnet:\?[^"\'<>\s]+', html)
            return match.group(0) if match else None
        except:
            return None


class DyTTScraper(BaseScraper):
    """DyTT - Chinese movie site (电影天堂)"""
    
    BASE_URL = 'https://www.dytt8.net'
    NAME = 'DyTT'
    
    def search(self, query, media_type='movie'):
        results = []
        try:
            search_url = f'{self.BASE_URL}/e/search/index.php'
            data = {
                'keyboard': query,
                'show': 'title',
                'tempid': '1'
            }
            html = self._http_get(search_url, data=data, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.select('div.co_content8 a')[:20]:
                try:
                    title = item.get_text(strip=True)
                    if not title:
                        continue
                    
                    detail_url = urljoin(self.BASE_URL, item.get('href', ''))
                    
                    # Get magnet from detail page
                    magnet = self._get_magnet_from_page(detail_url)
                    if not magnet:
                        continue
                    
                    results.append({
                        'title': title,
                        'url': detail_url,
                        'magnet': magnet,
                        'quality': self._parse_quality(title),
                        'size': 'Unknown',
                        'seeds': 0,
                        'host': 'DyTT'
                    })
                except:
                    continue
        except Exception as e:
            log_utils.log_error(f'DyTT error: {e}')
        return results
    
    def _get_magnet_from_page(self, url):
        try:
            html = self._http_get(url, cache_limit=24)
            # Look for magnet links or ed2k links
            match = re.search(r'magnet:\?[^"\'<>\s]+', html)
            if match:
                return match.group(0)
            # Try to find thunder/ed2k links
            match = re.search(r'thunder://[^"\'<>\s]+', html)
            return match.group(0) if match else None
        except:
            return None


class BTBTTScraper(TorrentScraper):
    """BTBTT - Chinese BT site"""
    
    BASE_URL = 'https://www.btbtt15.com'
    NAME = 'BTBTT'
    
    def search(self, query, media_type='movie'):
        results = []
        try:
            search_url = f'{self.BASE_URL}/search-index-keyword-{quote(query)}.htm'
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.select('div.search-item')[:30]:
                try:
                    title_link = item.select_one('a.subject-link')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    detail_url = urljoin(self.BASE_URL, title_link.get('href', ''))
                    
                    # Get magnet from detail
                    magnet = self._get_magnet_from_page(detail_url)
                    if not magnet:
                        continue
                    
                    results.append({
                        'title': title,
                        'magnet': magnet,
                        'quality': self._parse_quality(title),
                        'size': 'Unknown',
                        'seeds': 0,
                        'host': 'BTBTT'
                    })
                except:
                    continue
        except Exception as e:
            log_utils.log_error(f'BTBTT error: {e}')
        return results
    
    def _get_magnet_from_page(self, url):
        try:
            html = self._http_get(url, cache_limit=24)
            match = re.search(r'magnet:\?[^"\'<>\s]+', html)
            return match.group(0) if match else None
        except:
            return None


class SubsPleaseScaper(TorrentScraper):
    """SubsPlease - Anime releases"""
    
    BASE_URL = 'https://subsplease.org'
    NAME = 'SubsPlease'
    
    def search(self, query, media_type='movie'):
        results = []
        try:
            # API endpoint
            api_url = f'{self.BASE_URL}/api/?f=search&tz=UTC&s={quote_plus(query)}'
            html = self._http_get(api_url, cache_limit=1)
            if not html:
                return results
            
            data = json.loads(html)
            
            for key, item in data.items():
                if key == 'page':
                    continue
                try:
                    title = item.get('show', '')
                    downloads = item.get('downloads', [])
                    
                    for dl in downloads:
                        res = dl.get('res', '')
                        magnet = dl.get('magnet', '')
                        
                        if not magnet:
                            continue
                        
                        full_title = f'{title} [{res}]'
                        
                        results.append({
                            'title': full_title,
                            'magnet': magnet,
                            'quality': res,
                            'size': 'Unknown',
                            'seeds': 0,
                            'host': 'SubsPlease'
                        })
                except:
                    continue
        except Exception as e:
            log_utils.log_error(f'SubsPlease error: {e}')
        return results


class TokyoToshoScraper(TorrentScraper):
    """TokyoTosho - Anime torrent aggregator"""
    
    BASE_URL = 'https://www.tokyotosho.info'
    NAME = 'TokyoTosho'
    
    def search(self, query, media_type='movie'):
        results = []
        try:
            search_url = f'{self.BASE_URL}/search.php?terms={quote_plus(query)}&type=1'
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            for row in soup.select('tr.category_0, tr.category_1')[:30]:
                try:
                    title_cell = row.select_one('td.desc-top')
                    if not title_cell:
                        continue
                    
                    title_link = title_cell.select_one('a')
                    title = title_link.get_text(strip=True) if title_link else ''
                    
                    magnet_link = row.select_one('a[href^="magnet:"]')
                    if not magnet_link:
                        continue
                    
                    magnet = magnet_link['href']
                    
                    size_el = row.select_one('td.desc-bot')
                    size_match = re.search(r'Size:\s*([\d.]+\s*\w+)', size_el.get_text() if size_el else '')
                    size = size_match.group(1) if size_match else 'Unknown'
                    
                    seed_match = re.search(r'S:\s*(\d+)', size_el.get_text() if size_el else '')
                    seeds = int(seed_match.group(1)) if seed_match else 0
                    
                    results.append({
                        'title': title,
                        'magnet': magnet,
                        'quality': self._parse_quality(title),
                        'size': size,
                        'seeds': seeds,
                        'host': 'TokyoTosho'
                    })
                except:
                    continue
        except Exception as e:
            log_utils.log_error(f'TokyoTosho error: {e}')
        return results


class AnimeToshoScraper(TorrentScraper):
    """AnimeTosho - Anime releases with NyaaSi mirrors"""
    
    BASE_URL = 'https://animetosho.org'
    NAME = 'AnimeTosho'
    
    def search(self, query, media_type='movie'):
        results = []
        try:
            search_url = f'{self.BASE_URL}/search?q={quote_plus(query)}'
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.select('div.home_list_entry')[:30]:
                try:
                    title_link = item.select_one('div.link a')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    
                    magnet_link = item.select_one('a[href^="magnet:"]')
                    if not magnet_link:
                        continue
                    
                    magnet = magnet_link['href']
                    
                    size_el = item.select_one('div.size')
                    size = size_el.get_text(strip=True) if size_el else 'Unknown'
                    
                    results.append({
                        'title': title,
                        'magnet': magnet,
                        'quality': self._parse_quality(title),
                        'size': size,
                        'seeds': 0,
                        'host': 'AnimeTosho'
                    })
                except:
                    continue
        except Exception as e:
            log_utils.log_error(f'AnimeTosho error: {e}')
        return results


class AniDexScraper(TorrentScraper):
    """AniDex - Anime torrent site"""
    
    BASE_URL = 'https://anidex.info'
    NAME = 'AniDex'
    
    def search(self, query, media_type='movie'):
        results = []
        try:
            search_url = f'{self.BASE_URL}/?q={quote_plus(query)}'
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            for row in soup.select('div.torrent')[:30]:
                try:
                    title_link = row.select_one('a.torrent-title')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    
                    magnet_link = row.select_one('a[href^="magnet:"]')
                    if not magnet_link:
                        continue
                    
                    magnet = magnet_link['href']
                    
                    size_el = row.select_one('td.text-center')
                    size = size_el.get_text(strip=True) if size_el else 'Unknown'
                    
                    seed_el = row.select_one('td.text-success')
                    seeds = int(seed_el.get_text(strip=True)) if seed_el else 0
                    
                    results.append({
                        'title': title,
                        'magnet': magnet,
                        'quality': self._parse_quality(title),
                        'size': size,
                        'seeds': seeds,
                        'host': 'AniDex'
                    })
                except:
                    continue
        except Exception as e:
            log_utils.log_error(f'AniDex error: {e}')
        return results
