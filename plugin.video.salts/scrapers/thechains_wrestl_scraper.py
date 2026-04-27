"""
TheChains Wrestling Scraper (2026-04, v2.9.8)
Direct free streams for WWE / AEW / NXT / wrestling shows.
Source: https://thechains24.com/1/WRESTL.txt

Format (mixed):
  <item>...<title>..</title>...<sublink>https://streamtape.com/v/...</sublink>...</item>
  <dir>...<title>..</title>...<link>.../SEASON 1.txt</link>...</dir>

For this first pass we expose the flat <item> entries directly (treated as
movies / special events). The <dir> series entries are resolved lazily when
the user's search query matches the series title.
"""
import re
import time
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from .base_scraper import BaseScraper

ADDON = xbmcaddon.Addon()

INDEX_URL = 'https://thechains24.com/1/WRESTL.txt'
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Simple module-level caches (shared across instances within a Kodi session)
_cache_index = None
_cache_index_time = 0
_cache_dirs = {}          # url -> (timestamp, [items])
INDEX_TTL = 3600          # 1 hour
DIR_TTL = 3600


# ---------- helpers -------------------------------------------------------

def _norm(text):
    if not text:
        return ''
    text = text.lower()
    text = re.sub(r"[\u2018\u2019\u201c\u201d']", '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _parse_quality(url):
    u = (url or '').lower()
    if '2160' in u or '4k' in u or 'uhd' in u:
        return '4K'
    if '1080' in u:
        return '1080p'
    if '720' in u:
        return '720p'
    if '480' in u:
        return '480p'
    return '720p'


def _host_from_url(url):
    u = (url or '').lower()
    if 'streamtape' in u:
        return 'Streamtape'
    if 'luluv' in u:
        return 'LuluVid'
    if 'doodstream' in u or 'dood.' in u:
        return 'DoodStream'
    return 'DirectLink'


def _fetch(url, timeout=15):
    try:
        req = Request(url, headers={'User-Agent': USER_AGENT})
        resp = urlopen(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        xbmc.log(f'TheChainsWrestl: fetch failed {url}: {e}', xbmc.LOGWARNING)
        return ''


def _parse_items(raw):
    """Extract <item>...</item> blocks. Returns list of dicts."""
    items = []
    for block in re.findall(r'<item>(.*?)</item>', raw, re.DOTALL):
        title_m = re.search(r'<title>\s*(.*?)\s*</title>', block, re.DOTALL)
        if not title_m:
            continue
        title = re.sub(r'\s+', ' ', title_m.group(1)).strip()
        if not title:
            continue

        # Stream links
        subs = re.findall(r'<sublink>\s*(\S+?)\s*</sublink>', block, re.DOTALL)
        if not subs:
            # Fallback: any <link> containing http
            subs = re.findall(r'<link>\s*(https?://\S+?)\s*</link>', block, re.DOTALL)
        subs = [re.sub(r'[<>"\s].*$', '', s).strip() for s in subs if s]
        subs = [s for s in subs if s.startswith(('http://', 'https://'))]
        # Dedupe while preserving order
        seen = set()
        subs = [s for s in subs if not (s in seen or seen.add(s))]
        if not subs:
            continue

        summary_m = re.search(r'<summary>(.*?)</summary>', block, re.DOTALL)
        poster_m = re.search(r'<thumbnail>(.*?)</thumbnail>', block, re.DOTALL)

        items.append({
            'title': title,
            'norm_title': _norm(title),
            'streams': subs,
            'summary': summary_m.group(1).strip() if summary_m else '',
            'poster': poster_m.group(1).strip() if poster_m else '',
        })
    return items


def _parse_dirs(raw):
    """Extract <dir>...</dir> blocks pointing to nested .txt listings."""
    dirs = []
    for block in re.findall(r'<dir>(.*?)</dir>', raw, re.DOTALL):
        title_m = re.search(r'<title>\s*(.*?)\s*</title>', block, re.DOTALL)
        link_m = re.search(r'<link>\s*(\S+?)\s*</link>', block, re.DOTALL)
        if not (title_m and link_m):
            continue
        title = re.sub(r'\s+', ' ', title_m.group(1)).strip()
        link = link_m.group(1).strip()
        if not title or not link.startswith('http'):
            continue
        dirs.append({
            'title': title,
            'norm_title': _norm(title),
            'link': link,
        })
    return dirs


def _load_index():
    global _cache_index, _cache_index_time
    if _cache_index and (time.time() - _cache_index_time) < INDEX_TTL:
        return _cache_index
    raw = _fetch(INDEX_URL)
    index = {
        'items': _parse_items(raw) if raw else [],
        'dirs': _parse_dirs(raw) if raw else [],
    }
    _cache_index = index
    _cache_index_time = time.time()
    xbmc.log(
        f'TheChainsWrestl: index parsed {len(index["items"])} events / '
        f'{len(index["dirs"])} series',
        xbmc.LOGINFO,
    )
    return index


def _load_dir_items(url):
    now = time.time()
    cached = _cache_dirs.get(url)
    if cached and (now - cached[0]) < DIR_TTL:
        return cached[1]
    raw = _fetch(url)
    items = _parse_items(raw) if raw else []
    _cache_dirs[url] = (now, items)
    return items


# ---------- scraper -------------------------------------------------------

class TheChainsWrestlScraper(BaseScraper):
    """Free wrestling streams scraper backed by thechains24.com/1/WRESTL.txt"""
    NAME = 'Bones 2 Wrestling'
    BASE_URL = 'https://thechains24.com'
    is_free = True  # allow running without a configured debrid service

    def is_enabled(self):
        return ADDON.getSetting('thechains_wrestl_enabled') != 'false'

    # ---- matching ----
    def _match_title(self, query_norm, candidate_norm):
        if not query_norm or not candidate_norm:
            return False
        if query_norm == candidate_norm:
            return True
        # Contain check in either direction
        if query_norm in candidate_norm or candidate_norm in query_norm:
            return True
        # Word-set overlap (drop tiny stopwords)
        stop = {'a', 'an', 'the', 'of', 'and', 'or', 'to', 'in', 'on', 'wwe', 'aew'}
        qw = set(query_norm.split()) - stop
        cw = set(candidate_norm.split()) - stop
        if qw and qw.issubset(cw):
            return True
        return False

    def _make_source(self, item_title, stream_url, extra_tag=''):
        quality = _parse_quality(stream_url)
        host = _host_from_url(stream_url)
        label_prefix = '[TheChains Wrestling]'
        if extra_tag:
            label_prefix = f'[TheChains Wrestling {extra_tag}]'
        return {
            'multi-part': False,
            'host': host,
            'quality': quality,
            'label': f'{label_prefix} {item_title}',
            'title': f'{label_prefix} {item_title}',
            'rating': None,
            'views': None,
            'direct': True,
            'url': stream_url,
            'magnet': '',
            'seeds': 9999,
            'size': '',
            'is_free_link': True,
            'source': 'Bones 2 Wrestling',
        }

    def search(self, query, media_type='movie', **kwargs):
        title = (kwargs.get('title') or query or '').strip()
        season = str(kwargs.get('season') or '').strip()
        episode = str(kwargs.get('episode') or '').strip()

        clean_title = re.sub(r'\s*\(?\d{4}\)?\s*$', '', title).strip()
        q_norm = _norm(clean_title)
        if not q_norm:
            return []

        index = _load_index()
        results = []

        # 1) Flat <item> matches (events — Wrestlemania, Raw, Dynamite, etc.)
        for it in index['items']:
            if not self._match_title(q_norm, it['norm_title']):
                continue
            for idx, url in enumerate(it['streams']):
                tag = 'Mirror' if idx > 0 else ''
                results.append(self._make_source(it['title'], url, tag))

        # 2) <dir> matches (series) — follow the link and look for episode.
        # Only do this when the query looks series-oriented or episode info
        # was provided, to keep latency low.
        if index['dirs']:
            for d in index['dirs']:
                if not self._match_title(q_norm, d['norm_title']):
                    continue
                sub_items = _load_dir_items(d['link'])
                for it in sub_items:
                    # If season/episode provided, prefer matching that.
                    if season and episode:
                        try:
                            s = int(season)
                            e = int(episode)
                        except ValueError:
                            s, e = 0, 0
                        ep_token_a = f's{s:02d}e{e:02d}'
                        ep_token_b = f'episode {e}'
                        hay = _norm(it['title'])
                        stream_hay = ' '.join(it['streams']).lower()
                        if ep_token_a not in stream_hay and ep_token_b not in hay:
                            continue
                    for idx, url in enumerate(it['streams']):
                        tag = 'Mirror' if idx > 0 else ''
                        label = f'{d["title"]} - {it["title"]}'
                        results.append(self._make_source(label, url, tag))

        xbmc.log(
            f'TheChainsWrestl: {len(results)} source(s) for "{clean_title}"',
            xbmc.LOGINFO,
        )
        return results
