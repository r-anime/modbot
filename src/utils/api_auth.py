import os
from enum import Enum
from functools import wraps
from flask import request, jsonify, g

from utils import discord
from utils.logger import logger


class Scope(Enum):
    ALL = "all"
    DB_INGEST = "db_ingest"
    READ_DATA = "read_data"

    @classmethod
    def parse_string(cls, scopes_string: str, owner: str = "Unknown") -> set:
        parsed_scopes = set()
        invalid_scopes = []

        for s in scopes_string.split(","):
            cleaned = s.strip()
            if not cleaned:
                continue
            try:
                parsed_scopes.add(cls(cleaned))
            except ValueError:
                invalid_scopes.append(cleaned)

        if invalid_scopes:
            invalid_list_str = ", ".join(f"'{scope}'" for scope in invalid_scopes)
            error_msg = f"Unknown API scope(s) [{invalid_list_str}] found in environment for {owner}"
            logger.warning(error_msg)
            discord.add_urgent_message(error_msg)

        return parsed_scopes


def _load_api_auth_tokens():
    clients = {}
    for key, val in os.environ.items():
        if key.startswith("WEB_SERVER_API_AUTH_") and val.count("|") == 2:
            owner, scopes_str, token = val.split("|")
            parsed_scopes = Scope.parse_string(scopes_str, owner=owner)
            clients[token] = {"owner": owner, "scopes": parsed_scopes, "has_all_scope": Scope.ALL in parsed_scopes}

    discord.flush_urgent_messages()
    return clients


_API_AUTH_TOKENS = _load_api_auth_tokens()


def require_scope(required_scope):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "Missing or invalid token format"}), 401

            token = auth_header.split(" ")[1]
            g.auth_owner = f"'{token}'"

            client_data = _API_AUTH_TOKENS.get(token)

            if not client_data:
                return jsonify({"error": "Unauthorized"}), 401

            if client_data["has_all_scope"]:
                g.auth_scope = Scope.ALL.value
            elif required_scope in client_data["scopes"]:
                g.auth_scope = required_scope.value
            else:
                return jsonify({"error": f"Forbidden: Requires {required_scope.value} scope"}), 403

            g.auth_owner = client_data["owner"]

            return f(*args, **kwargs)

        return decorated_function

    return decorator
