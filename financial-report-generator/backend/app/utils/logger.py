"""
logger.py — Structured logging setup using Python's standard logging library.
Import `get_logger` and `log_timing` from this module in every service/router.
"""

import logging
import sys
import time
from contextlib import contextmanager
from config import settings


def get_logger(name: str = "bull_ai") -> logging.Logger:
    """
    Return a configured logger instance.

    Args:
        name: Logger name (typically the module __name__).

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    return logger


@contextmanager
def log_timing(logger: logging.Logger, stage: str):
    """
    Context manager that logs the elapsed time for a processing stage.

    Usage:
        with log_timing(logger, "Document Parsing"):
            result = parse_document(...)

    Logs:
        - START log at entry
        - DONE  log with elapsed time at exit
        - ERROR log if an exception occurs
    """
    logger.info(f"[STAGE START] {stage}")
    t0 = time.perf_counter()
    try:
        yield
        elapsed = time.perf_counter() - t0
        logger.info(f"[STAGE DONE ] {stage} — {elapsed:.2f}s")
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error(f"[STAGE FAIL ] {stage} — {elapsed:.2f}s — {exc}")
        raise


# Default module-level logger
logger = get_logger()
