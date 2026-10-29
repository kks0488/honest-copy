"""Honest Copy Catalog: a second look at a whole store catalog, with Beam."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import gradio as gr
import pandas as pd

from honest_catalog import pipeline
from honest_catalog.beam import BeamClient
from honest_catalog.budget import DailyBudget
from honest_catalog.catalog import CatalogError, MAX_EVIDENCE_FILES, parse_catalog_file, parse_evidence_file
from honest_catalog.examples import EXAMPLES, load_cached, load_example
from honest_catalog.i18n import t
from honest_catalog.pipeline import Review, review_catalog
from honest_catalog.report import CSS, findings_csv, findings_rows, guard_html, report_html

BUDGET = DailyBudget()


def _status(review: Review, lang: str, extra: list[str]) -> str:
    lines = []
    if review.mode == "live":
        lines.append(t(lang, "mode_live", calls=review.calls_made))
    elif review.mode == "cached":
        lines.append(t(lang, "mode_cached", when=review.generated_at or "?"))
    else:
        lines.append(t(lang, "mode_local"))
    for key in list(review.messages) + extra:
        if key == "live":
            continue
        lines.append(t(lang, key, limit=f"{pipeline.MAX_INPUT_CHARS:,}"))
    for s in review.steps:
        lines.append(f"Beam {s.step}: {'ok' if s.ok else 'failed'} ({s.detail})")
    lines.append(t(lang, "calls_left", n=BUDGET.remaining(), cap=BUDGET.cap))
    return "\n\n".join(f"- {line}" for line in lines)


def _load_source(source: dict):
    if source["kind"] == "example":
        return load_example(source["key"])
    catalog = parse_catalog_file(source["catalog"])
    docs = [parse_evidence_file(p) for p in source["evidence"]]
    return catalog, docs


def _render(state: dict | None, lang: str):
    if not state:
        empty = pd.DataFrame(columns=t(lang, "cols"))
        return "", "", empty, "", None, None
    review = Review.from_dict(state["review"])
    catalog, _ = _load_source(state["source"])
    out_dir = Path(tempfile.mkdtemp(prefix="honest_copy_"))
    corrected = out_dir / "corrected_catalog.csv"
    corrected.write_text(pipeline.corrected_csv(catalog, review), encoding="utf-8")
    findings = out_dir / "findings.csv"
    findings.write_text(findings_csv(review, lang), encoding="utf-8")
    table = pd.DataFrame(findings_rows(review, lang), columns=t(lang, "cols"))
    return (_status(review, lang, state.get("extra", [])), report_html(review, catalog, lang), table,
            guard_html(review, lang), str(corrected), str(findings))


def review_upload(catalog_file, evidence_files, lang, progress=gr.Progress()):
    if not catalog_file:
        raise gr.Error(t(lang, "no_file"))
    evidence = [str(f) for f in (evidence_files or [])][:MAX_EVIDENCE_FILES]
    source = {"kind": "upload", "catalog": str(catalog_file), "evidence": evidence}
    try:
        catalog, docs = _load_source(source)
    except CatalogError as exc:
        raise gr.Error(str(exc))
    review = review_catalog(catalog, docs, BeamClient(budget=BUDGET), progress=progress)
    state = {"review": review.to_dict(), "source": source, "extra": []}
    return (*_render(state, lang), state)


def review_example(key: str, lang: str, live: bool, progress=gr.Progress()):
    source = {"kind": "example", "key": key}
    catalog, docs = load_example(key)
    extra: list[str] = []
    client = BeamClient(budget=BUDGET)
    review = None
    if live and client.status()[0]:
        review = review_catalog(catalog, docs, client, progress=progress)
    else:
        # CACHED RESULT: produced only by scripts/make_cache.py with a real token.
        review, status = load_cached(key)
        if review is None:
            review = review_catalog(catalog, docs, None)
            review.messages = []
            extra.append("cache_stale" if status == "stale" else "cache_missing")
    state = {"review": review.to_dict(), "source": source, "extra": extra}
    return (*_render(state, lang), state)


def review_example_en(lang, live, progress=gr.Progress()):
    return review_example("en", lang, live, progress)


def review_example_ko(lang, live, progress=gr.Progress()):
    return review_example("ko", lang, live, progress)


def switch_language(lang: str, state):
    rendered = _render(state, lang)
    return (
        gr.update(value=f"# {t(lang, 'title')}\n\n{t(lang, 'intro')}\n\n> {t(lang, 'disclaimer')}"),
        gr.update(label=t(lang, "catalog")),
        gr.update(value=t(lang, "catalog_hint")),
        gr.update(label=t(lang, "evidence")),
        gr.update(value=t(lang, "run")),
        gr.update(value=t(lang, "example_en")),
        gr.update(value=t(lang, "example_ko")),
        gr.update(label=t(lang, "live_on_example")),
        gr.update(label=t(lang, "how")),
        gr.update(value=t(lang, "how_body")),
        gr.update(value=f"### {t(lang, 'status')}"),
        gr.update(value=f"### {t(lang, 'report')}"),
        gr.update(value=f"### {t(lang, 'table')}"),
        gr.update(value=f"### {t(lang, 'guard')}"),
        rendered[0], rendered[1], rendered[2], rendered[3],
        gr.update(label=t(lang, "download_catalog"), value=rendered[4]),
        gr.update(label=t(lang, "download_findings"), value=rendered[5]),
    )


def build() -> gr.Blocks:
    lang0 = "en"
    with gr.Blocks(title="Honest Copy Catalog") as demo:
        state = gr.State(None)
        lang = gr.Radio(["en", "ko"], value=lang0, label=t(lang0, "lang"),
                        info="English / 한국어")
        header = gr.Markdown(f"# {t(lang0, 'title')}\n\n{t(lang0, 'intro')}\n\n> {t(lang0, 'disclaimer')}")
        with gr.Row():
            with gr.Column(scale=3):
                catalog_in = gr.File(label=t(lang0, "catalog"), file_types=[".csv", ".xlsx"], type="filepath")
                hint = gr.Markdown(t(lang0, "catalog_hint"))
                evidence_in = gr.File(label=t(lang0, "evidence"), file_count="multiple",
                                      file_types=[".txt", ".md", ".pdf"], type="filepath")
                run_btn = gr.Button(t(lang0, "run"), variant="primary")
            with gr.Column(scale=2):
                ex_en = gr.Button(t(lang0, "example_en"))
                ex_ko = gr.Button(t(lang0, "example_ko"))
                live_cb = gr.Checkbox(False, label=t(lang0, "live_on_example"))
                with gr.Accordion(t(lang0, "how"), open=False) as how:
                    how_body = gr.Markdown(t(lang0, "how_body"))
        status_h = gr.Markdown(f"### {t(lang0, 'status')}")
        status = gr.Markdown()
        report_h = gr.Markdown(f"### {t(lang0, 'report')}")
        report = gr.HTML()
        guard_h = gr.Markdown(f"### {t(lang0, 'guard')}")
        guard = gr.HTML()
        with gr.Row():
            dl_catalog = gr.File(label=t(lang0, "download_catalog"), interactive=False)
            dl_findings = gr.File(label=t(lang0, "download_findings"), interactive=False)
        table_h = gr.Markdown(f"### {t(lang0, 'table')}")
        table = gr.Dataframe(value=pd.DataFrame(columns=t(lang0, "cols")), wrap=True, interactive=False)

        outputs = [status, report, table, guard, dl_catalog, dl_findings]
        run_btn.click(review_upload, [catalog_in, evidence_in, lang], outputs + [state])
        ex_en.click(review_example_en, [lang, live_cb], outputs + [state])
        ex_ko.click(review_example_ko, [lang, live_cb], outputs + [state])
        lang.change(switch_language, [lang, state],
                    [header, catalog_in, hint, evidence_in, run_btn, ex_en, ex_ko, live_cb, how, how_body,
                     status_h, report_h, table_h, guard_h] + outputs)
    return demo


demo = build()

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2).launch(css=CSS, server_name=os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0"))
