# -*- coding: utf-8 -*-
"""Discovery Feed - TikTok-style trailer scroll with auto-play and instant watch."""
import json
import ssl
import sys
import random
import urllib.request
import urllib.error
from urllib.parse import quote_plus, urlencode
import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from . import tmdb

ADDON = xbmcaddon.Addon()
SSL_CTX = ssl._create_unverified_context()
FANART = os.path.join(ADDON.getAddonInfo('path'), 'fanart.jpg')
ICON = os.path.join(ADDON.getAddonInfo('path'), 'icon.png')

INVIDIOUS_INSTANCES = [
    'https://inv.nadeko.net',
    'https://invidious.nerdvpn.de',
    'https://vid.puffyan.us',
    'https://invidious.privacyredirect.com',
]


def _handle():
    try:
        return int(sys.argv[1])
    except (IndexError, ValueError):
        return -1


def _resolve_youtube(video_id):
    """Resolve YouTube video to direct stream URL via Invidious API."""
    for instance in INVIDIOUS_INSTANCES:
        try:
            url = '%s/api/v1/videos/%s?fields=adaptiveFormats,formatStreams' % (instance, video_id)
            req = urllib.request.Request(url, headers={'User-Agent': 'TraktPlayer/2.0'})
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as r:
                data = json.loads(r.read().decode('utf-8'))

            # Prefer 720p or 1080p from formatStreams (muxed, simpler)
            for stream in data.get('formatStreams', []):
                quality = stream.get('qualityLabel', '')
                if '720p' in quality or '1080p' in quality:
                    return stream.get('url', '')

            # Fallback: any format stream
            for stream in data.get('formatStreams', []):
                if stream.get('url'):
                    return stream['url']

            # Try adaptive (video only, still works for trailers)
            for fmt in data.get('adaptiveFormats', []):
                if 'video' in fmt.get('type', '') and fmt.get('url'):
                    quality = fmt.get('qualityLabel', '')
                    if '720p' in quality or '1080p' in quality:
                        return fmt['url']

        except Exception as e:
            xbmc.log('Invidious %s failed: %s' % (instance, str(e)), xbmc.LOGWARNING)
            continue
    return ''


def _try_youtube_addon(video_id):
    """Try to play via Kodi YouTube addon if installed."""
    try:
        addon_info = xbmcaddon.Addon('plugin.video.youtube')
        if addon_info:
            return 'plugin://plugin.video.youtube/play/?video_id=%s' % video_id
    except Exception:
        pass
    return ''


def _resolve_trailer(video_id):
    """Resolve a YouTube trailer - try YouTube addon first, then Invidious."""
    yt_url = _try_youtube_addon(video_id)
    if yt_url:
        return yt_url
    return _resolve_youtube(video_id)


# ── Feed Categories ───────────────────────────────────────────────────────

def feed_menu():
    """Main discovery feed menu."""
    items = [
        ('Trending Trailers', 'feed_trending'),
        ('New Releases', 'feed_now_playing'),
        ('Coming Soon', 'feed_upcoming'),
        ('Trending TV', 'feed_trending_tv'),
        ('Surprise Me (Shuffle)', 'feed_shuffle'),
        ('Marathon Mode (Auto-Play All)', 'feed_marathon'),
    ]
    for label, action in items:
        url = '%s?action=%s' % (sys.argv[0], action)
        li = xbmcgui.ListItem(label=label)
        li.setArt({'fanart': FANART, 'icon': ICON, 'thumb': ICON})
        xbmcplugin.addDirectoryItem(_handle(), url, li, isFolder=True)
    xbmcplugin.endOfDirectory(_handle())


