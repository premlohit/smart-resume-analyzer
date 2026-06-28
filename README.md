# Smart Resume Analyzer

An AI-powered resume screening tool that extracts skills from a resume, compares
them against a job description, and produces a match score, missing-skills
report, ATS compatibility check, and AI-generated improvement suggestions.

## Features

**Basic**
- Upload resume (PDF, DOCX, or TXT)
- Automatic text extraction
- Skill extraction across 11 categories (Programming Languages, Cloud & DevOps,
  Data Science & ML, Soft Skills, etc.)
- Match resume against a job description (pasted text or uploaded file)

**Intermediate**
- Resume match score out of 100 (weighted skill overlap + semantic similarity)
- Missing skills suggestions
- Strengths and weaknesses breakdown
- ATS compatibility score with specific issues flagged

**Advanced**
- AI-generated improvement suggestions via the OpenAI API (specific rewrite
  examples, keyword recommendations, overall fit verdict)
- Batch mode: upload multiple resumes, rank them against one job description,
  export results to CSV

## Tech Stack

- **Python** — core language
- **Streamlit** — web app framework / UI
- **NLTK** — tokenization, stopword removal, lemmatization
- **Scikit-Learn** — TF-IDF vectorization + cosine similarity for semantic matching
- **PyPDF2 / pdfplumber** — PDF text extraction (pdfplumber primary, PyPDF2 fallback)
- **python-docx** — DOCX text extraction
- **OpenAI API** — AI-generated improvement suggestions
- **Plotly** — score gauge visualizations
- **Pandas** — batch ranking table + CSV export

## How Scoring Works

```
Match Score = 0.65 × Skill Overlap Ratio + 0.35 × Semantic Similarity
```

- **Skill Overlap Ratio**: fraction of job-description skills (from a curated
  100+ skill taxonomy across 11 categories) found in the resume.
- **Semantic Similarity**: TF-IDF + cosine similarity between the full
  lemmatized resume and job description text, capturing contextual overlap
  beyond exact keyword matches.
- **ATS Score**: a separate rule-based score (0–100) checking for common
  ATS-parsing pitfalls — missing contact info, resume length, layout issues,
  unusual characters.

These run fully offline. Only the "AI-Generated Improvement Suggestions"
feature calls the OpenAI API, and it's optional — everything else works
without an API key.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the app:
   ```bash
   streamlit run app.py
   ```

3. Open the local URL Streamlit prints (usually `http://localhost:8501`).

4. (Optional) To use AI-generated suggestions, paste your OpenAI API key into
   the sidebar field. It's used only for that session and never stored.

   NLTK data (punkt, stopwords, wordnet) downloads automatically the first
   time you run an analysis — this requires internet access on first run only.

## Project Structure

```
smart-resume-analyzer/
├── app.py                # Streamlit UI — single & batch modes
├── extractor.py          # PDF/DOCX/TXT text extraction
├── nlp_processor.py      # Preprocessing, lemmatization, skill extraction
├── scorer.py             # TF-IDF similarity, skill overlap, ATS scoring
├── ai_suggestions.py     # OpenAI API integration for AI suggestions
├── skills_db.py          # Curated skill taxonomy (11 categories, 150+ skills)
├── requirements.txt
└── .streamlit/
    └── config.toml       # Custom theme
```

## Usage

**Single Resume mode**: upload one resume, paste or upload a job description,
click Analyze. View match score, skill gaps, strengths/weaknesses, ATS issues,
and optionally generate AI suggestions.

**Batch Mode**: upload multiple resumes against one job description to get a
ranked candidate table (sortable, exportable to CSV), then drill into any
individual candidate's full analysis.

## Notes & Limitations

- Scanned/image-only PDFs won't extract text (no OCR included) — use a
  text-based PDF, DOCX, or TXT resume instead.
- The skill taxonomy in `skills_db.py` is curated and extensible — add new
  skills/categories there as needed for your domain.
- The OpenAI API key is required only for the "Generate AI suggestions"
  button; all other features work without it.
