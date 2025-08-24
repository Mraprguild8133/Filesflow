"""
Database management for Telegram Bot
SQLite database with user preferences, patterns, and bot data
"""

import sqlite3
import logging
import json
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Database:
    """Database manager for bot data"""
    
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.connection = None
        self.lock = threading.Lock()
    
    def init_db(self):
        """Initialize database with all required tables"""
        try:
            with self.lock:
                self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
                self.connection.row_factory = sqlite3.Row
                
                cursor = self.connection.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        subscription_status TEXT DEFAULT 'active',
                        permanent_thumbnail BLOB,
                        default_caption TEXT,
                        auto_rename_pattern TEXT,
                        total_files INTEGER DEFAULT 0,
                        total_size INTEGER DEFAULT 0,
                        preferences TEXT DEFAULT '{}'
                    )
                ''')
                
                # File processing queue
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        file_id TEXT,
                        original_name TEXT,
                        new_name TEXT,
                        operation_type TEXT,
                        status TEXT DEFAULT 'pending',
                        priority INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        error_message TEXT,
                        progress INTEGER DEFAULT 0,
                        file_size INTEGER DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Rename patterns
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS rename_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        pattern_name TEXT,
                        pattern_template TEXT,
                        is_global BOOLEAN DEFAULT FALSE,
                        usage_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Force subscribe channels
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS force_channels (
                        channel_id INTEGER PRIMARY KEY,
                        channel_name TEXT,
                        channel_username TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # User subscriptions
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_subscriptions (
                        user_id INTEGER,
                        channel_id INTEGER,
                        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, channel_id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (channel_id) REFERENCES force_channels (channel_id)
                    )
                ''')
                
                # Bot settings
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bot_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Bot logs
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bot_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT,
                        message TEXT,
                        user_id INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        details TEXT
                    )
                ''')
                
                # File metadata
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        file_id TEXT UNIQUE,
                        original_name TEXT,
                        file_type TEXT,
                        file_size INTEGER,
                        duration INTEGER,
                        width INTEGER,
                        height INTEGER,
                        metadata_json TEXT,
                        thumbnail_file_id TEXT,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Broadcast history
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS broadcasts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_id INTEGER,
                        message TEXT,
                        target_count INTEGER DEFAULT 0,
                        success_count INTEGER DEFAULT 0,
                        failed_count INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_queue_user_status ON file_queue (user_id, status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_queue_status ON file_queue (status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_user ON rename_patterns (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_file ON file_metadata (file_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON bot_logs (timestamp)')
                
                self.connection.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add or update user in database"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, last_activity)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, username, first_name, last_name))
                self.connection.commit()
                
        except Exception as e:
            logger.error(f"Failed to add user {user_id}: {e}")
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data from database"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def update_user_activity(self, user_id: int):
        """Update user's last activity timestamp"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('''
                    UPDATE users SET last_activity = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (user_id,))
                self.connection.commit()
                
        except Exception as e:
            logger.error(f"Failed to update activity for user {user_id}: {e}")
    
    def set_user_preference(self, user_id: int, key: str, value: Any):
        """Set user preference"""
        try:
            with self.lock:
                user = self.get_user(user_id)
                if not user:
                    return False
                
                preferences = json.loads(user.get('preferences', '{}'))
                preferences[key] = value
                
                cursor = self.connection.cursor()
                cursor.execute('''
                    UPDATE users SET preferences = ? WHERE user_id = ?
                ''', (json.dumps(preferences), user_id))
                self.connection.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to set preference for user {user_id}: {e}")
            return False
    
    def get_user_preference(self, user_id: int, key: str, default: Any = None) -> Any:
        """Get user preference"""
        try:
            user = self.get_user(user_id)
            if not user:
                return default
            
            preferences = json.loads(user.get('preferences', '{}'))
            return preferences.get(key, default)
            
        except Exception as e:
            logger.error(f"Failed to get preference for user {user_id}: {e}")
            return default
    
    def add_to_queue(self, user_id: int, file_id: str, original_name: str, 
                     new_name: str, operation_type: str, priority: int = 0) -> int:
        """Add file to processing queue"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO file_queue 
                    (user_id, file_id, original_name, new_name, operation_type, priority)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, file_id, original_name, new_name, operation_type, priority))
                self.connection.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Failed to add to queue: {e}")
            return 0
    
    def get_queue_item(self, queue_id: int) -> Optional[Dict]:
        """Get queue item by ID"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('SELECT * FROM file_queue WHERE id = ?', (queue_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get queue item {queue_id}: {e}")
            return None
    
    def update_queue_status(self, queue_id: int, status: str, progress: int = None, 
                           error_message: str = None):
        """Update queue item status"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                
                update_fields = ['status = ?']
                values = [status]
                
                if progress is not None:
                    update_fields.append('progress = ?')
                    values.append(progress)
                
                if error_message:
                    update_fields.append('error_message = ?')
                    values.append(error_message)
                
                if status == 'processing':
                    update_fields.append('started_at = CURRENT_TIMESTAMP')
                elif status in ['completed', 'failed']:
                    update_fields.append('completed_at = CURRENT_TIMESTAMP')
                
                values.append(queue_id)
                
                cursor.execute(f'''
                    UPDATE file_queue SET {', '.join(update_fields)} 
                    WHERE id = ?
                ''', values)
                self.connection.commit()
                
        except Exception as e:
            logger.error(f"Failed to update queue status {queue_id}: {e}")
    
    def get_user_queue(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's queue items"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('''
                    SELECT * FROM file_queue 
                    WHERE user_id = ? 
                    ORDER BY priority DESC, created_at ASC 
                    LIMIT ?
                ''', (user_id, limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get user queue {user_id}: {e}")
            return []
    
    def get_pending_queue_items(self, limit: int = 10) -> List[Dict]:
        """Get pending queue items for processing"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('''
                    SELECT * FROM file_queue 
                    WHERE status = 'pending' 
                    ORDER BY priority DESC, created_at ASC 
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get pending queue items: {e}")
            return []
    
    def add_rename_pattern(self, user_id: int, pattern_name: str, 
                          pattern_template: str, is_global: bool = False) -> bool:
        """Add rename pattern"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO rename_patterns 
                    (user_id, pattern_name, pattern_template, is_global)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, pattern_name, pattern_template, is_global))
                self.connection.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to add rename pattern: {e}")
            return False
    
    def get_user_patterns(self, user_id: int) -> List[Dict]:
        """Get user's rename patterns"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('''
                    SELECT * FROM rename_patterns 
                    WHERE user_id = ? OR is_global = TRUE
                    ORDER BY usage_count DESC, pattern_name
                ''', (user_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get user patterns {user_id}: {e}")
            return []
    
    def log_action(self, level: str, message: str, user_id: int = None, details: str = None):
        """Log bot action"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO bot_logs (level, message, user_id, details)
                    VALUES (?, ?, ?, ?)
                ''', (level, message, user_id, details))
                self.connection.commit()
                
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get bot statistics"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                
                stats = {}
                
                # User statistics
                cursor.execute('SELECT COUNT(*) FROM users')
                stats['total_users'] = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE last_activity > datetime('now', '-7 days')
                ''')
                stats['active_users_week'] = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE last_activity > datetime('now', '-1 day')
                ''')
                stats['active_users_day'] = cursor.fetchone()[0]
                
                # Queue statistics
                cursor.execute('SELECT COUNT(*) FROM file_queue WHERE status = "pending"')
                stats['pending_queue'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM file_queue WHERE status = "processing"')
                stats['processing_queue'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM file_queue WHERE status = "completed"')
                stats['completed_files'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM file_queue WHERE status = "failed"')
                stats['failed_files'] = cursor.fetchone()[0]
                
                # File statistics
                cursor.execute('SELECT SUM(total_files), SUM(total_size) FROM users')
                row = cursor.fetchone()
                stats['total_files_processed'] = row[0] or 0
                stats['total_size_processed'] = row[1] or 0
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def cleanup_old_logs(self, days: int = 7):
        """Clean up old log entries"""
        try:
            with self.lock:
                cursor = self.connection.cursor()
                cursor.execute('''
                    DELETE FROM bot_logs 
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(days))
                self.connection.commit()
                logger.info(f"Cleaned up logs older than {days} days")
                
        except Exception as e:
            logger.error(f"Failed to cleanup logs: {e}")
    
    def close(self):
        """Close database connection"""
        try:
            if self.connection:
                self.connection.close()
                logger.info("Database connection closed")
                
        except Exception as e:
            logger.error(f"Failed to close database: {e}")
