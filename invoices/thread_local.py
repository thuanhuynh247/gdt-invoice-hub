"""Thread-local context helper to maintain multitenancy variables in background worker pools."""

from __future__ import annotations
import threading

_thread_local = threading.local()

def set_current_thread_mst(mst: str | None) -> None:
    """Set the taxpayer MST for the active thread."""
    _thread_local.current_mst = mst

def get_current_thread_mst() -> str | None:
    """Retrieve the taxpayer MST for the active thread."""
    return getattr(_thread_local, "current_mst", None)

def set_current_thread_credentials(username: str | None, password_encrypted: str | None, jwt: str | None = None) -> None:
    """Set GDT credentials and JWT session token for the active thread."""
    _thread_local.username = username
    _thread_local.password_encrypted = password_encrypted
    _thread_local.jwt = jwt

def get_current_thread_credentials() -> tuple[str | None, str | None, str | None]:
    """Retrieve GDT credentials and JWT session token for the active thread."""
    username = getattr(_thread_local, "username", None)
    password_encrypted = getattr(_thread_local, "password_encrypted", None)
    jwt = getattr(_thread_local, "jwt", None)
    return username, password_encrypted, jwt

def set_current_thread_jwt(jwt: str | None) -> None:
    """Set the GDT JWT token for the active thread."""
    _thread_local.jwt = jwt

def set_current_thread_lookup(lookup: dict | None) -> None:
    """Set the GDT invoice lookup dictionary for the active thread."""
    _thread_local.lookup = lookup

def get_current_thread_lookup() -> dict | None:
    """Retrieve the GDT invoice lookup dictionary for the active thread."""
    return getattr(_thread_local, "lookup", None)

def clear_thread_local_context() -> None:
    """Clear all thread-local state variables."""
    if hasattr(_thread_local, "current_mst"):
        del _thread_local.current_mst
    if hasattr(_thread_local, "username"):
        del _thread_local.username
    if hasattr(_thread_local, "password_encrypted"):
        del _thread_local.password_encrypted
    if hasattr(_thread_local, "jwt"):
        del _thread_local.jwt
    if hasattr(_thread_local, "lookup"):
        del _thread_local.lookup
