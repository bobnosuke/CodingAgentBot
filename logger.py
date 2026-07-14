"""
Logging configuration for CoderAgent
"""
import logging
import logging.handlers
from config import Config
from pathlib import Path

def setup_logger(name: str) -> logging.Logger:
    """
    Setup logger with both file and console handlers
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set log level
    log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        Config.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    return logger


# Create module-level logger
logger = setup_logger(__name__)
