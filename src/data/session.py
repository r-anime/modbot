from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config_loader

from contextlib import contextmanager

_engine = create_engine(config_loader.DB_CONNECTION)
Session = sessionmaker(bind=_engine)


@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.
    """

    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
