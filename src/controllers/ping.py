from flask import Blueprint
from utils.api_auth import require_scope, Scope

ping_bp = Blueprint("ping", __name__, url_prefix="/ping")


@ping_bp.route("/")
def ping():
    return "pong"


def _register_ping_route(scope_enum):
    @ping_bp.route(f"/{scope_enum.value}", endpoint=f"ping_{scope_enum.value}")
    @require_scope(scope_enum)
    def ping():
        return f"pong {scope_enum.value} (successful auth)\n"


# Dynamically generate a route for every scope in the Enum
for scope in Scope:
    _register_ping_route(scope)
