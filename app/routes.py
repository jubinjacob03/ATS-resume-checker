import os
import re
import spacy
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from docx import Document
from transformers import pipeline

def create_app():
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = 'uploads'
    return app

app = create_app()
nlp = spacy.load('en_core_web_sm')
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", revision="a4f8f3e")

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def check_formatting(text):
    formatting_issues = []
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "DATE" and re.search(r"\d{2,}/\d{2,}/\d{2,4}", ent.text):
            formatting_issues.append(f"Avoid using exact dates like {ent.text}, use months and years instead.")
    return formatting_issues

def check_sections(text):
    required_sections = ["experience", "education", "skills"]
    missing_sections = []
    doc = nlp(text.lower())
    for section in required_sections:
        if section not in [token.text for token in doc]:
            missing_sections.append(section)
    return missing_sections

def check_keywords(text, keywords):
    found_keywords = []
    doc = nlp(text.lower())
    for keyword in keywords:
        if keyword.lower() in [token.text for token in doc]:
            found_keywords.append(keyword)
    return found_keywords

def ats_check(file_path, keywords):
    if file_path.endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        text = extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format")

    # Summarize the text to extract the main points
    summarized_text = summarizer(text, max_length=150, min_length=30, do_sample=False)[0]['summary_text']

    formatting_issues = check_formatting(summarized_text)
    missing_sections = check_sections(summarized_text)
    found_keywords = check_keywords(summarized_text, keywords)

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
            # Ensure the upload folder exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            keywords = request.form['keywords'].split(',')
            result = ats_check(file_path, keywords)

            os.remove(file_path)  # Clean up the uploaded file

            return render_template('results.html', result=result)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
