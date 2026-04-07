# Zeus768 Kodi Repository - PRD

## Original Problem Statement
Maintain and upgrade the Zeus768 custom Kodi repository. Tasks include: adding new addons (Poseidon Player/Guide, Syncher), removing StrikeZone, fixing SALTS, Trakt Player, Genesis, and building the Syncher addon from scratch.

## Architecture
```
/app/
├── addons.xml / addons.xml.md5       # Repo manifest (10 addons)
├── plugin.video.genesis/             # v9.4.1 - TMDB/Trakt powered, auth fixed
├── plugin.video.salts/               # v2.6.0 - Stable
├── plugin.video.trakt_player/        # v2.2.0 - Stable
├── plugin.video.syncher/             # v2.0.0 - NEW (Scene release scraper)
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
- [x] Genesis v9.3.0: Python 3 porting, CocoScrapers/Gears wrappers, Trakt auth URL fix
- [x] Genesis v9.4.0: Migrated all movie/TV indexers from IMDB to Trakt API + TMDB metadata
- [x] Genesis v9.4.1: Fixed ALL debrid auth dialogs + Trakt auth (Kodi 21 progressDialog compat)
- [x] **Syncher v2.0.0**: Complete addon build (Feb 2026)
  - Trakt API browsing (Movies, TV Shows) with TMDB metadata (posters, cast, directors)
  - 8 scene scrapers: RapidRAR, PSA, RapidMoviez, TFPDL, WatchSeriesHD, RLSbb, DDLValley, SceneSource
  - 4 sports replay scrapers: Sport-Video, FullMatchShows, FootballOrgin, Basketball-Video
  - 5 resolvers: Real-Debrid, Premiumize, AllDebrid, TorBox (device code auth), RapidRAR (login)
  - Trakt device code auth with user's own client ID/secret
  - Full menus: Movies, TV Shows, Sports, Music, My Trakt, Search, Settings
  - Warez site per-site login support
  - Sports categories with sub-menus (NBA, NFL, Premier League, Champions League, etc.)
  - Music search/trending from scene sites
  - Auto-play and source select modes

## Pending / Backlog
- [ ] P1: User testing of Syncher in Kodi
- [ ] P1: Fix StrikeZone scraper offline
- [ ] P2: Test Genesis debrid resolvers
- [ ] P2: Full Kodi verification of all addons
- [ ] P2: Push to GitHub for repo updates
