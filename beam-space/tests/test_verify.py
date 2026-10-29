"""Exact-quote checking: model citations that are not in the input must be thrown away."""

from honest_catalog.examples import load_example
from honest_catalog.catalog import all_sources
from honest_catalog.pipeline import (Citation, Claim, GuardEntry, apply_verification, check_quote, local_claims,
                                     merge_audit_issues, validate_rewrite, _order_and_number)

SOURCES = {
    "EN-001/description": "Our everyday apron in 100% linen. Two deep pockets.",
    "EN-001/material": "55% linen, 45% cotton",
    "specs.txt#L3": "Apron fabric (EN-001): 55% linen, 45% cotton, woven in Lithuania.",
    "KO-001/소재": "린넨 55%, 면 45%",
    "KO-001/인증": "없음",
}


def test_exact_quote_is_accepted():
    assert check_quote("EN-001/material", "55% linen, 45% cotton", SOURCES) == (True, "EN-001/material", "")
    assert check_quote("KO-001/소재", "린넨 55%", SOURCES)[0]


def test_invented_quote_is_rejected():
    ok, _, note = check_quote("specs.txt#L3", "Apron fabric is 100% linen", SOURCES)
    assert not ok and "not found" in note


def test_paraphrase_case_and_spacing_changes_are_rejected():
    for q in ("55% Linen, 45% Cotton", "55%  linen, 45% cotton", "55 % linen", "linen 55%"):
        assert not check_quote("EN-001/material", q, SOURCES)[0], q


def test_unknown_line_id_with_invented_text_is_rejected():
    assert not check_quote("specs.txt#L99", "tested by a lab", SOURCES)[0]


def test_wrong_line_id_is_corrected_only_when_unique():
    ok, sid, note = check_quote("specs.txt#L9", "woven in Lithuania", SOURCES)
    assert ok and sid == "specs.txt#L3" and "corrected" in note
    ok, _, note = check_quote("specs.txt#L9", "55% linen, 45% cotton", SOURCES)  # in two lines
    assert not ok


def test_short_or_empty_quotes_are_rejected_unless_whole_cell():
    assert not check_quote("EN-001/material", "45", SOURCES)[0]
    assert not check_quote("EN-001/material", "", SOURCES)[0]
    assert not check_quote("EN-001/material", None, SOURCES)[0]
    assert check_quote("KO-001/인증", "없음", SOURCES)[0]


def _claim():
    text = SOURCES["EN-001/description"]
    start = text.index("100% linen")
    return Claim(id="C001", sku="EN-001", column="description", source="EN-001/description", quote="100% linen",
                 start=start, end=start + len("100% linen"), origin=["beam"])


def test_verifier_label_is_lowered_when_all_citations_are_invented():
    claim, guard = _claim(), []
    data = {"results": [{"id": "C001", "label": "contradicted",
                         "citations": [{"source": "EN-001/material", "quote": "55% linen and 45% cotton blend"},
                                       {"source": "lab.txt#L1", "quote": "Lab test: 55% linen"}]}]}
    checked, accepted = apply_verification(data, [claim], SOURCES, guard)
    assert (checked, accepted) == (2, 0)
    assert claim.label == "no_evidence" and claim.citations == []
    assert len([g for g in guard if g.step == "verify"]) == 3  # two quotes + the lowered label


def test_verifier_keeps_real_citations_and_drops_fake_ones():
    claim, guard = _claim(), []
    data = {"results": [{"id": "C001", "label": "contradicted",
                         "citations": [{"source": "EN-001/material", "quote": "55% linen, 45% cotton"},
                                       {"source": "EN-001/material", "quote": "100% polyester"}]}]}
    assert apply_verification(data, [claim], SOURCES, guard) == (2, 1)
    assert claim.label == "contradicted"
    assert claim.citations == [Citation("EN-001/material", "55% linen, 45% cotton", True, "")]
    assert guard == [GuardEntry("verify", "C001", "EN-001/material: 100% polyester", "quote not found in the catalog or evidence")]


def test_claim_cannot_cite_itself_as_support():
    claim, guard = _claim(), []
    data = {"results": [{"id": "C001", "label": "supported",
                         "citations": [{"source": "EN-001/description", "quote": "apron in 100% linen"}]}]}
    apply_verification(data, [claim], SOURCES, guard)
    assert claim.label == "no_evidence"
    assert any("itself" in g.reason for g in guard)


def test_unknown_ids_and_labels_are_ignored():
    claim, guard = _claim(), []
    apply_verification({"results": [{"id": "C999", "label": "supported"}, {"id": "C001", "label": "maybe"}]},
                       [claim], SOURCES, guard)
    assert claim.label == "not_checked"
    apply_verification({"results": "nonsense"}, [claim], SOURCES, guard)
    assert claim.label == "not_checked"


def test_audit_issues_must_quote_seller_copy_exactly():
    catalog, docs = load_example("en")
    sources = all_sources(catalog, docs)
    claims, guard = local_claims(catalog), []
    n_local = len(claims)
    data = {"issues": [
        {"source": "EN-001/description", "quote": "100% linen", "type": "spec_conflict",
         "related": ["EN-001/material", "made-up#L1"], "reason": "Material column says 55% linen."},
        {"source": "EN-002/description", "quote": "voted best apron of the year", "type": "ranking"},
        {"source": "EN-001/material", "quote": "55% linen", "type": "contradiction"},
        {"source": "EN-002/description", "quote": "Best seller #1", "type": "ranking", "related": ["EN-004/description"]},
    ]}
    accepted, rejected = merge_audit_issues(data, claims, catalog, sources, guard)
    assert (accepted, rejected) == (2, 2)
    assert len(claims) == n_local + 1  # the "#1" issue merged into the existing rule finding
    new = next(c for c in claims if c.source == "EN-001/description")
    assert new.origin == ["beam"] and new.related == ["EN-001/material"]
    merged = next(c for c in claims if c.quote == "Best seller #1")
    assert merged.origin == ["rules", "beam"] and merged.related == ["EN-004/description"]
    reasons = [g.reason for g in guard]
    assert "quote not found in the catalog or evidence" in reasons
    assert any("not at seller copy" in r for r in reasons)
    assert any("does not exist" in r for r in reasons)
    _order_and_number(claims, catalog)
    assert [c.id for c in claims] == [f"C{i:03d}" for i in range(1, len(claims) + 1)]


def test_rewrite_guards():
    cell = SOURCES["EN-001/description"]
    claim = _claim()
    claim.citations = [Citation("EN-001/material", "55% linen, 45% cotton", True)]
    assert validate_rewrite(claim, "a 55% linen, 45% cotton blend", cell) == (True, "")
    assert not validate_rewrite(claim, "a 60% linen blend", cell)[0]          # invented number
    assert not validate_rewrite(claim, "린넨 혼방", cell)[0]                  # language switch
    assert not validate_rewrite(claim, "clinically proven linen", cell)[0]  # still risky
    assert not validate_rewrite(claim, "", cell)[0]
    assert not validate_rewrite(claim, "x" * 200, cell)[0]
    ko = Claim(id="C002", sku="K", column="d", source="s", quote="국내 1위", start=0, end=5, origin=["rules"])
    assert validate_rewrite(ko, "매일 쓰기 좋은", "국내 1위 앞치마")[0]
    assert not validate_rewrite(ko, "for everyday use", "국내 1위 앞치마")[0]
