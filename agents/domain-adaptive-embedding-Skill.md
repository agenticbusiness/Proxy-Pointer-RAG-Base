# Domain-Adaptive Embedding Skill — Agent-Skill-Gates V2
# Companion to domain-adaptive-embedding-Agent

skill:
  name: "domain-adaptive-embedding-Skill"
  version: "1.0"
  governance: "CCO-UPC §1 (Dumb Reader)"

  purpose: >
    Dynamic field concatenation and embedding generation. Reads the
    domain_schema.yaml to determine which corpus fields to concatenate
    before hashing/encoding, ensuring embeddings capture domain-relevant
    signal instead of generic noise.

  capabilities:
    - name: "read_schema"
      description: "Parse domain_schema.yaml for embedding_config.fields_to_hash"
      fallback: "Use DEFAULT_FIELDS if schema absent"

    - name: "field_concatenation"
      description: "Join selected corpus fields with space separator for hashing"
      method: "' '.join(str(record.get(field, '')) for field in EMBED_FIELDS)"

    - name: "pseudo_embed"
      description: "SHA-512 based deterministic pseudo-embedding (local testing)"
      dimensions: 384
      normalization: "L2 norm"

    - name: "ml_embed"
      description: "SentenceTransformer encoding (Oracle production)"
      model: "all-MiniLM-L6-v2"
      dimensions: 384
      batch_size: 32

  field_profiles:
    parts_catalog:
      fields: ["stock_code", "description", "material", "category", "size"]
      rationale: "Part numbers and physical attributes drive search relevance"
    knowledge_base:
      fields: ["description", "raw_line", "category", "material"]
      rationale: "Content and domain classification matter; stock_code is synthetic"
    legal:
      fields: ["description", "raw_line", "category", "source"]
      rationale: "Document prose and provenance drive legal search"
    financial:
      fields: ["description", "raw_line", "category", "material"]
      rationale: "Metric descriptions and financial categories drive search"

  backward_compatibility:
    schema_absent_behavior: "Falls back to hardcoded DEFAULT_FIELDS"
    breaking_changes: "NONE — all existing forks work without modification"

  wasi_bindings:
    fs_read: true
    fs_write: true
    net_outbound: false
    env_inherit: false
