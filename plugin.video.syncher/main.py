# -*- coding: utf-8 -*-
"""
Syncher v3.4.0 by zeus768
Scene Release Streamer with Debrid, Trakt, Music (AI+Deezer+Radio), Podcasts, Audiobooks
"""

import sys
import os
import json
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.modules import control
from resources.lib.modules import trakt_api
from resources.lib.modules import tmdb_api
from resources.lib.modules import cache
from resources.lib.modules import sources

HANDLE = int(sys.argv[1])
ADDON_URL = sys.argv[0]

def build_url(params):
    return '%s?%s' % (ADDON_URL, urllib.parse.urlencode(params))

def get_params():
    params = {}
    try:
        qs = sys.argv[2].lstrip('?')
        params = dict(urllib.parse.parse_qsl(qs))
    except:
        pass
    return params

# ============================================================
# DIRECTORY BUILDERS
# ============================================================

def add_dir(name, action, url='', image='', fanart='', is_folder=True, info=None, context=None):
    li = xbmcgui.ListItem(label=name)
    art = {}
    icon = image if image else control.addonIcon()
    art['icon'] = icon
    art['thumb'] = icon
    if image:
        art['poster'] = image
    if fanart:
        art['fanart'] = fanart
    elif control.addonFanart():
        art['fanart'] = control.addonFanart()
    li.setArt(art)
    if info:
        li.setInfo('Video', info)
    if context:
        li.addContextMenuItems(context)
    params = {'action': action}
    if url:
        params['url'] = url
    xbmcplugin.addDirectoryItem(HANDLE, build_url(params), li, isFolder=is_folder)

def add_movie_item(item, meta=None):
    title = item.get('title', '')
    year = item.get('year', '')
    imdb = item.get('imdb', '0')
    tmdb = item.get('tmdb', '0')
    label = '%s (%s)' % (title, year) if year else title

    poster = item.get('poster', '0')
    fanart = item.get('fanart', '0')
    if poster == '0':
        poster = control.addonIcon()
    if fanart == '0':
        fanart = control.addonFanart()

    li = xbmcgui.ListItem(label=label)
    li.setArt({'poster': poster, 'icon': poster, 'thumb': poster, 'fanart': fanart})

    info_labels = {
        'title': title, 'year': int(year) if year and year != '0' else 0,
        'plot': item.get('plot', ''), 'genre': item.get('genre', ''),
        'rating': float(item.get('rating', '0') or '0'),
        'duration': int(item.get('duration', '0') or '0') * 60,
        'mpaa': item.get('mpaa', ''), 'mediatype': 'movie',
    }
    if meta:
        if meta.get('director'):
            info_labels['director'] = meta['director']
        if meta.get('studio'):
            info_labels['studio'] = meta['studio']
        if meta.get('tagline'):
            info_labels['tagline'] = meta['tagline']
        if meta.get('cast'):
            try:
                li.setCast([{'name': c[0], 'role': c[1]} for c in meta['cast']])
            except:
                pass
    li.setInfo('Video', info_labels)
    li.setProperty('IsPlayable', 'true')

    url_params = {
        'action': 'playmovie',
        'title': title, 'year': year,
        'imdb': imdb, 'tmdb': tmdb,
    }
    cm = []
    cm.append(('Syncher Settings', 'RunPlugin(%s)' % build_url({'action': 'settings'})))
    li.addContextMenuItems(cm)
    xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)

def add_show_item(item, meta=None):
    title = item.get('title', '')
    year = item.get('year', '')
    imdb = item.get('imdb', '0')
    tmdb = item.get('tmdb', '0')
    tvdb = item.get('tvdb', '0')
    label = '%s (%s)' % (title, year) if year else title

    poster = item.get('poster', '0')
    fanart = item.get('fanart', '0')
    if poster == '0':
        poster = control.addonIcon()
    if fanart == '0':
        fanart = control.addonFanart()

    li = xbmcgui.ListItem(label=label)
    li.setArt({'poster': poster, 'icon': poster, 'thumb': poster, 'fanart': fanart})

    info_labels = {
        'title': title, 'year': int(year) if year and year != '0' else 0,
        'plot': item.get('plot', ''), 'genre': item.get('genre', ''),
        'rating': float(item.get('rating', '0') or '0'),
        'mpaa': item.get('mpaa', ''), 'mediatype': 'tvshow',
    }
    if meta and meta.get('cast'):
        try:
            li.setCast([{'name': c[0], 'role': c[1]} for c in meta['cast']])
        except:
            pass
    li.setInfo('Video', info_labels)

    url_params = {
        'action': 'seasons',
        'title': title, 'year': year,
        'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb,
    }
    cm = []
    cm.append(('Syncher Settings', 'RunPlugin(%s)' % build_url({'action': 'settings'})))
    li.addContextMenuItems(cm)
    xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=True)

def end_directory(content='videos', sort=False):
    if sort:
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)

# ============================================================
# MAIN MENU
# ============================================================

def main_menu():
    add_dir('[COLOR gold]Movies[/COLOR]', 'moviesmenu', image=control.addonIcon())
    add_dir('[COLOR gold]TV Shows[/COLOR]', 'tvmenu', image=control.addonIcon())
    add_dir('[COLOR gold]Sports Highlights[/COLOR]', 'sportsmenu', image=control.addonIcon())
    add_dir('[COLOR gold]Music[/COLOR]', 'musicmenu', image=control.addonIcon())
    add_dir('[COLOR gold]Podcasts[/COLOR]', 'podcastmenu', image=control.addonIcon())
    add_dir('[COLOR gold]Audiobooks[/COLOR]', 'audiobookmenu', image=control.addonIcon())
    add_dir('[COLOR skyblue]My Trakt[/COLOR]', 'traktmenu', image=control.addonIcon())
    add_dir('[COLOR skyblue]Search[/COLOR]', 'searchmenu', image=control.addonIcon())
    add_dir('[COLOR white]Settings[/COLOR]', 'settings', image=control.addonIcon(), is_folder=False)

    add_dir('[COLOR grey]INFO: Enable Debrid/TorBox/RapidRAR in Settings for best results[/COLOR]', 'settings', image=control.addonIcon(), is_folder=False)

    end_directory()

# ============================================================
# MOVIE MENUS
# ============================================================

def movies_menu():
    add_dir('[COLOR gold]Popular[/COLOR]', 'movies', url='/movies/popular?')
    add_dir('[COLOR gold]Trending[/COLOR]', 'movies', url='/movies/trending?')
    add_dir('[COLOR gold]Box Office[/COLOR]', 'movies', url='/movies/boxoffice')
    add_dir('[COLOR gold]Most Watched (Month)[/COLOR]', 'movies', url='/movies/watched/monthly?')
    add_dir('[COLOR gold]Most Watched (All Time)[/COLOR]', 'movies', url='/movies/watched/all?')
    add_dir('[COLOR gold]Most Played[/COLOR]', 'movies', url='/movies/played/all?')
    add_dir('[COLOR gold]New Releases[/COLOR]', 'movies', url='/movies/watched/weekly?')
    add_dir('[COLOR skyblue]Genres[/COLOR]', 'moviegenres')
    add_dir('[COLOR skyblue]Years[/COLOR]', 'movieyears')
    add_dir('[COLOR skyblue]Certifications[/COLOR]', 'moviecerts')
    add_dir('[COLOR skyblue]Search Movies[/COLOR]', 'searchmovie')
    end_directory()

def movie_list(url, page=1):
    items, next_page = trakt_api.get_movie_list(url, page)
    for item in items:
        meta = tmdb_api.get_movie_meta(tmdb_id=item.get('tmdb'), imdb_id=item.get('imdb'))
        if meta:
            item.update({k: v for k, v in meta.items() if v and v != '0'})
        add_movie_item(item, meta)

    if next_page:
        add_dir('[COLOR gold]Next Page >>[/COLOR]', 'movies', url=next_page)

    end_directory('movies')

def movie_genres():
    genres = [
        ('Action', 'action'), ('Adventure', 'adventure'), ('Animation', 'animation'),
        ('Comedy', 'comedy'), ('Crime', 'crime'), ('Documentary', 'documentary'),
        ('Drama', 'drama'), ('Family', 'family'), ('Fantasy', 'fantasy'),
        ('History', 'history'), ('Horror', 'horror'), ('Music', 'music'),
        ('Mystery', 'mystery'), ('Romance', 'romance'),
        ('Science Fiction', 'science-fiction'), ('Superhero', 'superhero'),
        ('Thriller', 'thriller'), ('War', 'war'), ('Western', 'western'),
    ]
    for name, slug in genres:
        add_dir(name, 'movies', url='/movies/popular?genres=%s&' % slug)
    end_directory()

def movie_years():
    import datetime
    year = datetime.datetime.now().year
    for y in range(year, year - 50, -1):
        add_dir(str(y), 'movies', url='/movies/popular?years=%s&' % y)
    end_directory()

def movie_certs():
    for c in ['G', 'PG', 'PG-13', 'R', 'NC-17']:
        add_dir(c, 'movies', url='/movies/popular?certifications=%s&' % c.lower())
    end_directory()

# ============================================================
# TV SHOW MENUS
# ============================================================

