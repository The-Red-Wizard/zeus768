# Orion Kodi Addon - PRD

## Original Problem Statement
Customize Orion Kodi addon with full Netflix-style UI, portrait poster tiles, cyan theme, season/episode flow, Up Next auto-play.

## Architecture
```
/app/orion_work/plugin.video.orion/ (v3.7.1)
  addon.xml | main.py | resources/settings.xml
  resources/lib/ - Python dialog modules (17 files)
  resources/skins/Default/1080i/ - XML skin files (10 dialogs)
```

## Implemented
- [x] Portrait poster carousel tiles on Main Menu and Submenus (185x280, 200x300)
- [x] BIG portrait poster grid cards (348x430px)
- [x] Full cyan (#00D4FF) color scheme
- [x] SEASONS button on TV show detail dialog
- [x] Season/Episode picker flow (SeasonDialog -> EpisodeDialog)
- [x] Netflix-style search with grid results
- [x] Netflix-style History grid
- [x] Netflix-style Favorites grid (Movies/TV picker)
- [x] Netflix-style Continue Watching grid
- [x] Netflix-style Trakt submenu
- [x] Netflix-style Settings panel
- [x] Master skin toggle (Settings > Appearance)
- [x] Cyan progress bars on all poster cards (Grid, MainMenu, Submenu, Episode)
- [x] Up Next auto-play dialog (UpNextDialog.xml + up_next.py)
- [x] Trakt scrobble sync during playback (start/pause/stop)
- [x] Episode playback monitor with progress saving
- [x] All emojis cleaned, all XML validated

## Backlog
### P2 - Future
- [ ] Resume Genesis addon work (on hold per user request)
