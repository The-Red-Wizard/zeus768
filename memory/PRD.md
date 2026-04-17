# Orion Kodi Addon - PRD

## Original Problem Statement
Customize Orion Kodi addon with full Netflix-style UI, bigger poster tiles, cyan theme, season/episode flow, and settings toggle.

## Architecture
```
/app/orion_work/plugin.video.orion/ (v3.7.0)
  addon.xml | main.py | resources/settings.xml
  resources/lib/ - Python dialog modules
  resources/skins/Default/1080i/ - XML skin files (9 dialogs)
```

## Implemented (v3.7.0)
- [x] Wider carousel tiles with proper TMDB poster art (titles baked in)
- [x] BIG portrait poster grid cards (348x430px) - no name banners
- [x] Full cyan (#00D4FF) color scheme throughout
- [x] SEASONS button on TV show detail (opens season/episode flow)
- [x] Season/Episode XML bugs fixed (malformed tags)
- [x] Back navigation: stays in Netflix skin, no Kodi default list fallback
- [x] Netflix-style search with grid results
- [x] **Netflix-style History** (grid with poster cards)
- [x] **Netflix-style Favorites** (Movies/TV picker then grid)
- [x] **Netflix-style Continue Watching** (grid with progress info)
- [x] **Netflix-style Trakt** (submenu with watchlist/lists/recommendations)
- [x] **Netflix-style Settings** (sidebar categories + setting rows, cyan theme)
- [x] Master skin toggle: Settings > Appearance > "Netflix-Style Skin"
- [x] All emojis cleaned, all XML validated

## Backlog
### P1 - Next
- [ ] Episode progress bars (cyan) on poster cards
- [ ] Trakt sync for watch progress
- [ ] "Up Next" auto-play for episodes

### P2 - Future
- [ ] Resume Genesis addon work (on hold per user request)
