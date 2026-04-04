import re
import json
import ssl
import urllib.request
import urllib.parse
import urllib.error

BASE_URL = "https://fullfightreplays.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': BASE_URL
}

_ctx = ssl._create_unverified_context()


def _fetch(url):
    """Fetch URL content as string using native urllib."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=_ctx, timeout=15) as resp:
            data = resp.read()
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                return data.decode('latin-1')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
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
    html = _fetch(BASE_URL)
    if not html:
        return []

    categories = []
    seen = set()

    # Parse short_cat divs
    for m in re.finditer(r'<div[^>]*class="short_cat"[^>]*>(.*?)</div>', html, re.S):
        link = re.search(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', m.group(1))
        if link:
            url = make_absolute_url(link.group(1))
            title = link.group(2).strip()
            if title and title not in seen:
                seen.add(title)
                slug = title.lower().replace(' ', '_').replace('-', '_')
                categories.append({'title': title, 'url': url, 'slug': slug})

    known = [
        ('UFC', 'ufc'), ('MMA', 'mma'), ('Boxing', 'boxing'),
        ('Kickboxing', 'kickboxing'), ('K-1', 'k1'), ('Bellator', 'bellator'),
        ('ONE Championship', 'one_championship'), ('PFL', 'pfl'),
        ('BKFC', 'bkfc'), ('Cage Warriors', 'cage_warriors'),
    ]
    for title, slug in known:
        if title not in seen:
            seen.add(title)
            categories.append({'title': title, 'url': f'{BASE_URL}/{slug.replace("_", "-")}', 'slug': slug})

    categories.sort(key=lambda x: x['title'])
    return categories


def get_fights(url, page=1):
    if page > 1:
        paginated_url = f"{url}{'&' if '?' in url else '?'}page{page}"
    else:
        paginated_url = url

    html = _fetch(paginated_url)
    fights = []
    next_page = None

    if not html:
        return fights, next_page

    # Find allEntries section or fall back to full page
    entries_match = re.search(r'<div[^>]*id="allEntries"[^>]*>(.*)', html, re.S)
    search_html = entries_match.group(1) if entries_match else html

    # Parse short_item divs
    for item_m in re.finditer(r'<div[^>]*class="short_item"[^>]*>(.*?)</div>\s*</div>\s*</div>', search_html, re.S):
        block = item_m.group(1)
        try:
            # Title + URL from h3 > a
            title_link = re.search(r'<h3[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', block, re.S)
            if not title_link:
                continue
            fight_url = make_absolute_url(title_link.group(1))
            title = title_link.group(2).strip()

            # Thumbnail
            img_m = re.search(r'<div[^>]*class="poster"[^>]*>.*?<img[^>]+src="([^"]+)"', block, re.S)
            img_url = make_absolute_url(img_m.group(1)) if img_m else ''

            # Category
            cat_m = re.search(r'<div[^>]*class="short_cat"[^>]*>.*?<a[^>]*>([^<]+)</a>', block, re.S)
            category = cat_m.group(1).strip() if cat_m else ''

            # Views
            views_m = re.search(r'<div[^>]*class="short_icn"[^>]*>.*?<span>(\d+)</span>', block, re.S)
            views = views_m.group(1) if views_m else '0'

            # Description
            desc_m = re.search(r'<div[^>]*class="short_descr"[^>]*>.*?<p>(.*?)</p>', block, re.S)
            description = _strip_tags(desc_m.group(1)) if desc_m else ''

            # Rating
            rating_m = re.search(r'Rating:\s*([\d.]+)', block)
            rating = rating_m.group(1) if rating_m else '0'

            fights.append({
                'title': title, 'url': fight_url, 'icon': img_url,
                'category': category, 'views': views,
                'description': description, 'rating': rating
            })
        except Exception:
            continue

    # Check next page
    if re.search(r'class="swchItem-next"', html):
        next_page = page + 1

    return fights, next_page


def get_fight_details(url):
    url = make_absolute_url(url)
    html = _fetch(url)
    if not html:
        return None

    details = {
        'title': '', 'image': '', 'description': '',
        'category': '', 'views': '0', 'rating': '0', 'links': []
    }

    # Title
    t = re.search(r'<h1[^>]*class="h_title"[^>]*>(.*?)</h1>', html, re.S)
    if t:
        details['title'] = _strip_tags(t.group(1))

    # Image
    img = re.search(r'<div[^>]*class="full_img"[^>]*>.*?<img[^>]+src="([^"]+)"', html, re.S)
    if img:
        details['image'] = make_absolute_url(img.group(1))

    # Category from speedbar
    sb = re.search(r'<div[^>]*class="speedbar"[^>]*>(.*?)</div>', html, re.S)
    if sb:
        for link in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', sb.group(1)):
            href = link.group(1)
            if href not in ('http://fullfightreplays.com/', BASE_URL, BASE_URL + '/'):
                details['category'] = link.group(2).strip()
                break

    # Views
    v = re.search(r'class="ed-value"[^>]*>(\d+)', html)
    if v:
        details['views'] = v.group(1)

    # Rating
    r = re.search(r'id="entRating\d+"[^>]*>([\d.]+)', html)
    if r:
        details['rating'] = r.group(1)

    # Description
    fs = re.search(r'<div[^>]*class="fullstory"[^>]*>(.*?)</div>\s*<!--', html, re.S)
    if fs:
        for p in re.finditer(r'<p>(.*?)</p>', fs.group(1), re.S):
            text = _strip_tags(p.group(1))
            if 'Watch' in text and 'Full Fight' in text:
                details['description'] = text
                break

    return details


def get_video_links(url):
    url = make_absolute_url(url)
    html = _fetch(url)
    links = []

    if not html:
        return links

    # Find fullstory div
    fs = re.search(r'<div[^>]*class="fullstory"[^>]*>(.*?)(?:</div>\s*<!--|<div[^>]*class="paging)', html, re.S)
    if not fs:
        return links

    content = fs.group(1)
    sections = {}

    # Extract iframes
    for m in re.finditer(r'<iframe[^>]+src="([^"]+)"', content, re.I):
        src = normalize_video_url(m.group(1))
        if is_video_link(src):
            section = _find_section(content, m.start())
            host = get_host_name(src)
            section = normalize_section_name(section)
            sections.setdefault(section, []).append({'url': src, 'host': host, 'type': 'embed', 'part': ''})

    # Extract data-original-tag="iframe" divs
    for m in re.finditer(r'<div[^>]*data-original-tag="iframe"[^>]+src="([^"]+)"', content, re.I):
        src = normalize_video_url(m.group(1))
        if is_video_link(src):
            section = _find_section(content, m.start())
            host = get_host_name(src)
            section = normalize_section_name(section)
            sections.setdefault(section, []).append({'url': src, 'host': host, 'type': 'embed', 'part': ''})

    # Extract direct links
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', content, re.S):
        href = m.group(1)
        if is_video_link(href):
            link_text = _strip_tags(m.group(2))
            section = _find_section(content, m.start())
            host = get_host_name(href)
            section = normalize_section_name(section)
            part = link_text if re.match(r'^Part\s*\d+$', link_text, re.I) else ''
            sections.setdefault(section, []).append({'url': href, 'host': host, 'type': 'direct', 'part': part})

    # Build final list
    for section_name, section_links in sections.items():
        seen = set()
        unique = []
        for lnk in section_links:
            if lnk['url'] not in seen:
                seen.add(lnk['url'])
                unique.append(lnk)
        for i, lnk in enumerate(unique):
            part = lnk.get('part', '')
            if part:
                label = f"{section_name} - {part} [{lnk['host']}]"
            else:
                label = f"{section_name} Server #{i+1} [{lnk['host']}]"
            links.append({
                'label': label, 'url': lnk['url'], 'type': lnk['type'],
                'server_num': i + 1, 'host': lnk['host'], 'section': section_name
            })

    return links


def _find_section(content, pos):
    """Find section context by looking backwards from position for section headers."""
    preceding = content[:pos]
    # Look for section headers in reverse
    patterns = [
        (r'(?i)full\s*event', 'Full Event'),
        (r'(?i)main\s*(?:event|card)', 'Main Event'),
        (r'(?i)early\s*prelim', 'Early Prelims'),
        (r'(?i)prelim', 'Prelims'),
    ]
    # Search backwards through strong/p/div tags
    for tag_m in reversed(list(re.finditer(r'<(?:strong|p|div|span|h\d)[^>]*>(.*?)</(?:strong|p|div|span|h\d)>', preceding, re.S))):
        text = _strip_tags(tag_m.group(1)).lower()
        if not text:
            continue
        for pat, name in patterns:
            if re.search(pat, text):
                return name
    return 'Main Event'


def normalize_section_name(section):
    if not section or section == 'Video':
        return 'Main Event'
    s = section.lower()
    if 'main card' in s or 'main event' in s:
        return 'Main Event'
    elif 'early prelim' in s:
        return 'Early Prelims'
    elif 'prelim' in s:
        return 'Prelims'
    elif 'full event' in s or 'full fight' in s:
        return 'Full Event'
    section = re.sub(r'server\s*#?\d*\s*', '', section, flags=re.I).strip()
    return section or 'Main Event'


def is_video_link(url):
    hosts = [
        'ok.ru', 'dailymotion', 'geo.dailymotion',
        'vidoza', 'upstream', 'mixdrop', 'dood', 'voe', 'streamtape',
        'bysesukior', 'vibuxer', 'f75s',
        'youtube', 'youtu.be', 'vimeo', 'streamable',
        'mp4upload', 'vidlox', 'fembed', 'huntrexus', 'okcdn'
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
    return 'Video'


def get_link_label(url, section=''):
    host = get_host_name(url)
    if section and section != 'Video':
        return f"{section} [{host}]"
    return f"Watch [{host}]"


def search_fights(query):
    search_url = f"{BASE_URL}/search/?q={query.replace(' ', '+')}"
    html = _fetch(search_url)
    fights = []

    if not html:
        return fights, None

    for item_m in re.finditer(r'<div[^>]*class="statvidp"[^>]*>(.*?)</div>\s*</div>', html, re.S):
        block = item_m.group(1)
        try:
            title_link = re.search(r'class="eTitle"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', block, re.S)
            if not title_link:
                continue
            fight_url = make_absolute_url(title_link.group(1))
            title = title_link.group(2).strip()

            img_m = re.search(r'class="fhkds54sa"[^>]*>.*?<img[^>]+src="([^"]+)"', block, re.S)
            img_url = make_absolute_url(img_m.group(1)) if img_m else ''

            fights.append({
                'title': title, 'url': fight_url, 'icon': img_url,
                'category': '', 'description': '', 'views': '0', 'rating': '0'
            })
        except Exception:
            continue

    return fights, None
