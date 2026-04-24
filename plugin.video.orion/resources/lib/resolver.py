# -*- coding: utf-8 -*-
"""
Link Resolver for Orion v3.3 - FIXED VERSION
Based on SALTS resolver implementation for reliable link resolution
Resolves magnet links via debrid services or ResolveURL

FIXES APPLIED:
- Direct debrid service calls (SALTS-style)
- Better fallback logic
- Improved logging and error handling
"""

import xbmcaddon
import xbmc
import xbmcgui


def get_addon():
    """Get fresh addon instance to ensure latest settings"""
    return xbmcaddon.Addon()


def get_active_debrid():
    """Get the active debrid service based on settings - SALTS-style direct checks"""
    from resources.lib import debrid
    
    addon = get_addon()
    priority = int(addon.getSetting('debrid_priority') or 0)
    
    services = [
        ('rd', debrid.RealDebrid),
        ('pm', debrid.Premiumize),
        ('ad', debrid.AllDebrid),
        ('tb', debrid.TorBox)
    ]
    
    # Reorder based on priority
    if priority == 1:
        services = [services[1], services[0], services[2], services[3]]
    elif priority == 2:
        services = [services[2], services[0], services[1], services[3]]
    elif priority == 3:
        services = [services[3], services[0], services[1], services[2]]
    
    # Debug: Log current settings state
    xbmc.log(f"Resolver: Checking debrid services. Priority: {priority}", xbmc.LOGINFO)
    for key, cls in services:
        enabled = addon.getSetting(f'{key}_enabled')
        token = addon.getSetting(f'{key}_token')
        xbmc.log(f"  {key}: enabled={enabled}, token={'SET' if token else 'EMPTY'}", xbmc.LOGINFO)
    
    # Find first enabled and authorized service
    for key, cls in services:
        enabled_setting = addon.getSetting(f'{key}_enabled')
        
        if enabled_setting == 'true':
            service = cls()
            if service.is_authorized():
                xbmc.log(f"Resolver: Found active service: {key}", xbmc.LOGINFO)
                return service
            else:
                xbmc.log(f"Resolver: {key} is enabled but not authorized", xbmc.LOGWARNING)
    
    # Fallback: try any authorized service (even if not explicitly enabled)
    # This fixes the bug where authorization works but enabled flag isn't set
    xbmc.log("Resolver: No enabled+authorized service found, checking for any authorized service...", xbmc.LOGINFO)
    
    for key, cls in services:
        service = cls()
        if service.is_authorized():
            # Auto-enable the service since it's authorized
            addon.setSetting(f'{key}_enabled', 'true')
            xbmc.log(f"Resolver: Auto-enabled {key} debrid service (was authorized but not enabled)", xbmc.LOGINFO)
            return service
    
    xbmc.log("Resolver: No authorized debrid service found at all", xbmc.LOGWARNING)
    return None


def resolve_with_resolveurl(url):
    """Try to resolve URL using Zeus Resolvers first, then ResolveURL addon"""
    # Zeus Resolvers first (Streamtape / DDownloads, no debrid required)
    try:
        from resources.lib.zeus_hook import try_zeus
        zeus_url = try_zeus(url)
        if zeus_url:
            xbmc.log(f"Zeus Resolvers resolved: {zeus_url[:50]}...", xbmc.LOGINFO)
            return zeus_url
    except Exception as e:
        xbmc.log(f"Zeus hook error: {e}", xbmc.LOGWARNING)

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


def resolve_with_resolveurl_rd(magnet):
    """Try to resolve magnet using ResolveURL's Real-Debrid integration"""
    try:
        import resolveurl
        
        # Check if ResolveURL has RealDebrid configured
        rd_resolver = None
        for resolver in resolveurl.relevant_resolvers(order_matters=True):
            if 'realdebrid' in resolver.__class__.__name__.lower() or \
               'real_debrid' in resolver.__class__.__name__.lower():
                rd_resolver = resolver
                break
        
        if rd_resolver and hasattr(rd_resolver, 'get_media_url'):
            resolved = rd_resolver.get_media_url('', magnet)
            if resolved:
                xbmc.log(f"ResolveURL RD resolved magnet", xbmc.LOGINFO)
                return resolved
    except ImportError:
        pass
    except Exception as e:
        xbmc.log(f"ResolveURL RD magnet error: {e}", xbmc.LOGWARNING)
    
    return None


