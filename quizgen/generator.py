import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_quiz(study_material, format, num):
    prompt = f"""
You are Drilr — an AI study assistant that transforms study content into well-structured quiz questions.

Generate {num} quiz questions in the "{format}" format using the study material below.

Each question should follow this JSON structure:
{{
  "number": 1,
  "topic": "Photosynthesis",
  "question": "What process allows plants to convert sunlight into energy?",
  "options": ["Digestion", "Photosynthesis", "Respiration", "Fermentation"],  # Only for multiple choice
  "answer": "Photosynthesis"
}}

Study Material:
\"\"\"
{study_material}
\"\"\"

Rules:
- Return only a **JSON array** of objects with the fields: number, topic, question, options (if multiple choice), and answer.
- The topic should be a one-word or short-phrase summary of what the question is about.
- For multiple choice: include exactly 4 choices in "options", one of which is the correct answer.
- For fill-in-the-blank: omit "options" and structure the question with a blank.
- For free response: omit "options", and write an open-ended conceptual question.
- Do NOT include any explanations, markdown, or commentary — only the JSON array.
- Ensure the JSON is valid and parseable.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message["content"]
