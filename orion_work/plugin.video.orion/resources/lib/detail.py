# -*- coding: utf-8 -*-
"""
Orion Detail Dialog - Movie/TV Show details with Trailer and Play buttons
"""

import xbmc
import xbmcgui
import xbmcaddon
import os

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_FANART = ADDON.getAddonInfo('fanart')

# Action codes
ACTION_SELECT_ITEM = 7
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

# Control IDs
PLAY_BTN = 800
TRAILER_BTN = 801
FAVORITE_BTN = 802
CLOSE_BTN = 810


class DetailDialog(xbmcgui.WindowXMLDialog):
    """
    Detail dialog showing movie/TV show information
    with Play, Trailer, and Favorite buttons.
    """
    
    def __init__(self, *args, **kwargs):
        self.item_data = kwargs.get('item_data', {})
        self.media_type = kwargs.get('media_type', 'movie')
        
        self.selected_action = None
        self.trailer_key = None
        
        super(DetailDialog, self).__init__(*args)
    
    def onInit(self):
        """Initialize the dialog with item details"""
        # Fetch full details from TMDB
        self._load_details()
    
    def _load_details(self):
        """Load full item details from TMDB"""
        from .tmdb import (get_movie_details, get_tv_details, get_poster_url, 
                          get_backdrop_url, fetch_json)
        
        tmdb_id = self.item_data.get('id')
        if not tmdb_id:
            self._set_basic_info()
            return
        
        try:
            # Fetch full details
            if self.media_type == 'tv':
                details = get_tv_details(tmdb_id)
                title = details.get('name', self.item_data.get('title', ''))
                date_str = details.get('first_air_date', '')
                runtime = f"{details.get('episode_run_time', [0])[0] if details.get('episode_run_time') else 0} min/ep"
                status = details.get('status', '')
                seasons = str(details.get('number_of_seasons', ''))
            else:
                details = get_movie_details(tmdb_id)
                title = details.get('title', self.item_data.get('title', ''))
                date_str = details.get('release_date', '')
                runtime_mins = details.get('runtime', 0)
                runtime = f"{runtime_mins // 60}h {runtime_mins % 60}m" if runtime_mins else ''
                status = ''
                seasons = ''
            
            # Extract year
            year = date_str[:4] if date_str and len(date_str) >= 4 else ''
            
            # Get rating
            rating = details.get('vote_average', 0)
            votes = details.get('vote_count', 0)
            
            # Get genres as string
            genres = ', '.join([g['name'] for g in details.get('genres', [])[:4]])
            
            # Get images
            poster = get_poster_url(details.get('poster_path')) or self.item_data.get('poster', ADDON_ICON)
            backdrop = get_backdrop_url(details.get('backdrop_path')) or self.item_data.get('backdrop', ADDON_FANART)
            
            # Get cast (top 5)
            credits = fetch_json(f"/{self.media_type}/{tmdb_id}/credits")
            cast_list = credits.get('cast', [])[:5]
            cast = ', '.join([c['name'] for c in cast_list])
            
            # Get director (for movies)
            director = ''
            if self.media_type == 'movie':
                crew = credits.get('crew', [])
                directors = [c['name'] for c in crew if c.get('job') == 'Director']
                director = ', '.join(directors[:2])
            else:
                # For TV, show creator
                creators = details.get('created_by', [])
                director = ', '.join([c['name'] for c in creators[:2]])
            
            # Get trailer
            videos = fetch_json(f"/{self.media_type}/{tmdb_id}/videos")
            trailers = [v for v in videos.get('results', []) 
                       if v.get('type') == 'Trailer' and v.get('site') == 'YouTube']
            if trailers:
                self.trailer_key = trailers[0].get('key')
            
            # Build meta string
            meta_parts = []
            if year:
                meta_parts.append(year)
            if rating:
                meta_parts.append(f"* {rating:.1f}")
            if runtime:
                meta_parts.append(runtime)
            if genres:
                meta_parts.append(genres)
            meta_string = '  •  '.join(meta_parts)
            
            # Set all properties
            self.setProperty('detail_title', title)
            self.setProperty('detail_meta', meta_string)
            self.setProperty('detail_tagline', details.get('tagline', ''))
            self.setProperty('detail_plot', details.get('overview', self.item_data.get('plot', '')))
            self.setProperty('detail_poster', poster)
            self.setProperty('detail_backdrop', backdrop)
            self.setProperty('detail_rating', f"{rating:.1f}" if rating else 'N/A')
            self.setProperty('detail_votes', f"{votes:,}")
            self.setProperty('detail_cast', cast or 'Unknown')
            self.setProperty('detail_director', director or 'Unknown')
            self.setProperty('detail_status', status)
            self.setProperty('detail_seasons', seasons)
            self.setProperty('detail_type', 'TV SHOW' if self.media_type == 'tv' else 'MOVIE')
            self.setProperty('detail_tmdb_id', str(tmdb_id))
            
            # Store for play action
            self.item_data['title'] = title
            self.item_data['year'] = year
            
            xbmc.log(f"[Orion] Detail loaded for: {title}", xbmc.LOGINFO)
            
        except Exception as e:
            xbmc.log(f"[Orion] Error loading details: {e}", xbmc.LOGWARNING)
            self._set_basic_info()
    
    def _set_basic_info(self):
        """Set basic info from item_data if TMDB fetch fails"""
        self.setProperty('detail_title', self.item_data.get('title', 'Unknown'))
        self.setProperty('detail_meta', self.item_data.get('year', ''))
        self.setProperty('detail_plot', self.item_data.get('plot', 'No description available.'))
        self.setProperty('detail_poster', self.item_data.get('poster', ADDON_ICON))
        self.setProperty('detail_backdrop', self.item_data.get('backdrop', ADDON_FANART))
        self.setProperty('detail_rating', self.item_data.get('rating', 'N/A'))
        self.setProperty('detail_votes', '0')
        self.setProperty('detail_cast', 'Unknown')
        self.setProperty('detail_director', 'Unknown')
        self.setProperty('detail_type', 'TV SHOW' if self.media_type == 'tv' else 'MOVIE')
        self.setProperty('detail_tmdb_id', str(self.item_data.get('id', '')))
    
    def onClick(self, controlId):
        """Handle control clicks"""
        xbmc.log(f"[Orion] DetailDialog onClick: {controlId}", xbmc.LOGINFO)
        
        if controlId == CLOSE_BTN:
            self.selected_action = 'close'
            self.close()
        
        elif controlId == PLAY_BTN:
            self.selected_action = 'play'
            self.close()
        
        elif controlId == TRAILER_BTN:
            self._play_trailer()
        
        elif controlId == FAVORITE_BTN:
            self._toggle_favorite()
    
    def _play_trailer(self):
        """Play YouTube trailer"""
        if not self.trailer_key:
            xbmcgui.Dialog().notification(
                'No Trailer',
                'No trailer available for this title',
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
            return
        
        # Try to play trailer via YouTube plugin
        youtube_url = f'plugin://plugin.video.youtube/play/?video_id={self.trailer_key}'
        
        try:
            xbmc.log(f"[Orion] Playing trailer: {youtube_url}", xbmc.LOGINFO)
            xbmc.Player().play(youtube_url)
        except Exception as e:
            xbmc.log(f"[Orion] Trailer playback error: {e}", xbmc.LOGWARNING)
            # Fallback: open in browser or show error
            xbmcgui.Dialog().notification(
                'Trailer Error',
                'Could not play trailer. YouTube addon may be required.',
                xbmcgui.NOTIFICATION_WARNING,
                3000
            )
    
    def _toggle_favorite(self):
        """Add/remove from favorites"""
        try:
            from .database import toggle_favorite, is_favorite
            
            tmdb_id = self.item_data.get('id')
            if not tmdb_id:
                return
            
            # Toggle favorite status
            is_fav = toggle_favorite(tmdb_id, self.media_type, self.item_data)
            
            # Show notification
            if is_fav:
                xbmcgui.Dialog().notification(
                    'Added to Favorites',
                    f"{self.item_data.get('title', 'Item')} added to favorites",
                    xbmcgui.NOTIFICATION_INFO,
                    2000
                )
            else:
                xbmcgui.Dialog().notification(
                    'Removed from Favorites',
                    f"{self.item_data.get('title', 'Item')} removed from favorites",
                    xbmcgui.NOTIFICATION_INFO,
                    2000
                )
                
        except Exception as e:
            xbmc.log(f"[Orion] Favorite toggle error: {e}", xbmc.LOGWARNING)
            xbmcgui.Dialog().notification(
                'Error',
                'Could not update favorites',
                xbmcgui.NOTIFICATION_WARNING,
                2000
            )
    
    def onAction(self, action):
        """Handle remote/keyboard actions"""
        action_id = action.getId()
        
        if action_id in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            self.selected_action = 'close'
            self.close()
        
        elif action_id == ACTION_SELECT_ITEM:
            focus_id = self.getFocusId()
            self.onClick(focus_id)
    
    def get_result(self):
        """Return the dialog result"""
        return self.selected_action, self.item_data


def show_detail(item_data, media_type='movie'):
    """
    Show the detail dialog for a movie or TV show.
    
    Args:
        item_data: Dict with item info {id, title, year, poster, backdrop, plot, rating}
        media_type: 'movie' or 'tv'
    
    Returns:
        Tuple of (action, item_data) where action is 'play', 'close', or None
    """
    dialog = DetailDialog(
        'DetailDialog.xml',
        ADDON_PATH,
        'Default',
        '1080i',
        item_data=item_data,
        media_type=media_type
    )
    
    dialog.doModal()
    result = dialog.get_result()
    del dialog
    
    return result
