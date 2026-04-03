# Trakt Player - Changelog

## v2.0.0 (2026-02-03)

### Complete Rewrite
- Built from scratch for Kodi 21+ (Python 3)
- 100% native urllib - zero external dependencies
- Removed all legacy code, Umbrella references, and free stream scrapers
- Strictly torrent-based with Debrid resolution

### Click-and-Play
- Auto-plays the best available quality at 1080p or below
- No source selection dialog - click a movie or episode and it plays instantly
- Automatically discards 4K/2160p sources to maintain the <= 1080p rule
- Falls through up to 10 sources until one resolves via Debrid
- Progress bar shows scraper results and resolution attempts

### Trakt Scrobbling
- Automatic scrobble start/pause/stop via background service
- Marks movies and episodes as watched on Trakt at 80%+ playback
- Real-time progress sync to Trakt account

### Up Next
- Auto-play next episode when current episode ends
- Shows confirmation dialog (auto-closes after 15 seconds)
- Handles season boundaries (auto-advances to next season)
- Toggle on/off in Settings > Playback

### Continue Watching
- Resume movies and episodes from where you left off
- Synced via Trakt playback progress
- Shows percentage watched for each item

### Personalized Recommendations
- "Recommended For You" for both Movies and TV Shows
- Powered by Trakt's recommendation engine based on your watch history

### My Calendar
- Shows upcoming new episodes for shows you're watching
- 30-day lookahead from today
- Displays air date, show name, season/episode, and episode title

### Watch History
- Recently Watched Movies and Episodes
- Shows watch date for each item
- Full TMDB artwork and metadata

### Popular Community Lists
- Browse trending Trakt lists curated by the community
- Shows item count and likes for each list
- Click to browse any list's full contents

### Anticipated Content
- Most Anticipated upcoming Movies and TV Shows
- Based on Trakt community data

### Related Content ("More Like This")
- Context menu on any movie or show
- Shows related titles powered by Trakt
- Great for discovering similar content

### Rate on Trakt
- Context menu to rate any movie or show 1-10
- Syncs directly to your Trakt account
- Ratings: 1 (Awful) through 10 (Masterpiece)

### Add to Watchlist
- Quick-add any movie or show to your Trakt watchlist
- Available via context menu on all content

### Debrid Account Status
- Dashboard showing all Debrid service statuses
- Shows: Premium/Free, expiration date, days remaining, auto-renew status
- Color-coded: Green (30+ days), Yellow (8-30 days), Red (< 7 days or expired)
- Supports: Real-Debrid, AllDebrid, Premiumize, TorBox
- Also shows Trakt authorization status

### Debrid Services
- Real-Debrid: Full OAuth device flow, magnet resolution, video file selection
- AllDebrid: PIN-based auth, magnet upload and unlock
- Premiumize: OAuth device flow, direct download
- TorBox: API key auth, torrent creation and download

### Torrent Scrapers (5 Sources)
- PirateBay (API-based, multi-mirror)
- YTS (Movie-focused, high quality)
- EZTV (TV episode specialist)
- 1337x (General purpose)
- TorrentGalaxy (Backup scraper)

### Trakt Integration
- Device-based OAuth authentication
- Automatic token refresh on expiry
- Supports: Trending, Popular, Most Watched, Box Office, Genres
- Personal: Watchlist, Collection, Watched history
- All API calls use user's dedicated Trakt keys

### Donation Tab
- "Buy Me a Beer" with Ko-fi link and QR code
- Supports the addon developer

### Friends Activity Feed
- View list of Trakt friends
- See what friends are watching NOW (live status)
- Browse friend's recent watch history
- Click to play anything a friend watched

### User Stats Dashboard
- Total movies watched, episodes watched, shows completed
- Watch time in hours and days (movies + TV separately + total)
- Ratings distribution with visual bar chart
- Network stats: friends, followers, following

### Custom Trakt Lists
- Create new lists (Private, Friends, or Public)
- Browse and manage your custom lists
- Delete lists with confirmation dialog
- Add movies/shows to any custom list via context menu
- View item count and privacy status per list

### Cached Torrent Indicator
- Checks Real-Debrid, Premiumize, and AllDebrid cache before resolving
- Cached torrents prioritized for instant playback (no download wait)
- [CACHED] tag shown in progress dialog during resolution
- Cached count displayed in scraper progress

### AI Discovery (Vibe Marathons)
- 12 preset mood/vibe options (Rainy Night Thriller, Mind-Bending Sci-Fi, etc.)
- Custom vibe input - describe any mood and AI picks 12-15 titles
- Powered by OpenAI via Emergent proxy
- Uses your Trakt watch history for personalized picks
- Mix of well-known titles and hidden gems across decades

### TMDB Metadata
- Movie and TV show posters, backdrops, ratings, genres
- Season and episode artwork
- Optional user TMDB API key for better rate limits
