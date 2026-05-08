# Zeus768 Kodi Repository - Product Requirements

## Original Problem Statement
Maintain and upgrade the Zeus768 Kodi repository. The repository hosts multiple video addons for Kodi 21+ (Python 3) with debrid service integrations.

## Current Focus
Fix TorBox account linking/authorization across 4 addons: Orion, Trakt Player, Genesis, and SALTS.

## Architecture
```
/app/
├── addons.xml              # Master addon index
├── addons.xml.md5          # MD5 checksum
├── plugin.video.genesis/   # Genesis addon
├── plugin.video.orion/     # Orion addon
├── plugin.video.salts/     # SALTS addon
├── plugin.video.trakt_player/ # Trakt Player addon
├── plugin.video.poseidonplayer/
├── plugin.program.theaccountant/
├── program.poseidonguide/
├── repository.zeus768/
├── script.genesis.skins/   (on GitHub, not local)
├── script.module.zeusresolvers/ (on GitHub, not local)
├── plugin.video.vidscr/    (on GitHub, not local)
├── plugin.video.tinklepad/ (on GitHub, not local)
├── plugin.video.zrtester/  (on GitHub, not local)
└── zips/                   # Packaged addon zips
```

## What's Been Implemented

### Completed (May 8, 2026) - TorBox Device Code Auth Fix
- **Root cause**: TorBox `/user/auth/device/token` endpoint requires JSON POST body, but all 4 addons were sending form-urlencoded POST data → TorBox returned 422 "Input should be a valid dictionary"
- **Fix applied to all 4 addons**:
  - Trakt Player v2.5.0: Fixed JSON POST, correct field names (`code` not `user_code`), `expires_at` handling
  - Orion v3.8.0: Replaced manual API key entry with full device code flow (JSON POST)
  - SALTS v2.6.1: Replaced manual API key entry with full device code flow (JSON POST)
  - Genesis v9.5.0: Replaced manual API key entry in resolvers/torbox.py with device code flow
- Rebuilt all 4 zips, updated addons.xml, regenerated MD5

### Previously Completed
- Trakt Player v2.3.0: Fixed Premiumize (response_type), Real-Debrid auth, added TorBox/LinkSnappy
- Syncher v3.2.0-3.4.0: Music, AI Playlists, Radio, Podcasts, Audiobooks (NOTE: User removed Syncher from repo)

## GitHub Repo Versions (as of May 8, 2026)
- Genesis: v1.5.3
- Orion: v3.7.2
- Trakt Player: v2.4.2
- SALTS: v2.5.2

## Local Versions (post-fix)
- Genesis: v9.5.0
- Orion: v3.8.0
- Trakt Player: v2.5.0
- SALTS: v2.6.1

## Key Technical Details
- TorBox API: `/user/auth/device/start` (GET) → returns `code`, `device_code`, `friendly_verification_url`, `expires_at`
- TorBox API: `/user/auth/device/token` (POST JSON) → requires `{"device_code": "..."}` as JSON body
- Kodi Python 3 compatibility: Use `urllib.request`, `urllib.parse`, `urllib.error`

## Backlog
- P1: Remove Syncher from local repo (user deleted from GitHub)
- P1: Sync local repo fully with GitHub (missing addons: vidscr, tinklepad, zrtester, zeusresolvers)
- P2: IPTV/Live TV section (user requested on backburner)

## 3rd Party Integrations
- Trakt API, TMDB API
- Real-Debrid, Premiumize, AllDebrid, TorBox, LinkSnappy
- Emergent LLM Key (for AI features in Syncher - now defunct)
