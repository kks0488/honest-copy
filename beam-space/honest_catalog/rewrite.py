"""Whole-field rewrites: one rewrite per affected product, checked in code.

A copy field (title or description) is split into sentences. Sentences that
contain a flagged claim (anything not labelled supported) may change; every
other sentence must come back character for character. Runs of flagged
sentences between kept sentences are "gaps"; each gap is checked on its own,
so one bad gap does not throw away a good fix elsewhere in the field.

When Beam's text for a gap fails a check (or there is no Beam text), the gap
falls back to the original sentences with the flagged spans removed cleanly.
If that would leave a fragment, the whole sentence is dropped. A field is
never emptied: if nothing would remain, it is kept and marked for the seller.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .rules import analyze_listing

_HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_SENTENCE_END = re.compile(r"[.!?。]+(?=\s|$)")
_TOKEN = re.compile(r"\d+(?:[.,]\d+)?|[^\W\d_]+", re.UNICODE)
_MARK = "\x00"

# English words that only make sense next to the phrase that was removed.
_EN_LEFT_GLUE = r"(?:a|an|the|and|or|with|that|which|who|is|are|was|were|it|its|to|for|so|but|&|plus|also|in|of|on|at|from|by|as|than)"
_EN_RIGHT_GLUE = r"(?:and|or|but|so|plus|also|is|are|was|were)"
_EN_START_BAD = r"(?:in|on|at|for|with|of|to|and|or|but|as|by|from|than|so|is|are|was|were|that|which|even|also|still|plus|while|when|after|before|without)"
_EN_RANK = r"(?:#\s*1|no\.?\s*1|number\s+one|top)"
# Korean particles left hanging after a removed phrase.
_KO_PARTICLE = r"(?:으로|에서|이라|이고|하고|의|을|를|이|가|은|는|로|와|과|도|에|만)"
# Words that only work as the predicate of the removed phrase ("평생 사용 가능한" -> "가능한").
_KO_DEPENDENT = r"(?:가능한|가능|된|되는|돼요|됩니다|한|하는|해|해요|합니다|드려요|까지)"
# A removed phrase ending like this was an argument of the following verb.
_KO_ARG_END = r"(?:으로만|로만|으로|에서|로|을|를|와|과|에)"

MIN_WORDS_EN = 3
MIN_WORDS_KO = 2
MIN_REPLACEMENT_WORDS = 3


def has_hangul(text: str) -> bool:
    return bool(_HANGUL.search(text or ""))


def words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if re.search(r"\w", w)]


def split_sentences(text: str) -> list[tuple[int, int]]:
    """Sentence spans (start, end). A period inside "No.1" or "4.5" does not end a sentence."""
    spans, start = [], 0
    for m in _SENTENCE_END.finditer(text):
        seg = text[start:m.end()]
        if seg.strip():
            spans.append((start + len(seg) - len(seg.lstrip()), m.end()))
        start = m.end()
    rest = text[start:]
    if rest.strip():
        spans.append((start + len(rest) - len(rest.lstrip()), start + len(rest.rstrip())))
    return spans


# ------------------------------------------------------------------ plans

@dataclass
class Gap:
    sentences: list[int]                 # indexes into FieldPlan.sentences
    start: int
    end: int
    claims: list = field(default_factory=list)   # Claim objects whose span is in this gap

    def text(self, field_text: str) -> str:
        return field_text[self.start:self.end]


@dataclass
class FieldPlan:
    sku: str
    column: str
    source: str
    text: str
    is_title: bool
    sentences: list[tuple[int, int]]
    keep: list[int]                      # indexes of sentences that must survive unchanged
    gaps: list[Gap]
    facts: str                           # spec cells of this row + verified citations

    def kept_sentences(self) -> list[str]:
        return [self.text[a:b] for i, (a, b) in enumerate(self.sentences) if i in self.keep]


def make_plan(product, column: str, is_title: bool, claims: list, spec_cols: list[str]) -> FieldPlan:
    text = product.cells.get(column, "")
    sentences = split_sentences(text) or [(0, len(text))]
    flagged = set()
    for c in claims:
        for i, (a, b) in enumerate(sentences):
            if c.start < b and a < c.end:
                flagged.add(i)
    gaps: list[Gap] = []
    for i in sorted(flagged):
        if gaps and gaps[-1].sentences[-1] == i - 1:
            gaps[-1].sentences.append(i)
            gaps[-1].end = sentences[i][1]
        else:
            gaps.append(Gap([i], sentences[i][0], sentences[i][1]))
    for c in claims:
        for g in gaps:
            if g.start <= c.start and c.end <= g.end:
                g.claims.append(c)
                break
    facts = [product.cells.get(h, "") for h in spec_cols]
    facts += [x.quote for c in claims for x in c.citations]
    return FieldPlan(sku=product.sku, column=column, source=product.source_id(column), text=text,
                     is_title=is_title, sentences=sentences,
                     keep=[i for i in range(len(sentences)) if i not in flagged], gaps=gaps,
                     facts=" ".join(f for f in facts if f))


# ------------------------------------------------------------- checking

def _fact_tokens_ok(replacement: str, facts: str) -> bool:
    """True if every word or number in the replacement comes from the seller's spec data or evidence."""
    low = facts.lower()
    fact_words = [w for w in _TOKEN.findall(low)]
    for tok in _TOKEN.findall(replacement.lower()):
        if tok in low:
            continue
        # Korean: allow a fact word followed by a particle, e.g. 베트남 -> 베트남에서
        if has_hangul(tok) and any(len(w) >= 2 and tok.startswith(w) for w in fact_words if has_hangul(w)):
            continue
        return False
    return True


