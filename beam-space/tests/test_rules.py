"""The Python rules must behave like src/rules.mjs in the Honest Copy web app.

tests/fixtures/rules_parity.json was produced by running the original
JavaScript (scripts/js_parity.mjs) on tests/fixtures/parity_phrases.json.
If Node and the JavaScript source are available, the comparison is also
re-run live.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from honest_catalog.rules import (ALL_RULES, PORTED_RULES, SAMPLES, analyze, analyze_listing, apply_all,
                                  apply_finding)

FIX = Path(__file__).parent / "fixtures"
JS_RULES = Path(__file__).resolve().parents[2] / "src" / "rules.mjs"


def _py(text):
    res = analyze(text)
    return {
        "text": text, "score": res["score"], "revised": apply_all(text),
        "findings": [{"rule_id": f.rule_id, "category": f.category, "phrase": f.phrase,
                      "replacement": f.replacement, "start": f.start, "end": f.end} for f in res["findings"]],
    }


EXPECTED = json.loads((FIX / "rules_parity.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", EXPECTED, ids=[repr(c["text"])[:40] for c in EXPECTED])
def test_parity_with_javascript_fixture(case):
    assert _py(case["text"]) == case


def test_fixture_covers_every_ported_rule():
    used = {f["rule_id"] for c in EXPECTED for f in c["findings"]}
    assert used == {r.id for r in PORTED_RULES}


@pytest.mark.skipif(not (shutil.which("node") and JS_RULES.exists()), reason="needs node and the honest-copy JS source")
def test_parity_live_against_node(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "js_parity.mjs"
    out = subprocess.run(["node", str(script), str(FIX / "parity_phrases.json")], capture_output=True, text=True, check=True)
    for js, phrase in zip(json.loads(out.stdout), json.loads((FIX / "parity_phrases.json").read_text(encoding="utf-8"))):
        assert _py(phrase) == js


# The same cases as tests/rules.test.mjs in the web app.
@pytest.mark.parametrize("lang", ["en", "ko"])
def test_samples_exact_spans_and_four_categories(lang):
    sample = SAMPLES[lang]
    res = analyze(sample)
    assert len(res["findings"]) == 4
    assert len({f.category for f in res["findings"]}) == 4
    assert res["score"] == 84
    for f in res["findings"]:
        assert sample[f.start:f.end] == f.phrase
    revised = apply_all(sample)
    assert analyze(revised)["score"] == 0 and revised and revised != sample


def test_repeated_matches_replace_only_selected():
    text = "cures acne. cures acne."
    f = analyze(text)["findings"][1]
    assert apply_finding(text, f) == "cures acne. Is designed for everyday care."
    assert analyze(apply_all(text))["findings"] == []


def test_unicode_and_html_stay_plain():
    text = "🧴 <script>alert(1)</script> 국내 1위"
    f = analyze(text)["findings"][0]
    assert text[f.start:f.end] == "국내 1위"
    assert "<script>" in apply_finding(text, f)


def test_benign_text_and_boundaries():
    assert analyze("A soft cotton towel. Made for everyday use.")["score"] == 0
    assert analyze("My best friend assures acne care is personal.")["score"] == 0
    assert analyze("")["findings"] == []
    with pytest.raises(TypeError):
        analyze(None)


def test_stale_span_fails():
    f = analyze("cures acne")["findings"][0]
    with pytest.raises(ValueError, match="Draft changed"):
        apply_finding("a different draft", f)


def test_score_caps_and_is_deterministic():
    text = "cures acne. " * 20
    assert analyze(text)["score"] == 100
    assert analyze(text) == analyze(text)


@pytest.mark.parametrize("text,expected", [
    ("This kitchen gadget is No.1 best-selling. It lasts forever.", [("No.1 best-selling", "superlative"), ("lasts forever", "guarantee")]),
    ("A best-selling kitchen tool.", [("best-selling", "superlative")]),
    ("3일 만에 여드름 완치. 100% 효과 보장. 국내 1위.", [("3일 만에 여드름 완치", "medical"), ("100% 효과 보장", "guarantee"), ("국내 1위", "superlative")]),
])
def test_production_regressions(text, expected):
    assert [(f.phrase, f.category) for f in analyze(text)["findings"]] == expected
    assert analyze(apply_all(text))["score"] == 0


def test_javascript_ascii_word_boundary_is_kept():
    # JS \b ignores non-ASCII letters, so "acne" is a whole word before "é"; Python's default \b would not match.
    assert [f.phrase for f in analyze("Treats acneé")["findings"]] == ["Treats acne"]
    # and "#1" after a space is not matched by the original rule (kept for parity)
    assert analyze("Best seller #1 in our shop.")["findings"] == []


def test_catalog_additions_are_separate_from_the_port():
    assert not {r.id for r in PORTED_RULES} & {r.id for r in ALL_RULES[len(PORTED_RULES):]}
    assert [f.phrase for f in analyze_listing("Best seller #1 in our shop.")["findings"]] == ["Best seller #1"]
    assert [f.phrase for f in analyze_listing("판매 1위 앞치마")["findings"]] == ["판매 1위"]
    assert [f.phrase for f in analyze_listing("평생 사용 가능한 비니")["findings"]] == ["평생 사용"]
    assert [f.phrase for f in analyze_listing("Colors may fade over time.")["findings"]] == []
    assert [f.phrase for f in analyze_listing("It never fades.")["findings"]] == ["never fades"]
