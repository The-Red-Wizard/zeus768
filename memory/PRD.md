# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons for Kodi 21+ (Python 3). Rewrite broken addons, optimize scrapers, add donation support.

## Architecture
- **Type**: Kodi Addons (Python 3), native `urllib` only (no `requests`)
- **APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid, Stremio Protocol
- **Ko-fi**: https://ko-fi.com/zeus768

---

## Completed

### Genesis — v9.3.0 (major Python 3 fix + external scrapers)
- [x] Fixed `default.py` Python 3 import (`import urlparse` → `from urllib.parse import parse_qsl`)
- [x] Fixed Trakt auth URL: `api-v2launch.trakt.tv` → `api.trakt.tv` (HTTPS)
- [x] Fixed all 4 debrid resolvers (RD, PM, AD, TorBox) Python 3 imports
- [x] Fixed player.py `unicode()` calls → Python 3 `bytes.decode()`
- [x] Fixed all 9 torrent/streaming scrapers Python 3 imports
- [x] Fixed all 90+ old resolvers Python 3 imports (batch-patched)
- [x] Fixed missing genre icons — falls back to addon icon when theme image not found
- [x] Added CocoScrapers external provider (`cocoscrapers_mv_tv.py`)
- [x] Added Gears Scrapers external provider (`gears_mv_tv.py`)
- [x] Added `script.module.cocoscrapers` and `script.module.gears` as optional dependencies
- [x] Added External Scrapers settings category

### Genesis Themepak — v9.2.4

### SALTS — v2.6.0 (user's v2.5.3 base + fixes)
- [x] 45+ scrapers: 7 Stremio + torrent + free streams
- [x] Trakt scrobbling, mark watched, TMDB posters, watched overlay
- [x] Stale ADDON fix

### Trakt Player — v2.2.0 (user's v2.1.6 base + features merged)
- [x] Premiumize device code fix
- [x] AI Vibes, Discovery Feed, Continue Watching, all superpower features merged

### Orion — v3.2.5 [STABLE]
### The Accountant — v3.9.7 [STABLE]
### Poseidon Player — v2.3.0
### Poseidon Guide — v1.1.0
### Repository — v1.1.1

### StrikeZone — REMOVED

---

## Backlog
- [ ] Fix plugin.video.strikezone scraper offline, re-add later
- [ ] User verification of all addons in Kodi
