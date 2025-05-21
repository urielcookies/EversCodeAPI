from flask import Flask
from apps.Test import test_bp
from apps.EversVozAPI import eversvoz_bp

app = Flask(__name__)

app.register_blueprint(test_bp)
app.register_blueprint(eversvoz_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)