# Proxy Pointer RAG-WASM-MCP: Operating SOP
> **Status:** 🔒 ACTIVE
> **Type:** Working SOP (Keyword Density)

## 1. What Material Can Be Uploaded?
- **Format:** `.pdf`
- **Content:** Manufacturer Catalogs, Spec Sheets, Cut Sheets.
- **Data Types:** Tabular data, Part Numbers (Stock Codes), Descriptions, Dimensions.

## 2. Pre-Upload Clean-Up Needed?
- **NONE.** 
- *Governance:* CCO-UPC §1 (Dumb Reader). 
- *Mechanism:* Pipeline auto-handles OCR errors, truncations, and missing headers. Rejected records log to `data/rejected_log.json`.

## 3. Upload Path (Where to put files)
- **Directory:** `c:\_0 SH-WF-Global gemini.md\_99-1 Proxy Pointer RAG-Creation\pdfs\`

## 4. How to View & Interact
- **Dashboard:** Open `index.html` in any web browser.
- **Path:** `c:\_0 SH-WF-Global gemini.md\_99-1 Proxy Pointer RAG-WASM-MCP\index.html`
- **Agent Access:** Browser DevTools Console (`window.MCP`).

## 5. Upload Confirmation
- **Console:** Output of `export_corpus.py` (Raw count vs Accepted count).
- **Log File:** `data/rejected_log.json` (Lists records failing Pre-Flight Gates).
- **Dashboard:** Top "Stats Bar" displays total indexed parts and loaded sources.

## 6. Actual Upload Process (What it does)
1. **Extract:** Read PDF (Text/Vision) → LLM Structuring → `full_extract.json`
2. **Sanitize:** `export_corpus.py` applies 4 Pre-Flight Gates (Confidence floor, Code length).
3. **Compile:** Transforms valid records into flat `rag_corpus.json`.
4. **Graph:** `generate_graph_data.py` builds relationship edges (Page/Size/Material) into `graph_data.json`.
5. **Serve:** Browser loads JSONs directly into memory.

## 7. Embedding System Used
- **NONE.** (Zero-Backend Mandate).
- **Engine:** `lunr.js` (In-Browser Full-Text Search) + JSON Graph Traversal.
- **Why:** Eliminates API latency, compute costs, and backend maintenance.

## 8. Data Storage Location
- **LOCAL.** 
- **Format:** Static JSON files (`rag_corpus.json`, `graph_data.json`).
- **Cloud:** GitHub Pages (GitOps via commits). **NO SUPABASE.**

## 9. Available Functions (Post-Upload)
### Human Interface (Dashboard)
- Instant Full-Text Search (Wildcard + Substring fallback).
- Faceted Filtering (Material, Source, Confidence).
- Visual Tags (Confidence High/Mid/Low, Engine, Page).

### Agent Interface (DevTools Console)
- `MCP.vector.search("term", topK)`: Search corpus.
- `MCP.graph.getConnections("node_id")`: Find related parts (same page/size/material).
- `MCP.proof.getVisualBbox(pageNum)`: Get page screenshot URL for cross-reference.
- `MCP.searchAndGraph("term")`: Combined search + relationship mapping.
