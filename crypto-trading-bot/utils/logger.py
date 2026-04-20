"""
Logger
=======
Structured logging with rich terminal output and file logging.
"""

import logging
import sys
from pathlib import Path

from rich.logging import RichHandler

_LOGGERS: dict = {}
_LOG_DIR = Path(__file__).parent.parent / "logs"


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Get or create a named logger with rich console + file handlers.

    Args:
        name: Logger name (usually __name__).
        level: Logging level string.

    Returns:
        Configured logging.Logger.
    """
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    # Rich console handler
    if not any(isinstance(h, RichHandler) for h in logger.handlers):
        console = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_path=False,
            markup=True,
        )
        console.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(message)s", datefmt="[%X]")
        console.setFormatter(fmt)
        logger.addHandler(console)

    # File handler
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = _LOG_DIR / "trading.log"
        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            file_fmt = logging.Formatter(
                "%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            fh.setFormatter(file_fmt)
            logger.addHandler(fh)
    except OSError:
        pass  # Skip file logging if directory not writable

    _LOGGERS[name] = logger
    return logger
