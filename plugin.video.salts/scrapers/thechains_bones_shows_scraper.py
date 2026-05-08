"""
TheChains "Bones" TV Shows Scraper (2026-04, v2.9.8)
Free direct streams for the Non-Show / classic TV catalog at:
  https://thechains24.com/ABSOLUTION/SHOWS/NON%20SHOWS/MAIN%20DIR.txt

The catalog is three-tier:
  Level 0 (MAIN DIR.txt)  -> <dir> entries per show, each <link> points to
                             either a SEASON X.txt directly OR a nested
                             MAIN DIR.txt listing seasons.
  Level 1 (MAIN DIR.txt)  -> <dir> entries per season, <link> -> SEASON X.txt
  Level 2 (SEASON X.txt)  -> <item> entries per episode with a direct
                             <link>https://streamtape.com/...</link>.

We walk up to two levels of <dir> redirection so both shapes work.
"""
import re
import time
import xbmc
import xbmcaddon

from urllib.request import urlopen, Request
from .base_scraper import BaseScraper

ADDON = xbmcaddon.Addon()

INDEX_URL = ('https://thechains24.com/ABSOLUTION/SHOWS/NON%20SHOWS/'
             'MAIN%20DIR.txt')
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

INDEX_TTL = 3600       # 1 hour
NODE_TTL = 3600
MAX_DIR_DEPTH = 2      # MAIN DIR.txt -> MAIN DIR.txt -> SEASON X.txt

_cache_index = None
_cache_index_time = 0
_cache_nodes = {}       # url -> (ts, {"items": [...], "dirs": [...]} )


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
    return 'SD'


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
        return urlopen(req, timeout=timeout).read().decode('utf-8', errors='ignore')
    except Exception as e:
        xbmc.log(f'TheChainsBonesShows: fetch failed {url}: {e}', xbmc.LOGWARNING)
        return ''


def _parse_node(raw):
    """Parse a .txt listing. Returns {'items': [...], 'dirs': [...]}"""
    node = {'items': [], 'dirs': []}
    if not raw:
        return node

    for block in re.findall(r'<item>(.*?)</item>', raw, re.DOTALL):
        title_m = re.search(r'<title>\s*(.*?)\s*</title>', block, re.DOTALL)
        if not title_m:
            continue
        title = re.sub(r'\s+', ' ', title_m.group(1)).strip()
        links = re.findall(r'<link>\s*(https?://\S+?)\s*</link>', block, re.DOTALL)
        links += re.findall(r'<sublink>\s*(https?://\S+?)\s*</sublink>', block, re.DOTALL)
        links = [re.sub(r'[<>"\s].*$', '', s).strip() for s in links if s]
        links = [s for s in links if s.startswith(('http://', 'https://'))]
        # Dedupe
        seen = set()
        links = [l for l in links if not (l in seen or seen.add(l))]
        if not (title and links):
            continue
        node['items'].append({
            'title': title,
            'norm_title': _norm(title),
            'streams': links,
        })

    for block in re.findall(r'<dir>(.*?)</dir>', raw, re.DOTALL):
        title_m = re.search(r'<title>\s*(.*?)\s*</title>', block, re.DOTALL)
        link_m = re.search(r'<link>\s*(\S+?)\s*</link>', block, re.DOTALL)
        if not (title_m and link_m):
            continue
        title = re.sub(r'\s+', ' ', title_m.group(1)).strip()
        link = link_m.group(1).strip()
        if not title or not link.startswith('http'):
            continue
        node['dirs'].append({
            'title': title,
            'norm_title': _norm(title),
            'link': link,
        })
    return node


def _load_node(url):
    now = time.time()
    cached = _cache_nodes.get(url)
    if cached and (now - cached[0]) < NODE_TTL:
        return cached[1]
    node = _parse_node(_fetch(url))
    _cache_nodes[url] = (now, node)
    return node


def _load_index():
    global _cache_index, _cache_index_time
    if _cache_index and (time.time() - _cache_index_time) < INDEX_TTL:
        return _cache_index
    node = _load_node(INDEX_URL)
    _cache_index = node
    _cache_index_time = time.time()
    xbmc.log(
        f'TheChainsBonesShows: index parsed {len(node["items"])} items / '
        f'{len(node["dirs"])} shows',
        xbmc.LOGINFO,
    )
    return node


