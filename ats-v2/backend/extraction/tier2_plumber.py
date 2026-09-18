# -*- coding: utf-8 -*-
"""
Tier 2 Extraction: pdfplumber

Used for complex PDFs where PyMuPDF fails or loses structure.
Particularly good at extracting text while preserving table and column structures.
"""

from __future__ import annotations

import io
import logging

import pdfplumber

log = logging.getLogger("ats.extraction.tier2")

def extract_text(file_content: bytes) -> str:
    """
    Extracts text from a PDF byte stream using pdfplumber.
    Preserves table structures by extracting them separately, then
    extracts the remaining page text.
    
    Args:
        file_content: Raw bytes of the PDF file.
        
    Returns:
        The extracted text as a single string.
    """
    log.info("Starting Tier 2 pdfplumber extraction")
    
    text_content = []
    
    try:
        # Wrap bytes in BytesIO for pdfplumber
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # 1. Extract tables first
                tables = page.extract_tables()
                if tables:
                    for table_idx, table in enumerate(tables):
                        text_content.append(f"--- Table {table_idx + 1} ---")
                        for row in table:
                            # Clean up None values and join cells
                            cleaned_row = [str(cell).strip().replace("\n", " ") if cell else "" for cell in row]
                            # Only add non-empty rows
                            if any(cleaned_row):
                                text_content.append(" | ".join(cleaned_row))
                        text_content.append("----------------")

                # 2. Extract standard text (layout preservation)
                page_text = page.extract_text(
                    layout=True,
                    x_tolerance=2,
                    y_tolerance=3
                )
                
                if page_text:
                    text_content.append(page_text.strip())
                    
                # Add separator
                text_content.append("\n--- PAGE BREAK ---\n")
                
    except Exception as e:
        log.error("Tier 2 pdfplumber extraction failed: %s", str(e))
        raise RuntimeError(f"Tier 2 extraction failed: {str(e)}") from e
        
    final_text = "\n".join(text_content).strip()
    log.debug("Tier 2 extracted %d characters", len(final_text))
    return final_text
