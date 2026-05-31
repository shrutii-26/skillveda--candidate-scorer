"""
preprocessor.py
---------------
Load candidates.json and normalize every field once at startup.
All downstream code works on the returned list — never on raw JSON.

Normalization decisions based on the actual dataset:
  - title      : always present, Title Case → lowercase
  - company    : 30 nulls → default ""
  - industry   : 76 nulls → default ""
  - location   : always present, clean 10-value set → lowercase
  - skills     : always a list (never null), Title Case → lowercase
  - years_exp  : 68 nulls + 0 is a real value → None when missing, float otherwise
"""

import json
from pathlib import Path


def _normalize_candidate(c: dict) -> dict:
    # ---- safe string fields ----
    title = c["title"].lower().strip()  # always present
    company = (c.get("company") or "").lower().strip()  # 30 nulls
    industry = (c.get("industry") or "").lower().strip()  # 76 nulls
    location = c["location"].lower().strip()  # always present
    # "delhi ncr" after lower — intentional, matches user typing "delhi"

    # ---- skills: Title Case → lowercase ----
    raw_skills = c.get("skills") or []
    skills = [s.lower().strip() for s in raw_skills if isinstance(s, str)]

    # ---- experience: None means unknown, 0 means genuinely zero ----
    raw_exp = c.get("years_experience")
    try:
        years = float(raw_exp) if raw_exp is not None else None
    except (ValueError, TypeError):
        years = None

    # ---- search blob: one string to run keyword checks against ----
    search_text = " ".join(
        filter(
            None,
            [
                title,
                industry,
                location,
                company,
                " ".join(skills),
            ],
        )
    )

    return {
        # --- originals (used in output, never for matching) ---
        "id": c["id"],
        "name": c["name"],
        "title": c["title"],
        "company": c.get("company") or "",
        "industry": c.get("industry") or "",
        "location": c["location"],
        "skills": raw_skills,
        "years_experience": c.get("years_experience"),
        # --- normalized (used for matching, prefixed with _ ) ---
        "_title": title,
        "_company": company,
        "_industry": industry,
        "_location": location,
        "_skills": skills,
        "_years": years,
        "_search_text": search_text,
    }


def load_and_preprocess(path: str) -> list[dict]:
    """
    Call this once at startup. Returns a list of normalized candidate dicts.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))

    candidates = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue  # skip any malformed entries silently
        candidates.append(_normalize_candidate(entry))

    print(f"[preprocessor] {len(candidates)} candidates loaded from '{path}'.")
    return candidates
