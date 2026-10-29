---
title: Honest Copy Catalog
emoji: 🧾
colorFrom: yellow
colorTo: green
sdk: gradio
sdk_version: 6.31.0
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
short_description: Check a whole shop catalog for claims that don't add up
---

# Honest Copy Catalog

Small online shops write hundreds of product listings, often copied and pasted between similar items. Over time the copy drifts: one apron says 100% linen while the spec sheet says a linen and cotton blend, three items each claim to be the #1 best seller, a cream says "clinically proven" when the only report on file is a 20-person comfort survey.

Honest Copy Catalog reads the whole catalog the way a careful second reader would. Upload a CSV or XLSX of your products (title, description, and any spec columns you have, such as material, size chart, origin, certifications, care) plus optional evidence documents (supplier spec sheets, test report summaries as .txt or text PDFs). You get:

- risky phrases marked right away by local rules (medical promises, absolute guarantees, rankings, implied evidence), with no model call;
- contradictions across products and conflicts with your own spec columns and documents, found by Beam reading the entire catalog at once;
- a label for every flagged claim: **supported**, **contradicted** or **no evidence**, with the exact catalog cell or document line quoted;
- each affected title or description rewritten as a whole, in your tone and language (English or Korean), with a before/after diff;
- a table per product and a downloadable corrected catalog CSV: your columns in their original order with the fixed copy, then a review note, a word diff and the original text of every changed field.

This is a second look at your wording, not legal or regulatory approval. Rules can miss claims and context, and the model can be wrong. Check every suggestion and its evidence before you publish.

## How Beam is used

