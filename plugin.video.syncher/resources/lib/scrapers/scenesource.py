# -*- coding: utf-8 -*-
"""Syncher - SceneSource.me scraper"""

import re
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.scrapers import parse_quality, parse_info, match_title, match_episode

BASE_URL = 'https://scenesource.me'

def is_enabled():
    return control.setting('scraper.scenesource') == 'true'

def _search(query):
    results = []
    try:
        search_url = BASE_URL + '/?s=%s' % query.replace(' ', '+')
        html = client.request(search_url, timeout=20)
        if not html:
            return results
        posts = re.findall(r'<a[^>]*href="([^"]*)"[^>]*rel="bookmark"[^>]*>([^<]*)</a>', html)
        if not posts:
            posts = re.findall(r'<h\d[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
        for url, name in posts:
            results.append((url, name.strip()))
    except Exception as e:
        control.log('SceneSource search error: %s' % e)
    return results

def _get_links(url):
    links = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return links
        ddl_patterns = [
            r'href="(https?://(?:rapidrar|nitroflare|clicknupload|uploadgig|rapidgator|turbobit|uploaded|ddownload|katfile|mega|1fichier)[^"]*)"',
        ]
        for pattern in ddl_patterns:
            for match in re.finditer(pattern, html, re.I):
                links.append(match.group(1))
        magnets = re.findall(r'(magnet:\?xt=urn:btih:[^"\'<\s]+)', html)
        for m in magnets:
            links.append(m)
        # NFO links often have torrent links nearby
        nfo_links = re.findall(r'href="([^"]*\.nfo)"', html, re.I)
    except:
        pass
    return links

def get_movie_sources(title, year, imdb=''):
    if not is_enabled():
        return []
    sources = []
    try:
        posts = _search('%s %s' % (title, year))
        for url, name in posts[:10]:
            if not match_title(name, title, year):
                continue
            quality = parse_quality(name)
            info = parse_info(name)
            links = _get_links(url)
            for link_url in links:
                is_magnet = link_url.startswith('magnet:')
                hoster = 'Torrent' if is_magnet else re.findall(r'https?://(?:www\.)?([^/]+)', link_url)[0].split('.')[0].title()
                label = '[COLOR white]SceneSource[/COLOR] | %s | %s | %s' % (quality, info, hoster) if info else '[COLOR white]SceneSource[/COLOR] | %s | %s' % (quality, hoster)
                sources.append({
                    'source': 'SceneSource', 'quality': quality, 'info': info,
                    'label': label, 'url': link_url, 'name': name,
                    'type': 'torrent' if is_magnet else 'hoster', 'debrid': '', 'direct': False,
                })
    except Exception as e:
        control.log('SceneSource movie error: %s' % e)
    return sources

def get_episode_sources(title, season, episode, imdb=''):
    if not is_enabled():
        return []
    sources = []
    try:
        posts = _search('%s S%sE%s' % (title, str(season).zfill(2), str(episode).zfill(2)))
        for url, name in posts[:10]:
            if not match_episode(name, title, season, episode):
                continue
            quality = parse_quality(name)
            info = parse_info(name)
            links = _get_links(url)
            for link_url in links:
                is_magnet = link_url.startswith('magnet:')
                hoster = 'Torrent' if is_magnet else re.findall(r'https?://(?:www\.)?([^/]+)', link_url)[0].split('.')[0].title()
                label = '[COLOR white]SceneSource[/COLOR] | %s | %s | %s' % (quality, info, hoster) if info else '[COLOR white]SceneSource[/COLOR] | %s | %s' % (quality, hoster)
                sources.append({
                    'source': 'SceneSource', 'quality': quality, 'info': info,
                    'label': label, 'url': link_url, 'name': name,
                    'type': 'torrent' if is_magnet else 'hoster', 'debrid': '', 'direct': False,
                })
    except Exception as e:
        control.log('SceneSource episode error: %s' % e)
    return sources
