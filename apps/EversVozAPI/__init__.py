from flask import Blueprint

eversvoz_bp = Blueprint('eversvoz_bp', __name__)

from apps.EversVozAPI import routes