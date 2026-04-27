"""
SALTS - Bento-Style Source Selection Dialog
Uses Kodi's native Dialog().select() with rich color-coded formatting.
Works reliably across all Kodi skins.
"""
import xbmcgui


# Quality -> color mapping
QUALITY_COLORS = {
    '4K':    'FFD4AF37',  # Gold
    '2160p': 'FFD4AF37',
    '1080p': 'FF00CC66',  # Green
    'HD':    'FF00CC66',
    '720p':  'FF4499DD',  # Blue
    '480p':  'FF9977CC',  # Purple
    'SD':    'FF999999',  # Gray
}


def show_bento_source_dialog(sources, title='Source Selection'):
    """Show a rich color-coded source dialog using native Kodi select.
    
    Returns selected index, or -1 if cancelled.
    """
    if not sources:
        return -1
    
    # Build quality summary for header
    quality_counts = {}
    cached_count = 0
    free_count = 0
    for s in sources:
        q = s.get('quality', 'SD')
        quality_counts[q] = quality_counts.get(q, 0) + 1
        if s.get('cached'):
            cached_count += 1
        if s.get('direct'):
            free_count += 1
    
    q_parts = []
    for q in ['4K', '2160p', '1080p', 'HD', '720p', '480p', 'SD']:
        if q in quality_counts:
            q_parts.append(f'{q}:{quality_counts[q]}')
    q_str = '  '.join(q_parts)
    
    header = f'SALTS: {len(sources)} sources'
    if cached_count:
        header += f'  |  {cached_count} cached'
    if free_count:
        header += f'  |  {free_count} free'
    header += f'  [{q_str}]'
    
    # Build formatted display list
    display_list = []
    
    for source in sources:
        quality = source.get('quality', 'SD')
        scraper = source.get('scraper', '?')
        seeds = source.get('seeds', 0)
        size = source.get('size', '')
        is_cached = source.get('cached', False)
        is_free = source.get('direct', False)
        source_title = source.get('title', '')
        
        q_color = QUALITY_COLORS.get(quality, 'FF999999')
        
        # Build label with Kodi markup
        parts = []
        
        # Quality badge
        parts.append(f'[COLOR {q_color}][B]{quality}[/B][/COLOR]')
        
        # Cached / Free tag
        if is_cached:
            parts.append('[B]CACHED[/B]')
        elif is_free:
            parts.append('[B]FREE[/B]')
        
        # Scraper name
        parts.append(f'{scraper}')
        
        # Seeds (torrent only)
        if seeds and not is_free:
            if seeds >= 100:
                parts.append(f'S:{seeds}')
            elif seeds >= 10:
                parts.append(f'S:{seeds}')
            else:
                parts.append(f'S:{seeds}')
        
        # Size
        if size:
            parts.append(f'{size}')
        
        # Source title (truncated)
        if source_title:
            clean_title = source_title[:60]
            parts.append(f'{clean_title}')
        
        label = '  |  '.join(parts)
        display_list.append(label)
    
    return xbmcgui.Dialog().select(header, display_list)
