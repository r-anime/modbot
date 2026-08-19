from flask import Blueprint
from utils.api_auth import require_scope, Scope

db_ingestion_bp = Blueprint("db_ingestion", __name__, url_prefix="/db_ingestion")


@db_ingestion_bp.route("/post", methods=["POST"])
@require_scope(Scope.DB_INGEST)
def post():
    return "TODO post"


@db_ingestion_bp.route("/comment", methods=["POST"])
@require_scope(Scope.DB_INGEST)
def comment():
    return "TODO comment"


@db_ingestion_bp.route("/mod_log", methods=["POST"])
@require_scope(Scope.DB_INGEST)
def mod_log():
    return "TODO mod_log"


@db_ingestion_bp.route("/report", methods=["POST"])
@require_scope(Scope.DB_INGEST)
def report():
    return "TODO report"


@db_ingestion_bp.route("/edit", methods=["POST"])
@require_scope(Scope.DB_INGEST)
def edit():
    return "TODO edit"
