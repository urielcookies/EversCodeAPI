from flask import Blueprint

test_bp = Blueprint('test', __name__, url_prefix='/test')

# Import routes *after* blueprint is created to avoid circular import
from apps.Test import routes
