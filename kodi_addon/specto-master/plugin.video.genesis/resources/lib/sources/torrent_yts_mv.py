# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    Torrent scraper for YTS (YIFY Torrents) - Movies only
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
        self.domains = ['yts.mx', 'yts.lt', 'yts.am']
        self.base_link = 'https://yts.mx'
        self.api_link = '/api/v2/list_movies.json?query_term=%s'
        self.min_seeders = 1

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            return

    def get_movie(self, imdb, title, year):
        try:
            url = self.base_link + self.api_link % imdb
            return url
        except:
            return

    def get_show(self, imdb, tvdb, tvshowtitle, year):
        # YTS is movies only
        return None

    def get_episode(self, url, imdb, tvdb, title, date, season, episode):
        # YTS is movies only
        return None

    def get_sources(self, url, hostDict, hostprDict, locDict):
        sources = []
        try:
            if url is None: return sources

            result = client.request(url, timeout=10)
            if result is None: return sources

            data = json.loads(result)
            
            if data.get('status') != 'ok': return sources
            
            movies = data.get('data', {}).get('movies', [])
            
            for movie in movies:
                try:
                    title = movie.get('title', '')
                    torrents = movie.get('torrents', [])
                    
                    for torrent in torrents:
                        try:
                            quality = torrent.get('quality', 'SD')
                            size = torrent.get('size', '0')
                            seeds = torrent.get('seeds', 0)
                            hash_val = torrent.get('hash', '')
                            
                            if seeds < self.min_seeders: continue
                            if not hash_val: continue
                            
                            # Create magnet link
                            magnet = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash_val, urllib.quote_plus(title))
                            magnet += '&tr=udp://tracker.opentrackr.org:1337/announce'
                            magnet += '&tr=udp://tracker.leechers-paradise.org:6969/announce'
                            magnet += '&tr=udp://9.rarbg.to:2710/announce'
                            
                            # Map YTS quality to standard format
                            if quality == '2160p':
                                q = '4K'
                            elif quality == '1080p':
                                q = '1080p'
                            elif quality == '720p':
                                q = 'HD'
                            else:
                                q = 'SD'
                            
                            info = '%s | %s Seeds | %s' % (size, seeds, torrent.get('type', ''))

                            sources.append({
                                'source': 'YTS',
                                'quality': q,
                                'language': 'en',
                                'url': magnet,
                                'info': info,
                                'direct': False,
                                'debridonly': True,
                                'provider': 'yts'
                            })

                        except:
                            pass
                except:
                    pass

            return sources
        except:
            return sources

    def resolve(self, url):
        return url
