# -*- coding: utf-8 -*-
"""
File validation module.

Handles checking magic bytes to prevent spoofed extensions, 
enforcing file size limits, and counting pages.
"""

from __future__ import annotations

import io
import logging
from typing import Tuple

import fitz  # PyMuPDF

log = logging.getLogger("ats.file_validator")

# Maximum size in bytes (10 MB)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Maximum allowed pages to prevent resource exhaustion
MAX_PAGES = 15

# Magic bytes for supported formats
MAGIC_BYTES = {
    "pdf": b"%PDF-",
    "docx": b"PK\x03\x04",
}


def validate_file(file_content: bytes, filename: str) -> Tuple[bool, str, str]:
    """
    Validates the uploaded file.
    Checks size limit, magic bytes for real file type, and page count for PDFs.

    Returns:
        (is_valid: bool, error_message: str, detected_type: str)
    """
    size = len(file_content)

    if size == 0:
        return False, "File is empty.", ""

    if size > MAX_FILE_SIZE_BYTES:
        return False, f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB.", ""

    # Check magic bytes
    detected_type = "unknown"
    if file_content.startswith(MAGIC_BYTES["pdf"]):
        detected_type = "pdf"
    elif file_content.startswith(MAGIC_BYTES["docx"]):
        detected_type = "docx"
    else:
        # Check for empty or malformed files bypassing the startswith
        return False, f"Unsupported file type. Expected PDF or DOCX, but magic bytes do not match.", ""

    # Specific validation for PDF
    if detected_type == "pdf":
        try:
            # We open the PDF from memory using PyMuPDF to check page count
            # Use 'pdf' stream type
            doc = fitz.open(stream=file_content, filetype="pdf")
            page_count = doc.page_count
            doc.close()
            
            if page_count > MAX_PAGES:
                return False, f"PDF exceeds maximum page limit of {MAX_PAGES}. Uploaded document has {page_count} pages.", "pdf"
                
        except Exception as e:
            log.warning("PyMuPDF failed to parse file for validation: %s", str(e))
            return False, "Uploaded file appears to be a corrupted or invalid PDF.", "pdf"

    return True, "", detected_type
