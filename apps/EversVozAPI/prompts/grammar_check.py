import openai
from flask import jsonify

def grammar_check(input_text):
    prompt = f"""
        You are a grammar and spelling-checking assistant. Analyze the following text for grammatical and spelling correctness.

        - If the text is in English and contains grammatical or spelling errors, provide the corrected version of the text only. Do not include any additional text or explanations.
        - If the text is already correct, respond: "The text is grammatically correct."
        - If there are numbers convert them into words. Ex 157 -> one hundred and fifty seven

        Text: {input_text}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=300,
            temperature=0.2
        )
        json_response = response['choices'][0]['message']['content'].strip()

        # If the text is grammatically correct, return the original text, else return the corrected text
        if json_response == "The text is grammatically correct.":
            return jsonify({'grammar_check': input_text})
        else:
            return jsonify({'grammar_check': json_response})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