def tv_menu():
    add_dir('[COLOR gold]Popular[/COLOR]', 'tvshows', url='/shows/popular?')
    add_dir('[COLOR gold]Trending[/COLOR]', 'tvshows', url='/shows/trending?')
    add_dir('[COLOR gold]Most Watched (Month)[/COLOR]', 'tvshows', url='/shows/watched/monthly?')
    add_dir('[COLOR gold]Most Watched (All Time)[/COLOR]', 'tvshows', url='/shows/watched/all?')
    add_dir('[COLOR gold]Most Played[/COLOR]', 'tvshows', url='/shows/played/all?')
    add_dir('[COLOR gold]New Shows[/COLOR]', 'tvshows', url='/shows/watched/weekly?')
    add_dir('[COLOR skyblue]Genres[/COLOR]', 'tvgenres')
    add_dir('[COLOR skyblue]Years[/COLOR]', 'tvyears')
    add_dir('[COLOR skyblue]Search TV Shows[/COLOR]', 'searchtv')
    end_directory()

def tv_list(url, page=1):
    items, next_page = trakt_api.get_show_list(url, page)
    for item in items:
        meta = tmdb_api.get_show_meta(tmdb_id=item.get('tmdb'), imdb_id=item.get('imdb'))
        if meta:
            item.update({k: v for k, v in meta.items() if v and v != '0'})
        add_show_item(item, meta)

    if next_page:
        add_dir('[COLOR gold]Next Page >>[/COLOR]', 'tvshows', url=next_page)

    end_directory('tvshows')

def tv_genres():
    genres = [
        ('Action', 'action'), ('Adventure', 'adventure'), ('Animation', 'animation'),
        ('Comedy', 'comedy'), ('Crime', 'crime'), ('Documentary', 'documentary'),
        ('Drama', 'drama'), ('Family', 'family'), ('Fantasy', 'fantasy'),
        ('Horror', 'horror'), ('Mystery', 'mystery'), ('Reality', 'reality'),
        ('Romance', 'romance'), ('Science Fiction', 'science-fiction'),
        ('Superhero', 'superhero'), ('Thriller', 'thriller'), ('War', 'war'),
        ('Western', 'western'),
    ]
    for name, slug in genres:
        add_dir(name, 'tvshows', url='/shows/popular?genres=%s&' % slug)
    end_directory()

def tv_years():
    import datetime
    year = datetime.datetime.now().year
    for y in range(year, year - 50, -1):
        add_dir(str(y), 'tvshows', url='/shows/popular?years=%s&' % y)
    end_directory()

def seasons(params):
    title = params.get('title', '')
    year = params.get('year', '')
    imdb = params.get('imdb', '0')
    tmdb = params.get('tmdb', '0')
    tvdb = params.get('tvdb', '0')

    season_list = trakt_api.get_season_list(imdb, tvdb)

    for s in season_list:
        season_num = s['season']
        label = 'Season %s' % season_num
        poster = control.addonIcon()
        season_poster = tmdb_api.get_season_poster(tmdb, season_num)
        if season_poster:
            poster = season_poster

        li = xbmcgui.ListItem(label=label)
        li.setArt({'poster': poster, 'icon': poster, 'thumb': poster, 'fanart': control.addonFanart()})
        li.setInfo('Video', {
            'title': label, 'plot': s.get('plot', ''),
            'season': int(season_num), 'mediatype': 'season',
        })

        url_params = {
            'action': 'episodes',
            'title': title, 'year': year,
            'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb,
            'season': season_num,
        }
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=True)

    end_directory('seasons')

def episodes(params):
    title = params.get('title', '')
    year = params.get('year', '')
    imdb = params.get('imdb', '0')
    tmdb = params.get('tmdb', '0')
    tvdb = params.get('tvdb', '0')
    season = params.get('season', '1')

    ep_list = trakt_api.get_episode_list(imdb, season)

    for ep in ep_list:
        ep_num = ep['episode']
        label = 'S%sE%s - %s' % (str(season).zfill(2), str(ep_num).zfill(2), ep.get('title', 'Episode %s' % ep_num))

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': control.addonIcon(), 'thumb': control.addonIcon(), 'fanart': control.addonFanart()})
        li.setInfo('Video', {
            'title': label, 'plot': ep.get('plot', ''),
            'season': int(season), 'episode': int(ep_num),
            'rating': float(ep.get('rating', '0') or '0'),
            'mediatype': 'episode',
        })
        li.setProperty('IsPlayable', 'true')

        url_params = {
            'action': 'playepisode',
            'title': title, 'year': year,
            'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb,
            'season': season, 'episode': ep_num,
        }
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)

    end_directory('episodes')

# ============================================================
# SPORTS MENU
# ============================================================

def sports_menu():
    from resources.lib.scrapers import sport_video, fullmatchshows, footballorgin, basketball_video

    add_dir('[COLOR gold]--- Sport-Video.org.ua ---[/COLOR]', 'sportcats', url='sportvideo')
    add_dir('[COLOR lime]--- FullMatchShows.com ---[/COLOR]', 'sportcats', url='fullmatchshows')
    add_dir('[COLOR cyan]--- FootballOrgin.com ---[/COLOR]', 'sportcats', url='footballorgin')
    add_dir('[COLOR orange]--- Basketball-Video.com ---[/COLOR]', 'sportcats', url='basketballvideo')
    end_directory()

def sport_categories(source):
    from resources.lib.scrapers import sport_video, fullmatchshows, footballorgin, basketball_video

    scrapers = {
        'sportvideo': sport_video,
        'fullmatchshows': fullmatchshows,
        'footballorgin': footballorgin,
        'basketballvideo': basketball_video,
    }
    scraper = scrapers.get(source)
    if not scraper:
        return

    cats = scraper.get_categories()
    for c in cats:
        add_dir(c['name'], 'sportitems', url='%s|%s' % (source, c['url']), image=control.addonIcon())
    end_directory()

def sport_items(params):
    from resources.lib.scrapers import sport_video, fullmatchshows, footballorgin, basketball_video

    url_data = params.get('url', '')
    parts = url_data.split('|', 1)
    if len(parts) != 2:
        return
    source, url = parts

    scrapers = {
        'sportvideo': sport_video,
        'fullmatchshows': fullmatchshows,
        'footballorgin': footballorgin,
        'basketballvideo': basketball_video,
    }
    scraper = scrapers.get(source)
    if not scraper:
        return

    items = scraper.get_items(url)
    for item in items:
        add_dir(item['name'], 'sportsources', url='%s|%s' % (source, item['url']),
                image=item.get('thumb') or control.addonIcon(), is_folder=True)
    end_directory()

def sport_sources(params):
    from resources.lib.scrapers import sport_video, fullmatchshows, footballorgin, basketball_video

    url_data = params.get('url', '')
    parts = url_data.split('|', 1)
    if len(parts) != 2:
        return
    source, url = parts

    scrapers = {
        'sportvideo': sport_video,
        'fullmatchshows': fullmatchshows,
        'footballorgin': footballorgin,
        'basketballvideo': basketball_video,
    }
    scraper = scrapers.get(source)
    if not scraper:
        return

    source_list = scraper.get_sources(url)
    if not source_list:
        control.infoDialog('No sources found')
        return

    for s in source_list:
        li = xbmcgui.ListItem(label=s['label'])
        li.setArt({'icon': control.addonIcon(), 'fanart': control.addonFanart()})
        li.setProperty('IsPlayable', 'true')
        li.setInfo('Video', {'title': s['label']})
        url_params = {'action': 'playsport', 'url': s['url'], 'type': s.get('type', 'direct')}
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)
    end_directory()

# ============================================================
# MUSIC MENU
# ============================================================

def music_menu():
    add_dir('[COLOR gold]AI Daily Playlists[/COLOR]', 'aidaily', image=control.addonIcon())
    add_dir('[COLOR gold]Mood Playlists[/COLOR]', 'aimood', image=control.addonIcon())
    add_dir('[COLOR gold]Decades[/COLOR]', 'aidecades', image=control.addonIcon())
    add_dir('[COLOR cyan]Radio[/COLOR]', 'radiomenu', image=control.addonIcon())
    add_dir('[COLOR gold]Top Charts[/COLOR]', 'musictracks', url='chart_tracks')
    add_dir('[COLOR gold]Top Albums[/COLOR]', 'musicalbums', url='chart_albums')
    add_dir('[COLOR gold]Top Artists[/COLOR]', 'musicartists', url='chart_artists')
    add_dir('[COLOR gold]New Releases[/COLOR]', 'musicalbums', url='new_releases')
    add_dir('[COLOR skyblue]Genres[/COLOR]', 'musicgenres')
    add_dir('[COLOR skyblue]Curated Playlists[/COLOR]', 'musicplaylists', url='chart_playlists')
    add_dir('[COLOR skyblue]Search Artist[/COLOR]', 'searchartist')
    add_dir('[COLOR skyblue]Search Album[/COLOR]', 'searchalbum')
    add_dir('[COLOR skyblue]Search Track[/COLOR]', 'searchtrack')
    add_dir('[COLOR lime]My Playlists[/COLOR]', 'myplaylists')
    end_directory()

def music_genres():
    from resources.lib.modules import deezer_api
    genres = deezer_api.get_genres()
    for g in genres:
        add_dir('[COLOR gold]%s[/COLOR]' % g['name'], 'musicgenreartists',
                url=g['id'], image=g.get('image') or control.addonIcon())
    end_directory()

def music_genre_artists(params):
    from resources.lib.modules import deezer_api
    genre_id = params.get('url', '')
    artists = deezer_api.get_genre_artists(genre_id)
    for a in artists:
        add_dir('%s  [COLOR grey](%s fans)[/COLOR]' % (a['name'], a.get('fans', '0')),
                'musicartist', url=a['id'], image=a.get('image') or control.addonIcon())
    end_directory()

def music_artists(params):
    from resources.lib.modules import deezer_api
    url = params.get('url', '')
    if url == 'chart_artists':
        artists = deezer_api.get_chart_artists()
    else:
        artists = []
    for a in artists:
        add_dir('%s  [COLOR grey](%s fans)[/COLOR]' % (a['name'], a.get('fans', '0')),
                'musicartist', url=a['id'], image=a.get('image') or control.addonIcon())
    end_directory()

