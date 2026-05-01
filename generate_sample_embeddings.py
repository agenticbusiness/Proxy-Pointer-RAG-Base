"""
generate_sample_embeddings.py — LOCAL TEST ONLY
Creates simulated 384-dim embeddings so the V2 dashboard can boot locally
without needing the Oracle node. Replace with real embeddings from generate_embeddings.py.
"""
import json, os, hashlib, math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_PATH = os.path.join(SCRIPT_DIR, "data", "rag_corpus.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "data", "embeddings.json")

with open(CORPUS_PATH, "r", encoding="utf-8") as f:
    corpus = json.load(f)

def pseudo_embed(text, dims=384):
    """Deterministic pseudo-embedding from text hash. NOT real ML — for testing only."""
    h = hashlib.sha512(text.encode()).hexdigest()
    raw = [int(h[i:i+2], 16) / 255.0 - 0.5 for i in range(0, min(len(h), dims * 2), 2)]
    while len(raw) < dims:
        h = hashlib.sha512(h.encode()).hexdigest()
        raw.extend([int(h[i:i+2], 16) / 255.0 - 0.5 for i in range(0, min(len(h), (dims - len(raw)) * 2), 2)])
    raw = raw[:dims]
    norm = math.sqrt(sum(x*x for x in raw))
    return [round(x / norm, 6) for x in raw] if norm > 0 else raw

output = {
    "model": "pseudo-hash-384 (SAMPLE — replace with Oracle output)",
    "dimensions": 384,
    "generated": "2026-04-30T00:00:00Z",
    "count": len(corpus),
    "vectors": []
}

# ─── Domain-Adaptive Field Selection ───
# Reads domain_schema.yaml (from domain_profiler.py) to determine which
# corpus fields carry the most signal for THIS domain's embeddings.
# Falls back to hardcoded defaults if no schema exists (backward-compatible).
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "domain_schema.yaml")
DEFAULT_FIELDS = ["stock_code", "description", "raw_line", "material", "category"]

if os.path.exists(SCHEMA_PATH):
    try:
        import yaml
        with open(SCHEMA_PATH, "r", encoding="utf-8") as sf:
            schema = yaml.safe_load(sf)
        EMBED_FIELDS = schema["domain_schema"]["embedding_config"]["fields_to_hash"]
        domain_type = schema["domain_schema"]["domain_type"]
        print(f"[EMBED] Domain-adaptive mode: {domain_type}")
        print(f"[EMBED] Hashing fields: {EMBED_FIELDS}")
    except Exception as e:
        print(f"[EMBED] Schema read failed ({e}) — using defaults")
        EMBED_FIELDS = DEFAULT_FIELDS
else:
    EMBED_FIELDS = DEFAULT_FIELDS
    print(f"[EMBED] No domain_schema.yaml — using default fields: {EMBED_FIELDS}")

for p in corpus:
    text = " ".join(str(p.get(f, "")) for f in EMBED_FIELDS)
    output["vectors"].append({"id": p["id"], "v": pseudo_embed(text)})


with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False)

size_kb = round(os.path.getsize(OUTPUT_PATH) / 1024, 1)
print(f"Sample embeddings: {len(corpus)} vectors x 384 dims -> {OUTPUT_PATH} ({size_kb} KB)")
