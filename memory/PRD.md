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
- [x] Features Meteor, Streamthru, Torz, Webstreamr scrapers

### Genesis Themepak — v9.2.4
- [x] Replaced with user's fixed v9.2.4 zip (Kodi 21 compatible)

### SALTS — v2.6.0
- [x] 45+ scrapers: torrent sites, Stremio protocol, free streams, anime, international
- [x] **Stremio scrapers**: Torrentio, MediaFusion, Comet, CyberFlix (free), Annatar, PeerFlix (free), EasyNews+
- [x] **Trakt scrobbling**: fires during playback (start at 2%, stop on finish)
- [x] **Trakt mark watched**: items marked after 80% playback completion
- [x] **Trakt watched overlay**: [W] tag + playcount on list items
- [x] **Trakt TMDB posters**: all Trakt list items show TMDB poster, fanart, ratings
- [x] **Trakt stale ADDON fix**: fresh xbmcaddon.Addon() in all settings reads/writes (same fix as Trakt Player)
- [x] Concurrent scraping: ThreadPoolExecutor (20 workers, 30s timeout)
- [x] 24/7 Channels, Skip Intro, Up Next, Pre-Scrape hover cache
- [x] Buy Me a Beer (Ko-fi) donation dialog

### Trakt Player — v2.1.3 [STABLE]
### Orion — v3.2.5 [STABLE]
### The Accountant — v3.9.7 [STABLE]

### Poseidon Player — v2.3.0 [NEW]
- [x] Premium Xtream Codes IPTV Player with EPG Grid

### Poseidon Guide — v1.1.0 [NEW]
- [x] EPG Grid Guide for Poseidon Player

### Repository — v1.1.1
- [x] All 9 addons, StrikeZone removed
- [x] All zips rebuilt, MD5 regenerated

### StrikeZone — REMOVED FROM REPO

---

## Backlog
- [ ] Fix plugin.video.strikezone scraper offline, re-add to repo when ready
- [ ] Test all addons in user's Kodi installation
