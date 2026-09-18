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

# Create the limiter instance — keyed by client IP address
limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])
