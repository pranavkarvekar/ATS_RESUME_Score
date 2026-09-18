# -*- coding: utf-8 -*-
"""
Skill Clusters.

Groups conceptually related skills so candidates get partial credit
if they have a skill in the same cluster as a required skill.
"""

# Cluster ID -> list of canonical skills
_CLUSTERS = {
    "frontend": ["react", "vue.js", "angular", "javascript", "typescript", "html", "css", "svelte"],
    "backend": ["python", "java", "c#", "node.js", "go", "ruby", "php", "django", "fastapi", "flask", "spring", "express"],
    "database": ["postgresql", "mysql", "mongodb", "redis", "oracle", "sql server", "cassandra", "elasticsearch"],
    "cloud_devops": ["aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd", "jenkins", "linux"],
    "data_ai": ["python", "ml", "ai", "pandas", "numpy", "tensorflow", "pytorch", "scikit-learn", "sql"],
}

# Reverse index: canonical skill -> list of clusters it belongs to
CLUSTER_MAP: dict[str, list[str]] = {}
for cluster, skills in _CLUSTERS.items():
    for skill in skills:
        if skill not in CLUSTER_MAP:
            CLUSTER_MAP[skill] = []
        CLUSTER_MAP[skill].append(cluster)

def get_clusters(skill: str) -> list[str]:
    """Returns the clusters a canonical skill belongs to."""
    return CLUSTER_MAP.get(skill, [])
