"""
app.py
-------
Smart Resume Analyzer — Streamlit application.

Modes:
- Single Resume: upload one resume, paste/upload a JD, get full analysis.
- Batch Mode: upload multiple resumes against one JD, get a ranked table
  plus per-candidate drill-down.

Run with:  streamlit run app.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ai_suggestions import generate_ai_suggestions
from extractor import extract_text, get_page_count
from scorer import analyze_resume

st.set_page_config(
    page_title="Smart Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom styling — restrained, intentional, not default Streamlit gray
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #FAFAF7; }
    h1, h2, h3 { font-family: 'Georgia', serif; color: #1F2421; }
    .score-card {
        background: #FFFFFF;
        border: 1px solid #E3E0D4;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .pill {
        display: inline-block;
        padding: 0.25rem 0.7rem;
        border-radius: 999px;
        font-size: 0.82rem;
        margin: 0.15rem;
        font-weight: 500;
    }
    .pill-matched { background: #E3F0E8; color: #2F6F4E; border: 1px solid #BFDDC9; }
    .pill-missing { background: #FBEAEA; color: #A33A3A; border: 1px solid #F0C8C8; }
    .section-label {
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #8A8675;
        margin-bottom: 0.3rem;
    }
    .rank-1 { border-left: 4px solid #2F6F4E; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def score_color(score: float) -> str:
    if score >= 75:
        return "#2F6F4E"
    elif score >= 50:
        return "#B8860B"
    else:
        return "#A33A3A"


def gauge_chart(score: float, title: str) -> go.Figure:
    color = score_color(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": title, "font": {"size": 16, "family": "Georgia, serif"}},
        number={"suffix": "", "font": {"size": 36, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#8A8675"},
            "bar": {"color": color, "thickness": 0.75},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 50], "color": "#FBEAEA"},
                {"range": [50, 75], "color": "#FCF3E3"},
                {"range": [75, 100], "color": "#E3F0E8"},
            ],
        },
    ))
    fig.update_layout(height=220, margin=dict(t=40, b=10, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def render_pills(items, css_class):
    if not items:
        return "<span style='color:#8A8675;'>None</span>"
    return "".join(f"<span class='pill {css_class}'>{item}</span>" for item in items)


def get_jd_text(key_prefix: str) -> str:
    """Renders the JD input widget (paste or upload) and returns the JD text."""
    jd_mode = st.radio(
        "Job description input",
        ["Paste text", "Upload file"],
        horizontal=True,
        key=f"{key_prefix}_jd_mode",
    )
    jd_text = ""
    if jd_mode == "Paste text":
        jd_text = st.text_area(
            "Paste the job description",
            height=220,
            key=f"{key_prefix}_jd_paste",
            placeholder="Paste the full job description here...",
        )
    else:
        jd_file = st.file_uploader(
            "Upload job description (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"],
            key=f"{key_prefix}_jd_file",
        )
        if jd_file is not None:
            try:
                jd_text = extract_text(jd_file.getvalue(), jd_file.name)
                with st.expander("Preview extracted JD text"):
                    st.text(jd_text[:2000] + ("..." if len(jd_text) > 2000 else ""))
            except ValueError as e:
                st.error(str(e))
    return jd_text


def render_analysis(resume_text: str, jd_text: str, analysis: dict, candidate_name: str, api_key: str, key_prefix: str):
    """Renders the full result block for one resume's analysis."""

    col1, col2, col3 = st.columns(3)
    with col1:
        st.plotly_chart(gauge_chart(analysis["match_score"], "Match Score"), use_container_width=True, key=f"{key_prefix}_gauge_match")
    with col2:
        st.plotly_chart(gauge_chart(analysis["skill_overlap_ratio"], "Skill Overlap"), use_container_width=True, key=f"{key_prefix}_gauge_skill")
    with col3:
        st.plotly_chart(gauge_chart(analysis["ats_score"], "ATS Compatibility"), use_container_width=True, key=f"{key_prefix}_gauge_ats")

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='section-label'>Matched Skills</div>", unsafe_allow_html=True)
        st.markdown(render_pills(analysis["matched_skills"], "pill-matched"), unsafe_allow_html=True)
    with col_b:
        st.markdown("<div class='section-label'>Missing Skills (in JD, not in resume)</div>", unsafe_allow_html=True)
        st.markdown(render_pills(analysis["missing_skills"], "pill-missing"), unsafe_allow_html=True)

    st.markdown("")
    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown("**Strengths**")
        for s in analysis["strengths"]:
            st.markdown(f"- {s}")
    with col_d:
        st.markdown("**Weaknesses**")
        for w in analysis["weaknesses"]:
            st.markdown(f"- {w}")

    if analysis["ats_flags"]:
        with st.expander(f"ATS compatibility details ({len(analysis['ats_flags'])} issue(s) found)"):
            for issue, severity in analysis["ats_flags"]:
                badge = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(severity, "⚪")
                st.markdown(f"{badge} **{severity.title()}** — {issue}")

    with st.expander("Skill breakdown by category"):
        cat_col1, cat_col2 = st.columns(2)
        with cat_col1:
            st.markdown("**Resume skills**")
            if analysis["resume_skills"]:
                for cat, skills in analysis["resume_skills"].items():
                    st.markdown(f"*{cat}*: {', '.join(skills)}")
            else:
                st.caption("No taxonomy skills detected.")
        with cat_col2:
            st.markdown("**Job description skills**")
            if analysis["jd_skills"]:
                for cat, skills in analysis["jd_skills"].items():
                    st.markdown(f"*{cat}*: {', '.join(skills)}")
            else:
                st.caption("No taxonomy skills detected.")

    st.markdown("---")
    st.markdown("### AI-Generated Improvement Suggestions")
    st.caption("Uses the OpenAI API to generate tailored, qualitative suggestions beyond the rule-based analysis above.")

    ai_key = f"{key_prefix}_ai_result"
    if st.button("Generate AI suggestions", key=f"{key_prefix}_ai_btn"):
        if not api_key:
            st.warning("Enter your OpenAI API key in the sidebar first.")
        else:
            with st.spinner("Asking OpenAI for tailored suggestions..."):
                result = generate_ai_suggestions(resume_text, jd_text, analysis, api_key)
                st.session_state[ai_key] = result

    if ai_key in st.session_state:
        result = st.session_state[ai_key]
        if "error" in result:
            st.error(result["error"])
        else:
            if result.get("overall_verdict"):
                st.info(result["overall_verdict"])

            if result.get("improvement_suggestions"):
                st.markdown("**Suggestions**")
                for s in result["improvement_suggestions"]:
                    st.markdown(f"- {s}")

            if result.get("rewrite_examples"):
                st.markdown("**Example rewrites**")
                for ex in result["rewrite_examples"]:
                    st.markdown(f"❌ *{ex.get('before', '')}*")
                    st.markdown(f"✅ {ex.get('after', '')}")
                    st.markdown("")

            if result.get("keyword_recommendations"):
                st.markdown("**Keyword recommendations**")
                st.markdown(render_pills(result["keyword_recommendations"], "pill-missing"), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚙️ Setup")
    api_key = st.text_input("OpenAI API key", type="password", help="Required only for the AI-generated suggestions feature. Skill matching and scoring work without it.")
    st.caption("Your key is used only for this session and is never stored.")

    st.markdown("---")
    st.markdown("### How scoring works")
    st.caption(
        "**Match score** = 65% skill overlap with the job description "
        "+ 35% semantic similarity (TF-IDF cosine similarity).\n\n"
        "**ATS score** is a separate rule-based check for formatting and "
        "parsing pitfalls (contact info, length, layout)."
    )

    st.markdown("---")
    st.caption("Built with Python, Streamlit, scikit-learn, spaCy, and the OpenAI API.")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("📄 Smart Resume Analyzer")
st.caption("Upload a resume, compare it against a job description, and get a match score, skill gap analysis, and AI-powered improvement suggestions.")

tab_single, tab_batch = st.tabs(["🔍 Single Resume", "📊 Batch Mode (Rank Multiple)"])

# ---------------------------------------------------------------------------
# SINGLE RESUME MODE
# ---------------------------------------------------------------------------
with tab_single:
    st.markdown("#### 1. Upload resume")
    resume_file = st.file_uploader(
        "Upload resume (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        key="single_resume_file",
    )

    st.markdown("#### 2. Provide job description")
    jd_text_single = get_jd_text("single")

    st.markdown("#### 3. Analyze")
    analyze_clicked = st.button("Analyze Resume", type="primary", key="single_analyze_btn")

    if analyze_clicked:
        if resume_file is None:
            st.error("Please upload a resume PDF/DOCX/TXT first.")
        elif not jd_text_single or not jd_text_single.strip():
            st.error("Please provide a job description (paste or upload).")
        else:
            with st.spinner("Extracting text and analyzing..."):
                try:
                    resume_bytes = resume_file.getvalue()
                    resume_text = extract_text(resume_bytes, resume_file.name)
                    page_count = get_page_count(resume_bytes, resume_file.name)

                    if not resume_text.strip():
                        st.error("Could not extract any text from this resume. It may be a scanned image — try a text-based PDF or DOCX.")
                    else:
                        analysis = analyze_resume(resume_text, jd_text_single, page_count)
                        st.session_state["single_resume_text"] = resume_text
                        st.session_state["single_jd_text"] = jd_text_single
                        st.session_state["single_analysis"] = analysis
                except ValueError as e:
                    st.error(str(e))

    if "single_analysis" in st.session_state:
        st.markdown("---")
        st.markdown("### Results")
        render_analysis(
            st.session_state["single_resume_text"],
            st.session_state["single_jd_text"],
            st.session_state["single_analysis"],
            candidate_name=resume_file.name if resume_file else "Candidate",
            api_key=api_key,
            key_prefix="single",
        )

# ---------------------------------------------------------------------------
# BATCH MODE
# ---------------------------------------------------------------------------
with tab_batch:
    st.markdown("#### 1. Upload multiple resumes")
    batch_files = st.file_uploader(
        "Upload resumes (PDF, DOCX, or TXT) — select multiple files",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="batch_resume_files",
    )

    st.markdown("#### 2. Provide job description")
    jd_text_batch = get_jd_text("batch")

    st.markdown("#### 3. Rank candidates")
    rank_clicked = st.button("Analyze & Rank All", type="primary", key="batch_analyze_btn")

    if rank_clicked:
        if not batch_files:
            st.error("Please upload at least one resume.")
        elif not jd_text_batch or not jd_text_batch.strip():
            st.error("Please provide a job description (paste or upload).")
        else:
            results = []
            progress = st.progress(0, text="Starting analysis...")
            for i, f in enumerate(batch_files):
                progress.progress((i) / len(batch_files), text=f"Analyzing {f.name}...")
                try:
                    resume_bytes = f.getvalue()
                    resume_text = extract_text(resume_bytes, f.name)
                    page_count = get_page_count(resume_bytes, f.name)
                    if not resume_text.strip():
                        results.append({"name": f.name, "error": "No extractable text (possibly a scanned image)."})
                        continue
                    analysis = analyze_resume(resume_text, jd_text_batch, page_count)
                    results.append({
                        "name": f.name,
                        "resume_text": resume_text,
                        "analysis": analysis,
                    })
                except ValueError as e:
                    results.append({"name": f.name, "error": str(e)})
            progress.progress(1.0, text="Done.")
            progress.empty()

            st.session_state["batch_results"] = results
            st.session_state["batch_jd_text"] = jd_text_batch

    if "batch_results" in st.session_state:
        results = st.session_state["batch_results"]
        valid_results = [r for r in results if "error" not in r]
        failed_results = [r for r in results if "error" in r]

        if failed_results:
            with st.expander(f"⚠️ {len(failed_results)} file(s) failed to process"):
                for r in failed_results:
                    st.markdown(f"**{r['name']}**: {r['error']}")

        if valid_results:
            ranked = sorted(valid_results, key=lambda r: r["analysis"]["match_score"], reverse=True)

            st.markdown("---")
            st.markdown("### 🏆 Ranked Candidates")

            table_data = []
            for i, r in enumerate(ranked):
                a = r["analysis"]
                table_data.append({
                    "Rank": i + 1,
                    "Candidate": r["name"],
                    "Match Score": a["match_score"],
                    "Skill Overlap %": a["skill_overlap_ratio"],
                    "ATS Score": a["ats_score"],
                    "Matched Skills": len(a["matched_skills"]),
                    "Missing Skills": len(a["missing_skills"]),
                })
            df = pd.DataFrame(table_data)

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Match Score": st.column_config.ProgressColumn(
                        "Match Score", min_value=0, max_value=100, format="%.1f"
                    ),
                    "ATS Score": st.column_config.ProgressColumn(
                        "ATS Score", min_value=0, max_value=100, format="%.0f"
                    ),
                },
            )

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download ranking as CSV", csv, "resume_ranking.csv", "text/csv")

            st.markdown("---")
            st.markdown("### Candidate Drill-Down")
            candidate_names = [r["name"] for r in ranked]
            selected_name = st.selectbox("Select a candidate to view full analysis", candidate_names, key="batch_candidate_select")

            selected = next(r for r in ranked if r["name"] == selected_name)
            render_analysis(
                selected["resume_text"],
                st.session_state["batch_jd_text"],
                selected["analysis"],
                candidate_name=selected_name,
                api_key=api_key,
                key_prefix=f"batch_{selected_name}",
            )
