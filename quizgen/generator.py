import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_quiz(study_material, format, num):
    prompt = f"""
You are Drilr — an AI study assistant that turns raw study materials into interactive quiz questions.

Study Material:
{study_material}

Format: {format}
Number of Questions: {num}

Rules:
- Focus on core ideas, terms, and concepts.
- For multiple choice: include 1 correct answer + 3 high-quality distractors.
- For fill-in-the-blank: remove one key term or phrase from a sentence.
- For free response: open-ended, concept-based questions only.
- Return everything in valid JSON format.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message["content"]
