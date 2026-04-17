# -*- coding: utf-8 -*-
"""Syncher - RapidRAR.cr scraper"""

import re
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.scrapers import parse_quality, parse_info, match_title, match_episode

BASE_URL = 'https://rapidrar.cr'

def is_enabled():
    return control.setting('scraper.rapidrar') == 'true'

def get_movie_sources(title, year, imdb=''):
    if not is_enabled():
        return []
    sources = []
    try:
        query = '%s %s' % (title, year)
        search_url = BASE_URL + '/search/%s' % query.replace(' ', '+')
        html = client.request(search_url, timeout=20)
        if not html:
            return sources

        # Parse search results
        items = re.findall(r'<a[^>]*href="(%s/[^"]*)"[^>]*>([^<]*)</a>' % re.escape(BASE_URL), html)
        items += re.findall(r'<a[^>]*href="(/[^"]*)"[^>]*>([^<]*(?:%s)[^<]*)</a>' % re.escape(title.split()[0]), html, re.I)

        for url, name in items:
            if not match_title(name, title, year):
                continue
            if not url.startswith('http'):
                url = BASE_URL + url
            quality = parse_quality(name)
            info = parse_info(name)
            label = '[COLOR gold]RapidRAR[/COLOR] | %s | %s' % (quality, info) if info else '[COLOR gold]RapidRAR[/COLOR] | %s' % quality
            sources.append({
                'source': 'RapidRAR',
                'quality': quality,
                'info': info,
                'label': label,
                'url': url,
                'name': name,
                'type': 'hoster',
                'debrid': 'rapidrar',
                'direct': False,
            })
    except Exception as e:
        control.log('RapidRAR scraper error: %s' % e)
    return sources

def get_episode_sources(title, season, episode, imdb=''):
    if not is_enabled():
        return []
    sources = []
    try:
        query = '%s S%sE%s' % (title, str(season).zfill(2), str(episode).zfill(2))
        search_url = BASE_URL + '/search/%s' % query.replace(' ', '+')
        html = client.request(search_url, timeout=20)
        if not html:
            return sources

        items = re.findall(r'<a[^>]*href="(%s/[^"]*)"[^>]*>([^<]*)</a>' % re.escape(BASE_URL), html)
        items += re.findall(r'<a[^>]*href="(/[^"]*)"[^>]*>([^<]*)</a>', html)

        for url, name in items:
            if not match_episode(name, title, season, episode):
                continue
            if not url.startswith('http'):
                url = BASE_URL + url
            quality = parse_quality(name)
            info = parse_info(name)
            label = '[COLOR gold]RapidRAR[/COLOR] | %s | %s' % (quality, info) if info else '[COLOR gold]RapidRAR[/COLOR] | %s' % quality
            sources.append({
                'source': 'RapidRAR',
                'quality': quality,
                'info': info,
                'label': label,
                'url': url,
                'name': name,
                'type': 'hoster',
                'debrid': 'rapidrar',
                'direct': False,
            })
    except Exception as e:
        control.log('RapidRAR episode scraper error: %s' % e)
    return sources
