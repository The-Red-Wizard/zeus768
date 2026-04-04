# Zeus768 Kodi Repository - PRD

## Problem Statement
Fix old Kodi addons for Kodi 21+ (Python 3). Addons: SALTS, Orion, StrikeZone, Trakt Player, Genesis, The Accountant.

## Architecture
- **Type**: Kodi Video Addons (Python 3), native `urllib` only (no `requests`)
- **APIs**: TMDB, Trakt, Real-Debrid, Premiumize, AllDebrid, TorBox, Orionoid, OpenAI (Emergent Proxy), Invidious
- **Ko-fi**: https://ko-fi.com/zeus768

---

## Completed (Feb 2026)

### Donation Tab (Buy Me a Beer) — ALL ADDONS
- [x] Genesis: Added buy_beer action with QR code + Ko-fi link
- [x] The Accountant: Added buy_beer action with QR code + Ko-fi link
- [x] SALTS, Orion, StrikeZone, Trakt Player: Made donation compact (single QR + dialog, removed multi-step select)
- [x] All addons use same pattern: download QR → ShowPicture → compact ok dialog → Action(Back)

### plugin.video.genesis — v2026.04.04.01 [IN REPO]
- [x] Added from user zip
- [x] Buy Me a Beer menu item added in navigator root()
- [x] Genesis Themepak (script.genesis.media v2026.04.04) also added

### plugin.video.salts (SALTS) — v2.5.0 [UPDATED]
- [x] **Concurrent scraping**: ThreadPoolExecutor (20 workers, 30s timeout) — all scrapers fire simultaneously
- [x] **24/7 Channels fixed**: Scrapers now properly instantiated (was calling methods on classes)
- [x] **24/7 Channels fixed**: Now uses `search()` instead of non-existent `get_movie_sources()`/`get_episode_sources()`
- [x] **Pre-scrape fixed**: Same instantiation + method bugs fixed, now concurrent (4 workers, 15s timeout)
- [x] Compact donation dialog

### plugin.video.trakt_player — v2.1.1 [STABLE]
- [x] Complete rewrite — 100% native urllib
- [x] Click-and-Play, Trakt Scrobbling, Up Next, Discovery Feed, AI Discovery
- [x] Compact donation dialog

### plugin.video.orion — v3.2.4 [STABLE]
- [x] Multi-scraper, Debrid support, Trakt, compact donation

### plugin.video.strikezone — v1.2.2 [STABLE]
- [x] Fight replays, search, favourites, compact donation

### plugin.program.theaccountant — v3.9.6 [UPDATED]
- [x] Speed Optimizer, Auto-Clean, Auth management
- [x] Buy Me a Beer added

### repository.zeus768 — v1.0.8 [STABLE]
- [x] All 8 addons registered in addons.xml
- [x] README.md with all addon icons and descriptions

---

## All Zips Rebuilt
- plugin.video.salts-2.5.0.zip
- plugin.video.orion-3.2.4.zip
- plugin.video.strikezone-1.2.2.zip
- plugin.video.trakt_player-2.1.1.zip
- plugin.program.theaccountant-3.9.6.zip
- plugin.video.genesis-2026.04.04.01.zip
- script.genesis.media-2026.04.04.zip
- repository.zeus768 (existing)

---

## Backlog
- [ ] Genesis: Audit for Python 3 / Kodi 21+ compatibility (uses Python 2 `urlparse`)
- [ ] Verify all addons stable in user's Kodi installation