def music_artist(params):
    from resources.lib.modules import deezer_api
    artist_id = params.get('url', '')
    artist = deezer_api.get_artist(artist_id)
    name = artist['name'] if artist else 'Artist'
    image = artist.get('image', '') if artist else ''

    add_dir('[COLOR gold]Top Tracks[/COLOR] - %s' % name, 'musictracks',
            url='artist_top|%s' % artist_id, image=image)
    add_dir('[COLOR gold]Albums[/COLOR] - %s' % name, 'musicalbums',
            url='artist_albums|%s' % artist_id, image=image)
    add_dir('[COLOR skyblue]Related Artists[/COLOR]', 'musicrelated',
            url=artist_id, image=image)
    add_dir('[COLOR magenta]AI: Similar To %s[/COLOR]' % name, 'aisimilar',
            url=name, image=image)
    add_dir('[COLOR lime]Search Scene Sites[/COLOR] for %s' % name, 'musicscenesearch',
            url=name, image=image)
    end_directory()

def music_related(params):
    from resources.lib.modules import deezer_api
    artist_id = params.get('url', '')
    artists = deezer_api.get_artist_related(artist_id)
    for a in artists:
        add_dir('%s  [COLOR grey](%s fans)[/COLOR]' % (a['name'], a.get('fans', '0')),
                'musicartist', url=a['id'], image=a.get('image') or control.addonIcon())
    end_directory()

def music_albums(params):
    from resources.lib.modules import deezer_api
    url = params.get('url', '')
    if url == 'chart_albums':
        albums = deezer_api.get_chart_albums()
    elif url == 'new_releases':
        albums = deezer_api.get_editorial_releases()
    elif url.startswith('artist_albums|'):
        artist_id = url.split('|')[1]
        albums = deezer_api.get_artist_albums(artist_id)
    else:
        albums = []
    for a in albums:
        label = '%s - %s' % (a.get('artist', ''), a['title']) if a.get('artist') else a['title']
        if a.get('release_date'):
            label += '  [COLOR grey](%s)[/COLOR]' % a['release_date'][:4]
        add_dir(label, 'musicalbum', url=a['id'],
                image=a.get('image') or control.addonIcon())
    end_directory()

def music_album(params):
    from resources.lib.modules import deezer_api
    album_id = params.get('url', '')
    album = deezer_api.get_album(album_id)
    if not album:
        control.infoDialog('Album not found')
        return

    album_name = '%s - %s' % (album.get('artist', ''), album['title'])
    album_image = album.get('image', '')

    # Auto-play all button
    add_dir('[COLOR gold]>>> Auto-Play All Tracks <<<[/COLOR]', 'musicautoplay',
            url='album|%s' % album_id, image=album_image, is_folder=False)

    # Scene download button
    add_dir('[COLOR lime]>>> Search Scene Sites for Download <<<[/COLOR]', 'musicscenesearch',
            url=album_name, image=album_image)

    # Track list
    tracks = deezer_api.get_album_tracks(album_id)
    for t in tracks:
        mins = int(t.get('duration', '0')) // 60
        secs = int(t.get('duration', '0')) % 60
        label = '%s. %s  [COLOR grey](%d:%02d)[/COLOR]' % (t.get('track_position', ''), t['title'], mins, secs)

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': album_image or control.addonIcon(), 'thumb': album_image or control.addonIcon(),
                    'fanart': control.addonFanart()})
        li.setInfo('Music', {
            'title': t['title'], 'artist': t.get('artist', album.get('artist', '')),
            'album': album['title'], 'tracknumber': int(t.get('track_position', '0') or '0'),
            'duration': int(t.get('duration', '0')),
        })
        li.setProperty('IsPlayable', 'true')
        url_params = {
            'action': 'playmusic',
            'title': t['title'], 'artist': t.get('artist', album.get('artist', '')),
            'album': album['title'], 'album_id': album_id,
        }
        # Context menu: add to playlist
        cm = [('Add to Playlist', 'RunPlugin(%s)' % build_url({
            'action': 'addtoplaylist',
            'track_id': t['id'], 'title': t['title'],
            'artist': t.get('artist', ''), 'album': album['title'],
            'album_id': album_id, 'image': album_image,
            'duration': t.get('duration', '0'),
        }))]
        li.addContextMenuItems(cm)
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)

    end_directory('songs')

def music_tracks(params):
    from resources.lib.modules import deezer_api
    url = params.get('url', '')
    if url == 'chart_tracks':
        tracks = deezer_api.get_chart_tracks()
    elif url.startswith('artist_top|'):
        artist_id = url.split('|')[1]
        tracks = deezer_api.get_artist_top(artist_id)
    else:
        tracks = []

    for t in tracks:
        mins = int(t.get('duration', '0')) // 60
        secs = int(t.get('duration', '0')) % 60
        label = '%s - %s  [COLOR grey](%d:%02d)[/COLOR]' % (t.get('artist', ''), t['title'], mins, secs)

        li = xbmcgui.ListItem(label=label)
        img = t.get('image') or control.addonIcon()
        li.setArt({'icon': img, 'thumb': img, 'fanart': control.addonFanart()})
        li.setInfo('Music', {
            'title': t['title'], 'artist': t.get('artist', ''),
            'album': t.get('album', ''), 'duration': int(t.get('duration', '0')),
        })
        li.setProperty('IsPlayable', 'true')
        url_params = {
            'action': 'playmusic',
            'title': t['title'], 'artist': t.get('artist', ''),
            'album': t.get('album', ''), 'album_id': t.get('album_id', ''),
        }
        cm = [('Add to Playlist', 'RunPlugin(%s)' % build_url({
            'action': 'addtoplaylist',
            'track_id': t['id'], 'title': t['title'],
            'artist': t.get('artist', ''), 'album': t.get('album', ''),
            'album_id': t.get('album_id', ''), 'image': img,
            'duration': t.get('duration', '0'),
        }))]
        li.addContextMenuItems(cm)
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)

    end_directory('songs')

def music_playlists(params):
    from resources.lib.modules import deezer_api
    url = params.get('url', '')
    if url == 'chart_playlists':
        playlists = deezer_api.get_chart_playlists()
    else:
        playlists = []
    for p in playlists:
        label = '%s  [COLOR grey](%s tracks)[/COLOR]' % (p['title'], p.get('tracks', '0'))
        add_dir(label, 'musicplaylist', url=p['id'],
                image=p.get('image') or control.addonIcon())
    end_directory()

def music_playlist(params):
    from resources.lib.modules import deezer_api
    playlist_id = params.get('url', '')

    # Auto-play button
    add_dir('[COLOR gold]>>> Auto-Play All <<<[/COLOR]', 'musicautoplay',
            url='playlist|%s' % playlist_id, is_folder=False)

    tracks = deezer_api.get_playlist_tracks(playlist_id)
    for t in tracks:
        mins = int(t.get('duration', '0')) // 60
        secs = int(t.get('duration', '0')) % 60
        label = '%s - %s  [COLOR grey](%d:%02d)[/COLOR]' % (t.get('artist', ''), t['title'], mins, secs)

        li = xbmcgui.ListItem(label=label)
        img = t.get('image') or control.addonIcon()
        li.setArt({'icon': img, 'thumb': img, 'fanart': control.addonFanart()})
        li.setInfo('Music', {
            'title': t['title'], 'artist': t.get('artist', ''),
            'duration': int(t.get('duration', '0')),
        })
        li.setProperty('IsPlayable', 'true')
        url_params = {
            'action': 'playmusic',
            'title': t['title'], 'artist': t.get('artist', ''),
            'album': t.get('album', ''), 'album_id': t.get('album_id', ''),
        }
        cm = [('Add to Playlist', 'RunPlugin(%s)' % build_url({
            'action': 'addtoplaylist',
            'track_id': t['id'], 'title': t['title'],
            'artist': t.get('artist', ''), 'album': t.get('album', ''),
            'album_id': t.get('album_id', ''), 'image': img,
            'duration': t.get('duration', '0'),
        }))]
        li.addContextMenuItems(cm)
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)

    end_directory('songs')

# ============================================================
# USER PLAYLISTS
# ============================================================

def my_playlists():
    from resources.lib.modules import playlists as pl

    add_dir('[COLOR gold]+ Create New Playlist[/COLOR]', 'createplaylist', is_folder=False)
    add_dir('[COLOR skyblue]+ Import Playlist[/COLOR]', 'importplaylist', is_folder=False)

    user_playlists = pl.get_all()
    for p in user_playlists:
        label = '%s  [COLOR grey](%d tracks)[/COLOR]' % (p['name'], len(p.get('tracks', [])))
        add_dir(label, 'myplaylist', url=p['id'])
    end_directory()

def create_playlist():
    from resources.lib.modules import playlists as pl
    name = control.keyboard('', 'Playlist Name')
    if not name:
        return
    pl.create(name)
    control.infoDialog('Playlist created: %s' % name)
    xbmc.executebuiltin('Container.Refresh')

