# Zeus768 Kodi Repository - PRD

## Original Problem Statement
Maintain and upgrade the Zeus768 custom Kodi repository with multiple addons.

## Architecture
```
/app/
├── addons.xml / addons.xml.md5
├── plugin.video.syncher/             # v3.4.0 - All-in-One (Music AI, Podcasts, Audiobooks, Radio)
├── plugin.video.trakt_player/        # v2.3.0 - 5 Debrid services + auth fixes + account info
├── plugin.video.genesis/             # v9.4.1
├── plugin.video.salts/               # v2.6.0
├── Other addons...
└── zips/
```

## Completed Tasks
- [x] Genesis v9.4.1: Python 3, TMDB/Trakt migration, auth fixes
- [x] Syncher v3.4.0: Movies, TV, Sports, Music (AI+Deezer+Radio), Podcasts, Audiobooks
- [x] **Trakt Player v2.3.0**: Debrid overhaul
  - FIXED: Premiumize auth (response_type vs grant_type)
  - FIXED: Real-Debrid false "expired" errors
  - ADDED: TorBox (device code auth, cache check, magnet resolve, account info)
  - ADDED: LinkSnappy (login auth, 30+ file host link gen, account info)
  - ADDED: Real account_info() for all 5 services (RD/AD/PM/TB/LS)
  - ADDED: Color-coded expiry warnings on Account Status page
  - Updated settings.xml with TorBox + LinkSnappy categories
  - Updated changelog

## Pending / Backlog
- [ ] P0: User must click "Save to Github"
- [ ] P1: Fix StrikeZone scraper offline
- [ ] P2: Test Genesis debrid resolvers
- [ ] P2: Full Kodi verification of all addons
- [ ] Backlog: IPTV/Live TV section for Syncher
