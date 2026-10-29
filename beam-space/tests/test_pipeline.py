"""End-to-end pipeline with a stand-in inference client.

The stand-in returns fixed JSON so the tests can check what the app does with
model output. It is test scaffolding only, not Beam output, and is never used
for the cached example files.
"""

import csv
import io
import json
from types import SimpleNamespace

from honest_catalog import pipeline
from honest_catalog.beam import BeamClient, final_answer, parse_json_answer, redact
from honest_catalog.budget import DailyBudget
from honest_catalog.examples import NOT_GENERATED, load_cached, load_example, placeholder
from honest_catalog.pipeline import Review, corrected_csv, review_catalog
from honest_catalog.report import findings_csv, guard_html, report_html


# Built at runtime so no token-shaped literal sits in the source.
FAKE_TOKEN = "hf" + "_" + "x" * 20


class StandInClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def chat_completion(self, **kwargs):
        self.requests.append(kwargs)
        content = self.replies.pop(0)
        if isinstance(content, Exception):
            raise content
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")],
                               usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2))


AUDIT = {"issues": [
    {"source": "EN-001/description", "quote": "100% linen", "type": "spec_conflict", "related": ["EN-001/material"],
     "reason": "The material column says 55% linen, 45% cotton."},
    {"source": "EN-026/description", "quote": "130 x 170 cm", "type": "spec_conflict", "related": ["EN-026/size_chart"],
     "reason": "The size chart says 130 x 180 cm."},
    {"source": "EN-005/description", "quote": "Certified organic cotton", "type": "unsupported", "related": [], "reason": "check"},
    {"source": "EN-003/description", "quote": "Made of bamboo fibre", "type": "contradiction", "reason": "invented"},
]}


def _verify(claims_by_quote):
    return {"results": [
        {"id": claims_by_quote["100% linen"], "label": "contradicted",
         "citations": [{"source": "EN-001/material", "quote": "55% linen, 45% cotton"}], "note": "Spec says blend."},
        {"id": claims_by_quote["130 x 170 cm"], "label": "contradicted",
         "citations": [{"source": "EN-026/size_chart", "quote": "130 x 190 cm"}]},
        {"id": claims_by_quote["Certified organic cotton"], "label": "supported",
         "citations": [{"source": "supplier_specs.txt#L6", "quote": "Organic cotton certificate OC-55120 covers style EN-005 only."}]},
    ]}


def _run(tmp_path, replies_fn, cap=40):
    catalog, docs = load_example("en")
    budget = DailyBudget(tmp_path / "u.json", cap=cap)
    # first build the claim ids the verifier will see
    local = pipeline.local_claims(catalog)
    sources = pipeline.all_sources(catalog, docs)
    pipeline.merge_audit_issues(AUDIT, local, catalog, sources, [])
    pipeline._order_and_number(local, catalog)
    ids = {c.quote: c.id for c in local}
    stand_in = StandInClient(replies_fn(ids))
    client = BeamClient(budget=budget, client=stand_in, token="test")
    return catalog, docs, review_catalog(catalog, docs, client), stand_in, budget, ids


def test_full_run_three_calls_and_guard(tmp_path):
    def replies(ids):
        rewrites = {"rewrites": [
            {"id": ids["100% linen"], "replacement": "a 55% linen, 45% cotton blend"},
            {"id": ids["130 x 170 cm"], "replacement": "130 x 999 cm"},            # invented number -> rejected
            {"id": ids["cures acne in 7 days"], "replacement": "is made for a calm daily routine"},
        ]}
        harmony = "<|channel|>analysis<|message|>thinking {\"x\":1}<|end|><|start|>assistant<|channel|>final<|message|>"
        return [json.dumps(AUDIT), harmony + json.dumps(_verify(ids)) + "<|return|>", "```json\n" + json.dumps(rewrites) + "\n```"]

    catalog, docs, review, stand_in, budget, ids = _run(tmp_path, replies)
    assert review.mode == "live" and review.calls_made == 3 and budget.used() == 3
    assert [s.ok for s in review.steps] == [True, True, True]
    req = stand_in.requests[0]
    assert req["model"] == "reflection/Beam-1.0-501B-A23B" and req["temperature"] == 0.7 and req["top_p"] == 0.99
    # whole catalog in one request
    assert all(f"{p.sku}/title" in req["messages"][1]["content"] for p in catalog.products)

    by_quote = {c.quote: c for c in review.claims}
    linen = by_quote["100% linen"]
    assert linen.label == "contradicted" and linen.citations[0].quote == "55% linen, 45% cotton"
    assert linen.rewrite == "a 55% linen, 45% cotton blend" and linen.rewrite_from == "beam"
    size = by_quote["130 x 170 cm"]
    assert size.label == "no_evidence"                    # its only citation was invented
    assert size.rewrite == ""                             # Beam rewrite rejected, no rule template
    assert by_quote["Certified organic cotton"].label == "supported"
    assert by_quote["cures acne in 7 days"].rewrite_from == "beam"
    assert by_quote["Never fades"].label == "not_checked" and by_quote["Never fades"].rewrite_from == "rule template"
    assert "Made of bamboo fibre" not in by_quote
    reasons = " ".join(g.reason for g in review.guard)
    assert "quote not found" in reasons and "label lowered" in reasons and "adds the number 999" in reasons
    assert review.quotes_checked == 3 and review.quotes_accepted == 2

    out = list(csv.DictReader(io.StringIO(corrected_csv(catalog, review).lstrip("﻿"))))
    assert out[0]["description"].startswith("Our everyday apron in a 55% linen, 45% cotton blend.")
    assert "needs your check" in out[25]["review_note"]          # EN-026 keeps its text, flagged
    assert out[25]["description"] == catalog.products[25].cells["description"]
    html = report_html(review, catalog, "en") + guard_html(review, "en")
    assert "Contradicted" in html and "second look" in html and "<script" not in html
    assert findings_csv(review, "ko").lstrip("\ufeff").startswith("상품코드")


