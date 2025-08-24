"""
Advanced pattern management system for file renaming
Supports variables, templates, counters, and dynamic naming
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from database import Database

logger = logging.getLogger(__name__)

class PatternManager:
    """Advanced pattern management with variable substitution"""
    
    def __init__(self, database: Database):
        self.db = database
        
        # Pattern variable definitions
        self.variables = {
            'counter': 'Auto-incrementing number (1, 2, 3...)',
            'counter:02d': 'Zero-padded counter (01, 02, 03...)',
            'counter:03d': '3-digit padded counter (001, 002, 003...)',
            'date': 'Current date (YYYYMMDD)',
            'time': 'Current time (HHMMSS)',
            'datetime': 'Date and time (YYYYMMDD_HHMMSS)',
            'year': 'Current year (YYYY)',
            'month': 'Current month (MM)',
            'day': 'Current day (DD)',
            'hour': 'Current hour (HH)',
            'minute': 'Current minute (MM)',
            'second': 'Current second (SS)',
            'original': 'Original filename (without extension)',
            'original_full': 'Original filename (with extension)',
            'ext': 'File extension (.mp4, .jpg, etc.)',
            'user': 'User\'s first name',
            'username': 'User\'s username',
            'user_id': 'User\'s Telegram ID',
            'size': 'File size (formatted)',
            'size_mb': 'File size in MB',
            'type': 'File type (video, audio, image, etc.)',
            'random': 'Random 6-digit number',
            'random:4': '4-digit random number',
            'random:8': '8-digit random number',
            'uuid': 'Short UUID (8 characters)',
            'timestamp': 'Unix timestamp'
        }
        
        # Pattern templates for common use cases
        self.templates = {
            'movie_collection': 'Movie_{counter:02d}_{original}',
            'tv_series': 'Series_S{season:02d}E{episode:02d}_{title}',
            'date_based': '{date}_{time}_{original}',
            'user_files': '{user}_{counter}_{original}',
            'numbered_sequence': '{original}_{counter:03d}',
            'timestamped': '{timestamp}_{original}',
            'categorized': '{type}_{date}_{original}',
            'professional': '{year}{month}{day}_{counter:04d}_{original}'
        }
        
        # User counters cache
        self.user_counters = {}
    
    def apply_pattern(self, pattern: str, file_info: Dict, user_id: int, **kwargs) -> str:
        """Apply pattern to generate new filename"""
        try:
            # Get user info
            user = self.db.get_user(user_id)
            user_name = user.get('first_name', 'User') if user else 'User'
            username = user.get('username', '') if user else ''
            
            # Prepare context variables
            now = datetime.now()
            original_name = file_info.get('name', 'file')
            original_without_ext = self._remove_extension(original_name)
            file_ext = self._get_extension(original_name)
            
            # Build variable context
            context = {
                'date': now.strftime('%Y%m%d'),
                'time': now.strftime('%H%M%S'),
                'datetime': now.strftime('%Y%m%d_%H%M%S'),
                'year': now.strftime('%Y'),
                'month': now.strftime('%m'),
                'day': now.strftime('%d'),
                'hour': now.strftime('%H'),
                'minute': now.strftime('%M'),
                'second': now.strftime('%S'),
                'original': original_without_ext,
                'original_full': original_name,
                'ext': file_ext,
                'user': user_name,
                'username': username or user_name,
                'user_id': str(user_id),
                'size': self._format_size(file_info.get('size', 0)),
                'size_mb': f"{file_info.get('size', 0) / (1024*1024):.1f}",
                'type': file_info.get('type', 'file'),
                'timestamp': str(int(now.timestamp())),
                'uuid': self._generate_short_uuid(),
                'random': self._generate_random_number(6),
            }
            
            # Add any additional context from kwargs
            context.update(kwargs)
            
            # Handle counters
            pattern_with_counters = self._process_counters(pattern, user_id)
            
            # Handle random numbers with custom lengths
            pattern_with_randoms = self._process_random_variables(pattern_with_counters)
            
            # Apply variable substitution
            result = self._substitute_variables(pattern_with_randoms, context)
            
            # Clean up the result
            result = self._clean_filename(result)
            
            # Ensure file extension is included if not specified
            if not result.endswith(file_ext) and file_ext:
                result += file_ext
            
            # Increment counter for this user/pattern combination
            self._increment_counter(user_id, pattern)
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying pattern '{pattern}': {e}")
            # Fallback to original name with timestamp
            now = datetime.now()
            original = self._remove_extension(file_info.get('name', 'file'))
            ext = self._get_extension(file_info.get('name', ''))
            return f"{original}_{now.strftime('%Y%m%d_%H%M%S')}{ext}"
    
    def _process_counters(self, pattern: str, user_id: int) -> str:
        """Process counter variables with formatting"""
        try:
            # Find all counter patterns
            counter_patterns = re.findall(r'\{counter(?::([^}]+))?\}', pattern)
            
            for format_spec in counter_patterns:
                counter_value = self._get_counter(user_id, pattern)
                
                if format_spec[0]:  # Has format specification
                    try:
                        formatted_counter = f"{counter_value:{format_spec[0]}}"
                        pattern = pattern.replace(f'{{counter:{format_spec[0]}}}', formatted_counter)
                    except ValueError:
                        # Invalid format spec, use plain counter
                        pattern = pattern.replace(f'{{counter:{format_spec[0]}}}', str(counter_value))
                else:
                    pattern = pattern.replace('{counter}', str(counter_value))
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error processing counters: {e}")
            return pattern
    
    def _process_random_variables(self, pattern: str) -> str:
        """Process random number variables with custom lengths"""
        try:
            # Find all random patterns
            random_patterns = re.findall(r'\{random(?::(\d+))?\}', pattern)
            
            for length_spec in random_patterns:
                if length_spec[0]:  # Has length specification
                    length = int(length_spec[0])
                    random_value = self._generate_random_number(length)
                    pattern = pattern.replace(f'{{random:{length_spec[0]}}}', random_value)
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error processing random variables: {e}")
            return pattern
    
    def _substitute_variables(self, pattern: str, context: Dict[str, str]) -> str:
        """Substitute variables in pattern"""
        try:
            result = pattern
            
            for variable, value in context.items():
                placeholder = f'{{{variable}}}'
                result = result.replace(placeholder, str(value))
            
            return result
            
        except Exception as e:
            logger.error(f"Error substituting variables: {e}")
            return pattern
    
    def _get_counter(self, user_id: int, pattern: str) -> int:
        """Get current counter value for user/pattern"""
        try:
            cache_key = f"{user_id}_{hash(pattern)}"
            
            if cache_key not in self.user_counters:
                # Load from database or start at 1
                counter_value = self.db.get_user_preference(user_id, f'counter_{hash(pattern)}', 1)
                self.user_counters[cache_key] = counter_value
            
            return self.user_counters[cache_key]
            
        except Exception as e:
            logger.error(f"Error getting counter: {e}")
            return 1
    
    def _increment_counter(self, user_id: int, pattern: str):
        """Increment counter for user/pattern"""
        try:
            cache_key = f"{user_id}_{hash(pattern)}"
            current_value = self._get_counter(user_id, pattern)
            new_value = current_value + 1
            
            self.user_counters[cache_key] = new_value
            self.db.set_user_preference(user_id, f'counter_{hash(pattern)}', new_value)
            
        except Exception as e:
            logger.error(f"Error incrementing counter: {e}")
    
    def _generate_random_number(self, length: int) -> str:
        """Generate random number string of specified length"""
        try:
            import random
            return ''.join([str(random.randint(0, 9)) for _ in range(length)])
        except Exception:
            return '123456'[:length]
    
    def _generate_short_uuid(self) -> str:
        """Generate short UUID (8 characters)"""
        try:
            import uuid
            return str(uuid.uuid4()).replace('-', '')[:8]
        except Exception:
            return self._generate_random_number(8)
    
    def _remove_extension(self, filename: str) -> str:
        """Remove file extension from filename"""
        try:
            if '.' in filename:
                return '.'.join(filename.split('.')[:-1])
            return filename
        except Exception:
            return filename
    
    def _get_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        try:
            if '.' in filename:
                return '.' + filename.split('.')[-1]
            return ''
        except Exception:
            return ''
    
    def _clean_filename(self, filename: str) -> str:
        """Clean filename by removing invalid characters"""
        try:
            # Remove invalid characters
            invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
            cleaned = filename
            
            for char in invalid_chars:
                cleaned = cleaned.replace(char, '_')
            
            # Remove multiple underscores
            while '__' in cleaned:
                cleaned = cleaned.replace('__', '_')
            
            # Remove leading/trailing underscores
            cleaned = cleaned.strip('_')
            
            # Ensure filename is not empty
            if not cleaned:
                cleaned = 'renamed_file'
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning filename: {e}")
            return filename
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.0f}{unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.1f}TB"
    
    def validate_pattern(self, pattern: str) -> Tuple[bool, str]:
        """Validate pattern syntax"""
        try:
            if not pattern or not pattern.strip():
                return False, "Pattern cannot be empty"
            
            # Check for unclosed braces
            open_braces = pattern.count('{')
            close_braces = pattern.count('}')
            
            if open_braces != close_braces:
                return False, "Unmatched braces in pattern"
            
            # Find all variables in pattern
            variables_in_pattern = re.findall(r'\{([^}]+)\}', pattern)
            
            # Check if all variables are valid
            for var in variables_in_pattern:
                base_var = var.split(':')[0]  # Remove format specifier
                
                if base_var not in self.variables:
                    # Check for special patterns
                    if not (base_var == 'counter' or base_var == 'random'):
                        return False, f"Unknown variable: {{{var}}}"
            
            # Check for invalid characters that would make filename unsafe
            test_result = self._clean_filename(pattern)
            if not test_result:
                return False, "Pattern would result in invalid filename"
            
            return True, "Valid pattern"
            
        except Exception as e:
            logger.error(f"Error validating pattern: {e}")
            return False, str(e)
    
    def get_pattern_preview(self, pattern: str, user_id: int, sample_file_info: Dict = None) -> str:
        """Generate preview of what the pattern would produce"""
        try:
            if sample_file_info is None:
                sample_file_info = {
                    'name': 'sample_video.mp4',
                    'size': 150 * 1024 * 1024,  # 150MB
                    'type': 'video'
                }
            
            # Create a temporary copy of counters to avoid affecting real counters
            original_counters = self.user_counters.copy()
            
            try:
                result = self.apply_pattern(pattern, sample_file_info, user_id)
                return result
            finally:
                # Restore original counters
                self.user_counters = original_counters
            
        except Exception as e:
            logger.error(f"Error generating pattern preview: {e}")
            return f"Error: {e}"
    
    def get_available_variables(self) -> Dict[str, str]:
        """Get all available pattern variables with descriptions"""
        return self.variables.copy()
    
    def get_pattern_templates(self) -> Dict[str, str]:
        """Get predefined pattern templates"""
        return self.templates.copy()
    
    def save_user_pattern(self, user_id: int, pattern_name: str, pattern_template: str) -> bool:
        """Save user's custom pattern"""
        try:
            # Validate pattern first
            is_valid, error_msg = self.validate_pattern(pattern_template)
            if not is_valid:
                logger.error(f"Invalid pattern '{pattern_template}': {error_msg}")
                return False
            
            # Save to database
            success = self.db.add_rename_pattern(user_id, pattern_name, pattern_template, is_global=False)
            
            if success:
                logger.info(f"Saved pattern '{pattern_name}' for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving user pattern: {e}")
            return False
    
    def get_user_patterns(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's saved patterns"""
        try:
            return self.db.get_user_patterns(user_id)
        except Exception as e:
            logger.error(f"Error getting user patterns: {e}")
            return []
    
    def delete_user_pattern(self, user_id: int, pattern_id: int) -> bool:
        """Delete user's saved pattern"""
        try:
            with self.db.lock:
                cursor = self.db.connection.cursor()
                cursor.execute('''
                    DELETE FROM rename_patterns 
                    WHERE id = ? AND user_id = ?
                ''', (pattern_id, user_id))
                
                success = cursor.rowcount > 0
                self.db.connection.commit()
                
                if success:
                    logger.info(f"Deleted pattern {pattern_id} for user {user_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Error deleting user pattern: {e}")
            return False
    
    def increment_pattern_usage(self, pattern_id: int):
        """Increment usage count for a pattern"""
        try:
            with self.db.lock:
                cursor = self.db.connection.cursor()
                cursor.execute('''
                    UPDATE rename_patterns 
                    SET usage_count = usage_count + 1 
                    WHERE id = ?
                ''', (pattern_id,))
                self.db.connection.commit()
                
        except Exception as e:
            logger.error(f"Error incrementing pattern usage: {e}")
    
    def get_pattern_help(self) -> str:
        """Get comprehensive pattern help text"""
        try:
            help_text = "📝 **Pattern Help**\n\n"
            
            help_text += "🔧 **Basic Syntax:**\n"
            help_text += "Use `{variable}` to insert dynamic values\n\n"
            
            help_text += "📊 **Available Variables:**\n"
            for var, desc in self.variables.items():
                help_text += f"• `{{{var}}}` - {desc}\n"
            
            help_text += "\n💡 **Examples:**\n"
            help_text += "• `Movie_{counter:02d}_{original}` → Movie_01_sample_video.mp4\n"
            help_text += "• `{user}_{date}_{original}` → John_20250824_video.mp4\n"
            help_text += "• `{type}_{year}{month}_{counter:03d}` → video_202508_001.mp4\n"
            help_text += "• `Series_S01E{counter:02d}_{title}` → Series_S01E01_episode.mp4\n"
            
            help_text += "\n🎯 **Pattern Templates:**\n"
            for name, template in self.templates.items():
                help_text += f"• **{name}**: `{template}`\n"
            
            help_text += "\n⚡ **Pro Tips:**\n"
            help_text += "• Counters auto-increment for each user\n"
            help_text += "• Use `:02d` for zero-padded numbers (01, 02, 03...)\n"
            help_text += "• Random numbers change each time\n"
            help_text += "• File extensions are added automatically\n"
            help_text += "• Invalid characters are cleaned automatically\n"
            
            return help_text
            
        except Exception as e:
            logger.error(f"Error generating pattern help: {e}")
            return "❌ Failed to load pattern help"
    
    async def save_pattern_from_text(self, user_id: int, text: str, update, context):
        """Save pattern from user text input"""
        try:
            # Parse input: "name pattern_template" or just "pattern_template"
            parts = text.strip().split(' ', 1)
            
            if len(parts) == 1:
                # Just pattern template, generate name
                pattern_template = parts[0]
                pattern_name = f"Pattern_{datetime.now().strftime('%m%d_%H%M')}"
            else:
                # Name and template provided
                pattern_name = parts[0]
                pattern_template = parts[1]
            
            # Validate pattern
            is_valid, error_msg = self.validate_pattern(pattern_template)
            
            if not is_valid:
                await update.message.reply_text(
                    f"❌ **Invalid Pattern**\n\n"
                    f"Error: {error_msg}\n\n"
                    f"Use /pattern for help with pattern syntax.",
                    parse_mode='Markdown'
                )
                return
            
            # Save pattern
            success = self.save_user_pattern(user_id, pattern_name, pattern_template)
            
            if success:
                # Generate preview
                preview = self.get_pattern_preview(pattern_template, user_id)
                
                await update.message.reply_text(
                    f"✅ **Pattern Saved!**\n\n"
                    f"📝 **Name:** {pattern_name}\n"
                    f"🔧 **Template:** `{pattern_template}`\n"
                    f"👀 **Preview:** `{preview}`\n\n"
                    f"Use this pattern with /auto_rename or batch renaming!",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ **Failed to save pattern**\n\n"
                    "Please try again or contact support.",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error saving pattern from text: {e}")
            await update.message.reply_text(
                "❌ Error processing pattern. Please try again.",
                parse_mode='Markdown'
            )
    
    def reset_user_counters(self, user_id: int):
        """Reset all counters for a user"""
        try:
            # Clear cache
            keys_to_remove = [key for key in self.user_counters.keys() if key.startswith(f"{user_id}_")]
            for key in keys_to_remove:
                del self.user_counters[key]
            
            # Reset in database (remove counter preferences)
            user_prefs = self.db.get_user(user_id)
            if user_prefs and user_prefs.get('preferences'):
                import json
                preferences = json.loads(user_prefs['preferences'])
                
                # Remove counter keys
                counter_keys = [key for key in preferences.keys() if key.startswith('counter_')]
                for key in counter_keys:
                    del preferences[key]
                
                # Save back to database
                with self.db.lock:
                    cursor = self.db.connection.cursor()
                    cursor.execute('''
                        UPDATE users SET preferences = ? WHERE user_id = ?
                    ''', (json.dumps(preferences), user_id))
                    self.db.connection.commit()
            
            logger.info(f"Reset counters for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting user counters: {e}")
            return False
