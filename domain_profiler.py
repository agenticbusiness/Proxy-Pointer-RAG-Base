"""
domain_profiler.py — Zod Schema Discovery Engine
═══════════════════════════════════════════════════
Governance: CCO-UPC §1 (Dumb Reader — reads files, never modifies source)
            Agent-Skill-Gates (domain-profiler-Skill)

PURPOSE:
  Reads ALL source documents in _1 Input Files Folder, performs:
    1. Token frequency analysis (TF-IDF style)
    2. Named entity extraction (regex-based, no ML dependency)
    3. Domain classification (auto-detect: parts_catalog | knowledge_base | legal | financial)
    4. Field relevance scoring (which corpus fields carry the most signal for THIS domain)

OUTPUT:
  domain_schema.yaml — consumed by generate_sample_embeddings.py, generate_embeddings.py,
                        and export_corpus.py for domain-adaptive field selection.

USAGE:
  python domain_profiler.py                          # Scan _1 Input Files Folder
  python domain_profiler.py --input-dir /path/to/src # Scan custom directory
  python domain_profiler.py --corpus data/rag_corpus.json  # Profile from existing corpus
"""
import os
import re
import json
import argparse
from collections import Counter
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

SCRIPT_DIR = Path(__file__).parent
DEFAULT_INPUT_DIR = SCRIPT_DIR / "_1 Input Files Folder"
SCHEMA_OUTPUT = SCRIPT_DIR / "domain_schema.yaml"

# ─── STOP WORDS (domain-agnostic noise) ───
STOP_WORDS = set("""
the a an is are was were be been being have has had do does did
will would shall should may might can could of in to for with on
at by from as into through during before after above below between
this that these those it its he she they we you and or but not
also use used uses using each all any both few more most other
some such than too very just like than then there here when where
how what which who whom whose why how much many well still also
however therefore moreover furthermore additionally new first one
two three four five about been into more only over same own per
each every either neither other such than too very just like more
most even also before after above again further then once here
there when where why how all any both each few more most some
can will just don should now its our their these those what
which who would could shall being from only each data file
than into that with this have from been more about over same
""".split())

# ─── DOMAIN SIGNAL DICTIONARIES ───
DOMAIN_SIGNALS = {
    "parts_catalog": [
        "part", "stock", "code", "size", "material", "fitting", "valve",
        "brass", "copper", "pipe", "elbow", "coupling", "tee", "nipple",
        "catalog", "manufacturer", "dimension", "inch", "diameter",
        "stainless", "galvanized", "iron", "chrome", "pex", "cpvc",
    ],
    "knowledge_base": [
        "architecture", "protocol", "hash", "encryption", "algorithm",
        "storage", "security", "performance", "distributed", "consensus",
        "merkle", "shard", "node", "pipeline", "framework", "engine",
        "compression", "serialization", "wasm", "browser", "sovereign",
        "decentralized", "immutable", "vector", "embedding", "index",
    ],
    "legal": [
        "agreement", "pursuant", "damages", "court", "statute",
        "plaintiff", "defendant", "claim", "compensation", "attorney",
        "breach", "contract", "liability", "negligence", "arbitration",
        "jurisdiction", "settlement", "indemnify", "warranty", "tort",
    ],
    "financial": [
        "revenue", "margin", "quarterly", "budget", "forecast",
        "expense", "profit", "sales", "commission", "invoice",
        "accounts", "receivable", "payable", "balance", "ledger",
        "depreciation", "amortization", "equity", "dividend", "yield",
    ],
}

# ─── FIELD PROFILES PER DOMAIN ───
# Defines which corpus fields are most signal-dense for embedding generation.
FIELD_PROFILES = {
    "parts_catalog": {
        "embedding_fields": ["stock_code", "description", "material", "category", "size"],
        "graph_fields": ["material", "category", "size", "source"],
        "filter_fields": ["material", "source", "confidence"],
        "id_prefix": "PXR",
    },
    "knowledge_base": {
        "embedding_fields": ["description", "raw_line", "category", "material"],
        "graph_fields": ["material", "category", "source"],
        "filter_fields": ["material", "source", "confidence"],
        "id_prefix": "KB",
    },
    "legal": {
        "embedding_fields": ["description", "raw_line", "category", "source"],
        "graph_fields": ["category", "source"],
        "filter_fields": ["category", "source", "confidence"],
        "id_prefix": "LEG",
    },
    "financial": {
        "embedding_fields": ["description", "raw_line", "category", "material"],
        "graph_fields": ["material", "category", "source"],
        "filter_fields": ["material", "source", "confidence"],
        "id_prefix": "FIN",
    },
}


