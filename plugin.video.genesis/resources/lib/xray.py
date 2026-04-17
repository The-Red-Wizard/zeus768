# -*- coding: utf-8 -*-
"""
Enhanced X-Ray Metadata Module for Test1
Provides comprehensive movie/show information:
- Cast & Crew with profile images
- Multi-source ratings (IMDB, Rotten Tomatoes, Metacritic)
- Awards, Box Office, Keywords
- Similar titles by genre AND by cast
- Accessible via context menu
"""
import json
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs
import sys
import os
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus

ADDON_ID = 'plugin.video.genesis'
ADDON_PATH = xbmcvfs.translatePath(f'special://home/addons/{ADDON_ID}/')

# Cache for X-Ray data
_xray_cache = {}


def _get_tmdb_api_key():
    """Get TMDB API key"""
    try:
        addon = xbmcaddon.Addon()
        user_key = addon.getSetting('tmdb_api_key')
        if user_key and len(user_key) > 10:
            return user_key
    except:
        pass
    return "f15af109700aab95d564acda15bdcd97"


def _http_get(url, timeout=10):
    """HTTP GET helper"""
    try:
        req = Request(url, headers={'User-Agent': 'Test1 Kodi Addon'})
        response = urlopen(req, timeout=timeout)
        return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        xbmc.log(f'X-Ray HTTP Error: {e}', xbmc.LOGWARNING)
        return None


