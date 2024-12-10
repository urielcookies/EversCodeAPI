import openai
from flask import jsonify

def translate_to_english(input_text):
  prompt = f"""
    You are a translation model. Translate the following text into English only if it is in Spanish.

    If the text is in Spanish, provide the English translation.
    If the text is not in Spanish, respond: "Translation not required as the text is not in Spanish."

    Text: {input_text}
  """

  try:
    response = openai.ChatCompletion.create(
      model="gpt-4o-mini",
      messages=[{"role": "system", "content": prompt}],
      max_tokens=300,
      temperature=0.2
    )
    json_response = response['choices'][0]['message']['content'].strip()
    return jsonify({'translation': json_response})
  except Exception as e:
    return jsonify({'error': str(e)}), 500