import os
from flask import Flask
from flask_cors import CORS
from apps.Test import test_bp
from apps.EversVozAPI import eversvoz_bp
from apps.PortfolioForm import portfoliocontactform_bp
from apps.EversPass import everspass_bp
from apps.EverApply import everapply_bp

app = Flask(__name__)

app.url_map.strict_slashes = False
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
CORS(app, origins=allowed_origins, supports_credentials=True)

app.register_blueprint(test_bp)
app.register_blueprint(eversvoz_bp)
app.register_blueprint(portfoliocontactform_bp)
app.register_blueprint(everspass_bp)
app.register_blueprint(everapply_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
