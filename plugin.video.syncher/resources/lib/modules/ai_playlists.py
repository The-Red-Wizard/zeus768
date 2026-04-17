# -*- coding: utf-8 -*-
"""Syncher - AI Playlist Generator powered by Emergent Universal Key
Generates daily themed playlists using GPT, looks up tracks on Deezer.
"""

import os
import json
import hashlib
import datetime
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.modules import deezer_api

PROXY_URL = 'https://integrations.emergentagent.com/llm'

# Daily playlist themes - rotates based on day of week + week number
DAILY_THEMES = [
    {'name': 'Daily Discovery', 'prompt': 'Create a diverse discovery playlist of 15 songs mixing different genres that a music lover would enjoy discovering today. Mix well-known and lesser-known tracks.', 'color': 'gold'},
    {'name': 'Chill Vibes', 'prompt': 'Create a chill, relaxing playlist of 15 songs perfect for unwinding. Include lo-fi, ambient, soft electronic, and mellow indie tracks.', 'color': 'cyan'},
    {'name': 'Throwback Classics', 'prompt': 'Create a nostalgic throwback playlist of 15 classic songs from the 80s, 90s, and early 2000s across pop, rock, R&B, and hip-hop.', 'color': 'orange'},
    {'name': 'Workout Energy', 'prompt': 'Create a high-energy workout playlist of 15 songs with strong beats, perfect for running or gym sessions. Mix EDM, hip-hop, pop, and rock bangers.', 'color': 'red'},
    {'name': 'Late Night Grooves', 'prompt': 'Create a late night playlist of 15 smooth, moody songs for after midnight. Include R&B, neo-soul, jazz-hop, and downtempo electronic.', 'color': 'magenta'},
    {'name': 'Feel Good Anthems', 'prompt': 'Create an uplifting feel-good playlist of 15 happy, positive songs that make you smile. Mix pop, funk, soul, and indie pop.', 'color': 'lime'},
    {'name': 'Indie Underground', 'prompt': 'Create an indie underground playlist of 15 songs from indie rock, indie pop, indie folk, and alternative artists. Focus on critically acclaimed but not mainstream tracks.', 'color': 'skyblue'},
    {'name': 'Hip-Hop Essentials', 'prompt': 'Create a hip-hop playlist of 15 songs mixing classic and modern hip-hop/rap. Include lyrical tracks, bangers, and conscious rap.', 'color': 'yellow'},
    {'name': 'Electronic Dreams', 'prompt': 'Create an electronic music playlist of 15 songs spanning house, techno, synthwave, ambient, and IDM. Mix dance floor tracks with headphone listening.', 'color': 'violet'},
    {'name': 'Acoustic Sessions', 'prompt': 'Create an acoustic playlist of 15 stripped-back, acoustic songs. Include singer-songwriter, folk, unplugged versions, and acoustic covers.', 'color': 'white'},
    {'name': 'World Music Journey', 'prompt': 'Create a world music playlist of 15 songs from different countries and cultures. Include Latin, African, Asian, Middle Eastern, and European music.', 'color': 'gold'},
    {'name': 'Rock Revival', 'prompt': 'Create a rock playlist of 15 songs spanning classic rock, alternative, punk, grunge, and modern rock. Mix legendary and contemporary artists.', 'color': 'red'},
    {'name': 'Jazz & Soul Cafe', 'prompt': 'Create a jazz and soul playlist of 15 songs perfect for a coffee shop atmosphere. Include classic jazz, modern jazz, neo-soul, and smooth grooves.', 'color': 'orange'},
    {'name': 'Party Starters', 'prompt': 'Create a party playlist of 15 high-energy dance songs. Include pop hits, EDM bangers, Latin party tracks, and singalong anthems.', 'color': 'lime'},
]

