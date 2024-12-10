import openai
from flask import jsonify

def grammar_check(input_text):
  prompt = f"""
    You are a grammar and spelling-checking assistant. Analyze the following text for grammatical and spelling correctness.

    - If the text is in English and contains grammatical or spelling errors, provide the corrected version of the text only. Do not include any additional text or explanations.
    - If the text is already correct, respond: "The text is grammatically correct."
    - If the text is not in English, respond: "Grammar check not required as the text is not in English."

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

    if json_response == "The text is grammatically correct.":
      corrected_text = input_text
    else:
      corrected_text = json_response

    return jsonify({'grammar_check': corrected_text})
  except Exception as e:
    return jsonify({'error': str(e)}), 500