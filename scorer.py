"""
scorer.py
----------
Core scoring engine. Combines two signals into a final match score:

1. Skill overlap score (weighted higher — recruiters care about hard skill
   matches): proportion of JD-required skills present in the resume.
2. Semantic similarity score: TF-IDF + cosine similarity between the full
   cleaned resume text and JD text, capturing context/phrasing overlap
   that a simple keyword match would miss.

Final score = 0.65 * skill_score + 0.35 * similarity_score, scaled to 100.
Weights are tunable via WEIGHTS below.

Also produces:
- Missing skills (in JD, not in resume)
- Matched skills
- Strengths / weaknesses summary
- ATS compatibility score (rule-based, separate from match score)
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from nlp_processor import (
    detect_resume_red_flags,
    extract_skills,
    flatten_skills,
    lemmatize_and_clean,
)

WEIGHTS = {
    "skill_overlap": 0.65,
    "semantic_similarity": 0.35,
}


def compute_semantic_similarity(resume_text: str, jd_text: str) -> float:
    """TF-IDF cosine similarity between resume and JD, lemmatized first."""
    resume_clean = lemmatize_and_clean(resume_text)
    jd_clean = lemmatize_and_clean(jd_text)


    if not resume_clean.strip() or not jd_clean.strip():
        return 0.0

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=5000,
        sublinear_tf=True,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform([resume_clean, jd_clean])
        sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(max(0.0, min(1.0, sim)))
    except ValueError:
        return 0.0


def compute_skill_overlap(resume_skills: set, jd_skills: set) -> tuple:
    """
    Returns (overlap_ratio, matched, missing).
    overlap_ratio = |matched| / |jd_skills|  (0 if JD has no detected skills)
    """
    if not jd_skills:
        return 0.0, set(), set()
    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills
    ratio = len(matched) / len(jd_skills)
    return ratio, matched, missing


def compute_ats_score(resume_text: str, page_count: int = 1) -> dict:
    """
    Rule-based ATS compatibility score (0-100), separate from JD match score.
    Penalizes common ATS-parsing pitfalls.
    """
    score = 100
    flags = detect_resume_red_flags(resume_text, page_count)
    penalty_map = {"high": 15, "medium": 8, "low": 3}

    for _, severity in flags:
        score -= penalty_map.get(severity, 5)

    score = max(0, min(100, score))
    return {
        "score": score,
        "flags": flags,
    }


def generate_strengths_weaknesses(matched: set, missing: set, similarity: float, overlap_ratio: float) -> dict:
    """Rule-based strengths/weaknesses summary (non-LLM, always available)."""
    strengths = []
    weaknesses = []

    if overlap_ratio >= 0.7:
        strengths.append(f"Strong alignment on required skills — {len(matched)} key skills matched.")
    elif overlap_ratio >= 0.4:
        strengths.append(f"Moderate skill alignment with {len(matched)} matched skills.")
    else:
        weaknesses.append(f"Low skill overlap — only {len(matched)} of the required skills were found.")

    if similarity >= 0.3:
        strengths.append("Resume phrasing and context closely mirror the job description's language.")
    elif similarity < 0.15:
        weaknesses.append("Resume content/context differs significantly from the job description's language and focus areas.")

    if missing:
        top_missing = sorted(missing)[:5]
        weaknesses.append(f"Missing or unmentioned skills: {', '.join(top_missing)}.")

    if matched:
        top_matched = sorted(matched)[:5]
        strengths.append(f"Demonstrates: {', '.join(top_matched)}.")

    if not strengths:
        strengths.append("Resume successfully parsed; consider adding more role-specific keywords.")
    if not weaknesses:
        weaknesses.append("No major gaps detected — fine-tune wording to mirror the JD even more closely.")

    return {"strengths": strengths, "weaknesses": weaknesses}


def analyze_resume(resume_text: str, jd_text: str, page_count: int = 1) -> dict:
    """
    Main entry point: runs the full analysis pipeline for one resume
    against one job description. Returns a structured result dict.
    """
    resume_skills_grouped = extract_skills(resume_text)
    jd_skills_grouped = extract_skills(jd_text)

    resume_skills_flat = flatten_skills(resume_skills_grouped)
    jd_skills_flat = flatten_skills(jd_skills_grouped)

    overlap_ratio, matched, missing = compute_skill_overlap(resume_skills_flat, jd_skills_flat)
    similarity = compute_semantic_similarity(resume_text, jd_text)

    final_score = (
        WEIGHTS["skill_overlap"] * overlap_ratio
        + WEIGHTS["semantic_similarity"] * similarity
    ) * 100
    final_score = round(min(100, max(0, final_score)), 1)

    ats = compute_ats_score(resume_text, page_count)
    sw = generate_strengths_weaknesses(matched, missing, similarity, overlap_ratio)

    return {
        "match_score": final_score,
        "skill_overlap_ratio": round(overlap_ratio * 100, 1),
        "semantic_similarity": round(similarity * 100, 1),
        "resume_skills": resume_skills_grouped,
        "jd_skills": jd_skills_grouped,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "ats_score": ats["score"],
        "ats_flags": ats["flags"],
        "strengths": sw["strengths"],
        "weaknesses": sw["weaknesses"],
    }
