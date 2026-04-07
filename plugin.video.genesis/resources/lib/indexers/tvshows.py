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

# Python 2/3 compatibility - must be FIRST
from resources.lib.libraries import py3compat

import os,sys,re,json,base64,datetime

# Python 2/3 compatible imports
try:
    import urllib
    import urlparse
except ImportError:
    import urllib.parse as urllib
    import urllib.parse as urlparse

try: action = dict(urlparse.parse_qsl(sys.argv[2].replace('?','')))['action']
except: action = None

from resources.lib.libraries import trakt
from resources.lib.libraries import control
from resources.lib.libraries import client
from resources.lib.libraries import cache
from resources.lib.libraries import metacache
from resources.lib.libraries import favourites
from resources.lib.libraries import workers
from resources.lib.libraries import views
from resources.lib.libraries import playcount
from resources.lib.libraries import cleangenre


# TMDB API key (shared with Orion)
TMDB_API_KEY = 'f15af109700aab95d564acda15bdcd97'
TMDB_BASE = 'https://api.themoviedb.org/3'


class tvshows:
    def __init__(self):
        self.list = []

        self.trakt_link = 'https://api.trakt.tv'
        self.tmdb_poster = 'https://image.tmdb.org/t/p/w500'
        self.tmdb_fanart = 'https://image.tmdb.org/t/p/w1280'
        self.tvdb_key = control.tvdb_key
        self.datetime = (datetime.datetime.utcnow() - datetime.timedelta(hours = 5))
        self.today_date = (self.datetime).strftime('%Y-%m-%d')
        self.week_date = (self.datetime - datetime.timedelta(days = 7)).strftime('%Y-%m-%d')
        self.month_date = (self.datetime - datetime.timedelta(days = 30)).strftime('%Y-%m-%d')
        self.year_date = (self.datetime - datetime.timedelta(days = 365)).strftime('%Y-%m-%d')
        self.trakt_user = control.setting('trakt.user')
        self.imdb_user = control.setting('imdb_user').replace('ur', '')
        self.info_lang = control.info_lang or 'en'

        self.tvdb_info_link = 'http://thetvdb.com/api/%s/series/%s/%s.xml' % (self.tvdb_key, '%s', re.sub('bg', 'en', self.info_lang))
        self.tvdb_by_imdb = 'http://thetvdb.com/api/GetSeriesByRemoteID.php?imdbid=%s'
        self.tvdb_image = 'http://thetvdb.com/banners/'

        # All category links now use Trakt API
        self.popular_link = 'https://api.trakt.tv/shows/popular?limit=20&page=1'
        self.rating_link = 'https://api.trakt.tv/shows/watched/all?limit=20&page=1'
        self.views_link = 'https://api.trakt.tv/shows/played/all?limit=20&page=1'
        self.trending_link = 'https://api.trakt.tv/shows/trending?limit=20&page=1'
        self.airing_link = 'https://api.trakt.tv/calendars/all/shows/%s/1?limit=20' % self.today_date
        self.premiere_link = 'https://api.trakt.tv/calendars/all/shows/premieres/%s/7?limit=20' % self.week_date

        # Genre and year links use Trakt filters
        self.genre_link = 'https://api.trakt.tv/shows/popular?genres=%s&limit=20&page=1'
        self.year_link = 'https://api.trakt.tv/shows/popular?years=%s&limit=20&page=1'

        # TV Maze network links (still works)
        self.tvmaze_link = 'http://www.tvmaze.com'
        self.tvmaze_info_link = 'http://api.tvmaze.com/shows/%s'

        self.search_link = 'https://api.trakt.tv/search?type=show&query=%s'

        # Trakt user list links
        self.traktlists_link = 'https://api.trakt.tv/users/me/lists'
        self.traktlist_link = 'https://api.trakt.tv/users/me/lists/%s/items' % '%s'
        self.traktcollection_link = 'https://api.trakt.tv/users/me/collection/shows'
        self.traktwatchlist_link = 'https://api.trakt.tv/users/me/watchlist/shows'
        self.traktfeatured_link = 'https://api.trakt.tv/recommendations/shows?limit=40'
        self.traktratings_link = 'https://api.trakt.tv/users/me/ratings/shows'

        # IMDB user list links (kept for IMDB lists if configured)
        self.imdb_link = 'http://www.imdb.com'
        self.imdblists_link = 'http://www.imdb.com/user/ur%s/lists?tab=all&sort=modified:desc&filter=titles' % self.imdb_user
        self.imdblist_link = 'http://www.imdb.com/list/%s/?view=detail&sort=title:asc&title_type=tv_series,mini_series&start=1'
        self.imdbwatchlist_link = 'http://www.imdb.com/user/ur%s/watchlist' % self.imdb_user

        self.trakt_lang_link = 'https://api.trakt.tv/shows/%s/translations/%s'

        # TMDB info link for metadata enrichment
        self.tmdb_tv_info_link = TMDB_BASE + '/tv/%s?api_key=' + TMDB_API_KEY + '&append_to_response=credits,external_ids'
        self.tmdb_find_link = TMDB_BASE + '/find/%s?api_key=' + TMDB_API_KEY + '&external_source=imdb_id'


    def get(self, url, idx=True):
        try:
            try: url = getattr(self, url + '_link')
            except: pass

            try: u = urlparse.urlparse(url).netloc.lower()
            except: pass

            if u in self.trakt_link and '/users/' in url:
                self.list = cache.get(self.trakt_list, 0, url)
                self.list = sorted(self.list, key=lambda k: k['title'])
                if idx == True: self.worker()

            elif u in self.trakt_link:
                self.list = cache.get(self.trakt_list, 1, url)
                if idx == True: self.worker()

            elif u in self.imdb_link and ('/user/' in url or '/list/' in url):
                self.list = cache.get(self.imdb_list, 0, url, idx)
                self.worker()

            elif u in self.imdb_link:
                self.list = cache.get(self.imdb_list, 24, url)
                self.worker()

            elif u in self.tvmaze_link:
                self.list = self.tvmaze_list(url)
                self.worker()

            if idx == True: self.tvshowDirectory(self.list)
            return self.list
        except:
            pass


    def favourites(self):
        try:
            items = favourites.getFavourites('tvshows')
            self.list = [i[1] for i in items]

            for i in self.list:
                if not 'name' in i: i['name'] = i['title']
                try: i['title'] = i['title']
                except: pass
                try: i['name'] = i['name']
                except: pass
                if not 'year' in i: i['year'] = '0'
                if not 'duration' in i: i['duration'] = '0'
                if not 'imdb' in i: i['imdb'] = '0'
                if not 'tmdb' in i: i['tmdb'] = '0'
                if not 'tvdb' in i: i['tvdb'] = '0'
                if not 'tvrage' in i: i['tvrage'] = '0'
                if not 'poster' in i: i['poster'] = '0'
                if not 'banner' in i: i['banner'] = '0'
                if not 'fanart' in i: i['fanart'] = '0'

            self.worker()
            self.list = sorted(self.list, key=lambda k: k['title'])
            self.tvshowDirectory(self.list)
        except:
            return

    def search(self, query=None):
        try:
            if query == None:
                t = control.lang(30231)
                k = control.keyboard('', t) ; k.doModal()
                self.query = k.getText() if k.isConfirmed() else None
            else:
                self.query = query

            if (self.query == None or self.query == ''): return

            url = self.search_link % urllib.quote_plus(self.query)
            self.list = cache.get(self.trakt_list, 0, url)

            self.worker()
            self.tvshowDirectory(self.list)
            return self.list
        except:
            return

    def person(self, query=None):
        try:
            if query == None:
                t = control.lang(30231)
                k = control.keyboard('', t) ; k.doModal()
                self.query = k.getText() if k.isConfirmed() else None
            else:
                self.query = query

            if (self.query == None or self.query == ''): return

            url = TMDB_BASE + '/search/person?api_key=' + TMDB_API_KEY + '&query=%s&page=1' % urllib.quote_plus(self.query)
            self.list = cache.get(self.tmdb_person_list, 0, url)

            if self.list is None:
                self.list = []
            for i in range(0, len(self.list)): self.list[i].update({'action': 'tvshows'})
            self.addDirectory(self.list)
            return self.list
        except:
            return

    def genres(self):
        genres = [
        ('Action', 'action'),
        ('Adventure', 'adventure'),
        ('Animation', 'animation'),
        ('Biography', 'biography'),
        ('Comedy', 'comedy'),
        ('Crime', 'crime'),
        ('Documentary', 'documentary'),
        ('Drama', 'drama'),
        ('Family', 'family'),
        ('Fantasy', 'fantasy'),
        ('Game Show', 'game-show'),
        ('History', 'history'),
        ('Horror', 'horror'),
        ('Music', 'music'),
        ('Musical', 'musical'),
        ('Mystery', 'mystery'),
        ('News', 'news'),
        ('Reality', 'reality'),
        ('Romance', 'romance'),
        ('Science Fiction', 'science-fiction'),
        ('Superhero', 'superhero'),
        ('Talk Show', 'talk-show'),
        ('Thriller', 'thriller'),
        ('War', 'war'),
        ('Western', 'western')
        ]

        for i in genres: self.list.append({'name': cleangenre.lang(i[0], self.info_lang), 'url': self.genre_link % i[1], 'image': 'genres.png', 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list

    def networks(self):
        networks = [
        ('A&E', '/networks/29/ae'),
        ('ABC', '/networks/3/abc'),
        ('AMC', '/networks/20/amc'),
        ('AT-X', '/networks/167/at-x'),
        ('Adult Swim', '/networks/10/adult-swim'),
        ('Amazon', '/webchannels/3/amazon'),
        ('Animal Planet', '/networks/92/animal-planet'),
        ('Audience', '/networks/31/audience-network'),
        ('BBC America', '/networks/15/bbc-america'),
        ('BBC Four', '/networks/51/bbc-four'),
        ('BBC One', '/networks/12/bbc-one'),
        ('BBC Three', '/webchannels/71/bbc-three'),
        ('BBC Two', '/networks/37/bbc-two'),
        ('BET', '/networks/56/bet'),
        ('Bravo', '/networks/52/bravo'),
        ('CBC', '/networks/36/cbc'),
        ('CBS', '/networks/2/cbs'),
        ('CTV', '/networks/48/ctv'),
        ('CW', '/networks/5/the-cw'),
        ('CW Seed', '/webchannels/13/cw-seed'),
        ('Cartoon Network', '/networks/11/cartoon-network'),
        ('Channel 4', '/networks/45/channel-4'),
        ('Channel 5', '/networks/135/channel-5'),
        ('Cinemax', '/networks/19/cinemax'),
        ('Comedy Central', '/networks/23/comedy-central'),
        ('Crackle', '/webchannels/4/crackle'),
        ('Discovery Channel', '/networks/66/discovery-channel'),
        ('Discovery ID', '/networks/89/investigation-discovery'),
        ('Disney Channel', '/networks/78/disney-channel'),
        ('Disney XD', '/networks/25/disney-xd'),
        ('Disney+', '/webchannels/287/disney-plus'),
        ('E! Entertainment', '/networks/43/e'),
        ('E4', '/networks/41/e4'),
        ('FOX', '/networks/4/fox'),
        ('FX', '/networks/13/fx'),
        ('Freeform', '/networks/26/freeform'),
        ('HBO', '/networks/8/hbo'),
        ('HGTV', '/networks/192/hgtv'),
        ('Hallmark', '/networks/50/hallmark-channel'),
        ('History Channel', '/networks/53/history'),
        ('Hulu', '/webchannels/2/hulu'),
        ('ITV', '/networks/35/itv'),
        ('Lifetime', '/networks/18/lifetime'),
        ('MTV', '/networks/22/mtv'),
        ('NBC', '/networks/1/nbc'),
        ('National Geographic', '/networks/42/national-geographic-channel'),
        ('Netflix', '/webchannels/1/netflix'),
        ('Nickelodeon', '/networks/27/nickelodeon'),
        ('PBS', '/networks/85/pbs'),
        ('Paramount+', '/webchannels/107/paramount-plus'),
        ('Peacock', '/webchannels/210/peacock'),
        ('Showtime', '/networks/9/showtime'),
        ('Sky1', '/networks/63/sky-1'),
        ('Starz', '/networks/17/starz'),
        ('Sundance', '/networks/33/sundance-tv'),
        ('Syfy', '/networks/16/syfy'),
        ('TBS', '/networks/32/tbs'),
        ('TLC', '/networks/80/tlc'),
        ('TNT', '/networks/14/tnt'),
        ('TV Land', '/networks/57/tvland'),
        ('Travel Channel', '/networks/82/travel-channel'),
        ('TruTV', '/networks/84/trutv'),
        ('USA', '/networks/30/usa-network'),
        ('VH1', '/networks/55/vh1'),
        ('WGN', '/networks/28/wgn-america'),
        ('Apple TV+', '/webchannels/310/apple-tv-plus'),
        ]
        for i in networks: self.list.append({'name': i[0], 'url': self.tvmaze_link + i[1], 'image': 'networks.png', 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list

    def years(self):
        year = (self.datetime.strftime('%Y'))

        for i in range(int(year)-0, int(year)-50, -1): self.list.append({'name': str(i), 'url': self.year_link % (str(i)), 'image': 'tvshows.jpg', 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list

    def userlists(self):
        try:
            userlists = []
            if trakt.getTraktCredentials() == False: raise Exception()
            userlists += cache.get(self.trakt_user_list, 0, self.traktlists_link)
        except:
            pass
        try:
            self.list = []
            if self.imdb_user == '': raise Exception()
            userlists += cache.get(self.imdb_user_list, 0, self.imdblists_link)
        except:
            pass

        self.list = userlists
        if self.list is None:
            self.list = []
        for i in range(0, len(self.list)): self.list[i].update({'image': 'tvUserlists.jpg', 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list

    def trakt_list(self, url):
        try:
            q = dict(urlparse.parse_qsl(urlparse.urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urllib.urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urlparse.urlparse(url).query, '') + '?' + q

            result = trakt.getTrakt(u)
            result = json.loads(result)

            items = []
            for i in result:
                try: items.append(i['show'])
                except: pass
            if len(items) == 0:
                items = result
        except:
            return

        try:
            q = dict(urlparse.parse_qsl(urlparse.urlsplit(url).query))
            p = str(int(q['page']) + 1)
            if p == '5': raise Exception()
            q.update({'page': p})
            q = (urllib.urlencode(q)).replace('%2C', ',')
            next = url.replace('?' + urlparse.urlparse(url).query, '') + '?' + q
            next = next
        except:
            next = ''

        for item in items:
            try:
                title = item['title']
                title = re.sub('\s(|[(])(UK|US|AU|\d{4})(|[)])$', '', title)
                title = client.replaceHTMLCodes(title)

                year = item['year']
                year = re.sub('[^0-9]', '', str(year))

                if int(year) > int((self.datetime).strftime('%Y')): raise Exception()

                tmdb = item['ids']['tmdb']
                if tmdb == None or tmdb == '': tmdb = '0'
                tmdb = re.sub('[^0-9]', '', str(tmdb))

                tvrage = item['ids'].get('tvrage', '0')
                if tvrage == None or tvrage == '': tvrage = '0'
                tvrage = re.sub('[^0-9]', '', str(tvrage))

                imdb = item['ids']['imdb']
                if imdb == None or imdb == '': imdb = '0'
                else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                tvdb = item['ids']['tvdb']
                if tvdb == None or tvdb == '': tvdb = '0'
                tvdb = re.sub('[^0-9]', '', str(tvdb))

                poster = '0'
                try: poster = item['images']['poster']['medium']
                except: pass
                if poster == None or not '/posters/' in str(poster): poster = '0'
                if not poster == '0': poster = poster.rsplit('?', 1)[0]

                banner = poster
                try: banner = item['images']['banner']['full']
                except: pass
                if banner == None or not '/banners/' in str(banner): banner = '0'
                if not banner == '0': banner = banner.rsplit('?', 1)[0]

                fanart = '0'
                try: fanart = item['images']['fanart']['full']
                except: pass
                if fanart == None or not '/fanarts/' in str(fanart): fanart = '0'
                if not fanart == '0': fanart = fanart.rsplit('?', 1)[0]

                try: premiered = item['first_aired']
                except: premiered = '0'
                try: premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                except: premiered = '0'

                try: studio = item['network']
                except: studio = '0'
                if studio == None: studio = '0'

                try: genre = item['genres']
                except: genre = '0'
                genre = [i.title() for i in genre]
                if genre == []: genre = '0'
                genre = ' / '.join(genre)

                try: duration = str(item['runtime'])
                except: duration = '0'
                if duration == None: duration = '0'

                try: rating = str(item['rating'])
                except: rating = '0'
                if rating == None or rating == '0.0': rating = '0'

                try: votes = str(item['votes'])
                except: votes = '0'
                try: votes = str(format(int(votes),',d'))
                except: pass
                if votes == None: votes = '0'

                try: mpaa = item['certification']
                except: mpaa = '0'
                if mpaa == None: mpaa = '0'

                try: plot = item['overview']
                except: plot = '0'
                if plot == None: plot = '0'
                plot = client.replaceHTMLCodes(plot)

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'cast': '0', 'plot': plot, 'name': title, 'code': imdb, 'imdb': imdb, 'tmdb': tmdb, 'tvrage': tvrage, 'tvdb': tvdb, 'poster': poster, 'banner': banner, 'fanart': fanart, 'next': next})
            except:
                pass

        return self.list

    def trakt_user_list(self, url):
        try:
            result = trakt.getTrakt(url)
            items = json.loads(result)
        except:
            pass

        for item in items:
            try:
                name = item['name']
                name = client.replaceHTMLCodes(name)

                url = self.traktlist_link % item['ids']['slug']

                self.list.append({'name': name, 'url': url, 'context': url})
            except:
                pass

        return self.list

    def imdb_list(self, url, idx=True):
        # Legacy IMDB list parsing - kept for user IMDB lists only
        try:
            if url == self.imdbwatchlist_link:
                def imdb_watchlist_id(url):
                    return re.compile('/export[?]list_id=(ls\d*)').findall(client.request(url))[0]
                url = cache.get(imdb_watchlist_id, 8640, url)
                url = self.imdblist_link % url

            result = str(client.request(url))

            try:
                if idx == True: raise Exception()
                pages = client.parseDOM(result, 'div', attrs = {'class': 'desc'})[0]
                pages = re.compile('Page \d+? of (\d*)').findall(pages)[0]
                for i in range(1, int(pages)):
                    u = url.replace('&start=1', '&start=%s' % str(i*100+1))
                    result += str(client.request(u))
            except:
                pass

            result = result.replace('\n','')
            if isinstance(result, bytes):
                result = result.decode('iso-8859-1')
            items = client.parseDOM(result, 'div', attrs = {'class': 'lister-item mode-advanced'})
            items += client.parseDOM(result, 'div', attrs = {'class': 'list_item.+?'})
        except:
            return

        try:
            next = client.parseDOM(result, 'a', ret='href', attrs = {'class': 'lister-page-next.+?'})

            if len(next) == 0:
                next = client.parseDOM(result, 'div', attrs = {'class': 'pagination'})[-1]
                name = client.parseDOM(next, 'a')[-1]
                if 'laquo' in name: raise Exception()
                next = client.parseDOM(next, 'a', ret='href')[-1]
                next = '%s%s' % (url.split('?', 1)[0], next)
                next = client.replaceHTMLCodes(next)
            else:
                next = url.replace(urlparse.urlparse(url).query, urlparse.urlparse(next[0]).query)
                next = client.replaceHTMLCodes(next)
        except:
            next = ''

        for item in items:
            try:
                try: title = client.parseDOM(item, 'a')[1]
                except: pass
                try: title = client.parseDOM(item, 'a', attrs = {'onclick': '.+?'})[-1]
                except: pass
                title = client.replaceHTMLCodes(title)

                year = client.parseDOM(item, 'span', attrs = {'class': 'lister-item-year.+?'})
                year += client.parseDOM(item, 'span', attrs = {'class': 'year_type'})
                year = re.findall('(\d{4})', year[0])[0]

                if int(year) > int((self.datetime).strftime('%Y')): raise Exception()

                imdb = client.parseDOM(item, 'a', ret='href')[0]
                imdb = 'tt' + re.sub('[^0-9]', '', imdb.rsplit('tt', 1)[-1])

                try: poster = client.parseDOM(item, 'img', ret='loadlate')[0]
                except: poster = '0'
                poster = re.sub('(?:_SX\d+?|)(?:_SY\d+?|)(?:_UX\d+?|)_CR\d+?,\d+?,\d+?,\d*','_SX500', poster)
                poster = client.replaceHTMLCodes(poster)

                plot = '0'
                try: plot = client.parseDOM(item, 'div', attrs = {'class': 'item_description'})[0]
                except: pass
                plot = plot.rsplit('<span>', 1)[0].strip()
                if plot == '': plot = '0'
                plot = client.replaceHTMLCodes(plot)

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': '0', 'studio': '0', 'genre': '0', 'duration': '0', 'rating': '0', 'votes': '0', 'mpaa': '0', 'cast': '0', 'plot': plot, 'name': title, 'code': imdb, 'imdb': imdb, 'tmdb': '0', 'tvdb': '0', 'tvrage': '0', 'poster': poster, 'banner': '0', 'fanart': '0'})
            except:
                pass

        return self.list

    def imdb_user_list(self, url):
        try:
            result = client.request(url)
            if isinstance(result, bytes):
                result = result.decode('iso-8859-1')
            items = client.parseDOM(result, 'div', attrs = {'class': 'list_name'})
        except:
            pass

        for item in items:
            try:
                name = client.parseDOM(item, 'a')[0]
                name = client.replaceHTMLCodes(name)

                url = client.parseDOM(item, 'a', ret='href')[0]
                url = url.split('/list/', 1)[-1].replace('/', '')
                url = self.imdblist_link % url
                url = client.replaceHTMLCodes(url)

                self.list.append({'name': name, 'url': url, 'context': url})
            except:
                pass

        self.list = sorted(self.list, key=lambda k: re.sub('(^the |^a )', '', k['name'].lower()))
        return self.list

    def tmdb_person_list(self, url):
        '''Parse TMDB person search results'''
        try:
            result = client.request(url)
            result = json.loads(result)
            items = result.get('results', [])
        except:
            return

        for item in items:
            try:
                name = item['name']
                name = client.replaceHTMLCodes(name)

                person_id = str(item['id'])
                url = TMDB_BASE + '/discover/tv?api_key=' + TMDB_API_KEY + '&with_people=%s&sort_by=first_air_date.desc&page=1' % person_id

                image = '0'
                if item.get('profile_path'):
                    image = self.tmdb_poster + item['profile_path']

                self.list.append({'name': name, 'url': url, 'image': image})
            except:
                pass

        return self.list

    def tvmaze_list(self, url):
        try:
            result = client.request(url)
            result = client.parseDOM(result, 'section', attrs={'id': 'this-seasons-shows'})

            items = client.parseDOM(result, 'li')
            items = [client.parseDOM(i, 'a', ret='href') for i in items]
            items = [i[0] for i in items if len(i) > 0]
            items = [re.findall('/(\d+)/', i) for i in items]
            items = [i[0] for i in items if len(i) > 0]
            items = items[:50]
        except:
            return

        def items_list(i):
            try:
                url = self.tvmaze_info_link % i

                item = client.request(url)
                item = json.loads(item)

                title = item['name']
                title = re.sub('\s(|[(])(UK|US|AU|\d{4})(|[)])$', '', title)
                title = client.replaceHTMLCodes(title)

                year = item['premiered']
                year = re.findall('(\d{4})', year)[0]

                if int(year) > int((self.datetime).strftime('%Y')): raise Exception()

                imdb = item['externals']['imdb']
                if imdb == None or imdb == '':
                    imdb = '0'
                else:
                    imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                tvdb = item['externals']['thetvdb']
                tvdb = re.sub('[^0-9]', '', str(tvdb))

                if tvdb == None or tvdb == '': raise Exception()

                try:
                    poster = item['image']['original']
                except:
                    poster = '0'
                if poster == None or poster == '': poster = '0'

                premiered = item['premiered']
                try:
                    premiered = re.findall('(\d{4}-\d{2}-\d{2})', premiered)[0]
                except:
                    premiered = '0'

                try:
                    studio = item['network']['name']
                except:
                    studio = '0'
                if studio == None: studio = '0'

                try:
                    genre = item['genres']
                except:
                    genre = '0'
                genre = [i.title() for i in genre]
                if genre == []: genre = '0'
                genre = ' / '.join(genre)

                try:
                    duration = str(item['runtime'])
                except:
                    duration = '0'
                if duration == None: duration = '0'

                try:
                    rating = str(item['rating']['average'])
                except:
                    rating = '0'
                if rating == None or rating == '0.0': rating = '0'

                try:
                    plot = item['summary']
                except:
                    plot = '0'
                if plot == None: plot = '0'
                plot = re.sub('<.+?>|</.+?>', '', plot)
                plot = client.replaceHTMLCodes(plot)

                try:
                    content = item['type'].lower()
                except:
                    content = '0'
                if content == None or content == '': content = '0'

                self.list.append(
                    {'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered, 'studio': studio,
                     'genre': genre, 'duration': duration, 'rating': rating, 'votes': '0', 'mpaa': '0', 'cast': '0',
                     'director':'0','writer':'0', 'plot': plot, 'code': imdb, 'imdb': imdb, 'tmdb': '0', 'tvdb': tvdb, 'tvrage':'0',
                     'poster': poster, 'banner': '0', 'fanart': '0', 'content': content,'next': '','name': title})

            except:
                pass

        try:
            threads = []
            for i in items: threads.append(workers.Thread(items_list, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

            filter = [i for i in self.list if i['content'] == 'scripted']
            filter += [i for i in self.list if not i['content'] == 'scripted']
            self.list = filter

            return self.list
        except:
            return

    def worker(self):
        self.meta = []
        total = len(self.list)

        for i in range(0, total): self.list[i].update({'metacache': False})
        self.list = metacache.fetch(self.list, self.info_lang)

        for r in range(0, total, 20):
            threads = []
            for i in range(r, r+20):
                if i <= total: threads.append(workers.Thread(self.super_info, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

        if len(self.meta) > 0: metacache.insert(self.meta)

        self.list = [i for i in self.list if not i['tvdb'] == '0']



    def super_info(self, i):
        try:
            if self.list[i]['metacache'] == True: raise Exception()

            try: imdb = self.list[i]['imdb']
            except: imdb = '0'
            try: tmdb = self.list[i]['tmdb']
            except: tmdb = '0'
            try: tvdb = self.list[i]['tvdb']
            except: tvdb = '0'
            try: tvrage = self.list[i]['tvrage']
            except: tvrage = '0'

            # Try to get TVDB ID from IMDB if missing
            if tvdb == '0' and not imdb == '0':
                try:
                    url = self.tvdb_by_imdb % imdb
                    result = client.request(url, timeout='10')
                    try: tvdb = client.parseDOM(result, 'seriesid')[0]
                    except: tvdb = '0'
                    try:
                        name = client.parseDOM(result, 'SeriesName')[0]
                        dupe = re.compile('[***]Duplicate (\d*)[***]').findall(name)
                        if len(dupe) > 0: tvdb = str(dupe[0])
                    except: pass
                    if tvdb == '': tvdb = '0'
                    self.list[i].update({'tvdb': tvdb})
                except: pass

            # Try TMDB for metadata enrichment
            tmdb_item = None
            if not tmdb == '0':
                try:
                    url = self.tmdb_tv_info_link % tmdb
                    tmdb_raw = client.request(url, timeout='10')
                    tmdb_item = json.loads(tmdb_raw)
                except: pass
            elif not imdb == '0':
                try:
                    find_url = self.tmdb_find_link % imdb
                    find_result = client.request(find_url, timeout='10')
                    find_result = json.loads(find_result)
                    tv_results = find_result.get('tv_results', [])
                    if tv_results:
                        tmdb = str(tv_results[0]['id'])
                        self.list[i].update({'tmdb': tmdb})
                        url = self.tmdb_tv_info_link % tmdb
                        tmdb_raw = client.request(url, timeout='10')
                        tmdb_item = json.loads(tmdb_raw)
                except: pass

            if tmdb_item:
                # Extract metadata from TMDB
                title = tmdb_item.get('name', '')
                if title:
                    title = client.replaceHTMLCodes(title)
                    self.list[i].update({'title': title})

                # Get IMDB from external_ids if missing
                if imdb == '0':
                    ext_ids = tmdb_item.get('external_ids', {})
                    imdb = ext_ids.get('imdb_id', '0')
                    if imdb: self.list[i].update({'imdb': imdb})
                    tvdb_ext = ext_ids.get('tvdb_id', '0')
                    if tvdb_ext and tvdb == '0':
                        tvdb = str(tvdb_ext)
                        self.list[i].update({'tvdb': tvdb})

                year = str(tmdb_item.get('first_air_date', '0000'))[:4]
                if year and not year == '0000':
                    self.list[i].update({'year': year})

                poster = '0'
                if tmdb_item.get('poster_path'):
                    poster = self.tmdb_poster + tmdb_item['poster_path']
                    self.list[i].update({'poster': poster})

                banner = '0'

                fanart = '0'
                if tmdb_item.get('backdrop_path'):
                    fanart = self.tmdb_fanart + tmdb_item['backdrop_path']
                    self.list[i].update({'fanart': fanart})

                if not poster == '0' and self.list[i].get('banner', '0') == '0':
                    self.list[i].update({'banner': poster})

                premiered = tmdb_item.get('first_air_date', '0')
                if premiered:
                    self.list[i].update({'premiered': premiered})

                try:
                    studio = tmdb_item.get('networks', [{}])[0].get('name', '0')
                    if studio: self.list[i].update({'studio': studio})
                except: pass

                try:
                    genre_list = tmdb_item.get('genres', [])
                    if genre_list:
                        genre = ' / '.join([g['name'] for g in genre_list])
                        self.list[i].update({'genre': genre})
                except: pass

                try:
                    duration = str(tmdb_item.get('episode_run_time', [0])[0])
                    if duration and not duration == '0':
                        self.list[i].update({'duration': duration})
                except: pass

                rating = str(tmdb_item.get('vote_average', 0))
                if rating and not rating == '0' and not rating == '0.0':
                    self.list[i].update({'rating': rating})

                votes = str(tmdb_item.get('vote_count', 0))
                try: votes = str(format(int(votes),',d'))
                except: pass
                if votes and not votes == '0':
                    self.list[i].update({'votes': votes})

                # Cast from credits
                credits = tmdb_item.get('credits', {})
                try:
                    cast_list = credits.get('cast', [])
                    if cast_list:
                        cast = [(c['name'], c.get('character', '')) for c in cast_list[:10]]
                        self.list[i].update({'cast': cast})
                except: pass

                plot = tmdb_item.get('overview', '')
                if plot:
                    plot = client.replaceHTMLCodes(plot)
                    self.list[i].update({'plot': plot})

            else:
                # Fallback: try TVDB for basic info
                if not tvdb == '0':
                    try:
                        url = self.tvdb_info_link % tvdb
                        item2 = client.request(url, timeout='10')

                        if imdb == '0':
                            try: imdb = client.parseDOM(item2, 'IMDB_ID')[0]
                            except: pass
                            if imdb == '': imdb = '0'
                            self.list[i].update({'imdb': imdb})

                        try:
                            title = client.parseDOM(item2, 'SeriesName')[0]
                            if title: self.list[i].update({'title': client.replaceHTMLCodes(title)})
                        except: pass

                        try:
                            poster_path = client.parseDOM(item2, 'poster')[0]
                            if poster_path:
                                poster = self.tvdb_image + poster_path
                                self.list[i].update({'poster': poster})
                        except: pass

                        try:
                            banner_path = client.parseDOM(item2, 'banner')[0]
                            if banner_path:
                                banner = self.tvdb_image + banner_path
                                self.list[i].update({'banner': banner})
                        except: pass

                        try:
                            fanart_path = client.parseDOM(item2, 'fanart')[0]
                            if fanart_path:
                                fanart = self.tvdb_image + fanart_path
                                self.list[i].update({'fanart': fanart})
                        except: pass

                        try:
                            plot = client.parseDOM(item2, 'Overview')[0]
                            if plot: self.list[i].update({'plot': client.replaceHTMLCodes(plot)})
                        except: pass

                        try:
                            genre = client.parseDOM(item2, 'Genre')[0]
                            genre = [x for x in genre.split('|') if not x == '']
                            genre = ' / '.join(genre)
                            if genre: self.list[i].update({'genre': genre})
                        except: pass
                    except: pass

            # Non-English translation
            if not self.info_lang == 'en' and not imdb == '0':
                try:
                    url = self.trakt_lang_link % (imdb, self.info_lang)
                    lang_item = trakt.getTrakt(url)
                    lang_item = json.loads(lang_item)[0]

                    t = lang_item.get('title')
                    if t: self.list[i].update({'title': t})

                    t = lang_item.get('overview')
                    if t: self.list[i].update({'plot': t})
                except: pass

            # Build meta cache entry
            poster = self.list[i].get('poster', '0')
            banner = self.list[i].get('banner', '0')
            fanart = self.list[i].get('fanart', '0')
            title = self.list[i].get('title', '0')
            year = self.list[i].get('year', '0')
            genre = self.list[i].get('genre', '0')
            duration = self.list[i].get('duration', '0')
            rating = self.list[i].get('rating', '0')
            votes = self.list[i].get('votes', '0')
            mpaa = self.list[i].get('mpaa', '0')
            cast = self.list[i].get('cast', '0')
            plot = self.list[i].get('plot', '0')
            premiered = self.list[i].get('premiered', '0')
            studio = self.list[i].get('studio', '0')

            self.meta.append({'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'lang': self.info_lang, 'item': {'title': title, 'year': year, 'code': imdb, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'banner': banner, 'fanart': fanart, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'cast': cast, 'plot': plot}})

        except:
            pass


    def tvshowDirectory(self, items):
        if items == None or len(items) == 0: return

        isFolder = True if control.setting('autoplay') == 'false' and control.setting('host_select') == '1' else False
        isFolder = False if control.window.getProperty('PseudoTVRunning') == 'True' else isFolder

        traktMode = False if trakt.getTraktCredentials() == False else True

        indicators = playcount.getTVShowIndicators(refresh=True) if action == 'tvshows' else playcount.getTVShowIndicators()

        watchedMenu = control.lang(30234) if trakt.getTraktIndicatorsInfo() == True else control.lang(30234)

        unwatchedMenu = control.lang(30235) if trakt.getTraktIndicatorsInfo() == True else control.lang(30235)


        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()
        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')
        sysaddon = sys.argv[0]

        try:
            favitems = favourites.getFavourites('tvshows')
            favitems = [i[0] for i in favitems]
        except:
            pass

        for i in items:
            try:
                label = i['title']
                systitle = sysname = urllib.quote_plus(i['originaltitle'])
                sysimage = urllib.quote_plus(i['poster'])
                imdb, tmdb, tvdb, tvrage, year = i['imdb'], i['tmdb'], i['tvdb'], i.get('tvrage', '0'), i['year']

                poster, banner, fanart = i['poster'], i['banner'], i['fanart']
                if poster == '0': poster = addonPoster
                if banner == '0' and poster == '0': banner = addonBanner
                elif banner == '0': banner = poster


                meta = dict((k,v) for k, v in i.items() if not v == '0')
                meta.update({'trailer': '%s?action=trailer&name=%s' % (sysaddon, sysname)})
                if i['duration'] == '0': meta.update({'duration': '60'})
                try: meta.update({'duration': str(int(meta['duration']) * 60)})
                except: pass
                sysmeta = urllib.quote_plus(json.dumps(meta))

                try:
                    overlay = int(playcount.getTVShowOverlay(indicators, tvdb))
                    if overlay == 7: meta.update({'playcount': 1, 'overlay': 7})
                    else: meta.update({'playcount': 0, 'overlay': 6})
                except:
                    pass


                url = '%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&tvrage=%s' % (sysaddon, systitle, year, imdb, tmdb, tvdb, tvrage)


                cm = []

                if isFolder == False:
                    cm.append((control.lang(30232), 'RunPlugin(%s?action=queueItem)' % sysaddon))

                cm.append((control.lang(30233), 'Action(Info)'))

                if not action == 'tvSearch':
                    cm.append((watchedMenu, 'RunPlugin(%s?action=tvPlaycount&name=%s&imdb=%s&tvdb=%s&query=7)' % (
                    sysaddon, systitle, imdb, tvdb)))

                    cm.append((unwatchedMenu, 'RunPlugin(%s?action=tvPlaycount&name=%s&imdb=%s&tvdb=%s&query=6)' % (
                    sysaddon, systitle, imdb, tvdb)))

                if traktMode == True:
                    cm.append((control.lang(30236), 'RunPlugin(%s?action=traktManager&name=%s&tvdb=%s&content=tvshow)' % (sysaddon, sysname, tvdb)))

                if action == 'tvFavourites':
                    cm.append((control.lang(30238), 'RunPlugin(%s?action=deleteFavourite&meta=%s&content=tvshows)' % (sysaddon, sysmeta)))
                elif action.startswith('tvSearch'):
                    cm.append((control.lang(30237), 'RunPlugin(%s?action=addFavourite&meta=%s&query=0&content=tvshows)' % (sysaddon, sysmeta)))
                else:
                    if not imdb in favitems and not tvdb in favitems: cm.append((control.lang(30237), 'RunPlugin(%s?action=addFavourite&meta=%s&content=tvshows)' % (sysaddon, sysmeta)))
                    else: cm.append((control.lang(30238), 'RunPlugin(%s?action=deleteFavourite&meta=%s&content=tvshows)' % (sysaddon, sysmeta)))

                cm.append((control.lang(30239), 'RunPlugin(%s?action=tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&tvrage=%s)' % (sysaddon, systitle, year, imdb, tmdb, tvdb, tvrage)))

                cm.append((control.lang(30240), 'RunPlugin(%s?action=addView&content=tvshows)' % sysaddon))


                item = control.item(label=label)

                try: item.setArt({'poster': poster, 'tvshow.poster': poster, 'season.poster': poster, 'banner': banner, 'tvshow.banner': banner, 'season.banner': banner})
                except: pass

                if settingFanart == 'true' and not fanart == '0':
                    item.setProperty('Fanart_Image', fanart)
                elif not addonFanart == None:
                    item.setProperty('Fanart_Image', addonFanart)

                item.setInfo(type='Video', infoLabels = meta)
                item.setProperty('Video', 'true')
                item.addContextMenuItems(cm, replaceItems=True)
                control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=True)
            except:
                pass

        try:
            url = items[0]['next']
            if url == '': raise Exception()
            url = '%s?action=tvshows&url=%s' % (sysaddon, urllib.quote_plus(url))
            addonNext = control.addonNext()
            item = control.item(label=control.lang(30241))
            item.addContextMenuItems([], replaceItems=False)
            if not addonFanart == None: item.setProperty('Fanart_Image', addonFanart)
            control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=True)
        except:
            pass


        control.content(int(sys.argv[1]), 'tvshows')
        control.directory(int(sys.argv[1]), cacheToDisc=True)
        views.setView('tvshows', {'skin.confluence': 500})


    def addDirectory(self, items):
        if items == None or len(items) == 0: return

        sysaddon = sys.argv[0]
        addonFanart = control.addonFanart()
        addonThumb = control.addonThumb()
        artPath = control.artPath()

        for i in items:
            try:
                try: name = control.lang(i['name'])
                except: name = i['name']

                if i['image'].startswith('http://') or i['image'].startswith('https://'): thumb = i['image']
                elif not artPath == None: thumb = os.path.join(artPath, i['image'])
                else: thumb = addonThumb

                url = '%s?action=%s' % (sysaddon, i['action'])
                try: url += '&url=%s' % urllib.quote_plus(i['url'])
                except: pass

                cm = []

                try: cm.append((control.lang(30239), 'RunPlugin(%s?action=tvshowsToLibrary&url=%s)' % (sysaddon, urllib.quote_plus(i['context']))))
                except: pass

                item = control.item(label=name)
                item.addContextMenuItems(cm, replaceItems=False)
                if not addonFanart == None: item.setProperty('Fanart_Image', addonFanart)
                control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=True)
            except:
                pass

        control.directory(int(sys.argv[1]), cacheToDisc=True)
