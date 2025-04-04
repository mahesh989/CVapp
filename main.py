
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import shutil
import os
from docx import Document
from dotenv import load_dotenv
from uuid import uuid4
from ai_matcher import analyze_match_fit, generate_tailored_cv_text_with_keywords
from cv_parser import extract_text_from_pdf, extract_text_from_docx
from job_scraper import scrape_job_description

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
TAILORED_DIR = "tailored_cvs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TAILORED_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return {"status": "AI CV Agent is running!"}

@app.post("/upload-cv/")
async def upload_cv(cv: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, cv.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(cv.file, buffer)
    return {"message": "CV uploaded and saved.", "filename": cv.filename}

@app.get("/list-cvs/")
def list_cvs():
    return {"uploaded_cvs": os.listdir(UPLOAD_DIR)}

@app.post("/analyze-fit/")
def analyze_fit(cv_filename: str = Form(...), url: Optional[str] = Form(None), text: Optional[str] = Form(None)):
    file_path = os.path.join(UPLOAD_DIR, cv_filename)
    if not os.path.exists(file_path):
        return {"error": "CV file not found."}
    ext = os.path.splitext(cv_filename)[1].lower()
    cv_text = extract_text_from_pdf(file_path) if ext == ".pdf" else extract_text_from_docx(file_path)
    job_text = scrape_job_description(url) if url else text
    result = analyze_match_fit(cv_text, job_text)
    return {
        "cv_text": cv_text,
        "job_description": job_text,
        "match_result": result
    }

@app.post("/generate-tailored-cv/")
def generate_tailored_cv(cv_filename: str = Form(...), url: Optional[str] = Form(None), text: Optional[str] = Form(None)):
    file_path = os.path.join(UPLOAD_DIR, cv_filename)
    if not os.path.exists(file_path):
        return {"error": "CV file not found."}
    ext = os.path.splitext(cv_filename)[1].lower()
    cv_text = extract_text_from_pdf(file_path) if ext == ".pdf" else extract_text_from_docx(file_path)
    job_text = scrape_job_description(url) if url else text
    result = generate_tailored_cv_text_with_keywords(cv_text, job_text)
    tailored_text = result["tailored_cv"]
    keywords = result["keywords"]
    phrases = result["key_phrases"]
    doc = Document()
    for line in tailored_text.splitlines():
        doc.add_paragraph(line)
    filename = f"tailored_{uuid4().hex[:8]}.docx"
    doc_path = os.path.join(TAILORED_DIR, filename)
    doc.save(doc_path)
    return {
        "tailored_cv_text": tailored_text,
        "keywords": keywords,
        "key_phrases": phrases,
        "download_link": f"/download-tailored-cv/{filename}"
    }

@app.get("/download-tailored-cv/{filename}")
def download_tailored_cv(filename: str):
    path = os.path.join(TAILORED_DIR, filename)
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=filename)
