# Zeus768 Kodi Repository - PRD

## Original Problem Statement
Maintain and upgrade the Zeus768 custom Kodi repository. Build the Syncher addon as an all-in-one media addon with Movies, TV Shows, Sports Highlights, Music (AI + Deezer + Radio), Podcasts, and Audiobooks.

## Architecture
```
/app/
├── addons.xml / addons.xml.md5       # Repo manifest (10 addons)
├── plugin.video.syncher/             # v3.4.0 - All-in-One Media Addon
│   ├── main.py                       # Router (94 entries, 2023 lines)
│   ├── resources/lib/modules/
│   │   ├── ai_playlists.py           # AI daily playlists via Emergent Universal Key + GPT
│   │   ├── radio_api.py              # Radio Browser API (30k+ live stations)
│   │   ├── deezer_api.py             # Deezer API for music metadata
│   │   ├── playlists.py              # User playlist mgmt (shuffle/sort/export/import)
│   │   ├── podcast_api.py            # iTunes Search API + RSS feed parser
│   │   ├── audiobook_api.py          # LibriVox API + Internet Archive API
│   │   ├── trakt_api.py / tmdb_api.py / sources.py / client.py / control.py / cache.py
│   ├── resources/lib/scrapers/       # 8 scene + 4 sports + 1 music scraper
│   └── resources/lib/resolvers/      # RD, PM, AD, TB, RapidRAR
├── plugin.video.genesis/             # v9.4.1
├── plugin.video.salts/               # v2.6.0
├── plugin.video.trakt_player/        # v2.2.0
├── Other addons...
└── zips/                             # 10 compiled distributables
```

## Completed Tasks
- [x] Genesis v9.4.1: Python 3, TMDB/Trakt migration, auth fixes
- [x] SALTS v2.6.0, Trakt Player v2.2.0, Poseidon Player/Guide
- [x] **Syncher v2.0.0**: Movies, TV, Sports, Scene scrapers, Debrid resolvers, Trakt
- [x] **Syncher v3.2.0**: Deezer Music (genres, artists, albums, charts, user playlists, autoplay)
- [x] **Syncher v3.3.0**: AI Daily Playlists (Emergent Universal Key), Mood/Decade/Similar, Radio, Enhanced playlists
- [x] **Syncher v3.4.0**: Podcasts (iTunes/RSS) + Audiobooks (LibriVox + Internet Archive)

## 3rd Party Integrations
| Service | Endpoint | Auth |
|---------|----------|------|
| Trakt | api.trakt.tv | User client ID/secret |
| TMDB | api.themoviedb.org/3 | Key in control.py |
| Deezer | api.deezer.com | None |
| Emergent AI | integrations.emergentagent.com/llm | Emergent Universal Key |
| Radio Browser | de1.api.radio-browser.info/json | None |
| iTunes Podcast | itunes.apple.com/search | None |
| Apple RSS | rss.applemarketingtools.com | None |
| LibriVox | librivox.org/api/feed | None |
| Internet Archive | archive.org/advancedsearch.php | None |
| Real-Debrid, Premiumize, AllDebrid, TorBox | various | Device code auth |

## Pending / Backlog
- [ ] P0: User must click "Save to Github" so Kodi can detect repo updates
- [ ] P1: User testing of Syncher in Kodi (all sections)
- [ ] P1: Fix StrikeZone scraper offline
- [ ] P2: Test Genesis debrid resolvers
- [ ] P2: Full Kodi verification of all addons