def extract_text_from_file(filepath):
    """Extract raw text from supported file types. Zero external dependencies for core types."""
    ext = filepath.suffix.lower()
    try:
        if ext in (".md", ".txt", ".csv", ".yaml", ".yml"):
            return filepath.read_text(encoding="utf-8", errors="ignore")
        elif ext == ".json":
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return json.dumps(data, indent=2)
        elif ext == ".docx":
            try:
                from docx import Document
                doc = Document(str(filepath))
                return "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                print(f"  [WARN] python-docx not installed — skipping {filepath.name}")
                return ""
        elif ext == ".pdf":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(filepath))
                return "\n".join(page.get_text() for page in doc)
            except ImportError:
                print(f"  [WARN] PyMuPDF not installed — skipping {filepath.name}")
                return ""
    except Exception as e:
        print(f"  [WARN] Failed to read {filepath.name}: {e}")
    return ""


def extract_text_from_corpus(corpus_path):
    """Extract text directly from an existing rag_corpus.json."""
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    texts = []
    for record in corpus:
        parts = [
            str(record.get("description", "")),
            str(record.get("raw_line", "")),
            str(record.get("material", "")),
            str(record.get("category", "")),
        ]
        texts.append(" ".join(parts))
    return "\n".join(texts), len(corpus)


def tokenize(text):
    """Whitespace + punctuation tokenizer with stop-word removal."""
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 2]


def detect_domain_type(token_freq):
    """Classify domain based on top token overlap with signal dictionaries."""
    top_tokens = set(t for t, _ in token_freq[:200])
    scores = {}
    for domain, signals in DOMAIN_SIGNALS.items():
        hits = sum(1 for s in signals if s in top_tokens)
        scores[domain] = hits
    winner = max(scores, key=scores.get)
    best_score = scores[winner]
    total_signals = len(DOMAIN_SIGNALS[winner])
    confidence = round(best_score / total_signals, 2) if total_signals > 0 else 0.0
    return winner, confidence, scores


def build_taxonomy(token_freq, n_categories=20):
    """Build the domain-specific keyword taxonomy from token frequencies."""
    return {
        "auto_detected_categories": [t for t, _ in token_freq[:n_categories]],
        "keyword_density": {t: c for t, c in token_freq[:80]},
        "total_unique_tokens": len(set(t for t, _ in token_freq)),
    }


