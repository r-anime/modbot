from flask import Blueprint

ingestion_bp = Blueprint("ingestion", __name__, url_prefix="/ingestion")


@ingestion_bp.route("/post", methods=["POST"])
def post():
    return "TODO post"


@ingestion_bp.route("/comment", methods=["POST"])
def comment():
    return "TODO comment"


@ingestion_bp.route("/mod_log", methods=["POST"])
def mod_log():
    return "TODO mod_log"


@ingestion_bp.route("/report", methods=["POST"])
def report():
    return "TODO report"


@ingestion_bp.route("/edit", methods=["POST"])
def edit():
    return "TODO edit"
