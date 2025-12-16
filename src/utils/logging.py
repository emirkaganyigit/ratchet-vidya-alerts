from __future__ import annotations

import logging
import os


def get_logger(name: str) -> logging.Logger:
    level_str = (os.getenv("LOG_LEVEL", "INFO") or "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    logger = logging.getLogger(name)

    # Eğer daha önce handler eklendiyse tekrar ekleme
    if logger.handlers:
        logger.setLevel(level)
        for h in logger.handlers:
            h.setLevel(level)
        return logger

    logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger
