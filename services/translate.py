import openai
from flask import jsonify

def translate_to_english(input_text):
  prompt = f"""
    Translate this Spanish word or phrase to English. 
    Respond with ONLY the English translation - no additional words or explanations.
    Do not include quotes, periods, or any other punctuation.
    Example input: casa
    Example output: house

    Text: {input_text}
  """

  try:
    response = openai.ChatCompletion.create(
      model="gpt-4o-mini",
      messages=[{"role": "system", "content": prompt}],
      max_tokens=300,
      temperature=0.2
    )
    translation = response['choices'][0]['message']['content'].strip()
    return jsonify({'translation': translation})
  except Exception as e:
    return jsonify({'error': str(e)}), 500
