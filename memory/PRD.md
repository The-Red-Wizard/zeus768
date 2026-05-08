# Zeus768 Kodi Repository - Product Requirements

## Original Problem Statement
Maintain and upgrade the Zeus768 Kodi repository. The repository hosts multiple video addons for Kodi 21+ (Python 3) with debrid service integrations.

## Current Focus
Fix TorBox account linking/authorization across 4 addons: Orion, Trakt Player, Genesis, and SALTS.

## Architecture
```
/app/
├── addons.xml / addons.xml.md5
├── plugin.program.theaccountant/
├── plugin.video.genesis/
├── plugin.video.orion/
├── plugin.video.poseidonplayer/
├── plugin.video.salts/
├── plugin.video.tinklepad/
├── plugin.video.trakt_player/
├── plugin.video.vidscr/
├── plugin.video.zrtester/
├── program.poseidonguide/
├── repository.zeus768/
├── script.genesis.skins/
├── script.module.zeusresolvers/
├── scripts/
└── zips/
```

## What's Been Implemented

### May 8, 2026 - Repo Replaced + TorBox Fix
- Replaced entire local repo with user's latest GitHub zip
- Kept Vidscr v1.4.17 (user's latest upload)
- **Root cause**: TorBox `/user/auth/device/token` requires JSON POST, all addons sent form-urlencoded → HTTP 422
- **Trakt Player v2.5.0**: Fixed field names (`code` not `user_code`), `expires_at` handling, JSON POST
- **Orion v3.8.0**: Replaced manual API key with device code flow + JSON POST
- **SALTS v2.10.0**: Replaced manual API key with device code flow + JSON POST
- **Genesis v1.6.0**: Fixed poll to use JSON POST (field names/expiry already correct)
- All 4 zips rebuilt, addons.xml updated with all new versions, MD5 regenerated

## Addon Versions (current local)
| Addon | Version | Status |
|-------|---------|--------|
| Trakt Player | 2.5.0 | TorBox fixed |
| Orion | 3.8.0 | TorBox fixed |
| Genesis | 1.6.0 | TorBox fixed |
| SALTS | 2.10.0 | TorBox fixed |
| Vidscr | 1.4.17 | Latest from user |
| The Accountant | 3.9.7 | From GitHub |
| Poseidon Player | 2.3.0 | From GitHub |
| Poseidon Guide | 1.1.0 | From GitHub |
| Tinklepad | (from GitHub) | From GitHub |
| ZR Tester | (from GitHub) | From GitHub |
| Genesis Skins | 1.1.0 | From GitHub |
| Zeus Resolvers | (from GitHub) | From GitHub |

## Key Technical Details
- TorBox API: `/user/auth/device/start` (GET) → `code`, `device_code`, `friendly_verification_url`, `expires_at`
- TorBox API: `/user/auth/device/token` (POST JSON) → `{"device_code": "..."}` required as JSON body

## Backlog
- P2: IPTV/Live TV section (user requested on backburner)
