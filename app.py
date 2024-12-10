import os
from flask import Flask, request, jsonify
import json
import openai
from services.detect_language import detect_language
from services.translate import translate_to_english
from services.grammar_check import grammar_check
from services.phonetic_transcription import phonetic_transcription
from utils.auth import require_transcribe_api_key 

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")
MAX_LENGTH = 250

@app.route('/transcribe', methods=['POST'])
@require_transcribe_api_key
def transcribe():
  data = request.json

  if not data or 'text' not in data or 'lang' not in data:
    return jsonify({"error": "Please provide 'text' and 'lang' in the request body"}), 400

  client_lang = data["lang"]
  input_text = data["text"]

  if not input_text or len(input_text) > MAX_LENGTH:
    return jsonify({"error": f"Text length exceeds {MAX_LENGTH} characters or is empty"}), 400

  if client_lang not in ['es', 'en']:
    return jsonify({"error": "Invalid value for 'lang'. Allowed values are 'es' or 'en'"}), 400

  detected_lang_response = detect_language(input_text)
  detected_lang_data = json.loads(detected_lang_response.get_data(as_text=True))
  detected_lang = detected_lang_data.get("detected_lang", "")

  if detected_lang == 'unsupported':
    return jsonify({"error": "Language Needs to be in English or Spanish"}), 400

  english_phrase = ''
  if detected_lang == 'english':
    grammar_check_response = grammar_check(input_text)
    grammar_check_data = json.loads(grammar_check_response.get_data(as_text=True))
    english_phrase = grammar_check_data.get("grammar_check", "")
  elif detected_lang == 'spanish':
    translate_response = translate_to_english(input_text)
    translate_data = json.loads(translate_response.get_data(as_text=True))
    english_phrase = translate_data.get("translation", "")

  phonetic_response = phonetic_transcription(english_phrase)
  phonetic_data = json.loads(phonetic_response.get_data(as_text=True))

  response_data = {
    "detected_lang": detected_lang,
    "english_phrase": english_phrase,
    "phonetic_transcription": phonetic_data.get("phonetic_transcription", "")
  }

  return app.response_class(
    json.dumps(response_data, ensure_ascii=False),
    mimetype='application/json'
  )

if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=5001)
