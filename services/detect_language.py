import openai
from flask import jsonify

def detect_language(input_text):
  prompt = f"""
    You are a language detection model. Analyze the following text and determine the primary language it is written in.

    - If the text is entirely in Spanish, respond: "The input is in Spanish."
    - If the text is entirely in English, respond: "The input is in English."
    - If the text contains a mix of Spanish and English or words from another language, respond: "unsupported."
    - If a word appears misspelled, evaluate its context and decide based on the rest of the text.

    Do not make any assumptions. Base your response solely on the input text provided below.

    Text: {input_text}
  """

  try:
    response = openai.ChatCompletion.create(
      model="gpt-4o-mini",
      messages=[{"role": "system", "content": prompt}],
      max_tokens=300,
      temperature=0.2
    )
    json_response = response['choices'][0]['message']['content'].strip().lower()
    if "spanish" in json_response:
      detected_language = "spanish"
    elif "english" in json_response:
      detected_language = "english"
    elif "unsupported" in json_response:
      detected_language = "unsupported"
    else:
      detected_language = "error"

    return jsonify({'detected_lang': detected_language})
  except Exception as e:
    return jsonify({'error': str(e)}), 500
