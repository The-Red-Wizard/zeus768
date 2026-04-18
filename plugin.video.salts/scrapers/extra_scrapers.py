"""
SALTS Scrapers - Additional Torrent Sites
More sources for maximum coverage
By zeus768 for Kodi 21+
"""
import re
import json
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup

from .base_scraper import TorrentScraper
from salts_lib import log_utils


class KickassScraper(TorrentScraper):
 """Kickass Torrents scraper"""
 
 BASE_URL = 'https://kickasstorrents.to'
 NAME = 'Kickass'
 
 MIRRORS = [
 'https://kickasstorrents.to',
 'https://katcr.to',
 'https://kat.am',
 'https://thekickasstorrents.to'
 ]
 
 def __init__(self, timeout=30):
 super().__init__(timeout)
 self._find_working_domain()
 
 def _find_working_domain(self):
 for mirror in self.MIRRORS:
 try:
 response = self.session.get(mirror, timeout=5)
 if response.status_code == 200:
 self.BASE_URL = mirror
 return
 except:
 continue
 
 def search(self, query, media_type='movie'):
 results = []
 try:
 search_url = f'{self.BASE_URL}/usearch/{quote_plus(query)}/'
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 for row in soup.select('tr.odd, tr.even')[:30]:
 try:
 title_link = row.select_one('a.cellMainLink')
 if not title_link:
 continue
 
 title = title_link.get_text(strip=True)
 magnet_link = row.select_one('a[href^="magnet:"]')
 if not magnet_link:
 continue
 
 magnet = magnet_link['href']
 size_cell = row.select_one('td.nobr')
 size = size_cell.get_text(strip=True) if size_cell else 'Unknown'
 
 seeds = 0
 seed_cell = row.select_one('td.green')
 if seed_cell:
 seeds = int(seed_cell.get_text(strip=True).replace(',', ''))
 
 results.append({
 'title': title,
 'magnet': magnet,
 'quality': self._parse_quality(title),
 'size': size,
 'seeds': seeds,
 'host': 'Kickass'
 })
 except:
 continue
 except Exception as e:
 log_utils.log_error(f'Kickass error: {e}')
 return results


class RuTrackerScraper(TorrentScraper):
 """RuTracker - Russian torrent site"""
 
 BASE_URL = 'https://rutracker.org'
 NAME = 'RuTracker'
 
 def search(self, query, media_type='movie'):
 results = []
 try:
 search_url = f'{self.BASE_URL}/forum/tracker.php?nm={quote_plus(query)}'
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 for row in soup.select('tr.tCenter.hl-tr')[:30]:
 try:
 title_link = row.select_one('a.tLink')
 if not title_link:
 continue
 
 title = title_link.get_text(strip=True)
 
 # Get topic ID for magnet
 topic_id = re.search(r't=(\d+)', title_link.get('href', ''))
 if topic_id:
 info_hash = self._get_hash_from_topic(topic_id.group(1))
 if info_hash:
 magnet = self._make_magnet(info_hash, title)
 else:
 continue
 else:
 continue
 
 size_cell = row.select_one('td.tor-size')
 size = size_cell.get_text(strip=True) if size_cell else 'Unknown'
 
 seed_cell = row.select_one('td.seedmed')
 seeds = int(seed_cell.get_text(strip=True)) if seed_cell else 0
 
 results.append({
 'title': title,
 'magnet': magnet,
 'quality': self._parse_quality(title),
 'size': size,
 'seeds': seeds,
 'host': 'RuTracker'
 })
 except:
 continue
 except Exception as e:
 log_utils.log_error(f'RuTracker error: {e}')
 return results
 
 def _get_hash_from_topic(self, topic_id):
 try:
 url = f'{self.BASE_URL}/forum/viewtopic.php?t={topic_id}'
 html = self._http_get(url, cache_limit=24)
 match = re.search(r'magnet:\?xt=urn:btih:([a-fA-F0-9]{40})', html)
 return match.group(1) if match else None
 except:
 return None


class BTDiggScraper(TorrentScraper):
 """BTDigg - DHT search engine"""
 
 BASE_URL = 'https://btdig.com'
 NAME = 'BTDigg'
 
 def search(self, query, media_type='movie'):
 results = []
 try:
 search_url = f'{self.BASE_URL}/search?q={quote_plus(query)}'
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 for item in soup.select('div.one_result')[:30]:
 try:
 title_link = item.select_one('div.torrent_name a')
 if not title_link:
 continue
 
 title = title_link.get_text(strip=True)
 
 magnet_link = item.select_one('a[href^="magnet:"]')
 if not magnet_link:
 continue
 
 magnet = magnet_link['href']
 
 size_el = item.select_one('span.torrent_size')
 size = size_el.get_text(strip=True) if size_el else 'Unknown'
 
 results.append({
 'title': title,
 'magnet': magnet,
 'quality': self._parse_quality(title),
 'size': size,
 'seeds': 0,
 'host': 'BTDigg'
 })
 except:
 continue
 except Exception as e:
 log_utils.log_error(f'BTDigg error: {e}')
 return results


