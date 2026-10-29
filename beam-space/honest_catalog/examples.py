"""Built-in example catalogs and their cached Beam results.

CACHED RESULTS: the files in examples/cache/ are written ONLY by
scripts/make_cache.py, which runs the real pipeline against Beam with an
HF_TOKEN. Until that script has been run, each cache file has
``"status": "not generated yet"`` and ``"result": null``, and the app shows
local rules only for the examples. Nothing in those files is hand-written
model output.
"""

from __future__ import annotations

import json
from pathlib import Path

from .catalog import Catalog, EvidenceDoc, parse_catalog_file, parse_evidence_file
from .pipeline import Review, catalog_fingerprint

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = ROOT / "examples"
CACHE_DIR = EXAMPLES_DIR / "cache"

EXAMPLES = {
    "en": {
        "catalog": EXAMPLES_DIR / "catalog_en.csv",
        "evidence": [EXAMPLES_DIR / "evidence_en" / "supplier_specs.txt",
                     EXAMPLES_DIR / "evidence_en" / "test_reports.txt"],
        "cache": CACHE_DIR / "example_en.json",
    },
    "ko": {
        "catalog": EXAMPLES_DIR / "catalog_ko.csv",
        "evidence": [EXAMPLES_DIR / "evidence_ko" / "supplier_specs_ko.txt",
                     EXAMPLES_DIR / "evidence_ko" / "test_reports_ko.txt"],
        "cache": CACHE_DIR / "example_ko.json",
    },
}

NOT_GENERATED = "not generated yet"


def load_example(key: str) -> tuple[Catalog, list[EvidenceDoc]]:
    ex = EXAMPLES[key]
    return parse_catalog_file(ex["catalog"]), [parse_evidence_file(p) for p in ex["evidence"]]


def placeholder(key: str) -> dict:
    catalog, docs = load_example(key)
    ex = EXAMPLES[key]
    return {
        "status": NOT_GENERATED,
        "example": key,
        "catalog_file": str(ex["catalog"].relative_to(ROOT)),
        "evidence_files": [str(p.relative_to(ROOT)) for p in ex["evidence"]],
        "input_sha256": catalog_fingerprint(catalog, docs),
        "model": None,
        "generated_at": None,
        "result": None,
        "note": "Produced by scripts/make_cache.py with a real HF_TOKEN. Not generated yet.",
    }


def load_cached(key: str) -> tuple[Review | None, str]:
    """Returns (review, status). The review is None unless a real cache exists for the current example files."""
    path = EXAMPLES[key]["cache"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, NOT_GENERATED
    if data.get("status") != "generated" or not data.get("result"):
        return None, data.get("status") or NOT_GENERATED
    catalog, docs = load_example(key)
    if data.get("input_sha256") != catalog_fingerprint(catalog, docs):
        return None, "stale"
    review = Review.from_dict(data["result"])
    review.mode = "cached"
    return review, "generated"
