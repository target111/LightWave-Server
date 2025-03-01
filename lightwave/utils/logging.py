"""
Logging utilities for LightWave-Server.

This module provides functions for setting up and retrieving loggers
with consistent configuration across the application.
"""

import logging
import sys
from typing import Optional

from lightwave.config import settings


def setup_logging() -> None:
    """
    Set up global logging configuration.
    
    Configures the root logger with appropriate handlers and formatters
    based on the application's configuration settings.
    """
    log_level = getattr(logging, settings.server.log_level.value)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers if any
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: The name of the logger. If None, returns the root logger.
        
    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)