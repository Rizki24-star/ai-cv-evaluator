import PyPDF2
import pdfplumber
import logging
from pathlib import Path
from typing import Optional

class PDFParser:
    """
    PDF Text Extraction with fallback strategies
    """

    def extract_text(self, file_path: Path) -> str:
        """Extract text from PDF file"""

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            text = PDFParser._extract_with_pdfplumber(file_path)
            if text and len(text) > 100:
                logging.info(f"Extracted {len(text)} char using pdfplumber")
                return text
        except Exception as e:
            logging.error(f"PDF plumber failed: {e}")


        try:
            text = PDFParser._extract_with_pdf2(file_path)
            if text and len(text) > 100:
                logging.info(f"Extracted {len(text)} char using pdfplumber")
                return text
        except Exception as e:
            logging.error(f"PDF plumber failed: {e}")


        raise ValueError(f"Could not extract text from PDF: {file_path}")

    @staticmethod
    def _extract_with_pdfplumber(file_path: Path) -> Optional[str]:
        """Extract text using pdfplumber"""
        text_part = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_part.append(page_text)

        return "\n\n".join(text_part)

    @staticmethod
    def _extract_with_pdf2(file_path: Path) -> Optional[str]:
        """Extract text using PyPDF2"""
        text_parts = []

        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n\n".join(text_parts)

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int,
        overlap: int
    ) -> list[str]:
        """Split text into overlapping chunks by word"""

        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)

        return chunks

    @staticmethod
    def chunk_by_sections(text: str) -> list[tuple[str, str]]:
        """Chunk text by sections (preserve headers)"""

        import re

        section_pattern = r'^([A-Z][A-Za-z\s&/]+):?\s*$'

        lines = text.split('\n')
        sections = []
        current_section = "Introduction"
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a header section
            if re.match(section_pattern, line):
                if current_content:
                    sections.append((
                        current_section,
                        '\n'.join(current_content)
                    ))

                # Start new section
                current_section = line.rstrip(':')
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections.append((
                current_section,
                '\n'.join(current_content)
            ))

        return sections

def get_pdf_parser() -> PDFParser:
    """Get PDFParser instance"""
    return PDFParser()
