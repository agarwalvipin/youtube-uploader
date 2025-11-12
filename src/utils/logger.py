"""
Logging configuration module for YouTube Uploader.

Provides structured logging with file rotation and multiple log levels.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class NoTracebackFilter(logging.Filter):
    """Filter that removes exception info from log records to prevent tracebacks on console."""

    def filter(self, record):
        # Remove exception info so traceback text is not printed to console handlers.
        record.exc_info = None
        record.exc_text = None
        return True


def setup_logger(
    name: str = "youtube_uploader",
    log_level: str = "INFO",
    log_dir: str = "./logs",
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 5,
    console_output: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger with file rotation and console output.

    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup log files to keep
        console_output: Whether to output logs to console

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter("[%(levelname)s] %(message)s")

    # Main application log file (INFO and above)
    main_log_file = log_path / f"{name}.log"
    main_handler = RotatingFileHandler(
        main_log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(detailed_formatter)
    logger.addHandler(main_handler)

    # Debug log file (all levels)
    debug_log_file = log_path / f"{name}_debug.log"
    debug_handler = RotatingFileHandler(
        debug_log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(detailed_formatter)
    logger.addHandler(debug_handler)

    # Error log file (ERROR and CRITICAL only)
    error_log_file = log_path / f"{name}_error.log"
    error_handler = RotatingFileHandler(
        error_log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)

    # Console handler (no traceback text)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(simple_formatter)
        # Prevent full traceback text from being printed to console; tracebacks should go to file handlers only
        console_handler.addFilter(NoTracebackFilter())
        logger.addHandler(console_handler)

    logger.info(f"Logger initialized: {name}")
    logger.debug(f"Log directory: {log_path.absolute()}")

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get an existing logger instance or create a default one.

    Args:
        name: Logger name (defaults to 'youtube_uploader')

    Returns:
        Logger instance
    """
    logger_name = name or "youtube_uploader"
    logger = logging.getLogger(logger_name)

    # If logger has no handlers, set up default configuration
    if not logger.handlers:
        return setup_logger(logger_name)

    return logger
