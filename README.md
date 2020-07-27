# modbot
A collection of Python scripts for monitoring and moderating /r/anime, designed to (eventually) be a cohesive backend for most automated work around a single subreddit.

## Features
* Relays all new submissions to Discord
* Saves metadata for every new submission (user, flair, creation time)
* Takes a snapshot of the front page for later analysis, including how many posts of a given type (flair) are present  

## Requirements
* Docker 19.03+ and docker-compose 1.23+ (which will run the following in containers)

OR

* Python 3.6+
* PostgreSQL or other relational database supported by SQLalchemy
* Celery with a broker backend (can use the same database, this project uses RabbitMQ)

## Setup - Docker
* Copy `config.py.eaxmple` to `config.py` and update values for Reddit/Discord.
* Run `docker-compose up dev.docker-compose.yml`

## Setup - Other

### New Submissions
* Run `python3 new.py` — this will run in the foreground so may want to use screen or tmux.
* Run `celery worker --app processor.post_processor`

### Front Page
* Configure `crontab` or other way of scheduling to run `frontpage.py` once per hour, e.g.
 * `0 * * * * cd /opt/r-anime/modbot/src/; /opt/r-anime/modbot/.venv/bin/python3 /opt/r-anime/modbot/src/frontpage.py`
