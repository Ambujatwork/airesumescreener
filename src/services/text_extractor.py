
import pdfplumber
import io
import re
import logging
from typing import Optional
from fastapi import UploadFile
from docx import Document

logger = logging.getLogger(__name__)

class TextExtractor:

    @staticmethod
    async def extract_text(file: UploadFile) -> Optional[str]:
        try:
            if file.filename.endswith(".pdf"):
                text = await TextExtractor._extract_pdf_text(file)
            elif file.filename.endswith(".docx"):
                text = await TextExtractor._extract_docx_text(file)
            else:
                logger.warning(f"Unsupported file type: {file.filename}")
                return None

            return TextExtractor._clean_text(text)

        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            return None

    @staticmethod
    async def _extract_pdf_text(file: UploadFile) -> str:
        try:
            content = await file.read()
            text = ""
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
            return text

        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}")
            return ""

    @staticmethod
    async def _extract_docx_text(file: UploadFile) -> str:
        try:
            content = await file.read()
            document = Document(io.BytesIO(content))
            return "\n".join([p.text for p in document.paragraphs if p.text.strip()])

        except Exception as e:
            logger.error(f"DOCX processing error: {str(e)}")
            return ""

    @staticmethod
    def _clean_text(text: str) -> str:
        try:
            text = re.sub(r'[\x00-\x1f]+', ' ', text)  # remove control characters
            text = re.sub(r'[\u200b-\u200f]+', ' ', text)  # invisible unicode
            text = re.sub(r'[\u2022\u25AA\u25E6\u2023\u2043]', '\u2022', text)  # normalize bullets

            sections = {
                r'(?i)about\s*me': 'SUMMARY',
                r'(?i)professional\s*summary': 'SUMMARY',
                r'(?i)work\s*experience': 'EXPERIENCE',
                r'(?i)education\s*history': 'EDUCATION',
                r'(?i)technical\s*skills': 'SKILLS'
            }
            for pattern, replacement in sections.items():
                text = re.sub(pattern, replacement, text)

            text = re.sub(r'\n+', '\n', text)  # Normalize multiple line breaks
            text = re.sub(r'[ \t]+', ' ', text)  # Normalize multiple spaces

            return text.strip()
        except Exception as e:
            logger.error(f"Text cleaning error: {str(e)}")
            return text.strip()