"""Structured logging configuration for NEXUS."""

import logging
import sys


def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure and return root logger with structured formatting."""
    log_level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger("nexus")
    logger.setLevel(log_level)

    # Avoid adding duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_logging()
