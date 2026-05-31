"""
output.py
---------
Rank scored candidates, format for display, print to console, save to JSON.
"""

import json
from pathlib import Path

import config


def rank_and_format(scored: list[dict]) -> list[dict]:
    """Sort by score descending, return top TOP_N with clean output fields only."""
    scored.sort(key=lambda x: x["score"], reverse=True)

    results = []
    for i, c in enumerate(scored[:config.TOP_N]):
        results.append({
            "rank":             i + 1,
            "id":               c["id"],
            "name":             c["name"],
            "title":            c["title"],
            "company":          c["company"],
            "industry":         c["industry"] or "—",
            "location":         c["location"],
            "years_experience": c["years_experience"],
            "skills":           c["skills"],
            "score":            c["score"],
            "reason":           c["reason"],
        })

    return results


def print_results(results: list[dict], requirement: str) -> None:
    sep = "─" * 68
    print(f"\n{sep}")
    print(f"  Top {len(results)} Candidates")
    print(f"  Requirement: {requirement}")
    print(sep)

    for r in results:
        exp = f"{r['years_experience']} yrs" if r["years_experience"] is not None else "exp unknown"
        skills_str = ", ".join(r["skills"][:4]) or "—"
        print(
            f"\n#{r['rank']:02d}  {r['name']}  ({r['title']})"
            f"\n    {r['company'] or '—'}  ·  {r['industry']}  ·  {r['location']}  ·  {exp}"
            f"\n    Skills: {skills_str}"
            f"\n    Score : {r['score']}/100"
            f"\n    Reason: {r['reason']}"
        )

    print(f"\n{sep}\n")


def save_results(results: list[dict], path: str = "results.json") -> None:
    Path(path).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[output] Results saved → {path}")