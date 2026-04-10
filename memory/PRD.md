# Zeus768 Kodi Repository - PRD

## Original Problem Statement
Maintain and upgrade the Zeus768 custom Kodi repository. Addons: Genesis, SALTS, Trakt Player, Syncher, Poseidon Player/Guide, and more.

## Architecture
```
/app/
├── addons.xml / addons.xml.md5
├── plugin.video.syncher/             # v3.4.0 - All-in-One (Music AI, Podcasts, Audiobooks, Radio)
├── plugin.video.trakt_player/        # v2.3.0 - Fixed PM auth + RD expiry + account info
├── plugin.video.genesis/             # v9.4.1 - TMDB/Trakt, auth fixed
├── plugin.video.salts/               # v2.6.0
├── Other addons...
└── zips/                             # Compiled distributables
```

## Completed Tasks
- [x] Genesis v9.4.1: Python 3, TMDB/Trakt migration, auth fixes
- [x] SALTS v2.6.0, Trakt Player v2.2.0, Poseidon Player/Guide
- [x] Syncher v3.4.0: Movies, TV, Sports, Music (AI+Deezer+Radio), Podcasts, Audiobooks
- [x] **Trakt Player v2.3.0**: Debrid auth fixes
  - FIXED: Premiumize auth code not showing (response_type vs grant_type)
  - FIXED: Real-Debrid false "expired" errors (token refresh fallback)
  - ADDED: Real account_info() for RD, PM, AD (username, email, expiry, days left, points)
  - ADDED: Color-coded expiry warnings on Account Status page

## Pending / Backlog
- [ ] P0: User must click "Save to Github"
- [ ] P1: Fix StrikeZone scraper offline
- [ ] P2: Test Genesis debrid resolvers
- [ ] P2: Full Kodi verification of all addons
- [ ] Backlog: IPTV/Live TV section for Syncher
