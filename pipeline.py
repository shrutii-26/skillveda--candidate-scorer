"""
pipeline.py — returns ALL scored candidates, UI handles pagination
"""

import config
from preprocessor import load_and_preprocess
from requirement_parser import parse_requirement
from retrieval import retrieve_shortlist
from scorer import score_shortlist

_candidates_cache = None


def get_candidates(dataset_path: str = "candidates.json") -> list[dict]:
    global _candidates_cache
    if _candidates_cache is None:
        _candidates_cache = load_and_preprocess(dataset_path)
    return _candidates_cache


def run_pipeline(
    requirement: str, progress_callback=None, dataset_path: str = "candidates.json"
) -> dict:
    """
    Returns ALL scored candidates ranked by score.
    UI decides how many to show and handles load-more.
    """
    candidates = get_candidates(dataset_path)

    if progress_callback:
        progress_callback("status", "Parsing requirement...")
    req = parse_requirement(requirement)

    if progress_callback:
        progress_callback("status", "Searching candidates...")
    shortlist = retrieve_shortlist(candidates, req, broaden=False)
    broadened = False

    if len(shortlist) < config.BROADENING_THRESHOLD:
        shortlist = retrieve_shortlist(candidates, req, broaden=True)
        broadened = True

    if not shortlist:
        return {
            "req": req,
            "all_results": [],
            "broadened": broadened,
            "total_scored": 0,
            "above_threshold": 0,
        }

    if progress_callback:
        progress_callback("status", f"Scoring {len(shortlist)} candidates with AI...")

    def score_progress(i, total, name):
        if progress_callback:
            progress_callback("scoring", i, total, name)

    scored = score_shortlist(shortlist, req, progress_callback=score_progress)
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Add rank across all results
    for i, c in enumerate(scored):
        c["rank"] = i + 1

    above_threshold = sum(1 for c in scored if c["score"] >= config.MIN_SCORE_THRESHOLD)

    return {
        "req": req,
        "all_results": scored,  # full ranked list, UI slices it
        "broadened": broadened,
        "total_scored": len(scored),
        "above_threshold": above_threshold,
    }
