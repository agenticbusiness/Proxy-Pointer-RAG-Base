"""
WASM Proxy RAG — Smoke Tests (ST-01 through ST-08)
Governance: CCO-UPC Pre-Flight Governance §4
Gate: gate_ci1_schema_compliance, gate_ci2_density_validation
"""
import json
import os
import sys

CORPUS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rag_corpus.json")
REQUIRED_FIELDS = ["id", "stock_code", "description", "page", "engine", "confidence", "material", "size", "category", "source", "raw_line"]

results = []

def log_result(test_id, name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"test_id": test_id, "name": name, "status": status, "detail": detail})
    print(f"  [{status}] {test_id}: {name}" + (f" -- {detail}" if detail else ""))

print("=" * 60)
print("  WASM Proxy RAG — Smoke Test Suite")
print("=" * 60)

# ─── ST-01: JSON Parseable ───
try:
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    assert isinstance(corpus, list), "Corpus must be a JSON array"
    log_result("ST-01", "JSON is parseable", True, f"{len(corpus)} records")
except Exception as e:
    log_result("ST-01", "JSON is parseable", False, str(e))
    print("\nHALT: Cannot proceed without valid JSON.")
    sys.exit(1)

# ─── ST-02: All IDs Unique ───
ids = [p["id"] for p in corpus]
unique_ids = set(ids)
log_result("ST-02", "All IDs unique", len(ids) == len(unique_ids),
           f"{len(ids)} total, {len(unique_ids)} unique")

# ─── ST-03: No Empty stock_codes ───
empty_codes = [p["id"] for p in corpus if not p.get("stock_code", "").strip()]
log_result("ST-03", "No empty stock_codes", len(empty_codes) == 0,
           f"{len(empty_codes)} empty" if empty_codes else "")

# ─── ST-04: No Empty Descriptions ───
empty_desc = [p["id"] for p in corpus if not p.get("description", "").strip()]
log_result("ST-04", "No empty descriptions", len(empty_desc) == 0,
           f"{len(empty_desc)} empty" if empty_desc else "")

# ─── ST-05: Confidence Range Valid ───
bad_conf = [p["id"] for p in corpus if not (0.0 <= p.get("confidence", -1) <= 1.0)]
log_result("ST-05", "Confidence range 0.0-1.0", len(bad_conf) == 0,
           f"{len(bad_conf)} out of range" if bad_conf else "")

# ─── ST-06: Page Numbers Positive ───
bad_pages = [p["id"] for p in corpus if not isinstance(p.get("page"), int) or p["page"] < 1]
log_result("ST-06", "Page numbers positive integers", len(bad_pages) == 0,
           f"{len(bad_pages)} invalid" if bad_pages else "")

# ─── ST-07: Source Field Populated ───
empty_source = [p["id"] for p in corpus if not p.get("source", "").strip()]
log_result("ST-07", "Source field populated", len(empty_source) == 0,
           f"{len(empty_source)} empty" if empty_source else "")

# ─── ST-08: Material Field Density ───
has_material = sum(1 for p in corpus if p.get("material", "").strip())
density = has_material / len(corpus) if corpus else 0
log_result("ST-08", "Material density >= 95%", density >= 0.95,
           f"{density:.1%} ({has_material}/{len(corpus)})")

# ─── ST-09: Required Fields Present ───
missing_fields = []
for p in corpus:
    for field in REQUIRED_FIELDS:
        if field not in p:
            missing_fields.append(f"{p.get('id', '?')}: missing {field}")
log_result("ST-09", "All required fields present", len(missing_fields) == 0,
           f"{len(missing_fields)} missing" if missing_fields else "")

# ─── ST-10: raw_line Contains stock_code (Cross-Ref) ───
raw_mismatches = []
for p in corpus:
    if p.get("confidence", 0) >= 0.90:
        sc = p.get("stock_code", "")
        rl = p.get("raw_line", "")
        if sc and rl and sc not in rl:
            raw_mismatches.append(p["id"])
log_result("ST-10", "stock_code in raw_line (conf>=0.90)", len(raw_mismatches) == 0,
           f"{len(raw_mismatches)} mismatches: {raw_mismatches[:5]}" if raw_mismatches else "")

# ─── Summary ───
passed = sum(1 for r in results if r["status"] == "PASS")
total = len(results)
print(f"\n{'=' * 60}")
print(f"  SMOKE TESTS: {passed}/{total} PASSED")
print(f"  Corpus: {len(corpus)} records, {len(set(p['source'] for p in corpus))} sources")
print(f"{'=' * 60}")

# Write results to JSON
results_path = os.path.join(os.path.dirname(__file__), "smoke_test_results.json")
with open(results_path, "w", encoding="utf-8") as f:
    json.dump({"total": total, "passed": passed, "tests": results}, f, indent=2)
print(f"\n  Results saved to: {results_path}")

sys.exit(0 if passed == total else 1)
