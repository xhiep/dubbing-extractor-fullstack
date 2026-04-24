"""
Structured logging setup for dubbing-extractor application.

Provides centralized logging configuration with file rotation and console output.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    """
    Configure structured logging for the application.

    Sets up:
    - File logging to output/app.log with rotation (10MB max, 3 backups)
    - Console logging for ERROR level and above
    - Structured log format with timestamps

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create output directory if it doesn't exist
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get or create logger
    logger = logging.getLogger("dubbing_extractor")
    logger.setLevel(logging.INFO)

    # Avoid adding handlers multiple times if setup_logging is called again
    if logger.handlers:
        return logger

    # File handler with rotation
    log_file = os.path.join(output_dir, "app.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler for critical errors only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger
