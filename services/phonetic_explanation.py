import openai
from flask import jsonify

def phonetic_explanation(input_text):
  prompt = f"""
    Eres un asistente de transcripción fonética. Convierte el siguiente texto en inglés en una transcripción fonética que imite la pronunciación del inglés pero sea fácil de leer y pronunciar para hablantes nativos de español.

    - Usa fonética simplificada que coincida con la pronunciación en español.
    - Puedes dar una explicación a cada palabra?
    - Evita símbolos IPA y utiliza combinaciones de letras familiares para los hablantes de español.
    - Proporciona una explicación para cada palabra indicando cómo debe sonar según el español.
    - Evita incluir prefijos como "Claro!" o "Aquí está la transcripción."


    Ejemplo:
    "My" (mai)
    - Suena como "mai". La "m" es igual a la del español, y la "y" suena como un diptongo "ai", similar al sonido de "hay" en inglés.
    
    "Day" (dei)
    - Suena como "dei". La "d" es suave, similar a cómo se pronuncia en "dedo" en español, y la "ay" tiene el sonido de "ei", como en la palabra inglesa "hey".
    
    "Is" (is)
    - Suena como "is". La "i" es corta y tensa, similar al sonido de la "i" en "mis" en español, pero más breve, y la "s" es como la de "sopa".
    
    "Going" (gouin)
    - Se pronuncia "gouin". La "g" es como en "gato", la "o" suena como una "ou" (como en "ou" de "ouch"), y "ing" suena como "in", pero con la lengua relajada al final.
    
    "Very" (veri)
    - Se pronuncia "veri". La "v" se parece a una mezcla entre "v" y "b" en español, pero más cercana a la "v". La "e" es como en "mesa", y la "r" es suave, como en "pero".
    
    "Well" (uel)
    - Se pronuncia "uel". La "w" suena como un leve "u" (como en "huevo"), la "e" es corta y clara, y la "ll" es como la "l" de "luz".
    
    "Today" (tudei)
    - Se pronuncia "tudei". La "t" es fuerte, como en "tapa", la "u" suena como la "u" en español, y "day" es igual a "dei" como en "day" explicado arriba.

    Texto: {input_text}
  """

  try:
    response = openai.ChatCompletion.create(
      model="gpt-4o-mini",
      messages=[{"role": "system", "content": prompt}],
      max_tokens=300,
      temperature=0.2
    )
    json_response = response['choices'][0]['message']['content'].strip()
    return jsonify({'phonetic_explanation': json_response})
  except Exception as e:
    return jsonify({'error': str(e)}), 500