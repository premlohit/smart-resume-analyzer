"""
ai_suggestions.py
-------------------
Calls the OpenAI API to generate qualitative, AI-written improvement
suggestions that go beyond the rule-based strengths/weaknesses output.

This is the only module that talks to an external LLM. It is designed to
fail soft: if no API key is configured or the call errors out, the rest
of the app (skill extraction, scoring, ATS check) continues to work using
only the offline NLP/Scikit-Learn pipeline.
"""

import json

from openai import OpenAI

MODEL = "gpt-4o-mini"


def get_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def build_prompt(resume_text: str, jd_text: str, analysis: dict) -> str:
    matched = ", ".join(analysis["matched_skills"]) or "none detected"
    missing = ", ".join(analysis["missing_skills"]) or "none"

    # Truncate very long resumes/JDs to keep prompt size reasonable
    resume_excerpt = resume_text[:6000]
    jd_excerpt = jd_text[:3000]

    return f"""You are an expert technical recruiter and resume coach.

JOB DESCRIPTION:
\"\"\"{jd_excerpt}\"\"\"

CANDIDATE RESUME:
\"\"\"{resume_excerpt}\"\"\"

ANALYSIS ALREADY COMPUTED:
- Match score: {analysis['match_score']}/100
- Matched skills: {matched}
- Missing skills: {missing}

TASK: Provide actionable, specific improvement suggestions for this resume so it
better matches the job description and performs better with both human recruiters
and ATS systems. Be concrete — reference actual content from the resume where possible,
not generic advice.

Respond ONLY in valid JSON, with this exact structure and nothing else:
{{
  "improvement_suggestions": ["suggestion 1", "suggestion 2", "..."],
  "rewrite_examples": [
    {{"before": "a real weak phrase or bullet from the resume", "after": "an improved, quantified, keyword-aligned rewrite"}}
  ],
  "keyword_recommendations": ["keyword or phrase to add", "..."],
  "overall_verdict": "1-2 sentence honest assessment of this candidate's fit for the role"
}}

Provide 4-6 improvement_suggestions, 2-3 rewrite_examples drawn from actual resume content,
and 5-8 keyword_recommendations prioritizing the missing skills listed above.
"""


def generate_ai_suggestions(resume_text: str, jd_text: str, analysis: dict, api_key: str) -> dict:
    """
    Calls OpenAI to generate structured improvement suggestions.
    Returns a dict matching the JSON schema requested in the prompt,
    or a dict with an "error" key if the call fails.
    """
    if not api_key:
        return {"error": "No OpenAI API key provided."}

    try:
        client = get_client(api_key)
        prompt = build_prompt(resume_text, jd_text, analysis)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful, precise resume-review assistant that always responds in valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "AI response could not be parsed. Please try again."}
    except Exception as e:
        return {"error": f"OpenAI API error: {e}"}
