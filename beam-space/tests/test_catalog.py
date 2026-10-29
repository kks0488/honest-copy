import csv
import io

import pytest
from openpyxl import Workbook

from honest_catalog import catalog as cat_mod
from honest_catalog.catalog import (CatalogError, all_sources, corrected_catalog_csv, parse_catalog_bytes,
                                    parse_evidence_bytes, render_corpus)
from honest_catalog.examples import EXAMPLES, load_example


def _csv(rows, encoding="utf-8"):
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode(encoding)


def test_examples_have_30_products_and_detect_columns():
    for key in ("en", "ko"):
        catalog, docs = load_example(key)
        assert len(catalog.products) == 30
        assert len(catalog.copy_cols) == 2
        assert catalog.sku_col
        assert len(docs) == 2 and all(d.lines for d in docs)
    ko, _ = load_example("ko")
    assert ko.copy_cols == ["상품명", "상세설명"] and ko.sku_col == "상품코드"
    assert "소재" in ko.spec_cols


def test_csv_with_quotes_commas_and_newlines():
    raw = _csv([["sku", "title", "description", "material"],
                ["A-1", "Apron", "Soft, washed linen.\nTwo pockets.", "55% linen, 45% cotton"]])
    c = parse_catalog_bytes(raw, "shop.csv")
    p = c.products[0]
    assert p.sku == "A-1"
    assert p.cells["description"] == "Soft, washed linen. Two pockets."
    assert c.spec_cols == ["material"]
    assert all_sources(c, [])["A-1/material"] == "55% linen, 45% cotton"


def test_korean_excel_csv_in_cp949():
    raw = _csv([["상품코드", "상품명", "상세설명"], ["K-1", "앞치마", "국내 1위 앞치마"]], encoding="cp949")
    c = parse_catalog_bytes(raw, "목록.csv")
    assert c.products[0].cells["상세설명"] == "국내 1위 앞치마"


def test_xlsx_parsing(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["SKU", "Product Name", "Description", "Origin"])
    ws.append(["X-1", "Mug", "Hand-glazed stoneware.", "Portugal"])
    ws.append([None, None, None, None])
    ws.append([1002, "Bowl", "No.1 bowl", None])
    path = tmp_path / "shop.xlsx"
    wb.save(path)
    c = cat_mod.parse_catalog_file(path)
    assert c.copy_cols == ["Product Name", "Description"]
    assert [p.sku for p in c.products] == ["X-1", "1002"]
    assert c.products[1].cells["Origin"] == ""


def test_missing_sku_and_duplicate_skus_get_unique_ids():
    raw = _csv([["title"], ["One"], ["Two"]])
    assert [p.sku for p in parse_catalog_bytes(raw, "a.csv").products] == ["ROW-1", "ROW-2"]
    raw = _csv([["sku", "title"], ["S/1", "One"], ["S/1", "Two"]])
    skus = [p.sku for p in parse_catalog_bytes(raw, "a.csv").products]
    assert len(set(skus)) == 2 and all("/" not in s for s in skus)


def test_errors_are_plain():
    with pytest.raises(CatalogError, match="title or description"):
        parse_catalog_bytes(_csv([["sku", "price"], ["A", "3"]]), "a.csv")
    with pytest.raises(CatalogError, match="header row"):
        parse_catalog_bytes(_csv([["sku", "title"]]), "a.csv")
    with pytest.raises(CatalogError, match=".csv or .xlsx"):
        parse_catalog_bytes(b"x", "a.json")
    with pytest.raises(CatalogError):
        parse_catalog_bytes(b"not a zip", "a.xlsx")


def test_row_and_size_limits(monkeypatch):
    monkeypatch.setattr(cat_mod, "MAX_ROWS", 3)
    rows = [["title"]] + [[f"t{i}"] for i in range(4)]
    with pytest.raises(CatalogError, match="limit is 3"):
        parse_catalog_bytes(_csv(rows), "a.csv")
    monkeypatch.setattr(cat_mod, "MAX_FILE_BYTES", 10)
    with pytest.raises(CatalogError, match="larger"):
        parse_catalog_bytes(b"title\n" + b"x" * 20, "a.csv")


def test_evidence_text_lines_keep_original_numbers():
    doc = parse_evidence_bytes("Header\n\nLine three  has  spaces\n".encode(), "notes.txt")
    assert doc.lines == [(1, "Header"), (3, "Line three has spaces")]
    assert doc.sources() == {"notes.txt#L1": "Header", "notes.txt#L3": "Line three has spaces"}


def _tiny_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % off for off in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def test_pdf_evidence_text():
    doc = parse_evidence_bytes(_tiny_pdf("Oven safe to 220 C"), "report.pdf")
    assert any("Oven safe to 220 C" in t for _, t in doc.lines)


def test_corpus_lists_every_source_once():
    catalog, docs = load_example("en")
    corpus = render_corpus(catalog, docs)
    for sid, text in all_sources(catalog, docs).items():
        assert f"{sid} :: {text}" in corpus


def test_corrected_csv_keeps_columns_and_adds_note():
    catalog, _ = load_example("en")
    out = corrected_catalog_csv(catalog, {"EN-001": {"description": "New text."}}, {"EN-001": "note"},
                                {"EN-001": "description: [-old-] {+new+}"})
    rows = list(csv.reader(io.StringIO(out.lstrip("\ufeff"))))
    assert rows[0] == catalog.headers + ["review_note", "changes", "title (before)", "description (before)"]
    n = len(catalog.headers)
    assert rows[1][2] == "New text." and rows[1][n:] == ["note", "description: [-old-] {+new+}", "",
                                                         catalog.products[0].cells["description"]]
    assert rows[2][2] == catalog.products[1].cells["description"] and rows[2][n:] == ["", "", "", ""]
    assert EXAMPLES["en"]["catalog"].exists()
