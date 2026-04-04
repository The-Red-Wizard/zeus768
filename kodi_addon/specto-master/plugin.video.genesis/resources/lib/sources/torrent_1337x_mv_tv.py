# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    Torrent scraper for 1337x
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
        self.domains = ['1337x.to', '1337x.st', '1337x.ws', '1337x.eu', '1337x.se']
        self.base_link = 'https://1337x.to'
        self.search_link = '/search/%s/1/'
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

            result = client.request(url, timeout=10)
            if result is None: return sources

            rows = client.parseDOM(result, 'tr')
            
            for row in rows:
                try:
                    # Get torrent name and link
                    name = client.parseDOM(row, 'a', ret='href')
                    name = [i for i in name if '/torrent/' in i]
                    if not name: continue
                    name = name[0]
                    
                    # Get seeders
                    seeds = client.parseDOM(row, 'td', attrs={'class': 'seeds'})
                    if not seeds: continue
                    seeds = int(re.sub('[^0-9]', '', seeds[0]))
                    if seeds < self.min_seeders: continue

                    # Get size
                    size = client.parseDOM(row, 'td', attrs={'class': 'size'})
                    size = size[0] if size else '0'
                    size = re.sub('<[^>]*>', '', size)

                    # Determine quality
                    quality = self._get_quality(name)

                    # Get torrent page for magnet
                    torrent_page = self.base_link + name
                    torrent_result = client.request(torrent_page, timeout=10)
                    if torrent_result is None: continue

                    magnet = re.findall('href="(magnet:[^"]+)"', torrent_result)
                    if not magnet: continue
                    magnet = magnet[0]

                    info = '%s | %s Seeds' % (size, seeds)

                    sources.append({
                        'source': '1337x',
                        'quality': quality,
                        'language': 'en',
                        'url': magnet,
                        'info': info,
                        'direct': False,
                        'debridonly': True,
                        'provider': '1337x'
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

    def resolve(self, url):
        return url