class ZooqleScraper(TorrentScraper):
 """Zooqle torrent scraper"""
 
 BASE_URL = 'https://zooqle.com'
 NAME = 'Zooqle'
 
 def search(self, query, media_type='movie'):
 results = []
 try:
 search_url = f'{self.BASE_URL}/search?q={quote_plus(query)}'
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 for row in soup.select('tr')[:30]:
 try:
 title_link = row.select_one('a.small')
 if not title_link:
 continue
 
 title = title_link.get_text(strip=True)
 
 magnet_link = row.select_one('a[href^="magnet:"]')
 if not magnet_link:
 continue
 
 magnet = magnet_link['href']
 
 size_el = row.select_one('td.prog')
 size = size_el.get('title', 'Unknown') if size_el else 'Unknown'
 
 seed_el = row.select_one('div.progress-bar.green')
 seeds = int(seed_el.get('title', '0').split()[0]) if seed_el else 0
 
 results.append({
 'title': title,
 'magnet': magnet,
 'quality': self._parse_quality(title),
 'size': size,
 'seeds': seeds,
 'host': 'Zooqle'
 })
 except:
 continue
 except Exception as e:
 log_utils.log_error(f'Zooqle error: {e}')
 return results


class MagnetDLScraper(TorrentScraper):
 """MagnetDL torrent scraper"""
 
 BASE_URL = 'https://www.magnetdl.com'
 NAME = 'MagnetDL'
 
 def search(self, query, media_type='movie'):
 results = []
 try:
 # MagnetDL uses first letter of query
 first_letter = query[0].lower() if query else 'a'
 search_url = f'{self.BASE_URL}/{first_letter}/{quote_plus(query)}/'
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 for row in soup.select('tr')[:30]:
 try:
 title_cell = row.select_one('td.n')
 if not title_cell:
 continue
 
 title_link = title_cell.select_one('a')
 title = title_link.get_text(strip=True) if title_link else ''
 
 magnet_link = row.select_one('a[href^="magnet:"]')
 if not magnet_link:
 continue
 
 magnet = magnet_link['href']
 
 cells = row.select('td')
 size = cells[5].get_text(strip=True) if len(cells) > 5 else 'Unknown'
 seeds = int(cells[6].get_text(strip=True)) if len(cells) > 6 else 0
 
 results.append({
 'title': title,
 'magnet': magnet,
 'quality': self._parse_quality(title),
 'size': size,
 'seeds': seeds,
 'host': 'MagnetDL'
 })
 except:
 continue
 except Exception as e:
 log_utils.log_error(f'MagnetDL error: {e}')
 return results


class GlodLSScraper(TorrentScraper):
 """GLODLS torrent scraper"""
 
 BASE_URL = 'https://glodls.to'
 NAME = 'GLODLS'
 
 def search(self, query, media_type='movie'):
 results = []
 try:
 search_url = f'{self.BASE_URL}/search_results.php?search={quote_plus(query)}'
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 for row in soup.select('tr.t-row')[:30]:
 try:
 title_link = row.select_one('a.title')
 if not title_link:
 continue
 
 title = title_link.get_text(strip=True)
 
 magnet_link = row.select_one('a[href^="magnet:"]')
 if not magnet_link:
 continue
 
 magnet = magnet_link['href']
 
 cells = row.select('td')
 size = cells[4].get_text(strip=True) if len(cells) > 4 else 'Unknown'
 seeds = int(cells[5].get_text(strip=True)) if len(cells) > 5 else 0
 
 results.append({
 'title': title,
 'magnet': magnet,
 'quality': self._parse_quality(title),
 'size': size,
 'seeds': seeds,
 'host': 'GLODLS'
 })
 except:
 continue
 except Exception as e:
 log_utils.log_error(f'GLODLS error: {e}')
 return results


class iDopeScraper(TorrentScraper):
 """iDope torrent scraper"""
 
 BASE_URL = 'https://idope.se'
 NAME = 'iDope'
 
 def search(self, query, media_type='movie'):
 results = []
 try:
 search_url = f'{self.BASE_URL}/torrent-list/{quote_plus(query)}/'
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 for item in soup.select('div.resultdiv')[:30]:
 try:
 title_link = item.select_one('div.resultdivtopname')
 if not title_link:
 continue
 
 title = title_link.get_text(strip=True)
 
 # Get info hash from data attribute or link
 hash_el = item.select_one('a[href*="/torrent/"]')
 if hash_el:
 href = hash_el.get('href', '')
 match = re.search(r'/torrent/([a-fA-F0-9]+)/', href)
 if match:
 info_hash = match.group(1)
 magnet = self._make_magnet(info_hash, title)
 else:
 continue
 else:
 continue
 
 size_el = item.select_one('div.resultdivbottonlength')
 size = size_el.get_text(strip=True) if size_el else 'Unknown'
 
 seed_el = item.select_one('div.resultdivbottonseed')
 seeds = int(seed_el.get_text(strip=True).replace(',', '')) if seed_el else 0
 
 results.append({
 'title': title,
 'magnet': magnet,
 'quality': self._parse_quality(title),
 'size': size,
 'seeds': seeds,
 'host': 'iDope'
 })
 except:
 continue
 except Exception as e:
 log_utils.log_error(f'iDope error: {e}')
 return results


