# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons for Kodi 21+ (Python 3). Addons: SALTS, Orion, StrikeZone, Trakt Player.

## Architecture
- **Type**: Kodi Video Addons (Python 3), native `urllib`, `resolveurl` optional
- **APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid, OpenAI (Emergent Proxy)
- **Ko-fi**: https://ko-fi.com/zeus768

---

## plugin.video.salts (SALTS) — v2.4.2 [STABLE]
- [x] Python 3 / Kodi 21+ | 34+ scrapers | Free Streams
- [x] Debrid: RD, PM, AD, TorBox | Batch cache + [CACHED] tags | Debrid gate
- [x] Trakt: OAuth, lists, scrobble, community ratings on browse & source dialog
- [x] AI Search, Franchises, Actors, 24/7 Channels (Movie/TV/Genre/AI Vibe)
- [x] Fixed RD .rar resolution | Buy Me a Beer

## plugin.video.orion (Orion) — v3.2.4 [STABLE]
- [x] Multi-scraper | Debrid: RD, PM, AD, TB | [CACHED] tags | Fixed RD .rar
- [x] Trakt, Kids Zone, Favorites, Quality filtering | Buy Me a Beer

## plugin.video.strikezone — v1.2.2 [STABLE]
- [x] Auto-scrape, infinite scroll, search, favourites | Buy Me a Beer

## plugin.video.trakt_player — v2.0.0 [STABLE]
### Core
- [x] Complete rewrite — removed all Umbrella/free stream references
- [x] 100% native urllib — zero external dependencies
- [x] **Click-and-Play**: Auto-plays best quality <= 1080p, no source dialog
- [x] **Trakt Scrobbling**: Auto start/pause/stop via background service
- [x] **Up Next**: Auto-play next episode with confirmation dialog (15s auto-close)

### Browse & Discovery
- [x] **Continue Watching**: Resume from Trakt playback progress
- [x] **Recommendations**: Personalized for Movies & TV Shows
- [x] **My Calendar**: Upcoming episodes for shows you watch (30-day lookahead)
- [x] **Watch History**: Recently watched movies & episodes
- [x] **Popular Lists**: Browse trending community-curated Trakt lists
- [x] **Anticipated**: Most anticipated upcoming movies & shows
- [x] **Related Content**: "More Like This" via context menu
- [x] **AI Discovery (Vibe Marathons)**: 12 presets + custom mood input, AI picks 12-15 titles

### Social & Lists
- [x] **Rate on Trakt**: Rate 1-10 via context menu
- [x] **Add to Watchlist**: Quick-add via context menu
- [x] **Add to List**: Add to any custom list via context menu
- [x] **Custom Lists**: Create, browse, delete custom Trakt lists
- [x] **Friends Activity Feed**: See what friends are watching NOW + their history

### Account & Status
- [x] **User Stats Dashboard**: Watch time, ratings distribution, network stats
- [x] **Debrid Account Status**: Premium/expiry/days left/auto-renew for RD, AD, PM, TB
- [x] **Buy Me a Beer**: Donation tab with QR code

### Technical
- [x] **Cached Torrent Indicator**: RD/PM/AD cache check, prioritizes cached for instant play
- [x] Debrid: Real-Debrid, Premiumize, AllDebrid, TorBox (all 4 with OAuth)
- [x] Scrapers: PirateBay, YTS, EZTV, 1337x, TorrentGalaxy
- [x] TMDB metadata for posters, backdrops, ratings, genres
- [x] Packaged into repository with addons.xml + md5

---

## All Tasks Complete