def _core_change(quote: str, replacement: str) -> str:
    """The part of a replacement that differs from the quote, after common leading/trailing words."""
    q, r = quote.split(), replacement.split()
    while q and r and q[0] == r[0]:
        q, r = q[1:], r[1:]
    while q and r and q[-1] == r[-1]:
        q, r = q[:-1], r[:-1]
    return " ".join(r)


def _substitution(original_gap: str, gap_start: int, claims: list, new_gap: str):
    """If new_gap is original_gap with only the flagged spans changed, return the replacements."""
    spans = sorted(((c.start - gap_start, c.end - gap_start, c) for c in claims), key=lambda x: x[0])
    pattern, pos = "", 0
    for a, b, _ in spans:
        if a < pos:
            return None
        pattern += re.escape(original_gap[pos:a]) + "(.*?)"
        pos = b
    pattern += re.escape(original_gap[pos:])
    m = re.fullmatch(pattern, new_gap, re.S)
    if not m:
        return None
    return [(c, m.group(i + 1)) for i, (_, _, c) in enumerate(spans)]


def sentence_ok(sentence: str, korean: bool, want_upper: bool, want_end: bool) -> str:
    """Empty string if the sentence looks complete, else the reason it does not."""
    s = sentence.strip()
    n = len(words(s))
    if n < (MIN_WORDS_KO if korean else MIN_WORDS_EN):
        return f"leaves a fragment ({s!r})"
    if want_end and not re.search(r"[.!?。]$", s):
        return f"sentence lost its ending ({s!r})"
    if not korean and want_upper and not re.match(r"[A-Z0-9\"'(]", s):
        return f"sentence starts mid-phrase ({s!r})"
    return ""


def check_gap(plan: FieldPlan, gap: Gap, new_gap: str, rest_of_field: str) -> str:
    """Empty string if Beam's text for this gap passes every check, else the reason."""
    original = gap.text(plan.text)
    korean = has_hangul(plan.text)
    new_gap = new_gap.strip()
    if not new_gap:
        return "" if rest_of_field.strip() else "would leave the field empty"
    if len(new_gap) > 2 * len(original) + 40:
        return "rewrite much longer than the original"
    if (korean and not has_hangul(new_gap)) or (not korean and has_hangul(new_gap)):
        return "rewrite changed the language"
    allowed_numbers = plan.text + " " + plan.facts
    for num in _NUMBER.findall(new_gap):
        if num not in allowed_numbers:
            return f"rewrite adds the number {num}, which is not in the seller's data"
    for f in analyze_listing(new_gap)["findings"]:
        return f"rewrite still contains a risky phrase ({f.phrase})"
    for c in gap.claims:
        if c.quote in new_gap:
            return f"flagged phrase is still there ({c.quote})"
    subs = _substitution(original, gap.start, gap.claims, new_gap)
    if subs is not None:
        for c, rep in subs:
            core = _core_change(c.quote, rep)
            if not rep.strip():
                continue
            if len(words(core)) >= MIN_REPLACEMENT_WORDS:
                if len(core) >= 4 and core in rest_of_field:
                    return f"replacement repeats text already in the field ({core!r})"
                continue
            if not _fact_tokens_ok(core, plan.facts):
                return f"flagged phrase replaced by a fragment ({rep!r})"
    elif not plan.is_title:
        for chunk in [new_gap[a:b] for a, b in split_sentences(new_gap)]:
            if len(chunk) >= 6 and chunk in rest_of_field:
                return f"rewrite repeats a sentence already in the field ({chunk!r})"
    if not plan.is_title:
        want_end = bool(re.search(r"[.!?。]\s*$", original))
        want_upper = bool(re.match(r"[A-Z0-9]", original))
        for a, b in split_sentences(new_gap):
            why = sentence_ok(new_gap[a:b], korean, want_upper, want_end)
            if why:
                return why
    return ""


