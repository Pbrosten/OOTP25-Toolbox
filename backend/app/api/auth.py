from functools import wraps

from flask import current_app, jsonify, request


def require_admin_token(view):
    """Guard a route behind the X-Admin-Token header, checked against
    current_app.config["ADMIN_API_TOKEN"]."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        expected_token = current_app.config.get("ADMIN_API_TOKEN")
        request_token = request.headers.get("X-Admin-Token")
        if not expected_token or request_token != expected_token:
            return jsonify({"error": "unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped_view
