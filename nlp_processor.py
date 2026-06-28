"""
nlp_processor.py
-----------------
Text preprocessing and skill extraction.

Pipeline:
1. Preprocess: lowercase, remove noise, tokenize, lemmatize, stopword removal.
2. Skill extraction: phrase-matching against the SKILLS_DB taxonomy
   (handles multi-word skills like "machine learning"), plus alias resolution.
3. Section detection: split resume into Experience / Education / Skills /
   Projects / Certifications sections using header heuristics.

We use NLTK for tokenization, stopword removal, and lemmatization. NLTK's
data packages (punkt, stopwords, wordnet) are downloaded once on first run
and cached locally — much lighter than a full spaCy model download, and
keeps the app working in network-restricted environments since NLTK's
data server is widely reachable.
"""

import re

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

from skills_db import ALIASES, ALL_SKILLS, SKILL_TO_CATEGORY

_NLTK_READY = False
_LEMMATIZER = None
_STOPWORDS = None


def _ensure_nltk_data():
    """Download required NLTK corpora once, silently, if not already present."""
    global _NLTK_READY, _LEMMATIZER, _STOPWORDS
    if _NLTK_READY:
        return
    required = [
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
        ("corpora/stopwords", "stopwords"),
        ("corpora/wordnet", "wordnet"),
    ]
    for path, pkg in required:
        try:
            nltk.data.find(path)
        except LookupError:
            try:
                nltk.download(pkg, quiet=True)
            except Exception:
                pass
    _LEMMATIZER = WordNetLemmatizer()
    try:
        _STOPWORDS = set(stopwords.words("english"))
    except LookupError:
        _STOPWORDS = set()
    _NLTK_READY = True


def preprocess_text(text: str) -> str:
    """Lowercase + strip special characters while preserving useful symbols
    like '+', '#', '.', '/' that appear in skill names (C++, C#, Node.js, CI/CD)."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#./\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def lemmatize_and_clean(text: str) -> str:
    """Tokenize, remove stopwords/short tokens, and lemmatize — used to build
    the cleaned text fed into TF-IDF for semantic similarity scoring."""
    _ensure_nltk_data()
    clean = preprocess_text(text)
    try:
        tokens = word_tokenize(clean)
    except LookupError:
        tokens = clean.split()

    result = []
    for tok in tokens:
        if len(tok) <= 1:
            continue
        if _STOPWORDS and tok in _STOPWORDS:
            continue
        if not re.search(r"[a-z0-9]", tok):
            continue
        lemma = _LEMMATIZER.lemmatize(tok) if _LEMMATIZER else tok
        result.append(lemma)
    return " ".join(result)


def extract_skills(text: str) -> dict:
    """
    Extract skills present in `text` by matching against the curated
    taxonomy (ALL_SKILLS, longest phrases first to avoid partial overlaps,
    e.g. matching "machine learning" before "learning").

    Returns a dict: {category: sorted list of matched skills}
    """
    clean = preprocess_text(text)
    padded = f" {clean} "

    found = set()
    matched_spans = []
    for skill in ALL_SKILLS:
        # Word-boundary-safe match for the skill phrase
        pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
        for m in re.finditer(pattern, padded):
            start, end = m.start(), m.end()
            # Skip if this match's span is fully contained within an already
            # matched (longer, since ALL_SKILLS is sorted longest-first) span,
            # e.g. "react" inside "react.js"
            if any(s <= start and end <= e for s, e in matched_spans):
                continue
            found.add(skill)
            matched_spans.append((start, end))
            break  # one span recorded per skill is enough to confirm presence

    # Also resolve aliases (e.g. "js" -> "javascript") that may appear standalone
    for alias, canonical in ALIASES.items():
        pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
        if re.search(pattern, padded) and canonical in SKILL_TO_CATEGORY:
            found.add(canonical)

    grouped = {}
    for skill in found:
        category = SKILL_TO_CATEGORY.get(skill, "Other")
        grouped.setdefault(category, []).append(skill)

    for category in grouped:
        grouped[category] = sorted(grouped[category])

    return grouped


def flatten_skills(grouped_skills: dict) -> set:
    """Flatten a {category: [skills]} dict into a single set of skill strings."""
    flat = set()
    for skills in grouped_skills.values():
        flat.update(skills)
    return flat


# --- Resume section detection -------------------------------------------------

SECTION_HEADERS = {
    "experience": [
        "experience", "work experience", "professional experience",
        "employment history", "work history"
    ],
    "education": ["education", "academic background", "academic qualifications"],
    "skills": ["skills", "technical skills", "core competencies", "key skills"],
    "projects": ["projects", "personal projects", "academic projects"],
    "certifications": ["certifications", "certificates", "licenses"],
    "summary": ["summary", "professional summary", "objective", "profile"],
    "contact": ["contact", "contact information"],
}


def detect_sections(text: str) -> dict:
    """
    Split resume text into sections based on header line detection.
    Returns {section_name: section_text}. Lines that look like a standalone
    header (short, matches known header keywords) start a new section.
    """
    lines = text.split("\n")
    sections = {}
    current_section = "header"
    buffer = []

    header_lookup = {
        alias: canon
        for canon, aliases in SECTION_HEADERS.items()
        for alias in aliases
    }

    def flush():
        if buffer:
            sections.setdefault(current_section, "")
            sections[current_section] += "\n".join(buffer) + "\n"

    for line in lines:
        stripped = line.strip()
        norm = stripped.lower().strip(":#-= ")
        if norm in header_lookup and len(stripped) < 40:
            flush()
            current_section = header_lookup[norm]
            buffer = []
        else:
            buffer.append(line)
    flush()
    return sections


def detect_resume_red_flags(text: str, page_count: int = 1) -> list:
    """
    Lightweight heuristic checks that feed into the ATS compatibility score.
    Returns a list of (issue, severity) tuples.
    """
    flags = []
    word_count = len(text.split())

    if word_count < 150:
        flags.append(("Resume content seems very short for thorough parsing.", "high"))
    if page_count > 2:
        flags.append(("Resume is longer than 2 pages, which some ATS systems truncate.", "medium"))
    if "@" not in text:
        flags.append(("No email address detected — ATS may reject resumes without contact info.", "high"))
    if not re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", text) and not re.search(r"\+\d{1,3}[\s-]?\d{6,12}", text):
        flags.append(("No phone number detected.", "medium"))
    if re.search(r"\t{2,}", text):
        flags.append(("Multiple tab characters detected — may indicate table/column layout that confuses ATS parsers.", "medium"))
    if sum(1 for c in text if ord(c) > 0x2500) > 5:
        flags.append(("Special/graphical characters detected — may not parse cleanly in ATS.", "low"))

    return flags
