# Telegram File Management Bot

## Overview

This is a comprehensive Telegram bot designed for advanced file management, processing, and distribution. The bot provides features like file upload/download with custom thumbnails, batch processing, force subscription management, broadcasting capabilities, and 24/7 monitoring. It's built to handle large-scale file operations with queue management, metadata extraction, pattern-based file renaming, and robust error handling.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Python-based Telegram Bot**: Built using the `python-telegram-bot` library with async/await patterns for concurrent operations
- **SQLite Database**: Single-file database for user data, preferences, file metadata, and bot analytics
- **Queue-based Processing**: Separate queues for upload/download operations with configurable concurrency limits
- **Modular Design**: Clear separation of concerns with dedicated modules for file management, thumbnails, broadcasting, subscriptions, and monitoring

### File Management System
- **Multi-format Support**: Handles videos, audio, images, and documents with comprehensive metadata extraction
- **Thumbnail Management**: Custom thumbnail support with permanent and temporary thumbnail options
- **Pattern-based Renaming**: Advanced file naming system with variables like counters, dates, user info, and metadata
- **Queue Processing**: Concurrent file operations with configurable limits and progress tracking

### User Management & Access Control
- **Force Subscription**: Mandatory channel subscription system with verification and caching
- **Admin Controls**: Multi-admin support with broadcast capabilities and user management
- **User Preferences**: Persistent storage of user settings, thumbnails, and naming patterns
- **Activity Tracking**: User activity monitoring and subscription status management

### Monitoring & Health System
- **24/7 Monitoring**: Continuous health checks with system resource monitoring (CPU, memory, disk)
- **Auto-recovery**: Automatic error recovery and alert systems
- **Performance Metrics**: Queue size monitoring, file processing statistics, and user activity tracking
- **Logging System**: Comprehensive logging with configurable retention and rotation

### Broadcasting System
- **Mass Messaging**: Efficient broadcast system with rate limiting and progress tracking
- **Error Handling**: Robust error handling for failed message deliveries
- **Analytics**: Delivery success tracking and user engagement metrics

### Configuration Management
- **Environment-based Config**: All settings configurable through environment variables
- **Resource Limits**: Configurable file size limits, queue sizes, and concurrent operations
- **Channel Integration**: Support for multiple force subscription channels and storage channels

## External Dependencies

### Core Framework
- **python-telegram-bot**: Primary Telegram Bot API wrapper for handling all bot interactions
- **asyncio**: Python's async framework for concurrent operations and non-blocking I/O

### Database & Storage
- **SQLite3**: Built-in Python database for persistent data storage
- **File System**: Local file storage for temporary downloads and processing

### File Processing
- **python-magic**: File type detection and MIME type identification
- **Pillow (PIL)**: Image processing for thumbnail generation and manipulation
- **mutagen**: Audio metadata extraction and manipulation (optional)
- **ffmpeg-python**: Video metadata extraction and processing (optional)

### System Monitoring
- **psutil**: System resource monitoring (CPU, memory, disk, network)
- **threading**: Multi-threaded processing for concurrent operations

### Utilities
- **pathlib**: Modern file path handling
- **hashlib**: File integrity verification and unique identification
- **tempfile**: Secure temporary file handling
- **mimetypes**: MIME type detection and validation

### Optional Enhancements
- **Additional metadata libraries**: For enhanced file format support
- **Compression libraries**: For file archiving and extraction
- **Cloud storage APIs**: For external file storage integration

The architecture is designed for scalability and maintainability, with clear module boundaries and async processing to handle multiple users concurrently. The bot can be easily extended with additional file formats, storage backends, or new features through its modular design.
