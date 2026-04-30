# MCP Shim Integration — Skill Definition (Pillar 2 of 5)

## Skill: BrowserVectorAPI Parity
- **Input:** Search query + Python MCP results
- **Output:** Pass/fail with diff of mismatched part IDs
- **Method:** Run identical query through Python VectorAPI and JS BrowserVectorAPI, compare result sets.

## Skill: Graph Data Generation
- **Input:** `rag_corpus.json`
- **Output:** `graph_data.json` with nodes and edges
- **Method:** Build page/size/material co-occurrence edges from corpus.

## Skill: SDK Type Contract Sync
- **Input:** `mcp_shim.js` JavaScript source
- **Output:** Updated `proxy_rag_sdk_types_browser.yaml`
- **Method:** Parse JS method signatures, compare against YAML, flag drift.

## Skill: Console Interface Audit
- **Input:** Live browser session
- **Output:** Pass/fail for each MCP.* command
- **Method:** Execute MCP.help(), MCP.vector.search(), MCP.graph.getConnections() in console.
