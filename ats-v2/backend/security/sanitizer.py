# -*- coding: utf-8 -*-
"""
Text Sanitizer.

Cleans extracted text before it is sent to the LLM to reduce token usage
and prevent prompt injection via unicode trickery.
"""

import re
import unicodedata
import logging

log = logging.getLogger("ats.security.sanitizer")

def sanitize_text(text: str) -> str:
    """
    Sanitizes raw extracted text:
    - Removes unicode control characters
    - Collapses multiple whitespaces into a single space
    - Collapses multiple newlines into a double newline
    
    Args:
        text: Raw text from extraction pipeline.
        
    Returns:
        Cleaned, token-efficient text.
    """
    if not text:
        return ""
        
    # Remove unicode control characters except newlines/tabs
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t"))
    
    # Collapse 3+ newlines into exactly 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Collapse 2+ spaces/tabs into a single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()
