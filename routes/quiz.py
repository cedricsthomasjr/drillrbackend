from flask import Blueprint, request, jsonify
from quizgen.generator import generate_quiz
import os
import pdfplumber
import docx
from quizgen.generator import extract_topics_and_definitions  # ← make sure this exists
from flask import Blueprint, request, jsonify

quiz_bp = Blueprint("quiz", __name__)

@quiz_bp.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    content = data.get("study_material")
    format = data.get("format", "multiple choice")
    num = data.get("num", 5)

    quiz = generate_quiz(content, format, num)
    return jsonify(quiz)
@quiz_bp.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            text = "\n".join(page.extract_text() or '' for page in pdf.pages)
    elif filename.endswith(".docx"):
        doc = docx.Document(file)
        text = "\n".join([para.text for para in doc.paragraphs])
    else:
        text = file.read().decode("utf-8")

    return jsonify({"text": text.strip()})


@quiz_bp.route("/summarize", methods=["POST"])
def summarize():
    data = request.get_json()
    content = data.get("study_material")

    if not content:
        return jsonify({"error": "Missing study_material"}), 400

    topics = extract_topics_and_definitions(content)
    return jsonify(topics)
@quiz_bp.route("/flow/process", methods=["POST"])
def flow_process():
    data = request.get_json()
    content = data.get("study_material")

    if not content:
        return jsonify({"error": "Missing study_material"}), 400

    chunks = [para.strip() for para in content.split("\n") if para.strip()]
    topics = extract_topics_and_definitions(content)

    return jsonify({ "chunks": chunks, "topics": topics })

import openai
import json

@quiz_bp.route("/grade-free-response", methods=["POST"])
def grade_free_response():
    data = request.get_json()
    question = data.get("question")
    user_answer = data.get("user_answer")
    correct_answer = data.get("correct_answer")

    if not all([question, user_answer, correct_answer]):
        return jsonify({"error": "Missing fields"}), 400

    prompt = f"""
You are grading a student's free response answer to a quiz question.

Return ONLY a JSON object in this format:
{{
  "score": decimal from 0.0 to 1.0 (in 0.1 increments),
  "feedback": "brief feedback (1–2 sentences)",
  "confidence": 0–100
}}

Be granular. Use:
- 1.0 for perfect answers,
- 0.9, 0.8, etc. for mostly correct but slightly off,
- 0.5 for halfway there,
- 0.1–0.4 for vague or weak responses,
- 0.0 for completely wrong.

Do not round to 0.5. Be precise.

Question: {question}
Correct Answer: {correct_answer}
User's Answer: {user_answer}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful grading assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )

        result_text = response.choices[0].message.content.strip()
        print("GPT RAW:", result_text)

        # Strip markdown if needed
        if "```json" in result_text:
            result_text = result_text.split("```json")[-1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[-1].strip()

        import json
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            result = {"score": 0, "feedback": "Invalid response.", "confidence": 0}

        return jsonify({
            "score": float(result.get("score", 0)),
            "feedback": result.get("feedback", "No feedback."),
            "confidence": result.get("confidence", 0)
        })

    except Exception as e:
        print("[GRADING ERROR]", e)
        return jsonify({"error": "Failed to grade"}), 500
