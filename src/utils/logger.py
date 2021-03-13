"""Provides a singleton logger to be imported and used from any other module."""

import logging

import config


logger = None


def _setup_logging():

    global logger

    logger = logging.getLogger("modbot")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)07s [%(filename)s:%(lineno)d] - %(message)s")

    file_handler = logging.FileHandler(config.LOGGING["file_path"])
    file_handler.setLevel(config.LOGGING["log_level_file"])
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.LOGGING["log_level_console"])
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


if logger is None:
    _setup_logging()
