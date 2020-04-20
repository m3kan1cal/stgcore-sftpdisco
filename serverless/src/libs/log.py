import logging
import sys


def setup_custom_logger(name):
    """Set up custom logger for specified namespace."""

    # Set up module logging levels and handlers.
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Remove any handlers that cloud provider attaches.
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)

    # Set up vendor library log settings.
    logging.getLogger('boto').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    logger.propagate = False

    return logger
