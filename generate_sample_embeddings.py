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

for p in corpus:
    text = f"{p['stock_code']} {p['description']} {p.get('raw_line','')} {p.get('material','')} {p.get('category','')}"
    output["vectors"].append({"id": p["id"], "v": pseudo_embed(text)})

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False)

size_kb = round(os.path.getsize(OUTPUT_PATH) / 1024, 1)
print(f"Sample embeddings: {len(corpus)} vectors x 384 dims -> {OUTPUT_PATH} ({size_kb} KB)")
