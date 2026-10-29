"""Reading a store catalog (CSV / XLSX) and evidence documents (text / PDF).

Every piece of text the model may quote gets a stable source id:

* catalog cells:   ``<sku>/<column header>``     e.g. ``EN-003/material``
* evidence lines:  ``<file name>#L<line number>`` e.g. ``supplier_notes.txt#L12``

The verifier checks model quotes against exactly these strings.
"""

from __future__ import annotations

import csv
import io
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_FILE_BYTES = int(os.environ.get("MAX_FILE_BYTES", str(5 * 1024 * 1024)))
MAX_ROWS = int(os.environ.get("MAX_CATALOG_ROWS", "2000"))
MAX_EVIDENCE_FILES = 10

# Header aliases (lower-cased, spaces/underscores removed) -> role
SKU_ALIASES = {"sku", "id", "productid", "itemid", "code", "productcode", "itemcode",
               "상품코드", "품번", "상품번호", "코드", "관리코드"}
TITLE_ALIASES = {"title", "name", "productname", "producttitle", "itemname",
                 "상품명", "제목", "제품명"}
DESCRIPTION_ALIASES = {"description", "desc", "details", "body", "productdescription", "copy",
                       "상세설명", "설명", "상품설명", "상세", "본문"}

_NEWLINES = re.compile(r"\s*[\r\n]+\s*")


class CatalogError(ValueError):
    """A problem with the uploaded file that the seller can fix."""


def _key(header: str) -> str:
    return re.sub(r"[\s_\-]+", "", header.strip().lower())


def clean_cell(value) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.lower() == "nan":
        return ""
    return _NEWLINES.sub(" ", text).strip()


@dataclass
class Product:
    row: int                       # 1-based data row number in the file
    sku: str
    cells: dict[str, str]          # header -> cleaned text, in file order

    def source_id(self, header: str) -> str:
        return f"{self.sku}/{header}"


@dataclass
class Catalog:
    headers: list[str]
    sku_col: str
    copy_cols: list[str]           # columns that are seller copy (checked by rules, may be rewritten)
    spec_cols: list[str]           # everything else (material, size chart, certifications ...)
    products: list[Product]
    name: str = "catalog"

    def sources(self) -> dict[str, str]:
        out = {}
        for p in self.products:
            for h in self.copy_cols + self.spec_cols:
                v = p.cells.get(h, "")
                if v:
                    out[p.source_id(h)] = v
        return out

    def copy_sources(self) -> dict[str, tuple[Product, str]]:
        return {p.source_id(h): (p, h) for p in self.products for h in self.copy_cols if p.cells.get(h)}


@dataclass
class EvidenceDoc:
    name: str
    lines: list[tuple[int, str]] = field(default_factory=list)  # (line number, text), non-empty only

    def sources(self) -> dict[str, str]:
        return {f"{self.name}#L{n}": t for n, t in self.lines}


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise CatalogError("Could not read the file's text encoding. Save it as UTF-8 CSV and try again.")


def _rows_from_csv(raw: bytes) -> list[list[str]]:
    text = _decode(raw)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return [row for row in csv.reader(io.StringIO(text), dialect)]


def _rows_from_xlsx(raw: bytes) -> list[list[str]]:
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception as exc:  # corrupt or not really xlsx
        raise CatalogError("Could not open the spreadsheet. Check that it is a valid .xlsx file.") from exc
    ws = wb.worksheets[0]
    rows = [["" if v is None else str(v) for v in row] for row in ws.iter_rows(values_only=True)]
    wb.close()
    return rows


