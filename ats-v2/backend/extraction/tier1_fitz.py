# -*- coding: utf-8 -*-
"""
Tier 1 Extraction: PyMuPDF (fitz)

The fastest extraction method for standard, text-based PDFs.
Reads text blocks and attempts basic spatial sorting to handle 
simple layout elements.
"""

from __future__ import annotations

import logging
import fitz  # PyMuPDF

log = logging.getLogger("ats.extraction.tier1")

def extract_text(file_content: bytes) -> str:
    """
    Extracts text from a PDF byte stream using PyMuPDF.
    Sorts blocks primarily by Y-coordinate, then by X-coordinate to 
    maintain logical reading order.
    
    Args:
        file_content: Raw bytes of the PDF file.
        
    Returns:
        The extracted text as a single string.
    """
    log.info("Starting Tier 1 PyMuPDF extraction")
    
    text_content = []
    
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Extract text blocks: (x0, y0, x1, y1, "text", block_no, block_type)
            # block_type 0 means text, 1 means image
            blocks = page.get_text("blocks")
            
            # Filter out images (block_type == 1)
            text_blocks = [b for b in blocks if b[6] == 0]
            
            # Sort blocks top-to-bottom (y0), then left-to-right (x0)
            # A tolerance of 10 points is used for y to group items on the same line
            text_blocks.sort(key=lambda b: (round(b[1] / 10.0), b[0]))
            
            for block in text_blocks:
                block_text = block[4].strip()
                if block_text:
                    # Clean up random linebreaks within blocks but keep structural ones
                    block_text = block_text.replace("\n", " ")
                    text_content.append(block_text)
                    
            # Add a clear separator between pages
            text_content.append("\n--- PAGE BREAK ---\n")
            
        doc.close()
        
    except Exception as e:
        log.error("Tier 1 PyMuPDF extraction failed: %s", str(e))
        raise RuntimeError(f"Tier 1 extraction failed: {str(e)}") from e
        
    final_text = "\n".join(text_content).strip()
    log.debug("Tier 1 extracted %d characters", len(final_text))
    return final_text
