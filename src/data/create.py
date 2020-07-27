from sqlalchemy import create_engine

from data.models import BaseModel
import config

if __name__ == "__main__":
    engine = create_engine(config.DB["connection"])
    engine.execute("CREATE SCHEMA IF NOT EXISTS reddit;")
    BaseModel.metadata.create_all(engine)
