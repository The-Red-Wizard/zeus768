# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons for Kodi 21+ (Python 3). Addons: SALTS, Orion, StrikeZone, Trakt Player, Genesis.

## Architecture
- **Type**: Kodi Video Addons (Python 3), native `urllib`, `resolveurl` optional
- **APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid, OpenAI (Emergent Proxy), Invidious (YouTube)
- **Ko-fi**: https://ko-fi.com/zeus768

---

## plugin.video.genesis (Genesis) — v2026.04.04.01 [ADDED TO REPO]
- [x] Added to repository from user-provided zip
- [x] Zip packaged into /app/zips/plugin.video.genesis/
- [x] addon.xml entry added to addons.xml

## script.genesis.media (Genesis Themepak) — v2026.04.04 [ADDED TO REPO]
- [x] Added to repository from user-provided zip
- [x] Zip packaged into /app/zips/script.genesis.media/
- [x] addon.xml entry added to addons.xml

## plugin.video.salts (SALTS) — v2.4.2 [STABLE]
- [x] Python 3 / Kodi 21+ | 34+ scrapers | Free Streams
- [x] Debrid: RD, PM, AD, TorBox | Batch cache + [CACHED] tags
- [x] AI Search, Franchises, Actors, 24/7 Channels, Buy Me a Beer

## plugin.video.orion (Orion) — v3.2.4 [STABLE]
- [x] Multi-scraper | Debrid: RD, PM, AD, TB | Buy Me a Beer

## plugin.video.strikezone — v1.2.2 [STABLE]
- [x] Auto-scrape, search, favourites | Buy Me a Beer

## plugin.video.trakt_player — v2.1.1 [STABLE]
### Core
- [x] Complete rewrite — 100% native urllib, zero `requests`
- [x] Click-and-Play (auto <=1080p, no source dialog)
- [x] Trakt Scrobbling (background service)
- [x] Up Next (auto-play next episode)
### Browse & Discovery
- [x] Continue Watching, Recommendations, Calendar, History
- [x] Popular Lists, Anticipated, Related Content
- [x] AI Discovery (12 mood presets + custom vibe)
- [x] Discovery Feed (Trailer Scroll) — 6 modes
### Social & Lists
- [x] Rate 1-10, Add to Watchlist, Add to Custom List
- [x] Custom Lists (create/browse/delete)
- [x] Friends Activity Feed (live + history)
### Account & Status
- [x] User Stats Dashboard, Debrid Account Status, Buy Me a Beer

## plugin.program.theaccountant — v3.9.6 [STABLE]
- [x] Speed Optimizer, Scheduled Auto-Clean, RD/PM/AD/Trakt/TMDB Auth

## repository.zeus768 — v1.0.8 [STABLE]
- [x] Includes ResolveURL repository reference

---

## Repository README
- [x] Updated with all addon icons and full descriptions (Feb 2026)

## Pending Tasks
- [ ] SALTS: Make scrapers concurrent/superfast
- [ ] SALTS: Fix 24/7 channel scraper instantiation bug
- [ ] SALTS: Package updated version after fixes
