# -*- coding: utf-8 -*-
"""
LLM Parser Orchestrator.

Manages communication with the Groq API for parsing resumes,
handles retries, and validates against Pydantic schemas.
"""

from __future__ import annotations

import json
import logging
from typing import Tuple

from openai import AsyncOpenAI, APIStatusError, APIConnectionError, APITimeoutError

import config
from models.schemas import ParsedResume
from . import prompts
from . import json_sanitizer
from . import regex_fallback

log = logging.getLogger("ats.parsing.llm")


async def parse_resume_with_groq(raw_text: str, job_description: str) -> Tuple[ParsedResume, float, str, int, bool]:
    """
    Parses the raw resume text into a structured ParsedResume object AND gets contextual fit.
    
    Returns:
        (ParsedResume, contextual_score, contextual_justification, attempts_used, used_regex_fallback)
    """
    if not config.GROQ_API_KEY or config.GROQ_API_KEY.startswith("gsk_your"):
        log.warning("No valid GROQ_API_KEY found! Using regex fallback.")
        fallback_data = regex_fallback.fallback_parse(raw_text)
        return ParsedResume(**fallback_data), 10.0, "API key missing. Defaulting.", 0, True

    model_name = config.GROQ_MODEL or "llama-3.3-70b-versatile"
    log.info("Using model: %s for unified parsing and scoring", model_name)

    client = AsyncOpenAI(
        api_key=config.GROQ_API_KEY,
        base_url=config.GROQ_BASE_URL or "https://api.groq.com/openai/v1",
        timeout=30.0,
    )

    system_prompt = prompts.SYSTEM_PARSE_RESUME
    user_prompt = prompts.USER_PARSE_TEMPLATE.format(
        job_description=job_description[:config.MAX_JD_CHARS_FOR_CONTEXT],
        resume_text=raw_text[:6000]
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
            max_tokens=2048,
        )
        
        raw_output = response.choices[0].message.content or "{}"
        parsed_dict = json.loads(raw_output)
        
        candidate_data = parsed_dict.get("candidate", {})
        evaluation = parsed_dict.get("contextual_evaluation", {})
        
        parsed_resume = ParsedResume.model_validate(candidate_data)
        
        score = float(evaluation.get("score", 10.0))
        score = max(10.0, min(score, 40.0))
        justification = evaluation.get("justification", "Contextual alignment calculated.")
        
        return parsed_resume, score, justification, 1, False

    except Exception as e:
        log.error("Unified LLM parsing failed: %s. Falling back to regex.", str(e))
        fallback_data = regex_fallback.fallback_parse(raw_text)
        return ParsedResume(**fallback_data), 10.0, "Parsing failed, regex fallback used.", 1, True
