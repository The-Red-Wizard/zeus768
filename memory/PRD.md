# SALTS Addon Modernization - PRD

## Original Problem Statement
Fix and modernize the SALTS (Stream All The Sources) Kodi addon for Kodi 21+ with torrent site support, Jackett integration, debrid services, and Trakt.tv support. Add author zeus768.

## Project Overview
Complete rewrite of the classic SALTS addon from Python 2/Kodi 18 to Python 3/Kodi 21+ (Omega).

## What's Been Implemented (2026-01-27)

### Core Modernization
- [x] Updated addon.xml for Kodi 21+ (Python 3.0.0)
- [x] Changed provider-name to zeus768
- [x] Replaced all Python 2 code with Python 3
- [x] Updated dependencies (resolveurl, requests, beautifulsoup4, six)
- [x] Changed from urlresolver to resolveurl (modern replacement)

### Torrent Scrapers (9 sites)
1. [x] **1337x** - General torrent site with mirror support
2. [x] **YTS/YIFY** - High quality movies (API-based)
3. [x] **EZTV** - TV shows only (API-based)
4. [x] **TorrentGalaxy** - General torrents with mirrors
5. [x] **ThePirateBay** - Classic site with API/HTML scraping
6. [x] **LimeTorrents** - General torrents
7. [x] **Torrentz2** - Meta-search engine
8. [x] **RARBG** - Mirror/clone sites
9. [x] **Nyaa** - Anime torrents

### Streaming Site Scrapers (Modernized Legacy - 4 sites)
10. [x] **PrimeWire** - General streaming with mirror detection
11. [x] **WatchSeries** - TV show streaming
12. [x] **Movie4K** - General streaming
13. [x] **SolarMovie** - General streaming

### Indexer Aggregators
14. [x] **Jackett** - Connect to 400+ indexers
15. [x] **Prowlarr** - Alternative aggregator

### APIs
16. [x] **TorrentAPI** - Generic torrent API support

### Debrid Services
- [x] **Real-Debrid** - Full OAuth device flow authentication
- [x] **Premiumize** - API key authentication
- [x] **AllDebrid** - PIN-based authentication

### Trakt.tv Integration (API v2)
- [x] Device OAuth authentication flow
- [x] Watchlist (Movies & TV Shows)
- [x] Collection management
- [x] Trending content
- [x] Popular content
- [x] Recommended content (personalized)
- [x] Custom lists support
- [x] Calendar (upcoming episodes)
- [x] Scrobbling support
- [x] Progress tracking

### Features
- [x] Quality parsing (4K, 1080p, 720p, etc.)
- [x] Size display
- [x] Seed/peer counts
- [x] Automatic mirror detection
- [x] Cached torrent detection
- [x] Settings UI for all options
- [x] ResolveURL integration (not deprecated urlresolver)

## Files Created
- `/app/salts_modern/plugin.video.salts/` - Complete addon
- `/app/plugin.video.salts-2.0.0.zip` - Installable zip

## Architecture
```
plugin.video.salts/
├── addon.xml           # Kodi 21+ manifest
├── default.py          # Main entry point with Trakt integration
├── service.py          # Background service
├── salts_lib/
│   ├── constants.py    # Quality definitions, patterns
│   ├── log_utils.py    # Logging
│   ├── db_utils.py     # SQLite caching
│   ├── debrid.py       # RD/PM/AD integration
│   ├── trakt_api.py    # Trakt.tv API v2 integration
│   └── utils.py        # Helper functions
├── scrapers/
│   ├── base_scraper.py # Abstract base class
│   │ Torrent Sites:
│   ├── x1337_scraper.py
│   ├── yts_scraper.py
│   ├── eztv_scraper.py
│   ├── torrentgalaxy_scraper.py
│   ├── tpb_scraper.py
│   ├── limetorrents_scraper.py
│   ├── torrentz2_scraper.py
│   ├── rarbg_scraper.py
│   ├── nyaa_scraper.py
│   │ Streaming Sites (Legacy Modernized):
│   ├── primewire_scraper.py
│   ├── watchseries_scraper.py
│   ├── movie4k_scraper.py
│   ├── solarmovie_scraper.py
│   │ Aggregators:
│   ├── jackett_scraper.py
│   ├── prowlarr_scraper.py
│   └── torrentapi_scraper.py
└── resources/
    └── settings.xml    # Kodi 19+ settings format
```

## Next Action Items
- [ ] Test in actual Kodi 21 environment
- [ ] Add more torrent sites as they come online
- [ ] Add playback progress saving via Trakt

## Backlog / Future Features
- P1: Season pack handling
- P1: Direct torrent streaming (without debrid)
- P2: Auto-play next episode
- P2: IMDb integration for metadata
- P3: Custom scraper priority settings
- P3: Bandwidth limiting options
