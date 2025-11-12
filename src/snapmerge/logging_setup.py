import logging
from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

_def_logger = None

def get_logger(name: str = "snapmerge", logfile: Path | None = None) -> logging.Logger:
    global _def_logger
    if _def_logger:
        return _def_logger

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(ch)

    if logfile:
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(fh)

    _def_logger = logger
    return logger