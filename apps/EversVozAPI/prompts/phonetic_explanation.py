from flask import jsonify
from apps.EversVozAPI.utils.kimi_client import kimi_client

def phonetic_explanation(input_text):
    prompt = f"""
        Eres un asistente de transcripción fonética. Convierte el siguiente texto en inglés en una transcripción fonética que imite la pronunciación del inglés pero sea fácil de leer y pronunciar para hablantes nativos de español.

        - Usa fonética simplificada que coincida con la pronunciación en español.
        - Evita símbolos IPA y utiliza combinaciones de letras familiares para los hablantes de español.
        - Use guiones entre palabras si eso ayuda a dividir la palabra para una pronunciación más fácil, "morning" -> "mor-ning".
        - Explicar cómo se pronuncia usando referencias al español
        - Proporciona una explicación para cada palabra indicando cómo debe sonar según el español.
        - Evita incluir prefijos como "Claro!" o "Aquí está la transcripción."
        - NO agregar resúmenes ni conclusiones al final

        La respuesta debe ser únicamente la transcripción fonética y la explicación de las palabras en el texto proporcionado, sin agregar palabras adicionales ni cambiar el formato estrictamente definido.
        La respuesta debe seguir ESTRICTAMENTE este formato para cada palabra:

        Ejemplo:
        "My" (mai)
        - La "m" es igual a la del español, y la "y" suena como un diptongo "ai", similar al sonido de "hay" en inglés.
        
        "Day" (dei)
        - La "d" es suave, similar a cómo se pronuncia en "dedo" en español, y la "ay" tiene el sonido de "ei", como en la palabra inglesa "hey".
        
        "Is" (is)
        - La "i" es corta y tensa, similar al sonido de la "i" en "mis" en español, pero más breve, y la "s" es como la de "sopa".
        
        "Going" (gouin)
        - La "g" es como en "gato", la "o" suena como una "ou" (como en "ou" de "ouch"), y "ing" suena como "in", pero con la lengua relajada al final.
        
        "Very" (veri)
        - "veri". La "v" se parece a una mezcla entre "v" y "b" en español, pero más cercana a la "v". La "e" es como en "mesa", y la "r" es suave, como en "pero".
        
        "Well" (uel)
        - "uel". La "w" suena como un leve "u" (como en "huevo"), la "e" es corta y clara, y la "ll" es como la "l" de "luz".
        
        "Today" (tudei)
        - "tudei". La "t" es fuerte, como en "tapa", la "u" suena como la "u" en español, y "day" es igual a "dei" como en "day" explicado arriba.

        Texto: {input_text} (solo transcribe las palabras proporcionadas, nada más).
    """

    try:
        response = kimi_client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=1000,
            temperature=0.2
        )
        json_response = response.choices[0].message.content.strip()
        return jsonify({'phonetic_explanation': json_response}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
