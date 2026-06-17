"""Modular routes package.

Exposes backward-compatible symbols and registers all split submodules.
"""

from invoices.routes.shared import invoices_blueprint, DOWNLOAD_TASKS, DOWNLOAD_TASKS_LOCK

# Import sub-modules to register routes on the blueprint
from invoices.routes import core, reconciliation, ocr, compliance, mitigation, settings

# Expose helper function render_html_to_pdf
from invoices.routes.helpers import render_html_to_pdf

__all__ = [
    "invoices_blueprint",
    "render_html_to_pdf",
    "DOWNLOAD_TASKS",
    "DOWNLOAD_TASKS_LOCK",
]
