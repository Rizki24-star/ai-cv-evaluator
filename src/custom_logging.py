import logging
from enum import StrEnum

LOG_FORMAT_DEBUG = "%(levelname)s - %(message)s - %(pathname)s - %(funcName)s %(lineno)d"

class LogLevels(StrEnum):
    debug = "DEBUG"
    info = "INFO"
    warn = "WARNING"
    error = "ERROR"

def configure_logging(log_level: str = LogLevels.error):
    log_level = str(log_level).upper()
    valid_levels = [level.value for level in LogLevels]

    if log_level not in valid_levels:
        logging.basicConfig(level=logging.ERROR)
        return

    level_map = {
        LogLevels.debug: logging.DEBUG,
        LogLevels.info: logging.INFO,
        LogLevels.warn: logging.WARNING,
        LogLevels.error: logging.ERROR,
    }

    if log_level == LogLevels.debug:
        logging.basicConfig(level=level_map[LogLevels.debug], format=LOG_FORMAT_DEBUG)
        return

    logging.basicConfig(level=level_map[log_level])