# Mood-based themes for "Similar To..." feature
MOOD_THEMES = {
    'happy': 'upbeat, joyful, feel-good songs that make you dance and smile',
    'sad': 'melancholic, emotional, bittersweet songs for when you are feeling down',
    'chill': 'relaxed, mellow, laid-back songs perfect for unwinding',
    'party': 'high-energy, danceable party anthems and club bangers',
    'focus': 'ambient, instrumental, minimal songs ideal for concentration and study',
    'workout': 'intense, high-BPM, motivating songs for exercise and sports',
    'romantic': 'love songs, romantic ballads, and tender duets',
    'angry': 'aggressive, intense, heavy songs for letting off steam',
    'nostalgic': 'throwback songs that bring back memories from past decades',
    'sleepy': 'soft, gentle, dreamy songs perfect for falling asleep',
}

def _get_api_key():
    """Get the Emergent API key from addon settings"""
    key = control.setting('emergent_key')
    if key:
        return key
    return ''

def _get_cache_dir():
    """Get the AI playlist cache directory"""
    d = os.path.join(control.addonProfile(), 'ai_cache')
    os.makedirs(d, exist_ok=True)
    return d

def _cache_key(name):
    """Generate a daily cache key"""
    today = datetime.date.today().isoformat()
    return hashlib.md5(('%s_%s' % (name, today)).encode()).hexdigest()[:16]

def _load_cache(name):
    """Load cached playlist if from today"""
    cache_file = os.path.join(_get_cache_dir(), '%s.json' % _cache_key(name))
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return None

def _save_cache(name, data):
    """Save playlist to daily cache"""
    cache_file = os.path.join(_get_cache_dir(), '%s.json' % _cache_key(name))
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass

def _call_gpt(prompt, system_msg='You are a music curator AI. Return ONLY valid JSON arrays with no markdown formatting.'):
    """Call GPT via Emergent proxy and return parsed JSON"""
    api_key = _get_api_key()
    if not api_key:
        return None

    import requests
    try:
        payload = {
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': system_msg},
                {'role': 'user', 'content': prompt},
            ],
            'temperature': 0.95,
            'max_tokens': 1200,
        }

        r = requests.post(PROXY_URL + '/chat/completions',
            headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'},
            json=payload, timeout=30)

        if r.status_code != 200:
            control.log('AI API error: %s' % r.status_code)
            return None

        data = r.json()
        content = data['choices'][0]['message']['content']

        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1] if '\n' in content else content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

        return json.loads(content)
    except Exception as e:
        control.log('AI call error: %s' % e)
        return None

def _lookup_tracks_on_deezer(ai_tracks):
    """Look up AI-suggested tracks on Deezer for metadata and artwork"""
    deezer_tracks = []
    for t in ai_tracks:
        query = '%s %s' % (t.get('artist', ''), t.get('title', ''))
        results = deezer_api.search_track(query.strip(), limit=1)
        if results:
            deezer_tracks.append(results[0])
        else:
            # Create a basic entry even if not found on Deezer
            deezer_tracks.append({
                'id': '0',
                'title': t.get('title', 'Unknown'),
                'artist': t.get('artist', 'Unknown'),
                'album': '',
                'album_id': '0',
                'image': '',
                'duration': '0',
                'track_position': '0',
                'rank': '0',
            })
    return deezer_tracks

def get_daily_playlists():
    """Get today's AI playlist themes"""
    today = datetime.date.today()
    day_of_year = today.timetuple().tm_yday
    # Rotate through themes - show 6 per day
    start = (day_of_year * 3) % len(DAILY_THEMES)
    playlists = []
    for i in range(6):
        idx = (start + i) % len(DAILY_THEMES)
        theme = DAILY_THEMES[idx]
        playlists.append({
            'name': theme['name'],
            'color': theme['color'],
            'index': idx,
        })
    return playlists

def get_daily_playlist_tracks(theme_index):
    """Generate or load a daily AI playlist"""
    theme = DAILY_THEMES[int(theme_index)]

    # Check cache first
    cached = _load_cache('daily_%s' % theme_index)
    if cached:
        return cached

    # Generate via AI
    today = datetime.date.today()
    day_name = today.strftime('%A')
    prompt = '%s Today is %s, %s. Return a JSON array of objects with keys: title, artist. No explanations.' % (
        theme['prompt'], day_name, today.isoformat())

    ai_tracks = _call_gpt(prompt)
    if not ai_tracks:
        return []

    # Look up on Deezer
    tracks = _lookup_tracks_on_deezer(ai_tracks)

    # Cache
    _save_cache('daily_%s' % theme_index, tracks)
    return tracks

