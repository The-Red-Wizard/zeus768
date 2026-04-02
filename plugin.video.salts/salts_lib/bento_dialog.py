"""
SALTS - Bento UI Source Selection Dialog
Custom WindowXMLDialog for visually rich source browsing.
"""
import xbmcgui
import xbmc
import os


# Quality -> badge color mapping (AARRGGBB)
QUALITY_COLORS = {
    '4K':    'FFD4AF37',  # Gold
    '2160p': 'FFD4AF37',
    '1080p': 'FF2E8B57',  # Sea green
    'HD':    'FF2E8B57',
    '720p':  'FF4682B4',  # Steel blue
    '480p':  'FF6A5ACD',  # Slate blue
    'SD':    'FF696969',  # Dim gray
}


class BentoSourceDialog(xbmcgui.WindowXMLDialog):
    """Bento-style source selection dialog"""
    
    PANEL_ID = 6000
    HEADER_ID = 100
    SUMMARY_ID = 200
    
    def __init__(self, *args, **kwargs):
        self.sources = kwargs.get('sources', [])
        self.title = kwargs.get('title', 'Sources')
        self.selected_index = -1
        super().__init__(*args)
    
    def onInit(self):
        """Called when the dialog is initialized"""
        # Set header
        header_label = self.getControl(self.HEADER_ID)
        header_label.setLabel(f'SALTS - {self.title}')
        
        # Build quality summary
        quality_counts = {}
        cached_count = 0
        free_count = 0
        for s in self.sources:
            q = s.get('quality', 'SD')
            quality_counts[q] = quality_counts.get(q, 0) + 1
            if s.get('cached'):
                cached_count += 1
            if s.get('direct'):
                free_count += 1
        
        q_parts = []
        for q in ['4K', '2160p', '1080p', 'HD', '720p', '480p', 'SD']:
            if q in quality_counts:
                q_parts.append(f'{q}: {quality_counts[q]}')
        q_str = ' | '.join(q_parts) if q_parts else 'Mixed'
        
        summary = f'{len(self.sources)} sources'
        if cached_count:
            summary += f' ({cached_count} cached)'
        if free_count:
            summary += f' ({free_count} free)'
        summary += f'  [{q_str}]'
        
        summary_label = self.getControl(self.SUMMARY_ID)
        summary_label.setLabel(summary)
        
        # Populate the panel
        panel = self.getControl(self.PANEL_ID)
        panel.reset()
        
        for source in self.sources:
            li = xbmcgui.ListItem(source.get('title', 'Unknown'))
            
            quality = source.get('quality', 'SD')
            scraper = source.get('scraper', 'Unknown')
            seeds = source.get('seeds', 0)
            size = source.get('size', '')
            is_cached = source.get('cached', False)
            is_free = source.get('direct', False)
            
            # Quality badge color
            badge_color = QUALITY_COLORS.get(quality, 'FF696969')
            li.setProperty('badge_color', badge_color)
            li.setProperty('quality', quality)
            li.setProperty('scraper', scraper)
            
            # Tag (Cached / Free / empty)
            if is_cached:
                li.setProperty('tag', 'CACHED')
                li.setProperty('tag_color', 'FF00FF7F')  # Spring green
            elif is_free:
                li.setProperty('tag', 'FREE')
                li.setProperty('tag_color', 'FFFFA500')  # Orange
            else:
                li.setProperty('tag', '')
                li.setProperty('tag_color', 'FF555555')
            
            # Seeds
            if seeds and not is_free:
                li.setProperty('seeds', f'Seeds: {seeds}')
            else:
                li.setProperty('seeds', '')
            
            # Size
            li.setProperty('size', str(size) if size else '')
            
            # Provider info line
            info_parts = []
            if is_cached:
                info_parts.append('Instant via Debrid')
            elif is_free:
                info_parts.append('Free Stream')
            if source.get('magnet'):
                info_parts.append('Torrent')
            elif source.get('url'):
                info_parts.append('Direct Link')
            li.setProperty('provider_info', ' | '.join(info_parts))
            
            panel.addItem(li)
        
        self.setFocusId(self.PANEL_ID)
    
    def onClick(self, controlId):
        """Handle click events"""
        if controlId == self.PANEL_ID:
            panel = self.getControl(self.PANEL_ID)
            self.selected_index = panel.getSelectedPosition()
            self.close()
    
    def onAction(self, action):
        """Handle key/remote actions"""
        action_id = action.getId()
        # ACTION_PREVIOUS_MENU = 10, ACTION_NAV_BACK = 92
        if action_id in (10, 92):
            self.selected_index = -1
            self.close()


def show_bento_source_dialog(sources, title='Source Selection'):
    """Show the Bento source dialog and return the selected source index, or -1 if cancelled.
    
    Falls back to standard Kodi select dialog if skin XML is not available.
    """
    try:
        import xbmcaddon
        import xbmcvfs
        addon = xbmcaddon.Addon()
        addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
        skin_path = os.path.join(addon_path, 'resources', 'skins', 'Default', '1080i')
        
        if not os.path.exists(os.path.join(skin_path, 'SourceSelectDialog.xml')):
            raise FileNotFoundError('Skin XML not found')
        
        dialog = BentoSourceDialog(
            'SourceSelectDialog.xml', addon_path, 'Default', '1080i',
            sources=sources, title=title
        )
        dialog.doModal()
        selected = dialog.selected_index
        del dialog
        return selected
        
    except Exception as e:
        xbmc.log(f'SALTS BentoDialog fallback: {e}', xbmc.LOGDEBUG)
        # Fallback to standard select dialog
        return _fallback_select(sources, title)


def _fallback_select(sources, title):
    """Fallback: standard Kodi select dialog"""
    display_list = []
    for source in sources:
        quality = source.get('quality', 'SD')
        scraper = source.get('scraper', 'Unknown')
        seeds = source.get('seeds', 0)
        size = source.get('size', '')
        is_cached = source.get('cached', False)
        is_free = source.get('direct', False)
        
        parts = [f'[{quality}]']
        if is_cached:
            parts.append('[CACHED]')
        if is_free:
            parts.append('[FREE]')
        parts.append(f'[{scraper}]')
        if seeds and not is_free:
            parts.append(f'Seeds: {seeds}')
        if size:
            parts.append(str(size))
        
        label = ' '.join(parts)
        
        if is_cached:
            label = f'[COLOR limegreen]{label}[/COLOR]'
        elif is_free:
            label = f'[COLOR orange]{label}[/COLOR]'
        elif quality in ['4K', '2160p']:
            label = f'[COLOR gold]{label}[/COLOR]'
        elif quality in ['1080p', 'HD']:
            label = f'[COLOR lime]{label}[/COLOR]'
        elif quality == '720p':
            label = f'[COLOR cyan]{label}[/COLOR]'
        
        display_list.append(label)
    
    return xbmcgui.Dialog().select(f'SALTS: {title}', display_list)
