# -*- coding: utf-8 -*-
"""
Orion Playback Monitor - Handles auto-play next episode and intro skipping
"""

import xbmc
import xbmcgui
import xbmcaddon
import json

ADDON = xbmcaddon.Addon()

class OrionPlayer(xbmc.Player):
    """Custom player to monitor playback"""
    
    def __init__(self):
        super(OrionPlayer, self).__init__()
        self.playing = False
        self.current_item = None
        self.total_time = 0
        self.intro_shown = False
        self.next_episode_shown = False
        self.intro_skip_dialog = None
        
    def onPlayBackStarted(self):
        """Called when playback starts"""
        self.playing = True
        self.intro_shown = False
        self.next_episode_shown = False
        
        # Get current playing item info
        try:
            info_tag = self.getVideoInfoTag()
            # Check if this is a TV episode
            if info_tag and info_tag.getMediaType() == 'episode':
                self.current_item = {
                    'type': 'episode',
                    'show_id': self.getProperty('orion.show_id'),
                    'show_title': self.getProperty('orion.show_title'),
                    'season': int(self.getProperty('orion.season') or 0),
                    'episode': int(self.getProperty('orion.episode') or 0)
                }
                xbmc.log(f"[Orion Monitor] Started playing: {self.current_item}", xbmc.LOGINFO)
            else:
                self.current_item = None
        except Exception as e:
            xbmc.log(f"[Orion Monitor] Error getting playback info: {e}", xbmc.LOGWARNING)
            self.current_item = None
    
    def onPlayBackStopped(self):
        """Called when playback stops"""
        self.playing = False
        self.current_item = None
        self._close_intro_dialog()
        
    def onPlayBackEnded(self):
        """Called when playback ends"""
        self.playing = False
        self.current_item = None
        self._close_intro_dialog()
    
    def _close_intro_dialog(self):
        """Close intro skip dialog if open"""
        if self.intro_skip_dialog:
            try:
                self.intro_skip_dialog.close()
            except:
                pass
            self.intro_skip_dialog = None
    
    def monitor_playback(self):
        """Main monitoring loop - call this from service"""
        while not xbmc.Monitor().abortRequested():
            if self.playing and self.current_item and self.current_item['type'] == 'episode':
                try:
                    # Get playback time
                    current_time = self.getTime()
                    total_time = self.getTotalTime()
                    
                    if total_time > 0:
                        # Check for intro skip (first 3 minutes of playback)
                        if not self.intro_shown and current_time < 180 and current_time > 5:
                            self._check_intro_skip(current_time, total_time)
                        
                        # Check for next episode countdown (1 minute before end)
                        time_remaining = total_time - current_time
                        if not self.next_episode_shown and 55 <= time_remaining <= 65:
                            self._show_next_episode_dialog()
                            
                except Exception as e:
                    xbmc.log(f"[Orion Monitor] Monitoring error: {e}", xbmc.LOGWARNING)
            
            xbmc.sleep(1000)  # Check every second
    
    def _check_intro_skip(self, current_time, total_time):
        """Check if we should show intro skip button"""
        skip_enabled = ADDON.getSetting('skip_intro_enabled') == 'true'
        if not skip_enabled:
            return
        
        auto_skip = ADDON.getSetting('skip_intro_auto') == 'true'
        
        # Get intro timing from TMDB or use fallback
        intro_end_time = self._get_intro_end_time()
        
        if intro_end_time and current_time < intro_end_time:
            if auto_skip:
                # Auto-skip intro
                xbmc.log(f"[Orion Monitor] Auto-skipping intro to {intro_end_time}s", xbmc.LOGINFO)
                self.seekTime(intro_end_time)
                xbmcgui.Dialog().notification('Orion', 'Intro skipped', ADDON.getAddonInfo('icon'), 2000)
                self.intro_shown = True
            else:
                # Show skip button
                self._show_skip_intro_button(intro_end_time)
                self.intro_shown = True
    
    def _get_intro_end_time(self):
        """Get intro end time from TMDB or use fallback"""
        # Try to get from TMDB first
        try:
            from resources.lib import tmdb
            
            if self.current_item:
                show_id = self.current_item.get('show_id')
                season = self.current_item.get('season')
                episode = self.current_item.get('episode')
                
                if show_id and season and episode:
                    intro_data = tmdb.get_episode_intro_markers(show_id, season, episode)
                    if intro_data and 'intro_end' in intro_data:
                        return intro_data['intro_end']
        except Exception as e:
            xbmc.log(f"[Orion Monitor] Error fetching intro data: {e}", xbmc.LOGWARNING)
        
        # Fallback to settings
        fallback_duration = int(ADDON.getSetting('skip_intro_fallback') or '90')
        return fallback_duration
    
    def _show_skip_intro_button(self, intro_end_time):
        """Show skip intro button overlay"""
        # Use simple notification for now - can be enhanced with custom dialog
        from resources.lib import intro_skipper
        intro_skipper.show_skip_intro_dialog(self, intro_end_time)
    
    def _show_next_episode_dialog(self):
        """Show next episode countdown dialog"""
        self.next_episode_shown = True
        
        auto_next_enabled = ADDON.getSetting('auto_next_episode') == 'true'
        if not auto_next_enabled:
            return
        
        # Get next episode info
        next_ep_info = self._get_next_episode_info()
        if not next_ep_info:
            xbmc.log("[Orion Monitor] No next episode found", xbmc.LOGINFO)
            return
        
        # Get countdown duration from settings
        countdown_duration = int(ADDON.getSetting('next_episode_countdown') or '5')
        
        # Show up next dialog
        from resources.lib import up_next
        
        show_title = self.current_item.get('show_title', 'Unknown')
        play_next = up_next.show_up_next(show_title, next_ep_info, countdown_duration)
        
        if play_next:
            # Stop current playback
            self.stop()
            
            # Play next episode
            self._play_next_episode(next_ep_info)
    
    def _get_next_episode_info(self):
        """Get next episode information from TMDB"""
        try:
            from resources.lib import tmdb
            
            if not self.current_item:
                return None
            
            show_id = self.current_item.get('show_id')
            current_season = self.current_item.get('season')
            current_episode = self.current_item.get('episode')
            
            if not all([show_id, current_season, current_episode]):
                return None
            
            # Try next episode in same season first
            season_data = tmdb.get_season_episodes(show_id, current_season)
            episodes = season_data.get('episodes', [])
            
            # Find next episode
            for ep in episodes:
                if ep.get('episode_number') == current_episode + 1:
                    return {
                        'show_id': show_id,
                        'season_number': current_season,
                        'episode_number': ep.get('episode_number'),
                        'name': ep.get('name', f"Episode {ep.get('episode_number')}"),
                        'still_path': tmdb.get_backdrop_url(ep.get('still_path')) or ADDON.getAddonInfo('icon'),
                        'overview': ep.get('overview', '')
                    }
            
            # If not found, try first episode of next season
            show_details = tmdb.get_tv_details(show_id)
            seasons = show_details.get('seasons', [])
            
            for season in seasons:
                if season.get('season_number') == current_season + 1:
                    next_season_data = tmdb.get_season_episodes(show_id, current_season + 1)
                    next_episodes = next_season_data.get('episodes', [])
                    
                    if next_episodes:
                        ep = next_episodes[0]
                        return {
                            'show_id': show_id,
                            'season_number': current_season + 1,
                            'episode_number': ep.get('episode_number'),
                            'name': ep.get('name', f"Episode {ep.get('episode_number')}"),
                            'still_path': tmdb.get_backdrop_url(ep.get('still_path')) or ADDON.getAddonInfo('icon'),
                            'overview': ep.get('overview', '')
                        }
            
            return None
            
        except Exception as e:
            xbmc.log(f"[Orion Monitor] Error getting next episode: {e}", xbmc.LOGERROR)
            return None
    
    def _play_next_episode(self, next_ep_info):
        """Trigger playback of next episode"""
        try:
            # Build plugin URL to play next episode
            show_id = next_ep_info.get('show_id')
            season = next_ep_info.get('season_number')
            episode = next_ep_info.get('episode_number')
            show_title = self.current_item.get('show_title', 'Unknown')
            
            # Use RunPlugin to trigger episode_sources action
            plugin_url = f'plugin://plugin.video.orion/?action=episode_sources&id={show_id}&title={show_title}&season={season}&episode={episode}'
            xbmc.executebuiltin(f'RunPlugin({plugin_url})')
            
            xbmc.log(f"[Orion Monitor] Playing next episode: S{season}E{episode}", xbmc.LOGINFO)
            
        except Exception as e:
            xbmc.log(f"[Orion Monitor] Error playing next episode: {e}", xbmc.LOGERROR)


def start_monitor():
    """Start the playback monitor service"""
    xbmc.log("[Orion Monitor] Starting playback monitor service", xbmc.LOGINFO)
    
    player = OrionPlayer()
    monitor = xbmc.Monitor()
    
    while not monitor.abortRequested():
        if player.playing and player.current_item:
            try:
                # Monitor playback for intro skip and next episode
                current_time = player.getTime()
                total_time = player.getTotalTime()
                
                if total_time > 0:
                    # Check for intro skip (first 3 minutes)
                    if not player.intro_shown and current_time < 180 and current_time > 5:
                        player._check_intro_skip(current_time, total_time)
                    
                    # Check for next episode (1 minute before end)
                    time_remaining = total_time - current_time
                    if not player.next_episode_shown and 55 <= time_remaining <= 65:
                        player._show_next_episode_dialog()
                        
            except Exception as e:
                xbmc.log(f"[Orion Monitor] Monitor error: {e}", xbmc.LOGWARNING)
        
        if monitor.waitForAbort(1):
            break
    
    xbmc.log("[Orion Monitor] Playback monitor service stopped", xbmc.LOGINFO)
