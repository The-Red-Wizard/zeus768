# -*- coding: utf-8 -*-
"""Syncher - Podcast discovery via iTunes Search API + RSS feed parsing"""

import re
import xml.etree.ElementTree as ET
from resources.lib.modules import client
from resources.lib.modules import control

ITUNES_SEARCH = 'https://itunes.apple.com/search'
ITUNES_LOOKUP = 'https://itunes.apple.com/lookup'
ITUNES_TOP = 'https://rss.applemarketingtools.com/api/v2/us/podcasts/top/%s/podcasts.json'

PODCAST_GENRES = [
    {'id': '1301', 'name': 'Arts'},
    {'id': '1321', 'name': 'Business'},
    {'id': '1303', 'name': 'Comedy'},
    {'id': '1304', 'name': 'Education'},
    {'id': '1483', 'name': 'Fiction'},
    {'id': '1511', 'name': 'Government'},
    {'id': '1512', 'name': 'Health & Fitness'},
    {'id': '1302', 'name': 'History'},
    {'id': '1305', 'name': 'Kids & Family'},
    {'id': '1502', 'name': 'Leisure'},
    {'id': '1310', 'name': 'Music'},
    {'id': '1489', 'name': 'News'},
    {'id': '1314', 'name': 'Religion & Spirituality'},
    {'id': '1533', 'name': 'Science'},
    {'id': '1324', 'name': 'Society & Culture'},
    {'id': '1545', 'name': 'Sports'},
    {'id': '1309', 'name': 'TV & Film'},
    {'id': '1318', 'name': 'Technology'},
    {'id': '1488', 'name': 'True Crime'},
]

def get_genres():
    return PODCAST_GENRES

def search_podcasts(query, limit=30):
    """Search for podcasts via iTunes"""
    import urllib.parse
    url = '%s?term=%s&media=podcast&entity=podcast&limit=%s' % (
        ITUNES_SEARCH, urllib.parse.quote(query), limit)
    data = client.request_json(url)
    if not data:
        return []
    return _parse_itunes_results(data.get('results', []))

def get_top_podcasts(limit=50):
    """Get top podcasts via Apple RSS feed"""
    url = ITUNES_TOP % limit
    data = client.request_json(url)
    if not data:
        return []
    feed = data.get('feed', {})
    results = feed.get('results', [])
    podcasts = []
    for r in results:
        podcasts.append({
            'id': r.get('id', ''),
            'name': r.get('name', ''),
            'artist': r.get('artistName', ''),
            'image': r.get('artworkUrl100', '').replace('100x100', '600x600'),
            'genre': ', '.join(g.get('name', '') for g in r.get('genres', [])),
            'feed_url': '',  # Need lookup for feed URL
            'url': r.get('url', ''),
        })
    return podcasts

def get_top_by_genre(genre_id, limit=30):
    """Search top podcasts in a genre"""
    import urllib.parse
    url = '%s?term=podcast&media=podcast&entity=podcast&genreId=%s&limit=%s' % (
        ITUNES_SEARCH, genre_id, limit)
    data = client.request_json(url)
    if not data:
        return []
    return _parse_itunes_results(data.get('results', []))

def lookup_podcast(podcast_id):
    """Get podcast details by iTunes ID"""
    url = '%s?id=%s&entity=podcast' % (ITUNES_LOOKUP, podcast_id)
    data = client.request_json(url)
    if not data or not data.get('results'):
        return None
    r = data['results'][0]
    return {
        'id': str(r.get('trackId', '')),
        'name': r.get('trackName', '') or r.get('collectionName', ''),
        'artist': r.get('artistName', ''),
        'image': (r.get('artworkUrl600', '') or r.get('artworkUrl100', '')).replace('100x100', '600x600'),
        'genre': r.get('primaryGenreName', ''),
        'feed_url': r.get('feedUrl', ''),
        'description': r.get('description', '') or r.get('longDescription', ''),
        'episode_count': r.get('trackCount', 0),
    }

def get_episodes(feed_url, limit=50):
    """Parse podcast RSS feed to get episodes"""
    if not feed_url:
        return []
    xml_text = client.request(feed_url, timeout=20)
    if not xml_text:
        return []
    return _parse_rss(xml_text, limit)

def _parse_itunes_results(results):
    """Parse iTunes search results"""
    podcasts = []
    for r in results:
        feed_url = r.get('feedUrl', '')
        if not feed_url:
            continue
        podcasts.append({
            'id': str(r.get('trackId', '')),
            'name': r.get('trackName', '') or r.get('collectionName', ''),
            'artist': r.get('artistName', ''),
            'image': (r.get('artworkUrl600', '') or r.get('artworkUrl100', '')).replace('100x100', '600x600'),
            'genre': r.get('primaryGenreName', ''),
            'feed_url': feed_url,
            'episode_count': r.get('trackCount', 0),
        })
    return podcasts

def _parse_rss(xml_text, limit=50):
    """Parse RSS XML feed to extract podcast episodes"""
    episodes = []
    try:
        # Clean up common RSS issues
        xml_text = xml_text.strip()
        if xml_text.startswith('\xef\xbb\xbf'):
            xml_text = xml_text[3:]

        root = ET.fromstring(xml_text)
        channel = root.find('channel')
        if channel is None:
            return episodes

        ns = {
            'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
            'content': 'http://purl.org/rss/1.0/modules/content/',
        }

        for item in channel.findall('item')[:limit]:
            title = ''
            title_el = item.find('title')
            if title_el is not None and title_el.text:
                title = title_el.text.strip()

            audio_url = ''
            enclosure = item.find('enclosure')
            if enclosure is not None:
                audio_url = enclosure.get('url', '')

            if not audio_url:
                continue

            description = ''
            desc_el = item.find('description')
            if desc_el is not None and desc_el.text:
                description = re.sub(r'<[^>]+>', '', desc_el.text)[:500]

            pub_date = ''
            date_el = item.find('pubDate')
            if date_el is not None and date_el.text:
                pub_date = date_el.text.strip()[:16]

            duration = ''
            dur_el = item.find('itunes:duration', ns)
            if dur_el is not None and dur_el.text:
                duration = dur_el.text.strip()

            image = ''
            img_el = item.find('itunes:image', ns)
            if img_el is not None:
                image = img_el.get('href', '')

            episodes.append({
                'title': title,
                'url': audio_url,
                'description': description,
                'date': pub_date,
                'duration': duration,
                'image': image,
            })
    except ET.ParseError:
        control.log('RSS parse error for feed')
    except Exception as e:
        control.log('RSS error: %s' % e)

    return episodes
