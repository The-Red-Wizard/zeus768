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

import os,sys,re,json,datetime
import base64

# Python 2/3 compatibility
try:
    from urllib import quote_plus, urlencode
    from urlparse import urlparse, parse_qsl, urlsplit
    import urllib
    import urlparse
except ImportError:
    from urllib.parse import quote_plus, urlencode, urlparse, parse_qsl, urlsplit
    import urllib.parse as urllib
    import urllib.parse as urlparse

try: action = dict(parse_qsl(sys.argv[2].replace('?','')))['action']
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


class movies:
    def __init__(self):
        self.list = []
        self.en_headers = {'Accept-Language': 'en-US'}

        self.trakt_link = 'https://api.trakt.tv'
        self.tmdb_image = 'https://image.tmdb.org/t/p/original'
        self.tmdb_poster = 'https://image.tmdb.org/t/p/w500'
        self.tmdb_fanart = 'https://image.tmdb.org/t/p/w1280'
        self.fanarttv_key = control.fanarttv_key
        self.datetime = (datetime.datetime.utcnow() - datetime.timedelta(hours = 5))
        self.systime = (self.datetime).strftime('%Y%m%d%H%M%S%f')
        self.today_date = (self.datetime).strftime('%Y-%m-%d')
        self.month_date = (self.datetime - datetime.timedelta(days = 30)).strftime('%Y-%m-%d')
        self.month2_date = (self.datetime - datetime.timedelta(days = 60)).strftime('%Y-%m-%d')
        self.year_date = (self.datetime - datetime.timedelta(days = 365)).strftime('%Y-%m-%d')
        self.year_date10 = (self.datetime - datetime.timedelta(days = 3650)).strftime('%Y-%m-%d')
        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb_user').replace('ur', '')
        self.info_lang = control.info_lang or 'en'

        # All category links now use Trakt API
        self.popular_link = 'https://api.trakt.tv/movies/popular?limit=20&page=1'
        self.featured_link = 'https://api.trakt.tv/movies/watched/monthly?limit=20&page=1'
        self.boxoffice_link = 'https://api.trakt.tv/movies/boxoffice'
        self.oscars_link = 'https://api.trakt.tv/movies/watched/all?limit=20&page=1'
        self.trending_link = 'https://api.trakt.tv/movies/trending?limit=20&page=1'
        self.views_link = 'https://api.trakt.tv/movies/played/all?limit=20&page=1'
        self.theaters_link = 'https://api.trakt.tv/movies/popular?years=%s&limit=20&page=1' % (self.datetime).strftime('%Y')
        self.added_link = 'https://api.trakt.tv/movies/watched/weekly?limit=20&page=1'

        self.search_link = 'https://api.trakt.tv/search?type=movie&query=%s&limit=20'

        # Genre and year links use Trakt filters
        self.genre_link = 'https://api.trakt.tv/movies/popular?genres=%s&limit=20&page=1'
        self.year_link = 'https://api.trakt.tv/movies/popular?years=%s&limit=20&page=1'

        # Person search via TMDB
        self.persons_link = TMDB_BASE + '/search/person?api_key=' + TMDB_API_KEY + '&query=%s&page=1'
        self.personlist_link = TMDB_BASE + '/person/popular?api_key=' + TMDB_API_KEY + '&page=1'
        self.person_link = TMDB_BASE + '/discover/movie?api_key=' + TMDB_API_KEY + '&with_people=%s&sort_by=release_date.desc&page=1'

        # Certification via TMDB
        self.certification_link = TMDB_BASE + '/discover/movie?api_key=' + TMDB_API_KEY + '&certification=%s&certification_country=US&primary_release_date.lte=%s&page=1' % ('%s', self.today_date)

        # Trakt user list links
        self.traktlists_link = 'https://api.trakt.tv/users/me/lists'
        self.traktlikedlists_link = 'https://api.trakt.tv/users/likes/lists?limit=1000000'
        self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items'
        self.traktcollection_link = 'https://api.trakt.tv/users/me/collection/movies'
        self.traktwatchlist_link = 'https://api.trakt.tv/users/me/watchlist/movies'
        self.traktfeatured_link = 'https://api.trakt.tv/recommendations/movies?limit=40'
        self.trakthistory_link = 'https://api.trakt.tv/users/me/history/movies?limit=40&page=1'

        # IMDB user list links (kept for user's IMDB lists if configured)
        self.imdb_link = 'http://www.imdb.com'
        self.imdblists_link = 'http://www.imdb.com/user/ur%s/lists?tab=all&sort=modified:desc&filter=titles' % self.imdb_user
        self.imdblist_link = 'http://www.imdb.com/list/%s/?view=detail&sort=title:asc&title_type=feature,short,tv_movie,tv_special,video,documentary,game&start=1'
        self.imdbwatchlist_link = 'http://www.imdb.com/user/ur%s/watchlist' % self.imdb_user

        self.trakt_lang_link = 'https://api.trakt.tv/movies/%s/translations/%s'

        # TMDB info link for metadata enrichment (replaces OMDB)
        self.tmdb_info_link = TMDB_BASE + '/movie/%s?api_key=' + TMDB_API_KEY + '&append_to_response=credits'
        self.tmdb_find_link = TMDB_BASE + '/find/%s?api_key=' + TMDB_API_KEY + '&external_source=imdb_id'

    def get(self, url, idx=True):
        try:
            try: url = getattr(self, url + '_link')
            except: pass

            try: u = urlparse.urlparse(url).netloc.lower()
            except: pass

            if u in self.trakt_link and '/users/' in url:
                try:
                    if url == self.trakthistory_link: raise Exception()
                    if not '/users/me/' in url: raise Exception()
                    if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user): raise Exception()
                    self.list = cache.get(self.trakt_list, 72, url, self.trakt_user)
                except:
                    self.list = cache.get(self.trakt_list, 2, url, self.trakt_user)

                if '/users/me/' in url:
                    self.list = sorted(self.list, key=lambda k: re.sub('(^the |^a )', '', k['title'].lower()))

                if idx == True: self.worker()

            elif u in self.trakt_link:
                self.list = cache.get(self.trakt_list, 24, url, self.trakt_user)
                if idx == True: self.worker()

            elif 'api.themoviedb.org' in url:
                self.list = cache.get(self.tmdb_list, 24, url)
                if idx == True: self.worker()

            elif u in self.imdb_link and ('/user/' in url or '/list/' in url):
                self.list = cache.get(self.imdb_list, 2, url, idx)
                if idx == True: self.worker()

            elif u in self.imdb_link:
                self.list = cache.get(self.imdb_list, 24, url)
                if idx == True: self.worker()

            if idx == True:
                if self.list is None:
                    self.list = []
                self.movieDirectory(self.list)
            return self.list
        except Exception as e:
            control.log("movies get e:%s" % e)
            pass


    def widget(self):
        setting = control.setting('movie_widget')

        if setting == '2':
            self.get(self.featured_link)
        elif setting == '3':
            self.get(self.trending_link)
        else:
            self.get(self.added_link)


    def favourites(self):
        try:
            items = favourites.getFavourites('movies')
            self.list = [i[1] for i in items]

            for i in self.list:
                if not 'name' in i: i['name'] = '%s (%s)' % (i['title'], i['year'])
                try: i['title'] = i['title']
                except: pass
                try: i['originaltitle'] = i['originaltitle']
                except: pass
                try: i['name'] = i['name']
                except: pass
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
            self.movieDirectory(self.list)
        except:
            return


    def search(self, query=None):
            if query == None:
                t = control.lang(30201)
                k = control.keyboard('', t) ; k.doModal()
                self.query = k.getText() if k.isConfirmed() else None
            else:
                self.query = query

            if (self.query == None or self.query == ''): return

            url = self.search_link % (urllib.quote_plus(self.query))
            self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)

            self.worker()
            self.movieDirectory(self.list)
            return self.list


    def person(self, query=None):
        try:
            if query == None:
                t = control.lang(30201)
                k = control.keyboard('', t) ; k.doModal()
                self.query = k.getText() if k.isConfirmed() else None
            else:
                self.query = query

            if (self.query == None or self.query == ''): return

            url = self.persons_link % urllib.quote_plus(self.query)
            self.list = cache.get(self.tmdb_person_list, 0, url)

            if self.list is None:
                self.list = []
            for i in range(0, len(self.list)): self.list[i].update({'action': 'movies'})
            self.addDirectory(self.list)
            return self.list
        except:
            return


    def genres(self):
        genres = [
        ('Action', 'action'),
        ('Adventure', 'adventure'),
        ('Animation', 'animation'),
        ('Comedy', 'comedy'),
        ('Crime', 'crime'),
        ('Documentary', 'documentary'),
        ('Drama', 'drama'),
        ('Family', 'family'),
        ('Fantasy', 'fantasy'),
        ('History', 'history'),
        ('Horror', 'horror'),
        ('Music', 'music'),
        ('Musical', 'musical'),
        ('Mystery', 'mystery'),
        ('Romance', 'romance'),
        ('Science Fiction', 'science-fiction'),
        ('Superhero', 'superhero'),
        ('Thriller', 'thriller'),
        ('War', 'war'),
        ('Western', 'western')
        ]

        for i in genres: self.list.append({'name': cleangenre.lang(i[0], self.info_lang), 'url': self.genre_link % i[1], 'image': 'genres.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def certifications(self):
        try:
            certs = [
                ('G', 'G'),
                ('PG', 'PG'),
                ('PG-13', 'PG-13'),
                ('R', 'R'),
                ('NC-17', 'NC-17'),
            ]
            for c in certs:
                self.list.append({'name': c[0], 'url': self.certification_link % (c[1], self.today_date), 'image': 'movieCertificates.jpg', 'action': 'movies'})
            self.addDirectory(self.list)
            return self.list
        except:
            return

    def years(self):
        year = (self.datetime.strftime('%Y'))

        for i in range(int(year)-0, int(year)-50, -1): self.list.append({'name': str(i), 'url': self.year_link % str(i), 'image': 'movieYears.jpg', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list

    def persons(self):
        self.list = cache.get(self.tmdb_person_list, 24, self.personlist_link)
        if self.list is None:
            self.list = []
        if len(self.list) > 0:
            for i in range(0, len(self.list)): self.list[i].update({'action': 'movies'})
        self.addDirectory(self.list)
        return self.list

    def userlists(self):
        try:
            userlists = []
            if trakt.getTraktCredentialsInfo() == False: raise Exception()
            activity = trakt.getActivity()
        except:
            pass
        try:
            if trakt.getTraktCredentialsInfo() == False: raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlists_link,
                                            self.trakt_user): raise Exception()
                userlists += cache.get(self.trakt_user_list, 720, self.traktlists_link, self.trakt_user)
            except:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlists_link, self.trakt_user)
        except:
            pass
        try:
            self.list = []
            if self.imdb_user == '': raise Exception()
            userlists += cache.get(self.imdb_user_list, 0, self.imdblists_link)
        except:
            pass
        try:
            self.list = []
            if trakt.getTraktCredentialsInfo() == False: raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlikedlists_link,
                                            self.trakt_user): raise Exception()
                userlists += cache.get(self.trakt_user_list, 720, self.traktlikedlists_link, self.trakt_user)
            except:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlikedlists_link, self.trakt_user)
        except:
            pass

        self.list = userlists
        if self.list is None:
            self.list = []
        for i in range(0, len(self.list)): self.list[i].update({'image': 'userlists.png', 'action': 'movies'})
        self.addDirectory(self.list)

        return self.list

    def trakt_list(self, url, user):
        try:
            q = dict(urlparse.parse_qsl(urlparse.urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urllib.urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urlparse.urlparse(url).query, '') + '?' + q

            result = trakt.getTrakt(u)
            result = json.loads(result)

            items = []
            for i in result:
                try: items.append(i['movie'])
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
                title = client.replaceHTMLCodes(title)

                year = item['year']
                year = re.sub('[^0-9]', '', str(year))

                if int(year) > int((self.datetime).strftime('%Y')): raise Exception()

                imdb = item['ids']['imdb']
                if imdb == None or imdb == '': raise Exception()
                imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                tmdb = item['ids'].get('tmdb', '0')
                if tmdb == None or tmdb == '': tmdb = '0'
                else: tmdb = str(tmdb)

                # Use TMDB for poster/fanart if tmdb id available
                poster = '0'
                fanart = '0'
                banner = '0'
                try:
                    poster_path = item.get('images', {}).get('poster', {}).get('medium', '')
                    if poster_path and '/posters/' in poster_path:
                        poster = poster_path.rsplit('?', 1)[0]
                except: pass

                try:
                    premiered = item['released']
                    premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                except: premiered = '0'

                try:
                    genre = item['genres']
                    genre = [i.title() for i in genre]
                except: genre = '0'
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

                plot = item.get('overview', '0')
                if plot == None: plot = '0'
                plot = client.replaceHTMLCodes(plot)

                try: tagline = item.get('tagline', None)
                except: tagline = None
                if tagline == None and not plot == '0': tagline = re.compile('[.!?][\s]{1,2}(?=[A-Z])').split(plot)[0]
                elif tagline == None: tagline = '0'
                tagline = client.replaceHTMLCodes(tagline)

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered, 'studio': '0', 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'director': '0', 'writer': '0', 'cast': '0', 'plot': plot, 'tagline': tagline, 'code': imdb, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0', 'tvrage': '0', 'poster': poster, 'banner': banner, 'fanart': fanart, 'next': next})
            except:
                pass

        return self.list

    def trakt_user_list(self, url, user):
        try:
            result = trakt.getTrakt(url)
            items = json.loads(result)
        except:
            pass

        for item in items:
            try:
                try:  name = item['list']['name']
                except:  name = item['name']
                name = client.replaceHTMLCodes(name)

                try:  url = (trakt.slug(item['list']['user']['username']), item['list']['ids']['slug'])
                except: url = ('me', item['ids']['slug'])
                url = self.traktlist_link % url

                self.list.append({'name': name, 'url': url, 'context': url})
            except:
                pass

        self.list = sorted(self.list, key=lambda k: re.sub('(^the |^a )', '', k['name'].lower()))
        return self.list

    def imdb_list(self, url, idx=True):
        # Legacy IMDB list parsing - kept for user IMDB lists only
        try:
            if url == self.imdbwatchlist_link:
                def imdb_watchlist_id(url):
                    return re.compile('/export[?]list_id=(ls\d*)').findall(client.request(url))[0]
                url = cache.get(imdb_watchlist_id, 8640, url)
                url = self.imdblist_link % url

            result = str(client.request(url,headers=self.en_headers))

            try:
                if idx == True: raise Exception()
                pages = client.parseDOM(result, 'div', attrs = {'class': 'desc'})[0]
                pages = re.compile('Page \d+? of (\d*)').findall(pages)[0]
                for i in range(1, int(pages)):
                    u = url.replace('&start=1', '&start=%s' % str(i*100+1))
                    result += str(client.request(u, headers=self.en_headers))
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
                next = client.parseDOM(result, 'div', attrs = {'class': 'pagination'})[0]
                next = zip(client.parseDOM(next, 'a', ret='href'), client.parseDOM(next, 'a'))
                next = [i[0] for i in next if 'Next' in i[1]]

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
                imdb = re.findall('(tt\d*)', imdb)[0]

                try: poster = client.parseDOM(item, 'img', ret='loadlate')[0]
                except: poster = '0'
                poster = re.sub('(?:_SX\d+?|)(?:_SY\d+?|)(?:_UX\d+?|)_CR\d+?,\d+?,\d+?,\d*','_SX500', poster)
                poster = client.replaceHTMLCodes(poster)

                try: genre = client.parseDOM(item, 'span', attrs = {'class': 'genre'})[0]
                except: genre = '0'
                genre = ' / '.join([i.strip() for i in genre.split(',')])
                if genre == '': genre = '0'
                genre = client.replaceHTMLCodes(genre)

                try: duration = re.findall('(\d+?) min(?:s|)', item)[-1]
                except: duration = '0'

                rating = '0'
                try: rating = client.parseDOM(item, 'span', attrs = {'class': 'rating-rating'})[0]
                except: pass
                try: rating = client.parseDOM(rating, 'span', attrs = {'class': 'value'})[0]
                except: rating = '0'
                try: rating = client.parseDOM(item, 'div', ret='data-value', attrs = {'class': '.*?imdb-rating'})[0]
                except: pass
                if rating == '' or rating == '-': rating = '0'
                rating = client.replaceHTMLCodes(rating)

                try: votes = client.parseDOM(item, 'div', ret='title', attrs = {'class': '.*?rating-list'})[0]
                except: votes = '0'
                try: votes = re.findall('\((.+?) vote(?:s|)\)', votes)[0]
                except: votes = '0'
                if votes == '': votes = '0'
                votes = client.replaceHTMLCodes(votes)

                try: mpaa = client.parseDOM(item, 'span', attrs = {'class': 'certificate'})[0]
                except: mpaa = '0'
                if mpaa == '' or mpaa == 'NOT_RATED': mpaa = '0'
                mpaa = mpaa.replace('_', '-')
                mpaa = client.replaceHTMLCodes(mpaa)

                try: director = re.findall('Director(?:s|):(.+?)(?:\||</div>)', item)[0]
                except: director = '0'
                director = client.parseDOM(director, 'a')
                director = ' / '.join(director)
                if director == '': director = '0'
                director = client.replaceHTMLCodes(director)

                try: cast = re.findall('Stars(?:s|):(.+?)(?:\||</div>)', item)[0]
                except: cast = '0'
                cast = client.replaceHTMLCodes(cast)
                cast = client.parseDOM(cast, 'a')
                if cast == []: cast = '0'

                plot = '0'
                try: plot = client.parseDOM(item, 'p', attrs = {'class': 'text-muted'})[0]
                except: pass
                try: plot = client.parseDOM(item, 'div', attrs = {'class': 'item_description'})[0]
                except: pass
                plot = plot.rsplit('<span>', 1)[0].strip()
                if plot == '': plot = '0'
                plot = client.replaceHTMLCodes(plot)

                tagline = re.compile('[.!?][\s]{1,2}(?=[A-Z])').split(plot)[0]

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': '0', 'studio': '0', 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'director': director, 'writer': '0', 'cast': cast, 'plot': plot, 'tagline': tagline, 'code': imdb, 'imdb': imdb, 'tmdb': '0', 'tvdb': '0', 'tvrage': '0', 'poster': poster, 'banner': '0', 'fanart': '0', 'next': next})
            except:
                pass

        return self.list

    def imdb_user_list(self, url):
        try:
            result = client.request(url, headers=self.en_headers)
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

    def tmdb_list(self, url):
        '''Parse TMDB API discover/search results into our standard list format'''
        try:
            result = client.request(url, headers=self.en_headers)
            result = json.loads(result)
            items = result.get('results', [])
        except:
            return

        try:
            page = result.get('page', 1)
            total_pages = result.get('total_pages', 1)
            if page < total_pages and page < 4:
                next_url = re.sub('page=\d+', 'page=%s' % str(page + 1), url)
                next = next_url
            else:
                next = ''
        except:
            next = ''

        for item in items:
            try:
                title = item['title']
                title = client.replaceHTMLCodes(title)

                year = item.get('release_date', '0000')[:4]
                if year == '' or year == '0000': year = '0'
                if int(year) > int((self.datetime).strftime('%Y')): raise Exception()

                tmdb_id = str(item['id'])
                imdb = '0'

                poster = '0'
                if item.get('poster_path'):
                    poster = self.tmdb_poster + item['poster_path']

                fanart = '0'
                if item.get('backdrop_path'):
                    fanart = self.tmdb_fanart + item['backdrop_path']

                rating = str(item.get('vote_average', '0'))
                votes = str(item.get('vote_count', '0'))
                try: votes = str(format(int(votes),',d'))
                except: pass

                plot = item.get('overview', '0')
                if not plot: plot = '0'
                plot = client.replaceHTMLCodes(plot)

                tagline = re.compile('[.!?][\s]{1,2}(?=[A-Z])').split(plot)[0] if not plot == '0' else '0'

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': item.get('release_date', '0'), 'studio': '0', 'genre': '0', 'duration': '0', 'rating': rating, 'votes': votes, 'mpaa': '0', 'director': '0', 'writer': '0', 'cast': '0', 'plot': plot, 'tagline': tagline, 'code': imdb, 'imdb': imdb, 'tmdb': tmdb_id, 'tvdb': '0', 'tvrage': '0', 'poster': poster, 'banner': '0', 'fanart': fanart, 'next': next})
            except:
                pass

        return self.list

    def tmdb_person_list(self, url):
        '''Parse TMDB person search/popular results'''
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
                url = self.person_link % person_id
                url = client.replaceHTMLCodes(url)

                image = '0'
                if item.get('profile_path'):
                    image = self.tmdb_poster + item['profile_path']

                self.list.append({'name': name, 'url': url, 'image': image})
            except:
                pass

        return self.list

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

        self.list = [i for i in self.list if not i['imdb'] == '0']


    def super_info(self, i):
        try:
            zero = '0'

            if self.list[i]['metacache'] == True: raise ValueError('Super in metacache')

            try: imdb = self.list[i]['imdb']
            except: imdb = '0'

            try: tmdb_id = self.list[i]['tmdb']
            except: tmdb_id = '0'

            # Use TMDB for metadata enrichment
            item = None

            if not imdb == '0':
                try:
                    # Find TMDB ID from IMDB ID if we don't have it
                    if tmdb_id == '0':
                        find_url = self.tmdb_find_link % imdb
                        find_result = client.request(find_url, timeout='10')
                        find_result = json.loads(find_result)
                        movie_results = find_result.get('movie_results', [])
                        if movie_results:
                            tmdb_id = str(movie_results[0]['id'])
                            self.list[i].update({'tmdb': tmdb_id})

                    if not tmdb_id == '0':
                        url = self.tmdb_info_link % tmdb_id
                        item_raw = client.request(url, timeout='10')
                        item = json.loads(item_raw)
                except:
                    item = None

            if item is None:
                # No TMDB data available, keep Trakt data
                if not imdb == '0':
                    self.meta.append({'imdb': imdb, 'tmdb': tmdb_id, 'tvdb': '0', 'lang': self.info_lang, 'item': {'code': imdb, 'imdb': imdb, 'tmdb': tmdb_id}})
                return

            title = item.get('title', '0')
            if title and not title == '0':
                self.list[i].update({'title': title, 'originaltitle': title})
                originaltitle = title
            else:
                originaltitle = self.list[i].get('title', '0')

            year = str(item.get('release_date', '0000'))[:4]
            if year and not year == '0' and not year == '0000':
                self.list[i].update({'year': year})
            else:
                year = self.list[i].get('year', '0')

            # IMDB ID from TMDB
            tmdb_imdb = item.get('imdb_id', '')
            if tmdb_imdb and not tmdb_imdb == '':
                self.list[i].update({'imdb': tmdb_imdb, 'code': tmdb_imdb})
                imdb = tmdb_imdb

            # Poster
            poster = zero
            if item.get('poster_path'):
                poster = self.tmdb_poster + item['poster_path']
                self.list[i].update({'poster': poster})

            # Fanart / Backdrop
            fanart = zero
            if item.get('backdrop_path'):
                fanart = self.tmdb_fanart + item['backdrop_path']
                self.list[i].update({'fanart': fanart})

            # Premiered
            premiered = item.get('release_date', '0')
            if premiered and not premiered == '':
                self.list[i].update({'premiered': premiered})
            else:
                premiered = '0'

            # Studio
            studio = zero
            try:
                companies = item.get('production_companies', [])
                if companies:
                    studio = companies[0]['name']
                    self.list[i].update({'studio': studio})
            except: pass

            # Genre
            genre = zero
            try:
                genre_list = item.get('genres', [])
                if genre_list:
                    genre = ' / '.join([g['name'] for g in genre_list])
                    self.list[i].update({'genre': genre})
            except: pass

            # Duration
            duration = str(item.get('runtime', 0))
            if duration and not duration == '0' and not duration == 'None':
                self.list[i].update({'duration': duration})
            else:
                duration = '0'

            # Rating
            rating = str(item.get('vote_average', 0))
            if rating and not rating == '0' and not rating == '0.0':
                self.list[i].update({'rating': rating})
            else:
                rating = '0'

            # Votes
            votes = str(item.get('vote_count', 0))
            try: votes = str(format(int(votes),',d'))
            except: pass
            if votes and not votes == '0':
                self.list[i].update({'votes': votes})
            else:
                votes = '0'

            # MPAA / Certification
            mpaa = zero

            # Director and cast from credits
            director = zero
            writer = zero
            cast = zero
            credits = item.get('credits', {})
            try:
                crew = credits.get('crew', [])
                directors = [c['name'] for c in crew if c.get('job') == 'Director']
                if directors:
                    director = ' / '.join(directors)
                    self.list[i].update({'director': director})
            except: pass
            try:
                writers_list = [c['name'] for c in credits.get('crew', []) if c.get('department') == 'Writing']
                if writers_list:
                    writer = ' / '.join(writers_list[:3])
                    self.list[i].update({'writer': writer})
            except: pass
            try:
                cast_list = credits.get('cast', [])
                if cast_list:
                    cast = [(c['name'], c.get('character', '')) for c in cast_list[:10]]
                    self.list[i].update({'cast': cast})
            except: pass

            # Plot
            plot = item.get('overview', '0')
            if plot and not plot == '':
                plot = client.replaceHTMLCodes(plot)
                self.list[i].update({'plot': plot})
            else:
                plot = '0'

            # Tagline
            tagline = item.get('tagline', '')
            if tagline:
                self.list[i].update({'tagline': tagline})

            # Non-English translation
            if not self.info_lang == 'en':
                url = self.trakt_lang_link % (imdb, self.info_lang)
                try:
                    lang_item = trakt.getTrakt(url)
                    lang_item = json.loads(lang_item)[0]

                    t = lang_item.get('title')
                    if t: self.list[i].update({'title': t})

                    t = lang_item.get('overview')
                    if t: self.list[i].update({'plot': t})
                except:
                    pass

            self.meta.append({'imdb': imdb, 'tmdb': tmdb_id, 'tvdb': '0', 'lang': self.info_lang, 'item': {'title': title, 'originaltitle': originaltitle, 'year': year, 'code': imdb, 'imdb': imdb, 'tmdb': tmdb_id, 'poster': poster, 'banner': zero, 'fanart': fanart, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'director': director, 'writer': writer, 'cast': cast, 'plot': plot}})

        except Exception as e:
            pass


    def movieDirectory(self, items):
        if items == None or len(items) == 0: return

        isFolder = True if control.setting('autoplay') == 'false' and control.setting('host_select') == '1' else False
        isFolder = False if control.window.getProperty('PseudoTVRunning') == 'True' else isFolder

        playbackMenu = control.lang(30204) if control.setting('autoplay') == 'true' else control.lang(30203)

        traktMode = False if trakt.getTraktCredentials() == False else True

        cacheToDisc = False if not action == 'movieSearch' else True

        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()
        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')
        sysaddon = sys.argv[0]

        indicators = playcount.getMovieIndicators(refresh=True) if action == 'movies' else playcount.getMovieIndicators()
        watchedMenu = control.lang(30206) if trakt.getTraktIndicatorsInfo() == True else control.lang(30206)
        unwatchedMenu = control.lang(30207) if trakt.getTraktIndicatorsInfo() == True else control.lang(30207)

        try:
            favitems = favourites.getFavourites('movies')
            favitems = [i[0] for i in favitems]
        except:
            pass


        for i in items:
            try:
                label = '%s (%s)' % (i['title'], i['year'])
                imdb, title, year = i['imdb'], i['originaltitle'], i['year']
                sysname = urllib.quote_plus('%s (%s)' % (title, year))
                systitle = urllib.quote_plus(title)
                tmdb = i['tmdb']


                poster, banner, fanart = i['poster'], i['banner'], i['fanart']
                if poster == '0': poster = addonPoster
                if banner == '0' and poster == '0': banner = addonBanner
                elif banner == '0': banner = poster


                meta = dict((k,v) for k, v in i.items() if not v == '0')
                meta.update({'trailer': '%s?action=trailer&name=%s' % (sysaddon, sysname)})
                if i['duration'] == '0': meta.update({'duration': '120'})
                try: meta.update({'duration': str(int(meta['duration']) * 60)})
                except: pass
                try: meta.update({'genre': cleangenre.lang(meta['genre'], self.info_lang)})
                except: pass
                sysmeta = urllib.quote_plus(json.dumps(meta))


                url = '%s?action=play&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&t=%s' % (sysaddon, sysname, systitle, year, imdb, tmdb, sysmeta, self.systime)
                sysurl = urllib.quote_plus(url)

                if isFolder == True:
                    url = '%s?action=sources&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s' % (sysaddon, sysname, systitle, year, imdb, tmdb, sysmeta)


                cm = []
                cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))
                cm.append((control.lang(30205), 'Action(Info)'))

                try:
                    overlay = int(playcount.getMovieOverlay(indicators, imdb))
                    if overlay == 7:
                        cm.append((unwatchedMenu, 'RunPlugin(%s?action=moviePlaycount&imdb=%s&query=6)' % (sysaddon, imdb)))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((watchedMenu, 'RunPlugin(%s?action=moviePlaycount&imdb=%s&query=7)' % (sysaddon, imdb)))
                        meta.update({'playcount': 0, 'overlay': 6})
                except Exception as e:
                    control.log('#Overlay e %s' % e)
                    pass

                if traktMode == True:
                    cm.append((control.lang(30208), 'RunPlugin(%s?action=traktManager&name=%s&imdb=%s&content=movie)' % (sysaddon, sysname, imdb)))

                if action == 'movieFavourites':
                    cm.append((control.lang(30210), 'RunPlugin(%s?action=deleteFavourite&meta=%s&content=movies)' % (sysaddon, sysmeta)))
                elif action == 'movieSearch':
                    cm.append((control.lang(30209), 'RunPlugin(%s?action=addFavourite&meta=%s&query=0&content=movies)' % (sysaddon, sysmeta)))
                else:
                    if not imdb in favitems: cm.append((control.lang(30209), 'RunPlugin(%s?action=addFavourite&meta=%s&content=movies)' % (sysaddon, sysmeta)))
                    else: cm.append((control.lang(30210), 'RunPlugin(%s?action=deleteFavourite&meta=%s&content=movies)' % (sysaddon, sysmeta)))

                cm.append((control.lang(30211), 'RunPlugin(%s?action=movieToLibrary&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, sysname, systitle, year, imdb, tmdb)))

                cm.append((control.lang(30212), 'RunPlugin(%s?action=addView&content=movies)' % sysaddon))
                #Trailer
                cm.append((control.lang(33003),'RunPlugin(%s?action=trailer&name=%s)' % (sysaddon, sysname)))

                item = control.item(label=label)

                try: item.setArt({'poster': poster, 'banner': banner})
                except: pass

                if settingFanart == 'true' and not fanart == '0':
                    item.setProperty('Fanart_Image', fanart)
                elif not addonFanart == None:
                    item.setProperty('Fanart_Image', addonFanart)

                item.setInfo(type='Video', infoLabels = meta)
                item.setProperty('Video', 'true')
                item.addContextMenuItems(cm, replaceItems=True)
                control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=isFolder)
            except:
                pass

        try:
            url = items[0]['next']
            if url == '': raise Exception()
            url = '%s?action=movies&url=%s' % (sysaddon, urllib.quote_plus(url))
            addonNext = control.addonNext()
            item = control.item(label=control.lang(30213))
            item.addContextMenuItems([], replaceItems=False)
            if not addonFanart == None: item.setProperty('Fanart_Image', addonFanart)
            control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=True)
        except:
            pass


        control.content(int(sys.argv[1]), 'movies')
        control.directory(int(sys.argv[1]), cacheToDisc=cacheToDisc)
        views.setView('movies', {'skin.confluence': 500})


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

                try: cm.append((control.lang(30211), 'RunPlugin(%s?action=moviesToLibrary&url=%s)' % (sysaddon, urllib.quote_plus(i['context']))))
                except: pass

                item = control.item(label=name)
                item.addContextMenuItems(cm, replaceItems=False)
                if not addonFanart == None: item.setProperty('Fanart_Image', addonFanart)
                control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=True)
            except:
                pass

        control.directory(int(sys.argv[1]), cacheToDisc=True)
