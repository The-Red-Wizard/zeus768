# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

# Python 2/3 compat - must be FIRST import
from resources.lib.libraries import py3compat

import sys
try:
    from urllib.parse import parse_qsl
except ImportError:
    from urlparse import parse_qsl
from resources.lib.libraries import control

import xbmcaddon, os, xbmc, xbmcvfs
scriptID = 'plugin.video.genesis'
ptv = xbmcaddon.Addon(scriptID)
datapath = xbmcvfs.translatePath(ptv.getAddonInfo('profile'))

BASE_RESOURCE_PATH = os.path.join( ptv.getAddonInfo('path'), "mylib" )
sys.path.append( os.path.join( ptv.getAddonInfo('path'), "mylib" ) )


params = dict(parse_qsl(sys.argv[2].replace('?','')))
control.log("->----------                PARAMS: %s" % params)


try:
    action = params['action']
except:
    action = None
try:
    name = params['name']
except:
    name = None
try:
    title = params['title']
except:
    title = None
try:
    year = params['year']
except:
    year = None
try:
    imdb = params['imdb']
except:
    imdb = '0'
try:
    tmdb = params['tmdb']
except:
    tmdb = '0'
try:
    tvdb = params['tvdb']
except:
    tvdb = '0'
try:
    tvrage = params['tvrage']
except:
    tvrage = '0'
try:
    season = params['season']
except:
    season = None
try:
    episode = params['episode']
except:
    episode = None
try:
    tvshowtitle = params['tvshowtitle']
except:
    tvshowtitle = None
try:
    tvshowtitle = params['show']
except:
    pass
try:
    alter = params['alter']
except:
    alter = '0'
try:
    alter = params['genre']
except:
    pass
try:
    date = params['date']
except:
    date = None
try:
    url = params['url']
except:
    url = None
try:
    image = params['image']
except:
    image = None
try:
    meta = params['meta']
except:
    meta = None
try:
    query = params['query']
except:
    query = None
try:
    source = params['source']
except:
    source = None
try:
    content = params['content']
except:
    content = None
try:
    provider = params['provider']
except:
    provider = None



if action == None:
    from resources.lib.indexers import navigator
    navigator.navigator().root()


elif action == 'realdebridauth':
    from resources.lib.resolvers.realdebrid import rdAuthorize
    rdAuthorize()

elif action == 'premiumizeauth':
    from resources.lib.resolvers.premiumize import pmAuthorize
    pmAuthorize()

elif action == 'alldebridauth':
    from resources.lib.resolvers.alldebrid import adAuthorize
    adAuthorize()

elif action == 'torboxauth':
    from resources.lib.resolvers.torbox import tbAuthorize
    tbAuthorize()

elif action == 'authTrakt':
    from resources.lib.libraries import trakt
    trakt.authTrakt()

elif action == 'movieNavigator':
    from resources.lib.indexers import navigator
    navigator.navigator().movies()

elif action == 'tvNavigator':
    from resources.lib.indexers import navigator
    navigator.navigator().tvshows()

elif action == 'myNavigator':
    from resources.lib.indexers import navigator
    navigator.navigator().genesis()

elif action == 'downloadNavigator':
    from resources.lib.indexers import navigator
    navigator.navigator().downloads()

elif action == 'toolNavigator':
    from resources.lib.indexers import navigator
    navigator.navigator().tools()

elif action == 'libtoolNavigator':
    from resources.lib.indexers import navigator
    navigator.navigator().library()

elif action == 'searchNavigator':
    from resources.lib.indexers import navigator
    navigator.navigator().search()

elif action == 'movies':
    from resources.lib.indexers import movies
    movies.movies().get(url)

elif action == 'movieWidget':
    from resources.lib.indexers import movies
    movies.movies().widget()

elif action == 'movieFavourites':
    from resources.lib.indexers import movies
    movies.movies().favourites()

elif action == 'movieSearch':
    from resources.lib.indexers import movies
    movies.movies().search(query)

elif action == 'moviePerson':
    from resources.lib.indexers import movies
    movies.movies().person(query)

elif action == 'movieGenres':
    from resources.lib.indexers import movies
    movies.movies().genres()

elif action == 'movieCertificates':
    from resources.lib.indexers import movies
    movies.movies().certifications()

elif action == 'movieYears':
    from resources.lib.indexers import movies
    movies.movies().years()

elif action == 'moviePersons':
    from resources.lib.indexers import movies
    movies.movies().persons()

elif action == 'movieUserlists':
    from resources.lib.indexers import movies
    movies.movies().userlists()

elif action == 'channels':
    from resources.lib.indexers import channels
    channels.channels().get()

elif action == 'tvshows':
    from resources.lib.indexers import tvshows
    tvshows.tvshows().get(url)

elif action == 'tvFavourites':
    from resources.lib.indexers import tvshows
    tvshows.tvshows().favourites()

elif action == 'tvSearch':
    from resources.lib.indexers import tvshows
    tvshows.tvshows().search(query)