def parse_catalog_bytes(raw: bytes, filename: str) -> Catalog:
    if len(raw) > MAX_FILE_BYTES:
        raise CatalogError(f"The catalog file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")
    suffix = Path(filename).suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        rows = _rows_from_xlsx(raw)
    elif suffix in (".csv", ".tsv", ".txt"):
        rows = _rows_from_csv(raw)
    else:
        raise CatalogError("Upload the catalog as .csv or .xlsx.")
    rows = [r for r in rows if any(clean_cell(c) for c in r)]
    if len(rows) < 2:
        raise CatalogError("The catalog needs a header row and at least one product row.")
    headers = [clean_cell(h) for h in rows[0]]
    # name blank or duplicate headers so every column has a unique id
    seen: dict[str, int] = {}
    for i, h in enumerate(headers):
        h = h or f"column_{i + 1}"
        h = h.replace("/", "-").replace("#", "-")
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 1
        headers[i] = h
    keys = [_key(h) for h in headers]

    def find(aliases):
        for h, k in zip(headers, keys):
            if k in aliases:
                return h
        return None

    sku_col = find(SKU_ALIASES)
    title_col = find(TITLE_ALIASES)
    desc_col = find(DESCRIPTION_ALIASES)
    copy_cols = [c for c in (title_col, desc_col) if c]
    if not copy_cols:
        raise CatalogError("Could not find a title or description column (for example: title, description, 상품명, 상세설명).")
    body = rows[1:]
    if len(body) > MAX_ROWS:
        raise CatalogError(f"The catalog has {len(body)} rows. The limit is {MAX_ROWS}.")
    products = []
    used_skus: set[str] = set()
    for n, row in enumerate(body, start=1):
        cells = {h: clean_cell(row[i]) if i < len(row) else "" for i, h in enumerate(headers)}
        sku = (cells.get(sku_col, "") if sku_col else "") or f"ROW-{n}"
        sku = sku.replace("/", "-").replace("#", "-")
        if sku in used_skus:
            sku = f"{sku}~row{n}"
        used_skus.add(sku)
        products.append(Product(row=n, sku=sku, cells=cells))
    spec_cols = [h for h in headers if h not in copy_cols and h != sku_col]
    return Catalog(headers=headers, sku_col=sku_col or "", copy_cols=copy_cols, spec_cols=spec_cols,
                   products=products, name=Path(filename).name)


def parse_catalog_file(path: str | os.PathLike) -> Catalog:
    p = Path(path)
    if p.stat().st_size > MAX_FILE_BYTES:
        raise CatalogError(f"The catalog file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")
    return parse_catalog_bytes(p.read_bytes(), p.name)


def parse_evidence_bytes(raw: bytes, filename: str) -> EvidenceDoc:
    if len(raw) > MAX_FILE_BYTES:
        raise CatalogError(f"Evidence file {filename} is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")
    name = Path(filename).name.replace("#", "-").replace("/", "-")
    if name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise CatalogError(f"Could not read text from {name}. Scanned PDFs need to be converted to text first.") from exc
    else:
        text = _decode(raw)
    lines = []
    for n, line in enumerate(text.splitlines(), start=1):
        t = re.sub(r"[ \t ]+", " ", line).strip()
        if t:
            lines.append((n, t))
    return EvidenceDoc(name=name, lines=lines)


def parse_evidence_file(path: str | os.PathLike) -> EvidenceDoc:
    p = Path(path)
    return parse_evidence_bytes(p.read_bytes(), p.name)


def all_sources(catalog: Catalog, docs: list[EvidenceDoc]) -> dict[str, str]:
    out = catalog.sources()
    for d in docs:
        out.update(d.sources())
    return out


def render_corpus(catalog: Catalog, docs: list[EvidenceDoc]) -> str:
    """The text Beam reads: one source per line, ``<source id> :: <text>``."""
    parts = [f"=== CATALOG: {catalog.name} ({len(catalog.products)} products) ===",
             f"Seller copy columns: {', '.join(catalog.copy_cols)}",
             f"Spec / evidence columns: {', '.join(catalog.spec_cols) or '(none)'}", ""]
    for p in catalog.products:
        parts.append(f"--- product {p.sku} (row {p.row}) ---")
        for h in catalog.copy_cols + catalog.spec_cols:
            v = p.cells.get(h, "")
            if v:
                parts.append(f"{p.source_id(h)} :: {v}")
    for d in docs:
        parts += ["", f"=== EVIDENCE DOCUMENT: {d.name} ==="]
        parts += [f"{d.name}#L{n} :: {t}" for n, t in d.lines]
    if not docs:
        parts += ["", "=== EVIDENCE DOCUMENTS: none provided ==="]
    return "\n".join(parts)


def corrected_catalog_csv(catalog: Catalog, new_cells: dict[str, dict[str, str]], notes: dict[str, str]) -> str:
    """Original columns with rewritten copy, plus a review note column. UTF-8 with BOM for spreadsheet apps."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(catalog.headers + ["review_note"])
    for p in catalog.products:
        cells = dict(p.cells)
        cells.update(new_cells.get(p.sku, {}))
        w.writerow([cells.get(h, "") for h in catalog.headers] + [notes.get(p.sku, "")])
    return "﻿" + buf.getvalue()