def get_mood_playlist(mood):
    """Generate a mood-based playlist"""
    cached = _load_cache('mood_%s' % mood)
    if cached:
        return cached

    description = MOOD_THEMES.get(mood, mood)
    prompt = 'Create a playlist of 15 songs that are %s. Return a JSON array of objects with keys: title, artist. No explanations.' % description

    ai_tracks = _call_gpt(prompt)
    if not ai_tracks:
        return []

    tracks = _lookup_tracks_on_deezer(ai_tracks)
    _save_cache('mood_%s' % mood, tracks)
    return tracks

def get_similar_artist_playlist(artist_name):
    """Generate a playlist of songs similar to a given artist"""
    cached = _load_cache('similar_%s' % artist_name.lower().replace(' ', '_')[:20])
    if cached:
        return cached

    prompt = 'Create a playlist of 15 songs that fans of %s would love. Include tracks from similar artists and the same musical style, but DO NOT include any songs by %s themselves. Return a JSON array of objects with keys: title, artist. No explanations.' % (artist_name, artist_name)

    ai_tracks = _call_gpt(prompt)
    if not ai_tracks:
        return []

    tracks = _lookup_tracks_on_deezer(ai_tracks)
    _save_cache('similar_%s' % artist_name.lower().replace(' ', '_')[:20], tracks)
    return tracks

def get_decade_playlist(decade):
    """Generate a best-of playlist for a specific decade"""
    cached = _load_cache('decade_%s' % decade)
    if cached:
        return cached

    prompt = 'Create a playlist of 20 of the best and most iconic songs from the %s across all genres. Return a JSON array of objects with keys: title, artist. No explanations.' % decade

    ai_tracks = _call_gpt(prompt)
    if not ai_tracks:
        return []

    tracks = _lookup_tracks_on_deezer(ai_tracks)
    _save_cache('decade_%s' % decade, tracks)
    return tracks

def get_mood_list():
    """Return available moods"""
    return [
        {'id': 'happy', 'name': 'Happy & Upbeat', 'color': 'gold'},
        {'id': 'sad', 'name': 'Sad & Emotional', 'color': 'skyblue'},
        {'id': 'chill', 'name': 'Chill & Relaxed', 'color': 'cyan'},
        {'id': 'party', 'name': 'Party & Dance', 'color': 'lime'},
        {'id': 'focus', 'name': 'Focus & Study', 'color': 'white'},
        {'id': 'workout', 'name': 'Workout & Energy', 'color': 'red'},
        {'id': 'romantic', 'name': 'Romantic & Love', 'color': 'magenta'},
        {'id': 'angry', 'name': 'Angry & Intense', 'color': 'red'},
        {'id': 'nostalgic', 'name': 'Nostalgic & Throwback', 'color': 'orange'},
        {'id': 'sleepy', 'name': 'Sleepy & Dreamy', 'color': 'violet'},
    ]

def get_decade_list():
    """Return available decades"""
    return [
        {'id': '1960s', 'name': '1960s - The Swinging Sixties', 'color': 'orange'},
        {'id': '1970s', 'name': '1970s - Disco & Punk', 'color': 'gold'},
        {'id': '1980s', 'name': '1980s - Synthpop & New Wave', 'color': 'magenta'},
        {'id': '1990s', 'name': '1990s - Grunge & Hip-Hop', 'color': 'lime'},
        {'id': '2000s', 'name': '2000s - Pop & R&B Golden Era', 'color': 'cyan'},
        {'id': '2010s', 'name': '2010s - Streaming Revolution', 'color': 'skyblue'},
        {'id': '2020s', 'name': '2020s - Current Hits', 'color': 'gold'},
    ]
