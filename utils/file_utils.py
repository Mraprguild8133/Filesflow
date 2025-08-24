"""
Advanced file utilities for Telegram Bot
File type detection, validation, processing, and management
"""

import logging
import os
import magic
import hashlib
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import mimetypes

from config import Config

logger = logging.getLogger(__name__)

class FileUtils:
    """Advanced file utilities with comprehensive format support"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize magic for file type detection
        try:
            self.magic_mime = magic.Magic(mime=True)
            self.magic_desc = magic.Magic()
        except Exception as e:
            logger.warning(f"Python-magic not available: {e}")
            self.magic_mime = None
            self.magic_desc = None
    
    def detect_file_type(self, file_path: str) -> Dict[str, Any]:
        """Detect comprehensive file type information"""
        try:
            if not os.path.exists(file_path):
                return {'error': 'File not found'}
            
            file_info = {
                'filename': os.path.basename(file_path),
                'size': os.path.getsize(file_path),
                'extension': Path(file_path).suffix.lower(),
                'mime_type': None,
                'description': None,
                'category': 'unknown',
                'is_safe': True,
                'encoding': None
            }
            
            # Get MIME type using multiple methods
            mime_type = self._get_mime_type(file_path)
            file_info['mime_type'] = mime_type
            
            # Get file description
            if self.magic_desc:
                try:
                    file_info['description'] = self.magic_desc.from_file(file_path)
                except Exception as e:
                    logger.warning(f"Failed to get file description: {e}")
            
            # Determine file category
            file_info['category'] = self._categorize_file(file_info['extension'], mime_type)
            
            # Security check
            file_info['is_safe'] = self._is_file_safe(file_path, mime_type)
            
            # Get file hash
            file_info['hash'] = self._calculate_file_hash(file_path)
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error detecting file type: {e}")
            return {'error': str(e)}
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type using multiple detection methods"""
        try:
            # Try python-magic first (most accurate)
            if self.magic_mime:
                try:
                    return self.magic_mime.from_file(file_path)
                except Exception:
                    pass
            
            # Fallback to mimetypes module
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                return mime_type
            
            # Extension-based fallback
            ext = Path(file_path).suffix.lower()
            extension_map = {
                '.mp4': 'video/mp4',
                '.mkv': 'video/x-matroska',
                '.avi': 'video/x-msvideo',
                '.mov': 'video/quicktime',
                '.wmv': 'video/x-ms-wmv',
                '.flv': 'video/x-flv',
                '.webm': 'video/webm',
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.flac': 'audio/flac',
                '.aac': 'audio/aac',
                '.ogg': 'audio/ogg',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp',
                '.pdf': 'application/pdf',
                '.zip': 'application/zip',
                '.rar': 'application/x-rar-compressed',
                '.7z': 'application/x-7z-compressed'
            }
            
            return extension_map.get(ext, 'application/octet-stream')
            
        except Exception as e:
            logger.error(f"Error getting MIME type: {e}")
            return 'application/octet-stream'
    
    def _categorize_file(self, extension: str, mime_type: str) -> str:
        """Categorize file based on extension and MIME type"""
        try:
            # Video files
            if (mime_type and mime_type.startswith('video/') or 
                extension in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp']):
                return 'video'
            
            # Audio files
            if (mime_type and mime_type.startswith('audio/') or 
                extension in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus']):
                return 'audio'
            
            # Image files
            if (mime_type and mime_type.startswith('image/') or 
                extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg']):
                return 'image'
            
            # Document files
            if (mime_type and (mime_type.startswith('application/') or mime_type.startswith('text/')) or 
                extension in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt']):
                return 'document'
            
            # Archive files
            if (mime_type and 'compressed' in mime_type or 'zip' in mime_type or 
                extension in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']):
                return 'archive'
            
            return 'other'
            
        except Exception as e:
            logger.error(f"Error categorizing file: {e}")
            return 'unknown'
    
    def _is_file_safe(self, file_path: str, mime_type: str) -> bool:
        """Check if file is safe (basic security check)"""
        try:
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.config.MAX_FILE_SIZE:
                return False
            
            # Check for potentially dangerous file types
            dangerous_extensions = ['.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js']
            extension = Path(file_path).suffix.lower()
            
            if extension in dangerous_extensions:
                return False
            
            # Check MIME type for executables
            if mime_type and ('executable' in mime_type or 'application/x-' in mime_type):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking file safety: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: str, algorithm: str = 'md5') -> str:
        """Calculate file hash for integrity checking"""
        try:
            hash_obj = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return ""
    
    def validate_filename(self, filename: str) -> Tuple[bool, str]:
        """Validate filename for safety and compliance"""
        try:
            if not filename:
                return False, "Filename cannot be empty"
            
            # Check length
            if len(filename) > 255:
                return False, "Filename too long (max 255 characters)"
            
            # Check for invalid characters
            invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
            for char in invalid_chars:
                if char in filename:
                    return False, f"Invalid character '{char}' in filename"
            
            # Check for reserved names (Windows)
            reserved_names = [
                'CON', 'PRN', 'AUX', 'NUL',
                'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
            ]
            
            name_without_ext = Path(filename).stem.upper()
            if name_without_ext in reserved_names:
                return False, f"'{name_without_ext}' is a reserved filename"
            
            # Check for leading/trailing spaces or dots
            if filename.startswith(' ') or filename.endswith(' '):
                return False, "Filename cannot start or end with spaces"
            
            if filename.startswith('.') or filename.endswith('.'):
                return False, "Filename cannot start or end with dots"
            
            return True, "Valid filename"
            
        except Exception as e:
            logger.error(f"Error validating filename: {e}")
            return False, str(e)
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing/replacing invalid characters"""
        try:
            if not filename:
                return "unnamed_file"
            
            # Replace invalid characters
            invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
            sanitized = filename
            
            for char in invalid_chars:
                sanitized = sanitized.replace(char, '_')
            
            # Remove leading/trailing spaces and dots
            sanitized = sanitized.strip(' .')
            
            # Ensure it's not empty
            if not sanitized:
                sanitized = "unnamed_file"
            
            # Truncate if too long
            if len(sanitized) > 255:
                name, ext = os.path.splitext(sanitized)
                max_name_length = 255 - len(ext)
                sanitized = name[:max_name_length] + ext
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Error sanitizing filename: {e}")
            return "unnamed_file"
    
    def get_file_info_summary(self, file_path: str) -> str:
        """Get human-readable file information summary"""
        try:
            file_info = self.detect_file_type(file_path)
            
            if 'error' in file_info:
                return f"Error: {file_info['error']}"
            
            summary = f"📁 **File Information**\n\n"
            summary += f"📋 **Name:** `{file_info['filename']}`\n"
            summary += f"📊 **Size:** {self._format_size(file_info['size'])}\n"
            summary += f"🏷️ **Type:** {file_info['category'].title()}\n"
            summary += f"📝 **MIME:** `{file_info['mime_type']}`\n"
            
            if file_info.get('description'):
                summary += f"ℹ️ **Description:** {file_info['description'][:100]}...\n"
            
            summary += f"🔒 **Safe:** {'✅ Yes' if file_info['is_safe'] else '❌ No'}\n"
            
            if file_info.get('hash'):
                summary += f"🔑 **Hash:** `{file_info['hash'][:16]}...`\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting file info summary: {e}")
            return "❌ Failed to get file information"
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.1f} PB"
    
    def create_temp_file(self, suffix: str = '', prefix: str = 'telegram_bot_') -> str:
        """Create a temporary file and return its path"""
        try:
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=suffix,
                prefix=prefix,
                dir=self.config.TEMP_DIR
            )
            os.close(temp_fd)
            return temp_path
            
        except Exception as e:
            logger.error(f"Error creating temp file: {e}")
            raise
    
    def cleanup_temp_file(self, file_path: str):
        """Safely clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up temp file: {file_path}")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
    
    def ensure_directory_exists(self, directory: str):
        """Ensure directory exists, create if not"""
        try:
            os.makedirs(directory, exist_ok=True)
            
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            raise
    
    def get_available_space(self, path: str = '/') -> int:
        """Get available disk space in bytes"""
        try:
            statvfs = os.statvfs(path)
            return statvfs.f_frsize * statvfs.f_bavail
            
        except Exception as e:
            logger.error(f"Error getting available space: {e}")
            return 0
    
    def is_supported_format(self, filename: str) -> bool:
        """Check if file format is supported"""
        try:
            category = self.config.get_file_category(filename)
            return category != 'unknown'
            
        except Exception as e:
            logger.error(f"Error checking format support: {e}")
            return False
    
    def get_file_extension_info(self, extension: str) -> Dict[str, Any]:
        """Get information about a file extension"""
        try:
            extension = extension.lower()
            if not extension.startswith('.'):
                extension = '.' + extension
            
            # Extension information database
            extension_info = {
                '.mp4': {'category': 'video', 'description': 'MPEG-4 Video', 'common': True},
                '.mkv': {'category': 'video', 'description': 'Matroska Video', 'common': True},
                '.avi': {'category': 'video', 'description': 'Audio Video Interleave', 'common': True},
                '.mov': {'category': 'video', 'description': 'QuickTime Movie', 'common': True},
                '.mp3': {'category': 'audio', 'description': 'MPEG Audio Layer 3', 'common': True},
                '.wav': {'category': 'audio', 'description': 'Waveform Audio', 'common': True},
                '.flac': {'category': 'audio', 'description': 'Free Lossless Audio Codec', 'common': True},
                '.jpg': {'category': 'image', 'description': 'JPEG Image', 'common': True},
                '.png': {'category': 'image', 'description': 'Portable Network Graphics', 'common': True},
                '.gif': {'category': 'image', 'description': 'Graphics Interchange Format', 'common': True},
                '.pdf': {'category': 'document', 'description': 'Portable Document Format', 'common': True},
                '.zip': {'category': 'archive', 'description': 'ZIP Archive', 'common': True},
                '.rar': {'category': 'archive', 'description': 'RAR Archive', 'common': True},
                '.7z': {'category': 'archive', 'description': '7-Zip Archive', 'common': True}
            }
            
            return extension_info.get(extension, {
                'category': 'unknown',
                'description': 'Unknown Format',
                'common': False
            })
            
        except Exception as e:
            logger.error(f"Error getting extension info: {e}")
            return {'category': 'unknown', 'description': 'Error', 'common': False}
    
    def convert_size_to_bytes(self, size_str: str) -> int:
        """Convert size string (e.g., '100MB') to bytes"""
        try:
            size_str = size_str.upper().strip()
            
            if size_str.endswith('B'):
                size_str = size_str[:-1]
            
            multipliers = {
                'K': 1024,
                'M': 1024**2,
                'G': 1024**3,
                'T': 1024**4
            }
            
            for suffix, multiplier in multipliers.items():
                if size_str.endswith(suffix):
                    return int(float(size_str[:-1]) * multiplier)
            
            return int(size_str)
            
        except Exception as e:
            logger.error(f"Error converting size string: {e}")
            return 0
    
    def batch_validate_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Validate multiple files and return batch results"""
        try:
            results = {
                'total_files': len(file_paths),
                'valid_files': 0,
                'invalid_files': 0,
                'total_size': 0,
                'files': []
            }
            
            for file_path in file_paths:
                file_info = self.detect_file_type(file_path)
                
                if 'error' not in file_info and file_info['is_safe']:
                    results['valid_files'] += 1
                    results['total_size'] += file_info['size']
                else:
                    results['invalid_files'] += 1
                
                results['files'].append(file_info)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch validation: {e}")
            return {'error': str(e)}
