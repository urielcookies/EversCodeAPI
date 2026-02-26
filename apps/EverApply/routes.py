from flask import jsonify
from apps.EverApply import everapply_bp

@everapply_bp.route('/hello-world', methods=['GET'])
def hello_world():
    return jsonify({"message": "EverApply is live!"}), 200
