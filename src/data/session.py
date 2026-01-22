from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config_loader

from contextlib import contextmanager

Session = None


def _create_session():
    _engine = create_engine(config_loader.DB_CONNECTION)
    global Session
    Session = sessionmaker(bind=_engine)


@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.
    """

    if Session is None:
        _create_session()
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
