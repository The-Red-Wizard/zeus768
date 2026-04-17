# -*- coding: utf-8 -*-
"""
Orion Link Picker - Fullscreen custom dialog for selecting streaming links
POV-style skin with movie info panel and sortable link list
"""

import xbmc
import xbmcgui
import xbmcaddon
import os
import re

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = ADDON.getAddonInfo('icon')

# Action codes
ACTION_SELECT_ITEM = 7
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_CONTEXT_MENU = 117

# Control IDs
LIST_LINKS = 9000
BTN_SEARCH = 9010
BTN_SORT = 9011
BTN_FILTER = 9012
BTN_BACK = 9013
BTN_PLAY = 9014


class LinkPickerDialog(xbmcgui.WindowXMLDialog):
    """
    Fullscreen link picker dialog with POV-style interface.
    Shows movie poster, info, and sortable list of streaming links.
    """
    
    def __init__(self, *args, **kwargs):
        self.sources = kwargs.get('sources', [])
        self.title = kwargs.get('title', '')
        self.year = kwargs.get('year', '')
        self.poster = kwargs.get('poster', '')
        self.backdrop = kwargs.get('backdrop', '')
        self.plot = kwargs.get('plot', '')
        self.media_info = kwargs.get('media_info', '')
        self.tmdb_id = kwargs.get('tmdb_id', '')
        self.media_type = kwargs.get('media_type', 'movie')
        self.original_params = kwargs.get('original_params', {})
        
        self.selected_source = None
        self.sort_order = 'default'  # default, quality, size, seeds, cached
        self.filter_type = 'all'  # all, cached, 4k, 1080p, 720p
        self.filtered_sources = list(self.sources)
        
        super(LinkPickerDialog, self).__init__(*args)
    
    def onInit(self):
        """Initialize the dialog and populate controls"""
        # Set window properties for media info
        self.setProperty('media_title', f"{self.title} ({self.year})" if self.year else self.title)
        self.setProperty('poster', self.poster or ADDON_ICON)
        self.setProperty('plot', self.plot or 'No description available.')
        self.setProperty('media_info', self.media_info)
        self.setProperty('links_count', str(len(self.sources)))
        
        # Populate the links list
        self._populate_links()
        
        # Focus on the list
        self.setFocusId(LIST_LINKS)
    
    def _populate_links(self):
        """Populate the links list control"""
        list_control = self.getControl(LIST_LINKS)
        list_control.reset()
        
        for idx, source in enumerate(self.filtered_sources):
            li = xbmcgui.ListItem(label=self._get_link_label(source))
            
            # Set properties for the skin
            quality = source.get('quality', 'Unknown')
            li.setProperty('quality', quality)
            li.setProperty('quality_color', self._get_quality_color(quality))
            li.setProperty('source', source.get('source', 'Unknown'))
            li.setProperty('size', source.get('size', '--'))
            li.setProperty('size2', source.get('size2', ''))
            li.setProperty('seeds', str(source.get('seeds', 0)))
            li.setProperty('provider', source.get('provider', ''))
            li.setProperty('subs', source.get('subs', ''))
            
            # Extract Season/Episode info from name or source properties
            season_episode = self._extract_season_episode(source)
            li.setProperty('season_episode', season_episode)
            
            # Cached status
            is_cached = source.get('cached', False)
            li.setProperty('cached', 'CACHED' if is_cached else '')
            li.setProperty('cached_color', 'FF00FF00' if is_cached else 'FF808080')
            
            # Star icon for favorites/cached
            if is_cached:
                li.setProperty('star_icon', '[COLOR FFFFCC00]*[/COLOR]')
            else:
                li.setProperty('star_icon', '[COLOR FF404060]-[/COLOR]')
            
            # Store index for selection
            li.setProperty('source_index', str(idx))
            
            list_control.addItem(li)
        
        # Update count
        self.setProperty('links_count', str(len(self.filtered_sources)))
    
    def _get_link_label(self, source):
        """Create display label for a source - no truncation, let skin handle scrolling"""
        name = source.get('name', 'Unknown')
        return name
    
    def _extract_season_episode(self, source):
        """Extract season/episode info from source name (e.g., S01E05)"""
        name = source.get('name', '')
        
        # Check if source already has season/episode properties
        season = source.get('season', '')
        episode = source.get('episode', '')
        if season and episode:
            return f"S{str(season).zfill(2)}E{str(episode).zfill(2)}"
        
        # Try to extract from name using common patterns
        # Patterns: S01E05, S01.E05, s01e05, Season 1 Episode 5, 1x05
        patterns = [
            r'[Ss](\d{1,2})[Ee](\d{1,2})',           # S01E05
            r'[Ss](\d{1,2})\.?[Ee](\d{1,2})',        # S01.E05
            r'[Ss]eason\s*(\d{1,2})\s*[Ee]pisode\s*(\d{1,2})',  # Season 1 Episode 5
            r'(\d{1,2})[xX](\d{1,2})',               # 1x05
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                season = match.group(1).zfill(2)
                episode = match.group(2).zfill(2)
                return f"S{season}E{episode}"
        
        return ''
    
    def _get_quality_color(self, quality):
        """Get color code for quality badge"""
        quality = quality.upper()
        if '4K' in quality or '2160' in quality:
            return 'FFFFCC00'  # Gold
        elif '1080' in quality:
            return 'FF00CC00'  # Green
        elif '720' in quality:
            return 'FF00CCCC'  # Cyan
        elif 'SD' in quality or '480' in quality:
            return 'FF808080'  # Gray
        else:
            return 'FF505050'  # Dark gray
    
    def _sort_sources(self, sort_by):
        """Sort sources by specified criteria"""
        quality_order = {'4K': 0, '2160p': 0, '1080p': 1, '720p': 2, 'SD': 3, '480p': 3, 'Unknown': 4}
        
        if sort_by == 'quality':
            self.filtered_sources.sort(key=lambda x: (
                quality_order.get(x.get('quality', 'Unknown'), 4),
                -x.get('seeds', 0)
            ))
        elif sort_by == 'size':
            self.filtered_sources.sort(key=lambda x: self._parse_size(x.get('size', '0')), reverse=True)
        elif sort_by == 'seeds':
            self.filtered_sources.sort(key=lambda x: -x.get('seeds', 0))
        elif sort_by == 'cached':
            self.filtered_sources.sort(key=lambda x: (
                0 if x.get('cached') else 1,
                quality_order.get(x.get('quality', 'Unknown'), 4),
                -x.get('seeds', 0)
            ))
        else:  # default
            self.filtered_sources.sort(key=lambda x: (
                0 if x.get('cached') else 1,
                quality_order.get(x.get('quality', 'Unknown'), 4),
                -x.get('seeds', 0)
            ))
        
        self.sort_order = sort_by
        self._populate_links()
    
    def _filter_sources(self, filter_type):
        """Filter sources by type"""
        if filter_type == 'all':
            self.filtered_sources = list(self.sources)
        elif filter_type == 'cached':
            self.filtered_sources = [s for s in self.sources if s.get('cached')]
        elif filter_type == '4k':
            self.filtered_sources = [s for s in self.sources if '4K' in s.get('quality', '').upper() or '2160' in s.get('quality', '')]
        elif filter_type == '1080p':
            self.filtered_sources = [s for s in self.sources if '1080' in s.get('quality', '')]
        elif filter_type == '720p':
            self.filtered_sources = [s for s in self.sources if '720' in s.get('quality', '')]
        
        self.filter_type = filter_type
        # Re-apply current sort
        self._sort_sources(self.sort_order)
    
    def _parse_size(self, size_str):
        """Parse size string to bytes for sorting"""
        if not size_str:
            return 0
        
        try:
            size_str = size_str.upper().replace(' ', '')
            if 'GB' in size_str:
                return float(re.sub(r'[^0-9.]', '', size_str)) * 1024 * 1024 * 1024
            elif 'MB' in size_str:
                return float(re.sub(r'[^0-9.]', '', size_str)) * 1024 * 1024
            elif 'KB' in size_str:
                return float(re.sub(r'[^0-9.]', '', size_str)) * 1024
            else:
                return float(re.sub(r'[^0-9.]', '', size_str))
        except:
            return 0
    
    def _show_sort_menu(self):
        """Show sort options dialog"""
        options = [
            ('Default (Cached + Quality)', 'default'),
            ('Quality (Highest first)', 'quality'),
            ('Size (Largest first)', 'size'),
            ('Seeds (Most first)', 'seeds'),
            ('Cached Only First', 'cached'),
        ]
        
        labels = [opt[0] for opt in options]
        selection = xbmcgui.Dialog().select('Sort By', labels)
        
        if selection >= 0:
            self._sort_sources(options[selection][1])
    
    def _show_filter_menu(self):
        """Show filter options dialog"""
        options = [
            ('All Sources', 'all'),
            ('Cached Only', 'cached'),
            ('4K Only', '4k'),
            ('1080p Only', '1080p'),
            ('720p Only', '720p'),
        ]
        
        labels = [opt[0] for opt in options]
        selection = xbmcgui.Dialog().select('Filter', labels)
        
        if selection >= 0:
            self._filter_sources(options[selection][1])
    
    def _show_search_dialog(self):
        """Show search keyboard to filter by name"""
        keyboard = xbmc.Keyboard('', 'Search Links')
        keyboard.doModal()
        
        if keyboard.isConfirmed():
            query = keyboard.getText().strip().lower()
            if query:
                self.filtered_sources = [
                    s for s in self.sources 
                    if query in s.get('name', '').lower() or
                       query in s.get('source', '').lower()
                ]
                self._sort_sources(self.sort_order)
            else:
                self._filter_sources('all')
    
    def onClick(self, controlId):
        """Handle button clicks"""
        if controlId == LIST_LINKS:
            # Get selected item
            list_control = self.getControl(LIST_LINKS)
            selected = list_control.getSelectedItem()
            if selected:
                idx = int(selected.getProperty('source_index'))
                self.selected_source = self.filtered_sources[idx]
                self.close()
        
        elif controlId == BTN_SEARCH:
            self._show_search_dialog()
        
        elif controlId == BTN_SORT:
            self._show_sort_menu()
        
        elif controlId == BTN_FILTER:
            self._show_filter_menu()
        
        elif controlId == BTN_BACK:
            self.close()
        
        elif controlId == BTN_PLAY:
            # Play currently highlighted item
            list_control = self.getControl(LIST_LINKS)
            selected = list_control.getSelectedItem()
            if selected:
                idx = int(selected.getProperty('source_index'))
                self.selected_source = self.filtered_sources[idx]
                self.close()
    
    def onAction(self, action):
        """Handle keyboard/remote actions"""
        action_id = action.getId()
        
        if action_id in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            self.close()
        
        elif action_id == ACTION_SELECT_ITEM:
            # Handle item selection from list
            focus_id = self.getFocusId()
            if focus_id == LIST_LINKS:
                self.onClick(LIST_LINKS)
        
        elif action_id == ACTION_CONTEXT_MENU:
            # Show context menu with sort/filter options
            options = ['Sort By...', 'Filter...', 'Search...']
            selection = xbmcgui.Dialog().select('Options', options)
            
            if selection == 0:
                self._show_sort_menu()
            elif selection == 1:
                self._show_filter_menu()
            elif selection == 2:
                self._show_search_dialog()
    
    def get_selected(self):
        """Return the selected source"""
        return self.selected_source


def show_link_picker(sources, title, year='', poster='', backdrop='', plot='', 
                     media_info='', tmdb_id='', media_type='movie', original_params=None):
    """
    Show the fullscreen link picker dialog.
    
    Args:
        sources: List of source dictionaries
        title: Media title
        year: Release year
        poster: Poster image URL
        backdrop: Backdrop image URL
        plot: Media description/plot
        media_info: Additional info string (runtime, genre, etc.)
        tmdb_id: TMDB ID for the media
        media_type: 'movie' or 'tv'
        original_params: Original parameters dict for playback
    
    Returns:
        Selected source dict or None if cancelled
    """
    # Get the skin path
    skin_path = os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', '1080i')
    
    dialog = LinkPickerDialog(
        'LinkPickerDialog.xml',
        ADDON_PATH,
        'Default',
        '1080i',
        sources=sources,
        title=title,
        year=year,
        poster=poster,
        backdrop=backdrop,
        plot=plot,
        media_info=media_info,
        tmdb_id=tmdb_id,
        media_type=media_type,
        original_params=original_params
    )
    
    dialog.doModal()
    selected = dialog.get_selected()
    del dialog
    
    return selected
