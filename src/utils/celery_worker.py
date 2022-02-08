"""
Entry point for celery worker, start with:
    celery -A utils.celery_worker

"""


import importlib

from utils.celery_utils import celery_app  # noqa: F401
from utils.logger import logger

task_list = ["processors.posts.flair_processor"]

for task_defs in task_list:
    logger.debug(f"Importing tasks from {task_defs}")
    importlib.import_module(task_defs)
