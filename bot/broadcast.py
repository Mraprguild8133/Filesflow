"""
Advanced broadcast system for Telegram Bot
Handles mass messaging with rate limiting, progress tracking, and error handling
"""

import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError, Forbidden, BadRequest

from database import Database
from config import Config

logger = logging.getLogger(__name__)

class BroadcastManager:
    """Advanced broadcast management with rate limiting and analytics"""
    
    def __init__(self, database: Database, config: Config):
        self.db = database
        self.config = config
        self.active_broadcasts = {}  # Track active broadcasts
        self.broadcast_lock = asyncio.Lock()
    
    async def start_broadcast(self, message: str, admin_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start a new broadcast to all users"""
        try:
            async with self.broadcast_lock:
                # Get all active users
                users = await self._get_broadcast_users()
                
                if not users:
                    await update.message.reply_text("❌ No users found for broadcast")
                    return
                
                # Create broadcast record
                broadcast_id = await self._create_broadcast_record(admin_id, message, len(users))
                
                if not broadcast_id:
                    await update.message.reply_text("❌ Failed to create broadcast record")
                    return
                
                # Show confirmation
                keyboard = [
                    [InlineKeyboardButton("✅ Confirm Send", callback_data=f"broadcast_confirm_{broadcast_id}"),
                     InlineKeyboardButton("❌ Cancel", callback_data=f"broadcast_cancel_{broadcast_id}")],
                    [InlineKeyboardButton("📝 Edit Message", callback_data=f"broadcast_edit_{broadcast_id}"),
                     InlineKeyboardButton("👁️ Preview", callback_data=f"broadcast_preview_{broadcast_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"📢 **Broadcast Ready**\n\n"
                    f"👥 **Target Users:** {len(users):,}\n"
                    f"📝 **Message Preview:**\n"
                    f"```\n{message[:500]}{'...' if len(message) > 500 else ''}\n```\n\n"
                    f"⚠️ **Warning:** This will send to ALL active users!\n"
                    f"📊 **Estimated Time:** {self._estimate_broadcast_time(len(users))}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        except Exception as e:
            logger.error(f"Error starting broadcast: {e}")
            await update.message.reply_text("❌ Failed to prepare broadcast")
    
    async def confirm_broadcast(self, broadcast_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and execute broadcast"""
        try:
            # Get broadcast details
            broadcast = await self._get_broadcast_record(broadcast_id)
            if not broadcast:
                await update.callback_query.message.reply_text("❌ Broadcast not found")
                return
            
            # Start broadcast task
            task = asyncio.create_task(self._execute_broadcast(broadcast_id, context))
            self.active_broadcasts[broadcast_id] = {
                'task': task,
                'started_at': datetime.now(),
                'status': 'running'
            }
            
            # Update broadcast status
            await self._update_broadcast_status(broadcast_id, 'running')
            
            await update.callback_query.message.reply_text(
                f"🚀 **Broadcast Started!**\n\n"
                f"📊 **Details:**\n"
                f"• Broadcast ID: {broadcast_id}\n"
                f"• Target Users: {broadcast['target_count']:,}\n"
                f"• Started: {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"📈 **Progress tracking enabled**\n"
                f"Use /broadcast_status {broadcast_id} to check progress",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log broadcast start
            self.db.log_action("INFO", f"Broadcast started", update.callback_query.from_user.id, f"Broadcast ID: {broadcast_id}")
            
        except Exception as e:
            logger.error(f"Error confirming broadcast: {e}")
            await update.callback_query.message.reply_text("❌ Failed to start broadcast")
    
    async def get_broadcast_status(self, broadcast_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get broadcast status and statistics"""
        try:
            broadcast = await self._get_broadcast_record(broadcast_id)
            if not broadcast:
                await update.message.reply_text("❌ Broadcast not found")
                return
            
            # Check if broadcast is active
            is_active = broadcast_id in self.active_broadcasts
            
            message = f"📊 **Broadcast Status** (ID: {broadcast_id})\n\n"
            
            if is_active:
                active_info = self.active_broadcasts[broadcast_id]
                elapsed = datetime.now() - active_info['started_at']
                
                message += (
                    f"🔄 **Status:** Running\n"
                    f"⏱️ **Running Time:** {self._format_duration(elapsed.total_seconds())}\n"
                    f"📤 **Sent:** {broadcast['success_count']:,}\n"
                    f"❌ **Failed:** {broadcast['failed_count']:,}\n"
                    f"📊 **Progress:** {self._calculate_progress(broadcast)}%\n"
                    f"🎯 **Target:** {broadcast['target_count']:,}\n\n"
                    f"📈 **Rate:** ~{self._calculate_send_rate(broadcast, elapsed.total_seconds())} msg/min"
                )
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Refresh", callback_data=f"broadcast_status_{broadcast_id}"),
                     InlineKeyboardButton("⏹️ Stop", callback_data=f"broadcast_stop_{broadcast_id}")]
                ]
            else:
                status_emoji = {
                    'completed': '✅',
                    'failed': '❌',
                    'cancelled': '⏹️',
                    'pending': '⏳'
                }.get(broadcast['status'], '❓')
                
                message += (
                    f"{status_emoji} **Status:** {broadcast['status'].title()}\n"
                    f"📤 **Sent:** {broadcast['success_count']:,}\n"
                    f"❌ **Failed:** {broadcast['failed_count']:,}\n"
                    f"🎯 **Target:** {broadcast['target_count']:,}\n"
                )
                
                if broadcast['completed_at']:
                    completed_time = datetime.fromisoformat(broadcast['completed_at'])
                    created_time = datetime.fromisoformat(broadcast['created_at'])
                    duration = completed_time - created_time
                    message += f"⏱️ **Duration:** {self._format_duration(duration.total_seconds())}\n"
                
                # Calculate success rate
                if broadcast['target_count'] > 0:
                    success_rate = (broadcast['success_count'] / broadcast['target_count']) * 100
                    message += f"📈 **Success Rate:** {success_rate:.1f}%"
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Refresh", callback_data=f"broadcast_status_{broadcast_id}")]
                ]
                
                if broadcast['status'] == 'completed' and broadcast['failed_count'] > 0:
                    keyboard.append([InlineKeyboardButton("📋 Failed Users", callback_data=f"broadcast_failed_{broadcast_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error getting broadcast status: {e}")
            await update.message.reply_text("❌ Failed to get broadcast status")
    
    async def stop_broadcast(self, broadcast_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop an active broadcast"""
        try:
            if broadcast_id not in self.active_broadcasts:
                await update.callback_query.message.reply_text("❌ Broadcast is not running")
                return
            
            # Cancel the task
            broadcast_info = self.active_broadcasts[broadcast_id]
            broadcast_info['task'].cancel()
            broadcast_info['status'] = 'cancelled'
            
            # Update database
            await self._update_broadcast_status(broadcast_id, 'cancelled')
            
            # Remove from active broadcasts
            del self.active_broadcasts[broadcast_id]
            
            await update.callback_query.message.reply_text(
                f"⏹️ **Broadcast Stopped**\n\n"
                f"Broadcast ID {broadcast_id} has been cancelled.\n"
                f"Use /broadcast_status {broadcast_id} to see final statistics.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log action
            self.db.log_action("INFO", f"Broadcast stopped", update.callback_query.from_user.id, f"Broadcast ID: {broadcast_id}")
            
        except Exception as e:
            logger.error(f"Error stopping broadcast: {e}")
            await update.callback_query.message.reply_text("❌ Failed to stop broadcast")
    
    async def _execute_broadcast(self, broadcast_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Execute the actual broadcast"""
        try:
            broadcast = await self._get_broadcast_record(broadcast_id)
            if not broadcast:
                logger.error(f"Broadcast {broadcast_id} not found")
                return
            
            # Get users to broadcast to
            users = await self._get_broadcast_users()
            
            success_count = 0
            failed_count = 0
            failed_users = []
            
            logger.info(f"Starting broadcast {broadcast_id} to {len(users)} users")
            
            for i, user in enumerate(users):
                try:
                    # Check if broadcast was cancelled
                    if broadcast_id not in self.active_broadcasts:
                        logger.info(f"Broadcast {broadcast_id} was cancelled")
                        break
                    
                    # Send message to user
                    await context.bot.send_message(
                        chat_id=user['user_id'],
                        text=broadcast['message'],
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    success_count += 1
                    
                    # Update progress every 50 messages
                    if (i + 1) % 50 == 0:
                        await self._update_broadcast_progress(broadcast_id, success_count, failed_count)
                    
                    # Rate limiting
                    await asyncio.sleep(self.config.BROADCAST_DELAY)
                    
                except Forbidden:
                    # User blocked the bot
                    failed_count += 1
                    failed_users.append({'user_id': user['user_id'], 'reason': 'blocked'})
                    
                except BadRequest as e:
                    # Invalid chat ID or other bad request
                    failed_count += 1
                    failed_users.append({'user_id': user['user_id'], 'reason': str(e)})
                    
                except Exception as e:
                    # Other errors
                    failed_count += 1
                    failed_users.append({'user_id': user['user_id'], 'reason': str(e)})
                    logger.error(f"Error sending to user {user['user_id']}: {e}")
                
                # Check if we're sending too fast
                if (i + 1) % 100 == 0:
                    await asyncio.sleep(1)  # Extra delay every 100 messages
            
            # Final update
            await self._update_broadcast_progress(broadcast_id, success_count, failed_count)
            await self._update_broadcast_status(broadcast_id, 'completed')
            
            # Store failed users info
            if failed_users:
                await self._store_failed_users(broadcast_id, failed_users)
            
            # Remove from active broadcasts
            if broadcast_id in self.active_broadcasts:
                del self.active_broadcasts[broadcast_id]
            
            logger.info(f"Broadcast {broadcast_id} completed: {success_count} sent, {failed_count} failed")
            
        except asyncio.CancelledError:
            logger.info(f"Broadcast {broadcast_id} was cancelled")
            await self._update_broadcast_status(broadcast_id, 'cancelled')
            
        except Exception as e:
            logger.error(f"Error executing broadcast {broadcast_id}: {e}")
            await self._update_broadcast_status(broadcast_id, 'failed')
            
            if broadcast_id in self.active_broadcasts:
                del self.active_broadcasts[broadcast_id]
    
    async def _get_broadcast_users(self) -> List[Dict]:
        """Get all users eligible for broadcast"""
        try:
            with self.db.lock:
                cursor = self.db.connection.cursor()
                # Get users active in last 30 days
                cursor.execute('''
                    SELECT user_id, username, first_name 
                    FROM users 
                    WHERE subscription_status = 'active'
                    AND last_activity > datetime('now', '-30 days')
                    ORDER BY last_activity DESC
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting broadcast users: {e}")
            return []
    
    async def _create_broadcast_record(self, admin_id: int, message: str, target_count: int) -> Optional[int]:
        """Create broadcast record in database"""
        try:
            with self.db.lock:
                cursor = self.db.connection.cursor()
                cursor.execute('''
                    INSERT INTO broadcasts (admin_id, message, target_count, status)
                    VALUES (?, ?, ?, 'pending')
                ''', (admin_id, message, target_count))
                self.db.connection.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error creating broadcast record: {e}")
            return None
    
    async def _get_broadcast_record(self, broadcast_id: int) -> Optional[Dict]:
        """Get broadcast record from database"""
        try:
            with self.db.lock:
                cursor = self.db.connection.cursor()
                cursor.execute('SELECT * FROM broadcasts WHERE id = ?', (broadcast_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting broadcast record: {e}")
            return None
    
    async def _update_broadcast_status(self, broadcast_id: int, status: str):
        """Update broadcast status"""
        try:
            with self.db.lock:
                cursor = self.db.connection.cursor()
                
                if status in ['completed', 'failed', 'cancelled']:
                    cursor.execute('''
                        UPDATE broadcasts 
                        SET status = ?, completed_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (status, broadcast_id))
                else:
                    cursor.execute('''
                        UPDATE broadcasts SET status = ? WHERE id = ?
                    ''', (status, broadcast_id))
                
                self.db.connection.commit()
                
        except Exception as e:
            logger.error(f"Error updating broadcast status: {e}")
    
    async def _update_broadcast_progress(self, broadcast_id: int, success_count: int, failed_count: int):
        """Update broadcast progress"""
        try:
            with self.db.lock:
                cursor = self.db.connection.cursor()
                cursor.execute('''
                    UPDATE broadcasts 
                    SET success_count = ?, failed_count = ? 
                    WHERE id = ?
                ''', (success_count, failed_count, broadcast_id))
                self.db.connection.commit()
                
        except Exception as e:
            logger.error(f"Error updating broadcast progress: {e}")
    
    async def _store_failed_users(self, broadcast_id: int, failed_users: List[Dict]):
        """Store failed users information"""
        try:
            # This could be stored in a separate table if needed
            # For now, we'll log it
            failed_user_ids = [user['user_id'] for user in failed_users]
            self.db.log_action(
                "WARNING", 
                f"Broadcast failed users", 
                None, 
                f"Broadcast ID: {broadcast_id}, Failed: {failed_user_ids}"
            )
            
        except Exception as e:
            logger.error(f"Error storing failed users: {e}")
    
    def _estimate_broadcast_time(self, user_count: int) -> str:
        """Estimate broadcast completion time"""
        try:
            # Calculate based on delay and rate limiting
            total_seconds = user_count * self.config.BROADCAST_DELAY
            
            # Add extra time for rate limiting
            extra_time = (user_count // 100) * 1  # 1 second per 100 messages
            total_seconds += extra_time
            
            return self._format_duration(total_seconds)
            
        except Exception:
            return "Unknown"
    
    def _calculate_progress(self, broadcast: Dict) -> int:
        """Calculate broadcast progress percentage"""
        try:
            if broadcast['target_count'] == 0:
                return 100
            
            completed = broadcast['success_count'] + broadcast['failed_count']
            return min(100, int((completed / broadcast['target_count']) * 100))
            
        except Exception:
            return 0
    
    def _calculate_send_rate(self, broadcast: Dict, elapsed_seconds: float) -> str:
        """Calculate sending rate"""
        try:
            if elapsed_seconds == 0:
                return "0"
            
            completed = broadcast['success_count'] + broadcast['failed_count']
            rate_per_second = completed / elapsed_seconds
            rate_per_minute = rate_per_second * 60
            
            return f"{rate_per_minute:.1f}"
            
        except Exception:
            return "0"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human readable format"""
        try:
            seconds = int(seconds)
            
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                return f"{seconds // 60}m {seconds % 60}s"
            else:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                return f"{hours}h {minutes}m"
                
        except Exception:
            return "Unknown"
    
    def get_active_broadcasts(self) -> Dict[int, Dict]:
        """Get all active broadcasts"""
        return self.active_broadcasts.copy()
    
    async def cleanup_old_broadcasts(self, days: int = 30):
        """Clean up old broadcast records"""
        try:
            with self.db.lock:
                cursor = self.db.connection.cursor()
                cursor.execute('''
                    DELETE FROM broadcasts 
                    WHERE created_at < datetime('now', '-{} days')
                    AND status IN ('completed', 'failed', 'cancelled')
                '''.format(days))
                
                deleted_count = cursor.rowcount
                self.db.connection.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old broadcast records")
                
        except Exception as e:
            logger.error(f"Error cleaning up broadcasts: {e}")
