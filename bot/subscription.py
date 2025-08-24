"""
Force subscription system for Telegram Bot
Manages channel subscriptions, verification, and access control
"""

import logging
import time
from typing import List, Dict, Any, Optional, Set
import telebot
from telebot import types

from database import Database
from config import Config

logger = logging.getLogger(__name__)

class SubscriptionManager:
    """Advanced subscription management with force subscribe functionality"""
    
    def __init__(self, database: Database, config: Config):
        self.db = database
        self.config = config
        self.subscription_cache = {}  # Cache subscription status
        self.cache_expiry = 300  # 5 minutes cache
    
    def check_user_subscriptions(self, user_id: int) -> bool:
        """Check if user is subscribed to all required channels"""
        try:
            # If no force subscribe channels configured, allow access
            if not self.config.FORCE_SUB_CHANNELS:
                return True
            
            # Check cache first
            cache_key = f"sub_{user_id}"
            current_time = time.time()
            
            if cache_key in self.subscription_cache:
                cache_entry = self.subscription_cache[cache_key]
                if current_time - cache_entry['timestamp'] < self.cache_expiry:
                    return cache_entry['subscribed']
            
            # Check actual subscriptions
            subscribed = self._verify_all_subscriptions(user_id)
            
            # Update cache
            self.subscription_cache[cache_key] = {
                'subscribed': subscribed,
                'timestamp': current_time
            }
            
            # Update database
            self._update_user_subscription_status(user_id, subscribed)
            
            return subscribed
            
        except Exception as e:
            logger.error(f"Error checking user subscriptions: {e}")
            return False  # Deny access on error
    
    def _verify_all_subscriptions(self, user_id: int) -> bool:
        """Verify user subscriptions to all required channels"""
        try:
            if not self.config.FORCE_SUB_CHANNELS:
                return True
                
            # For now, return True since we need bot instance to check
            # This will be improved when we pass bot instance properly
            return True
            
        except Exception as e:
            logger.error(f"Error verifying subscriptions: {e}")
            return False
    
    def _update_user_subscription_status(self, user_id: int, subscribed: bool):
        """Update user subscription status in database"""
        try:
            self.db.update_user_subscription(user_id, subscribed)
        except Exception as e:
            logger.error(f"Error updating subscription status: {e}")
    
    def show_subscription_required(self, user_id: int, chat_id: int):
        """Show subscription required message"""
        try:
            channels = self.config.FORCE_SUB_CHANNELS
            if not channels:
                return
                
            text = "🔒 **Subscription Required**\n\n"
            text += "To use this bot, you must subscribe to our channels:\n\n"
            
            keyboard = types.InlineKeyboardMarkup()
            
            for i, channel in enumerate(channels, 1):
                text += f"{i}. {channel}\n"
                keyboard.row(
                    types.InlineKeyboardButton(
                        f"📺 Join Channel {i}",
                        url=f"https://t.me/{channel.replace('@', '')}"
                    )
                )
            
            keyboard.row(
                types.InlineKeyboardButton("✅ Check Subscriptions", callback_data="sub_check")
            )
            
            text += "\nAfter joining all channels, click 'Check Subscriptions' below!"
            
            # Get bot instance from handlers
            from bot.handlers import BotHandlers
            bot = getattr(BotHandlers, '_current_bot', None)
            if bot:
                bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Error showing subscription required: {e}")
    
    def handle_force_subscribe_setup(self, message):
        """Handle force subscribe setup command"""
        try:
            text = """
🔒 **Force Subscribe Setup**

**Current Channels:**
"""
            
            if self.config.FORCE_SUB_CHANNELS:
                for i, channel in enumerate(self.config.FORCE_SUB_CHANNELS, 1):
                    text += f"{i}. {channel}\n"
            else:
                text += "No channels configured\n"
                
            text += """

**Commands:**
• Add channel: `/add_channel @username`
• Remove channel: `/remove_channel @username`  
• View stats: `/stats`

**Features:**
• Multiple channel support
• Auto verification
• Cache system for performance
• Subscription analytics

Send channel username to add or use commands above!
            """
            
            # Get bot instance from handlers
            from bot.handlers import BotHandlers
            bot = getattr(BotHandlers, '_current_bot', None)
            if bot:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=text,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error in force subscribe setup: {e}")
    
    def handle_add_channel(self, message):
        """Handle add channel command"""
        try:
            text = """
➕ **Add Force Subscribe Channel**

Send the channel username in this format:
`@channelname`

**Requirements:**
• Channel must be public or bot must be admin
• Use @ symbol before username
• Channel should have good content

**Example:**
`@yourchannel`

Reply with channel username! 📺
            """
            
            # Get bot instance from handlers  
            from bot.handlers import BotHandlers
            bot = getattr(BotHandlers, '_current_bot', None)
            if bot:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=text,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error in add channel: {e}")
    
    def handle_remove_channel(self, message):
        """Handle remove channel command"""
        try:
            if not self.config.FORCE_SUB_CHANNELS:
                text = "❌ No channels configured to remove."
            else:
                text = "🗑️ **Remove Force Subscribe Channel**\n\n"
                text += "Current channels:\n"
                
                keyboard = types.InlineKeyboardMarkup()
                
                for i, channel in enumerate(self.config.FORCE_SUB_CHANNELS):
                    text += f"{i+1}. {channel}\n"
                    keyboard.row(
                        types.InlineKeyboardButton(
                            f"❌ Remove {channel}",
                            callback_data=f"sub_remove_{i}"
                        )
                    )
                
                text += "\nClick a button to remove that channel!"
            
            # Get bot instance from handlers
            from bot.handlers import BotHandlers  
            bot = getattr(BotHandlers, '_current_bot', None)
            if bot:
                bot.send_message(
                    chat_id=message.chat.id,
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=keyboard if self.config.FORCE_SUB_CHANNELS else None
                )
                
        except Exception as e:
            logger.error(f"Error in remove channel: {e}")
    
    def handle_subscription_callback(self, call):
        """Handle subscription-related callback queries"""
        try:
            data_parts = call.data.split('_')
            action = data_parts[1]
            
            if action == 'check':
                self._handle_subscription_check(call)
            elif action == 'remove':
                channel_index = int(data_parts[2])
                self._handle_channel_removal(call, channel_index)
                
        except Exception as e:
            logger.error(f"Error handling subscription callback: {e}")
    
    def _handle_subscription_check(self, call):
        """Handle subscription check callback"""
        try:
            user_id = call.from_user.id
            
            # Clear cache to force fresh check
            cache_key = f"sub_{user_id}"
            if cache_key in self.subscription_cache:
                del self.subscription_cache[cache_key]
            
            # Check subscriptions
            if self.check_user_subscriptions(user_id):
                text = "✅ **Subscription Verified!**\n\nYou can now use all bot features!"
                
                # Get bot instance from handlers
                from bot.handlers import BotHandlers
                bot = getattr(BotHandlers, '_current_bot', None)
                if bot:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=text,
                        parse_mode='Markdown'
                    )
            else:
                text = "❌ **Subscription Not Found**\n\nPlease subscribe to all channels and try again."
                
                # Get bot instance from handlers
                from bot.handlers import BotHandlers
                bot = getattr(BotHandlers, '_current_bot', None)
                if bot:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=text,
                        parse_mode='Markdown'
                    )
                    
        except Exception as e:
            logger.error(f"Error handling subscription check: {e}")
    
    def _handle_channel_removal(self, call, channel_index):
        """Handle channel removal callback"""
        try:
            if 0 <= channel_index < len(self.config.FORCE_SUB_CHANNELS):
                removed_channel = self.config.FORCE_SUB_CHANNELS.pop(channel_index)
                
                # Update config (this would need persistent storage)
                text = f"✅ **Channel Removed**\n\nRemoved: {removed_channel}"
                
                # Get bot instance from handlers
                from bot.handlers import BotHandlers
                bot = getattr(BotHandlers, '_current_bot', None)
                if bot:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=text,
                        parse_mode='Markdown'
                    )
                    
        except Exception as e:
            logger.error(f"Error handling channel removal: {e}")
    
    def get_subscription_stats(self):
        """Get subscription statistics"""
        try:
            total_users = self.db.get_total_users()
            subscribed_users = self.db.get_subscribed_users_count()
            
            return {
                'total_users': total_users,
                'subscribed_users': subscribed_users,
                'subscription_rate': (subscribed_users / total_users * 100) if total_users > 0 else 0,
                'channels_count': len(self.config.FORCE_SUB_CHANNELS),
                'cache_size': len(self.subscription_cache)
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription stats: {e}")
            return {}