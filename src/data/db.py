from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config

from contextlib import contextmanager

engine = create_engine(config.DB["connection"])
Session = sessionmaker(bind=engine)


@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.
    """

    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
