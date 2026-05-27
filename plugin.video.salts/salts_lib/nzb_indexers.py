"""
SALTS Library - NZB Indexer Integration
Supports multiple NZB indexers with Newznab API:
- NZBGeek
- NZBFinder
- NZBPlanet
- NZBHydra2
- DrunkenSlug
- NZB.su
- Generic Newznab API support

Author: zeus768
"""
import json
import time
import re
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote_plus
from datetime import datetime

import xbmc
import xbmcgui
import xbmcaddon

from . import log_utils

ADDON = xbmcaddon.Addon()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


class NewznabIndexer:
    """Generic Newznab API indexer"""
    
    def __init__(self, name, url, api_key):
        self.name = name
        self.url = url.rstrip('/')
        self.api_key = api_key
    
    def search(self, query, category='5000', limit=100):
        """
        Search indexer using Newznab API
        Categories: 5000 = TV, 2000 = Movies, 5070 = Anime, 7000 = Other
        """
        try:
            params = {
                't': 'search',
                'apikey': self.api_key,
                'q': query,
                'cat': category,
                'limit': limit,
                'extended': 1
            }
            
            url = f'{self.url}/api?{urlencode(params)}'
            req = Request(url, headers={'User-Agent': UA})
            resp = urlopen(req, timeout=30)
            xml_data = resp.read().decode('utf-8')
            
            return self._parse_newznab_xml(xml_data)
        except Exception as e:
            log_utils.log_error(f'{self.name} search error: {e}')
            return []
    
    def search_movie(self, title, year=None, imdbid=None):
        """Search for movie"""
        params = {
            't': 'movie',
            'apikey': self.api_key,
            'extended': 1
        }
        
        if imdbid:
            params['imdbid'] = imdbid.replace('tt', '')
        else:
            params['q'] = title
            if year:
                params['q'] += f' {year}'
        
        try:
            url = f'{self.url}/api?{urlencode(params)}'
            req = Request(url, headers={'User-Agent': UA})
            resp = urlopen(req, timeout=30)
            xml_data = resp.read().decode('utf-8')
            
            return self._parse_newznab_xml(xml_data)
        except Exception as e:
            log_utils.log_error(f'{self.name} movie search error: {e}')
            return []
    
    def search_tv(self, title, season=None, episode=None, tvdbid=None):
        """Search for TV show"""
        params = {
            't': 'tvsearch',
            'apikey': self.api_key,
            'extended': 1
        }
        
        if tvdbid:
            params['tvdbid'] = tvdbid
        else:
            params['q'] = title
        
        if season:
            params['season'] = season
        if episode:
            params['ep'] = episode
        
        try:
            url = f'{self.url}/api?{urlencode(params)}'
            req = Request(url, headers={'User-Agent': UA})
            resp = urlopen(req, timeout=30)
            xml_data = resp.read().decode('utf-8')
            
            return self._parse_newznab_xml(xml_data)
        except Exception as e:
            log_utils.log_error(f'{self.name} TV search error: {e}')
            return []
    
    def _parse_newznab_xml(self, xml_data):
        """Parse Newznab XML response"""
        results = []
        
        try:
            root = ET.fromstring(xml_data)
            channel = root.find('channel')
            if channel is None:
                return results
            
            for item in channel.findall('item'):
                result = {
                    'title': '',
                    'link': '',
                    'nzb_url': '',
                    'size': 0,
                    'size_str': '',
                    'age_days': 0,
                    'category': '',
                    'indexer': self.name
                }
                
                # Basic fields
                title_elem = item.find('title')
                if title_elem is not None:
                    result['title'] = title_elem.text or ''
                
                link_elem = item.find('link')
                if link_elem is not None:
                    result['nzb_url'] = link_elem.text or ''
                    result['link'] = result['nzb_url']
                
                # Newznab attributes
                for attr in item.findall('{http://www.newznab.com/DTD/2010/feeds/attributes/}attr'):
                    name = attr.get('name', '')
                    value = attr.get('value', '')
                    
                    if name == 'size':
                        try:
                            result['size'] = int(value)
                            result['size_str'] = self._format_size(int(value))
                        except:
                            pass
                    elif name == 'category':
                        result['category'] = value
                    elif name == 'usenetdate':
                        try:
                            pub_date = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                            age = datetime.now() - pub_date
                            result['age_days'] = age.days
                        except:
                            pass
                
                # Fallback for size
                if not result['size_str']:
                    enclosure = item.find('enclosure')
                    if enclosure is not None:
                        try:
                            length = int(enclosure.get('length', 0))
                            result['size'] = length
                            result['size_str'] = self._format_size(length)
                        except:
                            pass
                
                if result['title'] and result['nzb_url']:
                    results.append(result)
        
        except Exception as e:
            log_utils.log_error(f'Newznab XML parse error: {e}')
        
        return results
    
    @staticmethod
    def _format_size(bytes_size):
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f'{bytes_size:.1f} {unit}'
            bytes_size /= 1024.0
        return f'{bytes_size:.1f} PB'


