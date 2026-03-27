# SALTS Addon Modernization - PRD

## Original Problem Statement
Fix and modernize the SALTS (Stream All The Sources) Kodi addon for Kodi 21+ with torrent site support, Jackett integration, and debrid services. Add author zeus768.

## Project Overview
Complete rewrite of the classic SALTS addon from Python 2/Kodi 18 to Python 3/Kodi 21+ (Omega).

## What's Been Implemented (2026-01-27)

### Core Modernization
- [x] Updated addon.xml for Kodi 21+ (Python 3.0.0)
- [x] Changed provider-name to zeus768
- [x] Replaced all Python 2 code with Python 3
- [x] Updated dependencies (resolveurl, requests, beautifulsoup4, six)

### Torrent Scrapers (12 Total)
1. [x] **1337x** - General torrent site with mirror support
2. [x] **YTS/YIFY** - High quality movies (API-based)
3. [x] **EZTV** - TV shows only (API-based)
4. [x] **TorrentGalaxy** - General torrents with mirrors
5. [x] **ThePirateBay** - Classic site with API/HTML scraping
6. [x] **LimeTorrents** - General torrents
7. [x] **Torrentz2** - Meta-search engine
8. [x] **RARBG** - Mirror/clone sites
9. [x] **Nyaa** - Anime torrents

### Indexer Aggregators
10. [x] **Jackett** - Connect to 400+ indexers
11. [x] **Prowlarr** - Alternative aggregator

### APIs
12. [x] **TorrentAPI** - Generic torrent API support

### Debrid Services
- [x] **Real-Debrid** - Full OAuth device flow authentication
- [x] **Premiumize** - API key authentication
- [x] **AllDebrid** - PIN-based authentication

### Features
- [x] Quality parsing (4K, 1080p, 720p, etc.)
- [x] Size display
- [x] Seed/peer counts
- [x] Automatic mirror detection
- [x] Cached torrent detection
- [x] Settings UI for all options

## Files Created
- `/app/salts_modern/plugin.video.salts/` - Complete addon
- `/app/plugin.video.salts-2.0.0.zip` - Installable zip

## Architecture
```
plugin.video.salts/
├── addon.xml           # Kodi 21+ manifest
├── default.py          # Main entry point
├── service.py          # Background service
├── salts_lib/
│   ├── constants.py    # Quality definitions, patterns
│   ├── log_utils.py    # Logging
│   ├── db_utils.py     # SQLite caching
│   ├── debrid.py       # RD/PM/AD integration
│   └── utils.py        # Helper functions
├── scrapers/
│   ├── base_scraper.py # Abstract base class
│   ├── x1337_scraper.py
│   ├── yts_scraper.py
│   ├── eztv_scraper.py
│   ├── torrentgalaxy_scraper.py
│   ├── tpb_scraper.py
│   ├── limetorrents_scraper.py
│   ├── torrentz2_scraper.py
│   ├── rarbg_scraper.py
│   ├── nyaa_scraper.py
│   ├── jackett_scraper.py
│   ├── prowlarr_scraper.py
│   └── torrentapi_scraper.py
└── resources/
    └── settings.xml    # Kodi 19+ settings format
```

## Next Action Items
- [ ] Test in actual Kodi 21 environment
- [ ] Add more torrent sites as they come online
- [ ] Implement Trakt.tv integration (optional)
- [ ] Add auto-update functionality

## Backlog / Future Features
- P1: Season pack handling
- P1: Direct torrent streaming (without debrid)
- P2: Trakt.tv watchlist integration
- P2: IMDb integration for metadata
- P3: Custom scraper priority settings
- P3: Bandwidth limiting options
