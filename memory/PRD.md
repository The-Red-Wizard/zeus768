# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons for Kodi 21+ (Python 3). Addons: SALTS, Orion, StrikeZone, Trakt Player.

## Architecture
- **Type**: Kodi Video Addons (Python 3), native `urllib`, `resolveurl` optional
- **APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid, OpenAI
- **Ko-fi**: https://ko-fi.com/zeus768

---

## plugin.video.salts (SALTS) — v2.4.2 [STABLE]
- [x] Python 3 / Kodi 21+ | 34+ scrapers | Free Streams
- [x] Debrid: RD, PM, AD, TorBox | Batch cache + [CACHED] tags | Debrid gate
- [x] Trakt: OAuth, lists, scrobble, community ratings on browse & source dialog
- [x] AI Search — NLP movie/TV discovery via OpenAI
- [x] Franchises: 60 curated collections with TMDB poster art
- [x] Actors: TMDB profile photos on all menus
- [x] **24/7 Movie Channels**: 40 actors with TMDB photos
- [x] **24/7 TV Show Channels**: 40 shows with TMDB posters
- [x] **24/7 Genre Channels**: 18 genres (Action thru Western) with TMDB art, 60 movies shuffled per genre
- [x] **24/7 AI Vibe Channel**: Describe a mood → AI picks 10-15 movies → shuffled marathon
- [x] Bento UI Source Dialog + Pre-Scrape & Hover Caching
- [x] Fixed RD .rar resolution | Buy Me a Beer

## plugin.video.orion (Orion) — v3.2.4 [STABLE]
- [x] Multi-scraper | Debrid: RD, PM, AD, TB | [CACHED] tags | Fixed RD .rar
- [x] Trakt, Kids Zone, Favorites, Quality filtering | Buy Me a Beer

## plugin.video.strikezone — v1.2.2 [STABLE]
- [x] Auto-scrape, infinite scroll, search, favourites | Buy Me a Beer

## plugin.video.trakt_player — v2.0.0 [STABLE]
- [x] Complete rewrite from scratch — removed all Umbrella/free stream references
- [x] Torrent-only with Click-and-Play (no source select dialog)
- [x] Auto-plays highest quality <= 1080p (discards 4K/2160p)
- [x] Debrid: Real-Debrid, Premiumize, AllDebrid, TorBox (all 4 with OAuth)
- [x] Trakt: OAuth device flow with user's keys (d2a8e820...)
- [x] Scrapers: PirateBay, YTS, EZTV, 1337x, TorrentGalaxy — all native urllib
- [x] TMDB metadata for posters, backdrops, ratings, genres
- [x] Browse: Movies (Trending/Popular/Watched/BoxOffice/Genres), TV Shows (Trending/Popular/Watched/Genres), My Trakt lists
- [x] No `requests` library — 100% native urllib for Kodi 21+ compatibility
- [x] Packaged into repository zip + addons.xml updated + md5 regenerated

---

## All Tasks Complete
