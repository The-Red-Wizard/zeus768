# -*- coding: utf-8 -*-
"""
Enhanced Source Picker Dialog for Genesis
Features:
- Provider | Size | Quality Type (REMUX/WebRip/BluRay) | Resolution | Seeds
- Filterable by Quality, Type, or Provider
- Color-coded cached sources (green checkmark)
- HDR/codec detection (HDR10, Dolby Vision, HEVC, x265)
"""
import re
import xbmc
import xbmcgui

# Quality type patterns
QUALITY_TYPE_PATTERNS = {
    'REMUX': r'(?:remux|bdremux)',
    'BluRay': r'(?:bluray|blu-ray|bdrip|brrip)',
    'WEB-DL': r'(?:web-dl|webdl|web\.dl)',
    'WEBRip': r'(?:webrip|web-rip|web\.rip)',
    'HDRip': r'(?:hdrip|hd-rip)',
    'DVDRip': r'(?:dvdrip|dvd-rip)',
    'HDTV': r'(?:hdtv)',
    'CAM': r'(?:cam|camrip|hdcam|ts|telesync)',
    'SCR': r'(?:scr|screener|dvdscr)'
}

# Resolution patterns
RESOLUTION_PATTERNS = {
    '4K': r'(?:2160p|4k|uhd)',
    '1080p': r'(?:1080p|1080i|fhd)',
    '720p': r'(?:720p|hd)',
    '480p': r'(?:480p|sd)',
    '360p': r'(?:360p)'
}

# HDR/Video codec patterns
HDR_PATTERNS = {
    'DV': r'(?:dovi|dolby\.?vision|dv)',
    'HDR10+': r'(?:hdr10\+|hdr10plus)',
    'HDR10': r'(?:hdr10|hdr\.10)',
    'HDR': r'(?:hdr(?![0-9]))',
    'SDR': None  # Default if no HDR detected
}

CODEC_PATTERNS = {
    'HEVC': r'(?:hevc|h\.?265|x265)',
    'AVC': r'(?:avc|h\.?264|x264)',
    'AV1': r'(?:av1)',
    'VP9': r'(?:vp9)'
}

AUDIO_PATTERNS = {
    'Atmos': r'(?:atmos)',
    'TrueHD': r'(?:truehd|true-hd)',
    'DTS-HD': r'(?:dts-hd|dtshd|dts\.hd)',
    'DTS-X': r'(?:dts-x|dtsx)',
    'DTS': r'(?:dts(?!-|x))',
    'DD+': r'(?:ddp|dd\+|eac3|e-ac-3)',
    'DD': r'(?:dd[^p+]|ac3|ac-3)',
    'AAC': r'(?:aac)',
    'FLAC': r'(?:flac)'
}

# Quality priority (higher = better)
QUALITY_PRIORITY = {
    '4K': 100,
    '1080p': 80,
    '720p': 60,
    '480p': 40,
    '360p': 20
}

TYPE_PRIORITY = {
    'REMUX': 100,
    'BluRay': 90,
    'WEB-DL': 80,
    'WEBRip': 70,
    'HDRip': 60,
    'DVDRip': 50,
    'HDTV': 40,
    'SCR': 20,
    'CAM': 10
}


def detect_quality_type(title):
    """Detect quality type from title (REMUX, BluRay, WEBRip, etc.)"""
    title_lower = title.lower()
    for qtype, pattern in QUALITY_TYPE_PATTERNS.items():
        if re.search(pattern, title_lower):
            return qtype
    return 'Unknown'


def detect_resolution(title):
    """Detect resolution from title"""
    title_lower = title.lower()
    for res, pattern in RESOLUTION_PATTERNS.items():
        if re.search(pattern, title_lower):
            return res
    return 'SD'


def detect_hdr(title):
    """Detect HDR format from title"""
    title_lower = title.lower()
    for hdr_type, pattern in HDR_PATTERNS.items():
        if pattern and re.search(pattern, title_lower):
            return hdr_type
    return None


def detect_codec(title):
    """Detect video codec from title"""
    title_lower = title.lower()
    for codec, pattern in CODEC_PATTERNS.items():
        if re.search(pattern, title_lower):
            return codec
    return None


def detect_audio(title):
    """Detect audio format from title"""
    title_lower = title.lower()
    for audio, pattern in AUDIO_PATTERNS.items():
        if re.search(pattern, title_lower):
            return audio
    return None


def format_size(size_bytes):
    """Format size in human readable form"""
    if not size_bytes:
        return ''
    
    try:
        size_bytes = int(size_bytes)
    except (ValueError, TypeError):
        return str(size_bytes)
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def parse_size_from_title(title):
    """Try to extract file size from torrent title"""
    # Match patterns like "2.5 GB", "700 MB", "4.2GB"
    match = re.search(r'(\d+(?:\.\d+)?)\s*(gb|mb|tb)', title.lower())
    if match:
        size = float(match.group(1))
        unit = match.group(2)
        if unit == 'tb':
            return f"{size:.1f} TB"
        elif unit == 'gb':
            return f"{size:.1f} GB"
        elif unit == 'mb':
            return f"{size:.0f} MB"
    return ''


