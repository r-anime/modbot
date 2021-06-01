# Tools

Various utilities are kept here to assist with the general functionality of modbot.


## Database Migrations

The database is managed using [Alembic](https://alembic.sqlalchemy.org/), see the documentation there
 for general use and detailed instructions.

To get the latest version of the database, start a shell in the tools container with
`docker-compose up run tools bash` then inside it:

    cd tools
    alembic upgrade head

You can also run it outside of a container with the appropriate environment variables set up for the database
connection (see `sqlalchemy.url` in `env.py`).
