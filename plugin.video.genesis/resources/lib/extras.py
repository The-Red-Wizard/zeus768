# -*- coding: utf-8 -*-
"""
Genesis Extras Module - Extras Tab
Provides a rich browsable extras menu for movies and TV shows:
- Trailers & Videos (YouTube via TMDB)
- Cast & Crew (clickable -> filmography, other movies)
- Reviews (TMDB user reviews)
- Recommended & Similar titles
- Image Gallery (posters, backdrops, stills)
- Trivia & Facts (budget, box office, awards, keywords)
- TV: Season overview, guest stars, episode videos
"""
import json
import sys
import os
import time
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
from urllib.request import urlopen, Request
from urllib.parse import quote_plus

ADDON_ID = 'plugin.video.genesis'
HANDLE = int(sys.argv[1])

_cache = {}
_CACHE_TTL = 900  # 15 min


def _get_addon_art():
    addon_path = xbmcvfs.translatePath(f'special://home/addons/{ADDON_ID}/')
    return (
        os.path.join(addon_path, 'icon.png'),
        os.path.join(addon_path, 'fanart.jpg'),
    )


def _tmdb_key():
    try:
        addon = xbmcaddon.Addon()
        k = addon.getSetting('tmdb_api_key')
        if k and len(k) > 10:
            return k
    except:
        pass
    return 'f15af109700aab95d564acda15bdcd97'


def _http(url, timeout=10):
    key = url
    now = time.time()
    if key in _cache and now - _cache[key][0] < _CACHE_TTL:
        return _cache[key][1]
    try:
        req = Request(url, headers={'User-Agent': 'Genesis Kodi Addon'})
        resp = urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode('utf-8'))
        _cache[key] = (now, data)
        return data
    except Exception as e:
        xbmc.log(f'Extras HTTP error: {e}', xbmc.LOGWARNING)
        return None


def _tmdb(path, extra_params=''):
    api_key = _tmdb_key()
    sep = '&' if '?' in path else '?'
    url = f'https://api.themoviedb.org/3{path}{sep}api_key={api_key}'
    if extra_params:
        url += f'&{extra_params}'
    return _http(url)


def _img(path, size='w500'):
    if path:
        return f'https://image.tmdb.org/t/p/{size}{path}'
    return ''


def _build_url(action, **kwargs):
    parts = [f'{sys.argv[0]}?action={action}']
    for k, v in kwargs.items():
        if v is not None and v != '':
            parts.append(f'{k}={quote_plus(str(v))}')
    return '&'.join(parts)


# ═══════════════════════════════════════════════════════════════
# MAIN EXTRAS MENU
# ═══════════════════════════════════════════════════════════════

def show_extras(tmdb_id, media_type='movie', title='', imdb_id='', season='', episode=''):
    """Extras tab - main hub"""
    icon, fanart = _get_addon_art()
    tmdb_id = str(tmdb_id)

    # Fetch basic details to get poster for the hub
    if media_type == 'movie':
        details = _tmdb(f'/movie/{tmdb_id}')
    else:
        details = _tmdb(f'/tv/{tmdb_id}')

    poster = _img(details.get('poster_path')) if details else icon
    backdrop = _img(details.get('backdrop_path'), 'original') if details else fanart

    items = [
        ('[B]Trailers & Videos[/B]', 'extras_videos',
         dict(tmdb_id=tmdb_id, media_type=media_type, title=title), True),
        ('[B]Cast & Crew[/B]', 'extras_cast',
         dict(tmdb_id=tmdb_id, media_type=media_type, title=title), True),
        ('[B]Reviews[/B]', 'extras_reviews',
         dict(tmdb_id=tmdb_id, media_type=media_type, title=title), True),
        ('[B]Recommended[/B]', 'extras_recommended',
         dict(tmdb_id=tmdb_id, media_type=media_type, title=title), True),
        ('[B]Similar[/B]', 'extras_similar',
         dict(tmdb_id=tmdb_id, media_type=media_type, title=title), True),
        ('[B]Image Gallery[/B]', 'extras_images',
         dict(tmdb_id=tmdb_id, media_type=media_type, title=title), True),
        ('[B]Trivia & Facts[/B]', 'extras_trivia',
         dict(tmdb_id=tmdb_id, media_type=media_type, title=title, imdb_id=imdb_id), False),
    ]

    if media_type == 'tv' and season:
        items.insert(3, (
            f'[B]Season {season} Overview[/B]', 'extras_season',
            dict(tmdb_id=tmdb_id, title=title, season=season), True
        ))

    for label, action, params, is_folder in items:
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': backdrop})
        url = _build_url(action, **params)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)

    xbmcplugin.endOfDirectory(HANDLE)