def get_movie_xray(tmdb_id, imdb_id=None):
    """Get complete X-Ray data for a movie including OMDB ratings"""
    cache_key = f'movie_{tmdb_id}'
    if cache_key in _xray_cache:
        return _xray_cache[cache_key]
    
    api_key = _get_tmdb_api_key()
    xray_data = {
        'cast': [],
        'crew': [],
        'trivia': [],
        'keywords': [],
        'similar': [],
        'similar_by_cast': [],
        'reviews': [],
        'ratings': {},
        'awards': '',
        'box_office': '',
        'budget': '',
        'runtime': '',
        'tagline': ''
    }
    
    # Get credits (cast & crew) with profile images
    credits = _http_get(f"https://api.themoviedb.org/3/movie/{tmdb_id}/credits?api_key={api_key}")
    if credits:
        # Top 15 cast members with full info
        for person in credits.get('cast', [])[:15]:
            xray_data['cast'].append({
                'name': person.get('name', ''),
                'character': person.get('character', ''),
                'profile': f"https://image.tmdb.org/t/p/w185{person.get('profile_path')}" if person.get('profile_path') else '',
                'profile_hd': f"https://image.tmdb.org/t/p/w500{person.get('profile_path')}" if person.get('profile_path') else '',
                'id': person.get('id'),
                'order': person.get('order', 99)
            })
        
        # Key crew members
        key_jobs = ['Director', 'Writer', 'Screenplay', 'Story', 'Producer', 'Executive Producer', 
                    'Director of Photography', 'Cinematography', 'Original Music Composer', 
                    'Music', 'Editor', 'Casting']
        crew_added = set()
        for person in credits.get('crew', []):
            job = person.get('job', '')
            person_id = person.get('id')
            if job in key_jobs and person_id not in crew_added:
                xray_data['crew'].append({
                    'name': person.get('name', ''),
                    'job': job,
                    'department': person.get('department', ''),
                    'profile': f"https://image.tmdb.org/t/p/w185{person.get('profile_path')}" if person.get('profile_path') else '',
                    'id': person_id
                })
                crew_added.add(person_id)
    
    # Get keywords
    keywords = _http_get(f"https://api.themoviedb.org/3/movie/{tmdb_id}/keywords?api_key={api_key}")
    if keywords:
        xray_data['keywords'] = [kw.get('name', '') for kw in keywords.get('keywords', [])[:15]]
    
    # Get reviews
    reviews = _http_get(f"https://api.themoviedb.org/3/movie/{tmdb_id}/reviews?api_key={api_key}")
    if reviews:
        for review in reviews.get('results', [])[:3]:
            xray_data['reviews'].append({
                'author': review.get('author', 'Anonymous'),
                'content': review.get('content', '')[:500],
                'rating': review.get('author_details', {}).get('rating')
            })
    
    # Get movie details
    details = _http_get(f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}&append_to_response=release_dates")
    if details:
        # Budget and revenue
        budget = details.get('budget', 0)
        revenue = details.get('revenue', 0)
        if budget > 0:
            xray_data['budget'] = f"${budget:,}"
            xray_data['trivia'].append(f"Budget: ${budget:,}")
        if revenue > 0:
            xray_data['box_office'] = f"${revenue:,}"
            xray_data['trivia'].append(f"Box Office: ${revenue:,}")
        
        # Runtime
        runtime = details.get('runtime', 0)
        if runtime > 0:
            hours = runtime // 60
            mins = runtime % 60
            xray_data['runtime'] = f"{hours}h {mins}m" if hours else f"{mins}m"
            xray_data['trivia'].append(f"Runtime: {xray_data['runtime']}")
        
        # Tagline
        tagline = details.get('tagline', '')
        if tagline:
            xray_data['tagline'] = tagline
            xray_data['trivia'].insert(0, f'"{tagline}"')
        
        # Production companies
        for company in details.get('production_companies', [])[:3]:
            xray_data['trivia'].append(f"Produced by {company.get('name', '')}")
        
        # Original language
        orig_lang = details.get('original_language', '')
        orig_title = details.get('original_title', '')
        if orig_lang and orig_lang != 'en':
            xray_data['trivia'].append(f"Original Language: {orig_lang.upper()}")
            if orig_title and orig_title != details.get('title'):
                xray_data['trivia'].append(f"Original Title: {orig_title}")
        
        # Store IMDB ID for OMDB lookup
        if not imdb_id:
            imdb_id = details.get('imdb_id', '')
    
    # Get OMDB ratings (IMDB, Rotten Tomatoes, Metacritic)
    if imdb_id:
        try:
            from . import omdb
            omdb_data = omdb.get_movie_data(imdb_id=imdb_id)
            if omdb_data:
                xray_data['ratings'] = omdb_data.get('ratings', {})
                if omdb_data.get('awards') and omdb_data['awards'] != 'N/A':
                    xray_data['awards'] = omdb_data['awards']
                if omdb_data.get('box_office') and omdb_data['box_office'] != 'N/A':
                    # Prefer OMDB box office if available
                    xray_data['box_office'] = omdb_data['box_office']
        except Exception as e:
            xbmc.log(f'X-Ray OMDB error: {e}', xbmc.LOGWARNING)
    
    # Get similar movies by genre/keywords
    similar = _http_get(f"https://api.themoviedb.org/3/movie/{tmdb_id}/similar?api_key={api_key}")
    if similar:
        for movie in similar.get('results', [])[:8]:
            xray_data['similar'].append({
                'id': movie.get('id'),
                'title': movie.get('title', ''),
                'year': (movie.get('release_date') or '')[:4],
                'poster': f"https://image.tmdb.org/t/p/w185{movie.get('poster_path')}" if movie.get('poster_path') else '',
                'rating': movie.get('vote_average', 0)
            })
    
    # Get movies by top cast members (Similar by Cast feature)
    if xray_data['cast']:
        top_cast = xray_data['cast'][:3]  # Top 3 actors
        seen_movies = {tmdb_id}  # Don't include current movie
        
        for actor in top_cast:
            person_id = actor.get('id')
            if not person_id:
                continue
            
            person_credits = _http_get(f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={api_key}")
            if person_credits:
                for movie in sorted(person_credits.get('cast', []), 
                                  key=lambda x: x.get('popularity', 0), reverse=True)[:5]:
                    movie_id = movie.get('id')
                    if movie_id and movie_id not in seen_movies:
                        seen_movies.add(movie_id)
                        xray_data['similar_by_cast'].append({
                            'id': movie_id,
                            'title': movie.get('title', ''),
                            'year': (movie.get('release_date') or '')[:4],
                            'poster': f"https://image.tmdb.org/t/p/w185{movie.get('poster_path')}" if movie.get('poster_path') else '',
                            'actor': actor['name'],
                            'character': movie.get('character', '')
                        })
                        
                        if len(xray_data['similar_by_cast']) >= 10:
                            break
            
            if len(xray_data['similar_by_cast']) >= 10:
                break
    
    _xray_cache[cache_key] = xray_data
    return xray_data


def get_tv_xray(tmdb_id, season=None, episode=None):
    """Get X-Ray data for a TV show/episode"""
    cache_key = f'tv_{tmdb_id}_{season}_{episode}'
    if cache_key in _xray_cache:
        return _xray_cache[cache_key]
    
    api_key = _get_tmdb_api_key()
    xray_data = {
        'cast': [],
        'crew': [],
        'guest_stars': [],
        'trivia': [],
        'keywords': [],
        'similar': [],
        'ratings': {}
    }
    
    # Get show credits
    credits = _http_get(f"https://api.themoviedb.org/3/tv/{tmdb_id}/credits?api_key={api_key}")
    if credits:
        for person in credits.get('cast', [])[:15]:
            xray_data['cast'].append({
                'name': person.get('name', ''),
                'character': person.get('character', ''),
                'profile': f"https://image.tmdb.org/t/p/w185{person.get('profile_path')}" if person.get('profile_path') else '',
                'profile_hd': f"https://image.tmdb.org/t/p/w500{person.get('profile_path')}" if person.get('profile_path') else '',
                'id': person.get('id')
            })
        
        key_jobs = ['Creator', 'Executive Producer', 'Director', 'Writer', 'Showrunner']
        for person in credits.get('crew', []):
            if person.get('job') in key_jobs or person.get('department') == 'Creator':
                xray_data['crew'].append({
                    'name': person.get('name', ''),
                    'job': person.get('job', person.get('department', '')),
                    'profile': f"https://image.tmdb.org/t/p/w185{person.get('profile_path')}" if person.get('profile_path') else '',
                    'id': person.get('id')
                })
    
    # Episode-specific credits
    if season and episode:
        ep_credits = _http_get(f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season}/episode/{episode}/credits?api_key={api_key}")
        if ep_credits:
            for person in ep_credits.get('guest_stars', [])[:10]:
                xray_data['guest_stars'].append({
                    'name': person.get('name', ''),
                    'character': person.get('character', ''),
                    'profile': f"https://image.tmdb.org/t/p/w185{person.get('profile_path')}" if person.get('profile_path') else '',
                    'id': person.get('id')
                })
    
    # Get show details
    details = _http_get(f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={api_key}&append_to_response=external_ids")
    if details:
        for company in details.get('production_companies', [])[:3]:
            xray_data['trivia'].append(f"Produced by {company.get('name', '')}")
        
        for network in details.get('networks', [])[:2]:
            xray_data['trivia'].append(f"Network: {network.get('name', '')}")
        
        seasons = details.get('number_of_seasons', 0)
        episodes = details.get('number_of_episodes', 0)
        if seasons and episodes:
            xray_data['trivia'].append(f"{seasons} Seasons, {episodes} Episodes")
        
        # Get IMDB ID for OMDB ratings
        external_ids = details.get('external_ids', {})
        imdb_id = external_ids.get('imdb_id', '')
        
        if imdb_id:
            try:
                from . import omdb
                omdb_data = omdb.get_movie_data(imdb_id=imdb_id)
                if omdb_data:
                    xray_data['ratings'] = omdb_data.get('ratings', {})
            except:
                pass
    
    # Get similar shows
    similar = _http_get(f"https://api.themoviedb.org/3/tv/{tmdb_id}/similar?api_key={api_key}")
    if similar:
        for show in similar.get('results', [])[:8]:
            xray_data['similar'].append({
                'id': show.get('id'),
                'title': show.get('name', ''),
                'year': (show.get('first_air_date') or '')[:4],
                'poster': f"https://image.tmdb.org/t/p/w185{show.get('poster_path')}" if show.get('poster_path') else ''
            })
    
    _xray_cache[cache_key] = xray_data
    return xray_data


def show_xray_dialog(tmdb_id, media_type='movie', season=None, episode=None, title='', imdb_id=''):
    """Display comprehensive X-Ray information in a dialog"""
    progress = xbmcgui.DialogProgress()
    progress.create('X-Ray', 'Loading metadata...')
    
    if media_type == 'movie':
        xray = get_movie_xray(tmdb_id, imdb_id)
    else:
        xray = get_tv_xray(tmdb_id, season, episode)
    
    progress.close()
    
    if not xray or (not xray.get('cast') and not xray.get('trivia')):
        xbmcgui.Dialog().notification('X-Ray', 'No metadata available', xbmcgui.NOTIFICATION_INFO)
        return
    
    # Build X-Ray content
    lines = []
    
    # Title
    lines.append(f'[B][COLOR skyblue]═══ X-RAY: {title} ═══[/COLOR][/B]\n')
    
    # Ratings section (multi-source)
    if xray.get('ratings'):
        lines.append('[B][COLOR gold]* RATINGS[/COLOR][/B]')
        ratings = xray['ratings']
        
        if 'imdb' in ratings:
            r = ratings['imdb']
            votes = f" ({r.get('votes', '')} votes)" if r.get('votes') else ''
            lines.append(f"  [COLOR gold]* IMDb:[/COLOR] {r['value']}{votes}")
        
        if 'rotten_tomatoes' in ratings:
            r = ratings['rotten_tomatoes']
            score = int(r['score']) if r['score'].isdigit() else 0
            color = 'lime' if score >= 60 else 'red'
            icon = '🍅' if score >= 60 else '🥀'
            lines.append(f"  [COLOR {color}]{icon} Rotten Tomatoes:[/COLOR] {r['value']}")
        
        if 'metacritic' in ratings:
            r = ratings['metacritic']
            score = int(r['score']) if r['score'].isdigit() else 0
            if score >= 61:
                color = 'lime'
            elif score >= 40:
                color = 'yellow'
            else:
                color = 'red'
            lines.append(f"  [COLOR {color}]◼ Metacritic:[/COLOR] {r['value']}")
        
        lines.append('')
    
    # Awards section
    if xray.get('awards'):
        lines.append('[B][COLOR gold]* AWARDS[/COLOR][/B]')
        lines.append(f"  {xray['awards']}")
        lines.append('')
    
    # Box Office section
    if xray.get('box_office') or xray.get('budget'):
        lines.append('[B][COLOR gold]* BOX OFFICE[/COLOR][/B]')
        if xray.get('budget'):
            lines.append(f"  Budget: {xray['budget']}")
        if xray.get('box_office'):
            lines.append(f"  Worldwide Gross: {xray['box_office']}")
        lines.append('')
    
    # Cast section with characters
    if xray.get('cast'):
        lines.append('[B][COLOR yellow]* CAST[/COLOR][/B]')
        for actor in xray['cast'][:10]:
            char = f" as [I]{actor['character']}[/I]" if actor.get('character') else ''
            profile_indicator = ' [IMG]' if actor.get('profile') else ''
            lines.append(f"  • {actor['name']}{char}")
        lines.append('')
    
    # Guest stars (TV only)
    if xray.get('guest_stars'):
        lines.append('[B][COLOR yellow]* GUEST STARS[/COLOR][/B]')
        for actor in xray['guest_stars'][:5]:
            char = f" as [I]{actor['character']}[/I]" if actor.get('character') else ''
            lines.append(f"  • {actor['name']}{char}")
        lines.append('')
    
    # Crew section
    if xray.get('crew'):
        lines.append('[B][COLOR yellow]* CREW[/COLOR][/B]')
        # Group by job
        directors = [c for c in xray['crew'] if c['job'] == 'Director']
        writers = [c for c in xray['crew'] if c['job'] in ['Writer', 'Screenplay', 'Story']]
        producers = [c for c in xray['crew'] if 'Producer' in c['job']]
        composers = [c for c in xray['crew'] if 'Composer' in c['job'] or c['job'] == 'Music']
        cinematographers = [c for c in xray['crew'] if c['job'] in ['Director of Photography', 'Cinematography']]
        
        if directors:
            lines.append(f"  [B]Director:[/B] {', '.join(d['name'] for d in directors)}")
        if writers:
            lines.append(f"  [B]Writers:[/B] {', '.join(w['name'] for w in writers[:3])}")
        if cinematographers:
            lines.append(f"  [B]Cinematography:[/B] {', '.join(c['name'] for c in cinematographers)}")
        if composers:
            lines.append(f"  [B]Music:[/B] {', '.join(c['name'] for c in composers)}")
        if producers:
            lines.append(f"  [B]Producers:[/B] {', '.join(p['name'] for p in producers[:3])}")
        lines.append('')
    
    # Keywords/Themes
    if xray.get('keywords'):
        lines.append('[B][COLOR yellow]* KEYWORDS[/COLOR][/B]')
        lines.append(f"  {', '.join(xray['keywords'])}")
        lines.append('')
    
    # Trivia section
    if xray.get('trivia'):
        lines.append('[B][COLOR yellow]* TRIVIA & FACTS[/COLOR][/B]')
        for fact in xray['trivia'][:8]:
            if not fact.startswith('"'):  # Don't duplicate tagline display
                lines.append(f"  • {fact}")
        lines.append('')
    
    # Reviews snippet
    if xray.get('reviews'):
        lines.append('[B][COLOR yellow]* REVIEWS[/COLOR][/B]')
        for review in xray['reviews'][:2]:
            rating = f" ({review['rating']}/10)" if review.get('rating') else ''
            lines.append(f"  [I]\"{review['content'][:200]}...\"[/I]")
            lines.append(f"  — {review['author']}{rating}")
            lines.append('')
    
    # Similar by genre
    if xray.get('similar'):
        lines.append('[B][COLOR yellow]* MORE LIKE THIS[/COLOR][/B]')
        similar_titles = [f"{m['title']} ({m['year']})" for m in xray['similar'][:5] if m.get('title')]
        lines.append(f"  {', '.join(similar_titles)}")
        lines.append('')
    
    # Similar by cast (unique feature)
    if xray.get('similar_by_cast'):
        lines.append('[B][COLOR yellow]* MORE FROM CAST[/COLOR][/B]')
        for movie in xray['similar_by_cast'][:5]:
            lines.append(f"  • {movie['title']} ({movie['year']}) - featuring {movie['actor']}")
    
    xbmcgui.Dialog().textviewer(f'X-Ray: {title}', '\n'.join(lines))


def show_cast_filmography(person_id, person_name=''):
    """Show filmography for a cast/crew member"""
    api_key = _get_tmdb_api_key()
    
    progress = xbmcgui.DialogProgress()
    progress.create('X-Ray', f'Loading filmography for {person_name}...')
    
    data = _http_get(f"https://api.themoviedb.org/3/person/{person_id}/combined_credits?api_key={api_key}")
    progress.close()
    
    if not data:
        xbmcgui.Dialog().notification('X-Ray', 'No filmography found', xbmcgui.NOTIFICATION_INFO)
        return
    
    lines = []
    lines.append(f'[B][COLOR skyblue]═══ {person_name} ═══[/COLOR][/B]\n')
    
    # Get person details
    person = _http_get(f"https://api.themoviedb.org/3/person/{person_id}?api_key={api_key}")
    if person:
        if person.get('birthday'):
            lines.append(f"[B]Born:[/B] {person['birthday']}")
        if person.get('place_of_birth'):
            lines.append(f"[B]From:[/B] {person['place_of_birth']}")
        if person.get('biography'):
            bio = person['biography'][:600]
            lines.append(f"\n{bio}...")
        lines.append('')
    
    # Movies
    movies = sorted(
        [c for c in data.get('cast', []) if c.get('media_type') == 'movie'],
        key=lambda x: x.get('popularity', 0),
        reverse=True
    )[:15]
    
    if movies:
        lines.append('[B][COLOR yellow]* NOTABLE FILMS[/COLOR][/B]')
        for movie in movies:
            year = (movie.get('release_date') or '')[:4]
            char = f" as [I]{movie.get('character')}[/I]" if movie.get('character') else ''
            rating = f" *{movie.get('vote_average', 0):.1f}" if movie.get('vote_average') else ''
            lines.append(f"  • {movie.get('title', '')} ({year}){char}{rating}")
        lines.append('')
    
    # TV Shows
    shows = sorted(
        [c for c in data.get('cast', []) if c.get('media_type') == 'tv'],
        key=lambda x: x.get('popularity', 0),
        reverse=True
    )[:10]
    
    if shows:
        lines.append('[B][COLOR yellow]* TV SHOWS[/COLOR][/B]')
        for show in shows:
            year = (show.get('first_air_date') or '')[:4]
            char = f" as [I]{show.get('character')}[/I]" if show.get('character') else ''
            lines.append(f"  • {show.get('name', '')} ({year}){char}")
    
    xbmcgui.Dialog().textviewer(f'Filmography: {person_name}', '\n'.join(lines))


def show_similar_movies(tmdb_id, title=''):
    """Display similar movies menu (allows navigation)"""
    api_key = _get_tmdb_api_key()
    handle = int(sys.argv[1])
    
    similar = _http_get(f"https://api.themoviedb.org/3/movie/{tmdb_id}/similar?api_key={api_key}")
    
    if not similar or not similar.get('results'):
        xbmcgui.Dialog().notification('X-Ray', 'No similar movies found', xbmcgui.NOTIFICATION_INFO)
        return
    
    for movie in similar.get('results', [])[:20]:
        movie_title = movie.get('title', '')
        year = (movie.get('release_date') or '')[:4]
        movie_id = movie.get('id')
        rating = movie.get('vote_average', 0)
        
        poster = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else ''
        backdrop = f"https://image.tmdb.org/t/p/original{movie.get('backdrop_path')}" if movie.get('backdrop_path') else ''
        
        label = f"{movie_title} ({year})" if year else movie_title
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': poster,
            'fanart': backdrop,
            'thumb': poster,
            'icon': poster
        })
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(movie_title)
        info_tag.setYear(int(year) if year else 0)
        info_tag.setPlot(movie.get('overview', ''))
        info_tag.setRating(rating)
        info_tag.setMediaType('movie')
        
        li.setProperty('IsPlayable', 'true')
        
        # Add context menu
        li.addContextMenuItems([
            ('X-Ray: Cast & Info', f'RunPlugin(plugin://{ADDON_ID}/?action=xray&tmdb_id={movie_id}&media_type=movie&title={quote_plus(movie_title)})'),
            ('Similar Movies', f'Container.Update(plugin://{ADDON_ID}/?action=similar_movies&tmdb_id={movie_id}&title={quote_plus(movie_title)})'),
        ])
        
        play_url = f"{sys.argv[0]}?action=play&title={quote_plus(movie_title)}&year={year}&tmdb_id={movie_id}"
        xbmcplugin.addDirectoryItem(handle, play_url, li, False)
    
    xbmcplugin.setContent(handle, 'movies')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def show_cast_movies(person_id, person_name=''):
    """Display movies by a specific cast member (navigable)"""
    api_key = _get_tmdb_api_key()
    handle = int(sys.argv[1])
    
    data = _http_get(f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={api_key}")
    
    if not data or not data.get('cast'):
        xbmcgui.Dialog().notification('X-Ray', 'No movies found', xbmcgui.NOTIFICATION_INFO)
        return
    
    # Sort by popularity
    movies = sorted(data.get('cast', []), key=lambda x: x.get('popularity', 0), reverse=True)[:25]
    
    for movie in movies:
        movie_title = movie.get('title', '')
        year = (movie.get('release_date') or '')[:4]
        movie_id = movie.get('id')
        character = movie.get('character', '')
        
        poster = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else ''
        backdrop = f"https://image.tmdb.org/t/p/original{movie.get('backdrop_path')}" if movie.get('backdrop_path') else ''
        
        label = f"{movie_title} ({year})"
        if character:
            label += f" - as {character}"
        
        li = xbmcgui.ListItem(label=label)
        li.setArt({
            'poster': poster,
            'fanart': backdrop,
            'thumb': poster,
            'icon': poster
        })
        
        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(movie_title)
        info_tag.setYear(int(year) if year else 0)
        info_tag.setPlot(movie.get('overview', ''))
        info_tag.setMediaType('movie')
        
        li.setProperty('IsPlayable', 'true')
        
        # Add context menu
        li.addContextMenuItems([
            ('X-Ray: Cast & Info', f'RunPlugin(plugin://{ADDON_ID}/?action=xray&tmdb_id={movie_id}&media_type=movie&title={quote_plus(movie_title)})'),
        ])
        
        play_url = f"{sys.argv[0]}?action=play&title={quote_plus(movie_title)}&year={year}&tmdb_id={movie_id}"
        xbmcplugin.addDirectoryItem(handle, play_url, li, False)
    
    xbmcplugin.setContent(handle, 'movies')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=True)


