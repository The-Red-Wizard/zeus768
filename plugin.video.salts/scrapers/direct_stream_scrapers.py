"""
SALTS Scrapers - Direct Stream Scrapers (No Streamtape/Doodstream/Mixdrop)
Added 2026-02 by request. Easy-to-scrape sites that serve direct MP4 / M3U8
playlists via public JSON endpoints — they do NOT rely on embedded third-party
file hosters like Streamtape, Doodstream, Mixdrop, Filemoon, etc.

All scrapers inherit from FreeStreamBase (extended_free_scrapers) so they get
TMDB/IMDB id resolution and the shared M3U8/MP4 extraction helper.

Providers included:
  1. ArchiveOrg     - archive.org public-domain movies + classic TV (pure MP4)
  2. Cineby         - cineby.ru         (JSON -> m3u8)
  3. VidFast        - vidfast.pro       (JSON -> m3u8)
  4. RiveStream     - rivestream.net    (JSON -> m3u8)
  5. UiraLive       - uira.live         (JSON -> m3u8)
  6. NetMirror      - netmirror.8man    (JSON -> m3u8)
  7. VidBinge       - vidbinge.com      (JSON -> m3u8)
  8. HollyMovieHD   - hollymoviehd.cc   (JSON -> m3u8)
"""
import re
import json
import xbmcaddon
from urllib.request import urlopen, Request
from urllib.parse import quote_plus

from .extended_free_scrapers import FreeStreamBase, UA
from salts_lib import log_utils

ADDON = xbmcaddon.Addon()


# ==========================================================================
# Shared helper — GET JSON with custom headers
# ==========================================================================
def _get_json(url, headers=None, timeout=12):
    try:
        hdrs = {'User-Agent': UA, 'Accept': 'application/json,*/*'}
        if headers:
            hdrs.update(headers)
        req = Request(url, headers=hdrs)
        resp = urlopen(req, timeout=timeout)
        raw = resp.read().decode('utf-8', errors='replace')
        return json.loads(raw)
    except Exception as e:
        log_utils.log_error(f'direct_stream: JSON error {url}: {e}')
        return None


