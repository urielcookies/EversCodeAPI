from flask import Blueprint

everapply_bp = Blueprint('everapply', __name__, url_prefix='/everapply')

# Import routes *after* blueprint is created to avoid circular import
from apps.EverApply import routes
