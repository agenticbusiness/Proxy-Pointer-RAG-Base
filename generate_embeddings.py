"""
generate_embeddings.py — ONE-TIME Oracle 24GB ARM Execution
Governance: CCO-UPC §1 (Dumb Reader — reads corpus, writes embeddings, never modifies source)

This script runs ONCE on the Oracle node to pre-compute semantic embeddings.
After this runs, the browser needs ZERO ML models — just cosine similarity math.

Usage:
  ssh oracle-arm
  pip install sentence-transformers
  python generate_embeddings.py

Output: data/embeddings.json (static file, served to browser)
"""
import json, os, sys, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_PATH = os.path.join(SCRIPT_DIR, "data", "rag_corpus.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "data", "embeddings.json")

# ─── Load corpus ───
with open(CORPUS_PATH, "r", encoding="utf-8") as f:
    corpus = json.load(f)

print(f"[Oracle] Corpus loaded: {len(corpus)} records")

# ─── Load model (384-dim, ~80MB, runs on CPU) ───
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
except ImportError:
    print("[ERROR] pip install sentence-transformers")
    sys.exit(1)

# ─── Build searchable text per record ───
texts = []
for p in corpus:
    searchable = f"{p['stock_code']} {p['description']} {p.get('raw_line', '')} {p.get('material', '')} {p.get('category', '')} {p.get('size', '')}"
    texts.append(searchable)

# ─── Encode ALL records (batch, fast on 24GB ARM) ───
print(f"[Oracle] Encoding {len(texts)} records with all-MiniLM-L6-v2 (384-dim)...")
t0 = time.time()
embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
elapsed = round(time.time() - t0, 1)
print(f"[Oracle] Encoding complete in {elapsed}s")

# ─── Save as JSON (list of {id, vector}) ───
output = {
    "model": "all-MiniLM-L6-v2",
    "dimensions": 384,
    "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "count": len(corpus),
    "vectors": []
}

for i, p in enumerate(corpus):
    output["vectors"].append({
        "id": p["id"],
        "v": [round(float(x), 6) for x in embeddings[i]]
    })

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False)

size_kb = round(os.path.getsize(OUTPUT_PATH) / 1024, 1)
print(f"[Oracle] Embeddings saved: {OUTPUT_PATH} ({size_kb} KB)")
print(f"[Oracle] Done. Transfer this file to the browser data/ directory.")
print(f"[Oracle] The browser will load it and do cosine similarity locally — ZERO model needed.")