# ------------------------------------------------------------- fallback

def remove_cleanly(sentence: str, spans: list[tuple[int, int]], korean: bool, is_title: bool) -> str:
    """The sentence with the flagged spans removed, or "" if what is left would be a fragment."""
    s = sentence
    for a, b in sorted(spans, reverse=True):
        s = s[:a] + _MARK + s[b:]
    starts_removed = s.lstrip().startswith(_MARK)
    if korean:
        for a, b in spans:
            if re.fullmatch(r"[\s.!?]*", sentence[b:]) and re.search(r"(?:요|다|니다|죠)$", sentence[a:b]) \
                    and sentence[:a].strip():
                # the sentence's verb was removed: keep only the complete part before the last comma
                head = sentence[:a]
                if "," not in head:
                    return ""
                cut = head.rindex(",")
                rest = [(x, y) for x, y in spans if y <= cut]
                shorter = head[:cut] + re.search(r"[.!?]*\s*$", sentence).group(0)
                return remove_cleanly(shorter, rest, korean, is_title)
        for a, b in spans:
            if re.search(_KO_ARG_END + r"$", sentence[a:b]):
                return ""  # the phrase was an argument of the verb that follows; cutting it breaks the verb
    for _ in range(4):
        before = s
        s = re.sub(r"[,;:]\s*" + _MARK, _MARK, s)
        s = re.sub(_MARK + r"\s*[,;:]", _MARK, s)
        if korean:
            s = re.sub(_MARK + r"의(?=[\s.,!?]|$)", _MARK, s)  # genitive before a noun is safe to drop
            s = re.sub(_MARK + r"(?:\s*" + _KO_DEPENDENT + r")+(?=\s*[.!?]*$)", _MARK, s)
        else:
            s = re.sub(r"(?i)\b(?:that|which|who)\s*" + _MARK + r"[^,.!?;]*", _MARK, s)
            s = re.sub(r"(?i)\b" + _EN_LEFT_GLUE + r"\s*" + _MARK, _MARK, s)
            s = re.sub(r"(?i)" + _MARK + r"\s*" + _EN_RIGHT_GLUE + r"\b", _MARK, s)
            s = re.sub(r"(?i)" + _EN_RANK + r"\s*" + _MARK, _MARK, s)
        s = re.sub(_MARK + r"(\s*" + _MARK + r")+", _MARK, s)
        if s == before:
            break
    if korean:
        if re.search(_MARK + r"[가-힣]", s):
            return ""  # the removed phrase was glued to a following word
        if re.search(_MARK + r"\s*" + _KO_PARTICLE + r"(?=[\s.,!?]|$)", s):
            return ""  # a particle tying the phrase to the verb would be left hanging
        if re.search(_MARK + r"\s*" + _KO_DEPENDENT + r"(?=[\s.,!?]|$)", s):
            return ""  # a predicate that only described the removed phrase would be left hanging
    s = s.replace(_MARK, " ")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([.,!?;:)])", r"\1", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"^[\s,;:.!?-]+", "", s).strip()
    if not s or not re.search(r"\w", s):
        return ""
    if analyze_listing(s)["findings"]:
        return ""
    if not korean and starts_removed:
        first = s.split()[0].lower()
        if re.fullmatch(_EN_START_BAD, first):
            return ""  # "in our shop." is not a sentence on its own
        if re.match(r"[A-Z]", sentence.strip()):
            s = s[0].upper() + s[1:]
    if is_title:
        return s
    if not korean and re.match(r"[a-z]", s) and re.match(r"[A-Z]", sentence.strip()):
        return ""
    want_end = bool(re.search(r"[.!?。]$", sentence.strip()))
    if want_end and not re.search(r"[.!?。]$", s):
        return ""
    if sentence_ok(s, korean, False, False):
        return ""
    return s


