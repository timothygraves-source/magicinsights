"""Extracts plain text from uploaded PDF or Word document files."""

import io
import PyPDF2
from docx import Document


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text(uploaded_file) -> str:
    """Accepts a Streamlit UploadedFile and returns plain text."""
    file_bytes = uploaded_file.read()
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif name.endswith(".docx") or name.endswith(".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {uploaded_file.name}. Please upload a PDF or Word document.")


def combine_transcripts(uploaded_files) -> str:
    """Extracts and combines text from multiple uploaded files."""
    parts = []
    for f in uploaded_files:
        text = extract_text(f)
        parts.append(f"=== TRANSCRIPT: {f.name} ===\n\n{text}")
    return "\n\n\n".join(parts)
