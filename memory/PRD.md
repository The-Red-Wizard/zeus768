# SALTS - Stream All The Sources (Kodi Addon)
## Product Requirements Document

### Current Version: SALTS 2.1.1 / Repo 1.0.7

### Architecture
```
/app/
├── addons.xml / addons.xml.md5
├── plugin.video.salts/ (v2.1.1)
│   ├── default.py          # ~1675 lines
│   ├── salts_lib/
│   │   ├── free_streams.py # VidSrc AJAX chain, 2Embed, Embed.su, VidLink, MultiEmbed
│   │   ├── trakt_api.py    # Trakt v2 (urllib)
│   │   ├── debrid.py       # RD/PM/AD
│   │   └── db_utils.py     # source_cache, favorites, scraper_priority, quality_presets
│   └── scrapers/           # 35+ scrapers + freestream_scraper.py
├── repository.zeus768/ (v1.0.7)
└── zips/ (all versions verified matching)
```

### Fixed This Session
- [x] Free streams: Rewrote free_streams.py - proper URL validation rejects garbage (github.com, .js etc.), VidSrc uses AJAX chain (/ajax/embed/episode, /ajax/embed/source), specific m3u8/mp4 patterns only
- [x] Repo versions: Fixed ALL version mismatches across addons.xml, zip addon.xml, and zip filenames (Orion 3.1.0, StrikeZone 1.2.0, ResolveURL 5.1.194)
- [x] HLS playback: Added inputstream.adaptive properties for m3u8 and mpd streams

### All Implemented Features
- Python 3 / Kodi 21+, 35+ scrapers, free streams (6 providers), autoplay, source caching, favorites, pre-emptive scraping, quality presets, scraper priority, custom source dialog, Up Next, Skip Intro, Trakt, debrid, Jackett/Prowlarr, TMDB, ResolveURL

### Remaining / Future
- OpenSubtitles integration
- Trakt scrobble during playback
- Genre/Year filtering
- Watch history overlay
