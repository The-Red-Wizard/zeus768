# SALTS - Stream All The Sources (Kodi Addon) - PRD

## Problem Statement
Fix the old Kodi addon "plugin.video.salts" (SALTS) and bring it back to life for Kodi 21+ (Python 3). Add torrent sites, Trakt support, ResolveURL, Debrid integration, content browsing, and 24/7 channels.

## Architecture
- **Type**: Kodi Video Addon (Python 3)
- **Entry Point**: `default.py` (router-based, ~2500 lines)
- **Libraries**: `salts_lib/` (trakt_api, debrid, db_utils, constants, utils, log_utils, free_streams)
- **Scrapers**: `scrapers/` (34+ scrapers)
- **Dependencies**: `urllib` (native), `bs4`, `resolveurl` — NO `requests` module
- **Database**: SQLite
- **External APIs**: TMDB (metadata + collections + people), Trakt, Real-Debrid/Premiumize/AllDebrid/TorBox

## Current Version: 2.1.6

## Completed Features
- [x] Full Python 3 / Kodi 21+ migration
- [x] 34+ scrapers
- [x] Free Stream scrapers (VidSrc, 2Embed, etc.)
- [x] Real-Debrid, Premiumize, AllDebrid, TorBox integration
- [x] Batch cache checking across all debrid services
- [x] [CACHED] source tagging + prioritized sorting
- [x] Debrid gate (blocks torrent scrapers without active debrid)
- [x] Trakt.tv integration (OAuth, all lists, scrobble)
- [x] TMDB metadata
- [x] **Franchises menu** (30 curated + search with unlimited pagination)
- [x] **Actors menu** (popular with pagination + search + filmography)
- [x] **24/7 Movie Channels** (pick actor, shuffled marathon, max 1080p, autoplay)
- [x] **24/7 TV Show Channels** (pick show, random start, sequential autoplay)
- [x] Custom source dialog, Autoplay, Source caching, Scraper priorities
- [x] Favorites, Watch history, OpenSubtitles, Skip Intro, Up Next
- [x] Jackett/Prowlarr, ResolveURL, Kodi repo structure

## v2.1.6 Changes (Apr 2026)
- Franchises menu with TMDB collections API
- Actors menu with TMDB people API
- 24/7 Movie Channels (actor-based random marathon)
- 24/7 TV Show Channels (random start, sequential play)
- Search for all new categories

## Backlog / Future
- [ ] P1: Bento UI source dialog (grid layout: large 4K cards, medium 1080p, small for info)
- [ ] P1: Pre-Scrape & Hover Caching (2s hover trigger, SQLite cache, 24hr TTL, "Ready" indicator)
- [ ] P2: AI Search with vector database (OpenAI embeddings + Pinecone/Weaviate)
- [ ] P2: Full regression test
- [ ] P3: Trakt ratings in source lists
