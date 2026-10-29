"""Turning a Review into HTML, tables and CSV downloads. All seller text is escaped."""

from __future__ import annotations

import csv
import io
from html import escape

from .catalog import Catalog
from .i18n import t
from .pipeline import Claim, Review, diff_words


def _reason(c: Claim, lang: str) -> str:
    parts = []
    if c.beam_reason:
        parts.append(c.beam_reason)
    rule = c.rule_reason_ko if (lang == "ko" and c.rule_reason_ko) else c.rule_reason
    if rule:
        parts.append(rule)
    if c.label_note and c.label_note not in parts:
        parts.append(c.label_note)
    return " ".join(parts)


def _evidence(c: Claim, lang: str) -> str:
    if c.citations:
        return " | ".join(f"[{x.source}] \"{x.quote}\"" for x in c.citations)
    return t(lang, "none") if c.label != "not_checked" else ""


def _rewrite(c: Claim, lang: str) -> str:
    """What the sentence holding this claim became."""
    if c.label == "supported":
        return t(lang, "keep")
    if c.rewrite_from not in ("beam", "cleanup"):
        return t(lang, "needs_edit")
    text = c.rewrite or t(lang, "sentence_removed")
    return f"{text} ({t(lang, 'rewrite_from')[c.rewrite_from]})"


def diff_html(before: str, after: str) -> str:
    parts = []
    for op, text in diff_words(before, after):
        if op == "same":
            parts.append(escape(text))
        elif op == "del":
            parts.append(f"<del class='hc-del'>{escape(text)}</del>")
        else:
            parts.append(f"<ins class='hc-ins'>{escape(text)}</ins>")
    return "".join(parts)


def _field_blocks(review: Review, sku: str, lang: str) -> str:
    blocks = []
    for fr in review.field_rewrites:
        if fr.sku != sku:
            continue
        if fr.after == fr.before:
            body = f"<div class='hc-after'>{escape(fr.before)}</div><div class='hc-small'>{escape(t(lang, 'field_kept'))}</div>"
        else:
            body = (f"<div class='hc-diff'>{diff_html(fr.before, fr.after)}</div>"
                    f"<div class='hc-small'>{escape(t(lang, 'before'))}: {escape(fr.before)}</div>"
                    f"<div class='hc-after'><b>{escape(t(lang, 'after'))}:</b> {escape(fr.after)}</div>")
        blocks.append(f"<div class='hc-field'><div class='hc-small'><b>{escape(fr.column)}</b></div>{body}</div>")
    return "".join(blocks)


def _found_by(c: Claim, lang: str) -> str:
    names = t(lang, "found_by")
    return " + ".join(names[o] for o in c.origin)


def counts(review: Review, catalog: Catalog) -> dict:
    labels = {k: 0 for k in ("supported", "contradicted", "no_evidence", "not_checked")}
    for c in review.claims:
        labels[c.label] = labels.get(c.label, 0) + 1
    return dict(products=len(catalog.products), flagged=len({c.sku for c in review.claims}),
                claims=len(review.claims), **labels)


def findings_rows(review: Review, lang: str) -> list[list[str]]:
    labels = t(lang, "labels")
    return [[c.sku, c.column, c.quote, _found_by(c, lang), _reason(c, lang), _evidence(c, lang),
             labels.get(c.label, c.label), _rewrite(c, lang)] for c in review.claims]


def findings_csv(review: Review, lang: str) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(t(lang, "cols"))
    w.writerows(findings_rows(review, lang))
    return "﻿" + buf.getvalue()


def guard_rows(review: Review, lang: str) -> list[list[str]]:
    return [[g.step, g.item, g.text, g.reason] for g in review.guard]


def guard_html(review: Review, lang: str) -> str:
    if review.mode == "local" or (review.quotes_checked == 0 and not review.guard):
        return f"<p class='hc-muted'>{escape(t(lang, 'guard_none'))}</p>"
    head = escape(t(lang, "guard_summary", accepted=review.quotes_accepted, checked=review.quotes_checked,
                    rejected=len(review.guard)))
    rows = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in r) + "</tr>" for r in guard_rows(review, lang))
    table = ""
    if rows:
        cols = "".join(f"<th>{escape(h)}</th>" for h in t(lang, "guard_cols"))
        table = f"<div class='hc-scroll'><table class='hc-table'><thead><tr>{cols}</tr></thead><tbody>{rows}</tbody></table></div>"
    return f"<div class='hc-guard'><p>{head}</p>{table}</div>"


