from flask import Blueprint

ping_bp = Blueprint("ping", __name__, url_prefix="/ping")


@ping_bp.route("/")
def ping():
    return "pong"
