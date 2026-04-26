"""
Unified logging configuration for WorkSpeak.
Both CDP overlay and Slack bot use the same logging setup.
"""

import logging
import sys
from typing import Optional

def setup_logging(
    level: int = logging.INFO,
    name: str = "workspeak",
    log_to_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up unified logging for WorkSpeak.
    
    Args:
        level: Logging level (INFO, DEBUG, etc.)
        name: Logger name
        log_to_file: Path to log file (optional)
        format_string: Custom format string (optional)
    
    Returns:
        Configured logger instance
    """
    
    if format_string is None:
        format_string = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_to_file:
        try:
            file_handler = logging.FileHandler(log_to_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file {log_to_file}: {e}")
    
    return logger

# Default logger instance
_default_logger: Optional[logging.Logger] = None

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get or create the default logger."""
    global _default_logger
    
    if name is None:
        if _default_logger is None:
            _default_logger = setup_logging()
        return _default_logger
    
    return logging.getLogger(f"workspeak.{name}")
