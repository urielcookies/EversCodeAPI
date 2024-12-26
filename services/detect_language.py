import openai
from flask import jsonify

def detect_language(input_text):
  prompt = f"""
    Analyze this text and respond with exactly one word:
    - "spanish" if the text is in Spanish
    - "english" if the text is in English
    - "unsupported" if the text is in another language or mixes languages

    Text: {input_text}
  """

  try:
    response = openai.ChatCompletion.create(
      model="gpt-4o-mini",
      messages=[{"role": "system", "content": prompt}],
      max_tokens=50,  # Reduced since we only need one word
      temperature=0.2
    )
    detected_language = response['choices'][0]['message']['content'].strip().lower()
    
    # Only accept the three valid responses
    if detected_language not in ["spanish", "english", "unsupported"]:
      detected_language = "error"
        
    return jsonify({'detected_lang': detected_language})
  except Exception as e:
    return jsonify({'error': str(e)}), 500
