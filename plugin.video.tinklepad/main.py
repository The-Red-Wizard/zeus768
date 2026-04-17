import sys
import urllib.parse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from resources.lib import gui, tmdb, scrapers
from resources.lib.debrid import debrid_manager

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])

def main():
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    action = params.get('action')
    
    xbmc.log(f'[Tinklepad] Action: {action}, Params: {params}', xbmc.LOGINFO)

    if not action:
        # Main menu
        gui.play_intro()
        items = [
            (gui.gold('MOVIES'), 'm_menu', 'movies.png'),
            (gui.gold('TV SHOWS'), 't_menu', 'tv.png'),
            (gui.gold('LITTLE EAGLES'), 'k_menu', 'kids.png'),
            (gui.gold('SEARCH'), 'global_search', 'search.png'),
            (gui.gold('TOOLS'), 'tools_menu', 'tools.png')
        ]
        gui.add_menu_items(HANDLE, items)

    elif action == 'm_menu':
        items = [
            ('Genres', 'genres', 'm_genres.png', {'type': 'movie'}),
            ('Years', 'years', 'm_years.png', {'type': 'movie'}),
            ('Trending', 'list_content', 'm_trend.png', {'type': 'movie', 'sort': 'trending'}),
            ('Popular', 'list_content', 'm_trend.png', {'type': 'movie', 'sort': 'popular'}),
            ('Actors', 'actors', 'people.png', {'type': 'movie'}),
            ('Search', 'global_search', 'search.png', {'type': 'movie'})
        ]
        gui.add_menu_items(HANDLE, items)

    elif action == 't_menu':
        items = [
            ('Genres', 'genres', 'm_genres.png', {'type': 'tv'}),
            ('Years', 'years', 'm_years.png', {'type': 'tv'}),
            ('Trending', 'list_content', 't_new_eps.png', {'type': 'tv', 'sort': 'trending'}),
            ('Networks', 'networks', 't_nets.png'),
            ('Actors', 'actors', 'people.png', {'type': 'tv'}),
            ('Search', 'global_search', 'search.png', {'type': 'tv'})
        ]
        gui.add_menu_items(HANDLE, items)

    elif action == 'k_menu':
        items = [
            ('Animated Movies', 'list_content', 'kids.png', {'type': 'movie', 'genre_id': '16'}),
            ('Family Movies', 'list_content', 'kids.png', {'type': 'movie', 'genre_id': '10751'}),
            ('Kids TV Shows', 'list_content', 'kids.png', {'type': 'tv', 'genre_id': '10762'}),
            ('Animation TV', 'list_content', 'kids.png', {'type': 'tv', 'genre_id': '16'})
        ]
        gui.add_menu_items(HANDLE, items)

    elif action == 'tools_menu':
        # Build dynamic menu showing debrid status
        items = []
        
        # Real-Debrid status
        if debrid_manager.rd_authorized():
            rd_user = ADDON.getSetting('rd.username') or 'Authorized'
            items.append((f'[COLOR green]Real-Debrid: {rd_user}[/COLOR]', 'rd_auth', 'tools.png'))
        else:
            items.append(('[COLOR red]Real-Debrid: Not Authorized[/COLOR]', 'rd_auth', 'tools.png'))
        
        # AllDebrid status
        if debrid_manager.ad_authorized():
            ad_user = ADDON.getSetting('ad.username') or 'Authorized'
            items.append((f'[COLOR green]AllDebrid: {ad_user}[/COLOR]', 'ad_auth', 'tools.png'))
        else:
            items.append(('[COLOR red]AllDebrid: Not Authorized[/COLOR]', 'ad_auth', 'tools.png'))
        
        # Premiumize status
        if debrid_manager.pm_authorized():
            pm_user = ADDON.getSetting('pm.username') or 'Authorized'
            items.append((f'[COLOR green]Premiumize: {pm_user}[/COLOR]', 'pm_auth', 'tools.png'))
        else:
            items.append(('[COLOR red]Premiumize: Not Authorized[/COLOR]', 'pm_auth', 'tools.png'))
        
        items.append(('', 'separator', 'tools.png'))  # Separator
        items.append((gui.gold('ADDON SETTINGS'), 'settings', 'tools.png'))
        items.append((gui.gold('CLEAR CACHE'), 'clear_cache', 'tools.png'))
        items.append((gui.gold('ABOUT'), 'about', 'tools.png'))
        
        gui.add_menu_items(HANDLE, items)

    elif action == 'rd_auth':
        # Real-Debrid authorization
        ADDON.setSetting('rd.enabled', 'true')
        
        if debrid_manager.rd_authorized():
            choice = xbmcgui.Dialog().yesno(
                'Real-Debrid',
                f'Currently authorized as: {ADDON.getSetting("rd.username")}\n\nDo you want to re-authorize?'
            )
            if not choice:
                return
        
        xbmc.log('[Tinklepad] Starting Real-Debrid authorization...', xbmc.LOGINFO)
        success = debrid_manager.rd_authorize()
        
        if success:
            xbmcgui.Dialog().ok('Real-Debrid', 'Authorization successful!\n\nYou can now use Real-Debrid links.')
        xbmc.executebuiltin('Container.Refresh')

    elif action == 'ad_auth':
        # AllDebrid authorization
        ADDON.setSetting('ad.enabled', 'true')
        
        if debrid_manager.ad_authorized():
            choice = xbmcgui.Dialog().yesno(
                'AllDebrid',
                f'Currently authorized as: {ADDON.getSetting("ad.username")}\n\nDo you want to re-authorize?'
            )
            if not choice:
                return
        
        xbmc.log('[Tinklepad] Starting AllDebrid authorization...', xbmc.LOGINFO)
        success = debrid_manager.ad_authorize()
        
        if success:
            xbmcgui.Dialog().ok('AllDebrid', 'Authorization successful!\n\nYou can now use AllDebrid links.')
        xbmc.executebuiltin('Container.Refresh')

    elif action == 'pm_auth':
        # Premiumize authorization
        ADDON.setSetting('pm.enabled', 'true')
        
        if debrid_manager.pm_authorized():
            choice = xbmcgui.Dialog().yesno(
                'Premiumize',
                f'Currently authorized as: {ADDON.getSetting("pm.username")}\n\nDo you want to re-authorize?'
            )
            if not choice:
                return
        
        xbmc.log('[Tinklepad] Starting Premiumize authorization...', xbmc.LOGINFO)
        success = debrid_manager.pm_authorize()
        
        if success:
            xbmcgui.Dialog().ok('Premiumize', 'Authorization successful!\n\nYou can now use Premiumize links.')
        xbmc.executebuiltin('Container.Refresh')

    elif action == 'settings':
        ADDON.openSettings()

    elif action == 'clear_cache':
        if tmdb.clear_all_cache():
            xbmcgui.Dialog().notification('Tinklepad', 'Cache cleared successfully!', xbmcgui.NOTIFICATION_INFO, 2000)
        else:
            xbmcgui.Dialog().notification('Tinklepad', 'Cache cleared!', xbmcgui.NOTIFICATION_INFO, 2000)

    elif action == 'about':
        info = (
            "[B][COLOR gold]TINKLEPAD v1.3.0[/COLOR][/B]\n\n"
            "The Golden Eagle of Entertainment\n\n"
            "[COLOR gold]Debrid Services:[/COLOR]\n"
            "• Real-Debrid, AllDebrid, Premiumize\n\n"
            "[COLOR gold]DDL Providers:[/COLOR]\n"
            "• Tinklepad (162.245.85.19)\n"
            "• 1DDL, DDLValley, RlsBB, ScnSrc\n\n"
            "[COLOR gold]Torrent Providers:[/COLOR]\n"
            "• YTS, 1337x, TPB, TorrentGalaxy\n\n"
            "[COLOR lime]Free Streaming:[/COLOR]\n"
            "• VidSrc.to, VidSrc.me\n"
            "• 2Embed, SuperEmbed\n\n"
            "[COLOR gold]Supported Hosts:[/COLOR]\n"
            "NitroFlare, RapidGator, ClicknUpload,\n"
            "UsersDrive, Uploaded, and more!\n\n"
            "By Zeus768"
        )
        xbmcgui.Dialog().textviewer('About Tinklepad', info)

    elif action == 'genres':
        tmdb.show_genres(params.get('type', 'movie'))

    elif action == 'years':
        tmdb.show_years(params.get('type', 'movie'))

    elif action == 'networks':
        tmdb.show_networks()

    elif action == 'actors':
        tmdb.show_actors(params.get('type', 'movie'))

    elif action == 'actor_content':
        tmdb.show_actor_content(
            params.get('type', 'movie'),
            params.get('person_id'),
            params.get('name', '')
        )

    elif action == 'list_content':
        tmdb.list_content(HANDLE, params)

    elif action == 'global_search':
        tmdb.global_search(HANDLE, params.get('query'), params.get('type'))

    elif action == 'info':
        tmdb.show_info(params.get('id'), params.get('type', 'movie'))

    elif action == 'play':
        # Play content - search for sources
        title = params.get('title', '')
        year = params.get('year', '')
        content_type = params.get('type', 'movie')
        tmdb_id = params.get('id')  # This is the TMDB ID
        season = params.get('season')
        episode = params.get('episode')
        
        # Get optional metadata passed from listing
        fanart = params.get('fanart', '')
        plot = params.get('plot', '')
        poster = params.get('poster', '')
        rating = params.get('rating', '')
        runtime = params.get('runtime', '')
        genres = params.get('genres', '')
        
        if not title:
            xbmcgui.Dialog().notification('Tinklepad', 'No title provided', xbmcgui.NOTIFICATION_ERROR, 3000)
            return
        
        xbmc.log(f'[Tinklepad] Playing: {title} ({year}) TMDB:{tmdb_id}', xbmc.LOGINFO)
        
        # Fetch full metadata from TMDB for the overlay display
        if tmdb_id:
            try:
                meta = tmdb.get_full_metadata(tmdb_id, content_type)
                if meta:
                    fanart = meta.get('fanart', fanart) or fanart
                    poster = meta.get('poster', poster) or poster
                    plot = meta.get('plot', plot) or plot
                    rating = meta.get('rating', rating) or rating
                    runtime = meta.get('runtime', runtime) or runtime
                    genres = meta.get('genres', genres) or genres
            except Exception as e:
                xbmc.log(f'[Tinklepad] Metadata fetch error: {e}', xbmc.LOGWARNING)
        
        # Get sources from all providers - pass full metadata for overlay display
        sources = scrapers.get_sources(
            title=title, 
            year=year, 
            content_type=content_type,
            tmdb_id=tmdb_id,
            season=season,
            episode=episode,
            fanart=fanart,
            plot=plot,
            poster=poster,
            rating=rating,
            runtime=runtime,
            genres=genres
        )
        
        if sources:
            scrapers.play_source(sources, title, year, fanart, poster)
        else:
            xbmcgui.Dialog().notification('Tinklepad', 'No sources found', xbmcgui.NOTIFICATION_WARNING, 3000)

    elif action == 'separator':
        pass  # Do nothing for separator

if __name__ == '__main__':
    main()