elif action == 'tvPerson':
    from resources.lib.indexers import tvshows
    tvshows.tvshows().person(query)

elif action == 'tvGenres':
    from resources.lib.indexers import tvshows
    tvshows.tvshows().genres()

elif action == 'tvNetworks':
    from resources.lib.indexers import tvshows
    tvshows.tvshows().networks()

elif action == 'tvYears':
    from resources.lib.indexers import tvshows
    tvshows.tvshows().years()

elif action == 'tvUserlists':
    from resources.lib.indexers import tvshows
    tvshows.tvshows().userlists()

elif action == 'seasons':
    from resources.lib.indexers import episodes
    episodes.seasons().get(tvshowtitle, year, imdb, tmdb, tvdb, tvrage)

elif action == 'episodes':
    from resources.lib.indexers import episodes
    episodes.episodes().get(tvshowtitle, year, imdb, tmdb, tvdb, tvrage, season, episode)

elif action == 'calendar':
    from resources.lib.indexers import episodes
    episodes.episodes().calendar(url)

elif action == 'tvWidget':
    from resources.lib.indexers import episodes
    episodes.episodes().widget()


elif action == 'episodeFavourites':
    from resources.lib.indexers import episodes
    episodes.episodes().favourites()

elif action == 'calendars':
    from resources.lib.indexers import episodes
    episodes.episodes().calendars()

elif action == 'refresh':
    from resources.lib.libraries import control
    control.refresh()

elif action == 'queueItem':
    from resources.lib.libraries import control
    control.queueItem()

elif action == 'openPlaylist':
    from resources.lib.libraries import control
    control.openPlaylist()

elif action == 'openSettings':
    from resources.lib.libraries import control
    control.openSettings(query)

elif action == 'moviePlaycount':
    from resources.lib.libraries import playcount
    playcount.movies(imdb, query)

elif action == 'episodePlaycount':
    from resources.lib.libraries import playcount
    playcount.episodes(imdb, tvdb, season, episode, query)

elif action == 'tvPlaycount':
    from resources.lib.libraries import playcount
    playcount.tvshows(name, imdb, tvdb, season, query)

elif action == 'trailer':
    from resources.lib.libraries import trailer
    trailer.trailer().play(name, url)

elif action == 'clearCache':
    from resources.lib.libraries import cache
    cache.clear()

elif action == 'addFavourite':
    from resources.lib.libraries import favourites
    favourites.addFavourite(meta, content, query)

elif action == 'deleteFavourite':
    from resources.lib.libraries import favourites
    favourites.deleteFavourite(meta, content)

elif action == 'addView':
    from resources.lib.libraries import views
    views.addView(content)

elif action == 'traktManager':
    from resources.lib.libraries import trakt
    trakt.manager(name, imdb, tvdb, content)

elif action == 'movieToLibrary':
    from resources.lib.libraries import libtools
    libtools.libmovies().add(name, title, year, imdb, tmdb)

elif action == 'moviesToLibrary':
    from resources.lib.libraries import libtools
    libtools.libmovies().range(url)

elif action == 'tvshowToLibrary':
    from resources.lib.libraries import libtools
    libtools.libtvshows().add(tvshowtitle, year, imdb, tmdb, tvdb, tvrage)

elif action == 'tvshowsToLibrary':
    from resources.lib.libraries import libtools
    libtools.libtvshows().range(url)

elif action == 'updateLibrary':
    from resources.lib.libraries import libtools
    libtools.libepisodes().update(query)

elif action == 'service':
    from resources.lib.libraries import libtools
    libtools.libepisodes().service()

elif action == 'resolve':
    from resources.lib.sources import sources
    from resources.lib.libraries import control
    url = sources().sourcesResolve(url, provider)
    control.addItem(handle=int(sys.argv[1]), url=url, listitem=control.item(name))
    control.directory(int(sys.argv[1]))

elif action == 'download':
    from resources.lib.sources import sources
    from resources.lib.libraries import simpledownloader
    url = sources().sourcesResolve(url, provider)
    simpledownloader.download(name, image, url)

elif action == 'play':
    from resources.lib.sources import sources
    sources().play(name, title, year, imdb, tmdb, tvdb, tvrage, season, episode, tvshowtitle, alter, date, meta, url)

elif action == 'sources':
    from resources.lib.sources import sources
    sources().addItem(name, title, year, imdb, tmdb, tvdb, tvrage, season, episode, tvshowtitle, alter, date, meta)

elif action == 'playItem':
    from resources.lib.sources import sources
    sources().playItem(content, name, year, imdb, tvdb, source)

elif action == 'alterSources':
    from resources.lib.sources import sources
    sources().alterSources(url, meta)

elif action == 'clearSources':
    from resources.lib.sources import sources
    sources().clearSources()

elif action == 'loguploader':
    from resources.lib.libraries import loguploader
    loguploader.Luguploader()

