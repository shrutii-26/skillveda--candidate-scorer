"""
scorer.py — LLM scoring with retry + exponential backoff for rate limits
"""

import json
import time
from openai import OpenAI, RateLimitError
import config

client = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)

SYSTEM_PROMPT = """You are a recruiter scoring candidate fit for a role.

Given a hiring requirement and a candidate profile, output ONLY valid JSON:

{
  "score": <integer 0-100>,
  "reason": "<1-2 sentences>"
}

Scoring guide:
  85-100 : Strong fit — title matches, meets/exceeds experience, good skill overlap, right location/industry
  65-84  : Good fit — matches most criteria, 1-2 minor gaps
  45-64  : Partial fit — meaningful alignment on 2-3 criteria but clear gaps
  20-44  : Weak fit — only 1-2 criteria match
  0-19   : Poor fit — barely anything aligns

Important rules:
- Score relative to how good this candidate is compared to what's realistically available
- If a required skill is rare or absent from the market, do NOT heavily penalize candidates who match everything else well
- Missing industry → unknown, treat neutrally
- Missing experience → unknown, treat neutrally
- Empty skills → unknown, treat neutrally
- Prioritize: title match > experience > location > industry > skills
- Reason: be specific — mention what matches AND what's missing, max 2 sentences
- Output ONLY the JSON, nothing else
"""


def _build_message(req: dict, candidate: dict) -> str:
    profile = {
        "title": candidate["title"],
        "company": candidate["company"],
        "industry": candidate["industry"] or "not specified",
        "location": candidate["location"],
        "years_experience": (
            candidate["years_experience"]
            if candidate["years_experience"] is not None
            else "not specified"
        ),
        "skills": candidate["skills"] if candidate["skills"] else "not specified",
    }
    return f"Requirement:\n{json.dumps(req, indent=2)}\n\nCandidate:\n{json.dumps(profile, indent=2)}"


def _parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def score_candidate(req: dict, candidate: dict) -> dict:
    """Call LLM with up to 4 retries on rate limit errors (exponential backoff)."""
    wait = 5  # seconds, doubles each retry
    for attempt in range(4):
        try:
            response = client.chat.completions.create(
                model=config.GROQ_MODEL_FAST,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_message(req, candidate)},
                ],
            )
            result = _parse(response.choices[0].message.content)
            return {
                "score": max(0, min(100, int(result["score"]))),
                "reason": result.get("reason", "").strip(),
            }
        except RateLimitError:
            if attempt < 3:
                time.sleep(wait)
                wait *= 2  # 5s → 10s → 20s → 40s
            else:
                # All retries exhausted — fall through to fallback
                break
        except Exception:
            break  # non-rate-limit error, go straight to fallback

    fallback = int(candidate.get("_prelim_score", 0) * 100)
    return {
        "score": fallback,
        "reason": "Auto-scored from retrieval heuristic (LLM rate limit reached — try again in a moment).",
    }


def score_shortlist(
    shortlist: list[dict], req: dict, progress_callback=None
) -> list[dict]:
    results = []
    total = len(shortlist)
    for i, candidate in enumerate(shortlist, 1):
        if progress_callback:
            progress_callback(i, total, candidate["name"])
        scored = score_candidate(req, candidate)
        results.append({**candidate, **scored})
        time.sleep(0.05)  # small courtesy delay between calls
    return results