# ═══════════════════════════════════════════════════════════════
# TRAILERS & VIDEOS
# ═══════════════════════════════════════════════════════════════

def show_videos(tmdb_id, media_type='movie', title=''):
    """Trailers, teasers, featurettes, behind-the-scenes"""
    icon, fanart = _get_addon_art()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    data = _tmdb(f'/{endpoint}/{tmdb_id}/videos')

    if not data or not data.get('results'):
        xbmcgui.Dialog().notification('Extras', 'No videos found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    # Sort: trailers first, then teasers, then the rest
    type_order = {'Trailer': 0, 'Teaser': 1, 'Clip': 2, 'Featurette': 3,
                  'Behind the Scenes': 4, 'Bloopers': 5}
    videos = sorted(data['results'], key=lambda v: type_order.get(v.get('type', ''), 9))

    for v in videos:
        site = v.get('site', '')
        key = v.get('key', '')
        vid_type = v.get('type', 'Video')
        vid_name = v.get('name', vid_type)
        size = v.get('size', 0)

        if site != 'YouTube' or not key:
            continue

        label = f'[COLOR yellow]{vid_type}[/COLOR]  {vid_name}'
        if size:
            label += f'  [COLOR grey]({size}p)[/COLOR]'

        thumb = f'https://img.youtube.com/vi/{key}/hqdefault.jpg'

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})
        li.setProperty('IsPlayable', 'true')

        # Play via YouTube plugin or direct
        url = f'plugin://plugin.video.youtube/play/?video_id={key}'
        xbmcplugin.addDirectoryItem(HANDLE, url, li, False)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


# ═══════════════════════════════════════════════════════════════
# CAST & CREW
# ═══════════════════════════════════════════════════════════════

def show_cast(tmdb_id, media_type='movie', title=''):
    """Browsable cast and crew list - click for filmography"""
    icon, fanart = _get_addon_art()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    data = _tmdb(f'/{endpoint}/{tmdb_id}/credits')

    if not data:
        xbmcgui.Dialog().notification('Extras', 'No cast info found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    # Cast
    for person in data.get('cast', [])[:20]:
        name = person.get('name', '')
        character = person.get('character', '')
        person_id = person.get('id')
        profile = _img(person.get('profile_path'), 'w185') or icon

        label = f'[B]{name}[/B]'
        if character:
            label += f'  [I]as {character}[/I]'

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': profile, 'thumb': profile, 'poster': profile, 'fanart': fanart})

        url = _build_url('extras_person', person_id=person_id, person_name=name)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)

    # Separator
    sep = xbmcgui.ListItem(label='[COLOR grey]--- Crew ---[/COLOR]')
    sep.setArt({'icon': icon, 'fanart': fanart})
    xbmcplugin.addDirectoryItem(HANDLE, '', sep, False)

    # Key crew
    key_jobs = {'Director', 'Writer', 'Screenplay', 'Story', 'Producer',
                'Executive Producer', 'Director of Photography', 'Original Music Composer',
                'Music', 'Editor', 'Creator', 'Showrunner'}
    seen = set()
    for person in data.get('crew', []):
        job = person.get('job', '')
        pid = person.get('id')
        if job not in key_jobs or pid in seen:
            continue
        seen.add(pid)

        name = person.get('name', '')
        profile = _img(person.get('profile_path'), 'w185') or icon
        label = f'[COLOR yellow]{job}[/COLOR]  {name}'

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': profile, 'thumb': profile, 'poster': profile, 'fanart': fanart})
        url = _build_url('extras_person', person_id=pid, person_name=name)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)

    xbmcplugin.setContent(HANDLE, 'artists')
    xbmcplugin.endOfDirectory(HANDLE)


