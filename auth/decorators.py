"""Authentication and Role-Based Access Control decorators."""

from __future__ import annotations
from functools import wraps
from flask import session, jsonify


def roles_required(*roles: str):
    """Decorator to enforce that the logged-in user has one of the required roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("logged_in"):
                return jsonify({"error": "Phien dang nhap da het han. Vui long dang nhap lai."}), 401
            
            # Default to viewer role if not set
            user_role = session.get("user_role", "viewer")
            if user_role not in roles:
                return jsonify({
                    "error": f"Quyen truy cap bi tu choi. Yeu cau vai tro: {', '.join(roles)}."
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
