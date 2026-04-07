# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons for Kodi 21+ (Python 3). Rewrite broken addons, optimize scrapers, add donation support.

## Architecture
- **Type**: Kodi Addons (Python 3), native `urllib` only (no `requests`)
- **APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid, Stremio Protocol
- **Ko-fi**: https://ko-fi.com/zeus768

---

## Completed

### Genesis — v9.2.6
- [x] User's fixed v9.2.6 zip (Kodi 21 compatible)

### Genesis Themepak — v9.2.4
- [x] User's fixed v9.2.4 zip

### SALTS — v2.6.0 (user's v2.5.3 base + fixes)
- [x] 45+ scrapers: 7 Stremio (Torrentio, MediaFusion, Comet, CyberFlix, Annatar, PeerFlix, EasyNews+)
- [x] Trakt scrobbling, mark watched, TMDB posters, watched overlay
- [x] Stale ADDON fix (fresh xbmcaddon.Addon())

### Trakt Player — v2.2.0 (user's v2.1.6 base + features merged)
- [x] **Base**: User's v2.1.6 with file-based token storage, filehost.py, faster TMDB loading
- [x] **Premiumize fix**: OAuth device code was hitting /api/token instead of /token
- [x] **Merged features**: AI Vibes, Discovery Feed, Continue Watching, Recommendations, Calendar, Friends, Stats, Custom Lists, Account Status, Buy Me a Beer, Rate/Watchlist/Add to List
- [x] **debrid.py helpers**: get_active_services, check_cache_all, resolve_magnet, get_all_account_info

### Orion — v3.2.5 [STABLE]
### The Accountant — v3.9.7 [STABLE]
### Poseidon Player — v2.3.0
### Poseidon Guide — v1.1.0
### Repository — v1.1.1

### StrikeZone — REMOVED FROM REPO

---

## Backlog
- [ ] Fix plugin.video.strikezone scraper offline, re-add later
- [ ] User verification of all addons in Kodi
