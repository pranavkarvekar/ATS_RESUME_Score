# -*- coding: utf-8 -*-
"""
JSON Sanitizer.

Cleans up LLM outputs that might include:
- Markdown fences (```json ... ```)
- Conversational filler text
- <think>...</think> reasoning blocks (Qwen/DeepSeek thinking models)
"""

import re
import logging

log = logging.getLogger("ats.parsing.sanitizer")


def sanitize_json_string(raw_output: str) -> str:
    """
    Strips markdown code fences, thinking blocks, and conversational filler
    from LLM output, extracting only the JSON block.
    """
    text = raw_output.strip()

    # ── 1. Strip <think>...</think> blocks (Qwen3, DeepSeek-R1 thinking models) ──
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

    # ── 2. Check for markdown code blocks ──
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()

    # ── 3. If it's already clean JSON, return it ──
    if text.startswith("{") and text.endswith("}"):
        return text

    # ── 4. Last ditch: find the first '{' and last '}' ──
    start_idx = text.find("{")
    end_idx = text.rfind("}")

    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        return text[start_idx:end_idx + 1]

    # If we really can't find anything, return as-is and let parser fail/fallback
    log.warning("Could not extract JSON from LLM output (len=%d)", len(text))
    return text
