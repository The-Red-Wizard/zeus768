# -*- coding: utf-8 -*-
"""Syncher - TMDB API for metadata enrichment"""

from resources.lib.modules import control
from resources.lib.modules import client

def get_movie_meta(tmdb_id=None, imdb_id=None):
    """Get movie metadata from TMDB including credits"""
    try:
        if tmdb_id and tmdb_id != '0':
            url = '%s/movie/%s?api_key=%s&append_to_response=credits' % (control.TMDB_BASE, tmdb_id, control.TMDB_KEY)
        elif imdb_id and imdb_id != '0':
            # Find TMDB ID from IMDB ID
            find_url = '%s/find/%s?api_key=%s&external_source=imdb_id' % (control.TMDB_BASE, imdb_id, control.TMDB_KEY)
            find = client.request_json(find_url)
            if find and find.get('movie_results'):
                tmdb_id = str(find['movie_results'][0]['id'])
                url = '%s/movie/%s?api_key=%s&append_to_response=credits' % (control.TMDB_BASE, tmdb_id, control.TMDB_KEY)
            else:
                return {}
        else:
            return {}

        data = client.request_json(url)
        if not data:
            return {}

        meta = {}
        if data.get('poster_path'):
            meta['poster'] = control.TMDB_POSTER + data['poster_path']
        if data.get('backdrop_path'):
            meta['fanart'] = control.TMDB_FANART + data['backdrop_path']

        # Director and cast
        credits = data.get('credits', {})
        directors = [c['name'] for c in credits.get('crew', []) if c.get('job') == 'Director']
        if directors:
            meta['director'] = ' / '.join(directors)
        cast = credits.get('cast', [])
        if cast:
            meta['cast'] = [(c['name'], c.get('character', '')) for c in cast[:10]]

        if data.get('overview'):
            meta['plot'] = data['overview']
        if data.get('tagline'):
            meta['tagline'] = data['tagline']
        if data.get('genres'):
            meta['genre'] = ' / '.join([g['name'] for g in data['genres']])
        if data.get('runtime'):
            meta['duration'] = str(data['runtime'])
        if data.get('vote_average'):
            meta['rating'] = str(data['vote_average'])
        if data.get('production_companies'):
            meta['studio'] = data['production_companies'][0]['name']
        if data.get('imdb_id'):
            meta['imdb'] = data['imdb_id']
        meta['tmdb'] = str(data.get('id', '0'))

        return meta
    except Exception as e:
        control.log('TMDB movie meta error: %s' % e)
        return {}


def get_show_meta(tmdb_id=None, imdb_id=None):
    """Get TV show metadata from TMDB"""
    try:
        if tmdb_id and tmdb_id != '0':
            url = '%s/tv/%s?api_key=%s&append_to_response=credits,external_ids' % (control.TMDB_BASE, tmdb_id, control.TMDB_KEY)
        elif imdb_id and imdb_id != '0':
            find_url = '%s/find/%s?api_key=%s&external_source=imdb_id' % (control.TMDB_BASE, imdb_id, control.TMDB_KEY)
            find = client.request_json(find_url)
            if find and find.get('tv_results'):
                tmdb_id = str(find['tv_results'][0]['id'])
                url = '%s/tv/%s?api_key=%s&append_to_response=credits,external_ids' % (control.TMDB_BASE, tmdb_id, control.TMDB_KEY)
            else:
                return {}
        else:
            return {}

        data = client.request_json(url)
        if not data:
            return {}

        meta = {}
        if data.get('poster_path'):
            meta['poster'] = control.TMDB_POSTER + data['poster_path']
        if data.get('backdrop_path'):
            meta['fanart'] = control.TMDB_FANART + data['backdrop_path']

        credits = data.get('credits', {})
        cast = credits.get('cast', [])
        if cast:
            meta['cast'] = [(c['name'], c.get('character', '')) for c in cast[:10]]

        if data.get('overview'):
            meta['plot'] = data['overview']
        if data.get('genres'):
            meta['genre'] = ' / '.join([g['name'] for g in data['genres']])
        if data.get('networks'):
            meta['studio'] = data['networks'][0]['name']
        if data.get('vote_average'):
            meta['rating'] = str(data['vote_average'])

        ext = data.get('external_ids', {})
        if ext.get('imdb_id'):
            meta['imdb'] = ext['imdb_id']
        if ext.get('tvdb_id'):
            meta['tvdb'] = str(ext['tvdb_id'])
        meta['tmdb'] = str(data.get('id', '0'))

        return meta
    except Exception as e:
        control.log('TMDB show meta error: %s' % e)
        return {}


def get_season_poster(tmdb_id, season):
    try:
        url = '%s/tv/%s/season/%s?api_key=%s' % (control.TMDB_BASE, tmdb_id, season, control.TMDB_KEY)
        data = client.request_json(url)
        if data and data.get('poster_path'):
            return control.TMDB_POSTER + data['poster_path']
    except:
        pass
    return None