def show_person(person_id, person_name=''):
    """Person detail hub: bio + filmography (movies & TV)"""
    icon, fanart = _get_addon_art()

    person = _tmdb(f'/person/{person_id}', 'append_to_response=combined_credits,images')
    if not person:
        xbmcgui.Dialog().notification('Extras', 'Person not found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    # Bio header
    bio = person.get('biography', '')
    born = person.get('birthday', '')
    birthplace = person.get('place_of_birth', '')
    profile = _img(person.get('profile_path'), 'w500') or icon

    bio_parts = []
    if born:
        bio_parts.append(f'Born: {born}')
    if birthplace:
        bio_parts.append(f'From: {birthplace}')
    if bio:
        bio_parts.append(bio[:400])
    bio_text = '\n'.join(bio_parts)

    if bio_text:
        li = xbmcgui.ListItem(label=f'[B]{person_name}[/B]')
        li.setArt({'icon': profile, 'thumb': profile, 'poster': profile, 'fanart': fanart})
        info_tag = li.getVideoInfoTag()
        info_tag.setPlot(bio_text)
        xbmcplugin.addDirectoryItem(HANDLE, '', li, False)

    # Movie credits
    credits = person.get('combined_credits', {})
    movies = sorted(
        [c for c in credits.get('cast', []) if c.get('media_type') == 'movie' and c.get('title')],
        key=lambda x: x.get('popularity', 0), reverse=True
    )[:20]

    if movies:
        sep = xbmcgui.ListItem(label='[COLOR gold][B]--- Movies ---[/B][/COLOR]')
        sep.setArt({'icon': icon, 'fanart': fanart})
        xbmcplugin.addDirectoryItem(HANDLE, '', sep, False)

        for m in movies:
            t = m.get('title', '')
            yr = (m.get('release_date') or '')[:4]
            mid = m.get('id')
            char = m.get('character', '')
            poster_url = _img(m.get('poster_path')) or icon

            label = f'{t} ({yr})' if yr else t
            if char:
                label += f'  [I]as {char}[/I]'

            li = xbmcgui.ListItem(label=label)
            li.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url, 'fanart': fanart})
            li.setProperty('IsPlayable', 'true')

            li.addContextMenuItems([
                ('Extras', f'Container.Update(plugin://{ADDON_ID}/?action=extras_hub&tmdb_id={mid}&media_type=movie&title={quote_plus(t)})'),
            ])

            url = f'{sys.argv[0]}?action=play&title={quote_plus(t)}&year={yr}&tmdb_id={mid}'
            xbmcplugin.addDirectoryItem(HANDLE, url, li, False)

    # TV credits
    shows = sorted(
        [c for c in credits.get('cast', []) if c.get('media_type') == 'tv' and c.get('name')],
        key=lambda x: x.get('popularity', 0), reverse=True
    )[:15]

    if shows:
        sep = xbmcgui.ListItem(label='[COLOR gold][B]--- TV Shows ---[/B][/COLOR]')
        sep.setArt({'icon': icon, 'fanart': fanart})
        xbmcplugin.addDirectoryItem(HANDLE, '', sep, False)

        for s in shows:
            t = s.get('name', '')
            yr = (s.get('first_air_date') or '')[:4]
            sid = s.get('id')
            char = s.get('character', '')
            poster_url = _img(s.get('poster_path')) or icon

            label = f'{t} ({yr})' if yr else t
            if char:
                label += f'  [I]as {char}[/I]'

            li = xbmcgui.ListItem(label=label)
            li.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url, 'fanart': fanart})

            url = f'{sys.argv[0]}?action=show_seasons&tmdb_id={sid}&title={quote_plus(t)}'
            xbmcplugin.addDirectoryItem(HANDLE, url, li, True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


# ═══════════════════════════════════════════════════════════════
# REVIEWS
# ═══════════════════════════════════════════════════════════════

def show_reviews(tmdb_id, media_type='movie', title=''):
    """TMDB user reviews"""
    icon, fanart = _get_addon_art()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    data = _tmdb(f'/{endpoint}/{tmdb_id}/reviews')

    if not data or not data.get('results'):
        xbmcgui.Dialog().notification('Extras', 'No reviews found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    for r in data['results'][:10]:
        author = r.get('author', 'Anonymous')
        content = r.get('content', '')
        rating = r.get('author_details', {}).get('rating')
        avatar = r.get('author_details', {}).get('avatar_path', '')

        rating_str = f'  [COLOR gold]{rating}/10[/COLOR]' if rating else ''
        label = f'[B]{author}[/B]{rating_str}'

        avatar_url = ''
        if avatar:
            if avatar.startswith('/http'):
                avatar_url = avatar[1:]
            else:
                avatar_url = _img(avatar, 'w185')

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': avatar_url or icon, 'thumb': avatar_url or icon, 'fanart': fanart})
        info_tag = li.getVideoInfoTag()
        info_tag.setPlot(content[:1500])

        xbmcplugin.addDirectoryItem(HANDLE, '', li, False)

    xbmcplugin.endOfDirectory(HANDLE)


# ═══════════════════════════════════════════════════════════════
# RECOMMENDED & SIMILAR
# ═══════════════════════════════════════════════════════════════

def _show_title_list(tmdb_id, media_type, list_type):
    """Generic similar/recommended list builder"""
    icon, fanart = _get_addon_art()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    data = _tmdb(f'/{endpoint}/{tmdb_id}/{list_type}')

    if not data or not data.get('results'):
        xbmcgui.Dialog().notification('Extras', f'No {list_type} found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    for item in data['results'][:20]:
        if media_type == 'movie':
            t = item.get('title', '')
            yr = (item.get('release_date') or '')[:4]
        else:
            t = item.get('name', '')
            yr = (item.get('first_air_date') or '')[:4]

        mid = item.get('id')
        rating = item.get('vote_average', 0)
        poster = _img(item.get('poster_path')) or icon
        backdrop = _img(item.get('backdrop_path'), 'original') or fanart
        overview = item.get('overview', '')

        label = f'{t} ({yr})' if yr else t
        if rating:
            label += f'  [COLOR gold]{rating:.1f}[/COLOR]'

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'fanart': backdrop})
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(t)
        info_tag.setYear(int(yr) if yr else 0)
        info_tag.setPlot(overview)
        info_tag.setRating(rating)

        li.addContextMenuItems([
            ('Extras', f'Container.Update(plugin://{ADDON_ID}/?action=extras_hub&tmdb_id={mid}&media_type={media_type}&title={quote_plus(t)})'),
        ])

        if media_type == 'movie':
            info_tag.setMediaType('movie')
            li.setProperty('IsPlayable', 'true')
            url = f'{sys.argv[0]}?action=play&title={quote_plus(t)}&year={yr}&tmdb_id={mid}'
            xbmcplugin.addDirectoryItem(HANDLE, url, li, False)
        else:
            info_tag.setMediaType('tvshow')
            url = f'{sys.argv[0]}?action=show_seasons&tmdb_id={mid}&title={quote_plus(t)}'
            xbmcplugin.addDirectoryItem(HANDLE, url, li, True)

    content = 'movies' if media_type == 'movie' else 'tvshows'
    xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.endOfDirectory(HANDLE)


def show_recommended(tmdb_id, media_type='movie', title=''):
    _show_title_list(tmdb_id, media_type, 'recommendations')


def show_similar(tmdb_id, media_type='movie', title=''):
    _show_title_list(tmdb_id, media_type, 'similar')


# ═══════════════════════════════════════════════════════════════
# IMAGE GALLERY
# ═══════════════════════════════════════════════════════════════

def show_images(tmdb_id, media_type='movie', title=''):
    """Posters, backdrops, stills - viewable as slideshow"""
    icon, fanart = _get_addon_art()
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    data = _tmdb(f'/{endpoint}/{tmdb_id}/images')

    if not data:
        xbmcgui.Dialog().notification('Extras', 'No images found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    count = 0

    # Backdrops
    for img in data.get('backdrops', [])[:15]:
        path = img.get('file_path', '')
        if not path:
            continue
        full = _img(path, 'original')
        thumb = _img(path, 'w780')
        w = img.get('width', 0)
        h = img.get('height', 0)

        label = f'[COLOR cyan]Backdrop[/COLOR]  {w}x{h}'
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': thumb, 'thumb': thumb, 'fanart': full})
        xbmcplugin.addDirectoryItem(HANDLE, full, li, False)
        count += 1

    # Posters
    for img in data.get('posters', [])[:10]:
        path = img.get('file_path', '')
        if not path:
            continue
        full = _img(path, 'original')
        thumb = _img(path, 'w342')

        label = f'[COLOR yellow]Poster[/COLOR]  {img.get("width", 0)}x{img.get("height", 0)}'
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': thumb, 'thumb': thumb, 'poster': full, 'fanart': fanart})
        xbmcplugin.addDirectoryItem(HANDLE, full, li, False)
        count += 1

    # Logos
    for img in data.get('logos', [])[:5]:
        path = img.get('file_path', '')
        if not path:
            continue
        full = _img(path, 'original')
        thumb = _img(path, 'w300')

        label = f'[COLOR lime]Logo[/COLOR]'
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})
        xbmcplugin.addDirectoryItem(HANDLE, full, li, False)
        count += 1

    if count == 0:
        xbmcgui.Dialog().notification('Extras', 'No images found', xbmcgui.NOTIFICATION_INFO)

    xbmcplugin.setContent(HANDLE, 'images')
    xbmcplugin.endOfDirectory(HANDLE)


