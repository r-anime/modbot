import os
from flask import Flask

import config_loader

from controllers.ping import ping_bp
from controllers.ingestion import ingestion_bp

app = Flask(__name__)

app.register_blueprint(ping_bp)
app.register_blueprint(ingestion_bp)


@app.route('/')
def home():
    return "Modbot webserver"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config_loader.WEB_SERVER["port"], debug=config_loader.WEB_SERVER["debug"])
