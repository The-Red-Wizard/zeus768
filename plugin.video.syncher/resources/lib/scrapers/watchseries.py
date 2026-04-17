# -*- coding: utf-8 -*-
"""Syncher - WatchSeriesHD.org scraper (streaming aggregator)"""

import re
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.scrapers import parse_quality, clean_title

BASE_URL = 'https://www1.watchserieshd.org'

def is_enabled():
    return control.setting('scraper.watchseries') == 'true'

def _search(query, content='movie'):
    results = []
    try:
        search_url = BASE_URL + '/search?keyword=%s' % query.replace(' ', '+')
        html = client.request(search_url, timeout=20)
        if not html:
            return results
        items = re.findall(r'<a[^>]*href="([^"]*(?:watch|series|movie)[^"]*)"[^>]*title="([^"]*)"', html, re.I)
        if not items:
            items = re.findall(r'class="[^"]*film-name[^"]*"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
        for url, name in items:
            if not url.startswith('http'):
                url = BASE_URL + url
            results.append((url, name.strip()))
    except Exception as e:
        control.log('WatchSeriesHD search error: %s' % e)
    return results

def _get_streams(url):
    streams = []
    try:
        html = client.request(url, timeout=20)
        if not html:
            return streams
        # Find iframe/embed sources
        iframes = re.findall(r'(?:src|data-src)="(https?://[^"]*(?:embed|player|stream)[^"]*)"', html, re.I)
        for iframe_url in iframes:
            streams.append(iframe_url)
        # Find direct video links
        directs = re.findall(r'(?:file|source|src)\s*[=:]\s*["\']?(https?://[^"\'<\s]*\.(?:mp4|m3u8|mkv)[^"\'<\s]*)', html, re.I)
        for d in directs:
            streams.append(d)
    except Exception as e:
        control.log('WatchSeriesHD streams error: %s' % e)
    return streams

def get_movie_sources(title, year, imdb=''):
    if not is_enabled():
        return []
    sources = []
    try:
        query = '%s %s' % (title, year)
        posts = _search(query, 'movie')
        for url, name in posts[:5]:
            if clean_title(title) not in clean_title(name):
                continue
            streams = _get_streams(url)
            for i, stream_url in enumerate(streams):
                label = '[COLOR magenta]WatchSeriesHD[/COLOR] | Server %d' % (i + 1)
                sources.append({
                    'source': 'WatchSeriesHD', 'quality': 'HD', 'info': '',
                    'label': label, 'url': stream_url, 'name': name,
                    'type': 'embed', 'debrid': '', 'direct': True,
                })
    except Exception as e:
        control.log('WatchSeriesHD movie error: %s' % e)
    return sources

def get_episode_sources(title, season, episode, imdb=''):
    if not is_enabled():
        return []
    sources = []
    try:
        query = '%s' % title
        posts = _search(query, 'tv')
        for url, name in posts[:5]:
            if clean_title(title) not in clean_title(name):
                continue
            # Try to navigate to specific episode
            ep_url = url.rstrip('/') + '/season-%s/episode-%s' % (season, episode)
            streams = _get_streams(ep_url)
            if not streams:
                streams = _get_streams(url)
            for i, stream_url in enumerate(streams):
                label = '[COLOR magenta]WatchSeriesHD[/COLOR] | S%sE%s | Server %d' % (str(season).zfill(2), str(episode).zfill(2), i + 1)
                sources.append({
                    'source': 'WatchSeriesHD', 'quality': 'HD', 'info': '',
                    'label': label, 'url': stream_url, 'name': name,
                    'type': 'embed', 'debrid': '', 'direct': True,
                })
    except Exception as e:
        control.log('WatchSeriesHD episode error: %s' % e)
    return sources
