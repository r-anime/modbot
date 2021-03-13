# modbot
A collection of Python scripts for monitoring and moderating /r/anime, designed to (eventually) be a cohesive backend for most automated work around a single subreddit.

**Note: Below section is currently out of date while under transition to Docker.**

## Features
* Relays all new submissions to Discord
* Takes a snapshot of the front page for later analysis, including how many posts of a given type (flair) are present  

## Requirements
* Python 3.6+ (new submissions)
* SQLAlchemy (for front page only)
* Docker and docker-compose (mod log)

## Setup
* Copy `config.py.eaxmple` to `config.py` and update values for Reddit/Discord.
* Install Python packages in `requirements.txt`

### Mod Log
* Copy and update `docker-compose.sample.yml` as appropriate.
* Start the database and build the tools container: `docker-compose up db tools`
* Run database update scripts (see `tools/README.md`)
* Start monitoring mod actions: `docker-compose up mod_log`

### New Submissions
* Run `python3 new.py` — this will run in the foreground so may want to use screen or tmux.

### Front Page
* Configure `crontab` or other way of scheduling to run `frontpage.py` once per hour, e.g.
 * `0 * * * * cd /opt/r-anime/modbot/src/; /opt/r-anime/modbot/.venv/bin/python3 /opt/r-anime/modbot/src/frontpage.py`
