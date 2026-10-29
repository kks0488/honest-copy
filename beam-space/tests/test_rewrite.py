"""Whole-field rewrite checks and the clean-removal fallback.

The "Beam text" strings below are hand-written test inputs that mimic the bad
phrase-level rewrites seen in a real run (for example "Best seller #1" ->
"Available"). They test what the code does with such output.
"""

import pytest

from honest_catalog.examples import load_example
from honest_catalog.pipeline import Citation, Claim, local_claims
from honest_catalog.rewrite import (build_field, check_gap, fallback_gap, make_plan, remove_cleanly, sentence_ok,
                                    split_sentences)
from honest_catalog.rules import analyze_listing

EN, _ = load_example("en")
KO, _ = load_example("ko")
ROWS = {p.sku: p for p in EN.products + KO.products}


def claim(sku, quote, column=None, label="no_evidence", citations=()):
    prod = ROWS[sku]
    column = column or ("description" if sku.startswith("EN") else "상세설명")
    text = prod.cells[column]
    start = text.index(quote)
    return Claim(id=f"C-{sku}-{start}", sku=sku, column=column, source=prod.source_id(column), quote=quote,
                 start=start, end=start + len(quote), origin=["beam"], label=label,
                 citations=[Citation(s, q, True) for s, q in citations])


def run(sku, quotes, proposal, column=None, citations=()):
    claims = [claim(sku, q, column, citations=citations) for q in quotes]
    catalog = EN if sku.startswith("EN") else KO
    col = claims[0].column
    plan = make_plan(ROWS[sku], col, col == catalog.title_col, claims, catalog.spec_cols)
    guard = []
    fr = build_field(plan, proposal, lambda item, text, why: guard.append(why))
    return fr, guard


def test_sentence_split_keeps_numbers_and_rankings_whole():
    text = "The No.1 knife. Weighs 4.5 g! Hand wash"
    assert [text[a:b] for a, b in split_sentences(text)] == ["The No.1 knife.", "Weighs 4.5 g!", "Hand wash"]
    assert split_sentences("Organic Cotton Pocket Tee") == [(0, 25)]


# --- the bad rewrites from the real run are now rejected and replaced by clean removal ---

def test_ranking_replaced_by_loose_word_is_rejected():
    fr, guard = run("EN-002", ["Best seller #1"],
                    "The same soft linen as our Everyday Apron, now with a cross-back. Available in our shop.")
    assert fr.after == "The same soft linen as our Everyday Apron, now with a cross-back."
    assert any("fragment ('Available')" in g for g in guard)


def test_single_word_swap_inside_a_sentence_is_rejected():
    fr, guard = run("EN-004", ["best-selling"],
                    "Three of our Waffle Bath Towels (380 GSM) tied with a gift band. Our #1 gift towel set.")
    assert fr.after == "Three of our Waffle Bath Towels (380 GSM) tied with a gift band. Our towel set."
    fr, guard = run("EN-008", ["never shrinks", "Soft enough for sensitive skin"], "Fine merino wool that is wool. Soft.")
    assert fr.after == "Fine merino wool."
    assert guard


def test_rewrite_that_repeats_the_field_is_rejected():
    fr, guard = run("KO-005", ["미리 세탁해서 형태가 잘 유지돼요"], "인증받은 오가닉 코튼 100% 티셔츠입니다. 오가닉 코튼 100%.")
    assert fr.after == "인증받은 오가닉 코튼 100% 티셔츠입니다."
    assert any("repeats" in g for g in guard)


def test_rewrite_that_keeps_a_ranking_is_rejected():
    fr, guard = run("KO-002", ["판매 1위"], "데일리 앞치마와 같은 원단으로 만들었어요. 판매 1위 앞치마!")
    assert fr.after == "데일리 앞치마와 같은 원단으로 만들었어요."
    assert any("risky phrase" in g for g in guard)


# --- what is accepted ---

def test_whole_sentence_rewrite_is_accepted():
    fr, guard = run("EN-003", ["Never fades"],
                    "Heavy 500 GSM waffle weave that dries fast. Tumble dry low to keep it soft wash after wash.")
    assert fr.gaps[0].source == "beam" and not guard
    assert fr.after.startswith("Heavy 500 GSM waffle weave that dries fast. ")


def test_number_origin_and_material_substitutions_are_accepted():
    fr, _ = run("EN-007", ["Size M has a 54 cm chest"], "Relaxed fit, true to size. Size M has a 58 cm chest.")
    assert fr.gaps[0].source == "beam" and fr.after.endswith("58 cm chest.")
    fr, _ = run("EN-026", ["130 x 170 cm"], "Warm recycled wool throw, 130 x 180 cm.")
    assert fr.gaps[0].source == "beam"
    fr, _ = run("KO-006", ["포르투갈에서 만들었어요"], "오가닉 코튼 티셔츠와 같은 원단이고 베트남에서 만들었어요.")
    assert fr.gaps[0].source == "beam"
    fr, _ = run("EN-001", ["100% linen"], "Our everyday apron in 55% linen, 45% cotton. Two deep pockets and an adjustable neck strap.")
    assert fr.gaps[0].source == "beam"


