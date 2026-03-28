# SALTS - Stream All The Sources (Kodi Addon)
## Product Requirements Document

### Original Problem Statement
Fix SALTS for Kodi 21+ Python 3. Add torrent sites, Jackett, fix scrapers, resolveurl, Trakt, free streams (Mobiflix-style), autoplay, favorites, source caching, quality presets, scraper priority. Author: tknorris, zeus768.

### Architecture
```
/app/
├── addons.xml / addons.xml.md5
├── plugin.video.salts/        # v2.1.1
│   ├── addon.xml
│   ├── default.py             # ~1660 lines: menus, sources, playback, favorites, presets
│   ├── service.py
│   ├── changelog.txt
│   ├── resources/settings.xml # 14 settings categories
│   ├── salts_lib/
│   │   ├── trakt_api.py       # Trakt v2 (urllib)
│   │   ├── free_streams.py    # 7 free providers (VidSrc, 2Embed, etc.)
│   │   ├── debrid.py          # RD/PM/AD
│   │   ├── db_utils.py        # SQLite: source_cache, favorites, scraper_priority, quality_presets
│   │   ├── log_utils.py / constants.py / utils.py
│   └── scrapers/              # 35+ scrapers
│       ├── freestream_scraper.py
│       ├── x1337_scraper.py
│       └── ... (torrent, streaming, anime, intl)
├── plugin.video.orion/
├── plugin.video.strikezone/
├── plugin.program.theaccountant/
├── repository.zeus768/        # v1.0.7
├── script.module.resolveurl/
└── zips/
```

### Implemented Features (Complete)
- [x] Python 3 / Kodi 21+ migration
- [x] 35+ scrapers (torrent, streaming, anime, intl, FREE streams)
- [x] Free Stream providers: VidSrc.to, VidSrc.me, 2Embed, AutoEmbed, MultiEmbed, Embed.su, VidLink
- [x] Autoplay mode (Settings toggle, prioritizes free streams)
- [x] Source caching with configurable TTL and cache/re-scrape dialog
- [x] Favorites/Bookmarks (main menu + context menu on all TMDB items)
- [x] Pre-emptive next episode scraping (at 75%, caches for Up Next)
- [x] Quality Presets (WiFi/Mobile/DataSaver/4K + custom)
- [x] Scraper Priority ordering (move up/down, set manual priority)
- [x] Custom source dialog (quality breakdown, free count, color-coded)
- [x] Up Next episode prompt
- [x] Skip Intro prompt (configurable)
- [x] ResolveURL / Direct stream detection (m3u8/mp4 bypass)
- [x] Trakt API v2 (urllib)
- [x] Real-Debrid / Premiumize / AllDebrid
- [x] Jackett / Prowlarr
- [x] TMDB metadata
- [x] Fixed rescrape loop (Player.play)
- [x] Removed repository.gujal

### Versions
- SALTS: 2.1.1
- Repository: 1.0.7

### Remaining / Future
- OpenSubtitles auto-subtitles integration
- Trakt scrobble during playback
- Genre/Year filtering on TMDB lists
- Watch history overlay (watched indicator on listings)
