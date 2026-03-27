"""
SALTS Scrapers - SolarMovie Scraper (Modernized)
Original by tknorris, Updated by zeus768 for Kodi 21+
"""
import re
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from salts_lib import log_utils

QUALITY_MAP = {'HD': '720p', 'DVD': 'SD', 'TV': 'SD', 'LQ DVD': 'SD', 'CAM': 'CAM'}

class SolarMovieScraper(BaseScraper):
    """SolarMovie streaming site scraper"""
    
    BASE_URL = 'https://solarmovie.pe'
    NAME = 'SolarMovie'
    
    # Mirror sites
    MIRRORS = [
        'https://solarmovie.pe',
        'https://solarmovie.to',
        'https://solarmovies.win',
        'https://solarmoviefree.net'
    ]
    
    def __init__(self, timeout=30):
        super().__init__(timeout)
        self._find_working_domain()
    
    def _find_working_domain(self):
        """Find a working mirror"""
        for mirror in self.MIRRORS:
            try:
                response = self.session.get(mirror, timeout=5)
                if response.status_code == 200:
                    self.BASE_URL = mirror
                    return
            except:
                continue
    
    def search(self, query, media_type='movie'):
        """Search SolarMovie"""
        results = []
        
        try:
            if media_type == 'movie':
                is_series = 1
            else:
                is_series = 2
            
            search_url = f'{self.BASE_URL}/movie/search/{quote_plus(query)}'
            
            html = self._http_get(search_url, cache_limit=1)
            if not html:
                return results
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find results
            for item in soup.select('.ml-item, .film-poster, .movie-item'):
                try:
                    link = item.select_one('a')
                    if not link:
                        continue
                    
                    title_el = item.select_one('.mli-info h2, .film-name, .title')
                    title = title_el.get_text(strip=True) if title_el else ''
                    
                    if not title:
                        title = link.get('title', link.get_text(strip=True))
                    
                    # Extract year
                    year_match = re.search(r'\((\d{4})\)', title)
                    year = year_match.group(1) if year_match else ''
                    title = re.sub(r'\s*\(\d{4}\)\s*', '', title)
                    
                    url = link.get('href', '')
                    
                    # Skip episodes in movie search
                    if media_type == 'movie' and re.search(r'/season-\d+/episode-\d+', url):
                        continue
                    
                    results.append({
                        'title': title,
                        'year': year,
                        'url': url,
                        'quality': 'HD',
                        'host': 'SolarMovie'
                    })
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            log_utils.log_error(f'SolarMovie: Search error: {e}')
        
        return results
    
    def get_sources(self, url):
        """Get sources from a SolarMovie page"""
        sources = []
        
        try:
            full_url = urljoin(self.BASE_URL, url)
            html = self._http_get(full_url, cache_limit=0.5)
            
            if not html:
                return sources
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find server links
            for row in soup.select('#link_ tr, .server-item, [data-video]'):
                try:
                    # Try data attribute first
                    video_url = row.get('data-video', '')
                    
                    if not video_url:
                        link = row.select_one('a')
                        if link:
                            video_url = link.get('href', '')
                    
                    if not video_url:
                        continue
                    
                    # Get host
                    host_el = row.select_one('.host, .server-name')
                    host = host_el.get_text(strip=True) if host_el else urlparse(video_url).netloc
                    
                    # Get quality
                    quality = 'SD'
                    quality_el = row.select_one('.quality, .qualityCell')
                    if quality_el:
                        q_text = quality_el.get_text(strip=True)
                        quality = QUALITY_MAP.get(q_text.upper(), 'SD')
                    
                    sources.append({
                        'url': video_url,
                        'host': host,
                        'quality': quality,
                        'direct': False
                    })
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            log_utils.log_error(f'SolarMovie: Get sources error: {e}')
        
        return sources
