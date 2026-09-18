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


async def parse_resume_with_groq(raw_text: str) -> Tuple[ParsedResume, int, bool]:
    """
    Parses the raw resume text into a structured ParsedResume object.
    Implements a 3-attempt retry logic with corrective feedback.

    Returns:
        (ParsedResume, attempts_used, used_regex_fallback)
    """
    if not config.GROQ_API_KEY or config.GROQ_API_KEY.startswith("gsk_your"):
        log.warning("No valid GROQ_API_KEY found! Using regex fallback.")
        fallback_data = regex_fallback.fallback_parse(raw_text)
        return ParsedResume(**fallback_data), 0, True

    # Use model from config — NOT hardcoded
    model_name = config.GROQ_MODEL or "llama-3.3-70b-versatile"
    log.info("Using model: %s", model_name)

    client = AsyncOpenAI(
        api_key=config.GROQ_API_KEY,
        base_url=config.GROQ_BASE_URL or "https://api.groq.com/openai/v1",
        timeout=30.0,
    )

    system_prompt = prompts.SYSTEM_PARSE_RESUME
    user_prompt = prompts.USER_PARSE_TEMPLATE.format(resume_text=raw_text[:6000])

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    max_attempts = 3
    raw_output = ""

    for attempt in range(1, max_attempts + 1):
        try:
            log.info("Parsing resume (Attempt %d/%d) model=%s", attempt, max_attempts, model_name)

            temperature = 0.1 if attempt == 1 else 0.0

            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=2048,
            )

            raw_output = response.choices[0].message.content or ""

            # Sanitize output
            json_str = json_sanitizer.sanitize_json_string(raw_output)

            # Parse JSON
            parsed_dict = json.loads(json_str)

            # Validate with Pydantic
            parsed_resume = ParsedResume.model_validate(parsed_dict)

            log.info("Successfully parsed resume on attempt %d", attempt)
            return parsed_resume, attempt, False

        except (APIStatusError, APIConnectionError, APITimeoutError) as e:
            # API-level errors — log and fall back immediately, no point retrying auth errors
            log.error("Groq API error on attempt %d: %s", attempt, str(e))
            if hasattr(e, "status_code") and e.status_code in (401, 403):
                log.error("Authentication failure — check GROQ_API_KEY")
                break
            # For connection/timeout errors, retry once more
            if attempt >= max_attempts:
                break

        except json.JSONDecodeError as e:
            error_msg = f"JSON Decode Error: {str(e)}"
            log.warning("Attempt %d failed: %s", attempt, error_msg)
            if attempt < max_attempts:
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({
                    "role": "user",
                    "content": prompts.RETRY_PARSE_TEMPLATE.format(error_details=error_msg)
                })

        except Exception as e:
            error_msg = f"Validation Error: {str(e)}"
            log.warning("Attempt %d failed: %s", attempt, error_msg)
            if attempt < max_attempts:
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({
                    "role": "user",
                    "content": prompts.RETRY_PARSE_TEMPLATE.format(error_details=error_msg)
                })

    # If all retries fail, use regex fallback
    log.error("All %d parse attempts failed. Falling back to regex.", max_attempts)
    fallback_data = regex_fallback.fallback_parse(raw_text)
    return ParsedResume(**fallback_data), max_attempts, True
