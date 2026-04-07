# -*- coding: utf-8 -*-
"""Syncher - Deezer API for music browsing and metadata"""

from resources.lib.modules import control
from resources.lib.modules import client

DEEZER_BASE = 'https://api.deezer.com'

def get_genres():
    """Get all music genres"""
    data = client.request_json(DEEZER_BASE + '/genre')
    if not data:
        return []
    genres = []
    for g in data.get('data', []):
        if g['id'] == 0:
            continue
        genres.append({
            'id': str(g['id']),
            'name': g['name'],
            'image': g.get('picture_medium', '') or g.get('picture', ''),
        })
    return genres

def get_genre_artists(genre_id, limit=40):
    """Get artists for a genre"""
    data = client.request_json(DEEZER_BASE + '/genre/%s/artists?limit=%s' % (genre_id, limit))
    if not data:
        return []
    return _parse_artists(data.get('data', []))

def get_chart_tracks(limit=50):
    """Get current chart tracks"""
    data = client.request_json(DEEZER_BASE + '/chart/0/tracks?limit=%s' % limit)
    if not data:
        return []
    return _parse_tracks(data.get('data', []))

def get_chart_albums(limit=50):
    """Get current chart albums"""
    data = client.request_json(DEEZER_BASE + '/chart/0/albums?limit=%s' % limit)
    if not data:
        return []
    return _parse_albums(data.get('data', []))

def get_chart_artists(limit=50):
    """Get current chart artists"""
    data = client.request_json(DEEZER_BASE + '/chart/0/artists?limit=%s' % limit)
    if not data:
        return []
    return _parse_artists(data.get('data', []))

def get_chart_playlists(limit=50):
    """Get editorial/chart playlists"""
    data = client.request_json(DEEZER_BASE + '/chart/0/playlists?limit=%s' % limit)
    if not data:
        return []
    return _parse_playlists(data.get('data', []))

def get_editorial_releases(limit=50):
    """Get new releases via editorial"""
    data = client.request_json(DEEZER_BASE + '/editorial/0/releases?limit=%s' % limit)
    if not data:
        # Fallback to chart albums
        return get_chart_albums(limit)
    return _parse_albums(data.get('data', []))

def search_artist(query, limit=30):
    """Search for artists"""
    data = client.request_json(DEEZER_BASE + '/search/artist?q=%s&limit=%s' % (query, limit))
    if not data:
        return []
    return _parse_artists(data.get('data', []))

def search_album(query, limit=30):
    """Search for albums"""
    data = client.request_json(DEEZER_BASE + '/search/album?q=%s&limit=%s' % (query, limit))
    if not data:
        return []
    return _parse_albums(data.get('data', []))

def search_track(query, limit=30):
    """Search for tracks"""
    data = client.request_json(DEEZER_BASE + '/search/track?q=%s&limit=%s' % (query, limit))
    if not data:
        return []
    return _parse_tracks(data.get('data', []))

def get_artist(artist_id):
    """Get artist details"""
    data = client.request_json(DEEZER_BASE + '/artist/%s' % artist_id)
    if not data:
        return None
    return {
        'id': str(data['id']),
        'name': data.get('name', ''),
        'image': data.get('picture_xl', '') or data.get('picture_big', '') or data.get('picture_medium', ''),
        'fans': str(data.get('nb_fan', 0)),
        'albums': str(data.get('nb_album', 0)),
    }

def get_artist_top(artist_id, limit=20):
    """Get artist's top tracks"""
    data = client.request_json(DEEZER_BASE + '/artist/%s/top?limit=%s' % (artist_id, limit))
    if not data:
        return []
    return _parse_tracks(data.get('data', []))

def get_artist_albums(artist_id, limit=50):
    """Get artist's albums"""
    data = client.request_json(DEEZER_BASE + '/artist/%s/albums?limit=%s' % (artist_id, limit))
    if not data:
        return []
    return _parse_albums(data.get('data', []))

