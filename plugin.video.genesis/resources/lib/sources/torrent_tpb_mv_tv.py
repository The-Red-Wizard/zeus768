# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    Torrent scraper for ThePirateBay
'''

import re
import urllib
import urlparse

from resources.lib.libraries import cleantitle
from resources.lib.libraries import client
from resources.lib.libraries import control


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['thepiratebay.org', 'thepiratebay10.org', 'piratebay.live']
        self.base_link = 'https://apibay.org'
        self.search_link = '/q.php?q=%s&cat=0'
        self.min_seeders = 1

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            return

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
            url = urlparse.parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urllib.urlencode(url)
            return url
        except:
            return

    def get_movie(self, imdb, title, year):
        try:
            query = '%s %s' % (title, year)
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            url = self.base_link + self.search_link % urllib.quote_plus(query)
            return url
        except:
            return

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
            data = urlparse.parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            tvshowtitle = data['tvshowtitle']
            query = '%s S%02dE%02d' % (tvshowtitle, int(season), int(episode))
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            url = self.base_link + self.search_link % urllib.quote_plus(query)
            return url
        except:
            return

    def get_sources(self, url, hostDict, hostprDict, locDict):
        sources = []
        try:
            if url is None: return sources

            import json
            result = client.request(url, timeout=10)
            if result is None: return sources

            try:
                torrents = json.loads(result)
            except:
                return sources

            if not isinstance(torrents, list):
                return sources

            for torrent in torrents:
                try:
                    name = torrent.get('name', '')
                    if not name or name == 'No results returned':
                        continue

                    info_hash = torrent.get('info_hash', '')
                    if not info_hash:
                        continue

                    seeds = int(torrent.get('seeders', 0))
                    if seeds < self.min_seeders:
                        continue

                    size = int(torrent.get('size', 0))
                    size = self._format_size(size)

                    # Create magnet link
                    magnet = 'magnet:?xt=urn:btih:%s&dn=%s' % (info_hash, urllib.quote_plus(name))
                    magnet += '&tr=udp://tracker.opentrackr.org:1337/announce'
                    magnet += '&tr=udp://tracker.openbittorrent.com:6969/announce'
                    magnet += '&tr=udp://open.stealth.si:80/announce'
                    magnet += '&tr=udp://tracker.torrent.eu.org:451/announce'

                    quality = self._get_quality(name)

                    info = '%s | %s Seeds' % (size, seeds)

                    sources.append({
                        'source': 'TPB',
                        'quality': quality,
                        'language': 'en',
                        'url': magnet,
                        'info': info,
                        'direct': False,
                        'debridonly': True,
                        'provider': 'thepiratebay'
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
