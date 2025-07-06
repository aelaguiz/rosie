"""
Logging configuration for Rosie voice transcription system
"""

import os
import logging
import logging.handlers
from datetime import datetime


def setup_logging(name="rosie", console_level=logging.INFO, file_level=logging.DEBUG):
    """
    Set up logging with both console and file handlers.
    
    Args:
        name: Logger name
        console_level: Minimum level for console output (default: INFO)
        file_level: Minimum level for file output (default: DEBUG)
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Console handler - clean output for users
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler - detailed debug output
    log_file = os.path.join(log_dir, f"{name}.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(file_level)
    file_format = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name):
    """Get a logger instance with the module name."""
    return logging.getLogger(f"rosie.{name}")