# ═══════════════════════════════════════════════════════════════
# TRIVIA & FACTS
# ═══════════════════════════════════════════════════════════════

def show_trivia(tmdb_id, media_type='movie', title='', imdb_id=''):
    """Budget, box office, keywords, production info, ratings - text dialog"""
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    details = _tmdb(f'/{endpoint}/{tmdb_id}', 'append_to_response=keywords,external_ids,release_dates')

    if not details:
        xbmcgui.Dialog().notification('Extras', 'No info available', xbmcgui.NOTIFICATION_INFO)
        return

    lines = []
    lines.append(f'[B][COLOR gold]{title}[/COLOR][/B]\n')

    # Tagline
    tagline = details.get('tagline', '')
    if tagline:
        lines.append(f'[I]"{tagline}"[/I]\n')

    # Ratings
    vote = details.get('vote_average', 0)
    vote_count = details.get('vote_count', 0)
    if vote:
        lines.append(f'[B]TMDB Rating:[/B] {vote:.1f}/10 ({vote_count:,} votes)')

    # OMDB ratings
    if not imdb_id:
        imdb_id = details.get('imdb_id', '') or details.get('external_ids', {}).get('imdb_id', '')
    if imdb_id:
        try:
            from resources.lib import omdb
            omdb_data = omdb.get_movie_data(imdb_id=imdb_id)
            if omdb_data and omdb_data.get('ratings'):
                r = omdb_data['ratings']
                if 'imdb' in r:
                    v = r['imdb'].get('votes', '')
                    lines.append(f'[B]IMDb:[/B] {r["imdb"]["value"]} ({v} votes)' if v else f'[B]IMDb:[/B] {r["imdb"]["value"]}')
                if 'rotten_tomatoes' in r:
                    lines.append(f'[B]Rotten Tomatoes:[/B] {r["rotten_tomatoes"]["value"]}')
                if 'metacritic' in r:
                    lines.append(f'[B]Metacritic:[/B] {r["metacritic"]["value"]}')
            if omdb_data and omdb_data.get('awards') and omdb_data['awards'] != 'N/A':
                lines.append(f'\n[B]Awards:[/B] {omdb_data["awards"]}')
        except:
            pass
    lines.append('')

    # Box Office (movies)
    if media_type == 'movie':
        budget = details.get('budget', 0)
        revenue = details.get('revenue', 0)
        if budget:
            lines.append(f'[B]Budget:[/B] ${budget:,}')
        if revenue:
            lines.append(f'[B]Box Office:[/B] ${revenue:,}')
        if budget and revenue:
            roi = ((revenue - budget) / budget) * 100
            color = 'lime' if roi > 0 else 'red'
            lines.append(f'[B]ROI:[/B] [COLOR {color}]{roi:+.0f}%[/COLOR]')
        runtime = details.get('runtime', 0)
        if runtime:
            h, m = divmod(runtime, 60)
            lines.append(f'[B]Runtime:[/B] {h}h {m}m' if h else f'[B]Runtime:[/B] {m}m')
        lines.append('')

    # TV specific
    if media_type == 'tv':
        seasons = details.get('number_of_seasons', 0)
        episodes = details.get('number_of_episodes', 0)
        status = details.get('status', '')
        if seasons:
            lines.append(f'[B]Seasons:[/B] {seasons}  |  [B]Episodes:[/B] {episodes}')
        if status:
            lines.append(f'[B]Status:[/B] {status}')
        for net in details.get('networks', [])[:3]:
            lines.append(f'[B]Network:[/B] {net.get("name", "")}')
        lines.append('')

    # Production
    companies = [c.get('name', '') for c in details.get('production_companies', [])[:4]]
    if companies:
        lines.append(f'[B]Production:[/B] {", ".join(companies)}')

    countries = [c.get('name', '') for c in details.get('production_countries', [])[:3]]
    if countries:
        lines.append(f'[B]Country:[/B] {", ".join(countries)}')

    langs = [l.get('english_name', '') for l in details.get('spoken_languages', [])[:3]]
    if langs:
        lines.append(f'[B]Languages:[/B] {", ".join(langs)}')

    orig_title = details.get('original_title') or details.get('original_name', '')
    orig_lang = details.get('original_language', '')
    if orig_lang and orig_lang != 'en':
        lines.append(f'[B]Original Title:[/B] {orig_title} ({orig_lang.upper()})')
    lines.append('')

    # Keywords
    kw_data = details.get('keywords', {})
    kw_list = kw_data.get('keywords', []) or kw_data.get('results', [])
    if kw_list:
        kw_names = [k.get('name', '') for k in kw_list[:20]]
        lines.append(f'[B]Keywords:[/B] {", ".join(kw_names)}')

    # Genres
    genres = [g.get('name', '') for g in details.get('genres', [])]
    if genres:
        lines.append(f'[B]Genres:[/B] {", ".join(genres)}')

    xbmcgui.Dialog().textviewer(f'Trivia & Facts: {title}', '\n'.join(lines))


