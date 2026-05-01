# Domain-Adaptive Embedding Agent — Agent-Skill-Gates V2
# Companion to domain-profiler-Agent

agent:
  name: "domain-adaptive-embedding-Agent"
  version: "1.0"
  governance: "CCO-UPC §1 (Dumb Reader Severance)"

  purpose: >
    Reads domain_schema.yaml (output of domain-profiler-Agent) and generates
    domain-optimized embeddings by hashing only the fields that carry signal
    for the detected domain type. Replaces the legacy hardcoded 5-field hash.

  triggers:
    - event: "domain_schema_generated"
      description: "Fires after domain_profiler.py completes successfully"
    - event: "corpus_updated"
      description: "Fires when rag_corpus.json is modified"

  inputs:
    corpus:
      type: "json"
      path: "data/rag_corpus.json"
    schema:
      type: "yaml"
      path: "domain_schema.yaml"

  outputs:
    embeddings:
      type: "json"
      path: "data/embeddings.json"
      format: "{model, dimensions, count, vectors: [{id, v: [float]}]}"

  execution:
    local:
      command: "python generate_sample_embeddings.py"
      model: "pseudo-hash-384"
      note: "For local testing only — deterministic hash-based vectors"
    production:
      command: "python generate_embeddings.py"
      model: "all-MiniLM-L6-v2"
      node: "Oracle 24GB ARM"
      note: "Real ML embeddings — transfer to browser data/ after generation"

  field_selection_logic: |
    1. Check if domain_schema.yaml exists
    2. If YES: read embedding_config.fields_to_hash
    3. If NO: fall back to DEFAULT_FIELDS (backward-compatible)
    4. Concatenate selected fields with space separator
    5. Hash (local) or encode (Oracle) the concatenated text

  validation_gate: "gate_mcp0_graph_data_integrity"
  skill_binding: "domain-adaptive-embedding-Skill"
