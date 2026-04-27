"""
PlanetScrapers - SALTS BaseScraper wrapper

Aggregates the bundled Torrentio + PirateBay + RARBG + TorrentGalaxy + 1337x
search backends (originally from C.O.S.M.O.S, ported into SALTS as
salts_lib/planet_scrapers.py) and exposes them as a single SALTS scraper
entry so the existing source-list / debrid pipeline can consume them
without any per-backend wiring.

Settings keys honoured by the underlying backends:
    enable_torrentio, enable_piratebay, enable_rarbg,
    enable_torrentgalaxy, enable_1337x
"""
from .base_scraper import TorrentScraper
from salts_lib import log_utils
from salts_lib import planet_scrapers as _backend


class PlanetScraper(TorrentScraper):
    """SALTS scraper that delegates to the planet_scrapers aggregator."""

    NAME = 'PlanetScrapers'
    BASE_URL = 'planetscrapers://aggregate'

    def search(self, query, media_type='movie'):
        try:
            results = _backend.search_all(
                query,
                preferred_quality='1080p',
                imdb_id=None,
                content='movie' if media_type == 'movie' else 'tv',
                season=None,
                episode=None,
            )
        except Exception as e:
            log_utils.log_error(f'PlanetScrapers: search error: {e}')
            return []

        out = []
        for r in results or []:
            magnet = r.get('magnet', '')
            out.append({
                'title': r.get('title', ''),
                'url': magnet,
                'magnet': magnet,
                'quality': r.get('quality', 'SD'),
                'size': r.get('size', 'Unknown'),
                'seeds': int(r.get('seeds', 0) or 0),
                'peers': int(r.get('peers', 0) or 0),
                'source': r.get('source', 'PlanetScrapers'),
            })
        return out

    def get_episode_sources(self, title, year, season, episode):
        """TV episode search - calls aggregator with content=tv so its
        per-episode title filter kicks in.
        """
        try:
            results = _backend.search_all(
                f'{title} S{int(season):02d}E{int(episode):02d}',
                preferred_quality='1080p',
                imdb_id=None,
                content='tv',
                season=int(season),
                episode=int(episode),
            )
        except Exception as e:
            log_utils.log_error(f'PlanetScrapers: episode search error: {e}')
            return []

        out = []
        for r in results or []:
            magnet = r.get('magnet', '')
            out.append({
                'title': r.get('title', ''),
                'url': magnet,
                'magnet': magnet,
                'quality': r.get('quality', 'SD'),
                'size': r.get('size', 'Unknown'),
                'seeds': int(r.get('seeds', 0) or 0),
                'peers': int(r.get('peers', 0) or 0),
                'source': r.get('source', 'PlanetScrapers'),
            })
        return out
