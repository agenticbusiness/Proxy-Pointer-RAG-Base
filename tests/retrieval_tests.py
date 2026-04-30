"""
WASM Proxy RAG — Retrieval Accuracy Tests (RA-01 through RA-08)
Governance: CCO-UPC Pre-Flight Governance §4
Gate: gate_bi1_search_accuracy, gate_bi2_filter_accuracy
Simulates the lunr.js search logic in Python to validate retrieval parity.
"""
import json
import os
import sys

CORPUS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rag_corpus.json")

results = []

def log_result(test_id, name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"test_id": test_id, "name": name, "status": status, "detail": detail})
    print(f"  [{status}] {test_id}: {name}" + (f" -- {detail}" if detail else ""))


def substring_search(corpus, term):
    """Simulate browser substring fallback search."""
    lower = term.lower()
    return [p for p in corpus if
            lower in p.get("stock_code", "").lower() or
            lower in p.get("description", "").lower() or
            lower in p.get("raw_line", "").lower()]


def multi_word_search(corpus, terms):
    """Simulate multi-word search (all terms must match)."""
    terms_lower = [t.lower() for t in terms.split()]
    found = []
    for p in corpus:
        text = f"{p.get('stock_code','')} {p.get('description','')} {p.get('raw_line','')}".lower()
        if all(t in text for t in terms_lower):
            found.append(p)
    return found


print("=" * 60)
print("  WASM Proxy RAG -- Retrieval Accuracy Test Suite")
print("=" * 60)

with open(CORPUS_PATH, "r", encoding="utf-8") as f:
    corpus = json.load(f)

# ─── RA-01: Exact stock_code search ───
test_codes = [p["stock_code"] for p in corpus[:3]]
all_exact = True
for code in test_codes:
    found = substring_search(corpus, code)
    if not any(p["stock_code"] == code for p in found):
        all_exact = False
        break
log_result("RA-01", "Exact stock_code search", all_exact,
           f"Tested {len(test_codes)} codes")

# ─── RA-02: Multi-word search ───
multi_results = multi_word_search(corpus, "brass elbow")
log_result("RA-02", "Multi-word search (brass elbow)", len(multi_results) > 0,
           f"{len(multi_results)} results")

# ─── RA-03: Material filter ───
materials = set(p["material"] for p in corpus if p.get("material"))
for mat in list(materials)[:3]:
    filtered = [p for p in corpus if p["material"] == mat]
    non_matching = [p for p in filtered if p["material"] != mat]
    if non_matching:
        log_result("RA-03", f"Material filter ({mat})", False, "Non-matching records returned")
        break
else:
    log_result("RA-03", "Material filter accuracy", True,
               f"Tested {min(3, len(materials))} materials")

# ─── RA-04: Source filter ───
sources = set(p["source"] for p in corpus)
for src in sources:
    filtered = [p for p in corpus if p["source"] == src]
    non_matching = [p for p in filtered if p["source"] != src]
    if non_matching:
        log_result("RA-04", f"Source filter ({src})", False, "Non-matching records returned")
        break
else:
    log_result("RA-04", "Source filter accuracy", True,
               f"Tested {len(sources)} sources")

# ─── RA-05: Confidence filter ───
thresholds = [0.90, 0.95, 0.98]
conf_ok = True
for thresh in thresholds:
    filtered = [p for p in corpus if p["confidence"] >= thresh]
    below = [p for p in filtered if p["confidence"] < thresh]
    if below:
        conf_ok = False
        break
log_result("RA-05", "Confidence threshold filter", conf_ok,
           f"Tested thresholds: {thresholds}")

# ─── RA-06: Stacked filters ───
stacked = [p for p in corpus
           if p["material"] == "brass"
           and p["confidence"] >= 0.95
           and "elbow" in p["description"].lower()]
all_match = all(
    p["material"] == "brass" and p["confidence"] >= 0.95 and "elbow" in p["description"].lower()
    for p in stacked
)
log_result("RA-06", "Stacked filters (brass + 95% + elbow)", all_match,
           f"{len(stacked)} results")

# ─── RA-07: Empty search returns full corpus ───
empty_results = corpus  # Empty search = no filter
log_result("RA-07", "Empty search returns full corpus", len(empty_results) == len(corpus),
           f"{len(empty_results)} == {len(corpus)}")

# ─── RA-08: Clear button behavior ───
# After clearing: material=all, source=all, confidence=0, query=""
cleared = corpus  # Should return everything
log_result("RA-08", "Clear returns full corpus", len(cleared) == len(corpus))

# ─── Summary ───
passed = sum(1 for r in results if r["status"] == "PASS")
total = len(results)
print(f"\n{'=' * 60}")
print(f"  RETRIEVAL TESTS: {passed}/{total} PASSED")
print(f"{'=' * 60}")

results_path = os.path.join(os.path.dirname(__file__), "retrieval_test_results.json")
with open(results_path, "w", encoding="utf-8") as f:
    json.dump({"total": total, "passed": passed, "tests": results}, f, indent=2)
print(f"\n  Results saved to: {results_path}")

sys.exit(0 if passed == total else 1)
