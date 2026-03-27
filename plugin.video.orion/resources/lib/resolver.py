# -*- coding: utf-8 -*-
"""
Link Resolver for Orion v3.0
Resolves magnet links via debrid services or ResolveURL
"""

import xbmcaddon
import xbmc

ADDON = xbmcaddon.Addon()

def get_active_debrid():
    """Get the active debrid service based on settings"""
    from resources.lib import debrid
    
    priority = int(ADDON.getSetting('debrid_priority') or 0)
    
    services = [
        ('rd', debrid.RealDebrid),
        ('pm', debrid.Premiumize),
        ('ad', debrid.AllDebrid)
    ]
    
    # Reorder based on priority
    if priority == 1:
        services = [services[1], services[0], services[2]]
    elif priority == 2:
        services = [services[2], services[0], services[1]]
    
    # Find first enabled and authorized service
    for key, cls in services:
        if ADDON.getSetting(f'{key}_enabled') == 'true':
            service = cls()
            if service.is_authorized():
                return service
    
    # Fallback: try any authorized service
    for key, cls in services:
        service = cls()
        if service.is_authorized():
            return service
    
    return None

def resolve_with_resolveurl(url):
    """Try to resolve URL using ResolveURL addon"""
    try:
        import resolveurl
        
        if resolveurl.HostedMediaFile(url).valid_url():
            resolved = resolveurl.HostedMediaFile(url).resolve()
            if resolved:
                xbmc.log(f"ResolveURL resolved: {resolved[:50]}...", xbmc.LOGINFO)
                return resolved
    except ImportError:
        xbmc.log("ResolveURL not installed", xbmc.LOGWARNING)
    except Exception as e:
        xbmc.log(f"ResolveURL error: {e}", xbmc.LOGWARNING)
    
    return None

def resolve_magnet(magnet, progress=None):
    """Resolve magnet link to stream URL"""
    from resources.lib import debrid
    
    # Check if we should try ResolveURL first for certain links
    use_resolveurl = ADDON.getSetting('use_resolveurl') == 'true'
    
    service = get_active_debrid()
    
    if not service:
        xbmc.log("No authorized debrid service found", xbmc.LOGERROR)
        
        # Try ResolveURL as fallback if enabled
        if use_resolveurl:
            resolved = resolve_with_resolveurl(magnet)
            if resolved:
                return resolved
        
        return None
    
    service_name = service.__class__.__name__
    xbmc.log(f"Resolving via {service_name}", xbmc.LOGINFO)
    
    if progress:
        progress.update(5, f'Resolving via {service_name}...')
    
    stream_url = service.resolve_magnet(magnet, progress)
    
    # If debrid resolution fails and ResolveURL is enabled, try that
    if not stream_url and use_resolveurl:
        if progress:
            progress.update(80, 'Trying ResolveURL...')
        stream_url = resolve_with_resolveurl(magnet)
    
    return stream_url

def resolve_url(url, progress=None):
    """Resolve a URL (non-magnet) using debrid or ResolveURL"""
    use_resolveurl = ADDON.getSetting('use_resolveurl') == 'true'
    
    # First try ResolveURL for direct links
    if use_resolveurl:
        if progress:
            progress.update(20, 'Trying ResolveURL...')
        resolved = resolve_with_resolveurl(url)
        if resolved:
            return resolved
    
    # Try debrid unrestrict
    service = get_active_debrid()
    if service:
        if progress:
            progress.update(50, f'Trying {service.__class__.__name__}...')
        
        try:
            if hasattr(service, 'unrestrict_link'):
                resolved = service.unrestrict_link(url)
                if resolved:
                    return resolved
        except Exception as e:
            xbmc.log(f"Debrid unrestrict error: {e}", xbmc.LOGWARNING)
    
    return url

def filter_by_quality(sources, preferred_quality):
    """Filter sources by preferred quality"""
    quality_map = {
        '0': ['4K', '2160p'],
        '1': ['1080p'],
        '2': ['720p'],
        '3': ['SD', '480p']
    }
    
    preferred = quality_map.get(str(preferred_quality), [])
    
    if not preferred:
        return sources
    
    filtered = [s for s in sources if s.get('quality') in preferred]
    
    return filtered if filtered else sources

def auto_select_source(sources):
    """Auto-select best source based on quality and seeds"""
    if not sources:
        return None
    
    quality_order = {'4K': 0, '2160p': 0, '1080p': 1, '720p': 2, 'SD': 3, '480p': 3, 'Unknown': 4}
    
    sorted_sources = sorted(
        sources,
        key=lambda x: (quality_order.get(x.get('quality', 'Unknown'), 4), -x.get('seeds', 0))
    )
    
    return sorted_sources[0] if sorted_sources else None
