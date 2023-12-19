from enum import IntEnum, unique
import logging

logger = logging.getLogger(__name__)


@unique
class LOG_LEVEL(IntEnum):
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    NOTSET = logging.NOTSET


def set_log_level(level: LOG_LEVEL):
    logging.getLogger().setLevel(level)
    logger.info(f"Logging at level: {level.name}")


def init_logging(log_level: LOG_LEVEL, log_file=None):
    logging.basicConfig(
        force=log_file is None,  # Replace the default logger if logging to stderr
        datefmt="%H:%M:%S",
        filename=log_file,
        format="%(levelname)s %(asctime)s.%(msecs)d [%(name)s.%(funcName)s:%(lineno)d] "
        "%(message)s",
    )

    set_log_level(log_level)
