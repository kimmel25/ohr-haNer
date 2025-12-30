"""
Async-Safe Logging Configuration
================================

This module provides thread-safe logging for async code using a queue-based approach.
Use this for high-concurrency scenarios where multiple async tasks are logging.

For simple use cases, logging_config.py is sufficient.

Usage:
    from logging_async_safe import setup_logging, stop_logging
    
    # At application start:
    setup_logging(log_dir=Path("logs"))
    
    # At application shutdown:
    stop_logging()
"""

import logging
import sys
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from pathlib import Path
from datetime import datetime
from typing import Optional


class AsyncSafeLogging:
    """Thread-safe logging for async code using QueueHandler/QueueListener."""
    
    def __init__(self):
        self.queue: Optional[Queue] = None
        self.listener: Optional[QueueListener] = None
        self._initialized = False
    
    def setup(
        self, 
        log_dir: Path = None, 
        level: int = logging.INFO,
        name_prefix: str = "ohr_haner"
    ) -> 'AsyncSafeLogging':
        """
        Set up async-safe logging.
        
        Args:
            log_dir: Directory for log files. If None, only console logging.
            level: Minimum log level
            name_prefix: Prefix for log file names
        
        Returns:
            Self for chaining
        """
        if self._initialized:
            return self
        
        self.queue = Queue(-1)  # Unlimited queue size
        handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        ))
        handlers.append(console_handler)
        
        # File handler (if log_dir specified)
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d')
            log_file = log_dir / f"{name_prefix}_{timestamp}.log"
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)  # Always log everything to file
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            handlers.append(file_handler)
            print(f"[ASYNC LOGGING] Log file: {log_file}")
        
        # Start the background listener thread
        self.listener = QueueListener(self.queue, *handlers, respect_handler_level=True)
        self.listener.start()
        
        # Configure root logger to use the queue
        queue_handler = QueueHandler(self.queue)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Capture everything, handlers will filter
        root_logger.handlers = [queue_handler]
        
        # Suppress noisy third-party loggers
        for name in ['httpx', 'httpcore', 'anthropic', 'urllib3', 'aiohttp']:
            logging.getLogger(name).setLevel(logging.WARNING)
        
        self._initialized = True
        
        # Log startup
        logging.info("=" * 60)
        logging.info("OHR HANER V2 - Async-safe logging initialized")
        logging.info("=" * 60)
        
        return self
    
    def stop(self):
        """
        Stop the background logging thread.
        
        Call this at application shutdown to ensure all log messages are flushed.
        """
        if self.listener:
            self.listener.stop()
            self.listener = None
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if logging has been initialized."""
        return self._initialized


# Singleton instance
_async_logging = AsyncSafeLogging()


def setup_logging(
    log_dir: Path = None, 
    level: int = logging.INFO,
    name_prefix: str = "ohr_haner"
) -> AsyncSafeLogging:
    """
    Set up async-safe logging.
    
    Args:
        log_dir: Directory for log files. If None, only console logging.
        level: Minimum log level
        name_prefix: Prefix for log file names
    
    Returns:
        The AsyncSafeLogging instance
    """
    return _async_logging.setup(log_dir=log_dir, level=level, name_prefix=name_prefix)


def stop_logging():
    """Stop the logging system. Call at application shutdown."""
    _async_logging.stop()


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return logging.getLogger(name)


def is_initialized() -> bool:
    """Check if logging has been initialized."""
    return _async_logging.is_initialized