def resolve_magnet(magnet, progress=None):
    """Resolve magnet link to stream URL - SALTS-style direct service calls"""
    from resources.lib import debrid
    
    addon = get_addon()
    use_resolveurl = addon.getSetting('use_resolveurl') == 'true'
    stream_url = None
    
    # SALTS-style: Try each debrid service directly
    
    # Try Real-Debrid
    if addon.getSetting('rd_enabled') == 'true':
        rd = debrid.RealDebrid()
        if rd.is_authorized():
            xbmc.log("Resolver: Trying Real-Debrid...", xbmc.LOGINFO)
            if progress:
                progress.update(10, 'Resolving with Real-Debrid...')
            stream_url = rd.resolve_magnet(magnet, progress)
            if stream_url:
                xbmc.log("Resolver: Successfully resolved via Real-Debrid", xbmc.LOGINFO)
                return stream_url
    
    # Try Premiumize
    if addon.getSetting('pm_enabled') == 'true':
        pm = debrid.Premiumize()
        if pm.is_authorized():
            xbmc.log("Resolver: Trying Premiumize...", xbmc.LOGINFO)
            if progress:
                progress.update(30, 'Resolving with Premiumize...')
            stream_url = pm.resolve_magnet(magnet, progress)
            if stream_url:
                xbmc.log("Resolver: Successfully resolved via Premiumize", xbmc.LOGINFO)
                return stream_url
    
    # Try AllDebrid
    if addon.getSetting('ad_enabled') == 'true':
        ad = debrid.AllDebrid()
        if ad.is_authorized():
            xbmc.log("Resolver: Trying AllDebrid...", xbmc.LOGINFO)
            if progress:
                progress.update(50, 'Resolving with AllDebrid...')
            stream_url = ad.resolve_magnet(magnet, progress)
            if stream_url:
                xbmc.log("Resolver: Successfully resolved via AllDebrid", xbmc.LOGINFO)
                return stream_url
    
    # Try TorBox
    if addon.getSetting('tb_enabled') == 'true':
        tb = debrid.TorBox()
        if tb.is_authorized():
            xbmc.log("Resolver: Trying TorBox...", xbmc.LOGINFO)
            if progress:
                progress.update(70, 'Resolving with TorBox...')
            stream_url = tb.resolve_magnet(magnet, progress)
            if stream_url:
                xbmc.log("Resolver: Successfully resolved via TorBox", xbmc.LOGINFO)
                return stream_url
    
    # Fallback: Try any authorized service (auto-enable)
    xbmc.log("Resolver: No enabled service resolved, trying fallback...", xbmc.LOGINFO)
    
    for key, cls, name in [
        ('rd', debrid.RealDebrid, 'Real-Debrid'),
        ('pm', debrid.Premiumize, 'Premiumize'),
        ('ad', debrid.AllDebrid, 'AllDebrid'),
        ('tb', debrid.TorBox, 'TorBox')
    ]:
        if addon.getSetting(f'{key}_enabled') != 'true':
            service = cls()
            if service.is_authorized():
                xbmc.log(f"Resolver: Found authorized but disabled service: {name}, auto-enabling...", xbmc.LOGINFO)
                addon.setSetting(f'{key}_enabled', 'true')
                
                if progress:
                    progress.update(80, f'Resolving with {name}...')
                
                stream_url = service.resolve_magnet(magnet, progress)
                if stream_url:
                    xbmc.log(f"Resolver: Successfully resolved via {name} (auto-enabled)", xbmc.LOGINFO)
                    return stream_url
    
    # Try ResolveURL as last resort
    if use_resolveurl:
        xbmc.log("Resolver: Trying ResolveURL fallback...", xbmc.LOGINFO)
        if progress:
            progress.update(90, 'Trying ResolveURL...')
        stream_url = resolve_with_resolveurl_rd(magnet)
        if stream_url:
            return stream_url
        stream_url = resolve_with_resolveurl(magnet)
        if stream_url:
            return stream_url
    
    # Nothing worked - show helpful error
    xbmc.log("Resolver: All debrid resolution attempts failed", xbmc.LOGERROR)
    
    # Log detailed status for debugging
    xbmc.log("=== DEBRID STATUS DEBUG ===", xbmc.LOGINFO)
    for key in ['rd', 'pm', 'ad', 'tb']:
        token = addon.getSetting(f'{key}_token')
        enabled = addon.getSetting(f'{key}_enabled')
        xbmc.log(f"  {key}: token={'[SET]' if token else '[EMPTY]'}, enabled='{enabled}'", xbmc.LOGINFO)
    xbmc.log("=== END DEBUG ===", xbmc.LOGINFO)
    
    # Show helpful error to user
    xbmcgui.Dialog().ok(
        'Orion - No Debrid Service',
        'No debrid service could resolve this link.\n\n'
        'Go to [COLOR cyan]Settings[/COLOR] and authorize one of:\n'
        '[COLOR lime]Real-Debrid | Premiumize | AllDebrid | TorBox[/COLOR]\n\n'
        '[COLOR yellow]TIP: After authorizing, try restarting Kodi if links still don\'t resolve.[/COLOR]'
    )
    return None


def resolve_url(url, progress=None):
    """Resolve a URL (non-magnet) using debrid or ResolveURL"""
    addon = get_addon()
    use_resolveurl = addon.getSetting('use_resolveurl') == 'true'
    
    # Check if URL is already a direct stream
    if any(ext in url.lower() for ext in ['.m3u8', '.mp4', '.mkv', '.avi']):
        xbmc.log(f"Resolver: URL is already direct stream: {url[:50]}...", xbmc.LOGINFO)
        return url
    
    # First try ResolveURL for direct links
    if use_resolveurl:
        if progress:
            progress.update(20, 'Trying ResolveURL...')
        resolved = resolve_with_resolveurl(url)
        if resolved:
            return resolved
    
    # Try debrid unrestrict
    from resources.lib import debrid
    
    # Real-Debrid unrestrict
    if addon.getSetting('rd_enabled') == 'true':
        rd = debrid.RealDebrid()
        if rd.is_authorized():
            if progress:
                progress.update(50, 'Trying Real-Debrid...')
            try:
                resolved = rd.unrestrict_link(url)
                if resolved:
                    xbmc.log("Resolver: Unrestricted via Real-Debrid", xbmc.LOGINFO)
                    return resolved
            except Exception as e:
                xbmc.log(f"Debrid unrestrict error: {e}", xbmc.LOGWARNING)
    
    # Fallback to raw URL
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
