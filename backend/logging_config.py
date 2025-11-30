"""
Logging Configuration for Marei Mekomos Backend V5

Comprehensive logging system with:
- Rotating file handler (max 10MB, 5 backups)
- Console handler for real-time monitoring
- Detailed formatting with timestamps
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(log_level=logging.DEBUG):
    """
    Set up logging with both file and console handlers.
    """
    # Create logs directory
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Log filename with date
    log_filename = os.path.join(log_dir, f'marei_mekomos_{datetime.now().strftime("%Y%m%d")}.log')
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Detailed format for file
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Simple format for console
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # Startup message
    logger.info("=" * 80)
    logger.info(f"Marei Mekomos V5 - Logging initialized")
    logger.info(f"Log file: {log_filename}")
    logger.info("=" * 80)
    
    return logger


def get_logger(name: str):
    """Get a logger instance for a specific module"""
    return logging.getLogger(name)
