# SALTS - Stream All The Sources (Kodi Addon)
## Product Requirements Document

### Original Problem Statement
Fix the old Kodi addon "plugin.video.salts" (SALTS) and bring it back to life for Kodi 21+ (Python 3). Add torrent sites, APIs, Jackett support, fix scrapers, use resolveurl (not urlresolver), add Trakt, change author to "tknorris, zeus768". Integrate into user's GitHub Kodi repository. Add free streams like Mobiflix, autoplay, custom source dialog, Up Next, Skip Intro.

### Architecture
```
/app/
├── addons.xml                 # Kodi repository index (v1.0.7)
├── addons.xml.md5             # MD5 checksum
├── plugin.video.salts/        # SALTS addon (v2.1.1)
│   ├── addon.xml
│   ├── default.py             # Main entry, routing, playback, autoplay
│   ├── service.py             # Background service
│   ├── resources/settings.xml # All user settings
│   ├── salts_lib/
│   │   ├── trakt_api.py       # Trakt v2 API (urllib)
│   │   ├── free_streams.py    # Free stream providers (VidSrc, 2Embed, etc.)
│   │   ├── debrid.py          # RD/PM/AD debrid
│   │   ├── db_utils.py        # SQLite cache
│   │   ├── log_utils.py
│   │   └── constants.py
│   └── scrapers/
│       ├── freestream_scraper.py  # Free direct streams (no debrid)
│       ├── x1337_scraper.py       # 1337x
│       └── ... (34+ scrapers total)
├── plugin.video.orion/
├── plugin.video.strikezone/
├── plugin.program.theaccountant/
├── repository.zeus768/        # v1.0.7
├── script.module.resolveurl/
└── zips/
```

### Implemented Features
- [x] Python 3 / Kodi 21+ migration
- [x] 35+ scrapers (torrent, streaming, anime, international, FREE streams)
- [x] Free Stream providers: VidSrc.to, VidSrc.me, 2Embed, AutoEmbed, MultiEmbed, Embed.su, VidLink
- [x] Autoplay mode (Settings > General toggle)
- [x] Custom source dialog with quality breakdown + free stream count
- [x] ResolveURL integration
- [x] TMDB metadata via native urllib
- [x] Trakt API v2 via native urllib
- [x] Real-Debrid / Premiumize / AllDebrid debrid
- [x] Jackett / Prowlarr aggregators
- [x] Fixed rescrape loop (xbmc.Player().play instead of setResolvedUrl)
- [x] Removed repository.gujal
- [x] Up Next - auto-play next episode
- [x] Skip Intro prompt (configurable duration)
- [x] Direct m3u8/mp4 stream detection (bypass ResolveURL for free streams)
- [x] Repository updated to v1.0.7

### Current Version: SALTS 2.1.1 / Repo 1.0.7

### Backlog / Future Enhancements
- P1: Source result caching (avoid re-scraping same title within session)
- P2: OpenSubtitles integration for auto-subtitles
- P2: Favorites/Bookmarks system (local, non-Trakt)
- P2: Pre-emptive scraping (scrape next episode while watching)
- P3: Provider priority ordering
- P3: Multiple quality presets (WiFi/Mobile profiles)
