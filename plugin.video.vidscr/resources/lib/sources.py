# -*- coding: utf-8 -*-
"""Multi-source resolver coordinator.

Three modes (controlled by user settings):

1. **Sequential** (default) — primary first; on failure walk
   ``_AUTO_FALLBACK_HOSTS`` one at a time until one returns streams.
2. **Multi-link aggregation** — set ``aggregate_all_sources = true``.
   Runs the primary plus every secondary host **concurrently** in a thread
   pool, then merges all results into a single deduped candidate pool.
3. **User-toggled secondary** — original behaviour where the user picks a
   single secondary host in settings (kept for back-compat).

v1.4.9 — fixed the v1.4.8 regression where ``_run_secondary`` overrode
``secondary_source_host`` on a fresh ``xbmcaddon.Addon()`` instance, but
the secondary resolver read from the module-level ``common.ADDON``
singleton — meaning the override was invisible. The host is now passed as
an explicit parameter to ``vidsrc2.resolve_all``.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed

from .common import get_setting_bool, get_setting_int, log
from . import vidsrc as V1
from . import vidsrc2 as V2
from . import stigstream as STIG

# Order matters — most reliable mirrors first. v1.4.9: dropped DNS-dead
# embed.su / autoembed.cc / smashystream.com hosts and the broken JSON-API
# endpoints (vidsrc.icu / vidlink.pro / vidjoy.pro public APIs return 404).
# vidsrc.icu kept because its embed page wraps a real iframe we can chase.
_AUTO_FALLBACK_HOSTS = (
    'vidsrc.xyz',
    'vidsrc.to',
    'vidsrc.net',
    'vidsrc.icu',
    'multiembed.mov',
    'moviesapi.club',
    '2embed.cc',
)


def _run_stigstream(media_type, tmdb_id, season, episode):
    """Run the stigstream resolver — completely independent of the cloudnestra
    chain, queries its own AES/ChaCha-encrypted JSON API and returns multiple
    HLS streams across 8+ regional servers."""
    if not get_setting_bool('enable_stigstream', True):
        return []
    try:
        streams = STIG.resolve_streams(media_type, tmdb_id,
                                       season=season, episode=episode) or []
    except Exception as e:
        log('sources: stigstream failed %s' % e)
        return []
    for s in streams:
        s.setdefault('provider', 'stigstream')
        s.setdefault('host_origin', 'stigstream.ru')
    return streams


def _run_secondary(media_type, tmdb_id, season, episode, imdb_id, host=None):
    """Run vidsrc2.resolve_all, optionally pinning a specific host."""
    try:
        streams = V2.resolve_all(media_type, tmdb_id,
                                 season=season, episode=episode,
                                 imdb_id=imdb_id, host=host) or []
    except Exception as e:
        log('sources: secondary [%s] failed %s' % (host or 'user', e))
        streams = []
    for s in streams:
        s.setdefault('provider', 'secondary')
        s.setdefault('host_origin', host or 'user')
    return streams


def _dedupe(streams):
    """Merge streams from multiple hosts, keeping the first occurrence of
    each unique URL."""
    seen = set()
    out = []
    for s in streams:
        u = s.get('url')
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(s)
    return out


def _aggregate_all(media_type, tmdb_id, season, episode, imdb_id):
    """Multi-link mode: query every secondary host concurrently and merge
    all returned streams into a single pool."""
    workers = max(get_setting_int('aggregate_workers', 5), 2)
    log('sources: aggregating %d hosts in parallel (workers=%d)'
        % (len(_AUTO_FALLBACK_HOSTS), workers))
    out = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(_run_secondary, media_type, tmdb_id, season, episode,
                      imdb_id, host): host
            for host in _AUTO_FALLBACK_HOSTS
        }
        for fut in as_completed(futures, timeout=30):
            host = futures[fut]
            try:
                streams = fut.result(timeout=1) or []
            except Exception as e:
                log('sources: aggregate [%s] error %s' % (host, e))
                continue
            if streams:
                log('sources: aggregate [%s] returned %d streams' % (host, len(streams)))
                for s in streams:
                    s['provider'] = 'aggregate'
                    s.setdefault('host_origin', host)
                out.extend(streams)
    return out


def resolve(media_type, tmdb_id, season=None, episode=None, imdb_id=None,
            force_provider=None):
    """Returns (primary_streams, secondary_streams)."""
    secondary_enabled = get_setting_bool('enable_secondary_source', False)
    auto_secondary = get_setting_bool('auto_secondary_on_404', True)
    aggregate_mode = get_setting_bool('aggregate_all_sources', False)

    primary, secondary = [], []
    use_primary = force_provider in (None, 'primary')
    use_secondary = secondary_enabled and force_provider in (None, 'secondary')

    # Multi-link aggregation overrides the sequential flow entirely.
    if aggregate_mode and force_provider is None:
        log('sources: multi-link aggregation mode')
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_primary = ex.submit(_resolve_primary, media_type, tmdb_id,
                                  season, episode, imdb_id)
            f_secondary = ex.submit(_aggregate_all, media_type, tmdb_id,
                                    season, episode, imdb_id)
            f_stig = ex.submit(_run_stigstream, media_type, tmdb_id,
                               season, episode)
            try:
                primary = f_primary.result(timeout=30) or []
            except Exception as e:
                log('sources: primary in aggregate mode failed %s' % e)
                primary = []
            try:
                secondary = f_secondary.result(timeout=35) or []
            except Exception as e:
                log('sources: aggregate failed %s' % e)
                secondary = []
            try:
                stig = f_stig.result(timeout=30) or []
                if stig:
                    log('sources: stigstream contributed %d streams' % len(stig))
                    secondary.extend(stig)
            except Exception as e:
                log('sources: stigstream in aggregate mode failed %s' % e)
        primary = _dedupe(primary)
        secondary = _dedupe(secondary)
        log('sources: aggregate result — %d primary + %d secondary candidates'
            % (len(primary), len(secondary)))
        return primary, secondary

    # ---- standard sequential flow ----
    if use_primary:
        primary = _resolve_primary(media_type, tmdb_id, season, episode, imdb_id)

    if use_secondary:
        secondary.extend(_run_secondary(media_type, tmdb_id, season, episode,
                                        imdb_id, host=None))

    # NEW v1.4.14 — Stigstream is an INDEPENDENT source (own AES/ChaCha API,
    # own CDN at proxy.stigstream.ru). Always merge its streams into the
    # secondary pool when enabled — it's the most reliable source we have for
    # titles cloudnestra doesn't carry. Skipped only when the user explicitly
    # forces a single provider (force_provider != None).
    if force_provider is None and get_setting_bool('enable_stigstream', True):
        try:
            stig_streams = _run_stigstream(media_type, tmdb_id, season, episode)
            if stig_streams:
                log('sources: stigstream contributed %d streams' % len(stig_streams))
                secondary.extend(stig_streams)
        except Exception as e:
            log('sources: stigstream lookup failed %s' % e)

    # Auto last-resort fallback chain when nothing came back.
    if not primary and not secondary and auto_secondary \
            and force_provider in (None, 'primary'):
        log('sources: primary returned nothing — trying auto-fallback hosts')
        for host in _AUTO_FALLBACK_HOSTS:
            for ident_imdb, ident_tmdb in (
                (imdb_id, None) if imdb_id else (None, tmdb_id),
                (None, tmdb_id) if (imdb_id and tmdb_id and imdb_id != tmdb_id) else (None, None),
            ):
                if not ident_imdb and not ident_tmdb:
                    continue
                log('sources: auto-fallback -> %s (imdb=%s tmdb=%s)'
                    % (host, ident_imdb, ident_tmdb))
                streams = _run_secondary(media_type, ident_tmdb or tmdb_id,
                                         season, episode,
                                         ident_imdb, host=host)
                if streams:
                    for s in streams:
                        s['provider'] = 'auto-secondary'
                    secondary.extend(streams)
                    break
            if secondary:
                break

    return primary, secondary


def _resolve_primary(media_type, tmdb_id, season, episode, imdb_id):
    try:
        streams = V1.resolve_all(media_type, tmdb_id, season=season,
                                 episode=episode, imdb_id=imdb_id) or []
        for s in streams:
            s.setdefault('provider', 'primary')
        return streams
    except Exception as e:
        log('sources: primary failed %s' % e)
        return []
