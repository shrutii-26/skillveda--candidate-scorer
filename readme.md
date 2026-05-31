# Search-and-Score Candidate Finder

A recruiting tool that takes a plain-English hiring requirement, searches a dataset of 500 candidates, and returns the top matches ranked by AI-generated fit scores — each with a short explanation.

Built for the SkillVeda Junior Engineering Assignment.

---

## Demo

### Input Screen

![Dashboard](https://raw.githubusercontent.com/shrutii-26/skillveda--candidate-scorer/main/dashboard.webp)

### Results

![Results](https://raw.githubusercontent.com/shrutii-26/skillveda--candidate-scorer/main/result.webp)

---

## How It Works

The system runs a two-stage pipeline:

**Stage 1 — Fast Retrieval (no LLM)**

All 500 candidates are scored with a lightweight heuristic before any LLM calls are made. The score is a weighted sum across five signals:

| Signal        | Weight | Notes                                                    |
| ------------- | ------ | -------------------------------------------------------- |
| Title match   | 35%    | Token overlap between required title and candidate title |
| Skill overlap | 30%    | Exact match against candidate's skill list               |
| Location      | 15%    | Substring match — "Delhi" correctly hits "Delhi NCR"     |
| Industry      | 10%    | Missing industry is neutral, not a penalty               |
| Experience    | 10%    | 1-year tolerance below minimum; unknown is neutral       |

The top 80 candidates by heuristic score are shortlisted for LLM scoring. This avoids calling the LLM 500 times per query.

**Stage 2 — LLM Scoring**

Each shortlisted candidate is scored by `llama-3.3-70b-versatile` via Groq. The model receives the parsed requirement and the candidate profile, and returns a score (0–100) plus a 1–2 sentence reason. The prompt explicitly instructs the model to score relative to what's realistically available in the dataset — so if a required skill is absent from the entire pool, candidates aren't all penalized to 40.

**Requirement Parsing**

Before retrieval, the free-text requirement is parsed by the same LLM into a structured JSON object with fields: `title`, `min_experience`, `industries`, `locations`, `skills`. The parser is given the exact list of location and industry values present in the dataset so it maps "fintech" → "financial services" and "Delhi" → "delhi ncr" correctly.

**Search Broadening**

If fewer than 10 candidates pass the initial retrieval filter, the system automatically lowers the threshold and retries once. It never loops — one broadening pass maximum.

**Load More**

All scored candidates are stored in session state. The UI shows the top 20 by default, with a "Load More" button that reveals 10 additional results at a time.

---

## How Missing Data Is Handled

The dataset has real-world gaps: 76 candidates have no industry, 68 have no years_experience, 30 have no company. The system treats all missing values as **unknown**, never as a disqualifier.

Concretely:

```python
industry = (candidate.get("industry") or "").lower().strip()   # null → ""
years    = float(raw_exp) if raw_exp is not None else None      # null → None, NOT 0
skills   = [s.lower() for s in (candidate.get("skills") or [])] # null → []
```

`years_experience = 0` is treated as a real value (someone with no experience), not as missing — the code checks `if raw_exp is not None`, not `if raw_exp`.

In retrieval scoring, missing fields receive a small neutral score (0.05) instead of zero. In LLM scoring, the prompt explicitly states: _"Missing industry/experience/skills = unknown, treat neutrally."_

---

## Project Structure

```
candidate_finder/
├── app.py                   ← Streamlit UI
├── pipeline.py              ← orchestrates the full flow
├── config.py                ← Groq API key (from .env), model, thresholds
├── preprocessor.py          ← loads + normalizes candidates.json once at startup
├── requirement_parser.py    ← LLM: free text → structured JSON
├── retrieval.py             ← fast heuristic shortlisting (500 → ~80)
├── scorer.py                ← LLM scoring with retry + backoff
├── requirements.txt
├── .env                     ← GROQ_API_KEY=gsk-... (you create this)
└── candidates.json
```

---

## Setup & Run

```bash
# 1. Install dependencies
pip install openai python-dotenv streamlit

# 2. Create .env in the project folder
echo "GROQ_API_KEY=gsk-your-key-here" > .env

# 3. Run
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Sample Run

**Requirement:** `Customer Success Manager, 3+ years, fintech / financial services background, in Bangalore or Delhi NCR`

**Pipeline output:**

- 500 candidates searched
- 80 shortlisted by heuristic scoring
- 14 scored ≥ 50 by LLM
- Top 20 shown (14 strong matches + 6 next-best filled in)

Top results included candidates with direct CSM titles and financial services backgrounds in Bangalore and Delhi NCR, scoring 70–85. Candidates with matching title but wrong location or industry scored 45–65. Candidates with no title or location match scored below 45 and appeared only in the fill slots.

---

## One Thing I'd Improve With More Time

**Semantic skill matching.** Right now skills are matched by exact lowercase string — "churn reduction" only hits if the candidate has exactly that string. A candidate who lists "customer retention" or "NRR management" would be missed. With more time I'd embed both the requirement skills and candidate skills using a small embedding model and match by cosine similarity. This would also handle synonyms like "Salesforce" vs "CRM" gracefully, without needing a hand-curated synonym list.
