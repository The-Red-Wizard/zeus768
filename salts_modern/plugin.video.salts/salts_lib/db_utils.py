"""
SALTS Library - Database utilities
Revived by zeus768 for Kodi 21+
"""
import os
import time
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
        
        # Related URL table (for tracking show/movie URLs per scraper)
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
        
        conn.commit()
        conn.close()
    
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
            age = (time.time() - timestamp) / 3600  # Convert to hours
            if age < cache_limit:
                return timestamp, response
        
        return None, None
    
    def flush_cache(self):
        """Clear all cached URLs"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM url_cache')
        conn.commit()
        conn.close()
    
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