def my_playlist(params):
    from resources.lib.modules import playlists as pl
    playlist_id = params.get('url', '')
    data = pl.get(playlist_id)
    if not data:
        control.infoDialog('Playlist not found')
        return

    tracks = data.get('tracks', [])

    if tracks:
        add_dir('[COLOR gold]>>> Auto-Play All <<<[/COLOR]', 'musicautoplay',
                url='myplaylist|%s' % playlist_id, is_folder=False)
        add_dir('[COLOR magenta]>>> Shuffle Play <<<[/COLOR]', 'shuffleplay',
                url=playlist_id, is_folder=False)

    add_dir('[COLOR skyblue]Sort by Artist[/COLOR]', 'sortplaylist',
            url='%s|artist' % playlist_id, is_folder=False)
    add_dir('[COLOR skyblue]Sort by Title[/COLOR]', 'sortplaylist',
            url='%s|title' % playlist_id, is_folder=False)
    add_dir('[COLOR skyblue]Export Playlist[/COLOR]', 'exportplaylist',
            url=playlist_id, is_folder=False)
    add_dir('[COLOR red]Delete Playlist[/COLOR]', 'deleteplaylist',
            url=playlist_id, is_folder=False)

    for i, t in enumerate(tracks):
        mins = int(t.get('duration', '0')) // 60
        secs = int(t.get('duration', '0')) % 60
        label = '%s - %s  [COLOR grey](%d:%02d)[/COLOR]' % (t.get('artist', ''), t.get('title', ''), mins, secs)

        li = xbmcgui.ListItem(label=label)
        img = t.get('image') or control.addonIcon()
        li.setArt({'icon': img, 'thumb': img, 'fanart': control.addonFanart()})
        li.setInfo('Music', {
            'title': t.get('title', ''), 'artist': t.get('artist', ''),
            'duration': int(t.get('duration', '0')),
        })
        li.setProperty('IsPlayable', 'true')
        url_params = {
            'action': 'playmusic',
            'title': t.get('title', ''), 'artist': t.get('artist', ''),
            'album': t.get('album', ''), 'album_id': t.get('album_id', ''),
        }
        cm = [('Remove from Playlist', 'RunPlugin(%s)' % build_url({
            'action': 'removefromplaylist', 'playlist_id': playlist_id, 'index': str(i),
        }))]
        li.addContextMenuItems(cm)
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)

    end_directory('songs')

def add_to_playlist(params):
    from resources.lib.modules import playlists as pl

    user_playlists = pl.get_all()
    if not user_playlists:
        control.infoDialog('No playlists. Create one first.')
        return

    names = [p['name'] for p in user_playlists]
    choice = xbmcgui.Dialog().select('Add to Playlist', names)
    if choice < 0:
        return

    track = {
        'id': params.get('track_id', ''),
        'title': params.get('title', ''),
        'artist': params.get('artist', ''),
        'album': params.get('album', ''),
        'album_id': params.get('album_id', ''),
        'image': params.get('image', ''),
        'duration': params.get('duration', '0'),
    }
    result = pl.add_track(user_playlists[choice]['id'], track)
    if result:
        control.infoDialog('Added to: %s' % user_playlists[choice]['name'])
    else:
        control.infoDialog('Already in playlist')

def remove_from_playlist(params):
    from resources.lib.modules import playlists as pl
    playlist_id = params.get('playlist_id', '')
    index = params.get('index', '0')
    if pl.remove_track(playlist_id, index):
        control.infoDialog('Track removed')
        xbmc.executebuiltin('Container.Refresh')

def delete_playlist(params):
    from resources.lib.modules import playlists as pl
    playlist_id = params.get('url', '')
    if control.yesnoDialog('Delete this playlist?'):
        pl.delete(playlist_id)
        control.infoDialog('Playlist deleted')
        xbmc.executebuiltin('Container.Refresh')

def shuffle_play(params):
    """Shuffle play a user playlist"""
    import random
    from resources.lib.modules import playlists as pl
    playlist_id = params.get('url', '')
    data = pl.get(playlist_id)
    if not data or not data.get('tracks'):
        control.infoDialog('No tracks to play')
        return
    tracks = list(data['tracks'])
    random.shuffle(tracks)
    # Play first, queue rest
    from resources.lib.scrapers import music_scraper
    first = tracks[0]
    query = '%s %s' % (first.get('artist', ''), first.get('title', ''))
    dp = control.progressDialog()
    dp.create('Syncher', 'Shuffling %d tracks...' % len(tracks))
    results = music_scraper.search_music(query.strip())
    dp.close()
    if results:
        resolved = sources.resolve_source(results[0])
        if resolved:
            kodi_pl = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
            kodi_pl.clear()
            li = xbmcgui.ListItem(label='%s - %s' % (first.get('artist', ''), first.get('title', '')), path=resolved)
            kodi_pl.add(resolved, li)
            for t in tracks[1:]:
                t_label = '%s - %s' % (t.get('artist', ''), t.get('title', ''))
                t_li = xbmcgui.ListItem(label=t_label)
                t_url = build_url({'action': 'playmusic', 'title': t.get('title', ''), 'artist': t.get('artist', '')})
                kodi_pl.add(t_url, t_li)
            xbmc.Player().play(kodi_pl)
            return
    control.infoDialog('No sources found')

def sort_playlist(params):
    """Sort a playlist by field"""
    from resources.lib.modules import playlists as pl
    url = params.get('url', '')
    parts = url.split('|', 1)
    if len(parts) != 2:
        return
    playlist_id, sort_by = parts
    data = pl.get(playlist_id)
    if not data:
        return
    if sort_by == 'artist':
        data['tracks'].sort(key=lambda t: t.get('artist', '').lower())
    elif sort_by == 'title':
        data['tracks'].sort(key=lambda t: t.get('title', '').lower())
    pl._save(playlist_id, data)
    control.infoDialog('Sorted by %s' % sort_by)
    xbmc.executebuiltin('Container.Refresh')

def export_playlist(params):
    """Export playlist as text to clipboard/dialog"""
    from resources.lib.modules import playlists as pl
    playlist_id = params.get('url', '')
    data = pl.get(playlist_id)
    if not data:
        return
    lines = ['Playlist: %s' % data['name'], '']
    for i, t in enumerate(data.get('tracks', []), 1):
        lines.append('%d. %s - %s' % (i, t.get('artist', ''), t.get('title', '')))
    text = '\n'.join(lines)
    control.okDialog(text[:2000], heading='Export: %s' % data['name'])

def import_playlist_menu():
    """Import a playlist from text"""
    from resources.lib.modules import playlists as pl
    from resources.lib.modules import deezer_api
    text = control.keyboard('', 'Paste: Artist - Title (one per line)')
    if not text:
        return
    name = control.keyboard('', 'Playlist Name')
    if not name:
        return
    new_pl = pl.create(name)
    lines = text.split(',') if ',' in text else text.split('\n')
    count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        results = deezer_api.search_track(line, limit=1)
        if results:
            track = results[0]
            pl.add_track(new_pl['id'], track)
            count += 1
    control.infoDialog('Imported %d tracks into: %s' % (count, name))
    xbmc.executebuiltin('Container.Refresh')

# ============================================================
# AI DAILY PLAYLISTS (Powered by Emergent Universal Key)
# ============================================================

def ai_daily_menu():
    from resources.lib.modules import ai_playlists
    key = ai_playlists._get_api_key()
    if not key:
        add_dir('[COLOR red]Set your Emergent Universal Key in Settings first[/COLOR]', 'settings', is_folder=False)
        end_directory()
        return
    playlists = ai_playlists.get_daily_playlists()
    for p in playlists:
        add_dir('[COLOR %s]%s[/COLOR]  [COLOR grey](refreshes daily)[/COLOR]' % (p['color'], p['name']),
                'aidailyplay', url=str(p['index']), image=control.addonIcon())
    add_dir('[COLOR grey]Powered by Emergent Universal Key + Deezer[/COLOR]', 'settings', is_folder=False)
    end_directory()

def ai_daily_play(params):
    from resources.lib.modules import ai_playlists
    theme_index = params.get('url', '0')
    dp = control.progressDialog()
    dp.create('Syncher AI', 'Generating your daily playlist...')
    tracks = ai_playlists.get_daily_playlist_tracks(theme_index)
    dp.close()
    if not tracks:
        control.infoDialog('Could not generate playlist. Check your Emergent key in Settings.')
        return
    _show_ai_track_list(tracks, 'aidaily_%s' % theme_index)

def ai_mood_menu():
    from resources.lib.modules import ai_playlists
    key = ai_playlists._get_api_key()
    if not key:
        add_dir('[COLOR red]Set your Emergent Universal Key in Settings first[/COLOR]', 'settings', is_folder=False)
        end_directory()
        return
    moods = ai_playlists.get_mood_list()
    for m in moods:
        add_dir('[COLOR %s]%s[/COLOR]' % (m['color'], m['name']),
                'aimoodplay', url=m['id'], image=control.addonIcon())
    end_directory()

def ai_mood_play(params):
    from resources.lib.modules import ai_playlists
    mood = params.get('url', '')
    dp = control.progressDialog()
    dp.create('Syncher AI', 'Creating %s playlist...' % mood)
    tracks = ai_playlists.get_mood_playlist(mood)
    dp.close()
    if not tracks:
        control.infoDialog('Could not generate playlist. Check your Emergent key.')
        return
    _show_ai_track_list(tracks, 'mood_%s' % mood)

def ai_decades_menu():
    from resources.lib.modules import ai_playlists
    key = ai_playlists._get_api_key()
    if not key:
        add_dir('[COLOR red]Set your Emergent Universal Key in Settings first[/COLOR]', 'settings', is_folder=False)
        end_directory()
        return
    decades = ai_playlists.get_decade_list()
    for d in decades:
        add_dir('[COLOR %s]%s[/COLOR]' % (d['color'], d['name']),
                'aidecadeplay', url=d['id'], image=control.addonIcon())
    end_directory()

def ai_decade_play(params):
    from resources.lib.modules import ai_playlists
    decade = params.get('url', '')
    dp = control.progressDialog()
    dp.create('Syncher AI', 'Creating best of %s...' % decade)
    tracks = ai_playlists.get_decade_playlist(decade)
    dp.close()
    if not tracks:
        control.infoDialog('Could not generate playlist. Check your Emergent key.')
        return
    _show_ai_track_list(tracks, 'decade_%s' % decade)

