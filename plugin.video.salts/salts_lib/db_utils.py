"""
SALTS Library - Database utilities
Revived by zeus768 for Kodi 21+
"""
import os
import time
import json
import sqlite3
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

class DB_Connection:
 def __init__(self):
 if not os.path.exists(ADDON_DATA):
 os.makedirs(ADDON_DATA)
 self.db_path = os.path.join(ADDON_DATA, 'salts.db')
 self._create_tables()
 
 def _get_connection(self):
 return sqlite3.connect(self.db_path)
 
 def _create_tables(self):
 """Create database tables if they don't exist"""
 conn = self._get_connection()
 cursor = conn.cursor()
 
 # URL cache table
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS url_cache (
 url TEXT PRIMARY KEY,
 response TEXT,
 timestamp REAL
 )
 ''')
 
 # Related URL table
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS related_url (
 video_type TEXT,
 title TEXT,
 year TEXT,
 source TEXT,
 rel_url TEXT,
 season TEXT DEFAULT '',
 episode TEXT DEFAULT '',
 PRIMARY KEY (video_type, title, year, source, season, episode)
 )
 ''')
 
 # Settings table
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS settings (
 setting TEXT PRIMARY KEY,
 value TEXT
 )
 ''')
 
 # Search history
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS search_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 section TEXT,
 query TEXT,
 timestamp REAL
 )
 ''')
 
 # Source cache - stores scraped results per title
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS source_cache (
 cache_key TEXT PRIMARY KEY,
 sources TEXT,
 timestamp REAL
 )
 ''')
 
 # Favorites / Bookmarks
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS favorites (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 media_type TEXT,
 title TEXT,
 year TEXT DEFAULT '',
 tmdb_id TEXT DEFAULT '',
 poster TEXT DEFAULT '',
 fanart TEXT DEFAULT '',
 overview TEXT DEFAULT '',
 rating REAL DEFAULT 0,
 season TEXT DEFAULT '',
 episode TEXT DEFAULT '',
 timestamp REAL,
 UNIQUE(media_type, title, year, season, episode)
 )
 ''')
 
 # Scraper priority ordering
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS scraper_priority (
 scraper_name TEXT PRIMARY KEY,
 priority INTEGER DEFAULT 100
 )
 ''')
 
 # Quality presets
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS quality_presets (
 name TEXT PRIMARY KEY,
 settings TEXT
 )
 ''')
 
 # Hover/pre-scrape cache (24hr TTL)
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS hover_cache (
 cache_key TEXT PRIMARY KEY,
 sources TEXT,
 timestamp REAL
 )
 ''')
 
 conn.commit()
 conn.close()
 
 # ==================== URL Cache ====================
 
 def cache_url(self, url, response):
 """Cache a URL response"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'INSERT OR REPLACE INTO url_cache (url, response, timestamp) VALUES (?, ?, ?)',
 (url, response, time.time())
 )
 conn.commit()
 conn.close()
 
 def get_cached_url(self, url, cache_limit=8):
 """Get cached URL response if still valid"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'SELECT response, timestamp FROM url_cache WHERE url = ?',
 (url,)
 )
 result = cursor.fetchone()
 conn.close()
 
 if result:
 response, timestamp = result
 age = (time.time() - timestamp) / 3600
 if age < cache_limit:
 return timestamp, response
 
 return None, None
 
 def flush_cache(self):
 """Clear all cached URLs and source cache"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('DELETE FROM url_cache')
 cursor.execute('DELETE FROM source_cache')
 conn.commit()
 conn.close()
 
 # ==================== Source Cache ====================
 
 def cache_sources(self, cache_key, sources):
 """Cache scraped sources for a title"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'INSERT OR REPLACE INTO source_cache (cache_key, sources, timestamp) VALUES (?, ?, ?)',
 (cache_key, json.dumps(sources), time.time())
 )
 conn.commit()
 conn.close()
 
 def get_cached_sources(self, cache_key, cache_limit_hours=2):
 """Get cached sources if still valid"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'SELECT sources, timestamp FROM source_cache WHERE cache_key = ?',
 (cache_key,)
 )
 result = cursor.fetchone()
 conn.close()
 
 if result:
 sources_json, timestamp = result
 age = (time.time() - timestamp) / 3600
 if age < cache_limit_hours:
 return json.loads(sources_json), timestamp
 
 return None, None
 
 def clear_source_cache(self):
 """Clear source cache only"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('DELETE FROM source_cache')
 conn.commit()
 conn.close()
 
 # ==================== Hover / Pre-Scrape Cache ====================
 
 def cache_hover(self, cache_key, sources):
 """Cache pre-scraped hover results (24hr TTL)"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'INSERT OR REPLACE INTO hover_cache (cache_key, sources, timestamp) VALUES (?, ?, ?)',
 (cache_key, json.dumps(sources), time.time())
 )
 conn.commit()
 conn.close()
 
 def get_hover_cache(self, cache_key, cache_limit_hours=24):
 """Get pre-scraped hover cache if still valid"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'SELECT sources, timestamp FROM hover_cache WHERE cache_key = ?',
 (cache_key,)
 )
 result = cursor.fetchone()
 conn.close()
 
 if result:
 sources_json, timestamp = result
 age = (time.time() - timestamp) / 3600
 if age < cache_limit_hours:
 return json.loads(sources_json)
 
 return None
 
 def clear_hover_cache(self):
 """Clear hover/pre-scrape cache"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('DELETE FROM hover_cache')
 conn.commit()
 conn.close()
 
 def prune_hover_cache(self, max_age_hours=24):
 """Remove expired hover cache entries"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cutoff = time.time() - (max_age_hours * 3600)
 cursor.execute('DELETE FROM hover_cache WHERE timestamp < ?', (cutoff,))
 conn.commit()
 conn.close()
 
 # ==================== Favorites ====================
 
 def add_favorite(self, media_type, title, year='', tmdb_id='',
 poster='', fanart='', overview='', rating=0,
 season='', episode=''):
 """Add to favorites"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 '''INSERT OR REPLACE INTO favorites 
 (media_type, title, year, tmdb_id, poster, fanart, overview, rating, season, episode, timestamp) 
 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
 (media_type, title, year, tmdb_id, poster, fanart, overview, rating, season, episode, time.time())
 )
 conn.commit()
 conn.close()
 
 def remove_favorite(self, media_type, title, year='', season='', episode=''):
 """Remove from favorites"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 '''DELETE FROM favorites 
 WHERE media_type = ? AND title = ? AND year = ? AND season = ? AND episode = ?''',
 (media_type, title, year, season, episode)
 )
 conn.commit()
 conn.close()
 
 def get_favorites(self, media_type=None):
 """Get all favorites, optionally filtered by media type"""
 conn = self._get_connection()
 cursor = conn.cursor()
 if media_type:
 cursor.execute(
 'SELECT * FROM favorites WHERE media_type = ? ORDER BY timestamp DESC',
 (media_type,)
 )
 else:
 cursor.execute('SELECT * FROM favorites ORDER BY timestamp DESC')
 
 columns = [d[0] for d in cursor.description]
 results = [dict(zip(columns, row)) for row in cursor.fetchall()]
 conn.close()
 return results
 
 def is_favorite(self, media_type, title, year='', season='', episode=''):
 """Check if item is in favorites"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 '''SELECT COUNT(*) FROM favorites 
 WHERE media_type = ? AND title = ? AND year = ? AND season = ? AND episode = ?''',
 (media_type, title, year, season, episode)
 )
 count = cursor.fetchone()[0]
 conn.close()
 return count > 0
 
 # ==================== Scraper Priority ====================
 
 def set_scraper_priority(self, scraper_name, priority):
 """Set priority for a scraper (lower = higher priority)"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'INSERT OR REPLACE INTO scraper_priority (scraper_name, priority) VALUES (?, ?)',
 (scraper_name, priority)
 )
 conn.commit()
 conn.close()
 
 def get_scraper_priority(self, scraper_name):
 """Get priority for a scraper"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'SELECT priority FROM scraper_priority WHERE scraper_name = ?',
 (scraper_name,)
 )
 result = cursor.fetchone()
 conn.close()
 return result[0] if result else 100
 
 def get_all_scraper_priorities(self):
 """Get all scraper priorities"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('SELECT scraper_name, priority FROM scraper_priority ORDER BY priority')
 results = {row[0]: row[1] for row in cursor.fetchall()}
 conn.close()
 return results
 
 # ==================== Quality Presets ====================
 
 def save_quality_preset(self, name, settings_dict):
 """Save a quality preset"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'INSERT OR REPLACE INTO quality_presets (name, settings) VALUES (?, ?)',
 (name, json.dumps(settings_dict))
 )
 conn.commit()
 conn.close()
 
 def get_quality_preset(self, name):
 """Get a quality preset"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('SELECT settings FROM quality_presets WHERE name = ?', (name,))
 result = cursor.fetchone()
 conn.close()
 return json.loads(result[0]) if result else None
 
 def get_all_quality_presets(self):
 """Get all quality presets"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('SELECT name, settings FROM quality_presets')
 results = {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
 conn.close()
 return results
 
 def delete_quality_preset(self, name):
 """Delete a quality preset"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('DELETE FROM quality_presets WHERE name = ?', (name,))
 conn.commit()
 conn.close()
 
 # ==================== Related URL ====================
 
 def get_related_url(self, video_type, title, year, source, season='', episode=''):
 """Get related URL for a video"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 '''SELECT rel_url FROM related_url 
 WHERE video_type = ? AND title = ? AND year = ? AND source = ? 
 AND season = ? AND episode = ?''',
 (video_type, title, year, source, season, episode)
 )
 result = cursor.fetchall()
 conn.close()
 return result
 
 def set_related_url(self, video_type, title, year, source, rel_url, season='', episode=''):
 """Set related URL for a video"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 '''INSERT OR REPLACE INTO related_url 
 (video_type, title, year, source, rel_url, season, episode) 
 VALUES (?, ?, ?, ?, ?, ?, ?)''',
 (video_type, title, year, source, rel_url, season, episode)
 )
 conn.commit()
 conn.close()
 
 # ==================== Settings ====================
 
 def get_setting(self, setting):
 """Get a setting value"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('SELECT value FROM settings WHERE setting = ?', (setting,))
 result = cursor.fetchone()
 conn.close()
 return result[0] if result else None
 
 def set_setting(self, setting, value):
 """Set a setting value"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'INSERT OR REPLACE INTO settings (setting, value) VALUES (?, ?)',
 (setting, value)
 )
 conn.commit()
 conn.close()
 
 # ==================== Search History ====================
 
 def add_search(self, section, query):
 """Add to search history"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 'INSERT INTO search_history (section, query, timestamp) VALUES (?, ?, ?)',
 (section, query, time.time())
 )
 conn.commit()
 conn.close()
 
 def get_searches(self, section, limit=20):
 """Get search history"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute(
 '''SELECT DISTINCT query FROM search_history 
 WHERE section = ? ORDER BY timestamp DESC LIMIT ?''',
 (section, limit)
 )
 results = cursor.fetchall()
 conn.close()
 return [r[0] for r in results]
 
 # ==================== Episode Countdown ====================
 
 def _ensure_countdown_table(self):
 """Ensure countdown table exists"""
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS countdown_shows (
 tmdb_id TEXT PRIMARY KEY,
 title TEXT,
 timestamp REAL
 )
 ''')
 conn.commit()
 conn.close()
 
 def add_countdown_show(self, tmdb_id, title):
 """Add a show to the countdown tracker"""
 self._ensure_countdown_table()
 conn = self._get_connection()
 cursor = conn.cursor()
 try:
 cursor.execute(
 'INSERT INTO countdown_shows (tmdb_id, title, timestamp) VALUES (?, ?, ?)',
 (str(tmdb_id), title, time.time())
 )
 conn.commit()
 conn.close()
 return True
 except sqlite3.IntegrityError:
 conn.close()
 return False # Already exists
 
 def remove_countdown_show(self, tmdb_id):
 """Remove a show from the countdown tracker"""
 self._ensure_countdown_table()
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('DELETE FROM countdown_shows WHERE tmdb_id = ?', (str(tmdb_id),))
 conn.commit()
 conn.close()
 
 def get_countdown_shows(self):
 """Get all tracked shows for countdown"""
 self._ensure_countdown_table()
 conn = self._get_connection()
 cursor = conn.cursor()
 cursor.execute('SELECT tmdb_id, title, timestamp FROM countdown_shows ORDER BY timestamp DESC')
 results = cursor.fetchall()
 conn.close()
 return [{'tmdb_id': r[0], 'title': r[1], 'timestamp': r[2]} for r in results]
