from flask import Flask
import logging

import config_loader

from controllers.ping import ping_bp
from controllers.ingestion import ingestion_bp
from utils.logger import logger

app = Flask(__name__)

for logger_name in ("werkzeug", "gunicorn.error", "gunicorn.access"):
    logging.getLogger(logger_name).handlers = logger.handlers

app.register_blueprint(ping_bp)
app.register_blueprint(ingestion_bp)


@app.route("/")
def home():
    return "Modbot webserver"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config_loader.WEB_SERVER["port"], debug=config_loader.WEB_SERVER["debug"])
