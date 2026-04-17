# -*- coding: utf-8 -*-
"""Syncher - Local user playlists stored as JSON files"""

import os
import json
from resources.lib.modules import control

_PLAYLIST_DIR = None

def _get_dir():
    global _PLAYLIST_DIR
    if _PLAYLIST_DIR is None:
        _PLAYLIST_DIR = os.path.join(control.addonProfile(), 'playlists')
        os.makedirs(_PLAYLIST_DIR, exist_ok=True)
    return _PLAYLIST_DIR

def get_all():
    """Get all user playlists"""
    playlists = []
    d = _get_dir()
    for f in sorted(os.listdir(d)):
        if f.endswith('.json'):
            try:
                with open(os.path.join(d, f), 'r') as fh:
                    data = json.load(fh)
                    playlists.append(data)
            except:
                pass
    return playlists

def get(playlist_id):
    """Get a single playlist"""
    path = os.path.join(_get_dir(), '%s.json' % playlist_id)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

def create(name):
    """Create a new empty playlist"""
    import hashlib, time
    pid = hashlib.md5(('%s%s' % (name, time.time())).encode()).hexdigest()[:12]
    data = {
        'id': pid,
        'name': name,
        'tracks': [],
    }
    path = os.path.join(_get_dir(), '%s.json' % pid)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    return data

def add_track(playlist_id, track):
    """Add a track to a playlist"""
    data = get(playlist_id)
    if not data:
        return False
    # Avoid duplicates
    existing_ids = [t.get('id') for t in data['tracks']]
    if track.get('id') in existing_ids:
        return False
    data['tracks'].append(track)
    path = os.path.join(_get_dir(), '%s.json' % playlist_id)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    return True

def remove_track(playlist_id, track_index):
    """Remove a track by index"""
    data = get(playlist_id)
    if not data:
        return False
    try:
        data['tracks'].pop(int(track_index))
        path = os.path.join(_get_dir(), '%s.json' % playlist_id)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except:
        return False

def delete(playlist_id):
    """Delete a playlist"""
    path = os.path.join(_get_dir(), '%s.json' % playlist_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False

def _save(playlist_id, data):
    """Save playlist data directly"""
    path = os.path.join(_get_dir(), '%s.json' % playlist_id)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
