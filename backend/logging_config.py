"""
Logging Configuration for Marei Mekomos
========================================

This module configures logging to reduce noise from HTTP libraries
while preserving useful application-level logs.

Usage:
    from logging_config import setup_logging
    setup_logging()
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(
    log_level: int = logging.INFO,
    log_file: str = None,
    silence_http_libs: bool = True
):
    """
    Configure logging for the application.
    
    Args:
        log_level: Minimum log level for application logs
        log_file: Path to log file (optional)
        silence_http_libs: If True, silence verbose HTTP library logs
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all, filter at handler level
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Silence verbose HTTP libraries
    if silence_http_libs:
        # These libraries produce extremely verbose DEBUG logs
        # that make it hard to read application logs
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
        logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("Marei Mekomos V5 - Flexible Thinking - Logging initialized")
    if log_file:
        logger.info(f"Log file: {log_file}")
    logger.info("=" * 80)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Module name (typically __name__)
    
    Returns:
        Configured logger
    """
    return logging.getLogger(name)


# Convenience function to set up with default settings
def setup_default_logging():
    """Set up logging with sensible defaults for development."""
    today = datetime.now().strftime("%Y%m%d")
    log_file = f"logs/marei_mekomos_{today}.log"
    return setup_logging(
        log_level=logging.INFO,
        log_file=log_file,
        silence_http_libs=True
    )