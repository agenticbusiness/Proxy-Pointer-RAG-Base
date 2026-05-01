# Proxy Pointer RAG-WASM-MCP: Operating SOP
> **Status:** 🔒 ACTIVE
> **Type:** Working SOP (Keyword Density)

## 1. What Material Can Be Uploaded?
- **Format:** `.pdf`, `.docx`, `.md`, `.txt`, `.json`
- **Content:** Any domain — Manufacturer Catalogs, Knowledge Bases, Legal Dossiers, Financial Reports.
- **Data Types:** Tabular data, Prose, Structured Records, Technical Specifications.
- **Domain Detection:** Automatic via `domain_profiler.py` (Zod Schema Discovery).

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
1. **Profile:** `domain_profiler.py` scans source files → Outputs `domain_schema.yaml` (domain type, keyword taxonomy, embedding field selection).
2. **Extract:** Read PDF/DOCX/MD (Text/Vision) → LLM Structuring → `full_extract.json`
3. **Sanitize:** `export_corpus.py` applies Pre-Flight Gates using domain-adaptive inference (reads `domain_schema.yaml`).
4. **Compile:** Transforms valid records into flat `rag_corpus.json`.
5. **Embed:** `generate_sample_embeddings.py` reads `domain_schema.yaml` to select which fields to hash (NOT hardcoded).
6. **Graph:** `generate_graph_data.py` builds relationship edges into `graph_data.json`.
7. **Serve:** Browser loads JSONs directly into memory.

## 7. Embedding System Used
- **Local:** `pseudo-hash-384` via `generate_sample_embeddings.py` (domain-adaptive field selection from `domain_schema.yaml`).
- **Production:** `all-MiniLM-L6-v2` via `generate_embeddings.py` (Oracle ARM node, same domain-adaptive field selection).
- **Browser:** Cosine similarity in `mcp_shim.js` — ZERO ML model needed client-side.
- **Field Selection:** Dynamic. Determined by `domain_schema.yaml`, NOT hardcoded. Defaults maintained for backward compatibility.

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
