# Genesis Kodi Addon PRD

## Original Problem Statement
Fix a Kodi addon (specto-master) and transform it into "Genesis" with:
- New name: Genesis
- Author: zeus768
- Custom icon and fanart provided by user
- Remove all references to previous author/addon name
- Make scrapers torrent-based with cached torrents
- Add 5 torrent scrapers
- Add TorBox support
- Debrid services (Real-Debrid, Premiumize, AllDebrid) via PIN system
- Update Trakt API keys with user's credentials

## User Personas
- Kodi power users who want torrent-based streaming
- Users with debrid service subscriptions
- Users wanting Trakt integration for watchlists

## Core Requirements (Static)
1. Addon rebrand from Specto to Genesis
2. Change author from mrknow/lambda to zeus768
3. 5 torrent-based scrapers
4. TorBox debrid support
5. PIN-based authentication for all debrid services
6. Trakt integration with user's API keys

## What's Been Implemented (April 4, 2026)
1. **Addon Rebrand Complete**
   - Renamed from plugin.video.specto to plugin.video.genesis
   - Updated all addon.xml files with new name, author (zeus768), version
   - Replaced icon.png and fanart.jpg with user-provided images
   - Updated all copyright headers and references

2. **Trakt API Keys Updated**
   - Client ID: 215436e27377a2e330cd8406ac1cd19de93eb956c3af50242ddf92c20e604f76
   - Client Secret: 9cc86f0c0aa4fb8d38fa1fd9d5daecceb7d25700ca1319416543a06591746468

3. **5 Torrent Scrapers Added**
   - 1337x (Movies & TV Shows)
   - TorrentGalaxy (Movies & TV Shows)
   - YTS (Movies only)
   - EZTV (TV Shows only)
   - ThePirateBay (Movies & TV Shows)

4. **Debrid Services with PIN Authentication**
   - Real-Debrid: Device code flow (OAuth)
   - Premiumize: Device code flow
   - AllDebrid: Device code flow (PIN)
   - TorBox: API key input flow

5. **Cached Torrent Support**
   - Cache checking functions for all debrid services
   - Direct download from cache when available

6. **Old Scrapers Removed**
   - All old streaming scrapers removed (28 scrapers)

## Addon Files
- Main addon: plugin.video.genesis.zip
- Theme pack: script.genesis.media.zip

## Backlog
- P1: Test on actual Kodi installation
- P2: Add more torrent scrapers if needed
- P2: Add subtitle support for torrents
- P3: Add custom filter options for torrent quality

## Next Tasks
1. User should test the addon on their Kodi installation
2. Configure debrid service(s) in settings
3. Authorize Trakt for watchlist sync
