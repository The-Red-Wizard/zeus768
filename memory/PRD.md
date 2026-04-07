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
- [x] Replaced with user's fixed v9.2.6 zip (Kodi 21 compatible)

### Genesis Themepak — v9.2.4
- [x] Replaced with user's fixed v9.2.4 zip (Kodi 21 compatible)

### SALTS — v2.6.0 (based on user's v2.5.3 + our fixes)
- [x] **Base**: User's v2.5.3 with file-based Trakt token storage and all their custom work
- [x] **Stremio scrapers**: Torrentio, MediaFusion, Comet, CyberFlix (free), Annatar, PeerFlix (free), EasyNews+
- [x] **Trakt scrobbling**: fires during playback (start at 2%, stop on finish)
- [x] **Trakt mark watched**: items marked after 80% playback completion
- [x] **Trakt watched overlay**: [W] tag + playcount on list items
- [x] **Trakt TMDB posters**: all Trakt list items show TMDB poster, fanart, ratings
- [x] **Trakt stale ADDON fix**: fresh xbmcaddon.Addon() for all settings reads/writes
- [x] 45+ scrapers total

### Trakt Player — v2.1.3 [STABLE]
### Orion — v3.2.5 [STABLE]
### The Accountant — v3.9.7 [STABLE]
### Poseidon Player — v2.3.0 [NEW]
### Poseidon Guide — v1.1.0 [NEW]

### Repository — v1.1.1
- [x] All 9 addons, StrikeZone removed
- [x] All zips rebuilt, MD5 regenerated

### StrikeZone — REMOVED FROM REPO

---

## Backlog
- [ ] Fix plugin.video.strikezone scraper offline, re-add to repo when ready
- [ ] Test all addons in user's Kodi installation
