"""The app works with no token: local rules plus a plain message."""

import csv
import io

import pytest


@pytest.fixture()
def app(monkeypatch, tmp_path):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.setenv("BEAM_USAGE_FILE", str(tmp_path / "usage.json"))
    import importlib
    import app as app_module
    importlib.reload(app_module)
    return app_module


def test_example_without_token_shows_local_rules_and_cache_notice(app):
    status, report, table, guard, corrected, findings, state = app.review_example("en", "en", True)
    assert "not been generated yet" in status or "saved Beam result" in status
    assert "Beam calls left today: 40 of 40" in status
    assert "EN-010" in report and "second look" in report
    assert len(table) > 10
    rows = list(csv.reader(io.open(corrected, encoding="utf-8-sig")))
    assert rows[0][-1] == "review_note" and len(rows) == 31


def test_upload_without_token_says_beam_is_not_connected(app):
    from honest_catalog.examples import EXAMPLES
    ex = EXAMPLES["ko"]
    out = app.review_upload(str(ex["catalog"]), [str(p) for p in ex["evidence"]], "ko")
    assert "토큰" in out[0] and "KO-009" in out[1]


def test_language_switch_rerenders(app):
    state = app.review_example("ko", "en", False)[-1]
    out = app.switch_language("ko", state)
    assert "확인 전" in out[15]  # report html in Korean labels
    assert app.build() is not None
