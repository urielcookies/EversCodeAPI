from flask import Blueprint

everspass_bp = Blueprint('everspass', __name__, url_prefix='/everspass')

# Import routes *after* blueprint is created to avoid circular import
from apps.EversPass import routes