def _walk_for_streams(obj, out):
    """Recursively walk a JSON blob collecting any http(s) urls pointing at
    .m3u8 / .mp4 / .mpd playlists. Also captures a sibling 'quality' if found.
    """
    if isinstance(obj, dict):
        q = obj.get('quality') or obj.get('label') or obj.get('name') or ''
        for key in ('file', 'url', 'src', 'playlist', 'hls', 'source', 'link'):
            val = obj.get(key)
            if isinstance(val, str) and val.startswith('http') and \
               re.search(r'\.(m3u8|mp4|mpd)(\?|$)', val, re.I):
                out.append((val, str(q)))
        for v in obj.values():
            _walk_for_streams(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_for_streams(v, out)


def _quality_from_label(label, url=''):
    text = f'{label} {url}'.lower()
    for tag, name in (('2160', '4K'), ('4k', '4K'),
                      ('1080', '1080p'), ('720', '720p'),
                      ('480', '480p'), ('360', '360p')):
        if tag in text:
            return name
    return 'HD'


# ==========================================================================
# 1. Archive.org — public-domain movies & classic TV (DIRECT MP4)
# ==========================================================================
class ArchiveOrgScraper(FreeStreamBase):
    """Internet Archive public-domain video library.

    Uses archive.org's advancedsearch JSON API to find matches, then the
    metadata API to pull the actual MP4/MPG/OGV file URLs. No embeds, no
    hosters — every link is a direct download from archive.org.
    """
    NAME = 'Archive.org'
    BASE_URL = 'https://archive.org'

    def is_enabled(self):
        return ADDON.getSetting('archiveorg_enabled') != 'false'

    # ----- helpers -----
    def _advanced_search(self, query, rows=5):
        q = quote_plus(f'({query}) AND mediatype:(movies)')
        url = (f'{self.BASE_URL}/advancedsearch.php?q={q}'
               f'&fl[]=identifier&fl[]=title&fl[]=year'
               f'&rows={rows}&output=json')
        data = _get_json(url)
        try:
            return data['response']['docs'] or []
        except Exception:
            return []

    def _sources_for_identifier(self, ident, label=''):
        meta_url = f'{self.BASE_URL}/metadata/{ident}'
        data = _get_json(meta_url)
        sources = []
        if not data:
            return sources
        files = data.get('files', []) or []
        for f in files:
            name = f.get('name', '')
            fmt = (f.get('format') or '').lower()
            if not name:
                continue
            if not re.search(r'\.(mp4|m4v|mpg|mpeg|ogv|webm)$', name, re.I):
                continue
            # Skip tiny derivative / sample files
            try:
                if int(f.get('size', 0)) < 20 * 1024 * 1024:  # <20MB usually trailers
                    continue
            except Exception:
                pass
            url = f'{self.BASE_URL}/download/{ident}/{quote_plus(name)}'
            q = 'HD' if '720' in fmt or '1080' in fmt or 'h.264' in fmt else 'SD'
            sources.append({
                'url': url,
                'quality': q,
                'host': 'archive.org',
                'direct': True,
                'scraper': self.NAME,
                'type': 'stream',
                'name': f'{self.NAME} | {label or name}',
                'seeds': 9998,
            })
        return sources

    # ----- public API -----
    def get_movie_sources(self, title, year=''):
        sources = []
        query = f'{title} {year}'.strip()
        for doc in self._advanced_search(query, rows=3):
            ident = doc.get('identifier')
            if not ident:
                continue
            sources.extend(self._sources_for_identifier(
                ident, label=doc.get('title', ident)))
            if sources:
                break
        return sources

    def get_episode_sources(self, title, year, season, episode):
        sources = []
        try:
            s = int(season)
            e = int(episode)
        except Exception:
            s = season
            e = episode
        query = f'{title} S{s:02d}E{e:02d}' if isinstance(s, int) else \
                f'{title} season {season} episode {episode}'
        for doc in self._advanced_search(query, rows=3):
            ident = doc.get('identifier')
            if not ident:
                continue
            sources.extend(self._sources_for_identifier(
                ident, label=doc.get('title', ident)))
            if sources:
                break
        return sources


# ==========================================================================
# 2. Cineby.ru — direct HLS via JSON
# ==========================================================================
class CinebyScraper(FreeStreamBase):
    """cineby.ru — exposes an /api/ endpoint that returns the final m3u8."""
    NAME = 'Cineby'
    BASE_URL = 'https://www.cineby.ru'
    API_URL = 'https://api.cineby.ru'

    def is_enabled(self):
        return ADDON.getSetting('cineby_enabled') != 'false'

    def _sources_from_payload(self, payload):
        found = []
        _walk_for_streams(payload or {}, found)
        out = []
        for url, label in found:
            out.append({
                'url': url,
                'quality': _quality_from_label(label, url),
                'host': 'cineby.ru',
                'direct': True,
                'scraper': self.NAME,
                'type': 'stream',
                'name': f'{self.NAME} | {labelbl or "auto"}',
                'seeds': 9997,
            })
        return out

    def get_movie_sources(self, title, year=''):
        _, tmdb = self._get_imdb_id(title, year, 'movie')
        if not tmdb:
            return []
        data = _get_json(f'{self.API_URL}/api/source/tmdb/movie/{tmdb}')
        sources = self._sources_from_payload(data)
        if not sources:
            # Fallback: playable web URL
            sources.append({
                'url': f'{self.BASE_URL}/movie/{tmdb}',
                'quality': 'HD', 'host': 'cineby.ru', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return sources

    def get_episode_sources(self, title, year, season, episode):
        _, tmdb = self._get_imdb_id(title, year, 'tvshow')
        if not tmdb:
            return []
        data = _get_json(
            f'{self.API_URL}/api/source/tmdb/tv/{tmdb}/{season}/{episode}')
        sources = self._sources_from_payload(data)
        if not sources:
            sources.append({
                'url': f'{self.BASE_URL}/tv/{tmdb}/{season}/{episode}',
                'quality': 'HD', 'host': 'cineby.ru', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return sources


# ==========================================================================
# 3. VidFast — vidfast.pro JSON API
# ==========================================================================
class VidFastScraper(FreeStreamBase):
    NAME = 'VidFast'
    BASE_URL = 'https://vidfast.pro'
    API_URL = 'https://api.vidfast.pro'

    def is_enabled(self):
        return ADDON.getSetting('vidfast_enabled') != 'false'

    def _collect(self, payload):
        found = []
        _walk_for_streams(payload or {}, found)
        return [{
            'url': u, 'quality': _quality_from_label(lbl, u),
            'host': 'vidfast.pro', 'direct': True,
            'scraper': self.NAME, 'type': 'stream',
            'name': f'{self.NAME} | {lbl or "auto"}', 'seeds': 9996,
        } for u, lbl in found]

    def get_movie_sources(self, title, year=''):
        _, tmdb = self._get_imdb_id(title, year, 'movie')
        if not tmdb:
            return []
        data = _get_json(f'{self.API_URL}/movie/{tmdb}')
        srcs = self._collect(data)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/movie/{tmdb}',
                'quality': 'HD', 'host': 'vidfast.pro', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs

    def get_episode_sources(self, title, year, season, episode):
        _, tmdb = self._get_imdb_id(title, year, 'tvshow')
        if not tmdb:
            return []
        data = _get_json(f'{self.API_URL}/tv/{tmdb}/{season}/{episode}')
        srcs = self._collect(data)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/tv/{tmdb}/{season}/{episode}',
                'quality': 'HD', 'host': 'vidfast.pro', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs


# ==========================================================================
# 4. RiveStream — rivestream.net / rivestream.live JSON API
# ==========================================================================
class RiveStreamScraper(FreeStreamBase):
    NAME = 'RiveStream'
    BASE_URL = 'https://rivestream.net'

    # Rive supports multiple internal providers — all return direct m3u8
    PROVIDERS = ('flowcast', 'shadow', 'asiacloud', 'hindicast',
                 'anime', 'animez', 'nova', 'prime', 'langitkuning')

    def is_enabled(self):
        return ADDON.getSetting('rivestream_enabled') != 'false'

    def _collect(self, payload, provider=''):
        found = []
        _walk_for_streams(payload or {}, found)
        return [{
            'url': u, 'quality': _quality_from_label(lbl, u),
            'host': f'rivestream.net/{provider}' if provider else 'rivestream.net',
            'direct': True, 'scraper': self.NAME, 'type': 'stream',
            'name': f'{self.NAME} [{provider}] {lbl or "auto"}'.strip(),
            'seeds': 9995,
        } for u, lbl in found]

    def _fetch(self, kind, tmdb, season=None, episode=None):
        sources = []
        for prov in self.PROVIDERS:
            if kind == 'movie':
                url = (f'{self.BASE_URL}/api/backendfetch'
                       f'?requestID=movieVideoProvider&id={tmdb}&service={prov}')
            else:
                url = (f'{self.BASE_URL}/api/backendfetch'
                       f'?requestID=tvVideoProvider&id={tmdb}'
                       f'&season={season}&episode={episode}&service={prov}')
            data = _get_json(url, timeout=8)
            sources.extend(self._collect(data, prov))
            if len(sources) >= 3:
                break
        return sources

    def get_movie_sources(self, title, year=''):
        _, tmdb = self._get_imdb_id(title, year, 'movie')
        if not tmdb:
            return []
        srcs = self._fetch('movie', tmdb)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/watch?id={tmdb}&type=movie',
                'quality': 'HD', 'host': 'rivestream.net', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs

    def get_episode_sources(self, title, year, season, episode):
        _, tmdb = self._get_imdb_id(title, year, 'tvshow')
        if not tmdb:
            return []
        srcs = self._fetch('tv', tmdb, season, episode)
        if not srcs:
            srcs.append({
                'url': (f'{self.BASE_URL}/watch?id={tmdb}&type=tv'
                        f'&season={season}&episode={episode}'),
                'quality': 'HD', 'host': 'rivestream.net', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs


# ==========================================================================
# 5. UiraLive — uira.live JSON API
# ==========================================================================
class UiraLiveScraper(FreeStreamBase):
    NAME = 'UiraLive'
    BASE_URL = 'https://uira.live'

    def is_enabled(self):
        return ADDON.getSetting('uiralive_enabled') != 'false'

    def _collect(self, payload):
        found = []
        _walk_for_streams(payload or {}, found)
        return [{
            'url': u, 'quality': _quality_from_label(lbl, u),
            'host': 'uira.live', 'direct': True,
            'scraper': self.NAME, 'type': 'stream',
            'name': f'{self.NAME} | {lbl or "auto"}', 'seeds': 9994,
        } for u, lbl in found]

    def get_movie_sources(self, title, year=''):
        _, tmdb = self._get_imdb_id(title, year, 'movie')
        if not tmdb:
            return []
        data = _get_json(f'{self.BASE_URL}/api/sources/movie/{tmdb}')
        srcs = self._collect(data)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/movie/{tmdb}', 'quality': 'HD',
                'host': 'uira.live', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs

    def get_episode_sources(self, title, year, season, episode):
        _, tmdb = self._get_imdb_id(title, year, 'tvshow')
        if not tmdb:
            return []
        data = _get_json(
            f'{self.BASE_URL}/api/sources/tv/{tmdb}/{season}/{episode}')
        srcs = self._collect(data)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/tv/{tmdb}/{season}/{episode}',
                'quality': 'HD', 'host': 'uira.live', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs


# ==========================================================================
# 6. NetMirror — Netflix-mirror style API
# ==========================================================================
class NetMirrorScraper(FreeStreamBase):
    NAME = 'NetMirror'
    BASE_URL = 'https://netmirror.8man.live'

    def is_enabled(self):
        return ADDON.getSetting('netmirror_enabled') != 'false'

    def _collect(self, payload):
        found = []
        _walk_for_streams(payload or {}, found)
        return [{
            'url': u, 'quality': _quality_from_label(lbl, u),
            'host': 'netmirror', 'direct': True,
            'scraper': self.NAME, 'type': 'stream',
            'name': f'{self.NAME} | {lbl or "auto"}', 'seeds': 9993,
        } for u, lbl in found]

    def get_movie_sources(self, title, year=''):
        _, tmdb = self._get_imdb_id(title, year, 'movie')
        if not tmdb:
            return []
        data = _get_json(f'{self.BASE_URL}/api/movie/{tmdb}')
        srcs = self._collect(data)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/movie/{tmdb}',
                'quality': 'HD', 'host': 'netmirror', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs

    def get_episode_sources(self, title, year, season, episode):
        _, tmdb = self._get_imdb_id(title, year, 'tvshow')
        if not tmdb:
            return []
        data = _get_json(
            f'{self.BASE_URL}/api/tv/{tmdb}/{season}/{episode}')
        srcs = self._collect(data)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/tv/{tmdb}/{season}/{episode}',
                'quality': 'HD', 'host': 'netmirror', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs


# ==========================================================================
# 7. VidBinge — vidbinge.com direct HLS
# ==========================================================================
class VidBingeScraper(FreeStreamBase):
    NAME = 'VidBinge'
    BASE_URL = 'https://vidbinge.com'
    API_URL = 'https://api.vidbinge.com'

    def is_enabled(self):
        return ADDON.getSetting('vidbinge_enabled') != 'false'

    def _collect(self, payload):
        found = []
        _walk_for_streams(payload or {}, found)
        return [{
            'url': u, 'quality': _quality_from_label(lbl, u),
            'host': 'vidbinge.com', 'direct': True,
            'scraper': self.NAME, 'type': 'stream',
            'name': f'{self.NAME} | {lbl or "auto"}', 'seeds': 9992,
        } for u, lbl in found]

    def get_movie_sources(self, title, year=''):
        _, tmdb = self._get_imdb_id(title, year, 'movie')
        if not tmdb:
            return []
        data = _get_json(f'{self.API_URL}/movie/{tmdb}')
        srcs = self._collect(data)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/movie/{tmdb}',
                'quality': 'HD', 'host': 'vidbinge.com', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs

    def get_episode_sources(self, title, year, season, episode):
        _, tmdb = self._get_imdb_id(title, year, 'tvshow')
        if not tmdb:
            return []
        data = _get_json(f'{self.API_URL}/tv/{tmdb}/{season}/{episode}')
        srcs = self._collect(data)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/tv/{tmdb}/{season}/{episode}',
                'quality': 'HD', 'host': 'vidbinge.com', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs


# ==========================================================================
# 8. HollyMovieHD — hollymoviehd.cc JSON API
# ==========================================================================
class HollyMovieHDScraper(FreeStreamBase):
    NAME = 'HollyMovieHD'
    BASE_URL = 'https://hollymoviehd.cc'

    def is_enabled(self):
        return ADDON.getSetting('hollymoviehd_enabled') != 'false'

    def _collect(self, payload):
        found = []
        _walk_for_streams(payload or {}, found)
        return [{
            'url': u, 'quality': _quality_from_label(lbl, u),
            'host': 'hollymoviehd.cc', 'direct': True,
            'scraper': self.NAME, 'type': 'stream',
            'name': f'{self.NAME} | {lbl or "auto"}', 'seeds': 9991,
        } for u, lbl in found]

    def get_movie_sources(self, title, year=''):
        _, tmdb = self._get_imdb_id(title, year, 'movie')
        if not tmdb:
            return []
        data = _get_json(f'{self.BASE_URL}/api/v1/source/movie/{tmdb}')
        srcs = self._collect(data)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/movie/{tmdb}',
                'quality': 'HD', 'host': 'hollymoviehd.cc', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs

    def get_episode_sources(self, title, year, season, episode):
        _, tmdb = self._get_imdb_id(title, year, 'tvshow')
        if not tmdb:
            return []
        data = _get_json(
            f'{self.BASE_URL}/api/v1/source/tv/{tmdb}/{season}/{episode}')
        srcs = self._collect(data)
        if not srcs:
            srcs.append({
                'url': f'{self.BASE_URL}/tv/{tmdb}/{season}/{episode}',
                'quality': 'HD', 'host': 'hollymoviehd.cc', 'direct': False,
                'scraper': self.NAME, 'type': 'embed',
                'name': f'{self.NAME} page', 'seeds': 9000,
            })
        return srcs


# ==========================================================================
# Export list — consumed by scrapers/__init__.py
# ==========================================================================
DIRECT_STREAM_SCRAPERS = [
    ArchiveOrgScraper,
    CinebyScraper,
    VidFastScraper,
    RiveStreamScraper,
    UiraLiveScraper,
    NetMirrorScraper,
    VidBingeScraper,
    HollyMovieHDScraper,
]
