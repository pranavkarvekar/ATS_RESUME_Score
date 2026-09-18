# -*- coding: utf-8 -*-
"""
Pipeline Orchestrator for Extraction.

Manages the extraction workflow:
- Routes based on file type (PDF vs DOCX).
- Runs Tier 1 and Tier 2 concurrently for PDFs.
- Detects multi-column layouts to switch to Tier 2.
- Detects scanned PDFs (low char count) and falls back to Tier 3 OCR.
"""

from __future__ import annotations

import asyncio
import logging
import concurrent.futures
from typing import Tuple

from . import docx_extractor
from . import tier1_fitz
from . import tier2_plumber
from . import tier3_ocr

log = logging.getLogger("ats.extraction.pipeline")

# If Tier 1 extracts fewer than this many characters, assume scanned PDF
OCR_THRESHOLD_CHARS = 150

# If Tier 2 extracts 15% more characters than Tier 1, assume Tier 1 
# missed columns/tables and use Tier 2 instead.
TWO_COLUMN_THRESHOLD_RATIO = 1.15


async def extract_resume_text(file_content: bytes, detected_type: str) -> Tuple[str, str]:
    """
    Main entry point for extraction.
    
    Args:
        file_content: Raw bytes of the uploaded file.
        detected_type: 'pdf' or 'docx', detected by magic bytes.
        
    Returns:
        A tuple of (extracted_text, tier_used).
    """
    if detected_type == "docx":
        log.info("Routing to DOCX extractor")
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            text = await loop.run_in_executor(pool, docx_extractor.extract_text, file_content)
        return text, "docx"
        
    elif detected_type == "pdf":
        log.info("Routing to PDF extraction pipeline")
        return await _run_pdf_pipeline(file_content)
        
    else:
        raise ValueError(f"Unsupported file type: {detected_type}")


async def _run_pdf_pipeline(file_content: bytes) -> Tuple[str, str]:
    """
    Runs the 3-tier PDF extraction pipeline.
    """
    loop = asyncio.get_running_loop()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        # Run Tier 1 (PyMuPDF) and Tier 2 (pdfplumber) concurrently
        t1_future = loop.run_in_executor(pool, tier1_fitz.extract_text, file_content)
        t2_future = loop.run_in_executor(pool, tier2_plumber.extract_text, file_content)
        
        # We wait for Tier 1 first as it's our primary
        try:
            t1_text = await t1_future
        except Exception as e:
            log.warning("Tier 1 failed: %s. Falling back to Tier 2.", str(e))
            t1_text = ""
            
        t1_len = len(t1_text)
        log.info("Tier 1 extracted %d characters", t1_len)
        
        # 1. OCR Fallback (Tier 3)
        if t1_len < OCR_THRESHOLD_CHARS:
            log.warning("Very low character count (%d). Assuming scanned PDF.", t1_len)
            log.info("Triggering Tier 3 OCR fallback")
            try:
                t3_text = await loop.run_in_executor(pool, tier3_ocr.extract_text, file_content)
                if len(t3_text) > t1_len:
                    return t3_text, "tier3_ocr"
            except Exception as e:
                log.error("Tier 3 OCR failed: %s", str(e))
                # If OCR fails, we just fall through and try to salvage Tier 2/Tier 1
                
        # 2. Complex Layout Detection (Tier 2 comparison)
        try:
            t2_text = await t2_future
            t2_len = len(t2_text)
            log.info("Tier 2 extracted %d characters", t2_len)
            
            # If Tier 2 extracted significantly more text, PyMuPDF probably dropped 
            # sidebars or complex columns. Use Tier 2.
            if t1_len == 0 and t2_len > 0:
                return t2_text, "tier2_plumber"
            elif t1_len > 0 and (t2_len / t1_len) >= TWO_COLUMN_THRESHOLD_RATIO:
                log.info("Complex layout detected (Tier 2 yield is %d%% of Tier 1). Using Tier 2.", 
                         int((t2_len / t1_len) * 100))
                return t2_text, "tier2_plumber"
                
        except Exception as e:
            log.warning("Tier 2 failed: %s", str(e))
            
        # 3. Default to Tier 1
        if t1_text:
            return t1_text, "tier1_fitz"
            
        return "", "failed"
