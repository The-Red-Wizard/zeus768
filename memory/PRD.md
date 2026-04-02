# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons and bring them back to life for Kodi 21+ (Python 3). Primary addons: SALTS, Orion, StrikeZone.

## Architecture
- **Type**: Kodi Video Addons (Python 3)
- **Repository**: `/app/` root with `addons.xml`, `addons.xml.md5`, individual addon folders, and `zips/`
- **Dependencies**: Native `urllib` only (no `requests` module for SALTS/Orion). `bs4` + `requests` for StrikeZone. `resolveurl` optional.
- **External APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid
- **Ko-fi**: https://ko-fi.com/zeus768

---

## plugin.video.salts (SALTS) — v2.2.1 [STABLE]
- [x] Full Python 3 / Kodi 21+ migration
- [x] 34+ scrapers (17 scraper classes), Free Stream scrapers
- [x] Real-Debrid, Premiumize, AllDebrid, TorBox integration
- [x] Batch cache checking + [CACHED] tagging
- [x] Debrid gate (blocks torrent scrapers without active debrid)
- [x] Trakt.tv integration (OAuth, all lists, scrobble)
- [x] **Trakt community ratings in source dialog header** (v2.2.1)
- [x] TMDB metadata + TMDB helper function
- [x] Franchises menu (30 curated + search + unlimited pagination)
- [x] Actors menu (popular + search + filmography with pagination)
- [x] 24/7 Movie Channels (actor-based random marathon, max 1080p)
- [x] 24/7 TV Show Channels (random start, sequential autoplay)
- [x] Bento UI Source Dialog (inline native dialog, quality badges, cached/free tags)
- [x] Pre-Scrape & Hover Caching (2s hover trigger, 4-link rule, 24hr SQLite TTL)
- [x] Fixed RD .rar resolution (v2.1.9)
- [x] Buy Me a Beer — Ko-fi QR code dialog (v2.2.0)
- [x] Full regression test — 46 files, all routes, scrapers, debrid classes validated

## plugin.video.orion (Orion) — v3.2.3 [STABLE]
- [x] Multi-scraper: Orionoid, Torrentio, MediaFusion, Jackettio, 1337x, TorrentDownloads, RARBG
- [x] Debrid: Real-Debrid, Premiumize, AllDebrid, TorBox — all native urllib
- [x] [CACHED] source tags with batch cache checking (v3.2.1)
- [x] Fixed RD .rar resolution + no-debrid error dialog + ResolveURL fallback (v3.2.2)
- [x] Buy Me a Beer (v3.2.3)
- [x] Trakt integration, Kids Zone, Watch history, Favorites, Quality filtering

## plugin.video.strikezone (Strike Zone) — v1.2.1 [STABLE]
- [x] Auto-scrape categories from FullFightReplays
- [x] Infinite scroll, search, favourites, watch history
- [x] Buy Me a Beer with Ko-fi QR (v1.2.1)

---

## Completed Backlog
- [x] P2: Full regression test for SALTS (46 files, all routes, scrapers, debrid validated)
- [x] P3: Trakt ratings in source lists for SALTS (community rating in dialog header)

## Remaining Backlog
- [ ] P2: AI Search with vector database (OpenAI) for SALTS (Bento UI & Search 2.0)
