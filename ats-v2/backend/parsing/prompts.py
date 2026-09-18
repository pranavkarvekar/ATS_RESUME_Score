# -*- coding: utf-8 -*-
"""
LLM Prompt templates.
"""

SYSTEM_PARSE_RESUME = """You are an expert technical recruiter and resume parser.
Your job is to extract structured data from the provided resume text.

Return ONLY a valid JSON object matching the exact schema below. Do not include markdown formatting or explanations.

{
  "name": "Candidate Full Name",
  "skills": ["Skill 1", "Skill 2"],
  "experience": [
    {
      "company": "Company Name",
      "role": "Job Title",
      "duration_months": 24,
      "responsibilities": ["Responsibility 1", "Responsibility 2"]
    }
  ],
  "education": ["Degree 1", "Degree 2"],
  "projects": [
    {
      "name": "Project Name",
      "description": "What it is",
      "tech_stack": ["Tech 1", "Tech 2"]
    }
  ],
  "certifications": ["Cert 1"]
}

RULES:
- If a field is missing from the resume, leave it as an empty list (or empty string for name).
- For duration_months, convert "2 years" -> 24. "May 2021 to June 2022" -> 13. "Present" means up to current month. If you cannot determine, output 0.
- Extract ONLY hard technical skills into the `skills` array. Ignore soft skills (e.g. "leadership", "communication").
"""

USER_PARSE_TEMPLATE = """
Parse the following resume text:

<resume>
{resume_text}
</resume>
"""

RETRY_PARSE_TEMPLATE = """
Your previous response failed to parse as valid JSON matching the schema. 
Error details: {error_details}

Please try again and ensure you return STRICTLY valid JSON and nothing else.
"""
