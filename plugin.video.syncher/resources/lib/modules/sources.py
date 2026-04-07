# -*- coding: utf-8 -*-
"""Syncher - Source manager: coordinates scrapers and resolvers"""

import threading
from resources.lib.modules import control
from resources.lib.scrapers import rapidrar, psa, rapidmoviez, tfpdl, watchseries, rlsbb, ddlvalley, scenesource
from resources.lib.resolvers import realdebrid, premiumize, alldebrid, torbox, rapidrar_resolver
from resources.lib.scrapers import extract_magnet_hash

ALL_SCRAPERS = [rapidrar, psa, rapidmoviez, tfpdl, watchseries, rlsbb, ddlvalley, scenesource]

def get_movie_sources(title, year, imdb=''):
    """Run all scrapers in parallel and collect sources"""
    all_sources = []
    lock = threading.Lock()
    timeout = int(control.setting('timeout') or '30')

    def _run_scraper(scraper, title, year, imdb):
        try:
            results = scraper.get_movie_sources(title, year, imdb)
            if results:
                with lock:
                    all_sources.extend(results)
        except Exception as e:
            control.log('Scraper %s error: %s' % (scraper.__name__, e))

    threads = []
    for scraper in ALL_SCRAPERS:
        t = threading.Thread(target=_run_scraper, args=(scraper, title, year, imdb))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=timeout)

    # Sort: 4K > 1080p > 720p > SD, then debrid sources first
    quality_order = {'4K': 0, '1080p': 1, '720p': 2, 'HD': 3, 'SD': 4}
    all_sources.sort(key=lambda x: (quality_order.get(x.get('quality', 'SD'), 4), 0 if x.get('debrid') else 1))

    return all_sources


def get_episode_sources(title, season, episode, imdb=''):
    """Run all scrapers in parallel for episodes"""
    all_sources = []
    lock = threading.Lock()
    timeout = int(control.setting('timeout') or '30')

    def _run_scraper(scraper, title, season, episode, imdb):
        try:
            results = scraper.get_episode_sources(title, season, episode, imdb)
            if results:
                with lock:
                    all_sources.extend(results)
        except Exception as e:
            control.log('Scraper %s error: %s' % (scraper.__name__, e))

    threads = []
    for scraper in ALL_SCRAPERS:
        t = threading.Thread(target=_run_scraper, args=(scraper, title, season, episode, imdb))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=timeout)

    quality_order = {'4K': 0, '1080p': 1, '720p': 2, 'HD': 3, 'SD': 4}
    all_sources.sort(key=lambda x: (quality_order.get(x.get('quality', 'SD'), 4), 0 if x.get('debrid') else 1))

    return all_sources


def resolve_source(source):
    """Resolve a source through the appropriate resolver"""
    url = source.get('url', '')
    source_type = source.get('type', '')
    debrid = source.get('debrid', '')

    # Magnet/torrent: resolve through debrid
    if source_type == 'torrent' or url.startswith('magnet:'):
        return _resolve_torrent(url)

    # RapidRAR specific
    if debrid == 'rapidrar' or 'rapidrar' in url.lower():
        if rapidrar_resolver.is_enabled():
            resolved = rapidrar_resolver.resolve(url)
            if resolved:
                return resolved
        # Fall through to debrid if RapidRAR login failed
        return _resolve_hoster(url)

    # Hoster links: resolve through debrid
    if source_type == 'hoster' and not source.get('direct'):
        return _resolve_hoster(url)

    # Direct/embed links
    if source_type in ('direct', 'embed') or source.get('direct'):
        return url

    # Fallback: try debrid first, then return as-is
    resolved = _resolve_hoster(url)
    return resolved if resolved else url


def _resolve_hoster(url):
    """Resolve a hoster URL through debrid services"""
    # Try Real-Debrid
    if realdebrid.is_enabled():
        try:
            resolved = realdebrid.resolve(url)
            if resolved:
                return resolved
        except:
            pass

    # Try AllDebrid
    if alldebrid.is_enabled():
        try:
            resolved = alldebrid.resolve(url)
            if resolved:
                return resolved
        except:
            pass

    # Try Premiumize
    if premiumize.is_enabled():
        try:
            resolved = premiumize.resolve(url)
            if resolved:
                return resolved
        except:
            pass

    # Try TorBox
    if torbox.is_enabled():
        try:
            resolved = torbox.resolve(url)
            if resolved:
                return resolved
        except:
            pass

    return None


def _resolve_torrent(magnet):
    """Resolve a magnet/torrent through debrid"""
    # Check cache first, then add
    hash_val = extract_magnet_hash(magnet) if magnet.startswith('magnet:') else None

    if realdebrid.is_enabled():
        try:
            if hash_val:
                cached = realdebrid.check_cache([hash_val])
                if hash_val in cached:
                    control.log('RD cache hit for %s' % hash_val[:8])
            resolved = realdebrid.add_magnet(magnet)
            if resolved:
                return resolved
        except:
            pass

    if premiumize.is_enabled():
        try:
            resolved = premiumize.add_magnet(magnet)
            if resolved:
                return resolved
        except:
            pass

    if alldebrid.is_enabled():
        try:
            resolved = alldebrid.add_magnet(magnet)
            if resolved:
                return resolved
        except:
            pass

    if torbox.is_enabled():
        try:
            resolved = torbox.add_magnet(magnet)
            if resolved:
                return resolved
        except:
            pass

    return None