class SolidTorrentsScraper(TorrentScraper):
 """SolidTorrents scraper"""
 
 BASE_URL = 'https://solidtorrents.to'
 NAME = 'SolidTorrents'
 
 def search(self, query, media_type='movie'):
 results = []
 try:
 # API endpoint
 api_url = f'{self.BASE_URL}/api/v1/search?q={quote_plus(query)}'
 html = self._http_get(api_url, cache_limit=1)
 if not html:
 return results
 
 data = json.loads(html)
 
 for item in data.get('results', [])[:30]:
 try:
 title = item.get('title', '')
 info_hash = item.get('infohash', '')
 
 if not info_hash:
 continue
 
 magnet = self._make_magnet(info_hash, title)
 size = item.get('size', 'Unknown')
 if isinstance(size, int):
 size = self._format_size(size)
 
 seeds = item.get('seeders', 0)
 
 results.append({
 'title': title,
 'magnet': magnet,
 'quality': self._parse_quality(title),
 'size': size,
 'seeds': seeds,
 'host': 'SolidTorrents'
 })
 except:
 continue
 except Exception as e:
 log_utils.log_error(f'SolidTorrents error: {e}')
 return results
 
 def _format_size(self, bytes_size):
 for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
 if bytes_size < 1024:
 return f'{bytes_size:.1f} {unit}'
 bytes_size /= 1024
 return f'{bytes_size:.1f} PB'


class TorrentDownloadScraper(TorrentScraper):
 """TorrentDownload scraper"""
 
 BASE_URL = 'https://www.torrentdownload.info'
 NAME = 'TorrentDownload'
 
 def search(self, query, media_type='movie'):
 results = []
 try:
 search_url = f'{self.BASE_URL}/search?q={quote_plus(query)}'
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 for row in soup.select('tr')[:30]:
 try:
 title_link = row.select_one('a[href*="/torrent/"]')
 if not title_link:
 continue
 
 title = title_link.get_text(strip=True)
 
 # Get hash from detail page link
 href = title_link.get('href', '')
 match = re.search(r'/([a-fA-F0-9]{40})\.html', href)
 if match:
 info_hash = match.group(1)
 magnet = self._make_magnet(info_hash, title)
 else:
 continue
 
 cells = row.select('td')
 size = cells[2].get_text(strip=True) if len(cells) > 2 else 'Unknown'
 seeds = int(cells[3].get_text(strip=True)) if len(cells) > 3 else 0
 
 results.append({
 'title': title,
 'magnet': magnet,
 'quality': self._parse_quality(title),
 'size': size,
 'seeds': seeds,
 'host': 'TorrentDownload'
 })
 except:
 continue
 except Exception as e:
 log_utils.log_error(f'TorrentDownload error: {e}')
 return results


class TorrentProjectScraper(TorrentScraper):
 """TorrentProject scraper"""
 
 BASE_URL = 'https://torrentproject.cc'
 NAME = 'TorrentProject'
 
 def search(self, query, media_type='movie'):
 results = []
 try:
 search_url = f'{self.BASE_URL}/?s={quote_plus(query)}'
 html = self._http_get(search_url, cache_limit=1)
 if not html:
 return results
 
 soup = BeautifulSoup(html, 'html.parser')
 for item in soup.select('div.torrent')[:30]:
 try:
 title_link = item.select_one('a')
 if not title_link:
 continue
 
 title = title_link.get_text(strip=True)
 
 # Get hash from link
 href = title_link.get('href', '')
 match = re.search(r'/([a-fA-F0-9]{40})/', href)
 if match:
 info_hash = match.group(1)
 magnet = self._make_magnet(info_hash, title)
 else:
 continue
 
 size_el = item.select_one('span.size')
 size = size_el.get_text(strip=True) if size_el else 'Unknown'
 
 seed_el = item.select_one('span.seed')
 seeds = int(seed_el.get_text(strip=True)) if seed_el else 0
 
 results.append({
 'title': title,
 'magnet': magnet,
 'quality': self._parse_quality(title),
 'size': size,
 'seeds': seeds,
 'host': 'TorrentProject'
 })
 except:
 continue
 except Exception as e:
 log_utils.log_error(f'TorrentProject error: {e}')
 return results
