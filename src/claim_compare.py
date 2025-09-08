"""Utilities for comparing patent claims.

The functions in this module help build a simple claim chart and compute
rough similarity scores using token-based matching from
:mod:`rapidfuzz`.
"""

from __future__ import annotations

from typing import Dict, List, Set

from rapidfuzz import fuzz

from .collect_lens import split_claim_elements


def normalize_term(s: str) -> str:
    """Normalize terms for comparison."""
    import re

    s = s.lower()
    s = re.sub(r"[^a-z0-9\s\-_/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def claim_elements(claim_text: str) -> List[str]:
    """Split a claim into normalized elements."""
    return [normalize_term(t) for t in split_claim_elements(claim_text)]


def chart_and_diff(my_claim: str, prior_claims: List[str]) -> List[Dict]:
    """Compare *my_claim* against *prior_claims*.

    Returns a list of dictionaries sorted by similarity containing
    overlapping, missing and extra elements for each prior claim.
    """
    my_elems: Set[str] = set(claim_elements(my_claim))
    rows = []
    for pc in prior_claims:
        pe = set(claim_elements(pc))
        overlap = my_elems & pe
        missing = my_elems - pe
        extra = pe - my_elems
        sim = fuzz.token_set_ratio(" ".join(my_elems), " ".join(pe))
        rows.append(
            {
                "sim": sim,
                "overlap": list(overlap)[:10],
                "missing": list(missing)[:10],
                "extra": list(extra)[:10],
            }
        )
    return sorted(rows, key=lambda x: x["sim"], reverse=True)[:5]
