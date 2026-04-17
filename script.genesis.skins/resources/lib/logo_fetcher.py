# -*- coding: utf-8 -*-
"""
Logo Fetcher - Fetches real logos from services
Caches logos locally for offline use
"""
import os
import xbmc
import xbmcvfs
import xbmcaddon
import hashlib
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ADDON = xbmcaddon.Addon('script.genesis.skins')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
CACHE_PATH = xbmcvfs.translatePath('special://profile/addon_data/script.genesis.skins/logo_cache/')

# Ensure cache directory exists
if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)


# ══════════════════════════════════════════════════════════════════════════════
# OFFICIAL LOGO URLS - Direct links to real service logos
# ══════════════════════════════════════════════════════════════════════════════

LOGO_URLS = {
    # ── Streaming Networks/Platforms ──
    'crunchyroll': 'https://www.crunchyroll.com/favicons/favicon-32x32.png',
    'netflix': 'https://assets.nflxext.com/us/ffe/siteui/common/icons/nficon2016.png',
    'funimation': 'https://www.funimation.com/favicon.ico',
    'hidive': 'https://www.hidive.com/favicon.ico',
    'amazon_prime': 'https://m.media-amazon.com/images/G/01/digital/video/web/Logo-min.png',
    'hulu': 'https://www.hulu.com/favicon.ico',
    'disney_plus': 'https://cnbl-cdn.bamgrid.com/assets/7ecc8bcb60ad77193058d63e321bd21cbac2fc67181f54b476b36a34d35d1e40/original',
    
    # ── Anime Studios ──
    'mappa': 'https://www.mappa.co.jp/favicon.ico',
    'ufotable': 'https://www.ufotable.com/favicon.ico',
    'wit_studio': 'https://www.wit-studio.co.jp/favicon.ico',
    'bones': 'https://www.bones.co.jp/favicon.ico',
    'madhouse': 'https://www.madhouse.co.jp/favicon.ico',
    'kyoto_animation': 'https://www.kyotoanimation.co.jp/favicon.ico',
    'toei': 'https://www.toei-anim.co.jp/favicon.ico',
    'sunrise': 'https://www.sunrise-inc.co.jp/favicon.ico',
    'a1_pictures': 'https://www.a1p.jp/favicon.ico',
    'cloverworks': 'https://cloverworks.co.jp/favicon.ico',
    
    # ── Anime Torrent Sites ──
    'nyaa': 'https://nyaa.si/static/favicon.png',
    'subsplease': 'https://subsplease.org/wp-content/uploads/2020/07/cropped-SubsPlease-32x32.png',
    'animetosho': 'https://animetosho.org/favicon.ico',
    'tokyotosho': 'https://www.tokyotosho.info/favicon.ico',
    'anidex': 'https://anidex.info/favicon.ico',
    
    # ── Live TV Channels ──
    'sky_cinema': 'https://www.sky.com/favicon.ico',
    'sony_movies': 'https://www.sonypictures.com/favicon.ico',
    'hallmark': 'https://www.hallmarkchannel.com/favicon.ico',
    'film4': 'https://www.channel4.com/favicon.ico',
    'hbo': 'https://www.hbo.com/favicon.ico',
    'showtime': 'https://www.sho.com/favicon.ico',
    'starz': 'https://www.starz.com/favicon.ico',
    'amc': 'https://www.amc.com/favicon.ico',
    'tcm': 'https://www.tcm.com/favicon.ico',
    'fx': 'https://www.fxnetworks.com/favicon.ico',
    'syfy': 'https://www.syfy.com/favicon.ico',
    'paramount': 'https://www.paramountnetwork.com/favicon.ico',
    'cinemax': 'https://www.cinemax.com/favicon.ico',
    
    # ── Debrid Services ──
    'realdebrid': 'https://real-debrid.com/favicon.ico',
    'alldebrid': 'https://alldebrid.com/favicon.ico',
    'premiumize': 'https://www.premiumize.me/favicon.ico',
    'torbox': 'https://torbox.app/favicon.ico',
    'linksnappy': 'https://linksnappy.com/favicon.ico',
    
    # ── General Torrent Sites ──
    '1337x': 'https://1337x.to/favicon.ico',
    'piratebay': 'https://thepiratebay.org/favicon.ico',
    'yts': 'https://yts.mx/assets/images/website/favicon.ico',
    'eztv': 'https://eztv.re/favicon.ico',
    'limetorrents': 'https://www.limetorrents.lol/favicon.ico',
    'torrentgalaxy': 'https://torrentgalaxy.to/favicon.ico',
    'magnetdl': 'https://www.magnetdl.com/favicon.ico',
    'solidtorrents': 'https://solidtorrents.to/favicon.ico',
    'bitsearch': 'https://bitsearch.to/favicon.ico',
    
    # ── Trakt / TMDB / OMDB ──
    'trakt': 'https://trakt.tv/favicon.ico',
    'tmdb': 'https://www.themoviedb.org/favicon.ico',
    'omdb': 'https://www.omdbapi.com/favicon.ico',
    'myanimelist': 'https://myanimelist.net/img/common/pwa/launcher-icon-1x.png',
}

