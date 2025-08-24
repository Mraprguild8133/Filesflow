"""
Configuration management for Telegram Bot
All environment variables and settings
"""

import os
from typing import List, Dict, Any

class Config:
    """Configuration class for bot settings"""
    
    def __init__(self):
        # Bot Token (Required)
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")
        
        # Admin User IDs
        self.ADMIN_IDS = self._parse_admin_ids()
        
        # Channel and Group Settings
        self.FORCE_SUB_CHANNELS = self._parse_channels("FORCE_SUB_CHANNELS")
        self.LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
        self.STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", "0"))
        
        # File Settings
        self.MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "2000000000"))  # 2GB default
        self.SUPPORTED_FORMATS = self._get_supported_formats()
        self.TEMP_DIR = os.getenv("TEMP_DIR", "./temp")
        self.DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "./downloads")
        
        # Thumbnail Settings
        self.THUMBNAIL_SIZE = (320, 320)  # Standard Telegram thumbnail size
        self.THUMBNAIL_QUALITY = int(os.getenv("THUMBNAIL_QUALITY", "85"))
        
        # Queue Settings
        self.MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "100"))
        self.CONCURRENT_UPLOADS = int(os.getenv("CONCURRENT_UPLOADS", "3"))
        self.CONCURRENT_DOWNLOADS = int(os.getenv("CONCURRENT_DOWNLOADS", "5"))
        
        # Monitoring Settings
        self.HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "300"))  # 5 minutes
        self.LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "7"))
        self.MAX_LOG_SIZE_MB = int(os.getenv("MAX_LOG_SIZE_MB", "100"))
        
        # Broadcast Settings
        self.BROADCAST_DELAY = float(os.getenv("BROADCAST_DELAY", "0.1"))  # Delay between messages
        self.MAX_BROADCAST_SIZE = int(os.getenv("MAX_BROADCAST_SIZE", "1000"))
        
        # Database Settings
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_database.db")
        self.BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
        
        # Performance Settings
        self.ENABLE_PROGRESS_TRACKING = os.getenv("ENABLE_PROGRESS_TRACKING", "true").lower() == "true"
        self.CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1048576"))  # 1MB chunks
        
        # Security Settings
        self.RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
        self.RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # 1 minute
        
        # Create necessary directories
        self._create_directories()
    
    def _parse_admin_ids(self) -> List[int]:
        """Parse admin IDs from environment variable"""
        admin_str = os.getenv("ADMIN_IDS", "")
        if not admin_str:
            return []
        
        try:
            return [int(user_id.strip()) for user_id in admin_str.split(",") if user_id.strip()]
        except ValueError:
            return []
    
    def _parse_channels(self, env_var: str) -> List[int]:
        """Parse channel IDs from environment variable"""
        channels_str = os.getenv(env_var, "")
        if not channels_str:
            return []
        
        try:
            return [int(channel_id.strip()) for channel_id in channels_str.split(",") if channel_id.strip()]
        except ValueError:
            return []
    
    def _get_supported_formats(self) -> Dict[str, List[str]]:
        """Define supported file formats by category"""
        return {
            'video': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg'],
            'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.zip', '.rar', '.7z'],
            'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
            'other': ['.*']  # Support all other formats
        }
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [self.TEMP_DIR, self.DOWNLOADS_DIR, './logs', './backups']
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.ADMIN_IDS
    
    def get_file_category(self, filename: str) -> str:
        """Get file category based on extension"""
        if not filename:
            return 'other'
        
        ext = os.path.splitext(filename.lower())[1]
        
        for category, extensions in self.SUPPORTED_FORMATS.items():
            if ext in extensions or '.*' in extensions:
                return category
        
        return 'other'
    
    def validate_config(self) -> bool:
        """Validate critical configuration"""
        if not self.BOT_TOKEN or self.BOT_TOKEN == "your_bot_token_here":
            return False
        
        if not self.ADMIN_IDS:
            return False
        
        return True
    
    def get_settings_summary(self) -> Dict[str, Any]:
        """Get configuration summary for display"""
        return {
            'admin_count': len(self.ADMIN_IDS),
            'force_sub_channels': len(self.FORCE_SUB_CHANNELS),
            'max_file_size_mb': self.MAX_FILE_SIZE // (1024 * 1024),
            'max_queue_size': self.MAX_QUEUE_SIZE,
            'concurrent_uploads': self.CONCURRENT_UPLOADS,
            'concurrent_downloads': self.CONCURRENT_DOWNLOADS,
            'log_retention_days': self.LOG_RETENTION_DAYS,
            'health_check_interval_min': self.HEALTH_CHECK_INTERVAL // 60,
            'progress_tracking': self.ENABLE_PROGRESS_TRACKING
        }
