# CCO-UPC: WASM Proxy RAG Pre-Flight Governance Protocol
> **Status:** 🔒 ACTIVE
> **Forked From:** `_99-1 Proxy Pointer RAG-Creation/cco_upc_pre_flight_governance.md`
> **Architecture:** Zero-Backend Browser-Native (ZWP-2)
> **Governing Agent:** `wasm-rag-corpus-auditor-Agent`

## Mission & Philosophy
This protocol governs the **Honest Output Mandate** for the browser-native WASM Proxy RAG Search. Because there is no backend server to run validation logic, ALL data quality enforcement must happen **before** the corpus enters `rag_corpus.json`. The browser is a Dumb Reader — it trusts whatever JSON it receives. Therefore, the corpus export pipeline bears 100% responsibility for data integrity.

---

## §1. The Corpus Export Gate (Dumb Reader Severance)

The browser MUST NOT contain any data validation logic. It reads `rag_corpus.json` as-is. This means the export script that transforms `full_extract.json` → `rag_corpus.json` must execute all quality gates inline.

### Rule 1: Engine Consensus Scoring
- Data agreed upon by BOTH text_layer AND OCR receives `engine: "confirmed"` and highest confidence (>= 0.95).
- OCR-only data receives `engine: "ocr"` with a confidence penalty (-0.3).
- Text-layer-only data receives `engine: "text_layer"` with baseline confidence.

### Rule 2: Stock Code Composition Guards
- **All-digit codes → REJECTED** (likely dimensions or page numbers).
- **All-alpha codes → REJECTED** (likely table headers).
- **Codes < 3 chars → REJECTED** (noise).
- **Codes > 30 chars → FLAGGED** (possible concatenation error).

### Rule 3: Description Density
- Records with empty or placeholder descriptions (`"(OCR — pending)"`) are **FLAGGED**.
- Records missing material classification are **FLAGGED** but not rejected.
- Records missing category classification are accepted (can be inferred later).

### Rule 4: Confidence Floor
- Records with `confidence < 0.40` are **REJECTED** and excluded from the corpus.
- Records with `confidence < 0.80` are included but tagged with `pre_flight_status: "flagged"`.
- Records with `confidence >= 0.80` are tagged `pre_flight_status: "approved"`.

---

## §2. The Export Script Contract

The corpus export script (`export_corpus.py`) MUST:

1. **Read** the source `full_extract.json` (CCO-UPC §1 Dumb Reader — read only, never modify source).
2. **Flatten** the nested `pages[].parts[]` structure into a flat array.
3. **Assign** unique IDs using the pattern `{SOURCE_PREFIX}-{SEQUENTIAL_NUMBER}` (e.g., `EVF-001`, `JS-001`).
4. **Apply** all 4 composition guards from §1 above.
5. **Write** the output to `data/rag_corpus.json` as a minified JSON array.
6. **Log** all rejected records to `data/rejected_log.json` with rejection reasons.

### Export Schema (Mandatory Fields)
```json
{
  "id": "string — unique identifier",
  "stock_code": "string — part number",
  "description": "string — human-readable product name",
  "page": "integer — source PDF page (1-indexed)",
  "engine": "string — text_layer | ocr | confirmed",
  "confidence": "float — 0.0 to 1.0",
  "material": "string — material classification",
  "size": "string — dimensional specification",
  "category": "string — product category path",
  "source": "string — source PDF filename",
  "raw_line": "string — original extracted text"
}
```

---

## §3. The Hallucination Cross-Reference Protocol (WASM Variant)

Because the browser has no access to the source PDF, the `raw_line` field serves as the **embedded truth anchor**. This is the exact text extracted from the source document.

- When a user searches and finds a result, they can compare the structured fields (`stock_code`, `description`, `material`) against the `raw_line` to detect extraction drift.
- If the `stock_code` in the structured field does not appear verbatim in the `raw_line`, the extraction is **suspect**.
- The export script MUST enforce: `stock_code ∈ raw_line` (substring match) for `confidence >= 0.90`. Violations drop confidence by 0.15.

### Fuzzy Match Thresholds (from CCO-UPC_V2.md §3):
- **5-character codes:** 79% similarity minimum.
- **6+ character codes:** 88% similarity minimum.

---

## §4. The TDD Iron Law (Testing Protocol)

### Smoke Tests (run on every corpus update):
Test ID | Description | Expected
--------|-------------|----------
ST-01 | JSON is parseable | `json.load()` succeeds
ST-02 | All IDs unique | `len(ids) == len(set(ids))`
ST-03 | No empty stock_codes | `all(p['stock_code'] for p in corpus)`
ST-04 | No empty descriptions | `all(p['description'] for p in corpus)`
ST-05 | Confidence range valid | `all(0.0 <= p['confidence'] <= 1.0)`
ST-06 | Page numbers positive | `all(p['page'] > 0)`
ST-07 | Source field populated | `all(p['source'])`
ST-08 | Material field density | `sum(bool(p['material'])) / len(corpus) >= 0.95`

### Retrieval Accuracy Tests (run on every search engine update):
Test ID | Description | Expected
--------|-------------|----------
RA-01 | Exact stock_code search | Returns 1 exact match
RA-02 | Multi-word search | Returns relevant subset
RA-03 | Material filter | Returns ONLY matching material
RA-04 | Source filter | Returns ONLY matching source
RA-05 | Confidence filter | Returns ONLY records >= threshold
RA-06 | Stacked filters | Intersection of all active filters
RA-07 | Empty search | Returns full corpus
RA-08 | Clear button | Resets all filters and shows full corpus

### Cross-Reference Tests (run when both catalogs present):
Test ID | Description | Expected
--------|-------------|----------
XR-01 | Same size brass elbow | EVF and JS results both appear
XR-02 | Size filter stacking | "1/2" filter across both sources
XR-03 | Category navigation | Fittings > Elbows returns all elbows

---

## §5. The Data Infusion Protocol (Adding Real Data)

When replacing the sample corpus with real extraction data:

1. **Run the extraction pipeline** using `_99-1 Proxy Pointer RAG-Creation` on the target PDF.
2. **Execute** `export_corpus.py` to transform `full_extract.json` → `rag_corpus.json`.
3. **Run** `tdd_validate.py` — all smoke tests MUST pass.
4. **Commit** the updated corpus to the repo.
5. **Push** to GitHub — Pages auto-deploys.
6. **Verify** via `gate_d2_live_site_verification` in `gates.yaml`.

### Critical Rule: NEVER manually edit `rag_corpus.json`
The corpus is an **output artifact** of the extraction pipeline. Manual edits bypass all quality gates and violate CCO-UPC §1 (Dumb Reader Severance). If a record is wrong, fix it at the source (`full_extract.json` or the extraction config) and re-export.

---

## §6. The Evolution Cycle

When the browser search reveals data quality issues:
1. User identifies a suspicious result via the `raw_line` cross-reference.
2. User logs the issue in `data/quality_issues.json`.
3. Next extraction run incorporates the feedback into `extraction_config.yaml`.
4. Re-export and redeploy.

This ensures the browser remains a **zero-logic Dumb Reader** while the extraction pipeline absorbs all intelligence.
