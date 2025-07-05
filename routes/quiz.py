from flask import Blueprint, request, jsonify
from quizgen.generator import generate_quiz
import os
import pdfplumber
import docx
from quizgen.generator import extract_topics_and_definitions  # ← make sure this exists
import openai
import json

quiz_bp = Blueprint("quiz", __name__)

@quiz_bp.route("/generate", methods=["POST"])
def generate():
    from difflib import SequenceMatcher

    def topic_in_para(topic, para):
        return SequenceMatcher(None, topic.lower(), para.lower()).ratio() > 0.5

    data = request.get_json()
    content = data.get("study_material", "")
    format = data.get("format", "multiple choice")
    num = data.get("num", 5)
    selected_topics = data.get("selected_topics", [])

    topic_chunks = {topic: [] for topic in selected_topics}
    paragraphs = content.split("\n\n")

    for para in paragraphs:
        for topic in selected_topics:
            if topic_in_para(topic, para):
                topic_chunks[topic].append(para)
                break

    questions = []
    q_number = 1

    for topic in selected_topics:
        topic_text = "\n\n".join(topic_chunks[topic])
        print(f"\n[DEBUG] Topic: {topic}")
        print(f"[DEBUG] Filtered Content (first 500 chars):\n{topic_text[:500]}\n")

        if not topic_text.strip():
            print(f"[WARN] No content found for topic: {topic}")
            continue

        topic_quiz = generate_quiz(topic_text, format, num)
        for q in topic_quiz.get("questions", []):
            q["topic"] = topic
            q["number"] = q_number
            questions.append(q)
            q_number += 1

    # Fallback if nothing matched
    if not questions:
        print("[WARN] No topic-specific content matched. Falling back to full document.")
        fallback_quiz = generate_quiz(content, format, num)
        for q in fallback_quiz.get("questions", []):
            q["topic"] = "General"
            q["number"] = q_number
            questions.append(q)
            q_number += 1

    return jsonify({
        "questions": questions,
        "summary": ", ".join(selected_topics)
    })

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

@quiz_bp.route("/grade-free-response", methods=["POST"])
def grade_free_response():
    data = request.get_json()
    question = data.get("question")
    user_answer = data.get("user_answer")
    correct_answer = data.get("correct_answer")

    if not all([question, user_answer, correct_answer]):
        return jsonify({"error": "Missing fields"}), 400

    try:
        response = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[
        {
  "role": "system",
  "content": (
    "You are a reasonable human teacher who grades free-response answers generously. "
    "If the student’s answer states the main idea clearly, never deduct points for not adding every example, historical influence, or minor technical detail. "
    "Only deduct if the missing information changes the student’s understanding of the core concept. "
    "Always respond ONLY in JSON."
  )
}
,
        {
            "role": "user",
            "content": f"""
Grade the following student's answer.

**Grading Scale**
- 1.0: Fully correct — the answer shows clear understanding and covers the main idea(s). Minor omissions, small missing examples, or slightly different wording **should NOT lower the score**.
- 0.9–0.8: Mostly correct — the answer is mostly right but misses an important piece of the explanation or shows minor confusion.
- 0.7–0.6: Partially correct — the gist is there, but multiple key points are missing or there is noticeable confusion.
- 0.5: Halfway — a good attempt but major pieces are missing or incorrect.
- 0.4–0.1: Mostly incorrect — some effort but misunderstood or guessed.
- 0.0: Completely incorrect or irrelevant.

**When in doubt, be generous.** If the answer explains the main point clearly, do not deduct points for not listing every variant or detail.

**Do NOT deduct for:**  
- Typos, grammar, or spelling mistakes  
- Slightly different wording or phrasing  
- Small facts that do not change the main meaning  
- Brief but clear answers that hit the core idea

**Do deduct for:**  
- Leaving out core parts of the answer  
- Including incorrect information that changes the meaning  
- Showing misunderstanding of the main concept

**Return only a JSON object exactly like this:**  
{{
  "score": decimal between 0.0 and 1.0 (0.1 steps),
  "feedback": "short human-style comment (1–2 sentences)",
  "confidence": integer between 0 and 100
}}

**Question:** {question}  
**Correct Answer:** {correct_answer}  
**User Answer:** {user_answer}
"""
        }
    ],
    temperature=0.2
)

        result_text = response.choices[0].message.content.strip()

        if "```json" in result_text:
            result_text = result_text.split("```json")[-1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[-1].strip()

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

@quiz_bp.route("/detect-topics", methods=["POST"])
def detect_topics():
    data = request.get_json()
    content = data.get("study_material")

    if not content:
        return jsonify({"error": "Missing study_material"}), 400

    prompt = f"""
You are a helpful assistant. Your task is to extract the *broadest possible* topic categories
from the following study material. Only list topics that are meaningfully distinct.

Guidelines:
- Return *only as many topics as truly necessary* (usually 3–6 for short study material).
- Do NOT always return 8.
- Combine similar or overlapping concepts under a single broader topic.
- Do NOT repeat or slightly reword similar topics.
- Do NOT list sources, tools, or specific books/articles — just conceptual categories.
- Return ONLY a valid JSON array of short strings. No explanation, no Markdown, no other text.

Example Output:
["Algorithms", "Computer Architecture", "Programming Paradigms"]

Study Material:

{content}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a topic detection assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )

        output = response.choices[0].message.content.strip()

        # Strip Markdown if needed
        if "```json" in output:
            output = output.split("```json")[-1].split("```")[0].strip()

        topics = json.loads(output)
        return jsonify({"topics": topics})
    except Exception as e:
        print("[TOPIC DETECTION ERROR]", e)
        return jsonify({"error": "Failed to detect topics."}), 500
