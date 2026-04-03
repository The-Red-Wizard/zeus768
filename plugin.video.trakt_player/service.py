# -*- coding: utf-8 -*-
"""Trakt Player background service: Scrobbling + Up Next."""
import sys
import os
import time
import xbmc
import xbmcgui
import xbmcaddon

# Ensure addon lib is importable
ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
sys.path.insert(0, ADDON_PATH)

from resources.lib import trakt_api, trakt_auth, tmdb


class TraktScrobbler(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.playing = False
        self.media_type = ''
        self.imdb_id = ''
        self.title = ''
        self.season = 0
        self.episode = 0
        self.show_title = ''
        self.scrobble_enabled = True
        self.upnext_enabled = True
        self.scrobbled_start = False
        self.total_time = 0

    def _read_props(self):
        """Read playback info from window properties set by player.py."""
        win = xbmcgui.Window(10000)
        self.media_type = win.getProperty('TraktPlayer.type')
        self.imdb_id = win.getProperty('TraktPlayer.imdb')
        self.title = win.getProperty('TraktPlayer.title')
        self.season = int(win.getProperty('TraktPlayer.season') or '0')
        self.episode = int(win.getProperty('TraktPlayer.episode') or '0')
        self.show_title = win.getProperty('TraktPlayer.show_title')
        self.scrobble_enabled = ADDON.getSetting('enable_scrobble') != 'false'
        self.upnext_enabled = ADDON.getSetting('enable_upnext') != 'false'

    def _clear_props(self):
        win = xbmcgui.Window(10000)
        for key in ('type', 'imdb', 'title', 'season', 'episode', 'show_title'):
            win.clearProperty('TraktPlayer.' + key)
        self.playing = False
        self.scrobbled_start = False
        self.media_type = ''

    def _progress(self):
        try:
            current = self.getTime()
            total = self.getTotalTime()
            if total > 0:
                return (current / total) * 100.0
        except Exception:
            pass
        return 0.0

    def _do_scrobble(self, action):
        if not self.scrobble_enabled or not self.media_type or not trakt_auth.is_authorized():
            return
        progress = self._progress()
        trakt_api.scrobble(action, self.media_type, self.imdb_id, self.season, self.episode, progress)

    def onAVStarted(self):
        self._read_props()
        if not self.media_type:
            return
        self.playing = True
        try:
            self.total_time = self.getTotalTime()
        except Exception:
            self.total_time = 0
        xbmc.log('TraktScrobbler: Playback started - %s' % self.title, xbmc.LOGINFO)
        self._do_scrobble('start')
        self.scrobbled_start = True

    def onPlayBackPaused(self):
        if self.playing and self.scrobbled_start:
            xbmc.log('TraktScrobbler: Paused', xbmc.LOGINFO)
            self._do_scrobble('pause')

    def onPlayBackResumed(self):
        if self.playing and self.scrobbled_start:
            xbmc.log('TraktScrobbler: Resumed', xbmc.LOGINFO)
            self._do_scrobble('start')

    def onPlayBackStopped(self):
        if self.playing and self.scrobbled_start:
            xbmc.log('TraktScrobbler: Stopped', xbmc.LOGINFO)
            self._do_scrobble('stop')
        self._clear_props()

    def onPlayBackEnded(self):
        if self.playing and self.scrobbled_start:
            xbmc.log('TraktScrobbler: Ended', xbmc.LOGINFO)
            self._do_scrobble('stop')
            # Up Next: auto-play next episode
            if self.upnext_enabled and self.media_type == 'episode' and self.show_title:
                self._try_upnext()
        self._clear_props()

    def _try_upnext(self):
        """Try to auto-play the next episode."""
        xbmc.log('TraktScrobbler: Up Next check for %s S%02dE%02d' % (
            self.show_title, self.season, self.episode), xbmc.LOGINFO)

        next_ep = self.episode + 1
        next_season = self.season

        # Try to find next episode via TMDB - need tmdb_id
        win = xbmcgui.Window(10000)
        tmdb_id = win.getProperty('TraktPlayer.tmdb_id')
        if not tmdb_id:
            return

        episodes = tmdb.get_season_episodes(tmdb_id, next_season)
        found = False
        for ep in episodes:
            if ep.get('episode_number', 0) == next_ep:
                found = True
                break

        if not found:
            # Try next season, episode 1
            next_season += 1
            next_ep = 1
            episodes = tmdb.get_season_episodes(tmdb_id, next_season)
            for ep in episodes:
                if ep.get('episode_number', 0) == next_ep:
                    found = True
                    break

        if found:
            ep_name = ''
            for ep in episodes:
                if ep.get('episode_number', 0) == next_ep:
                    ep_name = ep.get('name', '')
                    break

            dlg = xbmcgui.Dialog()
            label = '%s S%02dE%02d' % (self.show_title, next_season, next_ep)
            if ep_name:
                label += ' - %s' % ep_name
            play_next = dlg.yesno('Up Next', 'Play next episode?\n\n%s' % label,
                                  yeslabel='Play', nolabel='Stop', autoclose=15000)
            if play_next:
                from urllib.parse import quote_plus
                cmd = 'RunPlugin(plugin://plugin.video.trakt_player/?action=play_episode&title=%s&season=%d&episode=%d&imdb_id=%s)' % (
                    quote_plus(self.show_title), next_season, next_ep, self.imdb_id)
                xbmc.executebuiltin(cmd)


def main():
    xbmc.log('TraktPlayer Service: Started', xbmc.LOGINFO)
    monitor = xbmc.Monitor()
    player = TraktScrobbler()

    while not monitor.abortRequested():
        if monitor.waitForAbort(5):
            break

    xbmc.log('TraktPlayer Service: Stopped', xbmc.LOGINFO)


if __name__ == '__main__':
    main()
