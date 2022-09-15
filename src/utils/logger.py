"""Provides a singleton logger to be imported and used from any other module."""

import logging

import config_loader


logger = None


def _setup_logging():

    global logger

    logger = logging.getLogger("modbot")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)07s [%(filename)s:%(lineno)d] - %(message)s")

    log_file_path = config_loader.LOGGING["file_path"]
    if log_file_path:
        file_handler = logging.FileHandler(config_loader.LOGGING["file_path"])
        file_handler.setLevel(config_loader.LOGGING["log_level_file"])
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(config_loader.LOGGING["log_level_console"])
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    # Optional logging for PRAW.
    # for logger_name in ("praw", "prawcore"):
    #     logger = logging.getLogger(logger_name)
    #     logger.setLevel(logging.DEBUG)
    #     logger.addHandler(console_handler)
    #     if log_file_path:
    #         logger.addHandler(file_handler)


if logger is None:
    _setup_logging()
