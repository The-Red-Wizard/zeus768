# -*- coding: utf-8 -*-
"""
Syncher v2.0.0 by zeus768
Scene Release Downloader and Streamer with Debrid, Trakt, RapidRAR
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
    add_dir('[COLOR skyblue]My Trakt[/COLOR]', 'traktmenu', image=control.addonIcon())
    add_dir('[COLOR skyblue]Search[/COLOR]', 'searchmenu', image=control.addonIcon())
    add_dir('[COLOR white]Settings[/COLOR]', 'settings', image=control.addonIcon(), is_folder=False)

    # Info notice about debrid
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
    add_dir('[COLOR gold]Search Music[/COLOR]', 'searchmusic')
    add_dir('[COLOR gold]Trending Music Videos[/COLOR]', 'musictrending')
    end_directory()

def music_trending():
    # Use Trakt-like search for music content from scene sites
    control.infoDialog('Searching scene sites for music releases...')
    from resources.lib.scrapers import rlsbb, ddlvalley

    all_sources = []
    for scraper_mod in [rlsbb, ddlvalley]:
        try:
            results = scraper_mod._search('music discography mp3 flac')
            for url, name in results[:15]:
                li = xbmcgui.ListItem(label=name)
                li.setArt({'icon': control.addonIcon(), 'fanart': control.addonFanart()})
                li.setInfo('Video', {'title': name})
                url_params = {'action': 'musiclinks', 'url': url, 'name': name}
                xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=True)
        except:
            pass
    end_directory()

def music_links(params):
    url = params.get('url', '')
    from resources.lib.scrapers import rlsbb, ddlvalley

    links = []
    try:
        links = rlsbb._get_links(url)
    except:
        pass
    if not links:
        try:
            links = ddlvalley._get_links(url)
        except:
            pass

    for link_url in links:
        is_magnet = link_url.startswith('magnet:')
        import re
        hoster = 'Torrent' if is_magnet else re.findall(r'https?://(?:www\.)?([^/]+)', link_url)[0].split('.')[0].title()
        label = '[COLOR gold]%s[/COLOR]' % hoster

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': control.addonIcon(), 'fanart': control.addonFanart()})
        li.setProperty('IsPlayable', 'true')
        li.setInfo('Video', {'title': label})
        url_params = {'action': 'playsport', 'url': link_url, 'type': 'torrent' if is_magnet else 'hoster'}
        xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=False)
    end_directory()

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
    add_dir('[COLOR skyblue]Search Music[/COLOR]', 'searchmusic')
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

def search_music():
    query = control.keyboard('', 'Search Music')
    if not query:
        return
    from resources.lib.scrapers import rlsbb, ddlvalley
    for scraper_mod in [rlsbb, ddlvalley]:
        try:
            results = scraper_mod._search(query)
            for url, name in results[:15]:
                li = xbmcgui.ListItem(label=name)
                li.setArt({'icon': control.addonIcon(), 'fanart': control.addonFanart()})
                li.setInfo('Video', {'title': name})
                url_params = {'action': 'musiclinks', 'url': url, 'name': name}
                xbmcplugin.addDirectoryItem(HANDLE, build_url(url_params), li, isFolder=True)
        except:
            pass
    end_directory()

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

    # Music
    elif action == 'musictrending': music_trending()
    elif action == 'musiclinks': music_links(params)

    # Trakt
    elif action == 'traktlists': trakt_lists()
    elif action == 'traktlistitems': trakt_list_items(params)

    # Search
    elif action == 'searchmovie': search_movie()
    elif action == 'searchtv': search_tv()
    elif action == 'searchmusic': search_music()

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