def ai_similar(params):
    from resources.lib.modules import ai_playlists
    artist_name = params.get('url', '')
    if not artist_name:
        artist_name = control.keyboard('', 'Artist name')
    if not artist_name:
        return
    key = ai_playlists._get_api_key()
    if not key:
        control.infoDialog('Set your Emergent Universal Key in Settings first')
        return
    dp = control.progressDialog()
    dp.create('Syncher AI', 'Finding music similar to %s...' % artist_name)
    tracks = ai_playlists.get_similar_artist_playlist(artist_name)
    dp.close()
    if not tracks:
        control.infoDialog('Could not generate playlist. Check your Emergent key.')
        return
    _show_ai_track_list(tracks, 'similar_%s' % artist_name[:20])

def _show_ai_track_list(tracks, cache_id=''):
    """Display AI-generated track list with Deezer metadata"""
    if not tracks:
        control.infoDialog('No tracks')
        return

    # Auto-play all button
    add_dir('[COLOR gold]>>> Auto-Play All <<<[/COLOR]', 'musicautoplay',
            url='ai|%s' % cache_id, is_folder=False)

    for t in tracks:
        mins = int(t.get('duration', '0')) // 60
        secs = int(t.get('duration', '0')) % 60
        label = '%s - %s' % (t.get('artist', ''), t['title'])
        if int(t.get('duration', '0')) > 0:
            label += '  [COLOR grey](%d:%02d)[/COLOR]' % (mins, secs)

        li = xbmcgui.ListItem(label=label)
        img = t.get('image') or control.addonIcon()
        li.setArt({'icon': img, 'thumb': img, 'fanart': control.addonFanart()})
        li.setInfo('Music', {
            'title': t['title'], 'artist': t.get('artist', ''),
            'album': t.get('album', ''), 'duration': int(t.get('duration', '0')),
        })
        li.setProperty('IsPlayable', 'true')
        url_params = {
            'action': 'playmusic',
            'title': t['title'], 'artist': t.get('artist', ''),
            'album': t.get('album', ''), 'album_id': t.get('album_id', ''),
        }
        cm = [('Add to Playlist', 'RunPlugin(%s)' % build_url({
            'action': 'addtoplaylist',
            'track_id': t['id'], 'title': t['title'],
            'artist': t.get('artist', ''), 'album': t.get('album', ''),
            'album_id': t.get('album_id', ''), 'image': img,
            'duration': t.get('duration', '0'),
        }))]
        li.addContextMenuItems(cm)
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)

    end_directory('songs')

# ============================================================
# RADIO (Powered by Radio Browser API)
# ============================================================

def radio_menu():
    from resources.lib.modules import radio_api
    add_dir('[COLOR gold]Top Stations[/COLOR]', 'radiotop', image=control.addonIcon())
    add_dir('[COLOR gold]Most Popular[/COLOR]', 'radiopopular', image=control.addonIcon())
    add_dir('[COLOR gold]Trending[/COLOR]', 'radiotrending', image=control.addonIcon())
    add_dir('[COLOR skyblue]Browse by Genre[/COLOR]', 'radiogenres', image=control.addonIcon())
    add_dir('[COLOR skyblue]Browse by Country[/COLOR]', 'radiocountries', image=control.addonIcon())
    add_dir('[COLOR skyblue]Search Radio[/COLOR]', 'radiosearch', image=control.addonIcon())
    end_directory()

def radio_station_list(stations):
    """Display a list of radio stations"""
    for s in stations:
        li = xbmcgui.ListItem(label=s['label'])
        icon = s.get('icon') or control.addonIcon()
        li.setArt({'icon': icon, 'thumb': icon, 'fanart': control.addonFanart()})
        li.setInfo('Music', {'title': s['name'], 'genre': s.get('tags', '')})
        li.setProperty('IsPlayable', 'true')
        url_params = {'action': 'playradio', 'url': s['url'], 'name': s['name']}
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)
    end_directory('songs')

def radio_top():
    from resources.lib.modules import radio_api
    stations = radio_api.get_top_stations()
    radio_station_list(stations)

def radio_popular():
    from resources.lib.modules import radio_api
    stations = radio_api.get_popular_stations()
    radio_station_list(stations)

def radio_trending():
    from resources.lib.modules import radio_api
    stations = radio_api.get_trending_stations()
    radio_station_list(stations)

def radio_genres():
    from resources.lib.modules import radio_api
    tags = radio_api.get_genre_tags()
    for t in tags:
        add_dir('[COLOR %s]%s[/COLOR]' % (t['color'], t['name']),
                'radiobytag', url=t['tag'], image=control.addonIcon())
    end_directory()

def radio_by_tag(params):
    from resources.lib.modules import radio_api
    tag = params.get('url', '')
    stations = radio_api.search_by_tag(tag)
    radio_station_list(stations)

def radio_countries():
    from resources.lib.modules import radio_api
    countries = radio_api.get_countries()
    for c in countries:
        add_dir(c['name'], 'radiobycountry', url=c['code'], image=control.addonIcon())
    end_directory()

def radio_by_country(params):
    from resources.lib.modules import radio_api
    code = params.get('url', '')
    stations = radio_api.search_by_country(code)
    radio_station_list(stations)

def radio_search():
    from resources.lib.modules import radio_api
    query = control.keyboard('', 'Search Radio Stations')
    if not query:
        return
    stations = radio_api.search_stations(query)
    radio_station_list(stations)

def play_radio(params):
    """Play a live radio stream"""
    url = params.get('url', '')
    name = params.get('name', 'Radio')
    if not url:
        return
    li = xbmcgui.ListItem(label=name, path=url)
    li.setInfo('Music', {'title': name})
    li.setProperty('IsPlayable', 'true')
    xbmcplugin.setResolvedUrl(HANDLE, True, li)

# ============================================================
# PODCASTS (Powered by iTunes Search API)
# ============================================================

def podcast_menu():
    add_dir('[COLOR gold]Top Podcasts[/COLOR]', 'podcasttop', image=control.addonIcon())
    add_dir('[COLOR skyblue]Browse by Genre[/COLOR]', 'podcastgenres', image=control.addonIcon())
    add_dir('[COLOR skyblue]Search Podcasts[/COLOR]', 'podcastsearch', image=control.addonIcon())
    end_directory()

def podcast_top():
    from resources.lib.modules import podcast_api
    podcasts = podcast_api.get_top_podcasts()
    _show_podcast_list(podcasts, from_top=True)

def podcast_genres():
    from resources.lib.modules import podcast_api
    genres = podcast_api.get_genres()
    for g in genres:
        add_dir(g['name'], 'podcastbygenre', url=g['id'], image=control.addonIcon())
    end_directory()

def podcast_by_genre(params):
    from resources.lib.modules import podcast_api
    genre_id = params.get('url', '')
    podcasts = podcast_api.get_top_by_genre(genre_id)
    _show_podcast_list(podcasts)

def podcast_search():
    from resources.lib.modules import podcast_api
    query = control.keyboard('', 'Search Podcasts')
    if not query:
        return
    podcasts = podcast_api.search_podcasts(query)
    _show_podcast_list(podcasts)

def _show_podcast_list(podcasts, from_top=False):
    """Display a list of podcasts"""
    from resources.lib.modules import podcast_api
    for p in podcasts:
        label = p['name']
        if p.get('artist'):
            label += '  [COLOR grey]by %s[/COLOR]' % p['artist']
        if p.get('episode_count'):
            label += '  [COLOR grey](%s eps)[/COLOR]' % p['episode_count']

        # For top podcasts, we need to look up feed URL
        feed_url = p.get('feed_url', '')
        podcast_id = p.get('id', '')

        if from_top and not feed_url and podcast_id:
            # Will lookup on click
            add_dir(label, 'podcastlookup', url=podcast_id,
                    image=p.get('image') or control.addonIcon())
        elif feed_url:
            add_dir(label, 'podcastepisodes', url=feed_url,
                    image=p.get('image') or control.addonIcon())
        else:
            add_dir(label, 'podcastlookup', url=podcast_id,
                    image=p.get('image') or control.addonIcon())
    end_directory()

def podcast_lookup(params):
    """Lookup podcast by ID then show episodes"""
    from resources.lib.modules import podcast_api
    podcast_id = params.get('url', '')
    podcast = podcast_api.lookup_podcast(podcast_id)
    if not podcast or not podcast.get('feed_url'):
        control.infoDialog('Could not find podcast feed')
        return
    _show_podcast_episodes(podcast['feed_url'], podcast.get('image', ''), podcast.get('name', ''))

def podcast_episodes(params):
    """Show episodes from a podcast RSS feed"""
    feed_url = params.get('url', '')
    _show_podcast_episodes(feed_url)

def _show_podcast_episodes(feed_url, podcast_image='', podcast_name=''):
    from resources.lib.modules import podcast_api
    dp = control.progressDialog()
    dp.create('Syncher', 'Loading episodes...')
    episodes = podcast_api.get_episodes(feed_url)
    dp.close()
    if not episodes:
        control.infoDialog('No episodes found')
        return
    for ep in episodes:
        label = ep['title']
        if ep.get('date'):
            label += '  [COLOR grey](%s)[/COLOR]' % ep['date']
        if ep.get('duration'):
            label += '  [COLOR grey][%s][/COLOR]' % ep['duration']

        li = xbmcgui.ListItem(label=label)
        img = ep.get('image') or podcast_image or control.addonIcon()
        li.setArt({'icon': img, 'thumb': img, 'fanart': control.addonFanart()})
        li.setInfo('Music', {'title': ep['title'], 'comment': ep.get('description', '')[:500]})
        li.setProperty('IsPlayable', 'true')
        url_params = {'action': 'playpodcast', 'url': ep['url'], 'name': ep['title']}
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)

    end_directory('songs')

