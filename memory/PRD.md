# Zeus768 Kodi Repository - PRD

## Original Problem Statement
Maintain and upgrade the Zeus768 custom Kodi repository. Tasks include: adding new addons, fixing existing ones, and building the Syncher addon from scratch with a massive Music section powered by Deezer API, AI-generated playlists via Emergent Universal Key, and live radio streams.

## Architecture
```
/app/
├── addons.xml / addons.xml.md5       # Repo manifest (10 addons)
├── plugin.video.genesis/             # v9.4.1 - TMDB/Trakt powered, auth fixed
├── plugin.video.salts/               # v2.6.0 - Stable
├── plugin.video.trakt_player/        # v2.2.0 - Stable
├── plugin.video.syncher/             # v3.3.0 - AI Music + Debrid + Trakt + Radio
│   ├── main.py                       # Router (74 actions), all menus and playback
│   ├── resources/lib/modules/
│   │   ├── ai_playlists.py           # AI daily playlists via Emergent Universal Key
│   │   ├── radio_api.py              # Radio Browser API (30k+ live stations)
│   │   ├── deezer_api.py             # Deezer API for music metadata
│   │   ├── playlists.py              # User playlist management (shuffle/sort/export)
│   │   ├── trakt_api.py              # Trakt API
│   │   ├── tmdb_api.py               # TMDB API
│   │   ├── sources.py                # Source coordination + resolver chain
│   │   ├── control.py                # Addon helpers
│   │   ├── client.py                 # HTTP client
│   │   └── cache.py                  # Cache management
│   ├── resources/lib/scrapers/       # 8 scene + 4 sports + 1 music scraper
│   └── resources/lib/resolvers/      # RD, PM, AD, TB, RapidRAR
├── plugin.video.poseidonplayer/      # v2.3.0 - Stable
├── program.poseidonguide/            # v1.1.0 - Stable
├── plugin.program.theaccountant/     # v3.9.7 - Stable
├── plugin.video.orion/               # v3.2.5 - Stable
├── repository.zeus768/               # Repo config
└── zips/                             # 10 compiled distributables
```

## Completed Tasks
- [x] Replaced Genesis/Themepak with user's v9.2.6/v9.2.4 zips
- [x] Added Poseidon Player v2.3.0 and Poseidon Guide v1.1.0
- [x] Removed StrikeZone from repo
- [x] SALTS v2.6.0: Fixed Trakt scrobbling, added Stremio scrapers
- [x] Trakt Player v2.2.0: Merged AI Vibes/Discovery features, fixed Premiumize device auth
- [x] Genesis v9.3.0 -> v9.4.1: Python 3 porting, TMDB/Trakt migration, auth fixes
- [x] **Syncher v2.0.0**: Complete addon build - Trakt/TMDB/Debrid/Scene scrapers/Sports
- [x] **Syncher v3.2.0**: Deezer Music section - genres, artists, albums, charts, playlists, autoplay, scene search
- [x] **Syncher v3.3.0**: Massive Music upgrade
  - AI Daily Playlists via Emergent Universal Key (14 rotating themes, mood, decade, similar artist)
  - Live Radio via Radio Browser API (20 genres, 20 countries, search)
  - Enhanced playlists (shuffle, sort, export, import)
  - All tested: Deezer API, Radio Browser API, Emergent AI proxy, py_compile

## 3rd Party Integrations
- Trakt API: `https://api.trakt.tv/` (user's client ID/secret stored in addon)
- TMDB API: `https://api.themoviedb.org/3/` (key in control.py)
- Deezer API: `https://api.deezer.com/` (no auth needed)
- Emergent LLM Proxy: `https://integrations.emergentagent.com/llm` (GPT-4o-mini via Emergent Universal Key)
- Radio Browser API: `https://de1.api.radio-browser.info/json` (no auth needed)
- Debrid Services: Real-Debrid, Premiumize, AllDebrid, TorBox (device code auth in settings)

## Pending / Backlog
- [ ] P0: User must click "Save to Github" so Kodi can detect repo updates
- [ ] P1: User testing of Syncher in Kodi (all sections)
- [ ] P1: Fix StrikeZone scraper offline
- [ ] P2: Test Genesis debrid resolvers
- [ ] P2: Full Kodi verification of all addons
