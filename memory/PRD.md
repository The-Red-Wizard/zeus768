# SALTS - Stream All The Sources (Kodi Addon) - PRD

## Problem Statement
Fix the old Kodi addon "plugin.video.salts" (SALTS) and bring it back to life for Kodi 21+ (Python 3). Add torrent sites, Trakt support, ResolveURL, and Debrid integration.

## Architecture
- **Type**: Kodi Video Addon (Python 3)
- **Entry Point**: `default.py` (router-based)
- **Libraries**: `salts_lib/` (trakt_api, debrid, db_utils, constants, utils, log_utils, free_streams)
- **Scrapers**: `scrapers/` (34+ scrapers: torrent, streaming, anime, international)
- **Dependencies**: `urllib` (native), `bs4`, `resolveurl` — NO `requests` module
- **Database**: SQLite (source_cache, favorites, watched_items, quality_presets, scraper_priorities)
- **External APIs**: TMDB (metadata), Trakt (lists/scrobble), Real-Debrid/Premiumize/AllDebrid/TorBox (link resolution)

## Current Version: 2.1.5

## Completed Features
- [x] Full Python 3 / Kodi 21+ migration
- [x] 34+ scrapers (1337x, YTS, EZTV, TorrentGalaxy, TPB, Nyaa, international, anime, etc.)
- [x] Free Stream scrapers (VidSrc, 2Embed, AutoEmbed, etc.) - no Debrid needed
- [x] Real-Debrid, Premiumize, AllDebrid integration (OAuth device auth)
- [x] TorBox integration (API key auth, magnet resolve, cache check)
- [x] Batch cache checking (all hashes against all debrid services in one pass)
- [x] [CACHED] tag + green highlighting in source dialog
- [x] Debrid gate (torrent scrapers blocked until debrid enabled; free streams always available)
- [x] Trakt.tv integration (OAuth, watchlist, collection, trending, popular, custom lists, scrobble)
- [x] TMDB metadata (posters, backdrops, ratings, descriptions)
- [x] Custom source selection dialog with quality breakdown + cached count
- [x] Autoplay mode
- [x] Source caching
- [x] Scraper priorities
- [x] Favorites system
- [x] Watch history tracking
- [x] OpenSubtitles integration
- [x] Skip Intro for TV episodes
- [x] Up Next (auto-play next episode)
- [x] Pre-emptive scraping (scrape next episode at 75%)
- [x] Quality presets
- [x] Jackett/Prowlarr aggregator support
- [x] ResolveURL for direct links
- [x] Kodi repository structure with zips + MD5

## v2.1.5 Changes (Apr 2026)
- [x] TorBox debrid service support
- [x] Batch cache checking across all enabled debrid services
- [x] [CACHED] source tagging and prioritized sorting (cached > free > quality > seeds)
- [x] Debrid gate (blocks torrent scrapers without active debrid)
- [x] Replaced all `requests` usage with native `urllib` in base_scraper.py and debrid.py
- [x] Fixed Trakt API credentials (real CLIENT_ID/SECRET)
- [x] Hardened Trakt list/menu parsing for all response formats
- [x] Removed `script.module.requests` and `script.module.six` dependencies

## Backlog / Future
- [ ] P2: Full regression test of Free Streams + Autoplay + OpenSubtitles with Debrid gate
- [ ] P2: Trakt ratings display in source lists
- [ ] P3: Artwork/poster fetching from Trakt IDs in list views