class NZBGeek(NewznabIndexer):
    """NZBGeek indexer"""
    
    def __init__(self):
        api_key = ADDON.getSetting('nzbgeek_api_key') or ''
        super().__init__('NZBGeek', 'https://api.nzbgeek.info', api_key)
    
    def is_enabled(self):
        return ADDON.getSetting('nzbgeek_enabled') == 'true' and self.api_key


class NZBFinder(NewznabIndexer):
    """NZBFinder indexer"""
    
    def __init__(self):
        api_key = ADDON.getSetting('nzbfinder_api_key') or ''
        super().__init__('NZBFinder', 'https://nzbfinder.ws', api_key)
    
    def is_enabled(self):
        return ADDON.getSetting('nzbfinder_enabled') == 'true' and self.api_key


class NZBPlanet(NewznabIndexer):
    """NZBPlanet indexer"""
    
    def __init__(self):
        api_key = ADDON.getSetting('nzbplanet_api_key') or ''
        super().__init__('NZBPlanet', 'https://nzbplanet.net', api_key)
    
    def is_enabled(self):
        return ADDON.getSetting('nzbplanet_enabled') == 'true' and self.api_key


class DrunkenSlug(NewznabIndexer):
    """DrunkenSlug indexer"""
    
    def __init__(self):
        api_key = ADDON.getSetting('drunkenslug_api_key') or ''
        super().__init__('DrunkenSlug', 'https://api.drunkenslug.com', api_key)
    
    def is_enabled(self):
        return ADDON.getSetting('drunkenslug_enabled') == 'true' and self.api_key


class NZBsu(NewznabIndexer):
    """NZB.su indexer"""
    
    def __init__(self):
        api_key = ADDON.getSetting('nzbsu_api_key') or ''
        super().__init__('NZB.su', 'https://api.nzb.su', api_key)
    
    def is_enabled(self):
        return ADDON.getSetting('nzbsu_enabled') == 'true' and self.api_key


class NZBHydra2(NewznabIndexer):
    """NZBHydra2 meta-indexer"""
    
    def __init__(self):
        url = ADDON.getSetting('nzbhydra2_url') or 'http://localhost:5076'
        api_key = ADDON.getSetting('nzbhydra2_api_key') or ''
        super().__init__('NZBHydra2', url, api_key)
    
    def is_enabled(self):
        return ADDON.getSetting('nzbhydra2_enabled') == 'true' and self.api_key


class CustomNewznab(NewznabIndexer):
    """Custom Newznab indexer"""
    
    def __init__(self):
        name = ADDON.getSetting('custom_newznab_name') or 'Custom'
        url = ADDON.getSetting('custom_newznab_url') or ''
        api_key = ADDON.getSetting('custom_newznab_api_key') or ''
        super().__init__(name, url, api_key)
    
    def is_enabled(self):
        return (ADDON.getSetting('custom_newznab_enabled') == 'true' and 
                self.url and self.api_key)


def get_all_indexers():
    """Get all enabled NZB indexers"""
    indexers = []
    
    indexer_classes = [
        NZBGeek,
        NZBFinder,
        NZBPlanet,
        DrunkenSlug,
        NZBsu,
        NZBHydra2,
        CustomNewznab
    ]
    
    for indexer_class in indexer_classes:
        try:
            indexer = indexer_class()
            if indexer.is_enabled():
                indexers.append(indexer)
        except Exception as e:
            log_utils.log_error(f'Indexer init error: {e}')
    
    return indexers


def search_all_indexers(query, media_type='movie', **kwargs):
    """
    Search all enabled indexers
    media_type: 'movie', 'tv', or 'general'
    kwargs: title, year, season, episode, imdbid, tvdbid
    """
    indexers = get_all_indexers()
    if not indexers:
        log_utils.log_warning('No NZB indexers configured')
        return []
    
    all_results = []
    
    for indexer in indexers:
        try:
            if media_type == 'movie':
                results = indexer.search_movie(
                    kwargs.get('title', query),
                    kwargs.get('year'),
                    kwargs.get('imdbid')
                )
            elif media_type == 'tv':
                results = indexer.search_tv(
                    kwargs.get('title', query),
                    kwargs.get('season'),
                    kwargs.get('episode'),
                    kwargs.get('tvdbid')
                )
            else:
                results = indexer.search(query)
            
            all_results.extend(results)
        except Exception as e:
            log_utils.log_error(f'Indexer {indexer.name} search error: {e}')
    
    # Sort by size (larger first) and age (newer first)
    all_results.sort(key=lambda x: (-x['size'], x['age_days']))
    
    return all_results