def play_podcast(params):
    """Play a podcast episode"""
    url = params.get('url', '')
    name = params.get('name', 'Podcast')
    if not url:
        return
    li = xbmcgui.ListItem(label=name, path=url)
    li.setInfo('Music', {'title': name})
    li.setProperty('IsPlayable', 'true')
    xbmcplugin.setResolvedUrl(HANDLE, True, li)

# ============================================================
# AUDIOBOOKS (LibriVox + Internet Archive)
# ============================================================

def audiobook_menu():
    add_dir('[COLOR gold]Popular Audiobooks[/COLOR]', 'audiobookpopular', image=control.addonIcon())
    add_dir('[COLOR gold]New Arrivals[/COLOR]', 'audiobooknew', image=control.addonIcon())
    add_dir('[COLOR skyblue]Browse by Genre[/COLOR]', 'audiobookgenres', image=control.addonIcon())
    add_dir('[COLOR skyblue]Search by Title[/COLOR]', 'audiobooksearchtitle', image=control.addonIcon())
    add_dir('[COLOR skyblue]Search by Author[/COLOR]', 'audiobooksearchauthor', image=control.addonIcon())
    add_dir('[COLOR lime]Search Internet Archive[/COLOR]', 'audiobooksearcharchive', image=control.addonIcon())
    end_directory()

def audiobook_popular():
    from resources.lib.modules import audiobook_api
    # Search popular classics on Internet Archive, sorted by downloads
    import urllib.parse
    url = '%s?q=mediatype:(audio)+AND+collection:(librivoxaudio+OR+audio_bookspoetry)&fl[]=identifier,title,creator,description,downloads&rows=50&output=json&sort[]=downloads+desc' % audiobook_api.ARCHIVE_SEARCH
    data = audiobook_api.client.request_json(url)
    books = []
    if data:
        for d in data.get('response', {}).get('docs', []):
            identifier = d.get('identifier', '')
            if not identifier:
                continue
            books.append({
                'id': identifier,
                'title': d.get('title', ''),
                'author': d.get('creator', ['Unknown'])[0] if isinstance(d.get('creator'), list) else d.get('creator', 'Unknown'),
                'description': '',
                'image': 'https://archive.org/services/img/%s' % identifier,
                'downloads': d.get('downloads', 0),
                'source': 'archive',
            })
    _show_audiobook_list(books)

def audiobook_new():
    from resources.lib.modules import audiobook_api
    books = audiobook_api.get_recent_librivox()
    _show_audiobook_list(books)

def audiobook_genres():
    from resources.lib.modules import audiobook_api
    genres = audiobook_api.get_genres()
    for g in genres:
        add_dir(g, 'audiobookbygenre', url=g, image=control.addonIcon())
    end_directory()

def audiobook_by_genre(params):
    from resources.lib.modules import audiobook_api
    genre = params.get('url', '')
    # Use Internet Archive for genre search since LibriVox genre is unreliable
    books = audiobook_api.search_archive(genre, limit=30)
    if not books:
        books = audiobook_api.get_librivox_by_genre(genre)
    _show_audiobook_list(books)

def audiobook_search_title():
    from resources.lib.modules import audiobook_api
    query = control.keyboard('', 'Search Audiobook by Title')
    if not query:
        return
    # Search both sources
    books = audiobook_api.search_archive(query)
    lv_books = audiobook_api.search_librivox(query)
    # Merge, avoiding duplicates by title
    seen = set(b['title'].lower() for b in books)
    for b in lv_books:
        if b['title'].lower() not in seen:
            books.append(b)
    _show_audiobook_list(books)

def audiobook_search_author():
    from resources.lib.modules import audiobook_api
    query = control.keyboard('', 'Search Audiobook by Author')
    if not query:
        return
    books = audiobook_api.search_archive(query)
    lv_books = audiobook_api.search_librivox_author(query)
    seen = set(b['title'].lower() for b in books)
    for b in lv_books:
        if b['title'].lower() not in seen:
            books.append(b)
    _show_audiobook_list(books)

def audiobook_search_archive():
    from resources.lib.modules import audiobook_api
    query = control.keyboard('', 'Search Internet Archive Audiobooks')
    if not query:
        return
    books = audiobook_api.search_archive(query, limit=50)
    _show_audiobook_list(books)

def _show_audiobook_list(books):
    """Display a list of audiobooks"""
    for b in books:
        label = b['title']
        if b.get('author'):
            label += '  [COLOR grey]by %s[/COLOR]' % b['author']
        if b.get('chapters'):
            label += '  [COLOR grey](%s ch)[/COLOR]' % b['chapters']
        elif b.get('downloads'):
            label += '  [COLOR grey](%s downloads)[/COLOR]' % b['downloads']
        if b.get('duration'):
            label += '  [COLOR grey][%s][/COLOR]' % b['duration']

        source = b.get('source', 'librivox')
        if source == 'archive':
            action = 'audiobookarchivechapters'
            url_val = b['id']
        else:
            action = 'audiobooklvchapters'
            url_val = b['id']

        add_dir(label, action, url=url_val,
                image=b.get('image') or control.addonIcon())
    end_directory()

def audiobook_lv_chapters(params):
    """Show chapters for a LibriVox audiobook"""
    from resources.lib.modules import audiobook_api
    book_id = params.get('url', '')
    dp = control.progressDialog()
    dp.create('Syncher', 'Loading chapters...')
    tracks = audiobook_api.get_librivox_tracks(book_id)
    dp.close()
    if not tracks:
        control.infoDialog('No chapters found')
        return
    _show_audiobook_chapters(tracks)

def audiobook_archive_chapters(params):
    """Show chapters for an Internet Archive audiobook"""
    from resources.lib.modules import audiobook_api
    identifier = params.get('url', '')
    dp = control.progressDialog()
    dp.create('Syncher', 'Loading chapters...')
    tracks = audiobook_api.get_archive_tracks(identifier)
    dp.close()
    if not tracks:
        control.infoDialog('No audio files found')
        return
    _show_audiobook_chapters(tracks)

def _show_audiobook_chapters(tracks):
    """Display audiobook chapters/tracks"""
    # Auto-play all
    if len(tracks) > 1:
        add_dir('[COLOR gold]>>> Play All Chapters <<<[/COLOR]', 'audiobookplayall',
                url=json.dumps([t['url'] for t in tracks]), is_folder=False)

    for i, t in enumerate(tracks):
        label = t['title']
        if t.get('duration'):
            dur = t['duration']
            if isinstance(dur, str) and ':' in dur:
                label += '  [COLOR grey][%s][/COLOR]' % dur
            else:
                try:
                    secs = float(dur)
                    mins = int(secs) // 60
                    s = int(secs) % 60
                    label += '  [COLOR grey][%d:%02d][/COLOR]' % (mins, s)
                except:
                    pass
        if t.get('reader'):
            label += '  [COLOR grey](%s)[/COLOR]' % t['reader']

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': control.addonIcon(), 'fanart': control.addonFanart()})
        li.setInfo('Music', {'title': t['title'], 'tracknumber': i + 1})
        li.setProperty('IsPlayable', 'true')
        url_params = {'action': 'playaudiobook', 'url': t['url'], 'name': t['title']}
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)

    end_directory('songs')

def play_audiobook(params):
    """Play an audiobook chapter"""
    url = params.get('url', '')
    name = params.get('name', 'Audiobook')
    if not url:
        return
    li = xbmcgui.ListItem(label=name, path=url)
    li.setInfo('Music', {'title': name})
    li.setProperty('IsPlayable', 'true')
    xbmcplugin.setResolvedUrl(HANDLE, True, li)

def audiobook_play_all(params):
    """Play all chapters in sequence"""
    url_data = params.get('url', '[]')
    try:
        urls = json.loads(url_data)
    except:
        return
    if not urls:
        return
    kodi_pl = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    kodi_pl.clear()
    for i, url in enumerate(urls):
        name = 'Chapter %d' % (i + 1)
        li = xbmcgui.ListItem(label=name, path=url)
        kodi_pl.add(url, li)
    xbmc.Player().play(kodi_pl)

# ============================================================
# MUSIC SCENE SEARCH
# ============================================================

def music_scene_search(params):
    query = params.get('url', '')
    if not query:
        query = control.keyboard('', 'Search Scene Sites for Music')
    if not query:
        return

    from resources.lib.scrapers import music_scraper
    dp = control.progressDialog()
    dp.create('Syncher', 'Searching scene sites for: %s...' % query)

    results = music_scraper.search_music(query)

    dp.update(80, 'Found %d links' % len(results))
    dp.close()

    if not results:
        control.infoDialog('No music links found for: %s' % query)
        return

    for s in results:
        li = xbmcgui.ListItem(label=s['label'])
        li.setArt({'icon': control.addonIcon(), 'fanart': control.addonFanart()})
        li.setProperty('IsPlayable', 'true')
        li.setInfo('Music', {'title': s.get('name', '')})
        url_params = {'action': 'playsport', 'url': s['url'], 'type': s.get('type', 'hoster')}
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)
    end_directory('songs')

# ============================================================
# MUSIC SEARCH
# ============================================================

def search_artist_menu():
    from resources.lib.modules import deezer_api
    query = control.keyboard('', 'Search Artist')
    if not query:
        return
    artists = deezer_api.search_artist(query)
    for a in artists:
        add_dir('%s  [COLOR grey](%s fans)[/COLOR]' % (a['name'], a.get('fans', '0')),
                'musicartist', url=a['id'], image=a.get('image') or control.addonIcon())
    end_directory()