# Alternative high-quality logo sources (Fanart.tv style or direct CDN)
LOGO_URLS_HQ = {
    # Higher quality alternatives where available
    'netflix': 'https://images.ctfassets.net/4cd45et68cgf/7LrExJ6PAj6MSIPkDyCO86/542b1dfabbf3959908f69be546571f7c/Netflix-N-Logo-Red.png',
    'crunchyroll': 'https://www.crunchyroll.com/build/assets/img/favicons/favicon-96x96.png',
    'hbo': 'https://play-lh.googleusercontent.com/1iyX7VdQ7znlhPsNgpSl0nhb14M7YPJDnTc9v2EPiKWOMnMeqRPqQPREnLgt1sPjkPo',
    'disney_plus': 'https://cnbl-cdn.bamgrid.com/assets/7ecc8bcb60ad77193058d63e321bd21cbac2fc67181f54b476b36a34d35d1e40/original',
    'amazon_prime': 'https://m.media-amazon.com/images/G/01/digital/video/web/cues/v3/amazon-prime-702._CB612297703_.png',
    'trakt': 'https://walter-r2.trakt.tv/hotlink-ok/public/favicon-96x96.png',
}


def get_cache_filename(name):
    """Generate cache filename for a logo"""
    return os.path.join(CACHE_PATH, f'{name}.png')


def download_logo(name, url):
    """Download a logo and cache it locally"""
    cache_file = get_cache_filename(name)
    
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response = urlopen(req, timeout=10)
        data = response.read()
        
        with open(cache_file, 'wb') as f:
            f.write(data)
        
        xbmc.log(f'Genesis Skins: Downloaded logo for {name}', xbmc.LOGDEBUG)
        return cache_file
    except Exception as e:
        xbmc.log(f'Genesis Skins: Failed to download logo for {name}: {e}', xbmc.LOGWARNING)
        return None


def get_logo(name, fallback=None):
    """Get logo path - from cache or download
    
    Args:
        name: Service name (e.g., 'netflix', 'nyaa', 'realdebrid')
        fallback: Fallback path if logo unavailable
        
    Returns:
        Path to logo file or fallback
    """
    # Normalize name
    name_key = name.lower().replace(' ', '_').replace('-', '_')
    
    # Check cache first
    cache_file = get_cache_filename(name_key)
    if os.path.exists(cache_file):
        return cache_file
    
    # Try to download
    url = LOGO_URLS_HQ.get(name_key) or LOGO_URLS.get(name_key)
    if url:
        result = download_logo(name_key, url)
        if result:
            return result
    
    return fallback


def prefetch_all_logos():
    """Download all logos in background"""
    import threading
    
    def _fetch():
        for name, url in LOGO_URLS.items():
            cache_file = get_cache_filename(name)
            if not os.path.exists(cache_file):
                download_logo(name, url)
    
    thread = threading.Thread(target=_fetch)
    thread.daemon = True
    thread.start()


def clear_logo_cache():
    """Clear all cached logos"""
    import shutil
    if os.path.exists(CACHE_PATH):
        shutil.rmtree(CACHE_PATH)
        os.makedirs(CACHE_PATH)
    xbmc.log('Genesis Skins: Logo cache cleared', xbmc.LOGINFO)


def get_all_fetchable_logos():
    """Get list of all logos that can be auto-fetched"""
    return list(LOGO_URLS.keys())