def _season_matches(season, node_title):
    """Check whether a 'Season N' <dir> title corresponds to requested season."""
    if not season:
        return True
    try:
        s = int(season)
    except ValueError:
        return True
    m = re.search(r'\bseason\s+(\d+)\b', node_title.lower())
    return bool(m and int(m.group(1)) == s)


def _episode_matches(episode, item_title, stream_url):
    """Match episode by E## token or 'Episode N' phrasing."""
    if not episode:
        return True
    try:
        e = int(episode)
    except ValueError:
        return True
    title_l = item_title.lower()
    url_l = (stream_url or '').lower()
    patterns = [
        rf'\be{e:02d}\b',
        rf's\d{{1,2}}e{e:02d}',
        rf'episode\s+{e}\b',
        rf'\bep\s*0*{e}\b',
    ]
    for pat in patterns:
        if re.search(pat, title_l) or re.search(pat, url_l):
            return True
    return False


# ---------- scraper -------------------------------------------------------

class TheChainsBonesShowsScraper(BaseScraper):
    """Free TV-show streams from thechains24.com Non-Shows catalog."""
    NAME = 'Bones 2 Shows'
    BASE_URL = 'https://thechains24.com'
    is_free = True

    def is_enabled(self):
        return ADDON.getSetting('thechains_bones_shows_enabled') != 'false'

    def _match_show(self, query_norm, show_norm):
        if not query_norm or not show_norm:
            return False
        if query_norm == show_norm:
            return True
        stop = {'a', 'an', 'the', 'of', 'and', 'or', 'to', 'in', 'on'}
        qw = set(query_norm.split()) - stop
        sw = set(show_norm.split()) - stop
        if qw and qw.issubset(sw):
            return True
        if sw and sw.issubset(qw):
            return True
        return False

    def _make_source(self, label, url, extra_tag=''):
        prefix = '[Bones Shows]'
        if extra_tag:
            prefix = f'[Bones Shows {extra_tag}]'
        return {
            'multi-part': False,
            'host': _host_from_url(url),
            'quality': _parse_quality(url),
            'label': f'{prefix} {label}',
            'title': f'{prefix} {label}',
            'rating': None,
            'views': None,
            'direct': True,
            'url': url,
            'magnet': '',
            'seeds': 9999,
            'size': '',
            'is_free_link': True,
            'source': 'Bones 2 Shows',
        }

    def search(self, query, media_type='movie', **kwargs):
        # Only makes sense for TV content
        if media_type not in ('tvshow', 'episode', 'show', 'series'):
            return []

        title = (kwargs.get('title') or query or '').strip()
        season = str(kwargs.get('season') or '').strip()
        episode = str(kwargs.get('episode') or '').strip()
        clean_title = re.sub(r'\s*\(?\d{4}\)?\s*$', '', title).strip()
        q_norm = _norm(clean_title)
        if not q_norm:
            return []

        index = _load_index()
        results = []

        for show in index['dirs']:
            if not self._match_show(q_norm, show['norm_title']):
                continue

            # Walk at most MAX_DIR_DEPTH levels of nested <dir> redirection
            candidate_links = [show['link']]
            for _depth in range(MAX_DIR_DEPTH):
                next_links = []
                episode_items = []
                for link in candidate_links:
                    node = _load_node(link)
                    episode_items.extend(node['items'])
                    for sub in node['dirs']:
                        if _season_matches(season, sub['title']):
                            next_links.append(sub['link'])
                if episode_items:
                    for it in episode_items:
                        for s_url in it['streams']:
                            if not _episode_matches(episode, it['title'], s_url):
                                continue
                            label = f'{show["title"]} - {it["title"]}'
                            results.append(self._make_source(label, s_url))
                    if results:
                        break
                if not next_links:
                    break
                candidate_links = next_links

        xbmc.log(
            f'TheChainsBonesShows: {len(results)} source(s) for '
            f'"{clean_title}" S{season}E{episode}',
            xbmc.LOGINFO,
        )
        return results
