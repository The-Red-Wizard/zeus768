# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons for Kodi 21+ (Python 3). Rewrite broken addons, optimize scrapers, add donation support.

## Architecture
- **Type**: Kodi Video Addons (Python 3), native `urllib` only (no `requests`)
- **APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid
- **Ko-fi**: https://ko-fi.com/zeus768

---

## Completed (Feb 2026)

### Donation Tab (Buy Me a Beer) — ALL 7 ADDONS
- [x] Genesis: Added buy_beer action with QR code + Ko-fi link
- [x] The Accountant: Added buy_beer action with QR code + Ko-fi link
- [x] SALTS, Orion, StrikeZone, Trakt Player: Compact donation (single QR + dialog)

### plugin.video.genesis — v2026.04.04.01 [PYTHON 3 AUDITED]
- [x] Added from user zip
- [x] Buy Me a Beer added
- [x] **Full Python 3 / Kodi 21+ compatibility audit:**
  - Created `py3compat.py` shim (registers urlparse, urllib2, cookielib, httplib, HTMLParser, StringIO, Queue in sys.modules + patches builtins)
  - Fixed 145 Python files: removed `.encode('utf-8')`, `.decode('utf-8')`, `print` statements→functions, `except X, e:`→`except X as e:`, `long` literals, `__import__` level -1→0/1, `unicode()`→`str()`, `iconImage`/`thumbnailImage`→`setArt()`, `xbmc.LOGNOTICE`→`xbmc.LOGINFO`, `xbmc.translatePath`→`xbmcvfs.translatePath`, `reduce`→`functools.reduce`, `.translate(None,...)`→`re.sub`
  - All 147 files compile clean (0 failures)

### plugin.video.salts (SALTS) — v2.5.0 [SUPERFAST + 24/7 FIXED]
- [x] Concurrent scraping: ThreadPoolExecutor (20 workers, 30s timeout)
- [x] 24/7 Channels fixed: proper scraper instantiation + correct search() calls
- [x] Pre-scrape fixed: concurrent (4 workers, 15s timeout)
- [x] Compact donation dialog

### plugin.video.trakt_player — v2.1.1 [STABLE]
- [x] Complete rewrite, Click-and-Play, Trakt Scrobbling, Up Next, Discovery Feed
- [x] Compact donation dialog

### plugin.video.orion — v3.2.4 [STABLE]
- [x] Multi-scraper, Debrid support, compact donation

### plugin.video.strikezone — v1.2.2 [STABLE]
- [x] Fight replays, search, favourites, compact donation

### plugin.program.theaccountant — v3.9.6 [STABLE]
- [x] Speed Optimizer, Auto-Clean, Auth management, Buy Me a Beer added

### repository.zeus768 — v1.0.8 [STABLE]
- [x] 8 addons in addons.xml, README with icons

---

## All Zips Rebuilt
- plugin.video.genesis-2026.04.04.01.zip
- script.genesis.media-2026.04.04.zip
- plugin.video.salts-2.5.0.zip
- plugin.video.orion-3.2.4.zip
- plugin.video.strikezone-1.2.2.zip
- plugin.video.trakt_player-2.1.1.zip
- plugin.program.theaccountant-3.9.6.zip
- repository.zeus768

---

## Backlog
- [ ] Test all addons in user's Kodi installation
