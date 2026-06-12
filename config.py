"""Application configuration for the invoice download webapp."""

from __future__ import annotations

import os
from datetime import timedelta


class Config:
    """Central Flask configuration loaded from environment variables."""

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_REFRESH_EACH_REQUEST = True
    GDT_BASE_URL = os.getenv("GDT_BASE_URL", "https://hoadondientu.gdt.gov.vn")
    GDT_USE_MOCK = os.getenv("GDT_USE_MOCK", "true").lower() == "true"
    GDT_TIMEOUT_SECONDS = int(os.getenv("GDT_TIMEOUT_SECONDS", "30"))
    AUTO_SOLVE_CAPTCHA = os.getenv("AUTO_SOLVE_CAPTCHA", "true").lower() == "true"
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        f"sqlite:///{os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'invoices.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BASE_DATA_DIR = os.getenv(
        "BASE_DATA_DIR",
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
    )



