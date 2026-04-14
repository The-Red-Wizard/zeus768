# Orion Kodi Addon - PRD

## Original Problem Statement
User wants to customize the Orion Kodi addon (plugin.video.orion v3.4.5):
1. Make thumbnails bigger and stretched horizontally (landscape)
2. Remove name banners from posters
3. Change color scheme to cyan (#00D4FF)
4. Add Netflix-style TV show season dropdown selector and episode grid thumbnails
5. Netflix-style search skin
6. Settings toggle to switch between Netflix skin and classic list view

## Architecture
```
/app/orion_work/plugin.video.orion/
  addon.xml (v3.6.0)
  main.py (Main router - 3797 lines)
  resources/
    settings.xml (Addon settings with master skin toggle)
    lib/
      main_menu.py (Sidebar home screen dialog)
      submenu.py (Netflix-style Movies/TV/Kids submenu)
      detail.py (Movie/TV detail dialog)
      grid.py (Paginated grid view)
      link_picker.py (Source picker dialog)
      search_results.py (Netflix-style search results)
      season_dialog.py (Season selector)
      episode_dialog.py (Episode grid)
      tmdb.py (TMDB API)
      scraper.py (Torrent scrapers)
      debrid.py (Real-Debrid, Premiumize, AllDebrid, TorBox)
      trakt.py (Trakt integration)
      database.py (History, favorites, watch progress)
      resolver.py (Link resolver)
      qrcode_helper.py (QR code display)
    skins/Default/1080i/
      MainMenuDialog.xml (Home screen - landscape, cyan, no banners)
      SubmenuDialog.xml (Movies/TV browse - landscape, cyan, no banners)
      DetailDialog.xml (Movie/TV detail overlay)
      GridDialog.xml (Paginated grid view - landscape, cyan)
      SearchResultsDialog.xml (Search results grid - landscape, cyan)
      LinkPickerDialog.xml (Source picker - cyan theme)
      SeasonDialog.xml (Season selector)
      EpisodeDialog.xml (Episode grid)
  resources/icons/ (Category icons)
```

## What's Been Implemented (v3.6.0)
- [x] Landscape horizontal thumbnails across ALL views (MainMenu, Submenu, Grid, Search, LinkPicker)
- [x] Name banners removed from poster cards
- [x] Full cyan (#00D4FF) color scheme throughout all XML skins
- [x] All purple accents (FF6366F1, FF8B5CF6) replaced with cyan
- [x] All emojis cleaned from Python and XML files
- [x] Netflix-style search with fullscreen grid results (SearchResultsDialog + search_results.py)
- [x] Master skin toggle in Settings > Appearance > "Enable Netflix-Style Skin"
  - Controls: Main Menu, Submenus, Link Picker, Search
  - When OFF: Falls back to classic Kodi list views
- [x] Backdrop/thumb art used for landscape card images
- [x] Core control IDs preserved (100, 200, 205, 210, 215, etc.)
- [x] Netflix-style sidebar main menu (MainMenuDialog)
- [x] Netflix-style submenu for Movies, TV Shows, Kids (SubmenuDialog)
- [x] Detail dialog with Trailer/Play/Favorite (DetailDialog)
- [x] Paginated grid view (GridDialog)
- [x] Fullscreen link picker (LinkPickerDialog)
- [x] Season/Episode dialog XMLs exist (SeasonDialog, EpisodeDialog)

## Prioritized Backlog

### P0 - In Progress
- [ ] User validation of v3.6.0 visual changes in Kodi

### P1 - Next
- [ ] Safely integrate Season/Episode dialogs into TV show flow (hook into detail.py PLAY button for TV shows -> open SeasonDialog -> EpisodeDialog)
- [ ] Episode progress bars (cyan) and "Continue Watching" indicators
- [ ] Trakt sync for watch progress
- [ ] "Up Next" auto-play for episodes

### P2 - Future
- [ ] Resume Genesis addon work (on hold per user request)

## Key Safety Rules
- NEVER use Unicode emojis in Python strings or XML labels
- NEVER overwrite core control IDs in XML skins
- Always test by zipping and uploading to GoFile for user to test in Kodi
- Master skin toggle: `netflix_skin_enabled` setting controls all Netflix-style views

## Delivery
- GoFile upload: `zip -r plugin.video.orion-vX.X.zip plugin.video.orion && curl -F "file=@zip" https://store1.gofile.io/uploadFile`
