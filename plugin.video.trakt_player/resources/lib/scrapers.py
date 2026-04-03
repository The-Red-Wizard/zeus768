# -*- coding: utf-8 -*-
"""Torrent scrapers. Native urllib only. No free streams."""
import json
import re
import ssl
import urllib.request
import urllib.error
from urllib.parse import quote_plus
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
SSL_CTX = ssl._create_unverified_context()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

QUALITY_PATTERNS = {
    '2160p': re.compile(r'(?:2160p|4k|uhd)', re.I),
    '1080p': re.compile(r'(?:1080p|1080i|fhd)', re.I),
    '720p': re.compile(r'(?:720p|hd(?!r))', re.I),
    '480p': re.compile(r'(?:480p|sd)', re.I),
}

QUALITY_ORDER = ['1080p', '720p', '480p']

TRACKERS = [
    'udp://tracker.opentrackr.org:1337/announce',
    'udp://open.stealth.si:80/announce',
    'udp://tracker.torrent.eu.org:451/announce',
    'udp://tracker.bittor.pw:1337/announce',
    'udp://public.popcorn-tracker.org:6969/announce',
    'udp://tracker.dler.org:6969/announce',
    'udp://exodus.desync.com:6969/announce',
]


def _get(url, headers=None):
    hdrs = {'User-Agent': UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=12) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        xbmc.log('Scraper HTTP error: %s' % str(e), xbmc.LOGWARNING)
        return ''


def _get_json(url, headers=None):
    raw = _get(url, headers)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


def detect_quality(title):
    if QUALITY_PATTERNS['2160p'].search(title):
        return '2160p'
    if QUALITY_PATTERNS['1080p'].search(title):
        return '1080p'
    if QUALITY_PATTERNS['720p'].search(title):
        return '720p'
    if QUALITY_PATTERNS['480p'].search(title):
        return '480p'
    return '720p'


def _make_magnet(info_hash, name):
    m = 'magnet:?xt=urn:btih:%s&dn=%s' % (info_hash, quote_plus(name))
    for tr in TRACKERS:
        m += '&tr=' + quote_plus(tr)
    return m


def extract_hash(magnet):
    """Extract info_hash from a magnet URI."""
    match = re.search(r'btih:([a-fA-F0-9]{40})', magnet)
    if match:
        return match.group(1).lower()
    match = re.search(r'btih:([a-zA-Z2-7]{32})', magnet)
    if match:
        return match.group(1).lower()
    return ''


def _filter_quality(results, max_quality='1080p'):
    """Remove anything above max_quality (discard 4K/2160p)."""
    allowed = set(QUALITY_ORDER[QUALITY_ORDER.index(max_quality):]) if max_quality in QUALITY_ORDER else set(QUALITY_ORDER)
    return [r for r in results if r.get('quality') in allowed]


def _sort_results(results):
    """Sort by quality (best first), then by seeds descending."""
    order_map = {q: i for i, q in enumerate(QUALITY_ORDER)}
    return sorted(results, key=lambda r: (order_map.get(r.get('quality', '720p'), 9), -r.get('seeds', 0)))


# ── PirateBay ────────────────────────────────────────────────────────────

def _scrape_piratebay(query):
    results = []
    mirrors = ['https://apibay.org', 'https://piratebay.party']
    for mirror in mirrors:
        data = _get_json('%s/q.php?q=%s&cat=200' % (mirror, quote_plus(query)))
        if data and isinstance(data, list) and data[0].get('id') != '0':
            for item in data[:25]:
                if item.get('id') == '0':
                    continue
                name = item.get('name', '')
                quality = detect_quality(name)
                results.append({
                    'title': name,
                    'magnet': _make_magnet(item.get('info_hash', ''), name),
                    'seeds': int(item.get('seeders', 0)),
                    'size': int(item.get('size', 0)),
                    'quality': quality,
                    'source': 'PirateBay'
                })
            break
    return results


# ── TorrentGalaxy ────────────────────────────────────────────────────────

