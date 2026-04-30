# Sovereign Proxy Pointer RAG Search V2 (Base Setup)

This repository serves as a **clean base setup** for the Proxy Pointer RAG-WASM-MCP pipeline. It features the **Triple-Optimization Architecture** (Semantic + Fuzzy + Graph) operating entirely in-browser with zero backend dependencies for search.

## 📂 Folder Structure

This setup comes pre-configured with our standard ingestion pipeline folders:
- `_1 Input Files Folder/`: Place new PDFs here, or upload them via the UI while the local orchestrator is running.
- `_1.5 FAILED UPLOADS TO REVIEW/`: Any files that fail the pre-flight checks (e.g., low OCR confidence, missing headers) will be moved here.
- `_2 COMPLETED Upload Files/`: Successfully parsed and indexed PDFs are moved here.
- `data/`: Contains the static JSON indices (`rag_corpus.json`, `graph_data.json`, `embeddings.json`) loaded by the browser.

## 🚀 How to Use the UI (Search & Graph)

You can access the UI via the **GitHub Pages link** for this repository.

1. **Search:** Simply type your query in the search bar. The engine uses a blended score (60% Keyword, 40% Semantic via pre-computed embeddings) and will automatically apply fuzzy spell-correction if you make a typo.
2. **Filters:** Click the chips to filter by Material, Source Catalog, or Minimum Confidence.
3. **Agent Access:** Open Browser DevTools (F12) to access the `window.MCP` object. Your local autonomous agents can invoke `await MCP.vector.search("term")` or `MCP.graph.getConnections("node_id")`.

## 📤 How to Use the File Upload (Local Ingestion)

Because the search UI is hosted statically on GitHub Pages, it cannot save files directly to the GitHub repository. To upload files, you must run the local orchestrator alongside the UI:

1. **Clone or Fork this repo** to your local machine.
2. **Start the Orchestrator:** Open a terminal in your local folder and run `python local_orchestrator.py` (ensure you have Flask installed). This starts a local intake server on port `5000`.
3. **Upload from the UI:** Open the GitHub Pages URL (or open `index.html` locally). Drag and drop a PDF into the drop zone.
4. **Local Destination Guarantee:** The UI's file-drop specifically targets `http://localhost:5000/upload`. This guarantees that **when this repo is forked or taken local, the file upload goes straight to YOUR local file base (`_1 Input Files Folder`)** and is never connected to the global/upstream GitHub.
5. **Syncing Updates:** Once processed, the local Python script updates your `data/` JSONs. You can then commit and push the updated `data/` folder to your fork to make the new parts searchable on your own GitHub Pages.
