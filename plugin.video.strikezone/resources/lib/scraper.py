import re
import json
import ssl
import urllib.request
import urllib.parse
import urllib.error

BASE_URL = "https://fullfightreplays.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': BASE_URL
}

_ctx = ssl._create_unverified_context()


def _fetch(url):
    """Fetch URL content as string using native urllib."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=_ctx, timeout=20) as resp:
            data = resp.read()
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                return data.decode('latin-1')
    except Exception as e:
        return None


def make_absolute_url(url):
    if not url:
        return url
    if url.startswith('http'):
        return url
    if url.startswith('//'):
        return 'https:' + url
    if url.startswith('/'):
        return BASE_URL + url
    return BASE_URL + '/' + url


def normalize_video_url(url):
    if not url:
        return url
    if url.startswith('//'):
        return 'https:' + url
    return url


def _strip_tags(html):
    """Remove HTML tags, return plain text."""
    return re.sub(r'<[^>]+>', '', html).strip()


def get_categories():
    """Extract categories from the homepage fight listings."""
    html = _fetch(BASE_URL)
    if not html:
        return []

    categories = []
    seen = set()

    # Extract categories from short_cat links in fight listings
    for m in re.finditer(r'<div[^>]*class="short_cat"[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html, re.S):
        url = m.group(1).strip()
        title = m.group(2).strip()
        if title and title not in seen:
            seen.add(title)
            slug = title.lower().replace(' ', '_').replace('-', '_')
            categories.append({'title': title, 'url': url, 'slug': slug})

    # Add known categories that may not be on the current front page
    known = [
        ('UFC', 'https://fullfightreplays.com/ufc'),
        ('MMA', 'https://fullfightreplays.com/mma'),
        ('Boxing', 'https://fullfightreplays.com/boxing'),
        ('Kickboxing', 'https://fullfightreplays.com/kickboxing'),
        ('K-1', 'https://fullfightreplays.com/k-1'),
        ('Bellator', 'https://fullfightreplays.com/bellator'),
        ('ONE Championship', 'https://fullfightreplays.com/one-championship'),
        ('PFL', 'https://fullfightreplays.com/pfl'),
        ('BKFC', 'https://fullfightreplays.com/bkfc'),
        ('Cage Warriors', 'https://fullfightreplays.com/cage-warriors'),
        ('Other Tournaments', 'https://fullfightreplays.com/other-tournaments'),
    ]
    for title, url in known:
        if title not in seen:
            seen.add(title)
            slug = title.lower().replace(' ', '_').replace('-', '_')
            categories.append({'title': title, 'url': url, 'slug': slug})

    categories.sort(key=lambda x: x['title'])
    return categories


def _parse_fight_items(html):
    """Parse fight items from HTML. Works for homepage, category pages, and search."""
    fights = []
    if not html:
        return fights

    # Match each entryID block — the actual structure is:
    # <div id="entryIDxxx"><div class="short_item block_elem">...</div></div></div>
    for entry_m in re.finditer(r'<div\s+id="entryID\d+">(.*?)</div>\s*</div>\s*</div>', html, re.S):
        block = entry_m.group(1)
        try:
            # Title + URL from <h3><a href="...">Title</a></h3>
            title_link = re.search(r'<h3>\s*<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', block, re.S)
            if not title_link:
                continue
            fight_url = title_link.group(1).strip()
            title = title_link.group(2).strip()

            # Thumbnail from <div class="poster"><a ...><img src="..." ...></a></div>
            img_m = re.search(r'<div[^>]*class="poster"[^>]*>.*?<img[^>]+src="([^"]+)"', block, re.S)
            img_url = img_m.group(1).strip() if img_m else ''

            # Category from <div class="short_cat"><a ...>Category</a></div>
            cat_m = re.search(r'class="short_cat"[^>]*>\s*<a[^>]*>([^<]+)</a>', block, re.S)
            category = cat_m.group(1).strip() if cat_m else ''

            # Views from <div class="short_icn"><span><i ...></i>NNN</span></div>
            views_m = re.search(r'class="short_icn"[^>]*>\s*<span>.*?</i>(\d+)', block, re.S)
            views = views_m.group(1) if views_m else '0'

            # Description from <div class="short_descr"><p>...</p></div>
            desc_m = re.search(r'class="short_descr"[^>]*>\s*<p>(.*?)</p>', block, re.S)
            description = _strip_tags(desc_m.group(1)) if desc_m else ''

            # Rating from title="Rating: X.X/Y"
            rating_m = re.search(r'title="Rating:\s*([\d.]+)', block)
            rating = rating_m.group(1) if rating_m else '0'

            fights.append({
                'title': title, 'url': fight_url, 'icon': img_url,
                'category': category, 'views': views,
                'description': description, 'rating': rating
            })
        except Exception:
            continue

    return fights


def get_fights(url, page=1):
    """Get fights from a category or homepage URL."""
    if page > 1:
        # Pagination format: ?pageN (no equals sign, per actual site HTML)
        sep = '&' if '?' in url else '?'
        paginated_url = f"{url}{sep}page{page}"
    else:
        paginated_url = url

    html = _fetch(paginated_url)
    fights = _parse_fight_items(html)

    # Check for next page link
    next_page = None
    if html and re.search(r'class="swchItem\s+swchItem-next"', html):
        next_page = page + 1

    return fights, next_page


def get_fight_details(url):
    """Get details for a specific fight page."""
    url = make_absolute_url(url)
    html = _fetch(url)
    if not html:
        return None

    details = {
        'title': '', 'image': '', 'description': '',
        'category': '', 'views': '0', 'rating': '0', 'links': []
    }

    # Title from <h1 class="h_title">
    t = re.search(r'<h1[^>]*class="h_title"[^>]*>(.*?)</h1>', html, re.S)
    if t:
        details['title'] = _strip_tags(t.group(1))

    # Image from fullstory or poster
    img = re.search(r'<div[^>]*class="full_img[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"', html, re.S)
    if not img:
        img = re.search(r'<div[^>]*class="poster"[^>]*>.*?<img[^>]+src="([^"]+)"', html, re.S)
    if img:
        details['image'] = make_absolute_url(img.group(1))

    # Category from speedbar breadcrumb
    sb = re.search(r'<div[^>]*class="speedbar"[^>]*>(.*?)</div>', html, re.S)
    if sb:
        links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', sb.group(1))
        for href, text in links:
            if href.rstrip('/') != BASE_URL and text.strip().lower() != 'main':
                details['category'] = text.strip()
                break

    # Views
    v = re.search(r'class="ed-value"[^>]*>(\d+)', html)
    if v:
        details['views'] = v.group(1)

    # Rating
    r = re.search(r'title="Rating:\s*([\d.]+)', html)
    if r:
        details['rating'] = r.group(1)

    # Description from fullstory
    fs = re.search(r'<div[^>]*class="fullstory"[^>]*>(.*?)</div>\s*(?:<!--|<div[^>]*class="paging)', html, re.S)
    if fs:
        for p in re.finditer(r'<p>(.*?)</p>', fs.group(1), re.S):
            text = _strip_tags(p.group(1))
            if text and len(text) > 10:
                details['description'] = text
                break

    return details


def get_video_links(url):
    """Extract video embed links from a fight page."""
    url = make_absolute_url(url)
    html = _fetch(url)
    links = []

    if not html:
        return links

    # Find fullstory content div
    fs = re.search(r'<div[^>]*class="fullstory"[^>]*>(.*?)(?:</div>\s*<!--|<div[^>]*class="paging)', html, re.S)
    if not fs:
        return links

    content = fs.group(1)
    seen_urls = set()

    # Extract iframes
    for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', content, re.I):
        src = normalize_video_url(m.group(1))
        if is_video_link(src) and src not in seen_urls:
            seen_urls.add(src)
            host = get_host_name(src)
            section = _find_section(content, m.start())
            links.append({'label': f'{section} [{host}]', 'url': src, 'type': 'embed',
                          'server_num': len(links) + 1, 'host': host, 'section': section})

    # Extract data-original-tag="iframe" divs (lazy loaded)
    for m in re.finditer(r'data-original-tag="iframe"[^>]+src=["\']([^"\']+)["\']', content, re.I):
        src = normalize_video_url(m.group(1))
        if is_video_link(src) and src not in seen_urls:
            seen_urls.add(src)
            host = get_host_name(src)
            section = _find_section(content, m.start())
            links.append({'label': f'{section} [{host}]', 'url': src, 'type': 'embed',
                          'server_num': len(links) + 1, 'host': host, 'section': section})

    # Extract direct links
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', content, re.S):
        href = m.group(1)
        if is_video_link(href) and href not in seen_urls:
            seen_urls.add(href)
            host = get_host_name(href)
            section = _find_section(content, m.start())
            links.append({'label': f'{section} [{host}]', 'url': href, 'type': 'direct',
                          'server_num': len(links) + 1, 'host': host, 'section': section})

    return links


def _find_section(content, pos):
    """Find section name by looking backwards from position."""
    preceding = content[:pos]
    patterns = [
        (r'(?i)full\s*event', 'Full Event'),
        (r'(?i)main\s*(?:event|card)', 'Main Event'),
        (r'(?i)early\s*prelim', 'Early Prelims'),
        (r'(?i)prelim', 'Prelims'),
    ]
    for tag_m in reversed(list(re.finditer(r'<(?:strong|b|p|h\d)[^>]*>(.*?)</(?:strong|b|p|h\d)>', preceding, re.S))):
        text = _strip_tags(tag_m.group(1)).lower()
        if not text:
            continue
        for pat, name in patterns:
            if re.search(pat, text):
                return name
    return 'Main Event'


def is_video_link(url):
    if not url:
        return False
    hosts = [
        'ok.ru', 'dailymotion', 'geo.dailymotion',
        'vidoza', 'upstream', 'mixdrop', 'dood', 'voe', 'streamtape',
        'bysesukior', 'vibuxer', 'f75s', 'huntrexus',
        'youtube', 'youtu.be', 'vimeo', 'streamable',
        'mp4upload', 'vidlox', 'fembed', 'okcdn'
    ]
    return any(h in url.lower() for h in hosts)


def get_host_name(url):
    u = url.lower()
    if 'ok.ru' in u or 'okcdn' in u: return 'OK.ru'
    if 'dailymotion' in u: return 'Dailymotion'
    if 'bysesukior' in u or 'f75s' in u: return 'Byse'
    if 'vibuxer' in u: return 'Vibuxer'
    if 'vidoza' in u: return 'Vidoza'
    if 'mixdrop' in u: return 'MixDrop'
    if 'streamtape' in u: return 'StreamTape'
    if 'dood' in u: return 'DoodStream'
    if 'voe' in u: return 'Voe'
    if 'upstream' in u: return 'Upstream'
    if 'huntrexus' in u: return 'Huntrexus'
    return 'Video'


def get_link_label(url, section=''):
    host = get_host_name(url)
    if section and section != 'Video':
        return f"{section} [{host}]"
    return f"Watch [{host}]"


def search_fights(query):
    """Search for fights."""
    search_url = f"{BASE_URL}/search/?q={urllib.parse.quote_plus(query)}"
    html = _fetch(search_url)
    if not html:
        return [], None

    # Search results use the same entryID structure
    fights = _parse_fight_items(html)

    # If entryID parsing fails, try search-specific classes
    if not fights:
        for item_m in re.finditer(r'class="statvidp"[^>]*>(.*?)</div>\s*</div>', html, re.S):
            block = item_m.group(1)
            try:
                title_link = re.search(r'class="eTitle"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', block, re.S)
                if not title_link:
                    continue
                fight_url = title_link.group(1).strip()
                title = title_link.group(2).strip()

                img_m = re.search(r'<img[^>]+src="([^"]+)"', block, re.S)
                img_url = img_m.group(1).strip() if img_m else ''

                fights.append({
                    'title': title, 'url': fight_url, 'icon': img_url,
                    'category': '', 'description': '', 'views': '0', 'rating': '0'
                })
            except Exception:
                continue

    return fights, None
