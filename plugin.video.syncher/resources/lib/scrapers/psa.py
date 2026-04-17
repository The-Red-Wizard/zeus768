# -*- coding: utf-8 -*-
"""Syncher - PSA.wf scraper (torrents and DDL)"""

import re
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.scrapers import parse_quality, parse_info, match_title, match_episode, extract_magnet_hash

BASE_URL = 'https://psa.wf'

def is_enabled():
    return control.setting('scraper.psa') == 'true'

def _search(query):
    results = []
    try:
        search_url = BASE_URL + '/?s=%s' % query.replace(' ', '+')
        html = client.request(search_url, timeout=20)
        if not html:
            return results

        # Parse post entries
        posts = re.findall(r'<article[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>.*?</article>', html, re.S)
        if not posts:
            posts = re.findall(r'<h\d[^>]*class="[^"]*entry-title[^"]*"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
        if not posts:
            posts = re.findall(r'<a[^>]*href="([^"]*)"[^>]*rel="bookmark"[^>]*>([^<]*)</a>', html)

        for url, name in posts:
            results.append((url, name))
    except Exception as e:
        control.log('PSA search error: %s' % e)
    return results

def _get_links(url):
    """Get download/magnet links from a PSA post page"""
    links = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return links

        # Find magnet links
        magnets = re.findall(r'(magnet:\?xt=urn:btih:[^"\'<\s]+)', html)
        for m in magnets:
            links.append(('magnet', m))

        # Find torrent file links
        torrents = re.findall(r'href="([^"]*\.torrent[^"]*)"', html, re.I)
        for t in torrents:
            links.append(('torrent', t))

        # Find DDL links (RapidRAR, NitroFlare, etc.)
        ddl_patterns = [
            r'href="(https?://(?:rapidrar|nitroflare|clicknupload|uploadgig|rapidgator|turbobit|uploaded|ddownload|katfile|mega)[^"]*)"',
        ]
        for pattern in ddl_patterns:
            for match in re.finditer(pattern, html, re.I):
                links.append(('hoster', match.group(1)))

    except Exception as e:
        control.log('PSA get_links error: %s' % e)
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
            for link_type, link_url in links:
                if link_type == 'magnet':
                    hash_val = extract_magnet_hash(link_url)
                    label = '[COLOR lime]PSA[/COLOR] | %s | %s | Torrent' % (quality, info) if info else '[COLOR lime]PSA[/COLOR] | %s | Torrent' % quality
                    sources.append({
                        'source': 'PSA', 'quality': quality, 'info': info,
                        'label': label, 'url': link_url, 'name': name,
                        'type': 'torrent', 'hash': hash_val, 'debrid': '', 'direct': False,
                    })
                elif link_type == 'hoster':
                    hoster = re.findall(r'https?://(?:www\.)?([^/]+)', link_url)
                    hoster_name = hoster[0].split('.')[0].title() if hoster else 'DDL'
                    label = '[COLOR lime]PSA[/COLOR] | %s | %s | %s' % (quality, info, hoster_name) if info else '[COLOR lime]PSA[/COLOR] | %s | %s' % (quality, hoster_name)
                    sources.append({
                        'source': 'PSA', 'quality': quality, 'info': info,
                        'label': label, 'url': link_url, 'name': name,
                        'type': 'hoster', 'debrid': '', 'direct': False,
                    })
    except Exception as e:
        control.log('PSA movie scraper error: %s' % e)
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
            for link_type, link_url in links:
                if link_type == 'magnet':
                    hash_val = extract_magnet_hash(link_url)
                    label = '[COLOR lime]PSA[/COLOR] | %s | %s | Torrent' % (quality, info) if info else '[COLOR lime]PSA[/COLOR] | %s | Torrent' % quality
                    sources.append({
                        'source': 'PSA', 'quality': quality, 'info': info,
                        'label': label, 'url': link_url, 'name': name,
                        'type': 'torrent', 'hash': hash_val, 'debrid': '', 'direct': False,
                    })
                elif link_type == 'hoster':
                    hoster = re.findall(r'https?://(?:www\.)?([^/]+)', link_url)
                    hoster_name = hoster[0].split('.')[0].title() if hoster else 'DDL'
                    label = '[COLOR lime]PSA[/COLOR] | %s | %s | %s' % (quality, info, hoster_name) if info else '[COLOR lime]PSA[/COLOR] | %s | %s' % (quality, hoster_name)
                    sources.append({
                        'source': 'PSA', 'quality': quality, 'info': info,
                        'label': label, 'url': link_url, 'name': name,
                        'type': 'hoster', 'debrid': '', 'direct': False,
                    })
    except Exception as e:
        control.log('PSA episode scraper error: %s' % e)
    return sources
