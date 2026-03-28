# SALTS - Stream All The Sources (Kodi Addon)
## Product Requirements Document

### Original Problem Statement
Fix the old Kodi addon "plugin.video.salts" (SALTS) and bring it back to life for Kodi 21+ (Python 3). Add torrent sites, APIs, Jackett support, fix scrapers, use resolveurl (not urlresolver), add Trakt, change author to "tknorris, zeus768". Integrate into user's GitHub Kodi repository alongside other addons.

### Architecture
```
/app/
├── addons.xml                 # Kodi repository index
├── addons.xml.md5             # MD5 checksum
├── plugin.video.salts/        # SALTS addon (v2.1.1)
│   ├── addon.xml
│   ├── default.py             # Main entry point, routing, playback
│   ├── service.py             # Background service
│   ├── resources/settings.xml # User-facing settings
│   ├── salts_lib/             # trakt_api.py, debrid.py, db_utils.py, etc.
│   └── scrapers/              # 34+ modular scrapers
├── plugin.video.orion/
├── plugin.video.strikezone/
├── plugin.program.theaccountant/
├── repository.zeus768/
├── script.module.resolveurl/
└── zips/                      # Packaged zips for Kodi
```

### What's Been Implemented
- [x] Full Python 3 / Kodi 21+ migration
- [x] 34+ scrapers (torrent, streaming, anime, international)
- [x] ResolveURL integration (replaced urlresolver)
- [x] TMDB metadata using native urllib
- [x] Trakt API v2 using native urllib (fixed from requests)
- [x] Real-Debrid / Premiumize / AllDebrid debrid support
- [x] Jackett / Prowlarr aggregator support
- [x] Repository structure (addons.xml, zips, MD5)
- [x] Removed repository.gujal from repo index
- [x] Fixed rescrape loop (setResolvedUrl → xbmc.Player().play())
- [x] Custom source selection dialog with quality breakdown
- [x] Up Next - auto-play next episode for TV series
- [x] Skip Intro prompt for TV episodes (configurable)
- [x] Settings for all new features

### Current Version: 2.1.1

### Backlog / Future Enhancements
- P1: Autoplay mode (auto-select best quality source)
- P1: Source result caching (avoid re-scraping same title)
- P2: OpenSubtitles integration for auto-subtitles
- P2: Favorites/Bookmarks system (local, non-Trakt)
- P2: Pre-emptive scraping (scrape next episode while watching)
- P3: Provider priority ordering
- P3: Multiple quality presets (WiFi/Mobile profiles)