def test_two_claims_in_one_field_fixed_in_one_rewrite():
    fr, guard = run("EN-013", ["Same formula as our Sun Fluid", "SPF 50", "water resistant for 80 minutes"],
                    "A mineral sun stick for easy touch-ups. Reapply every 2 hours.")
    assert len(fr.gaps) == 1 and fr.gaps[0].source == "beam", guard


# --- code guards ---

def test_unflagged_sentence_must_survive_word_for_word():
    fr, guard = run("EN-011", ["Clinically proven"], "A rich cream for dry days. Rich, but not greasy.")
    assert fr.after == "Rich but not greasy."
    assert any("without a flagged claim was changed" in g for g in guard)


@pytest.mark.parametrize("proposal,why", [
    ("Breathable cotton socks with a soft rib. Comfort rated 9 of 10 by testers.", "adds the number"),
    ("Breathable cotton socks with a soft rib. 하루 종일 편안해요.", "language"),
    ("Breathable cotton socks with a soft rib. Clinically proven comfort for long days.", "risky"),
    ("Breathable cotton socks with a soft rib. Dermatologist-approved comfort.", "risky"),
    ("Breathable cotton socks with a soft rib. Comfort.", "fragment"),
])
def test_guards_reject(proposal, why):
    fr, guard = run("EN-009", ["Dermatologist-approved"], proposal)
    assert fr.after == "Breathable cotton socks with a soft rib."
    assert any(why in g for g in guard), guard


def test_missing_or_broken_proposal_uses_fallback():
    for proposal in (None, "", "   "):
        fr, _ = run("EN-021", ["Risk-free"], proposal)
        assert fr.after == "Borosilicate glass jars with airtight bamboo lids."
        assert fr.gaps[0].source == "cleanup"


def test_field_is_never_emptied():
    fr, _ = run("EN-006", ["Organic Cotton Pocket Tee"], None, column="title")
    assert fr.after == fr.before and fr.note and fr.gaps[0].source == "kept"
    fr, guard = run("EN-006", ["Organic Cotton Pocket Tee"], "", column="title")
    assert fr.after == fr.before


# --- fallback removal ---

@pytest.mark.parametrize("sentence,quotes,korean,expected", [
    ("Best seller #1 in our shop.", ["Best seller #1"], False, ""),
    ("Our everyday apron in 100% linen.", ["100% linen"], False, "Our everyday apron."),
    ("Our #1 best-selling towel set.", ["best-selling"], False, "Our towel set."),
    ("A lightweight serum that cures acne in 7 days and is 100% safe for every skin type.",
     ["cures acne in 7 days", "100% safe"], False, "A lightweight serum."),
    ("Soft cotton pajamas, 100% safe for babies and toddlers.", ["100% safe"], False, "Soft cotton pajamas for babies and toddlers."),
    ("Never fades, even after hundreds of washes.", ["Never fades"], False, ""),
    ("Naturally antibacterial olive wood, the world's best board for raw meat.",
     ["Naturally antibacterial", "the world's best"], False, "Olive wood board for raw meat."),
    ("판매 1위 앞치마!", ["판매 1위"], True, ""),
    ("멀버리 실크 100%, 자는 동안 피부 고민까지 해결해 줘요.", ["피부 고민까지 해결해 줘요"], True, "멀버리 실크 100%."),
    ("천연 항균 올리브나무로 만든 세계 최고의 도마.", ["천연 항균", "세계 최고"], True, "올리브나무로 만든 도마."),
    ("부드러운 메리노 울로 만들어 평생 사용 가능한 비니.", ["평생 사용"], True, ""),
    ("린넨 100%로 만든 데일리 앞치마입니다.", ["린넨 100%"], True, ""),
    ("따뜻한 재생 울 블랭킷, 130x170cm.", ["130x170cm"], True, "따뜻한 재생 울 블랭킷."),
])
def test_clean_removal(sentence, quotes, korean, expected):
    spans = [(sentence.index(q), sentence.index(q) + len(q)) for q in quotes]
    assert remove_cleanly(sentence, spans, korean, False) == expected


def test_fallback_never_leaves_a_fragment_on_the_example_shops():
    for catalog in (EN, KO):
        claims = local_claims(catalog)
        by_source = {}
        for c in claims:
            by_source.setdefault(c.source, []).append(c)
        for prod in catalog.products:
            for col in catalog.copy_cols:
                todo = by_source.get(prod.source_id(col))
                if not todo:
                    continue
                plan = make_plan(prod, col, col == catalog.title_col, todo, catalog.spec_cols)
                korean = catalog is KO
                for g in plan.gaps:
                    out = fallback_gap(plan, g)
                    for a, b in split_sentences(out):
                        s = out[a:b]
                        assert not sentence_ok(s, korean, False, False), s
                        assert not analyze_listing(s)["findings"], s
                    for c in g.claims:
                        assert c.quote not in out


def test_check_gap_allows_dropping_a_sentence_when_others_remain():
    c = claim("EN-021", "Risk-free")
    plan = make_plan(ROWS["EN-021"], "description", False, [c], EN.spec_cols)
    assert check_gap(plan, plan.gaps[0], "", "Borosilicate glass jars with airtight bamboo lids.") == ""
    assert check_gap(plan, plan.gaps[0], "", "") == "would leave the field empty"