def report_html(review: Review, catalog: Catalog, lang: str) -> str:
    labels = t(lang, "labels")
    by_sku: dict[str, list[Claim]] = {}
    for c in review.claims:
        by_sku.setdefault(c.sku, []).append(c)
    out = [f"<div class='hc-report'><p class='hc-summary'>{escape(t(lang, 'summary', **counts(review, catalog)))}</p>",
           f"<p class='hc-disclaimer'>{escape(t(lang, 'disclaimer'))}</p>"]
    title_col = catalog.copy_cols[0]
    clean = []
    cols = "".join(f"<th>{escape(h)}</th>" for h in t(lang, "card_cols"))
    for p in catalog.products:
        claims = by_sku.get(p.sku, [])
        if not claims:
            clean.append(p.sku)
            continue
        rows = []
        for c in claims:
            related = ""
            if c.related:
                related = f"<div class='hc-related'>{escape(t(lang, 'related'))}: {escape(', '.join(c.related))}</div>"
            rows.append(
                "<tr>"
                f"<td><mark class='hc-mark'>{escape(c.quote)}</mark><div class='hc-small'>{escape(c.column)}, {escape(_found_by(c, lang))}</div></td>"
                f"<td>{escape(_reason(c, lang))}{related}</td>"
                f"<td class='hc-evidence'>{escape(_evidence(c, lang))}</td>"
                f"<td><span class='hc-label hc-{escape(c.label)}'>{escape(labels.get(c.label, c.label))}</span></td>"
                f"<td>{escape(_rewrite(c, lang))}</td>"
                "</tr>")
        out.append(
            f"<details class='hc-card' open><summary><b>{escape(p.sku)}</b> {escape(p.cells.get(title_col, ''))}"
            f" <span class='hc-count'>{len(claims)}</span></summary>"
            f"{_field_blocks(review, p.sku, lang)}"
            f"<div class='hc-scroll'><table class='hc-table'><thead><tr>{cols}</tr></thead><tbody>{''.join(rows)}</tbody></table></div></details>")
    if clean:
        out.append(f"<p class='hc-muted'>{escape(t(lang, 'clean_products', skus=', '.join(clean)))}</p>")
    out.append("</div>")
    return "".join(out)


CSS = """
.hc-report{font-size:14px;line-height:1.45}
.hc-summary{font-weight:600}
.hc-disclaimer{padding:8px 12px;border-left:4px solid #c58b00;background:rgba(197,139,0,.08);border-radius:4px}
.hc-card{border:1px solid rgba(128,128,128,.35);border-radius:8px;padding:6px 10px;margin:10px 0}
.hc-card summary{cursor:pointer;padding:4px 0}
.hc-count{display:inline-block;min-width:20px;padding:0 6px;border-radius:10px;background:rgba(128,128,128,.2);text-align:center;font-size:12px}
.hc-table{width:100%;border-collapse:collapse;margin-top:6px}
.hc-table th,.hc-table td{border-top:1px solid rgba(128,128,128,.25);padding:6px;text-align:left;vertical-align:top}
.hc-mark{background:rgba(230,170,40,.35);color:inherit;padding:0 2px;border-radius:2px}
.hc-small,.hc-related{font-size:12px;opacity:.75;margin-top:2px}
.hc-evidence{font-family:ui-monospace,Menlo,monospace;font-size:12px;word-break:break-word}
.hc-label{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600;white-space:nowrap}
.hc-supported{background:rgba(40,160,90,.18);color:#1d7a46}
.hc-contradicted{background:rgba(210,60,60,.18);color:#b02a2a}
.hc-no_evidence{background:rgba(200,140,20,.2);color:#8a5a00}
.hc-not_checked{background:rgba(128,128,128,.2)}
.hc-muted{opacity:.75}
.hc-guard p{margin:4px 0 8px}
.hc-field{margin:6px 0 8px;padding:6px 8px;border-radius:6px;background:rgba(128,128,128,.08)}
.hc-diff{margin:2px 0 4px}
.hc-del{background:rgba(210,60,60,.18);text-decoration:line-through}
.hc-ins{background:rgba(40,160,90,.2);text-decoration:none}
.hc-after{margin-top:2px}
@media (prefers-color-scheme: dark){.hc-supported{color:#7fd8a4}.hc-contradicted{color:#ff9b9b}.hc-no_evidence{color:#f0c060}}
.hc-scroll{overflow-x:auto}
@media (max-width:640px){.hc-table{min-width:560px}}
"""
