"""Local phrase rules, ported from the Honest Copy web app (src/rules.mjs).

These are finite wording heuristics, not factual verification or legal
classification. The patterns below are copied from the JavaScript source and
translated mechanically so they behave the same way in Python:

* JavaScript ``\\b`` only knows ASCII word characters, even with the ``u`` flag.
  Python's ``\\b`` is Unicode-aware, so ``\\b`` becomes an explicit ASCII
  word boundary.
* JavaScript ``\\d`` is ASCII digits only; ``\\s`` is the ECMAScript whitespace
  set. Both are spelled out here.

Offsets are Python string indexes (code points). The JavaScript version uses
UTF-16 offsets; the matched phrases are identical.

``PORTED_RULES`` is the faithful port and is what the parity tests check.
``CATALOG_RULES`` are a few extra patterns added for whole-catalog review
(shop rankings such as "best seller #1", lifetime promises in Korean). They are
kept separate on purpose so the port stays an exact copy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CATEGORIES = {
    "medical": {"label": "Health / medical", "short": "Medical claim", "weight": 28},
    "guarantee": {"label": "Absolute guarantee", "short": "Guarantee", "weight": 22},
    "superlative": {"label": "Unverifiable superlative", "short": "Superlative", "weight": 18},
    "evidence": {"label": "Missing evidence", "short": "Evidence", "weight": 16},
}

CATEGORY_LABELS_KO = {
    "medical": "건강/의료 표현",
    "guarantee": "절대적 보장",
    "superlative": "근거 없는 최상급",
    "evidence": "근거 필요",
}

_ASCII_WORD = "A-Za-z0-9_"
_B = f"(?:(?<![{_ASCII_WORD}])(?=[{_ASCII_WORD}])|(?<=[{_ASCII_WORD}])(?![{_ASCII_WORD}]))"
_JS_WS = "\t\n\x0b\x0c\r    -     　﻿"
_S = f"[{_JS_WS}]"
_D = "[0-9]"
_TRAILING_SENTENCE_END = re.compile(f"[.!?]{_S}*$")
_TRIM = re.compile(f"^{_S}+|{_S}+$")


def _from_js(source: str) -> str:
    """Translate a JavaScript regex source to an equivalent Python pattern."""
    out = []
    i = 0
    while i < len(source):
        ch = source[i]
        if ch == "\\" and i + 1 < len(source):
            nxt = source[i + 1]
            out.append({"b": _B, "s": _S, "d": _D}.get(nxt, ch + nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    js_source: str
    js_flags: str
    replacement: str
    explanation: str
    explanation_ko: str = ""
    pattern: re.Pattern = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        flags = re.IGNORECASE if "i" in self.js_flags else 0
        object.__setattr__(self, "pattern", re.compile(_from_js(self.js_source), flags))


def _rule(rid, category, js_source, js_flags, replacement, explanation, explanation_ko=""):
    return Rule(rid, category, js_source, js_flags, replacement, explanation, explanation_ko)


# --- Faithful port of src/rules.mjs (same order, same patterns, same text) ---
PORTED_RULES = [
    _rule("medical-en", "medical",
          r"\b(?:cures?|treats?|heals?)\s+(?:acne|eczema|diabetes|cancer|arthritis|disease)(?:\s+in\s+\d+\s+days?)?\b", "giu",
          "is designed for everyday care",
          "This wording promises to treat a health condition. Describe the product’s everyday use instead; treatment claims need appropriate authorization and support.",
          "질환을 치료한다고 약속하는 표현입니다. 일상적인 사용법으로 설명하세요. 치료 효능 표현에는 별도의 허가와 근거가 필요합니다."),
    _rule("medical-ko", "medical",
          r"(?:\d+\s*일\s*만에\s*)?(?:여드름|아토피|당뇨|암|질병)(?:을|를)?\s*(?:완치|치료)(?:합니다|해요|한다|하는|해|된다)?", "gu",
          "일상적인 관리에 사용합니다",
          "This phrase promises treatment of a health condition, sometimes within a fixed time. Describe everyday use rather than claiming a medical effect.",
          "질환을 치료한다고, 때로는 기간까지 정해 약속하는 표현입니다. 의학적 효과 대신 일상적인 사용으로 설명하세요."),
    _rule("guarantee-en", "guarantee",
          r"\b(?:100\s*%\s*(?:guaranteed(?:\s+results)?|effective|safe)|guaranteed\s+results|always\s+works|zero\s+side\s+effects|risk[ -]free)\b", "giu",
          "results may vary",
          "An absolute promise leaves no room for different experiences. Set a realistic expectation instead.",
          "절대적인 약속은 사람마다 다른 경험을 고려하지 못합니다. 현실적인 기대치로 바꾸세요."),
    _rule("guarantee-duration-en", "guarantee",
          r"\blasts?\s+forever\b", "giu",
          "is intended for everyday use",
          "An unlimited lifetime promise cannot account for wear or different conditions of use. Remove the absolute durability promise or state a supported service life.",
          "끝없는 수명 약속은 마모나 사용 환경 차이를 반영하지 못합니다. 절대적인 내구성 약속을 빼거나 근거 있는 사용 기간을 적으세요."),
    _rule("guarantee-ko", "guarantee",
          r"(?:효과\s*)?100\s*%\s*(?:효과\s*보장|보장|안전|효과)(?:합니다|해요)?|부작용\s*(?:제로|없음|없는)|무조건\s*(?:효과|보장)", "gu",
          "개인에 따라 차이가 있을 수 있습니다",
          "A universal guarantee may overpromise. Make room for differences between people and situations.",
          "모두에게 같은 결과를 보장하면 과장이 될 수 있습니다. 사람과 상황에 따른 차이를 인정하세요."),
    _rule("superlative-en", "superlative",
          r"(?:\b(?:No\.?\s*1|number\s+one|#1)(?:\s+best[ -]selling|\s+in\s+(?:Korea|the\s+world))?\b|\b(?:the\s+)?(?:world['’]s\s+best|best\s+in\s+the\s+world|best\s+ever|best[ -]selling)\b)", "giu",
          "for everyday use",
          "A ranking or best-selling claim needs a clear source, category and date. Without those, describe a concrete feature rather than claiming first place.",
          "순위나 판매 1위 주장에는 출처, 비교 범위, 날짜가 필요합니다. 없다면 1위 대신 구체적인 특징을 설명하세요."),
    _rule("superlative-ko", "superlative",
          r"(?:국내|대한민국|세계)\s*(?:1\s*위|최고)|업계\s*(?:최초|최고)|넘버\s*원", "gu",
          "일상적인 사용을 위한 제품",
          "A first-place or best-in-category claim needs a defined comparison and current evidence. Describe a feature you can support.",
          "1위나 최고라는 주장에는 비교 기준과 최신 근거가 필요합니다. 근거로 뒷받침할 수 있는 특징을 설명하세요."),
    _rule("evidence-en", "evidence",
          r"\b(?:clinically\s+proven|scientifically\s+proven|doctor[ -]recommended|dermatologist[ -]approved|research[ -]backed)\b", "giu",
          "thoughtfully developed",
          "This wording suggests expert or research support. Check the actual evidence and its scope, or remove the implied endorsement. This tool does not verify studies.",
          "전문가나 연구의 뒷받침을 암시하는 표현입니다. 실제 근거와 범위를 확인하거나 암시된 추천을 빼세요."),
    _rule("evidence-ko", "evidence",
          r"임상(?:시험)?(?:으로)?\s*(?:입증|검증)(?:된|한|했습니다)?|의사\s*추천|과학적으로\s*입증(?:된)?|피부과\s*(?:인증|추천)", "gu",
          "일상적인 사용을 고려한",
          "This phrase implies research or expert support. Verify the specific evidence or use wording without an implied endorsement.",
          "연구나 전문가의 뒷받침을 암시하는 표현입니다. 구체적인 근거를 확인하거나 추천을 암시하지 않는 표현을 쓰세요."),
]

SAMPLES = {
    "en": "Our everyday face serum cures acne in 3 days.\n100% guaranteed results. No.1 in Korea.\nClinically proven care for your daily routine.",
    "ko": "이 세럼은 여드름을 치료합니다.\n효과 100% 보장. 국내 1위.\n임상으로 입증된 데일리 케어 제품입니다.",
}

# --- Catalog additions (not part of the port) ---
CATALOG_RULES = [
    _rule("shop-ranking-en", "superlative",
          r"\b(?:best[ -]?seller|top[ -]?seller|seller)\s*#\s*1\b|#\s*1\s+(?:best[ -]?seller|seller|pick|choice)\b|\btop[ -]rated\b", "giu",
          "for everyday use",
          "A ranking or best-selling claim needs a clear source, category and date. Without those, describe a concrete feature rather than claiming first place.",
          "순위나 판매 1위 주장에는 출처, 비교 범위, 날짜가 필요합니다. 없다면 1위 대신 구체적인 특징을 설명하세요."),
    _rule("shop-ranking-ko", "superlative",
          r"(?:판매량?|베스트셀러|랭킹|인기)\s*1\s*위|1\s*등\s*상품", "gu",
          "일상적인 사용을 위한 제품",
          "A first-place or best-in-category claim needs a defined comparison and current evidence. Describe a feature you can support.",
          "1위나 최고라는 주장에는 비교 기준과 최신 근거가 필요합니다. 근거로 뒷받침할 수 있는 특징을 설명하세요."),
    _rule("never-wears-en", "guarantee",
          r"\bnever\s+(?:fades?|shrinks?|breaks?|rusts?|pills?|stains?)\b", "giu",
          "is made for everyday use",
          "An absolute durability promise cannot account for wear or different conditions of use. Describe care instructions or a supported service life instead.",
          "절대 변하지 않는다는 약속은 마모나 사용 환경 차이를 반영하지 못합니다. 관리 방법이나 근거 있는 사용 기간을 적으세요."),
    _rule("lifetime-ko", "guarantee",
          r"평생\s*(?:사용|쓰는|보장|보증)", "gu",
          "오래 쓰도록 만든",
          "An unlimited lifetime promise cannot account for wear or different conditions of use. Remove the absolute durability promise or state a supported service life.",
          "끝없는 수명 약속은 마모나 사용 환경 차이를 반영하지 못합니다. 절대적인 내구성 약속을 빼거나 근거 있는 사용 기간을 적으세요."),
]

ALL_RULES = PORTED_RULES + CATALOG_RULES


@dataclass
class Finding:
    id: str
    rule_id: str
    start: int
    end: int
    phrase: str
    category: str
    label: str
    short: str
    weight: int
    explanation: str
    explanation_ko: str
    replacement: str


def _trim(value: str) -> str:
    return _TRIM.sub("", value)


def analyze(text: str, rules=None) -> dict:
    """Same behaviour as ``analyze`` in src/rules.mjs. Returns findings and a 0-100 score."""
    if not isinstance(text, str):
        raise TypeError("Copy must be text")
    rules = PORTED_RULES if rules is None else rules
    candidates: list[Finding] = []
    for r in rules:
        for m in r.pattern.finditer(text):
            start = m.start()
            if m.end() == start:
                continue
            before = text[:start]
            capitalise = bool(re.match(r"[A-Z]", m.group(0))) or not _trim(before) or bool(_TRAILING_SENTENCE_END.search(before))
            replacement = r.replacement[0].upper() + r.replacement[1:] if capitalise else r.replacement
            cat = CATEGORIES[r.category]
            candidates.append(Finding(
                id=f"{r.id}:{start}", rule_id=r.id, start=start, end=m.end(), phrase=m.group(0),
                category=r.category, label=cat["label"], short=cat["short"], weight=cat["weight"],
                explanation=r.explanation, explanation_ko=r.explanation_ko, replacement=replacement,
            ))
    candidates.sort(key=lambda f: (f.start, -f.weight, -f.end))
    findings: list[Finding] = []
    for f in candidates:
        if not findings or f.start >= findings[-1].end:
            findings.append(f)
    return {"findings": findings, "score": min(100, sum(f.weight for f in findings))}


def analyze_listing(text: str) -> dict:
    """Ported rules plus the catalog additions."""
    return analyze(text, ALL_RULES)


def apply_finding(text: str, finding: Finding, replacement: str | None = None) -> str:
    if text[finding.start:finding.end] != finding.phrase:
        raise ValueError("Draft changed; check again")
    rep = finding.replacement if replacement is None else replacement
    return text[:finding.start] + rep + text[finding.end:]


def apply_all(text: str, rules=None) -> str:
    draft = text
    for f in reversed(analyze(text, rules)["findings"]):
        draft = apply_finding(draft, f)
    return draft