def _scrape_torrentgalaxy(query):
    results = []
    html = _get('https://torrentgalaxy.to/torrents.php?search=%s&sort=seeders&order=desc' % quote_plus(query))
    if not html:
        return results
    magnets = re.findall(r'href="(magnet:\?xt=urn:btih:[^"]+)"', html)
    titles = re.findall(r'class="txlight">([^<]+)</a>', html)
    for i, magnet in enumerate(magnets[:20]):
        title = titles[i] if i < len(titles) else 'Result %d' % (i + 1)
        results.append({
            'title': title,
            'magnet': magnet,
            'seeds': 0,
            'quality': detect_quality(title),
            'source': 'TorrentGalaxy'
        })
    return results


# ── 1337x ─────────────────────────────────────────────────────────────────

def _scrape_1337x(query):
    results = []
    html = _get('https://1337x.to/search/%s/1/' % quote_plus(query))
    if not html:
        return results
    links = re.findall(r'<a href="(/torrent/\d+/[^"]+)"', html)
    for link in links[:15]:
        detail = _get('https://1337x.to' + link)
        if not detail:
            continue
        mag = re.search(r'href="(magnet:\?xt=urn:btih:[^"]+)"', detail)
        name_m = re.search(r'<title>Download\s+(.+?)\s+Torrent', detail)
        seed_m = re.search(r'Seeders.*?(\d+)', detail, re.S)
        if mag:
            name = name_m.group(1) if name_m else link.split('/')[-1].replace('-', ' ')
            results.append({
                'title': name,
                'magnet': mag.group(1),
                'seeds': int(seed_m.group(1)) if seed_m else 0,
                'quality': detect_quality(name),
                'source': '1337x'
            })
    return results


# ── YTS ───────────────────────────────────────────────────────────────────

def _scrape_yts(query):
    results = []
    data = _get_json('https://yts.mx/api/v2/list_movies.json?query_term=%s&sort_by=seeds&limit=20' % quote_plus(query))
    if isinstance(data, dict):
        movies = data.get('data', {}).get('movies', [])
        for movie in movies:
            for torrent in movie.get('torrents', []):
                quality = torrent.get('quality', '720p')
                name = '%s (%s) [%s]' % (movie.get('title', ''), movie.get('year', ''), quality)
                results.append({
                    'title': name,
                    'magnet': _make_magnet(torrent.get('hash', ''), name),
                    'seeds': torrent.get('seeds', 0),
                    'size': torrent.get('size_bytes', 0),
                    'quality': quality if quality in ('1080p', '720p', '480p', '2160p') else detect_quality(quality),
                    'source': 'YTS'
                })
    return results


# ── EZTV (TV shows) ──────────────────────────────────────────────────────

def _scrape_eztv(query):
    results = []
    data = _get_json('https://eztv.re/api/get-torrents?imdb_id=0&limit=30&page=1&query=%s' % quote_plus(query))
    if isinstance(data, dict):
        for t in data.get('torrents', []):
            name = t.get('title', '')
            results.append({
                'title': name,
                'magnet': t.get('magnet_url', ''),
                'seeds': t.get('seeds', 0),
                'size': t.get('size_bytes', 0),
                'quality': detect_quality(name),
                'source': 'EZTV'
            })
    return results


# ── Public API ────────────────────────────────────────────────────────────

def search_all(query, max_quality='1080p'):
    """Run all scrapers, filter <=max_quality, sort best first."""
    all_results = []
    scrapers = [
        ('PirateBay', _scrape_piratebay),
        ('YTS', _scrape_yts),
        ('EZTV', _scrape_eztv),
        ('1337x', _scrape_1337x),
        ('TorrentGalaxy', _scrape_torrentgalaxy),
    ]
    for name, fn in scrapers:
        try:
            xbmc.log('Scraping %s for: %s' % (name, query), xbmc.LOGINFO)
            results = fn(query)
            xbmc.log('%s returned %d results' % (name, len(results)), xbmc.LOGINFO)
            all_results.extend(results)
        except Exception as e:
            xbmc.log('Scraper %s failed: %s' % (name, str(e)), xbmc.LOGWARNING)

    filtered = _filter_quality(all_results, max_quality)
    xbmc.log('Total results: %d, after filter (<=%s): %d' % (len(all_results), max_quality, len(filtered)), xbmc.LOGINFO)
    return _sort_results(filtered)