def fallback_gap(plan: FieldPlan, gap: Gap) -> str:
    korean = has_hangul(plan.text)
    out = []
    for i in gap.sentences:
        a, b = plan.sentences[i]
        spans = [(max(c.start, a) - a, min(c.end, b) - a) for c in gap.claims if c.start < b and a < c.end]
        cleaned = remove_cleanly(plan.text[a:b], spans, korean, plan.is_title)
        if cleaned:
            out.append(cleaned)
    return " ".join(out)


# ------------------------------------------------------------- applying

@dataclass
class GapResult:
    claim_ids: list[str]
    before: str
    after: str
    source: str            # "beam", "cleanup" or "kept"
    note: str = ""


@dataclass
class FieldRewrite:
    sku: str
    column: str
    source: str
    before: str
    after: str
    gaps: list[GapResult] = field(default_factory=list)
    note: str = ""


def align(plan: FieldPlan, proposal: str) -> list[str] | None:
    """Split Beam's field text into one segment per gap, using the kept sentences as anchors."""
    anchors = plan.kept_sentences()
    pos, pieces = 0, []
    for anchor in anchors:
        idx = proposal.find(anchor, pos)
        if idx < 0:
            return None
        pieces.append(proposal[pos:idx])
        pos = idx + len(anchor)
    pieces.append(proposal[pos:])
    # pieces[k] is the text before anchor k; map to gaps by their position among kept sentences
    segments = []
    for g in plan.gaps:
        k = sum(1 for i in plan.keep if i < g.sentences[0])
        segments.append(pieces[k])
    # two gaps can never share a piece (they would be one gap), but a piece without a gap must be empty
    used = {sum(1 for i in plan.keep if i < g.sentences[0]) for g in plan.gaps}
    if any(pieces[k].strip() for k in range(len(pieces)) if k not in used):
        return None
    return segments


def build_field(plan: FieldPlan, proposal, guard_add) -> FieldRewrite:
    """Assemble the new field text from Beam's proposal (or None) and the fallbacks."""
    segments = align(plan, proposal) if isinstance(proposal, str) and proposal.strip() else None
    if isinstance(proposal, str) and proposal.strip() and segments is None:
        guard_add(plan.source, proposal, "a sentence without a flagged claim was changed or moved")
    results: list[GapResult] = []
    chosen: list[str] = []
    for gi, g in enumerate(plan.gaps):
        others = " ".join(plan.text[a:b] for i, (a, b) in enumerate(plan.sentences) if i not in g.sentences)
        ids = [c.id for c in g.claims]
        if segments is not None:
            why = check_gap(plan, g, segments[gi], others)
            if not why:
                chosen.append(segments[gi].strip())
                results.append(GapResult(ids, g.text(plan.text), segments[gi].strip(), "beam"))
                continue
            guard_add(",".join(ids), segments[gi].strip(), why)
            note = why
        else:
            note = "no usable rewrite from Beam" if proposal is not None else ""
        fb = fallback_gap(plan, g)
        chosen.append(fb)
        results.append(GapResult(ids, g.text(plan.text), fb, "cleanup", note))
    pieces, gi = [], 0
    i = 0
    while i < len(plan.sentences):
        if i in plan.keep:
            a, b = plan.sentences[i]
            pieces.append(plan.text[a:b])
            i += 1
        else:
            pieces.append(chosen[gi])
            i = plan.gaps[gi].sentences[-1] + 1
            gi += 1
    after = " ".join(p for p in pieces if p.strip())
    fr = FieldRewrite(plan.sku, plan.column, plan.source, plan.text, after, results)
    if not after.strip():
        fr.after = plan.text
        fr.note = "nothing would be left; kept as is for your edit"
        for r in results:
            r.after, r.source = r.before, "kept"
    return fr
