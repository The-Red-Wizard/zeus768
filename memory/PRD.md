# Zeus768 Kodi Repository - PRD

## Original Problem Statement
Maintain and upgrade the Zeus768 custom Kodi repository. Tasks include: adding new addons (Poseidon Player/Guide), removing StrikeZone, fixing SALTS (Trakt + Stremio scrapers), fixing Trakt Player (Premiumize auth + AI features merge), and comprehensive Genesis fixes (Python 3 porting, external scrapers, fixing broken category menus).

## Architecture
```
/app/
├── addons.xml / addons.xml.md5       # Repo manifest
├── plugin.video.genesis/             # v9.4.0 - TMDB/Trakt powered
├── plugin.video.salts/               # v2.6.0 - Stable
├── plugin.video.trakt_player/        # v2.2.0 - Stable
├── plugin.video.poseidonplayer/      # v2.3.0 - Stable
├── program.poseidonguide/            # v1.1.0 - Stable
├── plugin.program.theaccountant/     # v3.9.7 - Stable
├── plugin.video.orion/               # v3.2.5 - Stable
├── repository.zeus768/               # Repo config
└── zips/                             # Compiled distributables
```

## Completed Tasks
- [x] Replaced Genesis/Themepak with user's v9.2.6/v9.2.4 zips
- [x] Added Poseidon Player v2.3.0 and Poseidon Guide v1.1.0
- [x] Removed StrikeZone from repo
- [x] SALTS v2.6.0: Fixed Trakt scrobbling, added Stremio scrapers (Torrentio, MediaFusion, Comet, etc.)
- [x] Trakt Player v2.2.0: Merged AI Vibes/Discovery features, fixed Premiumize device auth
- [x] Genesis v9.3.0: Python 3 porting, CocoScrapers/Gears wrappers, Trakt auth URL fix
- [x] Genesis v9.4.0: **Migrated all movie/TV indexers from broken IMDB scraping to Trakt API** (Feb 2026)
  - Movies: popular, trending, box office, genres, years, search all now use Trakt API
  - TV Shows: popular, trending, genres, years, networks, search all now use Trakt API
  - Metadata enrichment: migrated from dead OMDB to TMDB API (Orion key: f15af109700aab95d564acda15bdcd97)
  - Full cast/director/poster/fanart from TMDB credits API
  - Episodes indexer: fixed api-v2launch → api.trakt.tv
  - Updated genres to Trakt slugs (science-fiction, superhero, etc.)
  - Rebuilt zip, addons.xml, MD5

## Pending / Backlog
- [ ] P1: Re-test Genesis debrid resolvers (RD, PM, AD, TorBox)
- [ ] P1: Fix StrikeZone scraper offline (user requested future re-addition)
- [ ] P2: Test Genesis Trakt user lists / watchlists / collections
- [ ] P2: User verification of all addons in Kodi
