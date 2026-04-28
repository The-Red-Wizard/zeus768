# -*- coding: utf-8 -*-
"""
Pre-Cache Next Episode Module
Auto-adds next episode to debrid cache while watching current episode
"""
import xbmc
import xbmcgui
import xbmcaddon
import threading
from . import scrapers
from . import debrid

ADDON = xbmcaddon.Addon()


def _get_next_episode_info(show_title, current_season, current_episode, tmdb_id=''):
    """Get info about the next episode"""
    next_season = current_season
    next_episode = current_episode + 1
    
    # Try to verify if next episode exists using TMDB
    if tmdb_id:
        try:
            from . import tmdb as tmdb_module
            episodes = tmdb_module.get_season_episodes(tmdb_id, current_season)
            
            # Check if next episode exists in current season
            ep_numbers = [ep.get('episode_number', 0) for ep in episodes]
            if next_episode not in ep_numbers:
                # Check next season
                next_season_episodes = tmdb_module.get_season_episodes(tmdb_id, current_season + 1)
                if next_season_episodes:
                    next_season = current_season + 1
                    next_episode = 1
                else:
                    return None  # No more episodes
        except Exception as e:
            xbmc.log(f'Pre-cache: Error checking TMDB: {e}', xbmc.LOGDEBUG)
    
    return {
        'title': show_title,
        'season': next_season,
        'episode': next_episode,
        'search_query': f'{show_title} S{str(next_season).zfill(2)}E{str(next_episode).zfill(2)}'
    }


def _precache_worker(show_title, season, episode, tmdb_id=''):
    """Background worker to pre-cache next episode"""
    try:
        addon = xbmcaddon.Addon()
        if addon.getSetting('enable_precache') != 'true':
            return
        
        xbmc.log(f'Pre-cache: Starting for {show_title} after S{season}E{episode}', xbmc.LOGINFO)
        
        # Get next episode info
        next_ep = _get_next_episode_info(show_title, season, episode, tmdb_id)
        if not next_ep:
            xbmc.log('Pre-cache: No next episode found', xbmc.LOGINFO)
            return
        
        search_query = next_ep['search_query']
        xbmc.log(f'Pre-cache: Searching for {search_query}', xbmc.LOGINFO)
        
        # Search for torrents
        try:
            results = scrapers.search_all(search_query, '1080p')
        except Exception as e:
            xbmc.log(f'Pre-cache: Scraper error: {e}', xbmc.LOGERROR)
            return
        
        if not results:
            xbmc.log('Pre-cache: No sources found for next episode', xbmc.LOGINFO)
            return
        
        # Extract hashes
        hashes = []
        for r in results[:10]:  # Check top 10
            h = scrapers.extract_hash(r.get('magnet', ''))
            if h:
                hashes.append(h)
                r['hash'] = h
        
        if not hashes:
            xbmc.log('Pre-cache: No valid hashes found', xbmc.LOGINFO)
            return
        
        # Check which are already cached
        try:
            cached_set = debrid.check_cache_all(hashes)
        except Exception as e:
            xbmc.log(f'Pre-cache: Cache check error: {e}', xbmc.LOGWARNING)
            cached_set = set()
        
        cached_count = len(cached_set)
        xbmc.log(f'Pre-cache: {cached_count}/{len(hashes)} already cached', xbmc.LOGINFO)
        
        if cached_count > 0:
            xbmc.log('Pre-cache: Next episode already cached!', xbmc.LOGINFO)
            _notify_precache_status(next_ep, 'already_cached')
            return
        
        # Try to add the best source to debrid cache
        # Sort by quality and seeds
        QUALITY_ORDER = ['1080p', '720p', '480p']
        order_map = {q: i for i, q in enumerate(QUALITY_ORDER)}
        results.sort(key=lambda r: (order_map.get(r.get('quality', '720p'), 9), -r.get('seeds', 0)))
        
        for source in results[:3]:  # Try top 3 sources
            magnet = source.get('magnet', '')
            if not magnet:
                continue
            
            xbmc.log(f'Pre-cache: Adding to cache: {source.get("title", "")[:50]}...', xbmc.LOGINFO)
            
            # Add magnet to debrid (this triggers caching)
            services = debrid.get_active_services()
            for name, service in services:
                try:
                    # Just add the magnet - don't wait for full download
                    if hasattr(service, 'add_magnet'):
                        result = service.add_magnet(magnet, check_cache_first=False)
                        if result:
                            xbmc.log(f'Pre-cache: Added to {name} cache queue', xbmc.LOGINFO)
                            _notify_precache_status(next_ep, 'caching', name)
                            return
                except Exception as e:
                    xbmc.log(f'Pre-cache: {name} error: {e}', xbmc.LOGWARNING)
                    continue
        
        xbmc.log('Pre-cache: Could not add to any debrid cache', xbmc.LOGWARNING)
        
    except Exception as e:
        xbmc.log(f'Pre-cache worker error: {e}', xbmc.LOGERROR)


