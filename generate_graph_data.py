"""
generate_graph_data.py — Build graph_data.json from rag_corpus.json
Governance: CCO-UPC §1 (Dumb Reader — reads corpus, writes graph, never modifies source)

V2: Domain-adaptive edge wiring via domain_schema.yaml
  - parts_catalog: page co-occurrence (w1), shared size (w2), shared material (w3)
  - knowledge_base: shared source (w1), shared category (w2), shared material/domain (w3)
  - legal/financial: shared source (w1), shared category (w2)
"""
import json, os, sys

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(SCRIPT_DIR, "data", "rag_corpus.json")
OUTPUT = os.path.join(SCRIPT_DIR, "data", "graph_data.json")
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "domain_schema.yaml")

with open(CORPUS, "r", encoding="utf-8") as f:
    corpus = json.load(f)

# ─── Load domain schema for adaptive edge wiring ───
DOMAIN_TYPE = "parts_catalog"
GRAPH_FIELDS = ["material", "category", "size", "source"]

if os.path.exists(SCHEMA_PATH) and HAS_YAML:
    try:
        with open(SCHEMA_PATH, "r") as sf:
            schema = yaml.safe_load(sf)
        DOMAIN_TYPE = schema["domain_schema"].get("domain_type", "parts_catalog")
        GRAPH_FIELDS = schema["domain_schema"].get("field_profile", {}).get(
            "graph_fields", GRAPH_FIELDS
        )
        print(f"[GRAPH] Domain-adaptive mode: {DOMAIN_TYPE}")
        print(f"[GRAPH] Edge fields: {GRAPH_FIELDS}")
    except Exception as e:
        print(f"[GRAPH] Schema read failed ({e}) — using defaults")
else:
    print(f"[GRAPH] No domain_schema.yaml — using default edge wiring")

nodes = []
edges = []
seen_edges = set()

# Build nodes — domain-adaptive ID format
for p in corpus:
    node = {"id": p["id"], "label": p.get("description", p["id"])[:60]}
    # Add all graph-relevant fields as node properties
    for field in GRAPH_FIELDS:
        node[field] = p.get(field, "")
    # Always include page for parts_catalog
    if DOMAIN_TYPE == "parts_catalog":
        node["page"] = p.get("page", 0)
        node["stock_code"] = p.get("stock_code", "")
        node["size"] = p.get("size", "")
    nodes.append(node)


def add_edge(src, tgt, weight, edge_type="related"):
    key = tuple(sorted([src, tgt]))
    if src != tgt and key not in seen_edges:
        seen_edges.add(key)
        edges.append({
            "source": src, "target": tgt,
            "weight": weight, "type": edge_type
        })


# ─── Domain-Adaptive Edge Wiring ───
if DOMAIN_TYPE == "parts_catalog":
    # Original V1 logic: page, size, material
    for i, a in enumerate(nodes):
        for b in nodes[i+1:]:
            if a.get("page") and b.get("page") and a["page"] == b["page"]:
                add_edge(a["id"], b["id"], 1, "same_page")
            if (a.get("size") and b.get("size") and
                    a["size"] == b["size"] and a.get("page") != b.get("page")):
                add_edge(a["id"], b["id"], 2, "same_size")
            if (a.get("material") and b.get("material") and
                    a["material"] == b["material"] and a.get("page") != b.get("page")):
                add_edge(a["id"], b["id"], 3, "same_material")
else:
    # Domain-adaptive: wire edges by ALL graph_fields
    # Weight: 1 = shared source, 2 = shared category, 3 = shared material/domain
    weight_map = {
        "source": 1,
        "category": 2,
        "material": 3,
    }
    for i, a in enumerate(nodes):
        for b in nodes[i+1:]:
            best_weight = 0
            best_type = "related"
            for field in GRAPH_FIELDS:
                val_a = a.get(field, "")
                val_b = b.get(field, "")
                if val_a and val_b and val_a == val_b:
                    w = weight_map.get(field, 1)
                    if w > best_weight:
                        best_weight = w
                        best_type = f"same_{field}"
            if best_weight > 0:
                add_edge(a["id"], b["id"], best_weight, best_type)

graph = {"nodes": nodes, "edges": edges}
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(graph, f, indent=2, ensure_ascii=False)

print(f"Graph: {len(nodes)} nodes, {len(edges)} edges -> {OUTPUT}")
