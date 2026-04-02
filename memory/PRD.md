# SALTS - Stream All The Sources (Kodi Addon) - PRD

## Problem Statement
Fix the old Kodi addon "plugin.video.salts" (SALTS) and bring it back to life for Kodi 21+ (Python 3). Add torrent sites, Trakt support, ResolveURL, Debrid integration, content browsing, 24/7 channels, and advanced UI/caching.

## Architecture
- **Type**: Kodi Video Addon (Python 3)
- **Entry Point**: `default.py` (router-based, ~2550 lines)
- **Libraries**: `salts_lib/` (trakt_api, debrid, db_utils, constants, utils, log_utils, free_streams, bento_dialog, prescrape)
- **Scrapers**: `scrapers/` (34+ scrapers)
- **Skin**: `resources/skins/Default/1080i/SourceSelectDialog.xml`
- **Service**: `service.py` (background hover monitor + pre-scrape)
- **Dependencies**: `urllib` (native), `bs4`, `resolveurl` — NO `requests` module
- **Database**: SQLite (url_cache, source_cache, hover_cache, favorites, scraper_priority, quality_presets, search_history, settings, related_url)
- **External APIs**: TMDB, Trakt, Real-Debrid/Premiumize/AllDebrid/TorBox

## Current Version: 2.1.7

## Completed Features
- [x] Full Python 3 / Kodi 21+ migration
- [x] 34+ scrapers, Free Stream scrapers
- [x] Real-Debrid, Premiumize, AllDebrid, TorBox integration
- [x] Batch cache checking + [CACHED] tagging
- [x] Debrid gate (blocks torrent scrapers without active debrid)
- [x] Trakt.tv integration (OAuth, all lists, scrobble)
- [x] TMDB metadata + TMDB helper function
- [x] Franchises menu (30 curated + search + unlimited pagination)
- [x] Actors menu (popular + search + filmography with pagination)
- [x] 24/7 Movie Channels (actor-based random marathon, max 1080p)
- [x] 24/7 TV Show Channels (random start, sequential autoplay)
- [x] **Bento UI Source Dialog** (custom skin XML, quality badges, cached/free tags, seeds/size)
- [x] **Pre-Scrape & Hover Caching** (2s hover trigger, 4-link rule, 24hr SQLite TTL, "Instant!" notification)
- [x] Autoplay, Source caching, Scraper priorities
- [x] Favorites, Watch history, OpenSubtitles, Skip Intro, Up Next
- [x] Jackett/Prowlarr, ResolveURL, Kodi repo structure

## Backlog / Future
- [ ] P2: AI Search with vector database (OpenAI embeddings + Pinecone/Weaviate)
- [ ] P2: Full regression test of all features
- [ ] P3: Trakt ratings in source lists
