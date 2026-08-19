from flask import Flask, request, g
import logging
import time

import config_loader

from controllers.ping import ping_bp
from controllers.db_ingestion import db_ingestion_bp
from utils.logger import logger

app = Flask(__name__)


# Filter out only Werkzeug's request log lines, but keep startup warnings
class SuppressWerkzeugRequests(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # Block lines that look like HTTP requests (e.g., "GET /...", "POST /...")
        return not any(
            method in msg for method in ('"GET ', '"POST ', '"PUT ', '"DELETE ', '"PATCH ', '"OPTIONS ', '"HEAD ')
        )


werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.addFilter(SuppressWerkzeugRequests())

for logger_name in ("werkzeug", "gunicorn.error"):
    logging.getLogger(logger_name).handlers = logger.handlers

# Explicitly silence gunicorn's access logger
gunicorn_access = logging.getLogger("gunicorn.access")
gunicorn_access.handlers = []
gunicorn_access.propagate = False

app.register_blueprint(ping_bp)
app.register_blueprint(db_ingestion_bp)


@app.before_request
def start_request_timer():
    g.start_time = time.perf_counter()


@app.after_request
def log_request_info(response):
    if request.path == "/favicon.ico":
        return response

    elapsed_ms = (time.perf_counter() - g.get("start_time", time.perf_counter())) * 1000
    owner = g.get("auth_owner", "Public")
    scope = g.get("auth_scope", "N/A")

    path_with_query = request.path
    if request.query_string:
        path_with_query = f"{request.path}?{request.query_string.decode('utf-8')}"

    timestamp_str = time.strftime("%d/%b/%Y %H:%M:%S", time.localtime())
    protocol = request.environ.get("SERVER_PROTOCOL", "HTTP/1.1")
    status_code = response.status_code

    if 100 <= status_code < 200:
        color = "\033[1m"  # Bold
    elif status_code == 200:
        color = ""  # No color for 200 Success
    elif status_code == 304:
        color = "\033[36m"  # Cyan
    elif 300 <= status_code < 400:
        color = "\033[32m"  # Green
    elif status_code == 404:
        color = "\033[33m"  # Yellow
    elif 400 <= status_code < 500:
        color = "\033[1;31m"  # Bold Red
    else:
        color = "\033[1;35m"  # Bold Magenta

    reset = "\033[0m" if color else ""

    logger.info(
        f"{request.remote_addr} - - [{timestamp_str}] "
        f'[{owner}@{scope}] "{color}{request.method} {path_with_query} {protocol}{reset}" '
        f"{response.status_code} "
        f"({elapsed_ms:.2f}ms)"
    )

    return response


@app.route("/")
def home():
    return "Modbot webserver"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config_loader.WEB_SERVER["port"], debug=config_loader.WEB_SERVER["debug"])
