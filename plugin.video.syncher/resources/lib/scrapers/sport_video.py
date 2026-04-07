# -*- coding: utf-8 -*-
"""Syncher - Sport-Video.org.ua scraper (NBA, NFL, MLB, football replays)"""

import re
from resources.lib.modules import control
from resources.lib.modules import client

BASE_URL = 'https://www.sport-video.org.ua'

def is_enabled():
    return control.setting('scraper.sportvideo') == 'true'

def get_categories():
    return [
        {'name': '[COLOR gold]NBA[/COLOR] - Basketball', 'url': BASE_URL + '/basketball/nba/', 'image': 'sports.png'},
        {'name': '[COLOR gold]NFL[/COLOR] - American Football', 'url': BASE_URL + '/americanfootball/', 'image': 'sports.png'},
        {'name': '[COLOR gold]MLB[/COLOR] - Baseball', 'url': BASE_URL + '/baseball/', 'image': 'sports.png'},
        {'name': '[COLOR gold]Premier League[/COLOR]', 'url': BASE_URL + '/football/england-premier-league/', 'image': 'sports.png'},
        {'name': '[COLOR gold]Champions League[/COLOR]', 'url': BASE_URL + '/football/uefa-champions-league/', 'image': 'sports.png'},
        {'name': '[COLOR gold]La Liga[/COLOR]', 'url': BASE_URL + '/football/spain-la-liga/', 'image': 'sports.png'},
        {'name': '[COLOR gold]Serie A[/COLOR]', 'url': BASE_URL + '/football/italy-serie-a/', 'image': 'sports.png'},
        {'name': '[COLOR gold]Bundesliga[/COLOR]', 'url': BASE_URL + '/football/germany-bundesliga/', 'image': 'sports.png'},
        {'name': '[COLOR gold]MMA / UFC[/COLOR]', 'url': BASE_URL + '/boxing/', 'image': 'sports.png'},
        {'name': '[COLOR gold]NHL[/COLOR] - Ice Hockey', 'url': BASE_URL + '/hockey/', 'image': 'sports.png'},
        {'name': '[COLOR gold]Tennis[/COLOR]', 'url': BASE_URL + '/tennis/', 'image': 'sports.png'},
        {'name': '[COLOR gold]Rugby[/COLOR]', 'url': BASE_URL + '/rugby/', 'image': 'sports.png'},
    ]

def get_items(url):
    items = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return items
        posts = re.findall(r'<a[^>]*href="([^"]*)"[^>]*title="([^"]*)"[^>]*>\s*(?:<img[^>]*src="([^"]*)")?', html)
        if not posts:
            posts = re.findall(r'<h\d[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
            posts = [(u, n, '') for u, n in posts]
        for url_item, name, thumb in posts[:30]:
            if not url_item.startswith('http'):
                url_item = BASE_URL + url_item
            if not thumb:
                thumb = ''
            elif not thumb.startswith('http'):
                thumb = BASE_URL + thumb
            items.append({
                'name': name.strip(),
                'url': url_item,
                'thumb': thumb,
            })
    except Exception as e:
        control.log('SportVideo items error: %s' % e)
    return items

def get_sources(url):
    sources = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return sources
        # Find direct video links
        videos = re.findall(r'(https?://[^"\'<\s]*\.(?:mp4|m3u8|mkv|avi|ts)[^"\'<\s]*)', html, re.I)
        for v in videos:
            sources.append({'label': '[COLOR gold]SportVideo[/COLOR] | Direct', 'url': v, 'type': 'direct'})
        # Find torrent/magnet links
        magnets = re.findall(r'(magnet:\?xt=urn:btih:[^"\'<\s]+)', html)
        for m in magnets:
            sources.append({'label': '[COLOR gold]SportVideo[/COLOR] | Torrent', 'url': m, 'type': 'torrent'})
        # Find DDL links
        ddl = re.findall(r'href="(https?://(?:rapidrar|nitroflare|rapidgator|turbobit|uploaded|mega)[^"]*)"', html, re.I)
        for d in ddl:
            hoster = re.findall(r'https?://(?:www\.)?([^/]+)', d)[0].split('.')[0].title()
            sources.append({'label': '[COLOR gold]SportVideo[/COLOR] | %s' % hoster, 'url': d, 'type': 'hoster'})
        # Find iframe embeds
        iframes = re.findall(r'(?:src|data-src)="(https?://[^"]*(?:embed|player|video)[^"]*)"', html, re.I)
        for i_url in iframes:
            sources.append({'label': '[COLOR gold]SportVideo[/COLOR] | Stream', 'url': i_url, 'type': 'embed'})
    except Exception as e:
        control.log('SportVideo sources error: %s' % e)
    return sources
