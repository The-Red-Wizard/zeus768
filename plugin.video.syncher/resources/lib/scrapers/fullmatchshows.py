# -*- coding: utf-8 -*-
"""Syncher - FullMatchShows.com scraper"""

import re
from resources.lib.modules import control
from resources.lib.modules import client

BASE_URL = 'https://fullmatchshows.com'

def is_enabled():
    return control.setting('scraper.fullmatchshows') == 'true'

def get_categories():
    return [
        {'name': '[COLOR lime]Premier League[/COLOR]', 'url': BASE_URL + '/category/premier-league/', 'image': 'sports.png'},
        {'name': '[COLOR lime]Champions League[/COLOR]', 'url': BASE_URL + '/category/champions-league/', 'image': 'sports.png'},
        {'name': '[COLOR lime]Europa League[/COLOR]', 'url': BASE_URL + '/category/europa-league/', 'image': 'sports.png'},
        {'name': '[COLOR lime]La Liga[/COLOR]', 'url': BASE_URL + '/category/la-liga/', 'image': 'sports.png'},
        {'name': '[COLOR lime]Serie A[/COLOR]', 'url': BASE_URL + '/category/serie-a/', 'image': 'sports.png'},
        {'name': '[COLOR lime]Bundesliga[/COLOR]', 'url': BASE_URL + '/category/bundesliga/', 'image': 'sports.png'},
        {'name': '[COLOR lime]Ligue 1[/COLOR]', 'url': BASE_URL + '/category/ligue-1/', 'image': 'sports.png'},
        {'name': '[COLOR lime]FIFA World Cup[/COLOR]', 'url': BASE_URL + '/category/world-cup/', 'image': 'sports.png'},
        {'name': '[COLOR lime]Latest Matches[/COLOR]', 'url': BASE_URL + '/', 'image': 'sports.png'},
    ]

def get_items(url):
    items = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return items
        posts = re.findall(r'<article[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>\s*(?:<img[^>]*src="([^"]*)"[^>]*)?\s*</a>.*?<h\d[^>]*>\s*<a[^>]*href="[^"]*"[^>]*>([^<]*)</a>', html, re.S)
        if not posts:
            posts = re.findall(r'<h\d[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
            posts = [(u, '', n) for u, n in posts]
        for url_item, thumb, name in posts[:30]:
            if not name:
                name = url_item.split('/')[-2].replace('-', ' ').title() if '/' in url_item else 'Match'
            items.append({'name': name.strip(), 'url': url_item, 'thumb': thumb or ''})
    except Exception as e:
        control.log('FullMatchShows items error: %s' % e)
    return items

def get_sources(url):
    sources = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return sources
        iframes = re.findall(r'(?:src|data-src)="(https?://[^"]*(?:embed|player|video|stream)[^"]*)"', html, re.I)
        for i, i_url in enumerate(iframes):
            sources.append({'label': '[COLOR lime]FullMatchShows[/COLOR] | Server %d' % (i + 1), 'url': i_url, 'type': 'embed'})
        videos = re.findall(r'(https?://[^"\'<\s]*\.(?:mp4|m3u8)[^"\'<\s]*)', html, re.I)
        for v in videos:
            sources.append({'label': '[COLOR lime]FullMatchShows[/COLOR] | Direct', 'url': v, 'type': 'direct'})
    except Exception as e:
        control.log('FullMatchShows sources error: %s' % e)
    return sources