# ═══════════════════════════════════════════════════════════════
# TV SEASON OVERVIEW
# ═══════════════════════════════════════════════════════════════

def show_season_overview(tmdb_id, title='', season=''):
    """Season episode list with air dates, ratings, guest stars"""
    icon, fanart = _get_addon_art()
    season = str(season)
    data = _tmdb(f'/tv/{tmdb_id}/season/{season}')

    if not data or not data.get('episodes'):
        xbmcgui.Dialog().notification('Extras', 'No season info found', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    # Season poster
    season_poster = _img(data.get('poster_path')) or icon
    season_name = data.get('name', f'Season {season}')
    overview = data.get('overview', '')

    if overview:
        li = xbmcgui.ListItem(label=f'[B]{season_name}[/B]')
        li.setArt({'icon': season_poster, 'thumb': season_poster, 'fanart': fanart})
        info_tag = li.getVideoInfoTag()
        info_tag.setPlot(overview)
        xbmcplugin.addDirectoryItem(HANDLE, '', li, False)

    for ep in data.get('episodes', []):
        ep_num = ep.get('episode_number', 0)
        ep_name = ep.get('name', f'Episode {ep_num}')
        air_date = ep.get('air_date', '')
        rating = ep.get('vote_average', 0)
        still = _img(ep.get('still_path'), 'w400') or icon
        ep_overview = ep.get('overview', '')

        # Guest stars count
        guests = ep.get('guest_stars', [])
        guest_str = f'  [COLOR grey]{len(guests)} guests[/COLOR]' if guests else ''

        label = f'E{ep_num:02d}  [B]{ep_name}[/B]'
        if air_date:
            label += f'  [COLOR grey]{air_date}[/COLOR]'
        if rating:
            label += f'  [COLOR gold]{rating:.1f}[/COLOR]'
        label += guest_str

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': still, 'thumb': still, 'fanart': fanart})
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(ep_name)
        info_tag.setPlot(ep_overview)
        info_tag.setSeason(int(season))
        info_tag.setEpisode(ep_num)
        info_tag.setMediaType('episode')
        li.setProperty('IsPlayable', 'true')

        url = f'{sys.argv[0]}?action=play&title={quote_plus(title)}&season={season}&episode={ep_num}&tmdb_id={tmdb_id}&media_type=tv'
        xbmcplugin.addDirectoryItem(HANDLE, url, li, False)

    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)


# ═══════════════════════════════════════════════════════════════
# CONTEXT MENU BUILDER
# ═══════════════════════════════════════════════════════════════

def build_extras_context_items(tmdb_id, media_type='movie', title='', imdb_id='', season='', episode=''):
    """Build context menu items for the Extras hub"""
    base = f'plugin://{ADDON_ID}/?action='
    params = f'tmdb_id={tmdb_id}&media_type={media_type}&title={quote_plus(title)}'
    if imdb_id:
        params += f'&imdb_id={imdb_id}'
    if season:
        params += f'&season={season}'
    if episode:
        params += f'&episode={episode}'

    return [
        ('Extras', f'Container.Update({base}extras_hub&{params})'),
    ]
