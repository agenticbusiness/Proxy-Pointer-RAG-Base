# Domain Profiler Skill — Agent-Skill-Gates V2
# Pillar 2 of 2 — Domain-Adaptive Embedding Pipeline

skill:
  name: "domain-profiler-Skill"
  version: "1.0"
  governance: "CCO-UPC §1 (Dumb Reader)"

  purpose: >
    Zod Schema Discovery logic — token frequency analysis, named entity
    extraction, domain classification, and field relevance scoring.

  capabilities:
    - name: "extract_text"
      description: "Read .md, .txt, .json, .docx, .pdf files to raw text"
      supports: [".md", ".txt", ".json", ".docx", ".pdf", ".csv", ".yaml"]

    - name: "tokenize"
      description: "Split text into cleaned tokens with stop-word removal"
      stop_word_count: 150

    - name: "detect_domain"
      description: "Classify domain via signal dictionary overlap scoring"
      domains:
        - parts_catalog
        - knowledge_base
        - legal
        - financial
      signal_words_per_domain: 20-25
      scoring: "top-200 token overlap with domain signal dictionary"

    - name: "score_field_relevance"
      description: "Map domain type to optimal embedding field selection"
      field_profiles:
        parts_catalog: ["stock_code", "description", "material", "category", "size"]
        knowledge_base: ["description", "raw_line", "category", "material"]
        legal: ["description", "raw_line", "category", "source"]
        financial: ["description", "raw_line", "category", "material"]

    - name: "build_taxonomy"
      description: "Extract domain-specific keyword taxonomy from token frequencies"
      output_size: "top 20 categories, top 80 keywords with counts"

  dependencies:
    required: []
    optional:
      - "pyyaml (for YAML output, falls back to JSON)"
      - "python-docx (for .docx extraction)"
      - "pymupdf (for .pdf extraction)"

  wasi_bindings:
    fs_read: true
    fs_write: true
    net_outbound: false
    env_inherit: false
