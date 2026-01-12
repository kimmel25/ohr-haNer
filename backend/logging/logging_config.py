"""
Logging Configuration for Ohr Haner V2
=======================================

Sets up file and console logging with rotation.
Import this module early in your application to ensure logging is configured.

Usage:
    from logging_config import setup_logging, get_logger
    
    # Either let it auto-setup on import, or call explicitly:
    setup_logging()
    
    # Get a logger for your module:
    logger = get_logger(__name__)
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Create logs directory relative to this file
LOGS_DIR = Path(__file__).parent / "logs"

# Log file name with date
def get_log_file() -> Path:
    """Get the log file path, creating directory if needed."""
    LOGS_DIR.mkdir(exist_ok=True)
    return LOGS_DIR / f"ohr_haner_{datetime.now().strftime('%Y%m%d')}.log"

# Track if logging has been set up
_logging_initialized = False


def setup_logging(
    level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    force: bool = False
) -> logging.Logger:
    """
    Set up logging with both file and console handlers.
    
    Args:
        level: File handler log level (default: DEBUG)
        console_level: Console handler log level (default: INFO)
        force: Force re-initialization even if already initialized
    
    Returns:
        The root logger
    
    Features:
    - File: DEBUG level, rotates at 10MB, keeps 5 backups
    - Console: INFO level (or specified)
    - Thread-safe
    """
    global _logging_initialized
    
    if _logging_initialized and not force:
        return logging.getLogger()
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Formatter for file (detailed)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Formatter for console (concise)
    console_formatter = logging.Formatter(
        '%(levelname)-8s | %(message)s'
    )
    
    # File handler with rotation
    try:
        log_file = get_log_file()
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        print(f"[LOGGING] Log file: {log_file}")
    except Exception as e:
        print(f"[LOGGING] Warning: Could not create file handler: {e}")
    
    # Console handler with UTF-8 encoding for Hebrew text
    # On Windows, reconfigure stdout to handle UTF-8
    try:
        if sys.platform == 'win32':
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Suppress noisy third-party loggers
    for name in ['httpx', 'httpcore', 'google', 'urllib3', 'aiohttp']:
        logging.getLogger(name).setLevel(logging.WARNING)
    
    # Log startup
    root_logger.info("=" * 60)
    root_logger.info("OHR HANER V2 - Logging initialized")
    root_logger.info(f"Log file: {get_log_file()}")
    root_logger.info(f"Console level: {logging.getLevelName(console_level)}")
    root_logger.info(f"File level: {logging.getLevelName(level)}")
    root_logger.info("=" * 60)
    
    _logging_initialized = True
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Usually __name__ from the calling module
    
    Returns:
        A configured logger
    """
    # Ensure logging is set up
    if not _logging_initialized:
        setup_logging()
    return logging.getLogger(name)


def is_initialized() -> bool:
    """Check if logging has been initialized."""
    return _logging_initialized


# Auto-setup on import (but only once)
if not _logging_initialized:
    _logger = setup_logging()