# -*- coding: utf-8 -*-
"""
Rate limiting configuration using slowapi.

Limits requests per IP/API key to prevent abuse and
protect the Groq API free tier quota (30 RPM).
"""

from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

from config import RATE_LIMIT

log = logging.getLogger("ats.ratelimit")


def _get_real_ip(request) -> str:
    """
    Returns the real client IP behind Render's reverse proxy.
    Render sets X-Forwarded-For; fall back to direct remote address.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Create the limiter instance — keyed by real client IP address
limiter = Limiter(key_func=_get_real_ip, default_limits=[RATE_LIMIT])
