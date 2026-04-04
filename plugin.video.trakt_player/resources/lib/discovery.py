# -*- coding: utf-8 -*-
"""Trakt Discovery - AI-powered movie marathons based on mood + watch history."""
import json
import ssl
import urllib.request
import urllib.error
from urllib.parse import quote_plus
import xbmc
import xbmcgui
import os
import xbmcplugin
import xbmcaddon
import sys
from . import trakt_auth, tmdb

ADDON = xbmcaddon.Addon()
SSL_CTX = ssl._create_unverified_context()
FANART = os.path.join(ADDON.getAddonInfo('path'), 'fanart.jpg')
ICON = os.path.join(ADDON.getAddonInfo('path'), 'icon.png')

LLM_URL = 'https://integrations.emergentagent.com/llm/v1/chat/completions'
LLM_KEY = 'sk-emergent-4Ed53090b4b04F8606'
CLIENT_ID = trakt_auth.CLIENT_ID


def _handle():
    try:
        return int(sys.argv[1])
    except (IndexError, ValueError):
        return -1


def _trakt_get(url):
    h = {
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': CLIENT_ID,
        'User-Agent': 'Kodi TraktPlayer/2.1.0'
    }
    token = trakt_auth.get_token()
    if token:
        h['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception:
        return []


def _llm_chat(prompt):
    """Call Emergent LLM proxy for AI recommendations."""
    body = json.dumps({
        'model': 'gpt-4o-mini',
        'messages': [
            {'role': 'system', 'content': 'You are a movie/TV recommendation engine. Return ONLY a JSON array of objects with keys: title, year, type (movie or show). No markdown, no explanation. Return 10-15 items.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.9,
        'max_tokens': 1500
    }).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer %s' % LLM_KEY
    }
    req = urllib.request.Request(LLM_URL, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '[]')
            # Parse JSON from response (handle markdown code blocks)
            content = content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            return json.loads(content)
    except Exception as e:
        xbmc.log('Discovery LLM error: %s' % str(e), xbmc.LOGERROR)
        return []


def _get_watch_history_context():
    """Get recent watch history to give AI context about user's taste."""
    if not trakt_auth.is_authorized():
        return ''
    # Fetch recent movie history
    movies = _trakt_get('https://api.trakt.tv/sync/history/movies?limit=20')
    shows = _trakt_get('https://api.trakt.tv/sync/history/shows?limit=10')

    titles = []
    for item in (movies or []):
        m = item.get('movie', {})
        if m.get('title'):
            titles.append('%s (%s)' % (m['title'], m.get('year', '')))
    for item in (shows or []):
        s = item.get('show', {})
        if s.get('title'):
            titles.append('%s (TV)' % s['title'])

    if titles:
        return 'The user recently watched: %s.' % ', '.join(titles[:15])
    return ''


def _search_trakt_for_title(title, year, media_type='movie'):
    """Search Trakt for a specific title to get IDs."""
    endpoint = 'movie' if media_type == 'movie' else 'show'
    url = 'https://api.trakt.tv/search/%s?query=%s&extended=full&limit=3' % (endpoint, quote_plus(title))
    data = _trakt_get(url)
    if data:
        for item in data:
            content = item.get(endpoint, {})
            if year and str(content.get('year', '')) == str(year):
                return content
            elif content.get('title', '').lower() == title.lower():
                return content
        # Fallback to first result
        return data[0].get(endpoint, {})
    return None


def vibe_discovery():
    """User describes a mood/vibe -> AI picks movies -> instant marathon."""
    if not trakt_auth.is_authorized():
        xbmcgui.Dialog().notification('Trakt', 'Please authorize Trakt first', xbmcgui.NOTIFICATION_WARNING)
        return

    kb = xbmc.Keyboard('', 'Describe your vibe (e.g. "rainy night thriller", "feel-good 90s nostalgia")')
    kb.doModal()
    if not kb.isConfirmed():
        return
    vibe = kb.getText().strip()
    if not vibe:
        return

    progress = xbmcgui.DialogProgress()
    progress.create('Trakt Discovery', 'AI is picking movies for your vibe: "%s"...' % vibe)

    history_ctx = _get_watch_history_context()
    prompt = 'Recommend 12-15 movies and/or TV shows for this vibe: "%s". %s Mix well-known and hidden gems. Variety in decades. Return JSON array with title, year, type.' % (vibe, history_ctx)

    progress.update(30, 'Asking AI for recommendations...')
    results = _llm_chat(prompt)

    if not results:
        progress.close()
        xbmcgui.Dialog().notification('Discovery', 'AI returned no results. Try another vibe.', xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(_handle())
        return

    progress.update(60, 'Found %d picks. Loading metadata...' % len(results))

    count = 0
    for i, item in enumerate(results):
        if progress.iscanceled():
            break
        title = item.get('title', '')
        year = item.get('year', '')
        media_type = item.get('type', 'movie')
        if not title:
            continue

        pct = 60 + int((i / len(results)) * 35)
        progress.update(pct, 'Loading: %s...' % title)

        # Search Trakt for the title to get proper IDs
        content = _search_trakt_for_title(title, year, media_type)
        if not content:
            continue

        ids = content.get('ids', {})
        tmdb_id = ids.get('tmdb')
        imdb_id = ids.get('imdb', '')
        actual_title = content.get('title', title)
        actual_year = content.get('year', year)

        meta = tmdb.get_details(tmdb_id, 'movie' if media_type == 'movie' else 'tv')
        label = '%s (%s)' % (actual_title, actual_year) if actual_year else actual_title

        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': meta.get('poster', ''),
            'fanart': FANART,
            'thumb': meta.get('poster', ''),
            'icon': ICON
        })
        li.setInfo('video', {
            'title': actual_title, 'year': actual_year,
            'plot': meta.get('overview', content.get('overview', '')),
            'rating': meta.get('rating', 0),
            'genre': ', '.join(meta.get('genres', []))
        })

        if media_type == 'movie':
            li.setInfo('video', {'mediatype': 'movie'})
            li.setProperty('IsPlayable', 'true')
            url = '%s?action=play&title=%s&year=%s&imdb_id=%s' % (
                sys.argv[0], quote_plus(actual_title), actual_year, imdb_id)
            xbmcplugin.addDirectoryItem(_handle(), url, li, False)
        else:
            li.setInfo('video', {'mediatype': 'tvshow'})
            url = '%s?action=show_seasons&tmdb_id=%s&title=%s' % (
                sys.argv[0], tmdb_id, quote_plus(actual_title))
            xbmcplugin.addDirectoryItem(_handle(), url, li, True)
        count += 1

    progress.close()
    if count > 0:
        xbmcgui.Dialog().notification('Discovery', 'Vibe: "%s" - %d picks loaded' % (vibe, count), xbmcgui.NOTIFICATION_INFO, 3000)
    xbmcplugin.setContent(_handle(), 'videos')
    xbmcplugin.endOfDirectory(_handle())


def mood_presets():
    """Show preset mood/vibe options."""
    presets = [
        ('Rainy Night Thriller', 'dark atmospheric thriller, tension, mystery'),
        ('Feel-Good 90s Nostalgia', 'uplifting 90s movies, nostalgia, comfort'),
        ('Mind-Bending Sci-Fi', 'mind-bending sci-fi, reality warping, cerebral'),
        ('Epic Adventure', 'epic adventure, journey, grand scale action'),
        ('Late Night Comedy', 'hilarious comedy, absurd humor, quotable'),
        ('Romantic Evening', 'romantic drama, love story, emotional'),
        ('Horror Marathon', 'terrifying horror, psychological, disturbing'),
        ('Documentary Deep Dive', 'fascinating documentaries, true crime, nature, science'),
        ('Anime Binge', 'best anime series and movies, action, emotional, artistic'),
        ('Cult Classics', 'cult classic, underrated, weird, unique cinema'),
        ('Adrenaline Rush', 'high octane action, chase scenes, explosions, stunts'),
        ('Cozy Sunday', 'warm family-friendly, wholesome, heartwarming'),
        ('Custom Vibe...', ''),
    ]
    for label, vibe in presets:
        if vibe:
            url = '%s?action=vibe_play&vibe=%s' % (sys.argv[0], quote_plus(vibe))
        else:
            url = '%s?action=vibe_custom' % sys.argv[0]
        li = xbmcgui.ListItem(label=label)
        li.setArt({'fanart': FANART, 'icon': ICON, 'thumb': ICON})
        xbmcplugin.addDirectoryItem(_handle(), url, li, isFolder=True)
    xbmcplugin.endOfDirectory(_handle())


def vibe_play(vibe):
    """Run AI discovery with a preset or custom vibe string."""
    if not trakt_auth.is_authorized():
        xbmcgui.Dialog().notification('Trakt', 'Please authorize Trakt first', xbmcgui.NOTIFICATION_WARNING)
        return

    progress = xbmcgui.DialogProgress()
    progress.create('Trakt Discovery', 'AI is curating your marathon: "%s"...' % vibe)

    history_ctx = _get_watch_history_context()
    prompt = 'Recommend 12-15 movies and/or TV shows for this mood: "%s". %s Mix well-known and hidden gems. Variety in decades. Return JSON array with title, year, type.' % (vibe, history_ctx)

    progress.update(30, 'Asking AI...')
    results = _llm_chat(prompt)

    if not results:
        progress.close()
        xbmcgui.Dialog().notification('Discovery', 'No results. Try another vibe.', xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(_handle())
        return

    progress.update(60, 'Loading %d picks...' % len(results))

    count = 0
    for i, item in enumerate(results):
        if progress.iscanceled():
            break
        title = item.get('title', '')
        year = item.get('year', '')
        media_type = item.get('type', 'movie')
        if not title:
            continue

        pct = 60 + int((i / len(results)) * 35)
        progress.update(pct, 'Loading: %s...' % title)

        content = _search_trakt_for_title(title, year, media_type)
        if not content:
            continue

        ids = content.get('ids', {})
        tmdb_id = ids.get('tmdb')
        imdb_id = ids.get('imdb', '')
        actual_title = content.get('title', title)
        actual_year = content.get('year', year)

        meta = tmdb.get_details(tmdb_id, 'movie' if media_type == 'movie' else 'tv')
        label = '%s (%s)' % (actual_title, actual_year) if actual_year else actual_title

        li = xbmcgui.ListItem(label=label)
        li.setArt({'poster': meta.get('poster', ''), 'fanart': FANART, 'thumb': meta.get('poster', ''), 'icon': ICON})
        li.setInfo('video', {
            'title': actual_title, 'year': actual_year,
            'plot': meta.get('overview', ''), 'rating': meta.get('rating', 0),
            'genre': ', '.join(meta.get('genres', []))
        })

        if media_type == 'movie':
            li.setInfo('video', {'mediatype': 'movie'})
            li.setProperty('IsPlayable', 'true')
            url = '%s?action=play&title=%s&year=%s&imdb_id=%s' % (
                sys.argv[0], quote_plus(actual_title), actual_year, imdb_id)
            xbmcplugin.addDirectoryItem(_handle(), url, li, False)
        else:
            li.setInfo('video', {'mediatype': 'tvshow'})
            url = '%s?action=show_seasons&tmdb_id=%s&title=%s' % (
                sys.argv[0], tmdb_id, quote_plus(actual_title))
            xbmcplugin.addDirectoryItem(_handle(), url, li, True)
        count += 1

    progress.close()
    if count:
        xbmcgui.Dialog().notification('Discovery', '%d picks loaded' % count, xbmcgui.NOTIFICATION_INFO, 2000)
    xbmcplugin.setContent(_handle(), 'videos')
    xbmcplugin.endOfDirectory(_handle())
