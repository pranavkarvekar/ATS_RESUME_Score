# -*- coding: utf-8 -*-
"""
Skill Aliases.

Maps synonymous skills to a single canonical name.
"""

# Canonical -> list of aliases
_ALIASES = {
    "react": ["reactjs", "react.js", "react js"],
    "node.js": ["node", "nodejs", "node js"],
    "vue.js": ["vue", "vuejs"],
    "kubernetes": ["k8s"],
    "postgresql": ["postgres"],
    "amazon web services": ["aws"],
    "google cloud platform": ["gcp"],
    "artificial intelligence": ["ai"],
    "machine learning": ["ml"],
    "ci/cd": ["continuous integration", "continuous deployment", "ci cd"],
    "c#": ["csharp", "c sharp"],
    "c++": ["cpp"],
}

# Build reverse index for O(1) lookups: alias -> canonical
ALIAS_MAP = {}
for canonical, aliases in _ALIASES.items():
    ALIAS_MAP[canonical.lower()] = canonical.lower()
    for alias in aliases:
        ALIAS_MAP[alias.lower()] = canonical.lower()

def get_canonical(skill: str) -> str:
    """Returns the canonical name for a skill, or the original if not found."""
    return ALIAS_MAP.get(skill.lower(), skill.lower())
