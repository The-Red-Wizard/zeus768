# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons and bring them back to life for Kodi 21+ (Python 3). Primary addons: SALTS, Orion, StrikeZone.

## Architecture
- **Type**: Kodi Video Addons (Python 3)
- **Repository**: `/app/` root with `addons.xml`, `addons.xml.md5`, individual addon folders, and `zips/`
- **Dependencies**: Native `urllib` only (no `requests`). `bs4` for scrapers. `resolveurl` optional.
- **External APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid, OpenAI
- **Ko-fi**: https://ko-fi.com/zeus768

---

## plugin.video.salts (SALTS) — v2.3.0 [STABLE]
- [x] Full Python 3 / Kodi 21+ migration
- [x] 34+ scrapers (17 scraper classes), Free Stream scrapers
- [x] Real-Debrid, Premiumize, AllDebrid, TorBox integration
- [x] Batch cache checking + [CACHED] tagging
- [x] Debrid gate (blocks torrent scrapers without active debrid)
- [x] Trakt.tv integration (OAuth, all lists, scrobble)
- [x] **Trakt community ratings on browse lists & source dialog** (v2.2.1 + v2.3.0)
- [x] **AI Search** — Natural language movie & TV discovery via OpenAI (v2.3.0)
  - Search by description ("movies about time travel with a twist ending")
  - Filter: Movies / TV / All
  - AI recommends 10-15 titles, TMDB lookup with posters, purple AI reason tags
  - Configurable model: gpt-4o-mini, gpt-4o, gpt-5.2
  - Pre-configured with Emergent LLM key
- [x] TMDB metadata + TMDB helper function
- [x] Franchises menu (30 curated + search + unlimited pagination)
- [x] Actors menu (popular + search + filmography with pagination)
- [x] 24/7 Movie & TV Show Channels
- [x] Bento UI Source Dialog + Pre-Scrape & Hover Caching
- [x] Fixed RD .rar resolution (v2.1.9)
- [x] Buy Me a Beer — Ko-fi QR code dialog (v2.2.0)
- [x] Full regression test — 46 files, all routes validated

## plugin.video.orion (Orion) — v3.2.3 [STABLE]
- [x] Multi-scraper: Orionoid, Torrentio, MediaFusion, Jackettio + Coco scrapers
- [x] Debrid: Real-Debrid, Premiumize, AllDebrid, TorBox — all native urllib
- [x] [CACHED] source tags, batch cache checking
- [x] Fixed RD .rar resolution + no-debrid error dialog + ResolveURL fallback
- [x] Trakt, Kids Zone, Watch history, Favorites, Quality filtering
- [x] Buy Me a Beer (v3.2.3)

## plugin.video.strikezone (Strike Zone) — v1.2.1 [STABLE]
- [x] Auto-scrape categories, infinite scroll, search, favourites
- [x] Buy Me a Beer with Ko-fi QR (v1.2.1)

---

## All Tasks Complete
No remaining backlog items.
