# modbot
A collection of Python scripts for monitoring and moderating /r/anime, designed to (eventually) be a cohesive backend for most automated work around a single subreddit.

## Features
* Saves all posts and comments made on the subreddit to a database for statistical analysis
* Relays all new submissions, mod actions taken by admins, and subreddit mentions to Discord
* Takes a snapshot of the front page for later analysis, including how many posts of a given type (flair) are present  

## Requirements
* Python 3.6+
* PostgreSQL (can support other databases with minor tweaks)
* (Optionally) Docker and docker-compose

## Non-Docker Setup
* Copy `template.env` to `src/.env` and update values.
* Install Python packages in `requirements.txt`
* Change to the `src` directory and execute the file for the feature you want, e.g. `python3 new_posts.py` 

## Docker Setup
* Copy and update `docker-compose.sample.yml` as appropriate. Set environment variables for config or use .env files as above.
* Start the database and build the tools container: `docker-compose up db tools`
* Run database update scripts (see `tools/README.md`)
* Start up other services: `docker-compose up mod_log new_posts new_comments sub_mentions`

## Front Page
* Configure `crontab` or other way of scheduling to run `frontpage.py` once per hour, e.g.
 * `0 * * * * cd /opt/r-anime/modbot/src/; /opt/r-anime/modbot/.venv/bin/python3 /opt/r-anime/modbot/src/frontpage.py`
* For Docker, run it via the tools container:
 * `0 * * * * cd /opt/r-anime/modbot/; docker-compose run tools python3 src/frontpage.py`