def build_source_label(source, is_cached=False):
    """Build a formatted label for source display"""
    title = source.get('title', 'Unknown')
    provider = source.get('source', 'Unknown')
    seeds = source.get('seeds', 0)
    is_free = source.get('is_free_link', False)
    
    # Detect attributes
    resolution = detect_resolution(title)
    quality_type = detect_quality_type(title)
    hdr = detect_hdr(title)
    codec = detect_codec(title)
    audio = detect_audio(title)
    
    # Get size
    size = source.get('size', '')
    if not size:
        size = parse_size_from_title(title)
    elif isinstance(size, (int, float)):
        size = format_size(size)
    
    # Build quality info string
    quality_parts = []
    
    # Resolution with color
    res_colors = {'4K': 'gold', '1080p': 'lime', '720p': 'yellow', '480p': 'orange', '360p': 'red'}
    res_color = res_colors.get(resolution, 'white')
    quality_parts.append(f"[COLOR {res_color}]{resolution}[/COLOR]")
    
    # Quality type
    if quality_type != 'Unknown':
        type_colors = {'REMUX': 'gold', 'BluRay': 'lime', 'WEB-DL': 'skyblue', 'WEBRip': 'skyblue'}
        type_color = type_colors.get(quality_type, 'white')
        quality_parts.append(f"[COLOR {type_color}]{quality_type}[/COLOR]")
    
    # HDR badge
    if hdr:
        hdr_colors = {'DV': 'magenta', 'HDR10+': 'gold', 'HDR10': 'orange', 'HDR': 'yellow'}
        hdr_color = hdr_colors.get(hdr, 'yellow')
        quality_parts.append(f"[COLOR {hdr_color}]{hdr}[/COLOR]")
    
    # Codec
    if codec:
        quality_parts.append(codec)
    
    # Audio
    if audio:
        audio_colors = {'Atmos': 'magenta', 'TrueHD': 'gold', 'DTS-HD': 'lime', 'DTS-X': 'lime'}
        audio_color = audio_colors.get(audio, 'white')
        quality_parts.append(f"[COLOR {audio_color}]{audio}[/COLOR]")
    
    quality_str = ' | '.join(quality_parts)
    
    # Build full label
    parts = []
    
    # Status indicator
    if is_free:
        parts.append('[COLOR magenta]*[/COLOR]')  # Free link indicator
    elif is_cached:
        parts.append('[COLOR lime][OK][/COLOR]')
    else:
        parts.append('[COLOR gray]○[/COLOR]')
    
    # Provider
    parts.append(f"[COLOR cyan]{provider}[/COLOR]")
    
    # Quality info
    parts.append(quality_str)
    
    # Size
    if size:
        parts.append(f"[COLOR silver]{size}[/COLOR]")
    
    # Seeds (only for torrents)
    if seeds > 0 and not is_free:
        seed_color = 'lime' if seeds > 50 else ('yellow' if seeds > 10 else 'orange')
        parts.append(f"[COLOR {seed_color}]↑{seeds}[/COLOR]")
    
    return ' '.join(parts)


