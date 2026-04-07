# -*- coding: utf-8 -*-
"""Syncher - Music scraper: searches scene sites for music downloads"""

import re
import threading
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.scrapers import parse_quality, parse_info, clean_title

# Music-focused scene sites
MUSIC_SITES = [
    {'name': 'RLSbb', 'base': 'https://rlsbb.to', 'color': 'red'},
    {'name': 'DDLValley', 'base': 'https://ddlvalley.me', 'color': 'yellow'},
    {'name': 'SceneSource', 'base': 'https://scenesource.me', 'color': 'white'},
    {'name': 'PSA', 'base': 'https://psa.wf', 'color': 'lime'},
]

def search_music(query):
    """Search all scene sites for music in parallel"""
    all_sources = []
    lock = threading.Lock()

    def _search_site(site, query):
        try:
            search_url = site['base'] + '/?s=%s' % query.replace(' ', '+')
            html = client.request(search_url, timeout=20)
            if not html:
                return

            posts = re.findall(r'<a[^>]*href="([^"]*)"[^>]*rel="bookmark"[^>]*>([^<]*)</a>', html)
            if not posts:
                posts = re.findall(r'<h\d[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)

            for url, name in posts[:10]:
                name_lower = name.lower()
                # Filter for music content
                if not any(kw in name_lower for kw in ['mp3', 'flac', 'wav', 'album', 'discography',
                    'music', '320kbps', '128kbps', 'cbr', 'vbr', 'lossless', 'soundtrack',
                    'ost', 'single', 'ep ', ' ep', 'vinyl', 'deluxe', 'remaster']):
                    # Also check if query words are in the name
                    query_words = clean_title(query).split()
                    if not all(w in clean_title(name) for w in query_words[:2]):
                        continue

                links = _get_links(url, site['base'])
                for link_url in links:
                    is_magnet = link_url.startswith('magnet:')
                    hoster = 'Torrent' if is_magnet else re.findall(r'https?://(?:www\.)?([^/]+)', link_url)[0].split('.')[0].title()

                    quality = 'FLAC' if 'flac' in name_lower else '320kbps' if '320' in name_lower else 'MP3'
                    label = '[COLOR %s]%s[/COLOR] | %s | %s | %s' % (site['color'], site['name'], quality, hoster, name[:60])

                    with lock:
                        all_sources.append({
                            'source': site['name'], 'quality': quality, 'info': '',
                            'label': label, 'url': link_url, 'name': name,
                            'type': 'torrent' if is_magnet else 'hoster',
                            'debrid': '', 'direct': False,
                        })
        except Exception as e:
            control.log('Music scraper %s error: %s' % (site['name'], e))

    threads = []
    for site in MUSIC_SITES:
        t = threading.Thread(target=_search_site, args=(site, query))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=25)

    return all_sources

def _get_links(url, base_url):
    """Extract download links from a post page"""
    links = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return links
        ddl_patterns = [
            r'href="(https?://(?:rapidrar|nitroflare|clicknupload|uploadgig|rapidgator|turbobit|uploaded|ddownload|katfile|mega|1fichier|hexupload|filefactory|krakenfiles|drop\.download)[^"]*)"',
        ]
        for pattern in ddl_patterns:
            for match in re.finditer(pattern, html, re.I):
                links.append(match.group(1))
        magnets = re.findall(r'(magnet:\?xt=urn:btih:[^"\'<\s]+)', html)
        for m in magnets:
            links.append(m)
    except:
        pass
    return links
