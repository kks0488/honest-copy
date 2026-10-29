"""Produce the cached example results shown in the Space.

This is the ONLY place cached Beam output comes from. It runs the real
pipeline (local rules, whole-catalog audit, verifier, rewrites) against Beam
and saves the processed result, including the citation-check log.

    HF_TOKEN=... python scripts/make_cache.py            # both examples
    HF_TOKEN=... python scripts/make_cache.py --only ko
    python scripts/make_cache.py --placeholder           # reset to "not generated yet"

Each example uses up to 3 Beam calls. The calls count against the same daily
cap as the app (BEAM_DAILY_CALL_CAP, file BEAM_USAGE_FILE). A cache file is
only written when all three Beam steps succeed, so a failed run never leaves
half a result behind.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from honest_catalog.beam import MODEL_ID, BeamClient  # noqa: E402
from honest_catalog.examples import EXAMPLES, load_example, placeholder  # noqa: E402
from honest_catalog.pipeline import review_catalog  # noqa: E402


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(EXAMPLES))
    ap.add_argument("--placeholder", action="store_true", help="write 'not generated yet' files, no model calls")
    args = ap.parse_args()
    keys = [args.only] if args.only else sorted(EXAMPLES)

    if args.placeholder:
        for k in keys:
            write(EXAMPLES[k]["cache"], placeholder(k))
            print(f"{k}: placeholder written")
        return 0

    if not os.environ.get("HF_TOKEN", "").strip():
        print("HF_TOKEN is not set. Nothing was generated.", file=sys.stderr)
        return 2

    status = 0
    for k in keys:
        catalog, docs = load_example(k)
        client = BeamClient()
        review = review_catalog(catalog, docs, client)
        failed = [s for s in review.steps if not s.ok]
        for s in review.steps:
            print(f"{k}: {s.step}: {'ok' if s.ok else 'FAILED'} ({s.detail})")
        if review.mode != "live" or failed or len(review.steps) < 3:
            print(f"{k}: not written (mode={review.mode}, messages={review.messages})", file=sys.stderr)
            status = 1
            continue
        data = placeholder(k)
        data.update({
            "status": "generated",
            "model": MODEL_ID,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": "Produced by scripts/make_cache.py from a live Beam run.",
            "result": review.to_dict(),
        })
        write(EXAMPLES[k]["cache"], data)
        print(f"{k}: written, {len(review.claims)} claims, {review.quotes_accepted}/{review.quotes_checked} quotes matched, "
              f"{len(review.guard)} rejected outputs, {review.calls_made} calls")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
