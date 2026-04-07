# -*- coding: utf-8 -*-

'''
    Genesis Add-on - CocoScrapers External Provider
    Wrapper for script.module.cocoscrapers

    If the user has CocoScrapers installed, this module loads their scrapers
    and converts the results into Genesis source format.
'''

import re
import xbmc

from resources.lib.libraries import control


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = []
        self.base_link = ''
        self._scrapers = []
        self._loaded = False

    def _load_scrapers(self):
        """Try to import CocoScrapers module."""
        if self._loaded:
            return
        self._loaded = True
        try:
            # CocoScrapers installs as script.module.cocoscrapers
            # It provides a sources_cocoscrapers package with individual scrapers
            import importlib
            coco = importlib.import_module('cocoscrapers')
            if hasattr(coco, 'sources'):
                self._scrapers = coco.sources()
            else:
                # Try to get the scraper list from the package
                from cocoscrapers import sources_cocoscrapers
                if hasattr(sources_cocoscrapers, 'all_scrapers'):
                    self._scrapers = sources_cocoscrapers.all_scrapers
            control.log('CocoScrapers: Loaded %d scrapers' % len(self._scrapers))
        except ImportError:
            control.log('CocoScrapers: Module not installed (script.module.cocoscrapers)')
        except Exception as e:
            control.log('CocoScrapers: Load error: %s' % str(e))

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = 'imdb=%s&title=%s&year=%s' % (imdb, title, year)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = 'imdb=%s&tvdb=%s&tvshowtitle=%s&year=%s' % (imdb, tvdb, tvshowtitle, year)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return
            url += '&title=%s&premiered=%s&season=%s&episode=%s' % (title, premiered, season, episode)
            return url
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        """Get sources from CocoScrapers external providers."""
        sources = []
        try:
            self._load_scrapers()
            if not self._scrapers:
                return sources

            try:
                from urllib.parse import parse_qs
            except ImportError:
                from urlparse import parse_qs

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data.get('tvshowtitle', data.get('title', ''))
            year = data.get('year', '')
            imdb = data.get('imdb', '')
            season = data.get('season', '')
            episode = data.get('episode', '')

            for scraper in self._scrapers:
                try:
                    if hasattr(scraper, 'sources'):
                        results = scraper.sources(url, hostDict, hostprDict)
                    elif hasattr(scraper, 'get_sources'):
                        results = scraper.get_sources(title, year, imdb, season, episode)
                    else:
                        continue

                    if results and isinstance(results, list):
                        for r in results:
                            if isinstance(r, dict):
                                source_entry = {
                                    'source': r.get('source', r.get('provider', 'CocoScrapers')),
                                    'quality': r.get('quality', 'SD'),
                                    'language': r.get('language', 'en'),
                                    'url': r.get('url', ''),
                                    'direct': r.get('direct', False),
                                    'debridonly': r.get('debridonly', False),
                                    'info': r.get('info', '')
                                }
                                if source_entry['url']:
                                    sources.append(source_entry)
                except Exception as e:
                    control.log('CocoScrapers scraper error: %s' % str(e))
                    continue

        except Exception as e:
            control.log('CocoScrapers sources error: %s' % str(e))

        control.log('CocoScrapers: Found %d sources' % len(sources))
        return sources

    def resolve(self, url):
        return url
