"""Modular routes package.

Exposes backward-compatible symbols by delegating to invoices.routes_old during Phase 1.
"""

from invoices.routes_old import (
    invoices_blueprint,
    render_html_to_pdf,
    DOWNLOAD_TASKS,
)

__all__ = [
    "invoices_blueprint",
    "render_html_to_pdf",
    "DOWNLOAD_TASKS",
]
