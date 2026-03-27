import requests
import re
import json
from bs4 import BeautifulSoup

BASE_URL = "https://fullfightreplays.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': BASE_URL
}

def get_soup(url):
    """Get BeautifulSoup object from URL"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def make_absolute_url(url):
    """Convert relative URL to absolute"""
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
    """Normalize video URLs for playback"""
    if not url:
        return url
    # Handle protocol-relative URLs
    if url.startswith('//'):
        return 'https:' + url
    return url

def get_categories():
    """Scrape all categories from the website"""
    soup = get_soup(BASE_URL)
    if not soup:
        return []
    
    categories = []
    seen_titles = set()
    
    # Find categories from fight listings (short_cat links)
    for cat_div in soup.find_all('div', class_='short_cat'):
        link = cat_div.find('a', href=True)
        if link:
            url = make_absolute_url(link['href'])
            title = link.text.strip()
            if title not in seen_titles and title:
                seen_titles.add(title)
                # Generate category slug for image matching
                slug = title.lower().replace(' ', '_').replace('-', '_')
                categories.append({
                    'title': title,
                    'url': url,
                    'slug': slug
                })
    
    # Also check for known categories
    known_categories = [
        {'title': 'UFC', 'url': f'{BASE_URL}/ufc', 'slug': 'ufc'},
        {'title': 'MMA', 'url': f'{BASE_URL}/mma', 'slug': 'mma'},
        {'title': 'Boxing', 'url': f'{BASE_URL}/boxing', 'slug': 'boxing'},
        {'title': 'Kickboxing', 'url': f'{BASE_URL}/kickboxing', 'slug': 'kickboxing'},
        {'title': 'K-1', 'url': f'{BASE_URL}/k-1', 'slug': 'k1'},
        {'title': 'Bellator', 'url': f'{BASE_URL}/bellator', 'slug': 'bellator'},
        {'title': 'ONE Championship', 'url': f'{BASE_URL}/one-championship', 'slug': 'one_championship'},
        {'title': 'PFL', 'url': f'{BASE_URL}/pfl', 'slug': 'pfl'},
        {'title': 'BKFC', 'url': f'{BASE_URL}/bkfc', 'slug': 'bkfc'},
        {'title': 'Cage Warriors', 'url': f'{BASE_URL}/cage-warriors', 'slug': 'cage_warriors'},
    ]
    
    for cat in known_categories:
        if cat['title'] not in seen_titles:
            seen_titles.add(cat['title'])
            categories.append(cat)
    
    # Sort alphabetically
    categories.sort(key=lambda x: x['title'])
    
    return categories

def get_fights(url, page=1):
    """Get fights from a category or search URL with pagination"""
    # Handle pagination
    if page > 1:
        if '?' in url:
            paginated_url = f"{url}&page{page}"
        else:
            paginated_url = f"{url}?page{page}"
    else:
        paginated_url = url
    
    soup = get_soup(paginated_url)
    fights = []
    next_page = None
    
    if not soup:
        return fights, next_page
    
    # Find all fight entries in allEntries div
    all_entries = soup.find('div', id='allEntries')
    if all_entries:
        items = all_entries.find_all('div', class_='short_item')
    else:
        items = soup.find_all('div', class_='short_item')
    
    for item in items:
        try:
            # Get title
            title_elem = item.find('h3')
            if not title_elem:
                continue
            link_elem = title_elem.find('a', href=True)
            if not link_elem:
                continue
            
            title = link_elem.text.strip()
            fight_url = make_absolute_url(link_elem['href'])
            
            # Get thumbnail image
            poster = item.find('div', class_='poster')
            img_url = ''
            if poster:
                img = poster.find('img')
                if img and img.get('src'):
                    img_url = make_absolute_url(img['src'])
            
            # Get category
            cat_div = item.find('div', class_='short_cat')
            category = ''
            if cat_div:
                cat_link = cat_div.find('a')
                if cat_link:
                    category = cat_link.text.strip()
            
            # Get views
            views = '0'
            views_span = item.find('div', class_='short_icn')
            if views_span:
                span = views_span.find('span')
                if span:
                    views = span.text.strip()
            
            # Get description
            desc_div = item.find('div', class_='short_descr')
            description = ''
            if desc_div:
                p = desc_div.find('p')
                if p:
                    description = p.text.strip()
            
            # Get rating
            rating = '0'
            stars = item.find('div', class_='stars')
            if stars:
                ul = stars.find('ul')
                if ul and ul.get('title'):
                    rating_match = re.search(r'Rating:\s*([\d.]+)', ul['title'])
                    if rating_match:
                        rating = rating_match.group(1)
            
            fights.append({
                'title': title,
                'url': fight_url,
                'icon': img_url,
                'category': category,
                'views': views,
                'description': description,
                'rating': rating
            })
        except Exception as e:
            print(f"Error parsing fight item: {e}")
            continue
    
    # Check for next page
    paging = soup.find('div', class_='paging-wrapper-bottom')
    if paging:
        next_link = paging.find('a', class_='swchItem-next')
        if next_link and next_link.get('href'):
            next_page = page + 1
    
    return fights, next_page

def get_fight_details(url):
    """Get detailed information about a specific fight"""
    url = make_absolute_url(url)
    soup = get_soup(url)
    if not soup:
        return None
    
    details = {
        'title': '',
        'image': '',
        'description': '',
        'category': '',
        'views': '0',
        'rating': '0',
        'links': []
    }
    
    # Get title
    title_elem = soup.find('h1', class_='h_title')
    if title_elem:
        details['title'] = title_elem.text.strip()
    
    # Get main image
    full_img = soup.find('div', class_='full_img')
    if full_img:
        img = full_img.find('img')
        if img and img.get('src'):
            details['image'] = make_absolute_url(img['src'])
    
    # Get category from breadcrumb
    speedbar = soup.find('div', class_='speedbar')
    if speedbar:
        links = speedbar.find_all('a', href=True)
        for link in links:
            if link['href'] != 'http://fullfightreplays.com/' and link['href'] != BASE_URL:
                details['category'] = link.text.strip()
                break
    
    # Get views and rating
    full_info = soup.find('div', class_='full_info')
    if full_info:
        views_span = full_info.find('span', class_='e-reads')
        if views_span:
            value = views_span.find('span', class_='ed-value')
            if value:
                details['views'] = value.text.strip()
        
        rating_span = soup.find('span', id=re.compile(r'entRating\d+'))
        if rating_span:
            details['rating'] = rating_span.text.strip()
    
    # Get description from fullstory
    fullstory = soup.find('div', class_='fullstory')
    if fullstory:
        # Get description paragraphs at the end
        for p in fullstory.find_all('p'):
            text = p.get_text(strip=True)
            if text and 'Watch' in text and 'Full Fight' in text:
                details['description'] = text
                break
    
    return details

def get_video_links(url):
    """Extract all video links from a fight page"""
    url = make_absolute_url(url)
    soup = get_soup(url)
    links = []
    
    if not soup:
        return links
    
    fullstory = soup.find('div', class_='fullstory')
    if not fullstory:
        return links
    
    # Group links by section
    sections = {}  # {'Main Event': [links], 'Full Event': [links], etc.}
    
    # Extract actual iframes
    for iframe in fullstory.find_all('iframe'):
        src = iframe.get('src', '')
        if src and is_video_link(src):
            src = normalize_video_url(src)
            section = find_section_context(iframe)
            host = get_host_name(src)
            
            # Normalize section names
            section = normalize_section_name(section)
            
            if section not in sections:
                sections[section] = []
            sections[section].append({
                'url': src,
                'host': host,
                'type': 'embed'
            })
    
    # Extract embedded iframes (stored as divs with data-original-tag="iframe") - fallback
    for iframe_div in fullstory.find_all('div', attrs={'data-original-tag': 'iframe'}):
        src = iframe_div.get('src', '')
        if src and is_video_link(src):
            src = normalize_video_url(src)
            section = find_section_context(iframe_div)
            host = get_host_name(src)
            
            section = normalize_section_name(section)
            
            if section not in sections:
                sections[section] = []
            sections[section].append({
                'url': src,
                'host': host,
                'type': 'embed'
            })
    
    # Extract direct anchor links (like dailymotion parts)
    for a in fullstory.find_all('a', href=True):
        href = a['href']
        if is_video_link(href):
            span = a.find('span')
            link_text = span.get_text(strip=True) if span else a.get_text(strip=True)
            section = find_section_context(a)
            host = get_host_name(href)
            
            section = normalize_section_name(section)
            
            # For parts (like Dailymotion), include part info
            part_info = ''
            if link_text and re.match(r'^Part\s*\d+$', link_text, re.IGNORECASE):
                part_info = link_text
            
            if section not in sections:
                sections[section] = []
            sections[section].append({
                'url': href,
                'host': host,
                'type': 'direct',
                'part': part_info
            })
    
    # Build final links list with proper numbering and formatting
    for section_name, section_links in sections.items():
        # Remove duplicates within section
        seen_urls = set()
        unique_links = []
        for link in section_links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                unique_links.append(link)
        
        # Number the servers
        for i, link in enumerate(unique_links):
            server_num = i + 1
            host = link['host']
            part = link.get('part', '')
            
            # Format label with section and server number
            if part:
                label = f"{section_name} - {part} [{host}]"
            else:
                label = f"{section_name} Server #{server_num} [{host}]"
            
            links.append({
                'label': label,
                'url': link['url'],
                'type': link['type'],
                'server_num': server_num,
                'host': host,
                'section': section_name
            })
    
    return links

def normalize_section_name(section):
    """Normalize section names for cleaner display"""
    if not section or section == 'Video':
        return 'Main Event'
    
    section_lower = section.lower()
    
    # Clean up common patterns
    if 'main card' in section_lower or 'main event' in section_lower:
        return 'Main Event'
    elif 'prelim' in section_lower:
        return 'Prelims'
    elif 'full event' in section_lower or 'full fight' in section_lower:
        return 'Full Event'
    elif 'early prelim' in section_lower:
        return 'Early Prelims'
    
    # Remove server mentions from section name (will be added separately)
    section = re.sub(r'server\s*#?\d*\s*', '', section, flags=re.IGNORECASE)
    section = re.sub(r'\(dm\)', '', section, flags=re.IGNORECASE)
    section = section.strip()
    
    if not section:
        return 'Main Event'
    
    return section

def find_section_context(element):
    """Find the section context (Server #1, Main Card, Prelims, etc.) for an element"""
    section = "Main Event"
    
    # Go up to find video-responsive or similar parent, then look for preceding headers
    current = element
    search_count = 0
    
    while current and search_count < 15:
        # Check previous siblings at current level
        prev = current.find_previous_sibling()
        while prev:
            if prev.name in ['p', 'div', 'span', 'strong']:
                text = prev.get_text(strip=True)
                if text:
                    text_lower = text.lower()
                    # Check for section indicators
                    if 'full event' in text_lower:
                        return 'Full Event'
                    elif 'main event' in text_lower or 'main card' in text_lower:
                        return 'Main Event'
                    elif 'prelim' in text_lower and 'early' in text_lower:
                        return 'Early Prelims'
                    elif 'prelim' in text_lower:
                        return 'Prelims'
                    elif 'server' in text_lower and 'full' not in text_lower and 'main' not in text_lower:
                        # Just "Server #2" without section - continue looking
                        pass
            prev = prev.find_previous_sibling()
        
        # Move up to parent
        current = current.parent
        search_count += 1
    
    return section

def is_video_link(url):
    """Check if URL is a video link that can be resolved"""
    video_hosts = [
        'ok.ru', 'dailymotion', 'geo.dailymotion',
        'vidoza', 'upstream', 'mixdrop', 'dood', 'voe', 'streamtape',
        'bysesukior', 'vibuxer', 'f75s',
        'youtube', 'youtu.be',
        'vimeo', 'streamable',
        'mp4upload', 'vidlox', 'fembed',
        'huntrexus', 'okcdn'
    ]
    return any(host in url.lower() for host in video_hosts)

def get_host_name(url):
    """Get the host name from URL"""
    url_lower = url.lower()
    
    if 'ok.ru' in url_lower or 'okcdn' in url_lower:
        return 'OK.ru'
    elif 'dailymotion' in url_lower:
        return 'Dailymotion'
    elif 'bysesukior' in url_lower or 'f75s' in url_lower:
        return 'Byse'
    elif 'vibuxer' in url_lower:
        return 'Vibuxer'
    elif 'vidoza' in url_lower:
        return 'Vidoza'
    elif 'mixdrop' in url_lower:
        return 'MixDrop'
    elif 'streamtape' in url_lower:
        return 'StreamTape'
    elif 'dood' in url_lower:
        return 'DoodStream'
    elif 'voe' in url_lower:
        return 'Voe'
    elif 'upstream' in url_lower:
        return 'Upstream'
    else:
        return 'Video'

def get_link_label(url, section=''):
    """Generate a readable label for a video link"""
    host = get_host_name(url)
    
    if section and section != 'Video':
        return f"{section} [{host}]"
    return f"Watch [{host}]"

def search_fights(query):
    """Search for fights"""
    # Use the correct search URL format for the site
    search_url = f"{BASE_URL}/search/?q={query.replace(' ', '+')}"
    soup = get_soup(search_url)
    fights = []
    
    if not soup:
        return fights, None
    
    # Search results use statvidp class structure
    items = soup.find_all('div', class_='statvidp')
    
    for item in items:
        try:
            # Get title from eTitle div
            title_div = item.find('div', class_='eTitle')
            if not title_div:
                continue
            
            link_elem = title_div.find('a', href=True)
            if not link_elem:
                continue
            
            title = link_elem.get_text(strip=True)
            fight_url = make_absolute_url(link_elem['href'])
            
            # Get thumbnail image from fhkds54sa div
            img_div = item.find('div', class_='fhkds54sa')
            img_url = ''
            if img_div:
                img = img_div.find('img')
                if img and img.get('src'):
                    img_url = make_absolute_url(img['src'])
            
            fights.append({
                'title': title,
                'url': fight_url,
                'icon': img_url,
                'category': '',
                'description': '',
                'views': '0',
                'rating': '0'
            })
        except Exception as e:
            print(f"Error parsing search result: {e}")
            continue
    
    return fights, None
