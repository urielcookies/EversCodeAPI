import openai
from flask import jsonify

def phonetic_transcription(input_text):
  prompt = f"""
    You are a phonetic transcription assistant. Convert the following English text into a phonetic transcription that mimics English pronunciation but is easier for Spanish speakers to pronounce.

    - Use simplified phonetics that match Spanish pronunciation.
    - Avoid IPA symbols and use combinations of letters that are familiar to Spanish speakers.
    - Do not include any prefixes like "Sure!" or "Here’s the transcription."

    Example:
    - "Hello" -> "Je-lo"
    - "Good morning" -> "Gud mor-ning"
    - "Cupcake" -> "Cap-keik"

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
    # Clean and extract the transcription
    if "->" in json_response:
      cleaned_transcription = json_response.split("->")[1].strip()
    else:
      cleaned_transcription = json_response

    return jsonify({'phonetic_transcription': cleaned_transcription})
  except Exception as e:
    return jsonify({'error': str(e)}), 500