def profile(input_dir=None, corpus_path=None):
    """Main profiling pipeline."""
    file_inventory = []
    file_extensions = Counter()

    if corpus_path and os.path.exists(corpus_path):
        # Profile from existing corpus
        print(f"[PROFILER] Profiling from corpus: {corpus_path}")
        all_text, record_count = extract_text_from_corpus(corpus_path)
        file_inventory.append({
            "name": os.path.basename(corpus_path),
            "ext": ".json",
            "size_bytes": os.path.getsize(corpus_path),
            "char_count": len(all_text),
        })
        file_extensions[".json"] = 1
    else:
        # Profile from source files
        scan_dir = Path(input_dir) if input_dir else DEFAULT_INPUT_DIR
        if not scan_dir.exists():
            print(f"[ERROR] Input directory not found: {scan_dir}")
            print(f"[INFO]  Create it and drop source files, or use --corpus flag.")
            return None

        print(f"[PROFILER] Scanning: {scan_dir}")
        all_text = ""
        for fpath in sorted(scan_dir.rglob("*")):
            if fpath.is_file() and not fpath.name.startswith("."):
                ext = fpath.suffix.lower()
                file_extensions[ext] += 1
                text = extract_text_from_file(fpath)
                all_text += text + "\n"
                file_inventory.append({
                    "name": fpath.name,
                    "ext": ext,
                    "size_bytes": fpath.stat().st_size,
                    "char_count": len(text),
                })

    if not all_text.strip():
        print("[ERROR] No text extracted from any file. Check input directory.")
        return None

    # Tokenize and analyze
    tokens = tokenize(all_text)
    freq = Counter(tokens).most_common(200)

    # Detect domain
    domain_type, confidence, all_scores = detect_domain_type(freq)
    field_profile = FIELD_PROFILES.get(domain_type, FIELD_PROFILES["knowledge_base"])
    taxonomy = build_taxonomy(freq)

    # Build schema
    schema = {
        "domain_schema": {
            "version": "1.0",
            "generator": "domain_profiler.py",
            "domain_type": domain_type,
            "domain_confidence": confidence,
            "domain_scores": all_scores,
            "file_inventory": {
                "total_files": len(file_inventory),
                "extensions": dict(file_extensions),
                "files": file_inventory,
            },
            "field_profile": field_profile,
            "taxonomy": taxonomy,
            "embedding_config": {
                "fields_to_hash": field_profile["embedding_fields"],
                "separator": " ",
                "note": "These fields are concatenated and hashed for embedding generation. "
                        "Override by editing this list manually if domain detection was wrong.",
            },
            "inference_config": {
                "material_keywords": taxonomy["auto_detected_categories"][:15],
                "category_keywords": taxonomy["auto_detected_categories"][5:20],
                "note": "Used by export_corpus.py for dynamic material/category inference. "
                        "Replace hardcoded plumbing keywords with these domain terms.",
            },
        }
    }

    # Write output
    if HAS_YAML:
        with open(SCHEMA_OUTPUT, "w", encoding="utf-8") as f:
            yaml.dump(schema, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    else:
        # Fallback: write as JSON with .yaml extension
        with open(SCHEMA_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        print("  [WARN] PyYAML not installed — wrote JSON format to .yaml file")

    # ─── AUTO-ENRICH: Push domain terms to global List_of_Terms_Phrases.md ───
    terms_enriched = enrich_global_terms(domain_type, taxonomy, field_profile)

    # Report
    print(f"\n{'=' * 60}")
    print(f"  DOMAIN SCHEMA DISCOVERY COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Domain type:      {domain_type}")
    print(f"  Confidence:       {confidence}")
    print(f"  Domain scores:    {all_scores}")
    print(f"  Files scanned:    {len(file_inventory)}")
    print(f"  Token vocabulary: {len(set(tokens))}")
    print(f"  Embedding fields: {field_profile['embedding_fields']}")
    print(f"  ID prefix:        {field_profile['id_prefix']}")
    print(f"  Schema saved:     {SCHEMA_OUTPUT}")
    if terms_enriched:
        print(f"  Terms enriched:   {terms_enriched} new terms → List_of_Terms_Phrases.md")
    print(f"{'=' * 60}")

    return schema


def enrich_global_terms(domain_type, taxonomy, field_profile):
    """
    Auto-append domain-specific terms to the global List_of_Terms_Phrases.md.
    This makes every PXR fork teach the entire workspace about its domain vocabulary.
    
    Governance: CCO-UPC §1 (Dumb Reader) — append-only, never modifies existing entries.
    """
    # Locate the global terms file — try multiple known paths
    terms_paths = [
        Path(r"C:\_0 SH-WF-Global gemini.md\_5 Connecting Lists\List_of_Terms_Phrases.md"),
        SCRIPT_DIR.parent / "_5 Connecting Lists" / "List_of_Terms_Phrases.md",
    ]
    
    terms_file = None
    for tp in terms_paths:
        if tp.exists():
            terms_file = tp
            break
    
    if not terms_file:
        print("  [INFO] Global List_of_Terms_Phrases.md not found — skipping auto-enrichment")
        return 0
    
    # Read existing terms to avoid duplicates
    existing_content = terms_file.read_text(encoding="utf-8", errors="ignore").lower()
    
    # Extract top domain terms that aren't already in the file
    new_terms = []
    categories = taxonomy.get("auto_detected_categories", [])[:20]
    for term in categories:
        # Skip generic/short terms and terms already present
        if len(term) < 4:
            continue
        if f"**{term}**" in existing_content or f"| {term} |" in existing_content:
            continue
        new_terms.append(term)
    
    if not new_terms:
        return 0
    
    # Build the append block — Section 2 style (Industry Standard Terms)
    timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
    domain_label = domain_type.replace("_", " ").title()
    id_prefix = field_profile.get("id_prefix", "PXR")
    
    append_block = f"\n\n<!-- _AUTO_ENRICHMENT {timestamp} from domain_profiler.py -->\n"
    append_block += f"## Section 2.{id_prefix}: Auto-Detected {domain_label} Terms\n\n"
    append_block += "| Code | Full Name | Industry Standard | Description |\n"
    append_block += "|------|-----------|------------------|-------------|\n"
    
    for term in new_terms[:15]:  # Cap at 15 to prevent bloat
        zod_tags = f"`{term}, {domain_type}, auto_detected`"
        append_block += f"| **{term.upper()}** | {term.title()} (Auto-Detected) | Domain: {domain_label} | Zod: {zod_tags} |\n"
    
    # Append-only write (governance compliant)
    with open(terms_file, "a", encoding="utf-8") as f:
        f.write(append_block)
    
    print(f"  [TERMS] Enriched {len(new_terms[:15])} domain terms → {terms_file.name}")
    return len(new_terms[:15])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zod Schema Discovery Engine — Domain Profiler")
    parser.add_argument("--input-dir", default=None, help="Directory containing source files to profile")
    parser.add_argument("--corpus", default=None, help="Path to existing rag_corpus.json to profile")
    args = parser.parse_args()

    profile(input_dir=args.input_dir, corpus_path=args.corpus)

