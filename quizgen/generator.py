import openai
import os
import json
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_quiz(study_material, format, num):
    format = format.lower()

    if format == "multiple choice":
        format_rules = """
- Each question must have exactly 4 answer choices: 1 correct answer and 3 well-reasoned distractors.
- Include all options in an "options" array.
- Only one correct answer allowed per question.
- Distractors must be plausible and not obviously wrong.
- Add an "explanation" field that briefly justifies why the answer is correct, using only the provided material.
"""
    elif format == "fill in the blank":
        format_rules = """
- Remove exactly one **key** word or phrase from a meaningful sentence in the material.
- Do not include multiple blanks or vague removals.
- Do NOT include an "options" field.
- The "answer" field must contain the exact removed word or phrase.
- Add an "explanation" field that briefly explains why the missing word or phrase is correct, using only the study material.
"""
    elif format == "free response":
        format_rules = """
- Questions must be clear, open-ended, and based directly on the provided content.
- Do NOT include an "options" field.
- The "answer" must be a concise, factual response directly supported by the material.
- Add an "explanation" field that clearly supports the answer using only information from the material.
"""
    else:
        raise ValueError("Invalid format. Choose 'multiple choice', 'fill in the blank', or 'free response'.")

    prompt = f"""
You are Drilr — an AI quiz generator. Your task is to extract high-quality quiz questions **strictly from the study material below**.

1. Start by identifying the main academic topics in the material. These should be broad categories, not specific terms (e.g., "Photosynthesis", "Economic Policy", "Human Anatomy").

2. Then generate {num} quiz questions in the "{format}" format, following all rules below.

📌 IMPORTANT:
- Use only the information explicitly provided in the study material.
- Do NOT invent facts or use external knowledge.
- Output must be valid JSON. No markdown, headings, or extra commentary.

Output Format:
{{
  "summary": "Comma-separated list of general topics from the material",
  "questions": [
    {{
      "number": 1,
      "topic": "General topic or keyword",
      "question": "The question itself",
      {"\"options\": [\"A\", \"B\", \"C\", \"D\"]," if format == "multiple choice" else ""}
      "answer": "Correct answer based on the study material",
      "explanation": "Brief justification based only on the material"
    }},
    ...
  ]
}}

Study Material:
\"\"\"
{study_material}
\"\"\"

Rules for this format:
{format_rules}
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1800,
    )

    try:
        parsed = json.loads(response.choices[0].message["content"])
        return {
            "summary": parsed.get("summary", ""),
            "questions": parsed.get("questions", [])
        }
    except json.JSONDecodeError as e:
        print("❌ Invalid JSON from OpenAI:", e)
        print("Raw output:\n", response.choices[0].message["content"])
        raise

openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_topics_and_definitions(content: str):
    system_prompt = (
        "You're a study assistant. Extract all overarching key academic concepts from the provided study material."
        "For each, return a JSON object with fields: topic, definition, summary. "
        "Use simple, accurate language for high school and college-level learners."
    )

    user_prompt = f"Text:\n{content.strip()}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        result = response.choices[0].message.content.strip()

        if "```json" in result:
            result = result.split("```json")[-1].split("```")[0].strip()

        return json.loads(result)

    except Exception as e:
        print("[ERROR] Failed to extract topics:", e)
        return []
    
    