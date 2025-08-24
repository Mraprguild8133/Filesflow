#!/usr/bin/env python3
"""
Professional Telegram Bot - Main Entry Point
Advanced file management, batch processing, force subscribe, and 24x7 monitoring
"""

import logging
import os
import threading
import time
import telebot
from telebot import types
from bot.handlers import BotHandlers
from bot.monitoring import BotMonitoring
from config import Config
from database import Database

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.config = Config()
        self.database = Database()
        self.bot = telebot.TeleBot(self.config.BOT_TOKEN)
        self.handlers = BotHandlers(self.database, self.config, self.bot)
        self.monitoring = BotMonitoring(self.config)
        self.monitoring_thread = None
        
    def setup_handlers(self):
        """Setup all bot command and message handlers"""
        
        # Command handlers
        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            self.handlers.start_command(message)
            
        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            self.handlers.help_command(message)
            
        @self.bot.message_handler(commands=['rename'])
        def rename_command(message):
            self.handlers.rename_command(message)
            
        @self.bot.message_handler(commands=['batch_rename'])
        def batch_rename_command(message):
            self.handlers.batch_rename_command(message)
            
        @self.bot.message_handler(commands=['set_thumbnail'])
        def set_thumbnail_command(message):
            self.handlers.set_thumbnail_command(message)
            
        @self.bot.message_handler(commands=['permanent_thumb'])
        def permanent_thumbnail_command(message):
            self.handlers.permanent_thumbnail_command(message)
            
        @self.bot.message_handler(commands=['metadata'])
        def metadata_command(message):
            self.handlers.metadata_command(message)
            
        @self.bot.message_handler(commands=['caption'])
        def caption_command(message):
            self.handlers.caption_command(message)
            
        @self.bot.message_handler(commands=['broadcast'])
        def broadcast_command(message):
            self.handlers.broadcast_command(message)
            
        @self.bot.message_handler(commands=['stats'])
        def stats_command(message):
            self.handlers.stats_command(message)
            
        @self.bot.message_handler(commands=['logs'])
        def logs_command(message):
            self.handlers.logs_command(message)
            
        @self.bot.message_handler(commands=['settings'])
        def settings_command(message):
            self.handlers.settings_command(message)
            
        @self.bot.message_handler(commands=['auto_rename'])
        def auto_rename_command(message):
            self.handlers.auto_rename_command(message)
            
        @self.bot.message_handler(commands=['pattern'])
        def pattern_command(message):
            self.handlers.pattern_command(message)
            
        @self.bot.message_handler(commands=['queue'])
        def queue_command(message):
            self.handlers.queue_command(message)
            
        # Admin commands
        @self.bot.message_handler(commands=['force_sub'])
        def force_subscribe_command(message):
            self.handlers.force_subscribe_command(message)
            
        @self.bot.message_handler(commands=['add_channel'])
        def add_channel_command(message):
            self.handlers.add_channel_command(message)
            
        @self.bot.message_handler(commands=['remove_channel'])
        def remove_channel_command(message):
            self.handlers.remove_channel_command(message)
            
        @self.bot.message_handler(commands=['set_log_channel'])
        def set_log_channel_command(message):
            self.handlers.set_log_channel_command(message)
            
        @self.bot.message_handler(commands=['set_storage'])
        def set_storage_command(message):
            self.handlers.set_storage_command(message)
            
        # File handlers
        @self.bot.message_handler(content_types=['document'])
        def handle_document(message):
            self.handlers.handle_document(message)
            
        @self.bot.message_handler(content_types=['photo'])
        def handle_photo(message):
            self.handlers.handle_photo(message)
            
        @self.bot.message_handler(content_types=['video'])
        def handle_video(message):
            self.handlers.handle_video(message)
            
        @self.bot.message_handler(content_types=['audio'])
        def handle_audio(message):
            self.handlers.handle_audio(message)
            
        @self.bot.message_handler(content_types=['voice'])
        def handle_voice(message):
            self.handlers.handle_voice(message)
            
        @self.bot.message_handler(content_types=['video_note'])
        def handle_video_note(message):
            self.handlers.handle_video_note(message)
            
        @self.bot.message_handler(content_types=['animation'])
        def handle_animation(message):
            self.handlers.handle_animation(message)
            
        # Callback query handler
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_query_handler(call):
            self.handlers.callback_query_handler(call)
            
        # Text message handler (for rename inputs, etc.)
        @self.bot.message_handler(func=lambda message: True)
        def handle_text(message):
            self.handlers.handle_text(message)
        
        logger.info("All handlers setup completed")
    
    def start_monitoring(self):
        """Start the monitoring thread for 24x7 operation"""
        def monitor_loop():
            while True:
                try:
                    self.monitoring.health_check()
                    self.monitoring.cleanup_old_logs()
                    self.monitoring.monitor_queue_status()
                    self.monitoring.check_storage_usage()
                    
                    # Sleep for 5 minutes between checks
                    time.sleep(300)
                    
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        
        self.monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("24x7 Monitoring system started")
    
    def start_bot(self):
        """Start the bot with error handling and auto-restart capability"""
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Starting Telegram Bot (Attempt {retry_count + 1}/{max_retries})")
                
                # Initialize database
                self.database.init_db()
                
                # Setup handlers
                self.setup_handlers()
                
                # Start monitoring
                self.start_monitoring()
                
                # Start polling
                logger.info("Bot started successfully! Listening for messages...")
                self.bot.infinity_polling(timeout=10, long_polling_timeout=5)
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Bot startup failed (Attempt {retry_count}): {e}")
                
                if retry_count < max_retries:
                    wait_time = min(300, 60 * retry_count)  # Max 5 minutes
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.critical("Maximum retries reached. Bot shutting down.")
                    break
    
    def shutdown(self):
        """Gracefully shutdown the bot"""
        logger.info("Shutting down bot...")
        
        try:
            self.bot.stop_polling()
            
            # Close database connection
            self.database.close()
            
            logger.info("Bot shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

def main():
    """Main entry point with auto-restart capability"""
    bot = TelegramBot()
    
    try:
        # Start the bot
        bot.start_bot()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        
    finally:
        bot.shutdown()

if __name__ == "__main__":
    try:
        # Run the bot
        main()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}")