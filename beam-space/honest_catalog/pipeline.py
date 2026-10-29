"""The review pipeline: local rules, whole-catalog Beam pass, verifier pass, rewrites.

Model calls per review: at most three (audit, verify, rewrite), each over the
whole catalog. Every quote the model returns is checked against the input by
exact substring match before it is shown (see ``check_quote``).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from . import beam as beam_mod
from .beam import BeamCallError, BeamClient, BeamUnavailable, parse_json_answer
from .catalog import Catalog, EvidenceDoc, all_sources, corrected_catalog_csv, render_corpus
from .rules import CATEGORIES, analyze_listing

MAX_INPUT_CHARS = int(os.environ.get("BEAM_MAX_INPUT_CHARS", "400000"))
MAX_CLAIMS = int(os.environ.get("BEAM_MAX_CLAIMS", "150"))
MIN_QUOTE_CHARS = 3
LABELS = ("supported", "contradicted", "no_evidence", "not_checked")
ISSUE_TYPES = ("contradiction", "spec_conflict", "ranking", "unsupported")
_HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def has_hangul(text: str) -> bool:
    return bool(_HANGUL.search(text or ""))


# ------------------------------------------------------------------ data

@dataclass
class Citation:
    source: str
    quote: str
    ok: bool = False
    note: str = ""


@dataclass
class Claim:
    id: str
    sku: str
    column: str
    source: str
    quote: str
    start: int
    end: int
    origin: list[str]                    # "rules" and/or "beam"
    category: str = ""                   # rule category, if any
    rule_id: str = ""
    rule_reason: str = ""
    rule_reason_ko: str = ""
    rule_replacement: str = ""
    beam_types: list[str] = field(default_factory=list)
    beam_reason: str = ""
    related: list[str] = field(default_factory=list)
    label: str = "not_checked"
    label_note: str = ""
    citations: list[Citation] = field(default_factory=list)
    rewrite: str = ""
    rewrite_from: str = ""               # "beam", "rule template" or ""


@dataclass
class GuardEntry:
    step: str        # audit / verify / rewrite
    item: str        # claim id or source id
    text: str        # what the model said
    reason: str      # why it was rejected


@dataclass
class StepStatus:
    step: str
    ok: bool
    detail: str


@dataclass
class Review:
    mode: str                                    # live / cached / local
    claims: list[Claim]
    guard: list[GuardEntry] = field(default_factory=list)
    steps: list[StepStatus] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)   # message keys for the UI
    quotes_checked: int = 0
    quotes_accepted: int = 0
    model: str = beam_mod.MODEL_ID
    generated_at: str = ""
    calls_made: int = 0
    raw_answers: dict = field(default_factory=dict)     # final answers only, never reasoning

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Review":
        claims = []
        for c in data.get("claims", []):
            c = dict(c)
            c["citations"] = [Citation(**x) for x in c.get("citations", [])]
            claims.append(Claim(**c))
        return cls(
            mode=data.get("mode", "cached"), claims=claims,
            guard=[GuardEntry(**g) for g in data.get("guard", [])],
            steps=[StepStatus(**s) for s in data.get("steps", [])],
            messages=list(data.get("messages", [])),
            quotes_checked=data.get("quotes_checked", 0), quotes_accepted=data.get("quotes_accepted", 0),
            model=data.get("model", beam_mod.MODEL_ID), generated_at=data.get("generated_at", ""),
            calls_made=data.get("calls_made", 0), raw_answers=data.get("raw_answers", {}),
        )


# ------------------------------------------------------- quote checking

def check_quote(source_id: str, quote: str, sources: dict[str, str]) -> tuple[bool, str, str]:
    """Exact-substring check of a model quote.

    Returns (ok, source id to show, note). A quote is accepted only if it is an
    exact substring of the named source. If the named id is wrong but the quote
    appears in exactly one other source, the id is corrected and noted. A quote
    found nowhere in the input is rejected.
    """
    if not isinstance(quote, str) or not quote.strip():
        return False, str(source_id), "empty quote"
    if not isinstance(source_id, str):
        source_id = ""
    text = sources.get(source_id)
    long_enough = len(quote.strip()) >= MIN_QUOTE_CHARS
    if text is not None and quote in text:
        if long_enough or quote == text:
            return True, source_id, ""
        return False, source_id, "quote too short to be meaningful"
    hits = [sid for sid, t in sources.items() if quote in t and (long_enough or quote == t)]
    if len(hits) == 1:
        return True, hits[0], f"line id corrected from {source_id or '(none)'}"
    if hits:
        return False, source_id, "quote matches several lines and the named line is wrong"
    return False, source_id, "quote not found in the catalog or evidence"


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


# ------------------------------------------------------------ local pass

def local_claims(catalog: Catalog) -> list[Claim]:
    claims = []
    for p in catalog.products:
        for col in catalog.copy_cols:
            text = p.cells.get(col, "")
            if not text:
                continue
            for f in analyze_listing(text)["findings"]:
                claims.append(Claim(
                    id="", sku=p.sku, column=col, source=p.source_id(col), quote=f.phrase,
                    start=f.start, end=f.end, origin=["rules"], category=f.category, rule_id=f.rule_id,
                    rule_reason=f.explanation, rule_reason_ko=f.explanation_ko, rule_replacement=f.replacement,
                ))
    return claims


def _order_and_number(claims: list[Claim], catalog: Catalog) -> list[Claim]:
    row = {p.sku: i for i, p in enumerate(catalog.products)}
    col = {c: i for i, c in enumerate(catalog.copy_cols)}
    claims.sort(key=lambda c: (row.get(c.sku, 0), col.get(c.column, 0), c.start))
    for i, c in enumerate(claims, start=1):
        c.id = f"C{i:03d}"
    return claims


# ------------------------------------------------------------ Beam passes

def merge_audit_issues(data: dict, claims: list[Claim], catalog: Catalog, sources: dict[str, str],
                       guard: list[GuardEntry]) -> tuple[int, int]:
    """Add whole-catalog issues to the claim list. Returns (accepted, rejected)."""
    copy_sources = catalog.copy_sources()
    issues = data.get("issues", [])
    if not isinstance(issues, list):
        issues = []
    accepted = rejected = 0
    for issue in issues[:MAX_CLAIMS]:
        if not isinstance(issue, dict):
            continue
        sid, quote = issue.get("source", ""), issue.get("quote", "")
        ok, sid2, note = check_quote(sid, quote, sources)
        if ok and sid2 not in copy_sources:
            ok, note = False, "points at a spec or evidence line, not at seller copy"
        if not ok:
            rejected += 1
            guard.append(GuardEntry("audit", str(sid), str(quote)[:200], note))
            continue
        product, col = copy_sources[sid2]
        text = product.cells[col]
        start = text.find(quote)
        end = start + len(quote)
        itype = issue.get("type") if issue.get("type") in ISSUE_TYPES else "unsupported"
        reason = str(issue.get("reason", ""))[:400]
        related = []
        for r in issue.get("related", []) if isinstance(issue.get("related"), list) else []:
            if isinstance(r, str) and r in sources and r not in related and r != sid2:
                related.append(r)
            elif isinstance(r, str) and r not in sources:
                guard.append(GuardEntry("audit", sid2, r[:120], "related line id does not exist"))
        target = next((c for c in claims if c.source == sid2 and _overlaps(c.start, c.end, start, end)), None)
        if target:
            if "beam" not in target.origin:
                target.origin.append("beam")
            if itype not in target.beam_types:
                target.beam_types.append(itype)
            target.beam_reason = target.beam_reason or reason
            target.related += [r for r in related if r not in target.related]
        else:
            claims.append(Claim(id="", sku=product.sku, column=col, source=sid2, quote=quote, start=start,
                                end=end, origin=["beam"], beam_types=[itype], beam_reason=reason, related=related))
        accepted += 1
    return accepted, rejected


def _claims_payload(claims: list[Claim]) -> str:
    items = []
    for c in claims:
        items.append({"id": c.id, "source": c.source, "claim": c.quote,
                      "why_flagged": c.beam_reason or c.rule_reason, "related": c.related})
    return json.dumps(items, ensure_ascii=False, indent=0)


def apply_verification(data: dict, claims: list[Claim], sources: dict[str, str], guard: list[GuardEntry]) -> tuple[int, int]:
    """Apply verifier labels. Returns (quotes checked, quotes accepted)."""
    by_id = {c.id: c for c in claims}
    results = data.get("results", [])
    if not isinstance(results, list):
        results = []
    checked = accepted = 0
    seen = set()
    for res in results:
        if not isinstance(res, dict) or res.get("id") not in by_id or res.get("id") in seen:
            continue
        seen.add(res["id"])
        claim = by_id[res["id"]]
        label = res.get("label") if res.get("label") in ("supported", "contradicted", "no_evidence") else None
        if label is None:
            guard.append(GuardEntry("verify", claim.id, str(res.get("label"))[:60], "unknown label"))
            continue
        good: list[Citation] = []
        cites = res.get("citations", []) if isinstance(res.get("citations"), list) else []
        for cit in cites[:6]:
            if not isinstance(cit, dict):
                continue
            checked += 1
            sid, quote = cit.get("source", ""), cit.get("quote", "")
            ok, sid2, note = check_quote(sid, quote, sources)
            if ok and sid2 == claim.source:
                pos = sources[sid2].find(quote)
                while pos >= 0:
                    if _overlaps(pos, pos + len(quote), claim.start, claim.end):
                        ok, note = False, "cites the flagged claim itself"
                        break
                    pos = sources[sid2].find(quote, pos + 1)
            if ok:
                accepted += 1
                good.append(Citation(sid2, quote, True, note))
            else:
                guard.append(GuardEntry("verify", claim.id, f"{sid}: {str(quote)[:200]}", note))
        claim.citations = good
        claim.label_note = str(res.get("note", ""))[:300]
        if label in ("supported", "contradicted") and not good:
            claim.label = "no_evidence"
            claim.label_note = "Beam's citation did not match the input, so the label was lowered to no evidence."
            guard.append(GuardEntry("verify", claim.id, label, "label lowered: no citation survived the exact-text check"))
        else:
            claim.label = label
    return checked, accepted


def validate_rewrite(claim: Claim, replacement, cell_text: str) -> tuple[bool, str]:
    if not isinstance(replacement, str) or not replacement.strip():
        return False, "empty rewrite"
    replacement = replacement.strip()
    if len(replacement) > max(3 * len(claim.quote), 80):
        return False, "rewrite much longer than the original phrase"
    if (has_hangul(claim.quote) and not has_hangul(replacement)) or (not has_hangul(cell_text) and has_hangul(replacement)):
        return False, "rewrite changed the language"
    facts = cell_text + " " + " ".join(c.quote for c in claim.citations)
    for num in _NUMBER.findall(replacement):
        if num not in facts:
            return False, f"rewrite adds the number {num}, which is not in the seller's data"
    new_text = cell_text[:claim.start] + replacement + cell_text[claim.end:]
    for f in analyze_listing(new_text)["findings"]:
        if _overlaps(f.start, f.end, claim.start, claim.start + len(replacement)):
            return False, f"rewrite still contains a risky phrase ({f.phrase})"
    return True, ""


def needs_rewrite(c: Claim) -> bool:
    return c.label != "supported"


def _rewrite_payload(claims: list[Claim], sources: dict[str, str]) -> str:
    items = []
    for c in claims:
        text = sources[c.source]
        items.append({
            "id": c.id, "language": "ko" if has_hangul(text) else "en",
            "before": text[max(0, c.start - 240):c.start], "phrase": c.quote, "after": text[c.end:c.end + 240],
            "problem": c.label_note or c.beam_reason or c.rule_reason, "label": c.label,
            "facts": [x.quote for x in c.citations],
        })
    return json.dumps(items, ensure_ascii=False, indent=0)


def apply_rewrites(data: dict | None, claims: list[Claim], sources: dict[str, str], guard: list[GuardEntry]) -> None:
    proposals = {}
    if data:
        rows = data.get("rewrites", [])
        for r in rows if isinstance(rows, list) else []:
            if isinstance(r, dict) and isinstance(r.get("id"), str):
                proposals.setdefault(r["id"], r.get("replacement"))
    for c in claims:
        if not needs_rewrite(c):
            continue
        if c.id in proposals:
            ok, why = validate_rewrite(c, proposals[c.id], sources[c.source])
            if ok:
                c.rewrite, c.rewrite_from = proposals[c.id].strip(), "beam"
                continue
            guard.append(GuardEntry("rewrite", c.id, str(proposals[c.id])[:200], why))
        if c.rule_replacement:
            c.rewrite, c.rewrite_from = c.rule_replacement, "rule template"


# --------------------------------------------------------------- driver

def corpus_for(catalog: Catalog, docs: list[EvidenceDoc]) -> str:
    return render_corpus(catalog, docs)


def catalog_fingerprint(catalog: Catalog, docs: list[EvidenceDoc]) -> str:
    return hashlib.sha256(corpus_for(catalog, docs).encode("utf-8")).hexdigest()


def review_catalog(catalog: Catalog, docs: list[EvidenceDoc], client: BeamClient | None = None,
                   progress=None) -> Review:
    def tick(frac, desc):
        if progress:
            progress(frac, desc=desc)

    sources = all_sources(catalog, docs)
    claims = local_claims(catalog)
    review = Review(mode="local", claims=claims)
    tick(0.05, "local rules")

    corpus = corpus_for(catalog, docs)
    live, why = (client.status() if client else (False, "no_token"))
    if live and len(corpus) > MAX_INPUT_CHARS:
        live, why = False, "too_large"
    if not live:
        review.messages.append(why)
        apply_rewrites(None, _order_and_number(claims, catalog), sources, review.guard)
        review.claims = claims
        return review

    review.mode = "live"
    review.generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # 1. whole-catalog pass
    tick(0.15, "Beam reads the whole catalog")
    try:
        reply = client.chat(beam_mod.AUDIT_SYSTEM, "Seller catalog and evidence:\n\n" + corpus)
        review.raw_answers["audit"] = reply.text
        data = parse_json_answer(reply.text)
        acc, rej = merge_audit_issues(data, claims, catalog, sources, review.guard)
        review.steps.append(StepStatus("audit", True, f"{acc} issues kept, {rej} rejected"))
    except (BeamCallError, BeamUnavailable) as exc:
        review.steps.append(StepStatus("audit", False, str(exc)))
    claims = _order_and_number(claims, catalog)[:MAX_CLAIMS]

    # 2. verifier pass
    if claims:
        tick(0.5, "Beam checks each claim against your data")
        try:
            reply = client.chat(beam_mod.VERIFY_SYSTEM,
                                "Seller catalog and evidence:\n\n" + corpus + "\n\n=== CLAIMS TO CHECK ===\n" + _claims_payload(claims))
            review.raw_answers["verify"] = reply.text
            checked, accepted = apply_verification(parse_json_answer(reply.text), claims, sources, review.guard)
            review.quotes_checked += checked
            review.quotes_accepted += accepted
            review.steps.append(StepStatus("verify", True, f"{accepted} of {checked} quotes matched the input exactly"))
        except (BeamCallError, BeamUnavailable) as exc:
            review.steps.append(StepStatus("verify", False, str(exc)))

    # 3. rewrites
    todo = [c for c in claims if needs_rewrite(c)]
    rewrite_data = None
    if todo:
        tick(0.8, "Beam suggests rewrites")
        try:
            reply = client.chat(beam_mod.REWRITE_SYSTEM, "Items to rewrite:\n" + _rewrite_payload(todo, sources))
            review.raw_answers["rewrite"] = reply.text
            rewrite_data = parse_json_answer(reply.text)
            review.steps.append(StepStatus("rewrite", True, f"{len(todo)} lines sent"))
        except (BeamCallError, BeamUnavailable) as exc:
            review.steps.append(StepStatus("rewrite", False, str(exc)))
    apply_rewrites(rewrite_data, claims, sources, review.guard)
    review.claims = claims
    review.calls_made = client.calls_made
    if any(not s.ok for s in review.steps):
        review.messages.append("partial")
    tick(1.0, "done")
    return review


def corrected_cells(catalog: Catalog, review: Review) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Apply accepted rewrites to the catalog. Returns (new cells per sku, review note per sku)."""
    by_source: dict[str, list[Claim]] = {}
    for c in review.claims:
        by_source.setdefault(c.source, []).append(c)
    new_cells: dict[str, dict[str, str]] = {}
    notes: dict[str, list[str]] = {}
    for p in catalog.products:
        for col in catalog.copy_cols:
            sid = p.source_id(col)
            text = p.cells.get(col, "")
            last_start = len(text) + 1
            changed = False
            for c in sorted(by_source.get(sid, []), key=lambda x: x.start, reverse=True):
                label = c.label.replace("_", " ")
                if c.rewrite and c.end <= last_start and text[c.start:c.end] == c.quote:
                    text = text[:c.start] + c.rewrite + text[c.end:]
                    last_start = c.start
                    changed = True
                    notes.setdefault(p.sku, []).append(f"{c.id} {label}: \"{c.quote}\" -> \"{c.rewrite}\"")
                elif c.label != "supported":
                    notes.setdefault(p.sku, []).append(f"{c.id} {label}: \"{c.quote}\" needs your check")
            if changed:
                new_cells.setdefault(p.sku, {})[col] = text
    return new_cells, {k: " | ".join(reversed(v)) for k, v in notes.items()}


def corrected_csv(catalog: Catalog, review: Review) -> str:
    cells, notes = corrected_cells(catalog, review)
    return corrected_catalog_csv(catalog, cells, notes)


def category_label(cat: str) -> str:
    return CATEGORIES.get(cat, {}).get("label", "")
