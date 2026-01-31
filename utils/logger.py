"""
Simple logging configuration for price tracker scraper.
CloudWatch handles JSON formatting automatically for Lambda functions.
"""
import logging
import os


def get_logger(name: str = "price-tracker-scraper") -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Simple format - CloudWatch adds timestamps and request IDs automatically
        formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.propagate = False
    
    return logger
