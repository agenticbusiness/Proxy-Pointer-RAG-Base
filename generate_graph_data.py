"""
generate_graph_data.py — Build graph_data.json from rag_corpus.json
Governance: CCO-UPC §1 (Dumb Reader — reads corpus, writes graph, never modifies source)
Edges: page co-occurrence (weight 1), shared size (weight 2), shared material (weight 3)
"""
import json, os, sys
from itertools import combinations

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(SCRIPT_DIR, "data", "rag_corpus.json")
OUTPUT = os.path.join(SCRIPT_DIR, "data", "graph_data.json")

with open(CORPUS, "r", encoding="utf-8") as f:
    corpus = json.load(f)

nodes = []
edges = []
seen_edges = set()

for p in corpus:
    nid = f"PAGE-{p['page']}-{p['id']}"
    nodes.append({"id": nid, "part_id": p["id"], "stock_code": p["stock_code"],
                   "page": p["page"], "material": p["material"], "size": p["size"]})

def add_edge(src, tgt, weight):
    key = tuple(sorted([src, tgt]))
    if key not in seen_edges:
        seen_edges.add(key)
        edges.append({"source": src, "target": tgt, "weight": weight})

# Build edges
for i, a in enumerate(nodes):
    for b in nodes[i+1:]:
        if a["page"] == b["page"]:
            add_edge(a["id"], b["id"], 1)
        if a["size"] and b["size"] and a["size"] == b["size"] and a["page"] != b["page"]:
            add_edge(a["id"], b["id"], 2)
        if a["material"] and b["material"] and a["material"] == b["material"] and a["page"] != b["page"]:
            add_edge(a["id"], b["id"], 3)

graph = {"nodes": nodes, "edges": edges}
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(graph, f, indent=2, ensure_ascii=False)

print(f"Graph: {len(nodes)} nodes, {len(edges)} edges -> {OUTPUT}")
