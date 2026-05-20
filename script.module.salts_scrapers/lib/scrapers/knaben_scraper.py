"""
SALTS Scrapers - Knaben Torrent Aggregator

Knaben (https://knaben.org) is a public torrent indexer / aggregator with
a JSON search API at https://api.knaben.org/v1. No API key is required.

The API takes a JSON body:
    {
      "search_type":   "score",
      "search_field":  "title",
      "query":         "<text>",
      "order_by":      "seeders",
      "order_direction": "desc",
      "size":          100,
      "from":          0,
      "hide_unsafe":   true,
      "hide_xxx":      true,
      "categories":    [[2000000],[2001000]]   # optional, see Knaben docs
    }

Each hit contains: id, title, hash, magnetUrl, seeders, peers, bytes,
date, tracker, category. We map these into the SALTS source dict shape.
"""
import json
import re
import ssl
from urllib.request import Request, urlopen
from urllib.parse import quote_plus

from .base_scraper import TorrentScraper
from salts_lib import log_utils


class KnabenScraper(TorrentScraper):
    """Knaben aggregator — covers TPB, 1337x, Nyaa, RuTracker etc. in one call."""

    BASE_URL = 'https://api.knaben.org/v1'
    NAME = 'Knaben'

    # SALTS-style is_enabled() uses setting `knaben_enabled`
    # (declared in plugin.video.salts settings.xml).

    _UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
           'AppleWebKit/537.36 (KHTML, like Gecko) '
           'Chrome/131.0.0.0 Safari/537.36')

    @staticmethod
    def _format_bytes(n):
        try:
            n = int(n)
        except (TypeError, ValueError):
            return ''
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if n < 1024:
                return f'{n:.2f} {unit}' if unit != 'B' else f'{n} B'
            n /= 1024
        return f'{n:.2f} PB'

    def _api_search(self, query, size=100):
        body = json.dumps({
            'search_type': 'score',
            'search_field': 'title',
            'query': query,
            'order_by': 'seeders',
            'order_direction': 'desc',
            'size': size,
            'from': 0,
            'hide_unsafe': True,
            'hide_xxx': True,
        }).encode('utf-8')
        req = Request(
            self.BASE_URL,
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': self._UA,
            },
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8', errors='replace'))

    def search(self, query, media_type='movie', **kwargs):
        """Search Knaben for the requested title."""
        results = []
        try:
            data = self._api_search(query)
        except Exception as e:
            log_utils.log_error(f'Knaben: search error: {e}')
            return results

        hits = (data or {}).get('hits') or []
        for hit in hits:
            try:
                title = hit.get('title') or ''
                info_hash = (hit.get('hash') or '').lower()
                magnet = hit.get('magnetUrl') or ''
                # If magnet is missing but we have a hash, synthesise one
                # so the addon can still resolve via debrid.
                if not magnet and info_hash and re.fullmatch(r'[a-f0-9]{40}', info_hash):
                    magnet = self._make_magnet(info_hash, title)
                if not magnet:
                    continue

                seeds = hit.get('seeders') or 0
                peers = hit.get('peers') or 0
                size = self._format_bytes(hit.get('bytes'))
                tracker = hit.get('tracker') or 'Knaben'

                results.append({
                    'title': title,
                    'url': hit.get('details') or '',
                    'magnet': magnet,
                    'quality': self._parse_quality(title),
                    'size': size,
                    'seeds': int(seeds) if isinstance(seeds, (int, float)) else 0,
                    'peers': int(peers) if isinstance(peers, (int, float)) else 0,
                    'host': f'Knaben ({tracker})',
                })
            except Exception as e:
                log_utils.log_error(f'Knaben: parse error: {e}')
                continue

        return results