elif action == 'buy_beer':
    import xbmcgui, xbmcvfs
    import time as _time
    try:
        import ssl
        from urllib.request import urlopen as _urlopen, Request as _Request
        from urllib.parse import quote_plus as _qp
    except:
        from urllib2 import urlopen as _urlopen, Request as _Request
        from urllib import quote_plus as _qp
    
    kofi_url = 'https://ko-fi.com/zeus768'
    qr_file = os.path.join(xbmcvfs.translatePath('special://temp/'), 'kofi_qr.png')
    DONATION_TIMEOUT = 60  # 60 seconds display time
    
    # Generate QR code
    qr_generated = False
    try:
        ctx = ssl._create_unverified_context()
        req = _Request(
            'https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=%s&bgcolor=0-0-0&color=255-255-255&margin=20' % _qp(kofi_url), 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        resp = _urlopen(req, context=ctx, timeout=10)
        with open(qr_file, 'wb') as f:
            f.write(resp.read())
        qr_generated = True
    except Exception as e:
        xbmc.log('[Genesis] QR generation error: %s' % str(e), xbmc.LOGERROR)
    
    # Show donation dialog with 60 second countdown
    class DonationWindow(xbmcgui.WindowDialog):
        def __init__(self, qr_path, url, timeout):
            self.qr_path = qr_path
            self.url = url
            self.timeout = timeout
            self.start_time = _time.time()
            self.running = True
            self.controls = []
            self._create_ui()
        
        def _create_ui(self):
            # Screen dimensions
            w, h = 1920, 1080
            
            # Semi-transparent background
            bg = xbmcgui.ControlImage(int(w*0.2), int(h*0.05), int(w*0.6), int(h*0.9), '', aspectRatio=0)
            self.addControl(bg)
            bg.setColorDiffuse('DD000000')
            self.controls.append(bg)
            
            # Title
            title = xbmcgui.ControlLabel(int(w*0.2), int(h*0.08), int(w*0.6), 60,
                '[B][COLOR gold]Buy Me a Beer![/COLOR][/B]', alignment=0x00000002, font='font37')
            self.addControl(title)
            self.controls.append(title)
            
            # QR Code
            if self.qr_path and os.path.exists(self.qr_path):
                qr_img = xbmcgui.ControlImage(int(w*0.35), int(h*0.18), int(w*0.3), int(h*0.5), self.qr_path, aspectRatio=2)
                self.addControl(qr_img)
                self.controls.append(qr_img)
            
            # URL
            url_lbl = xbmcgui.ControlLabel(int(w*0.2), int(h*0.7), int(w*0.6), 40,
                '[COLOR skyblue]%s[/COLOR]' % self.url, alignment=0x00000002)
            self.addControl(url_lbl)
            self.controls.append(url_lbl)
            
            # Instructions
            instr = xbmcgui.ControlLabel(int(w*0.2), int(h*0.75), int(w*0.6), 30,
                'Scan QR code or visit the link above', alignment=0x00000002)
            self.addControl(instr)
            self.controls.append(instr)
            
            # Countdown
            self.countdown_lbl = xbmcgui.ControlLabel(int(w*0.2), int(h*0.8), int(w*0.6), 30,
                '[COLOR yellow]Closing in %d seconds...[/COLOR]' % self.timeout, alignment=0x00000002)
            self.addControl(self.countdown_lbl)
            self.controls.append(self.countdown_lbl)
            
            # Close instruction
            close_lbl = xbmcgui.ControlLabel(int(w*0.2), int(h*0.85), int(w*0.6), 25,
                'Press [B]Back[/B] or [B]ESC[/B] to close earlier', alignment=0x00000002)
            self.addControl(close_lbl)
            self.controls.append(close_lbl)
            
            # Thanks
            thanks = xbmcgui.ControlLabel(int(w*0.2), int(h*0.9), int(w*0.6), 30,
                '[COLOR lime]Thank you for supporting Genesis development![/COLOR]', alignment=0x00000002)
            self.addControl(thanks)
            self.controls.append(thanks)
        
        def doModal(self):
            self.show()
            while self.running:
                elapsed = _time.time() - self.start_time
                remaining = max(0, self.timeout - int(elapsed))
                if remaining <= 0:
                    break
                try:
                    self.countdown_lbl.setLabel('[COLOR yellow]Closing in %d seconds...[/COLOR]' % remaining)
                except:
                    pass
                xbmc.sleep(1000)
            self.close()
        
        def onAction(self, action):
            if action.getId() in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, 10, 92]:
                self.running = False
    
    # Show the window
    try:
        donation_win = DonationWindow(qr_file if qr_generated else None, kofi_url, DONATION_TIMEOUT)
        donation_win.doModal()
        del donation_win
    except Exception as e:
        xbmc.log('[Genesis] Donation window error: %s' % str(e), xbmc.LOGERROR)
        # Fallback to simple dialog
        xbmcgui.Dialog().ok('Support zeus768', 
            'Scan QR or visit:\n[COLOR cyan]%s[/COLOR]\n\nThank you for your support!' % kofi_url)
