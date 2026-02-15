from google import genai
from django.conf import settings
import json

client = genai.Client(api_key=settings.GEMINI_API_KEY)

def evaluate_answer(question, answer):
    prompt = f"""
    You are a professional technical interviewer.

    Question:
    {question}

    Candidate Answer:
    {answer}

    Respond ONLY in valid JSON format like this:

    {{
        "score": number_between_1_and_10,
        "feedback": "detailed feedback in 3-4 lines"
    }}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    try:
        result = json.loads(response.text)
        return result
    except:
        # fallback if model returns extra text
        return {
            "score": 5,
            "feedback": response.text
        }