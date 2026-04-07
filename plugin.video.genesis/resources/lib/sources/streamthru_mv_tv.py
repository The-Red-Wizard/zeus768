# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    Streamthru scraper for movies and TV shows
'''

import re
import json

try:
    from urllib import quote_plus, urlencode
    from urlparse import urlparse, parse_qs
except ImportError:
    from urllib.parse import quote_plus, urlencode, urlparse, parse_qs

from resources.lib.libraries import cleantitle
from resources.lib.libraries import client
from resources.lib.libraries import control


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['streamthru.org', 'streamthru.to']
        self.base_link = 'https://streamthru.org'
        self.search_link = '/api/v1/search?q=%s'
        self.stream_link = '/api/v1/stream/%s'
        self.min_seeders = 1

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None: return
            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            return

    def get_sources(self, url, hostDict, hostprDict, locDict):
        sources = []
        try:
            if url is None: return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            if 'tvshowtitle' in data:
                query = '%s S%02dE%02d' % (data['tvshowtitle'], int(data['season']), int(data['episode']))
            else:
                query = '%s %s' % (data['title'], data['year'])

            query = re.sub(r'[\\|/| -|:|;|\*|\?|"|<|>|\|]', ' ', query)
            search_url = self.base_link + self.search_link % quote_plus(query)

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }

            result = client.request(search_url, headers=headers, timeout=10)
            if result is None: return sources

            try:
                items = json.loads(result)
                if isinstance(items, dict):
                    items = items.get('results', items.get('data', []))
            except:
                return sources

            if not items or not isinstance(items, list):
                return sources

            for item in items[:20]:
                try:
                    name = item.get('title', item.get('name', ''))
                    stream_id = item.get('id', item.get('stream_id', ''))
                    size = item.get('size', item.get('file_size', '0'))
                    quality_tag = item.get('quality', '')

                    quality = self._get_quality(name + ' ' + quality_tag)
                    
                    stream_url = self.base_link + self.stream_link % stream_id

                    info = self._format_size(size) if size else ''

                    sources.append({
                        'source': 'Streamthru',
                        'quality': quality,
                        'language': 'en',
                        'url': stream_url,
                        'info': info,
                        'direct': True,
                        'debridonly': False,
                        'provider': 'Streamthru'
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
        elif '480p' in name or 'dvd' in name:
            return 'SD'
        else:
            return 'SD'

    def _format_size(self, size):
        try:
            size = int(size)
            if size >= 1073741824:
                return '%.2f GB' % (size / 1073741824.0)
            elif size >= 1048576:
                return '%.2f MB' % (size / 1048576.0)
            else:
                return '%d B' % size
        except:
            return str(size) if size else ''

    def resolve(self, url):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            result = client.request(url, headers=headers, timeout=10)
            if result is None:
                return url
            
            data = json.loads(result)
            return data.get('url', data.get('stream_url', data.get('link', url)))
        except:
            return url
