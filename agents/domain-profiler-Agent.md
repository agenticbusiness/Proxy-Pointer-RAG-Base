# Domain Profiler Agent — Agent-Skill-Gates V2
# Pillar 1 of 2 — Domain-Adaptive Embedding Pipeline

agent:
  name: "domain-profiler-Agent"
  version: "1.0"
  governance: "CCO-UPC §1 (Dumb Reader Severance)"

  purpose: >
    Autonomous file scanner that profiles source documents to determine
    the domain type (parts_catalog | knowledge_base | legal | financial)
    and outputs a domain_schema.yaml for downstream embedding/inference scripts.

  triggers:
    - event: "new_pxr_fork_created"
      description: "Fires when a new Proxy Pointer RAG folder is forked from V2 base"
    - event: "source_files_dropped"
      description: "Fires when files are added to _1 Input Files Folder"
    - event: "corpus_updated"
      description: "Fires when rag_corpus.json is modified (re-profile)"

  inputs:
    source_directory:
      type: "path"
      default: "_1 Input Files Folder"
      description: "Directory containing source files to scan"
    corpus_path:
      type: "path"
      default: "data/rag_corpus.json"
      description: "Alternative: profile from existing corpus JSON"

  outputs:
    domain_schema:
      type: "yaml"
      path: "domain_schema.yaml"
      description: "Domain type, keyword taxonomy, embedding field selection"

  execution:
    command: "python domain_profiler.py"
    fallback: "python domain_profiler.py --corpus data/rag_corpus.json"
    timeout_seconds: 60

  validation_gate: "gate_ci_neg1_domain_profiling"

  skill_binding: "domain-profiler-Skill"
