# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    Webstreamr scraper for movies and TV shows
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
        self.domains = ['webstreamr.com', 'webstreamr.io']
        self.base_link = 'https://webstreamr.com'
        self.search_link = '/api/search/%s'
        self.movie_link = '/api/movie/%s'
        self.tv_link = '/api/tv/%s/%s/%s'

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

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': self.base_link
            }

            if 'tvshowtitle' in data:
                # TV Show episode
                imdb = data.get('imdb', '')
                season = data.get('season', '1')
                episode = data.get('episode', '1')
                api_url = self.base_link + self.tv_link % (imdb, season, episode)
            else:
                # Movie
                imdb = data.get('imdb', '')
                api_url = self.base_link + self.movie_link % imdb

            result = client.request(api_url, headers=headers, timeout=10)
            if result is None:
                # Fallback to search
                query = data.get('tvshowtitle', data.get('title', ''))
                if 'tvshowtitle' in data:
                    query = '%s S%02dE%02d' % (query, int(data['season']), int(data['episode']))
                else:
                    query = '%s %s' % (query, data.get('year', ''))
                
                api_url = self.base_link + self.search_link % quote_plus(query)
                result = client.request(api_url, headers=headers, timeout=10)
                
            if result is None:
                return sources

            try:
                response = json.loads(result)
            except:
                return sources

            streams = response.get('streams', response.get('sources', response.get('results', [])))
            
            if isinstance(streams, dict):
                streams = [streams]
            
            if not streams:
                return sources

            for stream in streams[:15]:
                try:
                    stream_url = stream.get('url', stream.get('stream_url', stream.get('link', '')))
                    quality = stream.get('quality', stream.get('resolution', 'SD'))
                    source_name = stream.get('source', stream.get('host', 'Webstreamr'))
                    size = stream.get('size', '')

                    if not stream_url:
                        continue

                    quality = self._normalize_quality(quality)
                    info = self._format_size(size) if size else ''

                    sources.append({
                        'source': source_name if source_name else 'Webstreamr',
                        'quality': quality,
                        'language': 'en',
                        'url': stream_url,
                        'info': info,
                        'direct': self._is_direct(stream_url),
                        'debridonly': False,
                        'provider': 'Webstreamr'
                    })

                except:
                    pass

            return sources
        except:
            return sources

    def _normalize_quality(self, quality):
        quality = str(quality).lower()
        if any(i in quality for i in ['2160', '4k', 'uhd']):
            return '4K'
        elif any(i in quality for i in ['1080', 'fullhd', 'fhd']):
            return '1080p'
        elif any(i in quality for i in ['720', 'hd']):
            return 'HD'
        elif any(i in quality for i in ['480', '360', 'sd']):
            return 'SD'
        else:
            return 'SD'

    def _is_direct(self, url):
        direct_extensions = ['.mp4', '.mkv', '.avi', '.m3u8', '.ts']
        return any(url.lower().endswith(ext) or ext + '?' in url.lower() for ext in direct_extensions)

    def _format_size(self, size):
        try:
            if isinstance(size, str) and any(x in size.upper() for x in ['GB', 'MB', 'KB']):
                return size
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
            # Check if it's a direct link
            if self._is_direct(url):
                return url
            
            # Otherwise try to resolve through API
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            result = client.request(url, headers=headers, timeout=10)
            if result is None:
                return url
            
            try:
                data = json.loads(result)
                return data.get('url', data.get('stream_url', data.get('direct_url', url)))
            except:
                return url
        except:
            return url