def search_album_menu():
    from resources.lib.modules import deezer_api
    query = control.keyboard('', 'Search Album')
    if not query:
        return
    albums = deezer_api.search_album(query)
    for a in albums:
        label = '%s - %s' % (a.get('artist', ''), a['title']) if a.get('artist') else a['title']
        add_dir(label, 'musicalbum', url=a['id'],
                image=a.get('image') or control.addonIcon())
    end_directory()

def search_track_menu():
    from resources.lib.modules import deezer_api
    query = control.keyboard('', 'Search Track')
    if not query:
        return
    tracks = deezer_api.search_track(query)
    for t in tracks:
        mins = int(t.get('duration', '0')) // 60
        secs = int(t.get('duration', '0')) % 60
        label = '%s - %s  [COLOR grey](%d:%02d)[/COLOR]' % (t.get('artist', ''), t['title'], mins, secs)
        li = xbmcgui.ListItem(label=label)
        img = t.get('image') or control.addonIcon()
        li.setArt({'icon': img, 'thumb': img, 'fanart': control.addonFanart()})
        li.setInfo('Music', {'title': t['title'], 'artist': t.get('artist', ''), 'duration': int(t.get('duration', '0'))})
        li.setProperty('IsPlayable', 'true')
        url_params = {'action': 'playmusic', 'title': t['title'], 'artist': t.get('artist', ''), 'album': t.get('album', ''), 'album_id': t.get('album_id', '')}
        cm = [('Add to Playlist', 'RunPlugin(%s)' % build_url({
            'action': 'addtoplaylist', 'track_id': t['id'], 'title': t['title'],
            'artist': t.get('artist', ''), 'album': t.get('album', ''),
            'album_id': t.get('album_id', ''), 'image': img, 'duration': t.get('duration', '0'),
        }))]
        li.addContextMenuItems(cm)
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)
    end_directory('songs')

# ============================================================
# MUSIC AUTOPLAY & PLAYBACK
# ============================================================

def music_autoplay(params):
    """Build a Kodi playlist and auto-play all tracks"""
    from resources.lib.modules import deezer_api
    from resources.lib.modules import playlists as pl

    url = params.get('url', '')
    parts = url.split('|', 1)
    if len(parts) != 2:
        return
    source_type, source_id = parts

    tracks = []
    if source_type == 'album':
        tracks = deezer_api.get_album_tracks(source_id)
        album = deezer_api.get_album(source_id)
        album_name = album.get('title', '') if album else ''
        artist_name = album.get('artist', '') if album else ''
    elif source_type == 'playlist':
        tracks = deezer_api.get_playlist_tracks(source_id)
        album_name = ''
        artist_name = ''
    elif source_type == 'myplaylist':
        data = pl.get(source_id)
        if data:
            tracks = data.get('tracks', [])
        album_name = ''
        artist_name = ''
    elif source_type == 'ai':
        from resources.lib.modules import ai_playlists
        cached = ai_playlists._load_cache(source_id)
        if cached:
            tracks = cached
        album_name = ''
        artist_name = ''
    else:
        return

    if not tracks:
        control.infoDialog('No tracks to play')
        return

    # Search for the first track, play it, queue the rest
    first_track = tracks[0]
    query = '%s %s' % (first_track.get('artist', artist_name), first_track.get('title', ''))

    dp = control.progressDialog()
    dp.create('Syncher', 'Searching for: %s (%d tracks)...' % (query, len(tracks)))

    # Find sources for first track
    from resources.lib.scrapers import music_scraper
    results = music_scraper.search_music(query.strip())

    dp.close()

    if results:
        # Resolve and play first result
        resolved = sources.resolve_source(results[0])
        if resolved:
            kodi_pl = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
            kodi_pl.clear()
            li = xbmcgui.ListItem(label='%s - %s' % (first_track.get('artist', ''), first_track['title']), path=resolved)
            kodi_pl.add(resolved, li)

            # Queue remaining tracks as search references
            for t in tracks[1:]:
                t_label = '%s - %s' % (t.get('artist', artist_name), t.get('title', ''))
                t_li = xbmcgui.ListItem(label=t_label)
                t_url = build_url({'action': 'playmusic', 'title': t.get('title', ''), 'artist': t.get('artist', artist_name), 'album': album_name})
                kodi_pl.add(t_url, t_li)

            xbmc.Player().play(kodi_pl)
            return

    control.infoDialog('No sources found for: %s' % query)

def play_music(params):
    """Play a single music track by searching scene sites"""
    title = params.get('title', '')
    artist = params.get('artist', '')
    album = params.get('album', '')

    query = '%s %s' % (artist, title)
    query = query.strip()
    if not query:
        return

    dp = control.progressDialog()
    dp.create('Syncher', 'Searching for: %s...' % query)

    from resources.lib.scrapers import music_scraper
    results = music_scraper.search_music(query)

    # Also try album name
    if not results and album:
        dp.update(50, 'Trying album: %s %s...' % (artist, album))
        results = music_scraper.search_music('%s %s' % (artist, album))

    dp.close()

    if not results:
        control.infoDialog('No sources found for: %s' % query)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    if len(results) == 1 or control.setting('autoplay') == 'true':
        resolved = sources.resolve_source(results[0])
        if resolved:
            li = xbmcgui.ListItem(path=resolved)
            xbmcplugin.setResolvedUrl(HANDLE, True, li)
            return
    else:
        labels = [s.get('label', s.get('name', 'Unknown')) for s in results]
        choice = xbmcgui.Dialog().select('Select Source', labels)
        if choice >= 0:
            resolved = sources.resolve_source(results[choice])
            if resolved:
                li = xbmcgui.ListItem(path=resolved)
                xbmcplugin.setResolvedUrl(HANDLE, True, li)
                return

    control.infoDialog('Failed to resolve source')
    xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

# ============================================================
# TRAKT MENU
# ============================================================

def trakt_menu():
    if not trakt_api.get_credentials():
        add_dir('[COLOR red]Not authorized - Go to Settings > Debrid Services > Authorize Trakt[/COLOR]', 'settings', is_folder=False)
    else:
        add_dir('[COLOR skyblue]Movie Watchlist[/COLOR]', 'movies', url='/users/me/watchlist/movies')
        add_dir('[COLOR skyblue]Movie Collection[/COLOR]', 'movies', url='/users/me/collection/movies')
        add_dir('[COLOR skyblue]Movie History[/COLOR]', 'movies', url='/users/me/history/movies?limit=40&page=1')
        add_dir('[COLOR skyblue]TV Watchlist[/COLOR]', 'tvshows', url='/users/me/watchlist/shows')
        add_dir('[COLOR skyblue]TV Collection[/COLOR]', 'tvshows', url='/users/me/collection/shows')
        add_dir('[COLOR skyblue]Recommendations (Movies)[/COLOR]', 'movies', url='/recommendations/movies?limit=40')
        add_dir('[COLOR skyblue]Recommendations (Shows)[/COLOR]', 'tvshows', url='/recommendations/shows?limit=40')
        add_dir('[COLOR skyblue]My Lists[/COLOR]', 'traktlists')
    end_directory()

def trakt_lists():
    result = trakt_api.call('/users/me/lists', auth=True)
    if result:
        for l in result:
            name = l.get('name', '')
            slug = l.get('ids', {}).get('slug', '')
            add_dir('[COLOR skyblue]%s[/COLOR]' % name, 'traktlistitems', url=slug)
    end_directory()

def trakt_list_items(params):
    slug = params.get('url', '')
    result = trakt_api.call('/users/me/lists/%s/items?extended=full' % slug, auth=True)
    if result:
        for entry in result:
            if entry.get('type') == 'movie' and entry.get('movie'):
                item = trakt_api._parse_movie(entry['movie'])
                meta = tmdb_api.get_movie_meta(tmdb_id=item.get('tmdb'), imdb_id=item.get('imdb'))
                if meta:
                    item.update({k: v for k, v in meta.items() if v and v != '0'})
                add_movie_item(item, meta)
            elif entry.get('type') == 'show' and entry.get('show'):
                item = trakt_api._parse_show(entry['show'])
                meta = tmdb_api.get_show_meta(tmdb_id=item.get('tmdb'), imdb_id=item.get('imdb'))
                if meta:
                    item.update({k: v for k, v in meta.items() if v and v != '0'})
                add_show_item(item, meta)
    end_directory()

# ============================================================
# SEARCH
# ============================================================

def search_menu():
    add_dir('[COLOR skyblue]Search Movies[/COLOR]', 'searchmovie')
    add_dir('[COLOR skyblue]Search TV Shows[/COLOR]', 'searchtv')
    add_dir('[COLOR skyblue]Search Music (Deezer)[/COLOR]', 'searchtrack')
    add_dir('[COLOR skyblue]Search Music (Scene Sites)[/COLOR]', 'musicscenesearch')
    add_dir('[COLOR skyblue]Search Podcasts[/COLOR]', 'podcastsearch')
    add_dir('[COLOR skyblue]Search Audiobooks[/COLOR]', 'audiobooksearchtitle')
    end_directory()

def search_movie():
    query = control.keyboard('', 'Search Movies')
    if not query:
        return
    items = trakt_api.search_movies(query)
    for item in items:
        meta = tmdb_api.get_movie_meta(tmdb_id=item.get('tmdb'), imdb_id=item.get('imdb'))
        if meta:
            item.update({k: v for k, v in meta.items() if v and v != '0'})
        add_movie_item(item, meta)
    end_directory('movies')

