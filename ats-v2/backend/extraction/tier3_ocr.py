# -*- coding: utf-8 -*-
"""
Tier 3 Extraction: OCR (Tesseract)

Used as a final fallback for scanned PDFs or PDFs consisting entirely of images.
Requires Tesseract OCR and Poppler to be installed on the host system.
"""

from __future__ import annotations

import io
import logging

from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

log = logging.getLogger("ats.extraction.tier3")

# Common Tesseract paths on Windows for graceful fallback checking
# If it's in PATH, pytesseract will find it automatically.
TESSERACT_WINDOWS_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

def extract_text(file_content: bytes) -> str:
    """
    Extracts text from a PDF byte stream using Tesseract OCR.
    Converts PDF pages to images, then runs OCR on each image.
    
    Args:
        file_content: Raw bytes of the PDF file.
        
    Returns:
        The extracted text as a single string.
    """
    log.info("Starting Tier 3 OCR extraction")
    
    text_content = []
    
    try:
        # Convert PDF bytes to a list of PIL Images
        # Note: requires poppler installed and in PATH
        images = convert_from_bytes(file_content, dpi=300)
        
        for i, image in enumerate(images):
            # psm 6 = Assume a single uniform block of text
            # oem 3 = Default OCR Engine Mode
            text = pytesseract.image_to_string(image, config="--psm 6 --oem 3")
            
            if text.strip():
                text_content.append(text.strip())
                
            text_content.append("\n--- PAGE BREAK ---\n")
            
    except pytesseract.TesseractNotFoundError as e:
        log.error("Tesseract OCR is not installed or not in PATH.")
        raise RuntimeError(
            "Tesseract OCR is not installed. Please install Tesseract OCR and add it to your PATH."
        ) from e
    except Exception as e:
        log.error("Tier 3 OCR extraction failed: %s", str(e))
        raise RuntimeError(f"Tier 3 extraction failed: {str(e)}") from e
        
    final_text = "\n".join(text_content).strip()
    log.debug("Tier 3 extracted %d characters", len(final_text))
    return final_text
