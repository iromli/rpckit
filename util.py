from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
import logging
import time


def make_logger(**opts):
    name = opts.get("name")
    level = opts.get("level", "info")

    level_mapper = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    ch = logging.StreamHandler()
    fmt = logging.Formatter(
        "[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    ch.setFormatter(fmt)
    logger = logging.getLogger(name)
    logger.setLevel(level_mapper.get(level, logging.INFO))
    logger.addHandler(ch)
    return logger


def clock_time():
    # TODO: Windows support?
    return time.clock() * 1000
