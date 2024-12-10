# utils/auth.py
from functools import wraps
from flask import request, jsonify
import os

def require_transcribe_api_key(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    api_key = request.headers.get('transcribe-api-key')
    if api_key and api_key == os.getenv("TRANSCRIBE_API_KEY"):
      return f(*args, **kwargs)
    else:
      return jsonify({"error": "Unauthorized"}), 401
  return decorated_function
