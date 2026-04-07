# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    Torz scraper for movies and TV shows (torrent aggregator)
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
        self.domains = ['torz.in', 'torz.to', 'torznab.to']
        self.base_link = 'https://torz.in'
        self.search_link = '/api/torrents?search=%s&sort=seeders&order=desc'
        self.min_seeders = 2

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
                response = json.loads(result)
                items = response.get('torrents', response.get('results', response.get('data', [])))
            except:
                return sources

            if not items or not isinstance(items, list):
                return sources

            for item in items[:25]:
                try:
                    name = item.get('name', item.get('title', ''))
                    magnet = item.get('magnet', item.get('magnet_uri', ''))
                    size = item.get('size', item.get('size_bytes', 0))
                    seeders = item.get('seeders', item.get('seed', 0))

                    if not magnet:
                        info_hash = item.get('hash', item.get('info_hash', ''))
                        if info_hash:
                            magnet = 'magnet:?xt=urn:btih:%s&dn=%s' % (info_hash, quote_plus(name))

                    if not magnet:
                        continue

                    if int(seeders) < self.min_seeders:
                        continue

                    quality = self._get_quality(name)
                    info = '%s | %s Seeds' % (self._format_size(size), seeders)

                    sources.append({
                        'source': 'Torz',
                        'quality': quality,
                        'language': 'en',
                        'url': magnet,
                        'info': info,
                        'direct': False,
                        'debridonly': True,
                        'provider': 'Torz'
                    })

                except:
                    pass

            return sources
        except:
            return sources

    def _get_quality(self, name):
        name = name.lower()
        if any(i in name for i in ['2160p', '4k', 'uhd', 'hdr']):
            return '4K'
        elif any(i in name for i in ['1080p', 'fullhd', 'full hd', 'fhd']):
            return '1080p'
        elif any(i in name for i in ['720p', 'hd', 'brrip', 'bdrip']):
            return 'HD'
        elif any(i in name for i in ['480p', 'dvdrip', 'dvd', 'sd']):
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
            elif size >= 1024:
                return '%.2f KB' % (size / 1024.0)
            else:
                return '%d B' % size
        except:
            return str(size) if size else 'N/A'

    def resolve(self, url):
        return url
