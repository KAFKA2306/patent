"""Utilities for retrieving patent data from The Lens API.

This module provides helper functions to query the Lens patent API and
return simplified patent information. An access token is expected in the
``LENS_API_TOKEN`` environment variable.
"""

from __future__ import annotations

import json
import os
from typing import List, Dict

import requests
from rapidfuzz import fuzz

LENS_ENDPOINT = "https://api.lens.org/patent/search"


def split_claim_elements(text: str) -> List[str]:
    """Split a claim into coarse elements using simple heuristics."""
    import re

    seps = r"(;|, and |, or | comprising | wherein | wherein the | including )"
    parts = [
        p.strip(" ,;.")
        for p in re.split(seps, text, flags=re.I)
        if p and not re.match(seps, p, re.I)
    ]
    return [p for p in parts if len(p.split()) >= 3]


def first_independent_claim(claims: List[str]) -> str:
    """Return the first independent claim from a list of claim strings."""
    import re

    for c in claims:
        if re.search(r"independent|claim\s*1", c, flags=re.I) or (
            "dependent" not in c.lower()
        ):
            return c
    return claims[0] if claims else ""


def similarity(a: str, b: str) -> int:
    """Return a rough similarity score between two texts."""
    return fuzz.token_set_ratio(a, b)


def search_lens(query: str, size: int = 50, my_invention: str = "") -> List[Dict]:
    """Query The Lens API and return simplified patent records.

    Parameters
    ----------
    query:
        Search expression supported by Lens.
    size:
        Number of records to request.
    my_invention:
        Optional description of the user's invention. If supplied, a
        similarity score against each independent claim is computed.
    """
    payload = {
        "query": query,
        "size": size,
        "include": [
            "lens_id",
            "title",
            "abstract",
            "claims",
            "applicants",
            "cpc",
            "date_published",
        ],
    }
    resp = requests.post(
        LENS_ENDPOINT,
        headers={
            "Authorization": f"Bearer {os.getenv('LENS_API_TOKEN')}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
    ).json()

    docs = resp.get("data", [])
    table = []
    for d in docs:
        claims = d.get("claims", []) or []
        ic = first_independent_claim(claims)
        elems = split_claim_elements(ic)
        score = similarity(my_invention, ic) if my_invention else 0
        table.append(
            {
                "lens_id": d["lens_id"],
                "title": d.get("title", "")[:80],
                "date": d.get("date_published", ""),
                "score": score,
                "elements": elems[:8],
            }
        )

    return sorted(table, key=lambda x: x["score"], reverse=True)
