# -*- coding: utf-8 -*-
"""Syncher - RapidMoviez.me scraper"""

import re
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.scrapers import parse_quality, parse_info, match_title, match_episode

BASE_URL = 'https://rapidmoviez.me'

def is_enabled():
    return control.setting('scraper.rapidmoviez') == 'true'

def _search(query):
    results = []
    try:
        search_url = BASE_URL + '/search/%s' % query.replace(' ', '+')
        html = client.request(search_url, timeout=20)
        if not html:
            return results
        posts = re.findall(r'<a[^>]*href="(%s/release/[^"]*)"[^>]*>\s*([^<]+)</a>' % re.escape(BASE_URL), html)
        if not posts:
            posts = re.findall(r'<a[^>]*href="(/release/[^"]*)"[^>]*>\s*([^<]+)</a>', html)
        for url, name in posts:
            if not url.startswith('http'):
                url = BASE_URL + url
            results.append((url, name.strip()))
    except Exception as e:
        control.log('RapidMoviez search error: %s' % e)
    return results

def _get_links(url):
    links = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return links
        # DDL links pattern
        ddl_patterns = [
            r'href="(https?://(?:rapidrar|nitroflare|clicknupload|uploadgig|rapidgator|turbobit|uploaded|ddownload|katfile|mega|1fichier)[^"]*)"',
            r'href="(https?://[^"]*(?:\.mkv|\.mp4|\.avi)[^"]*)"',
        ]
        for pattern in ddl_patterns:
            for match in re.finditer(pattern, html, re.I):
                links.append(match.group(1))
        # Magnet links
        magnets = re.findall(r'(magnet:\?xt=urn:btih:[^"\'<\s]+)', html)
        for m in magnets:
            links.append(m)
    except Exception as e:
        control.log('RapidMoviez get_links error: %s' % e)
    return links

def get_movie_sources(title, year, imdb=''):
    if not is_enabled():
        return []
    sources = []
    try:
        query = '%s %s' % (title, year)
        posts = _search(query)
        for url, name in posts[:10]:
            if not match_title(name, title, year):
                continue
            quality = parse_quality(name)
            info = parse_info(name)
            links = _get_links(url)
            for link_url in links:
                is_magnet = link_url.startswith('magnet:')
                hoster = 'Torrent' if is_magnet else re.findall(r'https?://(?:www\.)?([^/]+)', link_url)[0].split('.')[0].title()
                label = '[COLOR orange]RapidMoviez[/COLOR] | %s | %s | %s' % (quality, info, hoster) if info else '[COLOR orange]RapidMoviez[/COLOR] | %s | %s' % (quality, hoster)
                sources.append({
                    'source': 'RapidMoviez', 'quality': quality, 'info': info,
                    'label': label, 'url': link_url, 'name': name,
                    'type': 'torrent' if is_magnet else 'hoster', 'debrid': '', 'direct': False,
                })
    except Exception as e:
        control.log('RapidMoviez movie error: %s' % e)
    return sources

def get_episode_sources(title, season, episode, imdb=''):
    if not is_enabled():
        return []
    sources = []
    try:
        query = '%s S%sE%s' % (title, str(season).zfill(2), str(episode).zfill(2))
        posts = _search(query)
        for url, name in posts[:10]:
            if not match_episode(name, title, season, episode):
                continue
            quality = parse_quality(name)
            info = parse_info(name)
            links = _get_links(url)
            for link_url in links:
                is_magnet = link_url.startswith('magnet:')
                hoster = 'Torrent' if is_magnet else re.findall(r'https?://(?:www\.)?([^/]+)', link_url)[0].split('.')[0].title()
                label = '[COLOR orange]RapidMoviez[/COLOR] | %s | %s | %s' % (quality, info, hoster) if info else '[COLOR orange]RapidMoviez[/COLOR] | %s | %s' % (quality, hoster)
                sources.append({
                    'source': 'RapidMoviez', 'quality': quality, 'info': info,
                    'label': label, 'url': link_url, 'name': name,
                    'type': 'torrent' if is_magnet else 'hoster', 'debrid': '', 'direct': False,
                })
    except Exception as e:
        control.log('RapidMoviez episode error: %s' % e)
    return sources
