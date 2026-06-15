# Shared state for modular routes
from flask import Blueprint
import threading

invoices_blueprint = Blueprint("invoices", __name__)

DOWNLOAD_TASKS = {}
DOWNLOAD_TASKS_LOCK = threading.Lock()
