"""Retrieve patent documents from the EPO OPS service.

The :mod:`patent_client` package is used to access EPO's OPS API. API
credentials are read from ``PATENT_CLIENT_EPO_API_KEY`` and
``PATENT_CLIENT_EPO_SECRET`` environment variables.
"""

from __future__ import annotations

import os
from typing import Dict, List

from patent_client import PatentSearchClient


def parse_conditions(text: str) -> Dict[str, List]:
    """Extract simple process conditions from claim text."""
    import re

    o2 = re.findall(r"(oxygen|O2)[^0-9]{0,10}(\d+\.?\d*)\s*(Pa|%|sccm)", text, flags=re.I)
    temp = re.findall(r"(\d{2,3})\s*°?C", text)
    layers = re.findall(r"(multi[-\s]?layer|(\d+)\s*layers?)", text, flags=re.I)
    return {"o2": o2, "temp_C": temp, "layers": layers}


def search_ops(query: str, size: int = 50) -> List[Dict]:
    """Search the OPS API and return a simplified landscape table."""
    client = PatentSearchClient(
        ops_api_key=os.getenv("PATENT_CLIENT_EPO_API_KEY"),
        ops_api_secret=os.getenv("PATENT_CLIENT_EPO_SECRET"),
    )
    results = client.search(query, size=size)

    landscape = []
    for r in results:
        fulltext = r.get_fulltext() or ""
        claims = r.get_claims() or []
        ic = claims[0] if claims else fulltext[:2000]
        cond = parse_conditions(ic)
        landscape.append(
            {
                "pub": r.publication_number,
                "title": r.title[:80],
                "o2/temp/layers": cond,
                "cpc": r.cpc_classes[:5],
            }
        )
    return landscape
