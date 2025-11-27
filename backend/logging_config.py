"""
Logging Configuration for Marei Mekomos Backend

This module sets up a comprehensive logging system that writes to both
console and rotating log files, making it easy to debug issues.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging(log_level=logging.DEBUG):
    """
    Set up logging with both file and console handlers.

    Creates a 'logs' directory if it doesn't exist and configures:
    - Rotating file handler (max 10MB per file, keeps 5 backup files)
    - Console handler for real-time monitoring
    - Detailed formatting with timestamps, log levels, and function names
    """

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Create a unique log file name with timestamp
    log_filename = os.path.join(log_dir, f'marei_mekomos_{datetime.now().strftime("%Y%m%d")}.log')

    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # File handler with rotation (10MB max, keep 5 old files)
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Console handler (less verbose for console)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # Log startup message
    logger.info("="*80)
    logger.info(f"Logging system initialized - Log file: {log_filename}")
    logger.info("="*80)

    return logger


def get_logger(name: str):
    """
    Get a logger instance for a specific module/function.

    Usage:
        logger = get_logger(__name__)
        logger.info("This is an info message")
        logger.debug("This is a debug message")
        logger.error("This is an error message")
    """
    return logging.getLogger(name)
