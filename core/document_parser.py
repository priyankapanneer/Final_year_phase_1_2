import io
import os
from typing import Tuple, Dict, Any

def parse_pdf_bytes(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Extracts structured text from PDF bytes using PyMuPDF (fitz) with fallback to pypdf.
    """
    extracted_text = ""
    page_count = 0
    engine_used = "PyMuPDF"

    # Try PyMuPDF (fastest & most accurate for multi-column academic syllabi)
    try:
        import pymupdf
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        page_count = len(doc)
        pages_text = []
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                pages_text.append(text.strip())
        doc.close()
        extracted_text = "\n\n".join(pages_text)
    except Exception as e:
        print(f"[PyMuPDF Notice, trying pypdf]: {e}")
        # Fallback to pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            page_count = len(reader.pages)
            pages_text = [p.extract_text() for p in reader.pages if p.extract_text()]
            extracted_text = "\n\n".join(pages_text)
            engine_used = "pypdf"
        except Exception as e2:
            raise ValueError(f"Failed to extract text from PDF: {str(e2)}")

    return extracted_text.strip(), {"pages": page_count, "engine": engine_used}


def parse_docx_bytes(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Extracts text and table content from .docx Word documents.
    """
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        # Also extract table text (common in course syllabi & course credits)
        table_texts = []
        for table in doc.tables:
            for row in table.rows:
                row_str = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_str:
                    table_texts.append(row_str)

        full_content = "\n".join(paragraphs)
        if table_texts:
            full_content += "\n\n[Syllabus Table Data]:\n" + "\n".join(table_texts)

        return full_content.strip(), {"paragraphs": len(paragraphs), "tables": len(doc.tables)}
    except Exception as e:
        raise ValueError(f"Failed to parse Word (.docx) document: {str(e)}")


def parse_plain_text(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Decodes plain text files (.txt, .md, .csv) trying common encodings.
    """
    for encoding in ["utf-8", "latin-1", "cp1252", "utf-16"]:
        try:
            text = file_bytes.decode(encoding)
            return text.strip(), {"encoding": encoding}
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError("Could not decode text file with standard encodings.")


def parse_document_file(filename: str, file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Master dispatcher for extracting text from any academic document:
    Supports .pdf, .docx, .txt, .csv, .md.
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        return parse_pdf_bytes(file_bytes)
    elif ext in [".docx", ".doc"]:
        return parse_docx_bytes(file_bytes)
    elif ext in [".txt", ".csv", ".md", ".rtf", ".tsv"]:
        return parse_plain_text(file_bytes)
    else:
        # Fallback: attempt plain text decode
        try:
            return parse_plain_text(file_bytes)
        except Exception:
            raise ValueError(f"Unsupported document format '{ext}'. Supported: .pdf, .docx, .txt, .csv, .md")
