# -*- coding: utf-8 -*-
"""Syncher - Basketball-Video.com scraper"""

import re
from resources.lib.modules import control
from resources.lib.modules import client

BASE_URL = 'https://basketball-video.com'

def is_enabled():
    return control.setting('scraper.basketballvideo') == 'true'

def get_categories():
    return [
        {'name': '[COLOR orange]NBA Replays[/COLOR]', 'url': BASE_URL + '/category/nba/', 'image': 'sports.png'},
        {'name': '[COLOR orange]NBA Playoffs[/COLOR]', 'url': BASE_URL + '/category/nba-playoffs/', 'image': 'sports.png'},
        {'name': '[COLOR orange]NBA Finals[/COLOR]', 'url': BASE_URL + '/category/nba-finals/', 'image': 'sports.png'},
        {'name': '[COLOR orange]FIBA[/COLOR]', 'url': BASE_URL + '/category/fiba/', 'image': 'sports.png'},
        {'name': '[COLOR orange]Euroleague[/COLOR]', 'url': BASE_URL + '/category/euroleague/', 'image': 'sports.png'},
        {'name': '[COLOR orange]Latest[/COLOR]', 'url': BASE_URL + '/', 'image': 'sports.png'},
    ]

def get_items(url):
    items = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return items
        posts = re.findall(r'<article[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>\s*(?:<img[^>]*src="([^"]*)")?.*?<h\d[^>]*>(?:<a[^>]*>)?([^<]*)(?:</a>)?</h\d>', html, re.S)
        if not posts:
            posts = re.findall(r'<h\d[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
            posts = [(u, '', n) for u, n in posts]
        for url_item, thumb, name in posts[:30]:
            if not name:
                continue
            items.append({'name': name.strip(), 'url': url_item, 'thumb': thumb or ''})
    except Exception as e:
        control.log('BasketballVideo items error: %s' % e)
    return items

def get_sources(url):
    sources = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return sources
        iframes = re.findall(r'(?:src|data-src)="(https?://[^"]*(?:embed|player|video|stream)[^"]*)"', html, re.I)
        for i, i_url in enumerate(iframes):
            sources.append({'label': '[COLOR orange]BasketballVideo[/COLOR] | Server %d' % (i + 1), 'url': i_url, 'type': 'embed'})
        videos = re.findall(r'(https?://[^"\'<\s]*\.(?:mp4|m3u8)[^"\'<\s]*)', html, re.I)
        for v in videos:
            sources.append({'label': '[COLOR orange]BasketballVideo[/COLOR] | Direct', 'url': v, 'type': 'direct'})
    except Exception as e:
        control.log('BasketballVideo sources error: %s' % e)
    return sources