def _notify_precache_status(next_ep, status, service_name=''):
    """Show notification about pre-cache status"""
    addon = xbmcaddon.Addon()
    if addon.getSetting('precache_notifications') != 'true':
        return
    
    ep_str = f"S{next_ep['season']:02d}E{next_ep['episode']:02d}"
    
    if status == 'already_cached':
        msg = f'Next episode {ep_str} is ready!'
        icon = xbmcgui.NOTIFICATION_INFO
    elif status == 'caching':
        msg = f'Caching {ep_str} via {service_name}'
        icon = xbmcgui.NOTIFICATION_INFO
    else:
        msg = f'Pre-caching {ep_str}...'
        icon = xbmcgui.NOTIFICATION_INFO
    
    xbmcgui.Dialog().notification(
        next_ep['title'][:20],
        msg,
        icon,
        3000
    )


def start_precache(show_title, season, episode, tmdb_id=''):
    """Start pre-caching next episode in background thread"""
    addon = xbmcaddon.Addon()
    if addon.getSetting('enable_precache') != 'true':
        return
    
    try:
        season = int(season)
        episode = int(episode)
    except (ValueError, TypeError):
        return
    
    # Start background thread
    thread = threading.Thread(
        target=_precache_worker,
        args=(show_title, season, episode, tmdb_id),
        daemon=True
    )
    thread.start()
    xbmc.log(f'Pre-cache: Started background thread for {show_title}', xbmc.LOGDEBUG)


class PrecacheMonitor(xbmc.Player):
    """Monitor playback to trigger pre-caching at the right time"""
    
    def __init__(self):
        super().__init__()
        self._precache_triggered = False
        self._current_show = None
        self._current_season = 0
        self._current_episode = 0
        self._tmdb_id = ''
    
    def set_episode_info(self, show_title, season, episode, tmdb_id=''):
        """Set current episode info for pre-cache tracking"""
        self._current_show = show_title
        self._current_season = int(season) if season else 0
        self._current_episode = int(episode) if episode else 0
        self._tmdb_id = str(tmdb_id) if tmdb_id else ''
        self._precache_triggered = False
        xbmc.log(f'Pre-cache monitor: Tracking {show_title} S{season}E{episode}', xbmc.LOGDEBUG)
    
    def onPlayBackStarted(self):
        """Called when playback starts"""
        self._precache_triggered = False
    
    def onAVStarted(self):
        """Called when audio/video actually starts playing"""
        pass
    
    def check_and_precache(self):
        """Check playback progress and trigger pre-cache at ~75%"""
        if self._precache_triggered or not self._current_show:
            return
        
        if not self.isPlaying():
            return
        
        try:
            total_time = self.getTotalTime()
            current_time = self.getTime()
            
            if total_time <= 0:
                return
            
            progress = (current_time / total_time) * 100
            
            # Trigger pre-cache at 75% through the episode
            if progress >= 75:
                self._precache_triggered = True
                xbmc.log(f'Pre-cache: Triggering at {progress:.1f}% progress', xbmc.LOGINFO)
                start_precache(
                    self._current_show,
                    self._current_season,
                    self._current_episode,
                    self._tmdb_id
                )
        except Exception as e:
            xbmc.log(f'Pre-cache monitor error: {e}', xbmc.LOGDEBUG)
    
    def onPlayBackStopped(self):
        """Called when playback is stopped"""
        self._reset()
    
    def onPlayBackEnded(self):
        """Called when playback ends"""
        self._reset()
    
    def _reset(self):
        """Reset state"""
        self._precache_triggered = False
        self._current_show = None
        self._current_season = 0
        self._current_episode = 0
        self._tmdb_id = ''


# Global monitor instance
_precache_monitor = None


def get_monitor():
    """Get or create the pre-cache monitor"""
    global _precache_monitor
    if _precache_monitor is None:
        _precache_monitor = PrecacheMonitor()
    return _precache_monitor
