# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons for Kodi 21+ (Python 3). Rewrite broken addons, optimize scrapers, add donation support.

## Architecture
- **Type**: Kodi Addons (Python 3), native `urllib` only (no `requests`)
- **APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid
- **Ko-fi**: https://ko-fi.com/zeus768

---

## Completed

### Genesis — v9.2.6
- [x] Replaced with user's fixed v9.2.6 zip (Kodi 21 compatible)
- [x] Features Meteor, Streamthru, Torz, Webstreamr scrapers
- [x] Buy Me a Beer added
- [x] Assets block in addon.xml

### Genesis Themepak — v9.2.4
- [x] Replaced with user's fixed v9.2.4 zip (Kodi 21 compatible)

### SALTS — v2.5.2
- [x] Concurrent scraping: ThreadPoolExecutor (20 workers, 30s timeout)
- [x] 24/7 Channels fixed: proper scraper instantiation + correct search()
- [x] 24/7 Channels: stops when user quits stream
- [x] Pre-scrape fixed: concurrent (4 workers, 15s timeout)
- [x] Compact donation dialog

### Trakt Player — v2.1.3 [STABLE]
- [x] Real-Debrid & Premiumize pair code OAuth fixed
- [x] Settings persistence fixed (fresh xbmcaddon.Addon() instances)

### Orion — v3.2.5 [STABLE]
### The Accountant — v3.9.7 [STABLE]

### Poseidon Player — v2.3.0 [NEW]
- [x] Added to repository from user's zip
- [x] Premium Xtream Codes IPTV Player with EPG Grid

### Poseidon Guide — v1.1.0 [NEW]
- [x] Added to repository from user's zip
- [x] EPG Grid Guide for Poseidon Player

### Repository — v1.1.1
- [x] Updated addons.xml with all 9 addons (StrikeZone removed)
- [x] All zips rebuilt with icon/fanart in zip folders
- [x] MD5 checksum regenerated
- [x] README updated with Poseidon addons, StrikeZone removed
- [x] repository.zeus768 addon.xml bumped to v1.1.1

### StrikeZone — REMOVED FROM REPO
- [x] Removed from addons.xml, zips, and README per user request

---

## Backlog
- [ ] Fix plugin.video.strikezone scraper offline, re-add to repo when ready
- [ ] Test all addons in user's Kodi installation
