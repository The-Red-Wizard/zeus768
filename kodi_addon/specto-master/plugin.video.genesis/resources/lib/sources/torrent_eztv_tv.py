# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    Torrent scraper for EZTV - TV Shows only
'''

import re
import urllib
import json

from resources.lib.libraries import cleantitle
from resources.lib.libraries import client
from resources.lib.libraries import control


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['eztv.re', 'eztv.wf', 'eztv.tf']
        self.base_link = 'https://eztv.re'
        self.api_link = '/api/get-torrents?imdb_id=%s'
        self.search_link = '/api/get-torrents?search=%s&limit=50'
        self.min_seeders = 1

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None: return
            url_data = dict(urlparse.parse_qsl(url))
            url_data['title'] = title
            url_data['premiered'] = premiered
            url_data['season'] = season
            url_data['episode'] = episode
            return urllib.urlencode(url_data)
        except:
            return

    def get_movie(self, imdb, title, year):
        # EZTV is TV shows only
        return None

    def get_show(self, imdb, tvdb, tvshowtitle, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            return

    def get_episode(self, url, imdb, tvdb, title, date, season, episode):
        try:
            if url is None: return
            import urlparse
            data = urlparse.parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            
            imdb_id = data.get('imdb', imdb)
            if imdb_id.startswith('tt'):
                imdb_id = imdb_id[2:]
            
            tvshowtitle = data.get('tvshowtitle', '')
            
            # Store episode info
            result_url = {
                'imdb': imdb_id,
                'tvshowtitle': tvshowtitle,
                'season': season,
                'episode': episode
            }
            return urllib.urlencode(result_url)
        except:
            return

    def get_sources(self, url, hostDict, hostprDict, locDict):
        sources = []
        try:
            if url is None: return sources
            
            import urlparse
            data = urlparse.parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            
            imdb_id = data.get('imdb', '')
            season = data.get('season', '')
            episode = data.get('episode', '')
            tvshowtitle = data.get('tvshowtitle', '')

            # Try IMDB-based search first
            if imdb_id:
                api_url = self.base_link + self.api_link % imdb_id
            else:
                # Fallback to title search
                query = '%s S%02dE%02d' % (tvshowtitle, int(season), int(episode))
                api_url = self.base_link + self.search_link % urllib.quote_plus(query)

            result = client.request(api_url, timeout=10)
            if result is None: return sources

            data = json.loads(result)
            torrents = data.get('torrents', [])
            
            # Filter for specific episode
            season_str = 'S%02d' % int(season)
            episode_str = 'E%02d' % int(episode)
            
            for torrent in torrents:
                try:
                    title = torrent.get('title', '')
                    
                    # Check if this is the right episode
                    if season_str.lower() not in title.lower():
                        continue
                    if episode_str.lower() not in title.lower():
                        continue
                    
                    magnet = torrent.get('magnet_url', '')
                    if not magnet: continue
                    
                    seeds = torrent.get('seeds', 0)
                    if seeds < self.min_seeders: continue
                    
                    size = torrent.get('size_bytes', 0)
                    size = self._format_size(size)
                    
                    quality = self._get_quality(title)
                    
                    info = '%s | %s Seeds' % (size, seeds)

                    sources.append({
                        'source': 'EZTV',
                        'quality': quality,
                        'language': 'en',
                        'url': magnet,
                        'info': info,
                        'direct': False,
                        'debridonly': True,
                        'provider': 'eztv'
                    })

                except:
                    pass

            return sources
        except:
            return sources

    def _get_quality(self, name):
        name = name.lower()
        if any(i in name for i in ['2160p', '4k', 'uhd']):
            return '4K'
        elif '1080p' in name:
            return '1080p'
        elif '720p' in name:
            return 'HD'
        else:
            return 'SD'

    def _format_size(self, size_bytes):
        try:
            size_bytes = int(size_bytes)
            if size_bytes >= 1073741824:
                return '%.2f GB' % (size_bytes / 1073741824.0)
            elif size_bytes >= 1048576:
                return '%.2f MB' % (size_bytes / 1048576.0)
            else:
                return '%.2f KB' % (size_bytes / 1024.0)
        except:
            return '0'

    def resolve(self, url):
        return url