def test_review_round_trips_through_json(tmp_path):
    def replies(ids):
        return [json.dumps(AUDIT), json.dumps(_verify(ids)), json.dumps({"rewrites": []})]
    *_, review, _, _, _ = _run(tmp_path, replies)
    again = Review.from_dict(json.loads(json.dumps(review.to_dict(), ensure_ascii=False)))
    assert again.to_dict() == review.to_dict()


def test_failed_step_falls_back_and_says_so(tmp_path):
    def replies(ids):
        return [RuntimeError("upstream 503 for token " + FAKE_TOKEN), "not json at all", json.dumps({"rewrites": []})]
    catalog, docs, review, *_ = _run(tmp_path, replies)
    assert [s.ok for s in review.steps] == [False, False, True]
    assert FAKE_TOKEN not in json.dumps(review.to_dict())
    assert "partial" in review.messages
    assert all(c.label == "not_checked" for c in review.claims)
    assert all(c.rewrite for c in review.claims if c.rule_replacement)


def test_cap_reached_mid_run_stops_calling(tmp_path):
    def replies(ids):
        return [json.dumps(AUDIT), json.dumps(_verify(ids)), json.dumps({"rewrites": []})]
    catalog, docs, review, stand_in, budget, _ = _run(tmp_path, replies, cap=1)
    assert len(stand_in.requests) == 1 and budget.used() == 1
    assert [s.ok for s in review.steps] == [True, False, False]


def test_no_token_and_cap_and_size_fall_back_to_local(tmp_path, monkeypatch):
    catalog, docs = load_example("ko")
    r = review_catalog(catalog, docs, BeamClient(budget=DailyBudget(tmp_path / "a.json"), token=""))
    assert r.mode == "local" and r.messages == ["no_token"] and r.claims
    assert all(c.label == "not_checked" and c.rewrite for c in r.claims)
    r = review_catalog(catalog, docs, BeamClient(budget=DailyBudget(tmp_path / "b.json", cap=0), token="x"))
    assert r.messages == ["cap_reached"]
    monkeypatch.setattr(pipeline, "MAX_INPUT_CHARS", 100)
    r = review_catalog(catalog, docs, BeamClient(budget=DailyBudget(tmp_path / "c.json"), token="x",
                                                 client=StandInClient([])))
    assert r.messages == ["too_large"]


def test_harmony_and_json_parsing():
    raw = "<|channel|>analysis<|message|>{\"draft\":true}<|end|><|start|>assistant<|channel|>final<|message|>{\"ok\":1}<|return|>"
    assert parse_json_answer(final_answer(raw)) == {"ok": 1}
    assert parse_json_answer(final_answer("<think>{\"no\":1}</think> Here: {\"ok\": 2} done")) == {"ok": 2}
    assert final_answer("<think>cut off before answer") == ""


def test_redact_hides_secret_like_strings():
    assert "hf_" not in redact("bad token " + FAKE_TOKEN + " and Bearer abc.def")
    assert "sk-" not in redact("key " + "sk" + "-" + "x" * 12)


def test_cached_examples_are_placeholders_until_generated():
    for key in ("en", "ko"):
        review, status = load_cached(key)
        data = json.loads(open(f"{pipeline.__file__.rsplit('/honest_catalog', 1)[0]}/examples/cache/example_{key}.json",
                               encoding="utf-8").read())
        if data["status"] == NOT_GENERATED:
            assert review is None and status == NOT_GENERATED and data["result"] is None
            assert data["input_sha256"] == placeholder(key)["input_sha256"]
        else:
            assert data["status"] == "generated" and review is not None
