# Orion Kodi Addon - PRD

## Original Problem Statement
Customize Orion Kodi addon with Netflix-style UI, bigger poster tiles, cyan theme, season/episode flow.

## Architecture
```
/app/orion_work/plugin.video.orion/ (v3.6.2)
  addon.xml | main.py | resources/settings.xml
  resources/lib/ - Python dialogs and logic
  resources/skins/Default/1080i/ - XML skin files
```

## Implemented (v3.6.2)
- [x] Wider carousel tiles with proper TMDB poster art (movie/show titles visible)
- [x] All views use poster art instead of backdrop art
- [x] Cyan (#00D4FF) color scheme throughout
- [x] No name banner text overlays on tiles
- [x] SEASONS button on TV show detail dialog
- [x] Season dialog + Episode dialog XML bugs fixed (malformed `<label<` tags)
- [x] Season/Episode flow wired into all entry points
- [x] Back navigation fix (no more falling to Kodi default list)
- [x] Netflix-style search with grid results
- [x] Master skin on/off toggle in Settings
- [x] All emojis cleaned from Python and XML

## Backlog
### P1 - Phase 2 (Next)
- [ ] History view with Netflix-style tiles
- [ ] Favorites view with Netflix-style tiles
- [ ] Trakt view with Netflix-style tiles
- [ ] Netflix-style settings skin

### P2 - Future
- [ ] Episode progress bars and Continue Watching indicators
- [ ] Trakt sync for watch progress
- [ ] "Up Next" auto-play for episodes
