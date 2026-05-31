"""
app.py — Streamlit UI for Search-and-Score Candidate Finder
Run: streamlit run app.py
"""
import streamlit as st
import json
import config
from pipeline import run_pipeline

st.set_page_config(page_title="Candidate Finder", page_icon="🔍", layout="wide")

# ---------------------------------------------------------------------------
# Styles — explicit colors on every element so dark/light theme both work
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .candidate-card {
        background: #1e2130;
        border: 1px solid #2e3250;
        border-left: 4px solid #4f8ef7;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
        color: #e8eaf6;
    }
    .c-name   { color: #ffffff; font-size: 1.05rem; font-weight: 700; }
    .c-title  { color: #b0bec5; font-size: 0.95rem; }
    .c-meta   { color: #90a4ae; font-size: 0.85rem; margin-top: 5px; }
    .c-reason { color: #cfd8dc; font-size: 0.88rem; margin-top: 8px; }
    .score-high { color: #69f0ae; font-weight: 700; font-size: 1.1rem; }
    .score-mid  { color: #ffd740; font-weight: 700; font-size: 1.1rem; }
    .score-low  { color: #ff5252; font-weight: 700; font-size: 1.1rem; }
    .rank-badge {
        background: #4f8ef7; color: #fff;
        border-radius: 50%; padding: 3px 9px;
        font-weight: 700; margin-right: 8px; font-size: 0.9rem;
    }
    .skill-tag {
        background: #263064; color: #82b1ff;
        border-radius: 12px; padding: 2px 10px;
        font-size: 0.78rem; margin: 2px; display: inline-block;
    }
    .warn-box {
        background: #2c2400; border: 1px solid #f59e0b;
        border-radius: 6px; padding: 10px 16px; margin-bottom: 12px;
        color: #ffd54f;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🔍 Search-and-Score Candidate Finder")
st.markdown("Enter a hiring requirement in plain English. The system searches 500 candidates and ranks the best matches using AI.")

if not config.GROQ_API_KEY:
    st.error("⚠️ GROQ_API_KEY not found. Add it to your `.env` file and restart.")
    st.stop()

st.markdown("---")

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
for key, default in [
    ("req_input", ""),
    ("all_results", None),
    ("search_meta", None),
    ("shown_count", config.TOP_N),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------------------------------------------------------------------
# Example requirements
# Clicking copies text into the text area widget via its key directly
# ---------------------------------------------------------------------------
EXAMPLES = [
    "Customer Success Manager, 3+ years, fintech, Bangalore or Delhi NCR",
    "Backend Engineer, Python and AWS, Mumbai",
    "Data Analyst, 2+ years, financial services",
    "Product Manager, SaaS, remote",
    "Senior Software Engineer, 5+ years, Kubernetes, Hyderabad or Bangalore",
    "Sales Manager, 4+ years, retail or e-commerce, Mumbai",
]

with st.expander("💡 Example requirements — click any to use"):
    cols = st.columns(2)
    for i, ex in enumerate(EXAMPLES):
        if cols[i % 2].button(ex, key=f"ex_{i}", use_container_width=True):
            # Write directly to the widget's session state key
            st.session_state["req_input"] = ex

# ---------------------------------------------------------------------------
# Input row
# ---------------------------------------------------------------------------
col1, col2 = st.columns([3, 1])
with col1:
    requirement = st.text_area(
        "Hiring Requirement",
        placeholder="e.g. Product Manager, SaaS, 3+ years, Mumbai or remote",
        height=90,
        label_visibility="collapsed",
        key="req_input",        # bound to session state — example clicks update this
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    search_btn = st.button("🔍 Find Candidates", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Search — runs pipeline, stores ALL results in session state
# ---------------------------------------------------------------------------
if search_btn and requirement.strip():
    st.session_state["all_results"]  = None
    st.session_state["shown_count"]  = config.TOP_N
    st.session_state["search_meta"]  = None

    status_text  = st.empty()
    progress_bar = st.progress(0)
    scoring_text = st.empty()

    def progress_callback(*args):
        if args[0] == "status":
            status_text.info(f"⏳ {args[1]}")
        elif args[0] == "scoring":
            i, total, name = args[1], args[2], args[3]
            progress_bar.progress(int(i / total * 100))
            scoring_text.caption(f"Scoring {i}/{total}: {name}")

    try:
        result = run_pipeline(requirement.strip(), progress_callback=progress_callback)
    except Exception as e:
        st.error(f"Something went wrong: {e}")
        st.stop()

    status_text.empty()
    progress_bar.empty()
    scoring_text.empty()

    st.session_state["all_results"] = result["all_results"]
    st.session_state["search_meta"] = {
        "req":             result["req"],
        "broadened":       result["broadened"],
        "total_scored":    result["total_scored"],
        "above_threshold": result["above_threshold"],
        "requirement":     requirement.strip(),
    }

elif search_btn:
    st.warning("Please enter a hiring requirement first.")

# ---------------------------------------------------------------------------
# Results display — reads from session state, supports load more
# ---------------------------------------------------------------------------
if st.session_state["all_results"] is not None:
    all_results = st.session_state["all_results"]
    meta        = st.session_state["search_meta"]
    shown       = st.session_state["shown_count"]

    if not all_results:
        st.warning("No candidates found. Try a broader requirement.")
        st.stop()

    # Summary metrics
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Candidates Searched", 500)
    m2.metric("Shortlisted & Scored", meta["total_scored"])
    m3.metric("Strong Matches (≥50)", meta["above_threshold"])
    m4.metric("Showing Now", min(shown, len(all_results)))

    if meta["broadened"]:
        st.markdown('<div class="warn-box">⚠️ Fewer than 10 candidates matched initial filters — search was broadened automatically.</div>', unsafe_allow_html=True)
    if meta["above_threshold"] < config.TOP_N:
        st.markdown(
            f'<div class="warn-box">ℹ️ Only <b>{meta["above_threshold"]}</b> candidates scored ≥50. '
            f'Showing next best matches to fill results.</div>',
            unsafe_allow_html=True,
        )

    # Parsed requirement breakdown
    req = meta["req"]
    with st.expander("🔎 How your requirement was interpreted"):
        ca, cb = st.columns(2)
        with ca:
            st.markdown(f"**Title:** {req.get('title','—').title()}")
            st.markdown(f"**Min Experience:** {req.get('min_experience') or 'Not specified'} years")
        with cb:
            st.markdown(f"**Locations:** {', '.join(req.get('locations') or []) or 'Not specified'}")
            st.markdown(f"**Industries:** {', '.join(req.get('industries') or []) or 'Not specified'}")
            st.markdown(f"**Skills:** {', '.join(req.get('skills') or []) or 'Not specified'}")

    # Candidate cards
    visible = all_results[:shown]
    st.markdown(f"### Top {len(visible)} Candidates")

    for c in visible:
        score       = c["score"]
        score_class = "score-high" if score >= 70 else ("score-mid" if score >= 45 else "score-low")
        score_emoji = "🟢" if score >= 70 else ("🟡" if score >= 45 else "🔴")
        exp_str     = f"{c['years_experience']} yrs" if c["years_experience"] is not None else "Exp unknown"
        skills_html = "".join(f'<span class="skill-tag">{s}</span>' for s in c["skills"][:5]) or "—"

        st.markdown(f"""
        <div class="candidate-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <span class="rank-badge">#{c['rank']}</span>
                    <span class="c-name">{c['name']}</span>
                    <span class="c-title"> · {c['title']}</span>
                </div>
                <div class="{score_class}">{score_emoji} {score}/100</div>
            </div>
            <div class="c-meta">
                🏢 {c['company'] or '—'} &nbsp;|&nbsp;
                🏭 {c['industry'] or 'Industry unknown'} &nbsp;|&nbsp;
                📍 {c['location']} &nbsp;|&nbsp;
                🗓 {exp_str}
            </div>
            <div style="margin-top:8px;">{skills_html}</div>
            <div class="c-reason">💬 {c['reason']}</div>
        </div>
        """, unsafe_allow_html=True)

    # Load more button
    st.markdown("")
    remaining = len(all_results) - shown
    if remaining > 0:
        load_n = min(10, remaining)
        if st.button(f"⬇️ Load {load_n} More Candidates ({remaining} remaining)", use_container_width=True):
            st.session_state["shown_count"] += 10
            st.rerun()
    else:
        st.info(f"✅ All {len(all_results)} scored candidates shown.")

    # Download full results
    st.markdown("---")
    clean = [{
        "rank": c["rank"], "name": c["name"], "title": c["title"],
        "company": c["company"], "industry": c["industry"],
        "location": c["location"], "years_experience": c["years_experience"],
        "skills": c["skills"], "score": c["score"], "reason": c["reason"],
    } for c in all_results]

    st.download_button(
        label="⬇️ Download All Results (JSON)",
        data=json.dumps(clean, indent=2, ensure_ascii=False),
        file_name="candidate_results.json",
        mime="application/json",
    )