def _build_feed_items(tmdb_items, media_type='movie'):
    """Build Kodi list items from TMDB results with trailer + full movie options."""
    count = 0
    for item in tmdb_items:
        tmdb_id = item.get('id')
        title = item.get('title') or item.get('name', 'Unknown')
        year = (item.get('release_date') or item.get('first_air_date', ''))[:4]
        overview = item.get('overview', '')
        rating = item.get('vote_average', 0)
        poster = ('https://image.tmdb.org/t/p/w500' + item['poster_path']) if item.get('poster_path') else ''
        backdrop = ('https://image.tmdb.org/t/p/original' + item['backdrop_path']) if item.get('backdrop_path') else ''

        # Get trailer
        yt_key = tmdb.get_trailer(tmdb_id, media_type)
        if not yt_key:
            continue

        label = '%s (%s)' % (title, year) if year else title
        li = xbmcgui.ListItem(label=label)
        li.setArt({'poster': poster, 'fanart': FANART, 'thumb': poster, 'icon': ICON})
        li.setInfo('video', {
            'title': title, 'year': year, 'plot': overview,
            'rating': rating, 'mediatype': media_type
        })
        li.setProperty('IsPlayable', 'true')

        # Context menu: Watch Full Movie/Show
        ctx = []
        if media_type == 'movie':
            ctx.append(('Watch Full Movie',
                         'RunPlugin(plugin://plugin.video.trakt_player/?action=play&title=%s&year=%s&imdb_id=)' % (
                             quote_plus(title), year)))
        else:
            ctx.append(('Browse Show',
                         'Container.Update(plugin://plugin.video.trakt_player/?action=show_seasons&tmdb_id=%s&title=%s)' % (
                             tmdb_id, quote_plus(title))))
        li.addContextMenuItems(ctx)

        # Play trailer URL
        url = '%s?action=play_trailer&yt_key=%s&title=%s' % (
            sys.argv[0], yt_key, quote_plus(title))
        xbmcplugin.addDirectoryItem(_handle(), url, li, False)
        count += 1

    return count


def feed_trending():
    """Trending movie trailers."""
    progress = xbmcgui.DialogProgress()
    progress.create('Discovery Feed', 'Loading trending trailers...')
    items = tmdb.get_trending_movies(1)
    progress.update(50, 'Found %d movies. Loading trailers...' % len(items))
    count = _build_feed_items(items, 'movie')
    progress.close()
    if count:
        xbmcgui.Dialog().notification('Discovery Feed', '%d trailers loaded' % count, xbmcgui.NOTIFICATION_INFO, 2000)
    xbmcplugin.setContent(_handle(), 'movies')
    xbmcplugin.endOfDirectory(_handle())


def feed_trending_tv():
    """Trending TV trailers."""
    progress = xbmcgui.DialogProgress()
    progress.create('Discovery Feed', 'Loading trending TV trailers...')
    items = tmdb.get_trending_shows(1)
    progress.update(50, 'Found %d shows. Loading trailers...' % len(items))
    count = _build_feed_items(items, 'tv')
    progress.close()
    if count:
        xbmcgui.Dialog().notification('Discovery Feed', '%d trailers loaded' % count, xbmcgui.NOTIFICATION_INFO, 2000)
    xbmcplugin.setContent(_handle(), 'tvshows')
    xbmcplugin.endOfDirectory(_handle())


def feed_now_playing():
    """Now playing in theaters - trailers."""
    progress = xbmcgui.DialogProgress()
    progress.create('Discovery Feed', 'Loading new releases...')
    items = tmdb.get_now_playing()
    progress.update(50, 'Loading trailers...')
    count = _build_feed_items(items, 'movie')
    progress.close()
    xbmcplugin.setContent(_handle(), 'movies')
    xbmcplugin.endOfDirectory(_handle())


def feed_upcoming():
    """Upcoming movies - trailers."""
    progress = xbmcgui.DialogProgress()
    progress.create('Discovery Feed', 'Loading upcoming trailers...')
    items = tmdb.get_upcoming_movies()
    progress.update(50, 'Loading trailers...')
    count = _build_feed_items(items, 'movie')
    progress.close()
    xbmcplugin.setContent(_handle(), 'movies')
    xbmcplugin.endOfDirectory(_handle())


