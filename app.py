from flask import Flask
from apps.Test import test_bp
from apps.EversVozAPI import eversvoz_bp
from apps.PortfolioForm import portfoliocontactform_bp
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.register_blueprint(test_bp)
app.register_blueprint(eversvoz_bp)
app.register_blueprint(portfoliocontactform_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)