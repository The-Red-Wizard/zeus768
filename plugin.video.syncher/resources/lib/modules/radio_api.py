# -*- coding: utf-8 -*-
"""Syncher - Radio Browser API for free live radio streams"""

from resources.lib.modules import client
from resources.lib.modules import control

RADIO_BASE = 'https://de1.api.radio-browser.info/json'

GENRE_TAGS = [
    {'tag': 'pop', 'name': 'Pop', 'color': 'gold'},
    {'tag': 'rock', 'name': 'Rock', 'color': 'red'},
    {'tag': 'hip hop', 'name': 'Hip-Hop', 'color': 'yellow'},
    {'tag': 'electronic', 'name': 'Electronic', 'color': 'cyan'},
    {'tag': 'jazz', 'name': 'Jazz', 'color': 'orange'},
    {'tag': 'classical', 'name': 'Classical', 'color': 'white'},
    {'tag': 'r&b', 'name': 'R&B / Soul', 'color': 'magenta'},
    {'tag': 'country', 'name': 'Country', 'color': 'lime'},
    {'tag': 'reggae', 'name': 'Reggae', 'color': 'green'},
    {'tag': 'metal', 'name': 'Metal', 'color': 'red'},
    {'tag': 'blues', 'name': 'Blues', 'color': 'skyblue'},
    {'tag': 'latin', 'name': 'Latin', 'color': 'orange'},
    {'tag': 'ambient', 'name': 'Ambient / Chill', 'color': 'violet'},
    {'tag': 'indie', 'name': 'Indie', 'color': 'skyblue'},
    {'tag': 'dance', 'name': 'Dance / EDM', 'color': 'lime'},
    {'tag': 'punk', 'name': 'Punk', 'color': 'red'},
    {'tag': 'funk', 'name': 'Funk', 'color': 'gold'},
    {'tag': 'lounge', 'name': 'Lounge', 'color': 'magenta'},
    {'tag': 'house', 'name': 'House', 'color': 'cyan'},
    {'tag': 'drum and bass', 'name': 'Drum & Bass', 'color': 'yellow'},
]

COUNTRY_LIST = [
    {'code': 'US', 'name': 'United States'},
    {'code': 'GB', 'name': 'United Kingdom'},
    {'code': 'DE', 'name': 'Germany'},
    {'code': 'FR', 'name': 'France'},
    {'code': 'BR', 'name': 'Brazil'},
    {'code': 'JP', 'name': 'Japan'},
    {'code': 'AU', 'name': 'Australia'},
    {'code': 'CA', 'name': 'Canada'},
    {'code': 'ES', 'name': 'Spain'},
    {'code': 'IT', 'name': 'Italy'},
    {'code': 'NL', 'name': 'Netherlands'},
    {'code': 'MX', 'name': 'Mexico'},
    {'code': 'SE', 'name': 'Sweden'},
    {'code': 'KR', 'name': 'South Korea'},
    {'code': 'IN', 'name': 'India'},
    {'code': 'RU', 'name': 'Russia'},
    {'code': 'NG', 'name': 'Nigeria'},
    {'code': 'ZA', 'name': 'South Africa'},
    {'code': 'JM', 'name': 'Jamaica'},
    {'code': 'IE', 'name': 'Ireland'},
]

def _headers():
    return {'User-Agent': 'Syncher/3.2.0 Kodi Addon'}

def get_top_stations(limit=50):
    """Get top voted radio stations"""
    data = client.request_json(
        RADIO_BASE + '/stations/topvote?limit=%s&hidebroken=true' % limit,
        headers=_headers())
    return _parse_stations(data) if data else []

def get_popular_stations(limit=50):
    """Get most clicked stations"""
    data = client.request_json(
        RADIO_BASE + '/stations/topclick?limit=%s&hidebroken=true' % limit,
        headers=_headers())
    return _parse_stations(data) if data else []

def get_trending_stations(limit=50):
    """Get trending stations (recently changed)"""
    data = client.request_json(
        RADIO_BASE + '/stations/lastchange?limit=%s&hidebroken=true' % limit,
        headers=_headers())
    return _parse_stations(data) if data else []

def search_by_tag(tag, limit=40):
    """Search stations by genre tag"""
    data = client.request_json(
        RADIO_BASE + '/stations/bytag/%s?limit=%s&hidebroken=true&order=votes&reverse=true' % (tag, limit),
        headers=_headers())
    return _parse_stations(data) if data else []

def search_by_country(country_code, limit=40):
    """Search stations by country code"""
    data = client.request_json(
        RADIO_BASE + '/stations/bycountrycodeexact/%s?limit=%s&hidebroken=true&order=votes&reverse=true' % (country_code, limit),
        headers=_headers())
    return _parse_stations(data) if data else []

def search_stations(query, limit=30):
    """Search stations by name"""
    data = client.request_json(
        RADIO_BASE + '/stations/byname/%s?limit=%s&hidebroken=true&order=votes&reverse=true' % (query, limit),
        headers=_headers())
    return _parse_stations(data) if data else []

def get_genre_tags():
    """Return pre-curated genre tags"""
    return GENRE_TAGS

def get_countries():
    """Return country list"""
    return COUNTRY_LIST

def _parse_stations(data):
    """Parse radio station data"""
    if not isinstance(data, list):
        return []
    stations = []
    for s in data:
        url = s.get('url_resolved') or s.get('url', '')
        if not url:
            continue
        name = s.get('name', '').strip()
        if not name:
            continue
        tags = s.get('tags', '')
        country = s.get('country', '')
        bitrate = s.get('bitrate', 0)
        codec = s.get('codec', '')
        votes = s.get('votes', 0)
        favicon = s.get('favicon', '')

        label_parts = [name]
        if country:
            label_parts.append(country)
        if bitrate:
            label_parts.append('%skbps' % bitrate)
        if codec:
            label_parts.append(codec)

        stations.append({
            'name': name,
            'url': url,
            'label': ' | '.join(label_parts),
            'icon': favicon,
            'country': country,
            'tags': tags,
            'bitrate': bitrate,
            'codec': codec,
            'votes': votes,
        })
    return stations