def show_extras_menu(tmdb_id, media_type='movie', title='', imdb_id=''):
    """Show extras menu with similar movies and cast options"""
    handle = int(sys.argv[1])
    api_key = _get_tmdb_api_key()
    
    addon = xbmcaddon.Addon()
    addon_path = xbmcvfs.translatePath(f'special://home/addons/{ADDON_ID}/')
    icon_path = os.path.join(addon_path, 'icon.png')
    fanart_path = os.path.join(addon_path, 'fanart.jpg')
    
    # Menu items
    items = [
        ('Similar Movies', 'similar_movies', f'tmdb_id={tmdb_id}&title={quote_plus(title)}'),
        ('X-Ray: Full Info', 'xray', f'tmdb_id={tmdb_id}&media_type={media_type}&title={quote_plus(title)}&imdb_id={imdb_id}'),
    ]
    
    # Add cast members as options
    if media_type == 'movie':
        credits = _http_get(f"https://api.themoviedb.org/3/movie/{tmdb_id}/credits?api_key={api_key}")
    else:
        credits = _http_get(f"https://api.themoviedb.org/3/tv/{tmdb_id}/credits?api_key={api_key}")
    
    if credits:
        for actor in credits.get('cast', [])[:8]:
            person_id = actor.get('id')
            person_name = actor.get('name', '')
            character = actor.get('character', '')
            profile = f"https://image.tmdb.org/t/p/w185{actor.get('profile_path')}" if actor.get('profile_path') else icon_path
            
            label = f"More with {person_name}"
            if character:
                label += f" ({character})"
            
            li = xbmcgui.ListItem(label=label)
            li.setArt({
                'icon': profile,
                'thumb': profile,
                'poster': profile,
                'fanart': fanart_path
            })
            
            url = f"{sys.argv[0]}?action=cast_movies&person_id={person_id}&person_name={quote_plus(person_name)}"
            xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    # Add the fixed menu items
    for label, action, params in items:
        li = xbmcgui.ListItem(label=f'[B]{label}[/B]')
        li.setArt({
            'icon': icon_path,
            'thumb': icon_path,
            'fanart': fanart_path
        })
        
        if action == 'xray':
            url = f"{sys.argv[0]}?action={action}&{params}"
            xbmcplugin.addDirectoryItem(handle, url, li, False)
        else:
            url = f"{sys.argv[0]}?action={action}&{params}"
            xbmcplugin.addDirectoryItem(handle, url, li, True)
    
    xbmcplugin.endOfDirectory(handle)


def build_xray_context_menu(tmdb_id, media_type='movie', title='', season=None, episode=None, imdb_id=''):
    """Build context menu items for X-Ray features"""
    items = []
    
    base_url = f'plugin://{ADDON_ID}/?action='
    
    # Main X-Ray option
    params = f'tmdb_id={tmdb_id}&media_type={media_type}&title={quote_plus(title)}'
    if imdb_id:
        params += f'&imdb_id={imdb_id}'
    if season:
        params += f'&season={season}'
    if episode:
        params += f'&episode={episode}'
    
    items.append(('X-Ray: Cast & Info', f'RunPlugin({base_url}xray&{params})'))
    items.append(('Extras: Similar & Cast', f'Container.Update({base_url}extras_menu&{params})'))
    
    return items
