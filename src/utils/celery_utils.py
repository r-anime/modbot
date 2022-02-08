from celery import Celery

import config_loader

celery_app = None


def initialize_celery() -> Celery:
    app = Celery("modbot", broker=config_loader.REDIS_CONNECTION)
    return app


if celery_app is None:
    celery_app = initialize_celery()
