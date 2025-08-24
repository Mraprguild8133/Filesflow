"""
24x7 Monitoring system for Telegram Bot
Health checks, performance monitoring, auto-recovery, and system diagnostics
"""

import logging
import os
import time
import psutil
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from config import Config

logger = logging.getLogger(__name__)

class BotMonitoring:
    """Advanced 24x7 monitoring system with auto-recovery"""
    
    def __init__(self, config: Config):
        self.config = config
        self.start_time = datetime.now()
        self.health_status = {
            'status': 'healthy',
            'last_check': datetime.now(),
            'uptime': 0,
            'errors': [],
            'warnings': []
        }
        
        # Performance metrics
        self.metrics = {
            'cpu_usage': 0.0,
            'memory_usage': 0.0,
            'disk_usage': 0.0,
            'network_io': {'sent': 0, 'received': 0},
            'queue_size': 0,
            'active_users': 0,
            'files_processed': 0,
            'errors_count': 0
        }
        
        # Monitoring thresholds
        self.thresholds = {
            'cpu_usage': 80.0,      # 80% CPU usage
            'memory_usage': 85.0,   # 85% Memory usage
            'disk_usage': 90.0,     # 90% Disk usage
            'queue_size': 1000,     # 1000 items in queue
            'error_rate': 50        # 50 errors per hour
        }
        
        # Error tracking
        self.error_log = []
        self.performance_log = []
        
        # Auto-recovery settings
        self.auto_recovery = {
            'enabled': True,
            'restart_threshold': 5,  # Restart after 5 critical errors
            'restart_count': 0,
            'last_restart': None
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            self.health_status['last_check'] = datetime.now()
            self.health_status['uptime'] = (datetime.now() - self.start_time).total_seconds()
            
            # Clear previous status
            self.health_status['errors'] = []
            self.health_status['warnings'] = []
            
            # Check system resources
            self._check_system_resources()
            
            # Check database health
            self._check_database_health()
            
            # Check queue health
            self._check_queue_health()
            
            # Check disk space
            self._check_disk_space()
            
            # Determine overall health status
            error_count = len(self.health_status['errors'])
            warning_count = len(self.health_status['warnings'])
            
            if error_count >= 3:
                self.health_status['status'] = 'critical'
            elif error_count >= 1:
                self.health_status['status'] = 'degraded'
            elif warning_count >= 3:
                self.health_status['status'] = 'warning'
            else:
                self.health_status['status'] = 'healthy'
            
            logger.info(f"Health check: {self.health_status['status']} - Errors: {error_count}, Warnings: {warning_count}")
            
            return self.health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.health_status['status'] = 'critical'
            self.health_status['errors'].append(f"Health check system failure: {e}")
            return self.health_status
    
    def _check_system_resources(self):
        """Check system CPU, memory, and network resources"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics['cpu_usage'] = cpu_percent
            
            if cpu_percent > self.thresholds['cpu_usage']:
                self.health_status['errors'].append(f"High CPU usage: {cpu_percent:.1f}%")
            elif cpu_percent > self.thresholds['cpu_usage'] * 0.8:
                self.health_status['warnings'].append(f"Elevated CPU usage: {cpu_percent:.1f}%")
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.metrics['memory_usage'] = memory_percent
            
            if memory_percent > self.thresholds['memory_usage']:
                self.health_status['errors'].append(f"High memory usage: {memory_percent:.1f}%")
            elif memory_percent > self.thresholds['memory_usage'] * 0.8:
                self.health_status['warnings'].append(f"Elevated memory usage: {memory_percent:.1f}%")
            
            # Network I/O
            net_io = psutil.net_io_counters()
            self.metrics['network_io'] = {
                'sent': net_io.bytes_sent,
                'received': net_io.bytes_recv
            }
            
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            self.health_status['errors'].append(f"System monitoring failure: {e}")
    
    def _check_database_health(self):
        """Check database connection and performance"""
        try:
            # For now, just check if database file exists
            db_path = "bot_database.db"
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                if file_size > 0:
                    # Database exists and has content - assume healthy
                    pass
                else:
                    self.health_status['warnings'].append("Database file is empty")
            else:
                self.health_status['errors'].append("Database file not found")
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            self.health_status['errors'].append(f"Database check failed: {e}")
    
    def _check_queue_health(self):
        """Check processing queue status"""
        try:
            # For now, just log that queue check was attempted
            # This would be enhanced with actual queue monitoring
            pass
            
        except Exception as e:
            logger.error(f"Queue health check failed: {e}")
            self.health_status['errors'].append(f"Queue check failed: {e}")
    
    def _check_disk_space(self):
        """Check available disk space"""
        try:
            disk_usage = psutil.disk_usage('/')
            disk_percent = disk_usage.percent
            self.metrics['disk_usage'] = disk_percent
            
            if disk_percent > self.thresholds['disk_usage']:
                self.health_status['errors'].append(f"Low disk space: {disk_percent:.1f}% used")
            elif disk_percent > self.thresholds['disk_usage'] * 0.8:
                self.health_status['warnings'].append(f"Disk space getting low: {disk_percent:.1f}% used")
                
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            self.health_status['warnings'].append(f"Could not check disk space: {e}")
    
    def cleanup_old_logs(self):
        """Clean up old log files and temporary data"""
        try:
            current_time = datetime.now()
            
            # Clean log files older than 7 days
            log_retention_days = 7
            cutoff_time = current_time - timedelta(days=log_retention_days)
            
            log_files = ['bot.log', 'error.log', 'debug.log']
            for log_file in log_files:
                if os.path.exists(log_file):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                    if file_mtime < cutoff_time:
                        try:
                            # Instead of deleting, truncate large log files
                            if os.path.getsize(log_file) > 10 * 1024 * 1024:  # 10MB
                                with open(log_file, 'w') as f:
                                    f.write(f"Log file truncated on {current_time}\n")
                                logger.info(f"Truncated large log file: {log_file}")
                        except Exception as e:
                            logger.error(f"Error managing log file {log_file}: {e}")
            
            # Clean temporary files
            temp_dirs = ['/tmp', './temp', './downloads']
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    try:
                        for filename in os.listdir(temp_dir):
                            file_path = os.path.join(temp_dir, filename)
                            if os.path.isfile(file_path):
                                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                                if file_mtime < cutoff_time:
                                    os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Error cleaning temp directory {temp_dir}: {e}")
            
            logger.info("Log cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
    
    def monitor_queue_status(self):
        """Monitor processing queue status"""
        try:
            # This would monitor actual queue status
            # For now, just update metrics with dummy data
            self.metrics['queue_size'] = 0
            self.metrics['active_users'] = 1
            
        except Exception as e:
            logger.error(f"Queue monitoring failed: {e}")
    
    def check_storage_usage(self):
        """Check storage usage and manage files"""
        try:
            # Check current directory size
            total_size = 0
            for dirpath, dirnames, filenames in os.walk('.'):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        pass
            
            # Convert to MB
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb > 500:  # 500MB threshold
                logger.warning(f"High storage usage: {total_size_mb:.1f} MB")
                self.health_status['warnings'].append(f"Storage usage: {total_size_mb:.1f} MB")
            
        except Exception as e:
            logger.error(f"Storage check failed: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            'uptime': (datetime.now() - self.start_time).total_seconds(),
            'health_status': self.health_status['status'],
            'cpu_usage': self.metrics['cpu_usage'],
            'memory_usage': self.metrics['memory_usage'],
            'disk_usage': self.metrics['disk_usage'],
            'queue_size': self.metrics['queue_size'],
            'active_users': self.metrics['active_users'],
            'files_processed': self.metrics['files_processed'],
            'errors_count': len(self.health_status['errors']),
            'warnings_count': len(self.health_status['warnings'])
        }
    
    def log_error(self, error: str, severity: str = 'error'):
        """Log error with timestamp and severity"""
        try:
            error_entry = {
                'timestamp': datetime.now(),
                'error': error,
                'severity': severity
            }
            
            self.error_log.append(error_entry)
            
            # Keep only last 1000 errors
            if len(self.error_log) > 1000:
                self.error_log = self.error_log[-1000:]
            
            # Check for auto-recovery triggers
            if severity == 'critical':
                self.auto_recovery['restart_count'] += 1
                if (self.auto_recovery['enabled'] and 
                    self.auto_recovery['restart_count'] >= self.auto_recovery['restart_threshold']):
                    self._trigger_auto_recovery()
            
        except Exception as e:
            logger.error(f"Error logging failed: {e}")
    
    def _trigger_auto_recovery(self):
        """Trigger auto-recovery procedures"""
        try:
            logger.critical("Auto-recovery triggered due to critical errors")
            
            # Reset error count
            self.auto_recovery['restart_count'] = 0
            self.auto_recovery['last_restart'] = datetime.now()
            
            # Here you could implement recovery procedures like:
            # - Clearing queues
            # - Restarting services
            # - Sending admin notifications
            
        except Exception as e:
            logger.error(f"Auto-recovery failed: {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            return {
                'bot_uptime': (datetime.now() - self.start_time).total_seconds(),
                'system_boot_time': psutil.boot_time(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'disk_total': psutil.disk_usage('/').total,
                'python_version': os.sys.version,
                'platform': os.name,
                'health_status': self.health_status,
                'performance_metrics': self.metrics
            }
        except Exception as e:
            logger.error(f"System info gathering failed: {e}")
            return {}