# -*- coding: utf-8 -*-
"""Syncher - FootballOrgin.com scraper"""

import re
from resources.lib.modules import control
from resources.lib.modules import client

BASE_URL = 'https://www.footballorgin.com'

def is_enabled():
    return control.setting('scraper.footballorgin') == 'true'

def get_categories():
    return [
        {'name': '[COLOR cyan]Premier League[/COLOR]', 'url': BASE_URL + '/category/premier-league/', 'image': 'sports.png'},
        {'name': '[COLOR cyan]Champions League[/COLOR]', 'url': BASE_URL + '/category/champions-league/', 'image': 'sports.png'},
        {'name': '[COLOR cyan]La Liga[/COLOR]', 'url': BASE_URL + '/category/la-liga/', 'image': 'sports.png'},
        {'name': '[COLOR cyan]Serie A[/COLOR]', 'url': BASE_URL + '/category/serie-a/', 'image': 'sports.png'},
        {'name': '[COLOR cyan]Bundesliga[/COLOR]', 'url': BASE_URL + '/category/bundesliga/', 'image': 'sports.png'},
        {'name': '[COLOR cyan]FA Cup[/COLOR]', 'url': BASE_URL + '/category/fa-cup/', 'image': 'sports.png'},
        {'name': '[COLOR cyan]Full Match Replay[/COLOR]', 'url': BASE_URL + '/full-match-replay/', 'image': 'sports.png'},
        {'name': '[COLOR cyan]Latest[/COLOR]', 'url': BASE_URL + '/', 'image': 'sports.png'},
    ]

def get_items(url):
    items = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return items
        posts = re.findall(r'<h\d[^>]*class="[^"]*entry-title[^"]*"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
        if not posts:
            posts = re.findall(r'<a[^>]*href="([^"]*)"[^>]*rel="bookmark"[^>]*>([^<]*)</a>', html)
        for url_item, name in posts[:30]:
            items.append({'name': name.strip(), 'url': url_item, 'thumb': ''})
    except Exception as e:
        control.log('FootballOrgin items error: %s' % e)
    return items

def get_sources(url):
    sources = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return sources
        iframes = re.findall(r'(?:src|data-src)="(https?://[^"]*(?:embed|player|video|stream)[^"]*)"', html, re.I)
        for i, i_url in enumerate(iframes):
            sources.append({'label': '[COLOR cyan]FootballOrgin[/COLOR] | Server %d' % (i + 1), 'url': i_url, 'type': 'embed'})
        videos = re.findall(r'(https?://[^"\'<\s]*\.(?:mp4|m3u8)[^"\'<\s]*)', html, re.I)
        for v in videos:
            sources.append({'label': '[COLOR cyan]FootballOrgin[/COLOR] | Direct', 'url': v, 'type': 'direct'})
    except Exception as e:
        control.log('FootballOrgin sources error: %s' % e)
    return sources
