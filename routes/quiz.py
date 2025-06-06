from flask import Blueprint, request, jsonify
from quizgen.generator import generate_quiz
import os
import pdfplumber
import docx

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
