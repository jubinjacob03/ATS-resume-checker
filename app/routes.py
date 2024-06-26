from flask import request, render_template, jsonify
from werkzeug.utils import secure_filename
import os
import spacy
import re
from docx import Document
from . import create_app

app = create_app()

nlp = spacy.load("en_core_web_sm")

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_pdf(file_path):
    import fitz  # PyMuPDF
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def check_formatting(text):
    formatting_issues = []
    if re.search(r"\d{2,}/\d{2,}/\d{2,4}", text):
        formatting_issues.append("Avoid using exact dates, use months and years instead.")
    return formatting_issues

def check_sections(text):
    required_sections = ["experience", "education", "skills"]
    missing_sections = [section for section in required_sections if section not in text.lower()]
    return missing_sections

def check_keywords(text, keywords):
    doc = nlp(text)
    found_keywords = [keyword for keyword in keywords if any(keyword.lower() in token.text.lower() for token in doc)]
    return found_keywords

def ats_check(file_path, keywords):
    if file_path.endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        text = extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format")

    formatting_issues = check_formatting(text)
    missing_sections = check_sections(text)
    found_keywords = check_keywords(text, keywords)

    score = len(found_keywords) / len(keywords) * 100

    return {
        "formatting_issues": formatting_issues,
        "missing_sections": missing_sections,
        "found_keywords": found_keywords,
        "score": score
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'resume' not in request.files:
            return "No file part"
        file = request.files['resume']
        if file.filename == '':
            return "No selected file"
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join('uploads', filename)
            file.save(file_path)

            keywords = request.form['keywords'].split(',')
            result = ats_check(file_path, keywords)

            os.remove(file_path)  # Clean up the uploaded file

            return render_template('results.html', result=result)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
