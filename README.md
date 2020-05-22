# modbot
A collection of Python scripts for monitoring and moderating /r/anime, designed to (eventually) be a cohesive backend for most automated work around a single subreddit.

## Features
* Relays all new submissions to Discord
* Takes a snapshot of the front page for later analysis, including how many posts of a given type (flair) are present  

## Requirements
* Python 3.6+
* PRAW
* SQLAlchemy (for front page only)


## Setup
* Copy `config.py.eaxmple` to `config.py` and update values for Reddit/Discord.
* Install Python packages in `requirements.txt`

### New Submissions
* Run `python3 new.py` — this will run in the foreground so may want to use screen or tmux.

### Front Page
* Configure `crontab` or other way of scheduling to run `frontpage.py` once per hour, e.g.
 * `0 * * * * cd /opt/r-anime/modbot/src/; /opt/r-anime/modbot/.venv/bin/python3 /opt/r-anime/modbot/src/frontpage.py`