The model is [`reflection/Beam-1.0-501B-A23B`](https://huggingface.co/reflection/Beam-1.0-501B-A23B), called through Hugging Face Inference Providers (provider `baseten`) with chat completions, using the sampling from the model card (temperature 0.7, top_p 0.99). A review makes at most three calls.

1. **Whole-catalog pass (long context).** The catalog is written out one source per line, `EN-003/material :: 100% cotton, 380 GSM`, followed by every evidence document line, `supplier_specs.txt#L5 :: Waffle towel ...`. All of it goes to Beam in one request. Because Beam has a 1M-token context window, it sees every product next to every other product and every document, which is what makes cross-product checks possible: the same towel listed at 500 GSM in one row and 380 GSM in another, a tee "made in Portugal" whose origin column says Vietnam, a "same formula" sun stick with a different SPF, several products all claiming first place. Splitting the catalog into chunks would hide exactly these problems.
2. **Verifier pass.** Every flagged claim (from the rules and from pass 1) is sent back with the whole catalog. For each one Beam must give a label and quote the cell or line it relies on. The app then checks every quote in code, by exact substring match against the named source:
   - a quote that is not in the input is thrown away;
   - a quote of the flagged sentence itself does not count as support;
   - if a claim is labelled supported or contradicted but none of its quotes survive, the label is lowered to no evidence;
   - a correct quote with a wrong line id is accepted only if the text appears in exactly one line, and the corrected id is shown.

   Everything rejected is listed in the **Citation check** panel, so you can see what the model got wrong instead of having it hidden.
3. **Rewrite pass.** Every product with a claim that is not supported goes into one batched request (still a single call for the whole catalog). For each affected field Beam gets the full text, its flagged claims with the verified facts, the product's own spec cells, and the list of sentences that have no flag. It returns the whole field rewritten, fixing all of that field's claims at once. The app then checks it in code, sentence group by sentence group:
   - every sentence without a flag must come back character for character and in order;
   - no number that is not in the product's row or its verified evidence, no switch of language, nothing that still trips a local rule, and none of the flagged words left in place;
   - each changed sentence must still look like a full sentence (enough words, original ending punctuation, no sentence starting mid-phrase), and it may not just repeat something the field already says;
   - if a flagged phrase was only swapped for a bare word or two, that is rejected unless the swap is a fact taken from the seller's own data, such as `54 cm` to `58 cm`, `Portugal` to `Vietnam` or `100% linen` to `55% linen, 45% cotton`.

   When a check fails, that part falls back to the original sentence with the flagged words removed cleanly (for example "Our everyday apron in 100% linen." becomes "Our everyday apron."). If removing them would leave a fragment, the sentence is dropped; if nothing would be left of the field, it is kept as is and marked for your own edit. Every rejected rewrite is listed in the Citation check panel with the reason.

Pass 1 issues must also quote the seller's copy exactly, or they are dropped before they reach the verifier.

## Running without a token, and cost limits

- The token is read only from the `HF_TOKEN` environment variable (set it as a Space secret). It is never written to disk or shown; error messages are scrubbed of anything token-like.
- `BEAM_DAILY_CALL_CAP` (default 40) limits model calls per day (UTC). The count is a date and a number in a small JSON file (`BEAM_USAGE_FILE`, default `/data/beam_usage.json` when persistent storage is enabled, otherwise `.usage/` next to the app).
- `BEAM_MAX_INPUT_CHARS` (default 400,000) caps the text sent to Beam. Files are limited to 5 MB and 2,000 rows.
- With no token, when the daily cap is reached, or when a catalog is too large, the app still runs the local rules and says so plainly. Labels then show as not checked, and the corrected copy uses the clean removal described above.
- Other settings: `BEAM_MAX_TOKENS` (default 32768, output budget per call including reasoning), `BEAM_REASONING_EFFORT` (unset by default, which keeps the model's own default), `BEAM_TIMEOUT_S`.

## Example shops

Two fictional shops ship with the app, each with 30 products (apparel, skincare, kitchen goods) and two evidence documents:

- `examples/catalog_en.csv` with `examples/evidence_en/`
- `examples/catalog_ko.csv` with `examples/evidence_ko/` (Korean headers: 상품코드, 상품명, 상세설명, 소재, ...)

Both contain planted problems: copy that disagrees with its own material or size column, "same as" items that are not the same, several first-place claims, a "clinically proven" claim backed only by a comfort survey, an oven temperature above the supplier's limit, a "plant oils only" lip balm that contains beeswax, plus some claims that are genuinely supported so the labels have something to agree with.

Cached results for the examples live in `examples/cache/`. They are produced only by `scripts/make_cache.py`, which runs the real pipeline against Beam:

```bash
HF_TOKEN=... python scripts/make_cache.py
```

Until that has been run, each cache file says `"status": "not generated yet"` and the app shows local rules for the examples, with a note. The cache also stores a hash of the example files, so a cache made for older files is not shown.

## Local rules

The phrase rules come from [Honest Copy](https://github.com/kks0488/honest-copy) (`src/rules.mjs`) and are ported to Python in `honest_catalog/rules.py` with the same patterns, order, replacements and overlap handling. JavaScript's ASCII-only `\b`, `\d` and its whitespace set are spelled out so the Python version matches the original exactly. `tests/fixtures/rules_parity.json` is the output of the original JavaScript on 49 phrases (`scripts/js_parity.mjs`), and the tests compare against it; when Node and the original source are present, the comparison also runs live.

A few catalog-specific patterns (shop rankings like "Best seller #1" and "판매 1위", "never fades", "평생 사용") are kept in a separate list so the port itself stays unchanged.

## Run it locally

```bash
pip install -r requirements.txt
python app.py                  # local rules only
HF_TOKEN=... python app.py     # with Beam
pip install pytest && python -m pytest -q
```

## Demo script (about 2 minutes)

1. Open the Space. Point out the line at the top: a second look, not legal approval.
2. Click **Try the English example shop**. The local rules mark phrases like "cures acne in 7 days" and "Best seller #1" at once, with no model call.
3. With Beam connected (or the cached result generated), open the report. Look at EN-001, where the copy says "100% linen" but the material column says `55% linen, 45% cotton`: the claim should come back **contradicted**, quoting that cell, and the before/after diff shows the description rewritten with the seller's own fabric data while the pockets sentence stays untouched.
4. Show a cross-product find: the waffle towel at 500 GSM against the 380 GSM set, or the "same formula" sun stick with a different SPF.
5. Open **Citation check**: every quote Beam gave was compared with the files word for word, and anything that did not match is listed with the reason.
6. Download the corrected catalog CSV and open it: same columns in the same order with the fixed copy, then a review note, a word diff (`[-removed-] {+added+}`) and the original text for every changed field.
7. Switch the language to 한국어 and run the Korean example shop to show the same review in Korean.

## Limitations

- Rules are a fixed list of English and Korean phrases. They miss claims phrased differently and can flag harmless uses (for example "risk-free returns").
- Beam can misread a catalog or miss a contradiction. The exact-quote check proves a citation exists in your files, not that the model's reasoning about it is right.
- Only text is read. Scanned PDFs without a text layer, images and size charts inside pictures are not checked.
- Line breaks inside a cell are joined with spaces, so the corrected CSV has single-line cells.
- The "full sentence" check is a set of plain rules (word count, ending punctuation, no sentence starting mid-phrase, no hanging Korean particle), not a grammar checker. Clean removal can drop a sentence that a person would have rescued with a small edit.
- Very large catalogs (above the input limit) get local rules only. Up to 150 flagged claims are verified per review.
- Nothing here is legal, medical or regulatory advice.

## License

MIT, like the Honest Copy project it builds on. The Beam model is released under Apache 2.0.