def feed_shuffle():
    """Shuffle mix of trending movies + TV + new releases."""
    progress = xbmcgui.DialogProgress()
    progress.create('Discovery Feed', 'Building your surprise feed...')
    all_items = []
    all_items.extend([(i, 'movie') for i in tmdb.get_trending_movies(1)[:10]])
    progress.update(30, 'Got trending movies...')
    all_items.extend([(i, 'tv') for i in tmdb.get_trending_shows(1)[:10]])
    progress.update(60, 'Got trending shows...')
    all_items.extend([(i, 'movie') for i in tmdb.get_now_playing()[:5]])
    progress.update(80, 'Shuffling...')
    random.shuffle(all_items)

    count = 0
    for item, media_type in all_items:
        tmdb_id = item.get('id')
        title = item.get('title') or item.get('name', 'Unknown')
        year = (item.get('release_date') or item.get('first_air_date', ''))[:4]
        poster = ('https://image.tmdb.org/t/p/w500' + item['poster_path']) if item.get('poster_path') else ''
        backdrop = ('https://image.tmdb.org/t/p/original' + item['backdrop_path']) if item.get('backdrop_path') else ''

        yt_key = tmdb.get_trailer(tmdb_id, media_type)
        if not yt_key:
            continue

        label = '%s (%s)' % (title, year) if year else title
        tag = '[MOVIE]' if media_type == 'movie' else '[TV]'
        li = xbmcgui.ListItem(label='%s %s' % (tag, label))
        li.setArt({'poster': poster, 'fanart': FANART, 'thumb': poster, 'icon': ICON})
        li.setInfo('video', {'title': title, 'year': year, 'plot': item.get('overview', ''),
                              'rating': item.get('vote_average', 0)})
        li.setProperty('IsPlayable', 'true')

        ctx = []
        if media_type == 'movie':
            ctx.append(('Watch Full Movie',
                         'RunPlugin(plugin://plugin.video.trakt_player/?action=play&title=%s&year=%s&imdb_id=)' % (
                             quote_plus(title), year)))
        else:
            ctx.append(('Browse Show',
                         'Container.Update(plugin://plugin.video.trakt_player/?action=show_seasons&tmdb_id=%s&title=%s)' % (
                             tmdb_id, quote_plus(title))))
        li.addContextMenuItems(ctx)

        url = '%s?action=play_trailer&yt_key=%s&title=%s' % (
            sys.argv[0], yt_key, quote_plus(title))
        xbmcplugin.addDirectoryItem(_handle(), url, li, False)
        count += 1

    progress.close()
    if count:
        xbmcgui.Dialog().notification('Surprise Feed', '%d trailers shuffled' % count, xbmcgui.NOTIFICATION_INFO, 2000)
    xbmcplugin.setContent(_handle(), 'videos')
    xbmcplugin.endOfDirectory(_handle())


def feed_marathon():
    """Auto-play all trending trailers as a playlist (marathon mode)."""
    progress = xbmcgui.DialogProgress()
    progress.create('Marathon Mode', 'Building trailer playlist...')

    items = tmdb.get_trending_movies(1)[:20]
    progress.update(40, 'Found %d movies. Resolving trailers...' % len(items))

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    count = 0

    for i, item in enumerate(items):
        if progress.iscanceled():
            break
        tmdb_id = item.get('id')
        title = item.get('title', 'Unknown')
        year = (item.get('release_date', ''))[:4]
        poster = ('https://image.tmdb.org/t/p/w500' + item['poster_path']) if item.get('poster_path') else ''

        yt_key = tmdb.get_trailer(tmdb_id, 'movie')
        if not yt_key:
            continue

        pct = 40 + int((i / len(items)) * 55)
        progress.update(pct, 'Resolving: %s...' % title)

        stream_url = _resolve_trailer(yt_key)
        if not stream_url:
            continue

        label = '%s (%s)' % (title, year) if year else title
        li = xbmcgui.ListItem(label=label)
        li.setArt({'poster': poster, 'thumb': poster, 'fanart': FANART, 'icon': ICON})
        li.setInfo('video', {'title': title, 'year': year})

        playlist.add(stream_url, li)
        count += 1

    progress.close()

    if count > 0:
        xbmcgui.Dialog().notification('Marathon Mode', 'Playing %d trailers' % count, xbmcgui.NOTIFICATION_INFO, 3000)
        xbmc.Player().play(playlist)
    else:
        xbmcgui.Dialog().notification('Marathon Mode', 'Could not resolve any trailers', xbmcgui.NOTIFICATION_WARNING)


def play_trailer(yt_key, title=''):
    """Resolve and play a single YouTube trailer."""
    progress = xbmcgui.DialogProgress()
    progress.create('Trailer', 'Loading trailer for %s...' % title)

    stream_url = _resolve_trailer(yt_key)

    progress.close()

    if stream_url:
        xbmc.log('Playing trailer: %s -> %s' % (yt_key, stream_url[:80]), xbmc.LOGINFO)
        if stream_url.startswith('plugin://'):
            # YouTube addon URL - use setResolvedUrl won't work, use Player directly
            li = xbmcgui.ListItem(path=stream_url)
            xbmc.Player().play(stream_url, li)
        else:
            li = xbmcgui.ListItem(path=stream_url)
            li.setInfo('video', {'title': title})
            xbmcplugin.setResolvedUrl(_handle(), True, li)
    else:
        xbmcgui.Dialog().notification('Trailer', 'Could not load trailer', xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.setResolvedUrl(_handle(), False, xbmcgui.ListItem())
