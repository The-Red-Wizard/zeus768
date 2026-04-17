# -*- coding: utf-8 -*-
"""Syncher - Audiobook browsing via LibriVox API + Internet Archive"""

from resources.lib.modules import client
from resources.lib.modules import control

LIBRIVOX_BASE = 'https://librivox.org/api/feed'
ARCHIVE_SEARCH = 'https://archive.org/advancedsearch.php'
ARCHIVE_META = 'https://archive.org/metadata'
ARCHIVE_DL = 'https://archive.org/download'

AUDIOBOOK_GENRES = [
    'Adventure', 'Biography', 'Children', 'Classic',
    'Comedy', 'Crime', 'Drama', 'Fantasy',
    'Fiction', 'Historical', 'Horror', 'Humor',
    'Mystery', 'Non-fiction', 'Philosophy', 'Poetry',
    'Romance', 'Science Fiction', 'Short Stories', 'Thriller',
]

def search_librivox(query, limit=30):
    """Search LibriVox audiobooks by title"""
    import urllib.parse
    url = '%s/audiobooks?title=%s&format=json&limit=%s&coverart=1' % (
        LIBRIVOX_BASE, urllib.parse.quote(query), limit)
    data = client.request_json(url)
    if not data:
        return []
    return _parse_librivox_books(data.get('books', []))

def search_librivox_author(query, limit=30):
    """Search LibriVox audiobooks by author"""
    import urllib.parse
    url = '%s/audiobooks?author=%s&format=json&limit=%s&coverart=1' % (
        LIBRIVOX_BASE, urllib.parse.quote(query), limit)
    data = client.request_json(url)
    if not data:
        return []
    return _parse_librivox_books(data.get('books', []))

def get_recent_librivox(limit=50):
    """Get recently cataloged LibriVox audiobooks"""
    import time
    since = int(time.time()) - (30 * 86400)  # Last 30 days
    url = '%s/audiobooks?since=%s&format=json&limit=%s&coverart=1' % (
        LIBRIVOX_BASE, since, limit)
    data = client.request_json(url)
    if not data:
        return []
    return _parse_librivox_books(data.get('books', []))

def get_librivox_by_genre(genre, limit=30):
    """Get LibriVox audiobooks by genre"""
    import urllib.parse
    url = '%s/audiobooks?genre=%s&format=json&limit=%s&coverart=1' % (
        LIBRIVOX_BASE, urllib.parse.quote(genre), limit)
    data = client.request_json(url)
    if not data:
        return []
    return _parse_librivox_books(data.get('books', []))

def get_librivox_tracks(book_id):
    """Get chapters/tracks for a LibriVox audiobook"""
    url = '%s/audiotracks?project_id=%s&format=json' % (LIBRIVOX_BASE, book_id)
    data = client.request_json(url)
    if not data:
        return []
    sections = data.get('sections', [])
    tracks = []
    for s in sections:
        title = s.get('title', 'Chapter %s' % s.get('section_number', '?'))
        listen_url = s.get('listen_url', '')
        if not listen_url:
            continue
        duration = s.get('playtime', '0:00:00')
        tracks.append({
            'title': title,
            'url': listen_url,
            'duration': duration,
            'section': s.get('section_number', '0'),
            'reader': s.get('readers', [{}])[0].get('display_name', '') if s.get('readers') else '',
        })
    return tracks

def search_archive(query, limit=30):
    """Search Internet Archive for audiobooks"""
    import urllib.parse
    url = '%s?q=%s+AND+mediatype:(audio)+AND+collection:(librivoxaudio+OR+audio_bookspoetry)&fl[]=identifier,title,creator,description,downloads&rows=%s&output=json&sort[]=downloads+desc' % (
        ARCHIVE_SEARCH, urllib.parse.quote(query), limit)
    data = client.request_json(url)
    if not data:
        return []
    response = data.get('response', {})
    docs = response.get('docs', [])
    books = []
    for d in docs:
        identifier = d.get('identifier', '')
        if not identifier:
            continue
        books.append({
            'id': identifier,
            'title': d.get('title', ''),
            'author': d.get('creator', ['Unknown'])[0] if isinstance(d.get('creator'), list) else d.get('creator', 'Unknown'),
            'description': (d.get('description', [''])[0] if isinstance(d.get('description'), list) else d.get('description', ''))[:300],
            'image': 'https://archive.org/services/img/%s' % identifier,
            'downloads': d.get('downloads', 0),
            'source': 'archive',
        })
    return books

def get_archive_tracks(identifier):
    """Get audio files from an Internet Archive item"""
    url = '%s/%s' % (ARCHIVE_META, identifier)
    data = client.request_json(url)
    if not data:
        return []
    files = data.get('files', [])
    tracks = []
    seen = set()
    for f in files:
        name = f.get('name', '')
        fmt = f.get('format', '')
        # Match MP3 formats from Internet Archive
        if fmt not in ('VBR MP3', '128Kbps MP3', '64Kbps MP3', 'Ogg Vorbis') and not name.lower().endswith('.mp3'):
            continue
        # Prefer VBR MP3, skip 64kb duplicates if VBR exists
        base_name = name.rsplit('.', 1)[0].replace('_64kb', '')
        if '64kb' in name and base_name in seen:
            continue
        if '64kb' not in name:
            seen.add(name.rsplit('.', 1)[0])

        title = f.get('title', '') or name.replace('.mp3', '').replace('.ogg', '').replace('_', ' ')
        duration = f.get('length', '0')
        audio_url = '%s/%s/%s' % (ARCHIVE_DL, identifier, name)
        tracks.append({
            'title': title,
            'url': audio_url,
            'duration': duration,
            'format': fmt,
        })
    return tracks

def get_genres():
    return AUDIOBOOK_GENRES

def _parse_librivox_books(books):
    """Parse LibriVox book results"""
    result = []
    for b in books:
        book_id = b.get('id', '')
        if not book_id:
            continue
        title = b.get('title', '')
        authors = b.get('authors', [])
        author_name = ''
        if authors:
            a = authors[0]
            author_name = ('%s %s' % (a.get('first_name', ''), a.get('last_name', ''))).strip()

        # Get cover art URL
        url_librivox = b.get('url_librivox', '')
        image = ''
        if url_librivox:
            # LibriVox cover art pattern
            image = 'https://archive.org/services/img/librivox_%s' % book_id

        total_time = b.get('totaltime', '')
        num_sections = b.get('num_sections', '0')
        description = b.get('description', '')[:300]
        # Strip HTML
        import re
        description = re.sub(r'<[^>]+>', '', description)

        result.append({
            'id': str(book_id),
            'title': title,
            'author': author_name,
            'image': image,
            'duration': total_time,
            'chapters': num_sections,
            'description': description,
            'language': b.get('language', 'English'),
            'source': 'librivox',
        })
    return result