def search_tv():
    query = control.keyboard('', 'Search TV Shows')
    if not query:
        return
    items = trakt_api.search_shows(query)
    for item in items:
        meta = tmdb_api.get_show_meta(tmdb_id=item.get('tmdb'), imdb_id=item.get('imdb'))
        if meta:
            item.update({k: v for k, v in meta.items() if v and v != '0'})
        add_show_item(item, meta)
    end_directory('tvshows')

# ============================================================
# PLAYBACK
# ============================================================

def play_movie(params):
    title = params.get('title', '')
    year = params.get('year', '')
    imdb = params.get('imdb', '')

    dp = control.progressDialog()
    dp.create('Syncher', 'Scraping sources for: %s (%s)...' % (title, year))

    source_list = sources.get_movie_sources(title, year, imdb)

    dp.update(50, 'Found %d sources. Preparing...' % len(source_list))

    if not source_list:
        dp.close()
        control.infoDialog('No sources found for %s' % title)
        return

    dp.close()

    # Auto-play or source select
    if control.setting('autoplay') == 'true':
        _autoplay(source_list)
    else:
        _source_select(source_list)

def play_episode(params):
    title = params.get('title', '')
    year = params.get('year', '')
    imdb = params.get('imdb', '')
    season = params.get('season', '1')
    episode = params.get('episode', '1')

    dp = control.progressDialog()
    dp.create('Syncher', 'Scraping sources for: %s S%sE%s...' % (title, str(season).zfill(2), str(episode).zfill(2)))

    source_list = sources.get_episode_sources(title, season, episode, imdb)

    dp.update(50, 'Found %d sources. Preparing...' % len(source_list))

    if not source_list:
        dp.close()
        control.infoDialog('No sources found')
        return

    dp.close()

    if control.setting('autoplay') == 'true':
        _autoplay(source_list)
    else:
        _source_select(source_list)

def play_sport(params):
    url = params.get('url', '')
    source_type = params.get('type', 'direct')

    if source_type == 'torrent' or url.startswith('magnet:'):
        resolved = sources._resolve_torrent(url)
    elif source_type == 'hoster':
        resolved = sources._resolve_hoster(url)
    else:
        resolved = url

    if resolved:
        li = xbmcgui.ListItem(path=resolved)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        control.infoDialog('Could not resolve source')
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

def _autoplay(source_list):
    for source in source_list:
        try:
            resolved = sources.resolve_source(source)
            if resolved:
                li = xbmcgui.ListItem(path=resolved)
                xbmcplugin.setResolvedUrl(HANDLE, True, li)
                return
        except:
            continue
    control.infoDialog('All sources failed to resolve')
    xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

def _source_select(source_list):
    labels = [s.get('label', s.get('name', 'Unknown')) for s in source_list]
    choice = xbmcgui.Dialog().select('Select Source (%d found)' % len(source_list), labels)
    if choice < 0:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    selected = source_list[choice]
    resolved = sources.resolve_source(selected)
    if resolved:
        li = xbmcgui.ListItem(path=resolved)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    else:
        control.infoDialog('Failed to resolve: %s' % selected.get('source', ''))
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())

# ============================================================
# AUTH ACTIONS
# ============================================================

def auth_trakt():
    trakt_api.auth()

def auth_rd():
    from resources.lib.resolvers import realdebrid
    realdebrid.auth()

def auth_pm():
    from resources.lib.resolvers import premiumize
    premiumize.auth()

def auth_ad():
    from resources.lib.resolvers import alldebrid
    alldebrid.auth()

def auth_tb():
    from resources.lib.resolvers import torbox
    torbox.auth()

# ============================================================
# ROUTER
# ============================================================

def router():
    params = get_params()
    action = params.get('action', '')
    url = params.get('url', '')

    if not action:
        main_menu()

    # Menus
    elif action == 'moviesmenu': movies_menu()
    elif action == 'tvmenu': tv_menu()
    elif action == 'sportsmenu': sports_menu()
    elif action == 'musicmenu': music_menu()
    elif action == 'traktmenu': trakt_menu()
    elif action == 'searchmenu': search_menu()
    elif action == 'settings': control.openSettings()

    # Movie lists
    elif action == 'movies':
        page = 1
        if 'page=' in url:
            import re
            page_match = re.search(r'page=(\d+)', url)
            if page_match:
                page = int(page_match.group(1))
                url = re.sub(r'page=\d+&?', '', url).rstrip('&').rstrip('?')
        movie_list(url, page)
    elif action == 'moviegenres': movie_genres()
    elif action == 'movieyears': movie_years()
    elif action == 'moviecerts': movie_certs()

    # TV lists
    elif action == 'tvshows':
        page = 1
        if 'page=' in url:
            import re
            page_match = re.search(r'page=(\d+)', url)
            if page_match:
                page = int(page_match.group(1))
                url = re.sub(r'page=\d+&?', '', url).rstrip('&').rstrip('?')
        tv_list(url, page)
    elif action == 'tvgenres': tv_genres()
    elif action == 'tvyears': tv_years()
    elif action == 'seasons': seasons(params)
    elif action == 'episodes': episodes(params)

    # Sports
    elif action == 'sportcats': sport_categories(url)
    elif action == 'sportitems': sport_items(params)
    elif action == 'sportsources': sport_sources(params)
    elif action == 'playsport': play_sport(params)

    # Music - Browsing
    elif action == 'musictracks': music_tracks(params)
    elif action == 'musicalbums': music_albums(params)
    elif action == 'musicartists': music_artists(params)
    elif action == 'musicgenres': music_genres()
    elif action == 'musicgenreartists': music_genre_artists(params)
    elif action == 'musicartist': music_artist(params)
    elif action == 'musicrelated': music_related(params)
    elif action == 'musicalbum': music_album(params)
    elif action == 'musicplaylists': music_playlists(params)
    elif action == 'musicplaylist': music_playlist(params)
    elif action == 'musicscenesearch': music_scene_search(params)

    # Music - AI Playlists (Emergent Universal Key)
    elif action == 'aidaily': ai_daily_menu()
    elif action == 'aidailyplay': ai_daily_play(params)
    elif action == 'aimood': ai_mood_menu()
    elif action == 'aimoodplay': ai_mood_play(params)
    elif action == 'aidecades': ai_decades_menu()
    elif action == 'aidecadeplay': ai_decade_play(params)
    elif action == 'aisimilar': ai_similar(params)

    # Music - Radio
    elif action == 'radiomenu': radio_menu()
    elif action == 'radiotop': radio_top()
    elif action == 'radiopopular': radio_popular()
    elif action == 'radiotrending': radio_trending()
    elif action == 'radiogenres': radio_genres()
    elif action == 'radiobytag': radio_by_tag(params)
    elif action == 'radiocountries': radio_countries()
    elif action == 'radiobycountry': radio_by_country(params)
    elif action == 'radiosearch': radio_search()
    elif action == 'playradio': play_radio(params)

    # Music - Search
    elif action == 'searchartist': search_artist_menu()
    elif action == 'searchalbum': search_album_menu()
    elif action == 'searchtrack': search_track_menu()

    # Music - User Playlists
    elif action == 'myplaylists': my_playlists()
    elif action == 'createplaylist': create_playlist()
    elif action == 'myplaylist': my_playlist(params)
    elif action == 'addtoplaylist': add_to_playlist(params)
    elif action == 'removefromplaylist': remove_from_playlist(params)
    elif action == 'deleteplaylist': delete_playlist(params)
    elif action == 'shuffleplay': shuffle_play(params)
    elif action == 'sortplaylist': sort_playlist(params)
    elif action == 'exportplaylist': export_playlist(params)
    elif action == 'importplaylist': import_playlist_menu()

    # Music - Playback
    elif action == 'musicautoplay': music_autoplay(params)
    elif action == 'playmusic': play_music(params)

    # Podcasts
    elif action == 'podcastmenu': podcast_menu()
    elif action == 'podcasttop': podcast_top()
    elif action == 'podcastgenres': podcast_genres()
    elif action == 'podcastbygenre': podcast_by_genre(params)
    elif action == 'podcastsearch': podcast_search()
    elif action == 'podcastlookup': podcast_lookup(params)
    elif action == 'podcastepisodes': podcast_episodes(params)
    elif action == 'playpodcast': play_podcast(params)

    # Audiobooks
    elif action == 'audiobookmenu': audiobook_menu()
    elif action == 'audiobookpopular': audiobook_popular()
    elif action == 'audiobooknew': audiobook_new()
    elif action == 'audiobookgenres': audiobook_genres()
    elif action == 'audiobookbygenre': audiobook_by_genre(params)
    elif action == 'audiobooksearchtitle': audiobook_search_title()
    elif action == 'audiobooksearchauthor': audiobook_search_author()
    elif action == 'audiobooksearcharchive': audiobook_search_archive()
    elif action == 'audiobooklvchapters': audiobook_lv_chapters(params)
    elif action == 'audiobookarchivechapters': audiobook_archive_chapters(params)
    elif action == 'playaudiobook': play_audiobook(params)
    elif action == 'audiobookplayall': audiobook_play_all(params)

    # Trakt
    elif action == 'traktlists': trakt_lists()
    elif action == 'traktlistitems': trakt_list_items(params)

    # Search
    elif action == 'searchmovie': search_movie()
    elif action == 'searchtv': search_tv()

    # Playback
    elif action == 'playmovie': play_movie(params)
    elif action == 'playepisode': play_episode(params)

    # Auth
    elif action == 'authTrakt': auth_trakt()
    elif action == 'rdAuth': auth_rd()
    elif action == 'pmAuth': auth_pm()
    elif action == 'adAuth': auth_ad()
    elif action == 'tbAuth': auth_tb()


if __name__ == '__main__':
    router()