def show_source_picker(sources, cached_hashes=None, title='', include_free_links=True):
    """
    Display enhanced source picker dialog
    
    Args:
        sources: List of source dicts with keys: title, magnet, seeds, quality, source, size
        cached_hashes: Set of cached info hashes (lowercase)
        title: Movie/show title for dialog header
        include_free_links: Whether to search and include free links
    
    Returns:
        Selected source dict or None if cancelled
    """
    # Search for free links if enabled
    free_sources = []
    if include_free_links and title:
        try:
            from resources.lib import free_links_scraper
            free_sources = free_links_scraper.search_free_links(title)
            if free_sources:
                xbmc.log(f'Source Picker: Found {len(free_sources)} free links for {title}', xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f'Source Picker: Free links error: {e}', xbmc.LOGWARNING)
    
    # Combine sources
    all_sources = list(sources) if sources else []
    all_sources.extend(free_sources)
    
    if not all_sources:
        xbmcgui.Dialog().notification('No Sources', 'No sources available', xbmcgui.NOTIFICATION_WARNING)
        return None
    
    cached_hashes = cached_hashes or set()
    
    # Enrich sources with parsed metadata
    enriched_sources = []
    for source in all_sources:
        src = source.copy()
        src['resolution'] = detect_resolution(src.get('title', ''))
        src['quality_type'] = detect_quality_type(src.get('title', ''))
        src['hdr'] = detect_hdr(src.get('title', ''))
        src['codec'] = detect_codec(src.get('title', ''))
        src['audio'] = detect_audio(src.get('title', ''))
        src['is_cached'] = src.get('hash', '').lower() in cached_hashes if src.get('hash') else False
        src['is_free_link'] = src.get('is_free_link', False)
        enriched_sources.append(src)
    
    # Sort: free links first (instant), then cached, then by quality score
    def sort_key(s):
        free_score = 0 if s.get('is_free_link') else 1
        cached_score = 0 if s['is_cached'] else 1
        res_score = QUALITY_PRIORITY.get(s['resolution'], 30)
        type_score = TYPE_PRIORITY.get(s['quality_type'], 30)
        hdr_score = 50 if s['hdr'] else 0
        seeds = s.get('seeds', 0)
        return (free_score, cached_score, -res_score, -type_score, -hdr_score, -seeds)
    
    enriched_sources.sort(key=sort_key)
    
    # Build dialog items
    items = []
    for src in enriched_sources:
        label = build_source_label(src, src['is_cached'])
        items.append(label)
    
    # Show filter options first
    filter_options = [
        '[B][COLOR skyblue]▶ Show All Sources[/COLOR][/B]',
        '[COLOR yellow]Filter: 4K Only[/COLOR]',
        '[COLOR yellow]Filter: 1080p Only[/COLOR]',
        '[COLOR yellow]Filter: 720p Only[/COLOR]',
        '[COLOR lime]Filter: Cached Only[/COLOR]',
        '[COLOR gold]Filter: REMUX Only[/COLOR]',
        '[COLOR skyblue]Filter: WEB-DL Only[/COLOR]',
        '[COLOR magenta]Filter: Free Links Only[/COLOR]'
    ]
    
    while True:
        # Show filter menu
        filter_choice = xbmcgui.Dialog().select(
            f'Source Picker: {title}',
            filter_options,
            useDetails=False
        )
        
        if filter_choice < 0:
            return None
        
        # Apply filter
        if filter_choice == 0:
            filtered = enriched_sources
        elif filter_choice == 1:  # 4K
            filtered = [s for s in enriched_sources if s['resolution'] == '4K']
        elif filter_choice == 2:  # 1080p
            filtered = [s for s in enriched_sources if s['resolution'] == '1080p']
        elif filter_choice == 3:  # 720p
            filtered = [s for s in enriched_sources if s['resolution'] == '720p']
        elif filter_choice == 4:  # Cached
            filtered = [s for s in enriched_sources if s['is_cached']]
        elif filter_choice == 5:  # REMUX
            filtered = [s for s in enriched_sources if s['quality_type'] == 'REMUX']
        elif filter_choice == 6:  # WEB-DL
            filtered = [s for s in enriched_sources if s['quality_type'] in ('WEB-DL', 'WEBRip')]
        elif filter_choice == 7:  # Free Links
            filtered = [s for s in enriched_sources if s.get('is_free_link')]
        else:
            filtered = enriched_sources
        
        if not filtered:
            xbmcgui.Dialog().notification('No Results', 'No sources match this filter', xbmcgui.NOTIFICATION_INFO)
            continue
        
        # Build filtered items
        filtered_items = []
        for src in filtered:
            label = build_source_label(src, src['is_cached'])
            filtered_items.append(label)
        
        # Add back option
        filtered_items.insert(0, '[B][COLOR gray]◀ Back to Filters[/COLOR][/B]')
        
        # Show sources
        cached_count = sum(1 for s in filtered if s['is_cached'])
        free_count = sum(1 for s in filtered if s.get('is_free_link'))
        header = f'Sources ({len(filtered)} total, {cached_count} cached, {free_count} free)'
        
        choice = xbmcgui.Dialog().select(header, filtered_items, useDetails=False)
        
        if choice < 0:
            return None
        elif choice == 0:
            # Go back to filters
            continue
        else:
            # Return selected source
            return filtered[choice - 1]


def show_source_picker_simple(sources, cached_hashes=None, title=''):
    """
    Simplified source picker without filter menu
    For cases where quick selection is preferred
    """
    if not sources:
        return None
    
    cached_hashes = cached_hashes or set()
    
    # Enrich and sort
    enriched = []
    for source in sources:
        src = source.copy()
        src['resolution'] = detect_resolution(src.get('title', ''))
        src['quality_type'] = detect_quality_type(src.get('title', ''))
        src['hdr'] = detect_hdr(src.get('title', ''))
        src['is_cached'] = src.get('hash', '').lower() in cached_hashes
        enriched.append(src)
    
    def sort_key(s):
        cached = 0 if s['is_cached'] else 1
        res = QUALITY_PRIORITY.get(s['resolution'], 30)
        qtype = TYPE_PRIORITY.get(s['quality_type'], 30)
        return (cached, -res, -qtype, -s.get('seeds', 0))
    
    enriched.sort(key=sort_key)
    
    # Build items
    items = []
    for src in enriched:
        label = build_source_label(src, src['is_cached'])
        items.append(label)
    
    cached_count = sum(1 for s in enriched if s['is_cached'])
    header = f'{title} - {len(enriched)} sources ({cached_count} cached)'
    
    choice = xbmcgui.Dialog().select(header, items, useDetails=False)
    
    if choice < 0:
        return None
    
    return enriched[choice]
