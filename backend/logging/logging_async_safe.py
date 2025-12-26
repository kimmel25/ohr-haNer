"""
Async-Safe Logging Configuration
"""

import logging
import sys
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from pathlib import Path
from datetime import datetime
from typing import Optional


class AsyncSafeLogging:
    """Thread-safe logging for async code."""
    
    def __init__(self):
        self.queue: Optional[Queue] = None
        self.listener: Optional[QueueListener] = None
        self._initialized = False
    
    def setup(
        self, 
        log_dir: Path = None, 
        level: int = logging.INFO,
        name_prefix: str = "marei_mekomos"
    ) -> 'AsyncSafeLogging':
        """Set up async-safe logging."""
        if self._initialized:
            return self
        
        self.queue = Queue(-1)
        handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        ))
        handlers.append(console_handler)
        
        # File handler
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d')
            log_file = log_dir / f"{name_prefix}_{timestamp}.log"
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            handlers.append(file_handler)
            print(f"Log file: {log_file}")
        
        # Queue listener
        self.listener = QueueListener(self.queue, *handlers, respect_handler_level=True)
        self.listener.start()
        
        # Configure root logger
        queue_handler = QueueHandler(self.queue)
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers = [queue_handler]
        
        # Suppress noisy loggers
        for name in ['httpx', 'httpcore', 'anthropic']:
            logging.getLogger(name).setLevel(logging.WARNING)
        
        self._initialized = True
        return self
    
    def stop(self):
        """Stop the background logging thread."""
        if self.listener:
            self.listener.stop()
            self.listener = None
        self._initialized = False


_logging = AsyncSafeLogging()


def setup_logging(log_dir: Path = None, level: int = logging.INFO) -> AsyncSafeLogging:
    """Set up async-safe logging."""
    return _logging.setup(log_dir=log_dir, level=level)


def stop_logging():
    """Stop the logging system."""
    _logging.stop()