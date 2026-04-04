# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons for Kodi 21+ (Python 3). Rewrite broken addons, optimize scrapers, add donation support.

## Architecture
- **Type**: Kodi Addons (Python 3), native `urllib` only (no `requests`)
- **APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid
- **Ko-fi**: https://ko-fi.com/zeus768

---

## Completed

### Genesis — v2026.04.04.02
- [x] Full Python 3 / Kodi 21+ audit (147 files, 0 failures)
- [x] py3compat.py shim for transparent Python 2 module compatibility
- [x] Removed dead dependencies (script.mrknow.urlresolver, script.module.metahandler)
- [x] xbmc.python version bumped to 3.0.0
- [x] Resolvers __init__.py: urlresolver9 made optional, falls back to resolveurl
- [x] Buy Me a Beer added
- [x] Assets block added to addon.xml

### SALTS — v2.5.1
- [x] Concurrent scraping: ThreadPoolExecutor (20 workers, 30s timeout)
- [x] 24/7 Channels fixed: proper scraper instantiation + correct search()
- [x] 24/7 Channels: stops when user quits stream (user-stop detection via position tracking)
- [x] Pre-scrape fixed: concurrent (4 workers, 15s timeout)
- [x] Compact donation dialog

### StrikeZone — v1.2.3
- [x] Rewrote scraper.py from requests+BeautifulSoup → native urllib+regex
- [x] Removed dead dependencies (requests, beautifulsoup4)
- [x] resolveurl made optional

### Genesis Themepak — v2026.04.04
- [x] xbmc.python bumped to 3.0.0
- [x] Icon/fanart matched to Genesis branding

### Trakt Player — v2.1.1 [STABLE]
### Orion — v3.2.4 [STABLE]
### The Accountant — v3.9.6 [STABLE]
### Repository — v1.0.9 [STABLE]

---

## Backlog
- [ ] Test all addons in user's Kodi installation
