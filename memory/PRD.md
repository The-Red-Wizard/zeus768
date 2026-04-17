# Orion Kodi Addon - PRD

## Original Problem Statement
User wants to customize the Orion Kodi addon (plugin.video.orion v3.4.5):
1. Make thumbnails bigger and stretched horizontally (landscape) - later changed to BIG portrait poster cards for grid
2. Remove name banners from posters
3. Change color scheme to cyan (#00D4FF)
4. Add Netflix-style TV show season dropdown selector and episode grid thumbnails
5. Netflix-style search skin
6. Settings toggle to switch between Netflix skin and classic list view

## Architecture
```
/app/orion_work/plugin.video.orion/
  addon.xml (v3.6.1)
  main.py (Main router)
  resources/
    settings.xml (Addon settings with master skin toggle)
    lib/
      main_menu.py - Sidebar home screen dialog
      submenu.py - Netflix-style Movies/TV/Kids submenu
      detail.py - Movie/TV detail dialog (SEASONS btn for TV)
      grid.py - Paginated grid view (BIG portrait poster cards)
      link_picker.py - Source picker dialog
      search_results.py - Netflix-style search results
      season_dialog.py - Season selector dialog
      episode_dialog.py - Episode grid dialog
      tmdb.py, scraper.py, debrid.py, trakt.py, database.py, resolver.py, qrcode_helper.py
    skins/Default/1080i/
      MainMenuDialog.xml - Home (landscape cards, cyan)
      SubmenuDialog.xml - Browse (landscape cards, cyan)
      DetailDialog.xml - Detail overlay (SEASONS btn for TV shows)
      GridDialog.xml - Paginated grid (BIG portrait posters, no banners)
      SearchResultsDialog.xml - Search grid (landscape, cyan)
      LinkPickerDialog.xml - Source picker (cyan)
      SeasonDialog.xml - Season selector
      EpisodeDialog.xml - Episode grid
```

## What's Been Implemented
- [x] BIG portrait poster cards in GridDialog (348x430px) - no name banners, rating+year badges
- [x] Landscape horizontal thumbnails in MainMenu and Submenu views
- [x] Full cyan (#00D4FF) color scheme - all purple accents replaced
- [x] All emojis cleaned from Python and XML files
- [x] Netflix-style search (SearchResultsDialog + search_results.py)
- [x] Master skin toggle: Settings > Appearance > "Enable Netflix-Style Skin"
- [x] SEASONS button on TV show detail dialog (replaces PLAY for TV shows)
- [x] Netflix-style season/episode flow: SeasonDialog -> EpisodeDialog -> sources
- [x] Fixed season_dialog.py and episode_dialog.py constructors (wrong path)
- [x] All detail dialog handlers updated to support 'seasons' action
- [x] TV show items in submenu/grid/main menu route through Netflix season picker

## Prioritized Backlog

### P0 - Awaiting User Testing
- [ ] User validation of v3.6.1 in Kodi

### P1 - Next
- [ ] Episode progress bars (cyan) and "Continue Watching" indicators
- [ ] Trakt sync for watch progress
- [ ] "Up Next" auto-play for episodes

### P2 - Future
- [ ] Resume Genesis addon work (on hold per user request)

## Key Safety Rules
- NEVER use Unicode emojis in Python strings or XML labels
- NEVER overwrite core control IDs in XML skins
- Delivery: zip + GoFile upload
- Master skin toggle: `netflix_skin_enabled` controls all Netflix views
