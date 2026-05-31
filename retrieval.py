"""
retrieval.py
------------
Fast heuristic scoring — no LLM involved.
Reduces 500 candidates to ~80 before any LLM calls.

Scoring breakdown (weights sum to 1.0):
  Title match     35%   — most important signal
  Skill overlap   30%   — exact lowercase match against 47-skill vocabulary
  Location match  15%   — substring match handles "delhi ncr" / "delhi" edge cases
  Industry match  10%   — missing industry is neutral, not a penalty
  Experience      10%   — 1-year tolerance below minimum

Missing data is never a hard disqualifier:
  - missing industry  → neutral score (0.05)
  - missing/empty skills → 0 overlap but candidate stays in
  - missing experience → neutral (0.05)
  - location always present in this dataset
"""

import re

import config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _token_overlap(query: str, target: str) -> float:
    """
    Fraction of non-empty tokens in `query` that appear in `target`.
    e.g. query="customer success manager", target="senior customer success manager"
    → tokens_q = {customer, success, manager}
    → tokens_t = {senior, customer, success, manager}
    → overlap = 3/3 = 1.0
    """
    tokens_q = set(re.split(r"\W+", query)) - {""}
    tokens_t = set(re.split(r"\W+", target)) - {""}
    if not tokens_q:
        return 0.0
    return len(tokens_q & tokens_t) / len(tokens_q)


def _location_matches(req_locations: list[str], candidate_location: str) -> bool:
    """
    Substring match in both directions to handle:
      - req: "delhi ncr"  candidate: "delhi ncr"  → True
      - req: "delhi"      candidate: "delhi ncr"  → True  (user typed short form)
      - req: "gurgaon"    candidate: "gurgaon"    → True
    """
    for req_loc in req_locations:
        if req_loc in candidate_location or candidate_location in req_loc:
            return True
    return False


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------


def _preliminary_score(candidate: dict, req: dict) -> float:
    score = 0.0

    req_title = req.get("title") or ""
    req_skills = req.get("skills") or []
    req_locs = req.get("locations") or []
    req_inds = req.get("industries") or []
    req_min_exp = req.get("min_experience")  # int or None

    c_title = candidate["_title"]
    c_skills = candidate["_skills"]  # already lowercased list
    c_location = candidate["_location"]  # already lowercased
    c_industry = candidate["_industry"]  # already lowercased, "" if null
    c_years = candidate["_years"]  # float or None

    # --- Title match (0.0 – 0.35) ---
    title_sim = _token_overlap(req_title, c_title)
    score += title_sim * 0.35

    # --- Skill overlap (0.0 – 0.30) ---
    if req_skills:
        matched = sum(1 for s in req_skills if s in c_skills)
        score += (matched / len(req_skills)) * 0.30
    else:
        score += 0.10  # no skills specified → neutral bonus

    # --- Location match (0.0 – 0.15) ---
    if req_locs:
        if _location_matches(req_locs, c_location):
            score += 0.15
        elif "remote" in req_locs:
            score += 0.05  # remote mentioned → partial credit for any location
    else:
        score += 0.08  # location not specified → neutral

    # --- Industry match (0.0 – 0.10) ---
    if req_inds:
        if c_industry:
            if any(ri in c_industry or c_industry in ri for ri in req_inds):
                score += 0.10
            # else: wrong industry → 0
        else:
            score += 0.05  # industry unknown → neutral, not penalized
    else:
        score += 0.05  # not specified → neutral

    # --- Experience (0.0 – 0.10) ---
    if req_min_exp is not None:
        if c_years is not None:
            if c_years >= req_min_exp:
                score += 0.10
            elif c_years >= req_min_exp - 1:
                score += 0.05  # 1 year short → partial
            # else: clearly under → 0
        else:
            score += 0.05  # experience unknown → neutral
    else:
        score += 0.05  # not specified → neutral

    return round(score, 4)


# ---------------------------------------------------------------------------
# Shortlist builder
# ---------------------------------------------------------------------------


def retrieve_shortlist(
    candidates: list[dict],
    req: dict,
    broaden: bool = False,
) -> list[dict]:
    """
    Score all candidates and return the top SHORTLIST_SIZE above threshold.
    broaden=True halves the threshold to let more candidates through.
    """
    threshold = (
        (config.MIN_RETRIEVAL_SCORE / 2) if broaden else config.MIN_RETRIEVAL_SCORE
    )

    scored = []
    for c in candidates:
        ps = _preliminary_score(c, req)
        if ps >= threshold:
            scored.append({**c, "_prelim_score": ps})

    scored.sort(key=lambda x: x["_prelim_score"], reverse=True)
    shortlist = scored[: config.SHORTLIST_SIZE]

    print(
        f"[retrieval] {len(shortlist)} candidates shortlisted "
        f"(threshold={threshold}, broaden={broaden})."
    )
    return shortlist
