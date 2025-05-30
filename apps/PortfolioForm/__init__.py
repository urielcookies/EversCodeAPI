from flask import Blueprint

portfoliocontactform_bp = Blueprint('portfoliocontactform', __name__, url_prefix='/portfoliocontactform')

# Import routes *after* blueprint is created to avoid circular import
from apps.PortfolioForm import routes
