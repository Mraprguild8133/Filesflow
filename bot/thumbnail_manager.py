"""
Advanced thumbnail management system
Handles custom thumbnails, permanent thumbnails, and thumbnail generation
"""

import logging
import os
import tempfile
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import io

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

from database import Database
from config import Config

logger = logging.getLogger(__name__)

class ThumbnailManager:
    """Advanced thumbnail management with permanent and temporary thumbnails"""
    
    def __init__(self, database: Database, config: Config):
        self.db = database
        self.config = config
        self.thumbnail_cache = {}  # Cache for temporary thumbnails
    
    async def set_temporary_thumbnail(self, user_id: int, photo_file_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set temporary thumbnail for next file upload"""
        try:
            # Download and process thumbnail
            thumbnail_data = await self._download_and_process_thumbnail(photo_file_id, context)
            
            if not thumbnail_data:
                await update.message.reply_text("❌ Failed to process thumbnail image")
                return
            
            # Store in cache for temporary use
            self.thumbnail_cache[user_id] = {
                'data': thumbnail_data,
                'file_id': photo_file_id,
                'timestamp': update.message.date.timestamp()
            }
            
            keyboard = [
                [InlineKeyboardButton("📁 Send File Now", callback_data="thumb_send_file"),
                 InlineKeyboardButton("🖼️ Preview", callback_data=f"thumb_preview_{photo_file_id}")],
                [InlineKeyboardButton("💾 Make Permanent", callback_data=f"thumb_permanent_{photo_file_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ **Temporary Thumbnail Set!**\n\n"
                "🖼️ This thumbnail will be used for your next file upload.\n"
                "📁 Send any file now to apply this thumbnail!\n\n"
                "💡 **Options:**\n"
                "• Send file to apply thumbnail\n"
                "• Make it permanent for all files\n"
                "• Preview the processed thumbnail",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            # Log action
            self.db.log_action("INFO", "Temporary thumbnail set", user_id)
            
        except Exception as e:
            logger.error(f"Error setting temporary thumbnail: {e}")
            await update.message.reply_text("❌ Failed to set thumbnail. Please try again.")
    
    async def set_permanent_thumbnail(self, user_id: int, photo_file_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set permanent thumbnail for all user's uploads"""
        try:
            # Download and process thumbnail
            thumbnail_data = await self._download_and_process_thumbnail(photo_file_id, context)
            
            if not thumbnail_data:
                await update.message.reply_text("❌ Failed to process thumbnail image")
                return
            
            # Store in database
            with self.db.lock:
                cursor = self.db.connection.cursor()
                cursor.execute('''
                    UPDATE users SET permanent_thumbnail = ? WHERE user_id = ?
                ''', (thumbnail_data, user_id))
                self.db.connection.commit()
            
            keyboard = [
                [InlineKeyboardButton("🖼️ Preview", callback_data=f"perm_thumb_preview_{user_id}"),
                 InlineKeyboardButton("📁 Test Upload", callback_data="perm_thumb_test")],
                [InlineKeyboardButton("🗑️ Remove", callback_data="perm_thumb_remove")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ **Permanent Thumbnail Set!**\n\n"
                "🎯 **Features:**\n"
                "• Applied to ALL your file uploads automatically\n"
                "• High quality 320x320 resolution\n"
                "• Works with any file type\n"
                "• Overrides original file thumbnails\n\n"
                "🚀 **Ready to use!** Upload any file to see it in action!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            # Log action
            self.db.log_action("INFO", "Permanent thumbnail set", user_id)
            
        except Exception as e:
            logger.error(f"Error setting permanent thumbnail: {e}")
            await update.message.reply_text("❌ Failed to set permanent thumbnail. Please try again.")
    
    async def remove_permanent_thumbnail(self, user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove user's permanent thumbnail"""
        try:
            with self.db.lock:
                cursor = self.db.connection.cursor()
                cursor.execute('''
                    UPDATE users SET permanent_thumbnail = NULL WHERE user_id = ?
                ''', (user_id,))
                self.db.connection.commit()
            
            await update.message.reply_text(
                "✅ **Permanent Thumbnail Removed**\n\n"
                "📁 Files will now use their original thumbnails.\n"
                "🖼️ You can set a new permanent thumbnail anytime with /permanent_thumb",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log action
            self.db.log_action("INFO", "Permanent thumbnail removed", user_id)
            
        except Exception as e:
            logger.error(f"Error removing permanent thumbnail: {e}")
            await update.message.reply_text("❌ Failed to remove permanent thumbnail")
    
    async def preview_thumbnail(self, user_id: int, thumbnail_type: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Preview thumbnail (permanent or temporary)"""
        try:
            thumbnail_data = None
            
            if thumbnail_type == 'permanent':
                user = self.db.get_user(user_id)
                if user and user.get('permanent_thumbnail'):
                    thumbnail_data = user['permanent_thumbnail']
            
            elif thumbnail_type == 'temporary':
                if user_id in self.thumbnail_cache:
                    thumbnail_data = self.thumbnail_cache[user_id]['data']
            
            if not thumbnail_data:
                await update.message.reply_text("❌ No thumbnail found to preview")
                return
            
            # Convert binary data to image
            thumbnail_io = io.BytesIO(thumbnail_data)
            
            # Send thumbnail preview
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=thumbnail_io,
                caption=(
                    f"🖼️ **Thumbnail Preview**\n\n"
                    f"📊 **Details:**\n"
                    f"• Resolution: 320x320\n"
                    f"• Format: JPEG\n"
                    f"• Quality: High\n"
                    f"• Type: {thumbnail_type.title()}\n\n"
                    f"✨ This is how your thumbnail will appear on files!"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error previewing thumbnail: {e}")
            await update.message.reply_text("❌ Failed to preview thumbnail")
    
    async def get_thumbnail_for_file(self, user_id: int, file_info: Dict) -> Optional[bytes]:
        """Get appropriate thumbnail for file upload"""
        try:
            # Check for permanent thumbnail first
            user = self.db.get_user(user_id)
            if user and user.get('permanent_thumbnail'):
                return user['permanent_thumbnail']
            
            # Check for temporary thumbnail
            if user_id in self.thumbnail_cache:
                cache_entry = self.thumbnail_cache[user_id]
                
                # Check if cache is still valid (24 hours)
                import time
                if time.time() - cache_entry['timestamp'] < 86400:
                    # Remove from cache after use (temporary)
                    thumbnail_data = cache_entry['data']
                    del self.thumbnail_cache[user_id]
                    return thumbnail_data
                else:
                    # Cache expired, remove it
                    del self.thumbnail_cache[user_id]
            
            # No custom thumbnail, return None to use original
            return None
            
        except Exception as e:
            logger.error(f"Error getting thumbnail for file: {e}")
            return None
    
    async def generate_text_thumbnail(self, text: str, user_id: int) -> Optional[bytes]:
        """Generate thumbnail with text (for documents without thumbnails)"""
        try:
            # Create image
            image = Image.new('RGB', self.config.THUMBNAIL_SIZE, color='white')
            draw = ImageDraw.Draw(image)
            
            # Try to use a font, fallback to default if not available
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            except (OSError, IOError):
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
            
            # Add text to image
            if font:
                # Calculate text position for centering
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                x = (self.config.THUMBNAIL_SIZE[0] - text_width) // 2
                y = (self.config.THUMBNAIL_SIZE[1] - text_height) // 2
                
                # Add background rectangle
                draw.rectangle([x-10, y-10, x+text_width+10, y+text_height+10], fill='lightblue')
                draw.text((x, y), text, fill='black', font=font)
            
            # Convert to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=self.config.THUMBNAIL_QUALITY)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating text thumbnail: {e}")
            return None
    
    async def generate_media_info_thumbnail(self, file_info: Dict) -> Optional[bytes]:
        """Generate thumbnail with media info"""
        try:
            # Create image
            image = Image.new('RGB', self.config.THUMBNAIL_SIZE, color='#2c3e50')
            draw = ImageDraw.Draw(image)
            
            # Try to use a font
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
                info_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            except:
                title_font = info_font = ImageFont.load_default()
            
            # Add file type as title
            file_type = file_info.get('type', 'File').upper()
            draw.text((20, 20), file_type, fill='white', font=title_font)
            
            # Add file info
            y_offset = 60
            info_lines = []
            
            if file_info.get('size'):
                info_lines.append(f"Size: {self._format_size(file_info['size'])}")
            
            if file_info.get('duration'):
                info_lines.append(f"Duration: {self._format_duration(file_info['duration'])}")
            
            if file_info.get('width') and file_info.get('height'):
                info_lines.append(f"Resolution: {file_info['width']}x{file_info['height']}")
            
            # Draw info lines
            for line in info_lines:
                draw.text((20, y_offset), line, fill='lightgray', font=info_font)
                y_offset += 25
            
            # Add decorative elements
            draw.rectangle([10, 10, 310, 50], outline='#3498db', width=2)
            
            # Convert to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=self.config.THUMBNAIL_QUALITY)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating media info thumbnail: {e}")
            return None
    
    async def _download_and_process_thumbnail(self, photo_file_id: str, context: ContextTypes.DEFAULT_TYPE) -> Optional[bytes]:
        """Download and process thumbnail image"""
        try:
            # Download the photo
            file = await context.bot.get_file(photo_file_id)
            
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            
            try:
                # Download to temp file
                await file.download_to_drive(temp_path)
                
                # Process with PIL
                with Image.open(temp_path) as img:
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize to thumbnail size maintaining aspect ratio
                    img.thumbnail(self.config.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                    
                    # Create new image with exact thumbnail size
                    thumb = Image.new('RGB', self.config.THUMBNAIL_SIZE, color='white')
                    
                    # Calculate position to center the image
                    x = (self.config.THUMBNAIL_SIZE[0] - img.size[0]) // 2
                    y = (self.config.THUMBNAIL_SIZE[1] - img.size[1]) // 2
                    
                    # Paste the resized image onto the thumbnail
                    thumb.paste(img, (x, y))
                    
                    # Convert to bytes
                    output = io.BytesIO()
                    thumb.save(output, format='JPEG', quality=self.config.THUMBNAIL_QUALITY, optimize=True)
                    return output.getvalue()
            
            finally:
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
            logger.error(f"Error processing thumbnail: {e}")
            return None
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.1f} TB"
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    async def cleanup_expired_cache(self):
        """Clean up expired temporary thumbnails"""
        try:
            import time
            current_time = time.time()
            expired_users = []
            
            for user_id, cache_entry in self.thumbnail_cache.items():
                # Remove cache entries older than 24 hours
                if current_time - cache_entry['timestamp'] > 86400:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self.thumbnail_cache[user_id]
            
            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired thumbnail cache entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up thumbnail cache: {e}")
    
    def get_thumbnail_stats(self, user_id: int) -> Dict[str, Any]:
        """Get thumbnail statistics for user"""
        try:
            user = self.db.get_user(user_id)
            has_permanent = bool(user and user.get('permanent_thumbnail'))
            has_temporary = user_id in self.thumbnail_cache
            
            stats = {
                'has_permanent_thumbnail': has_permanent,
                'has_temporary_thumbnail': has_temporary,
                'cache_entries': len(self.thumbnail_cache),
                'thumbnail_size': f"{self.config.THUMBNAIL_SIZE[0]}x{self.config.THUMBNAIL_SIZE[1]}",
                'thumbnail_quality': self.config.THUMBNAIL_QUALITY
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting thumbnail stats: {e}")
            return {}