def get_artist_related(artist_id, limit=20):
    """Get related artists"""
    data = client.request_json(DEEZER_BASE + '/artist/%s/related?limit=%s' % (artist_id, limit))
    if not data:
        return []
    return _parse_artists(data.get('data', []))

def get_album(album_id):
    """Get album details"""
    data = client.request_json(DEEZER_BASE + '/album/%s' % album_id)
    if not data:
        return None
    return {
        'id': str(data['id']),
        'title': data.get('title', ''),
        'artist': data.get('artist', {}).get('name', ''),
        'artist_id': str(data.get('artist', {}).get('id', '0')),
        'image': data.get('cover_xl', '') or data.get('cover_big', '') or data.get('cover_medium', ''),
        'tracks': str(data.get('nb_tracks', 0)),
        'duration': str(data.get('duration', 0)),
        'release_date': data.get('release_date', ''),
        'genre': data.get('genres', {}).get('data', [{}])[0].get('name', '') if data.get('genres', {}).get('data') else '',
        'label': data.get('label', ''),
    }

def get_album_tracks(album_id):
    """Get all tracks in an album"""
    data = client.request_json(DEEZER_BASE + '/album/%s/tracks?limit=100' % album_id)
    if not data:
        return []
    return _parse_tracks(data.get('data', []))

def get_playlist_tracks(playlist_id):
    """Get all tracks in a playlist"""
    data = client.request_json(DEEZER_BASE + '/playlist/%s/tracks?limit=200' % playlist_id)
    if not data:
        return []
    return _parse_tracks(data.get('data', []))

# ============================================================
# PARSERS
# ============================================================

def _parse_artists(items):
    artists = []
    for a in items:
        artists.append({
            'id': str(a['id']),
            'name': a.get('name', ''),
            'image': a.get('picture_xl', '') or a.get('picture_big', '') or a.get('picture_medium', '') or a.get('picture', ''),
            'fans': str(a.get('nb_fan', 0)),
        })
    return artists

def _parse_albums(items):
    albums = []
    for a in items:
        artist_name = ''
        if isinstance(a.get('artist'), dict):
            artist_name = a['artist'].get('name', '')
        albums.append({
            'id': str(a['id']),
            'title': a.get('title', ''),
            'artist': artist_name,
            'artist_id': str(a.get('artist', {}).get('id', '0')) if isinstance(a.get('artist'), dict) else '0',
            'image': a.get('cover_xl', '') or a.get('cover_big', '') or a.get('cover_medium', '') or a.get('cover', ''),
            'tracks': str(a.get('nb_tracks', 0)),
            'release_date': a.get('release_date', ''),
        })
    return albums

def _parse_tracks(items):
    tracks = []
    for t in items:
        artist_name = ''
        if isinstance(t.get('artist'), dict):
            artist_name = t['artist'].get('name', '')
        album_title = ''
        album_id = '0'
        album_cover = ''
        if isinstance(t.get('album'), dict):
            album_title = t['album'].get('title', '')
            album_id = str(t['album'].get('id', '0'))
            album_cover = t['album'].get('cover_medium', '') or t['album'].get('cover', '')
        tracks.append({
            'id': str(t['id']),
            'title': t.get('title', ''),
            'artist': artist_name,
            'artist_id': str(t.get('artist', {}).get('id', '0')) if isinstance(t.get('artist'), dict) else '0',
            'album': album_title,
            'album_id': album_id,
            'image': album_cover,
            'duration': str(t.get('duration', 0)),
            'track_position': str(t.get('track_position', 0)),
            'rank': str(t.get('rank', 0)),
        })
    return tracks

def _parse_playlists(items):
    playlists = []
    for p in items:
        playlists.append({
            'id': str(p['id']),
            'title': p.get('title', ''),
            'image': p.get('picture_xl', '') or p.get('picture_big', '') or p.get('picture_medium', '') or p.get('picture', ''),
            'tracks': str(p.get('nb_tracks', 0)),
            'description': p.get('description', ''),
        })
    return playlists
