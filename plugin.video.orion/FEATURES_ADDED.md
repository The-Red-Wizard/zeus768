# Orion Plugin - Auto-Play Next Episode & Intro Skip Features

## New Features Added

### 1. Auto-Play Next Episode with Countdown
- **Trigger Time**: Countdown starts 60 seconds (1 minute) before episode ends
- **Default Countdown**: 5 seconds (configurable: 5, 10, 15, 20, 30 seconds)
- **Enabled by Default**: Yes
- **Smart Detection**: Automatically detects next episode in same season or first episode of next season
- **User Control**: Users can cancel countdown by pressing Back/Escape during countdown

### 2. Intro Skipping
- **Detection Method**: Uses TMDB episode data + intelligent heuristics
  - Sitcoms (20-25 min): ~45 second intro
  - Dramas (40-50 min): ~75 second intro  
  - Long-form (50+ min): ~90 second intro
- **Skip Modes**:
  - **Manual** (default): Shows notification with intro duration, user can manually seek
  - **Auto-skip**: Automatically skips intro when detected
- **Fallback Duration**: 90 seconds (configurable: 30, 60, 90, 120 seconds)
- **Enabled by Default**: Yes

## Settings Location

Go to **Settings → Playback** to configure:

### Auto-Play Next Episode Settings
- `Auto-play next episode` - Enable/disable feature (ON by default)
- `Auto-play countdown (seconds)` - Duration of countdown (5-30 seconds, default: 5)

### Intro Skip Settings  
- `Enable intro skipping` - Enable/disable feature (ON by default)
- `Auto-skip intros (no button)` - When ON, automatically skips intros without user interaction (OFF by default)
- `Fallback intro duration (seconds)` - Duration to use when TMDB data unavailable (30-120 seconds, default: 90)

## Technical Implementation

### Files Modified
1. `/resources/settings.xml` - Added new settings for both features
2. `/resources/lib/tmdb.py` - Added functions to fetch episode intro markers and runtime data
3. `/resources/lib/up_next.py` - Updated to support configurable countdown and fallback dialog
4. `/main.py` - Updated `_monitor_episode_playback()` to:
   - Trigger countdown at 60 seconds before end (instead of 2 minutes)
   - Use configurable countdown from settings
   - Detect and skip intros based on TMDB data
   - Support both manual and auto-skip modes

### Files Created
1. `/resources/lib/playback_monitor.py` - Standalone playback monitor (for future enhancements)
2. `/resources/lib/intro_skipper.py` - Intro skip dialog and utilities

## How It Works

### Auto-Play Next Episode Flow
1. User plays TV show episode
2. Playback monitor tracks episode progress
3. At 60 seconds before end (during credits), countdown appears
4. User can:
   - Let it auto-play (countdown reaches 0)
   - Press OK/Select to play immediately
   - Press Back/Escape to cancel
5. If approved, current episode stops and next episode starts automatically

### Intro Skip Flow
1. Episode playback starts
2. Between 5-180 seconds (depending on detection), system checks for intro
3. TMDB episode data is fetched for runtime
4. Intro duration calculated based on episode type
5. If **Auto-skip** enabled:
   - Automatically seeks past intro
   - Shows notification "Intro skipped"
6. If **Manual** mode:
   - Shows notification with skip timestamp
   - User can manually seek to skip intro

## User Benefits
- **Binge-watching made easy**: No need to manually start next episode
- **Skip repetitive intros**: Save time by skipping show intros automatically
- **Fully configurable**: Users can adjust countdown duration and intro skip behavior
- **Smart defaults**: Works out of the box with sensible defaults
- **Respects user choice**: Easy to cancel or disable features

## Testing Recommendations
1. Play a TV show episode
2. Watch for intro skip notification in first 2 minutes
3. Let episode play until 1 minute remaining
4. Observe countdown dialog appearance
5. Test canceling countdown with Back button
6. Test letting countdown complete to auto-play
7. Verify settings changes take effect immediately
