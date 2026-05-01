"""
export_corpus.py — Full Extract to WASM Corpus Transformer
═══════════════════════════════════════════════════════════
Governance: CCO-UPC §1 (Dumb Reader Severance)
Purpose: Transforms full_extract.json (nested pages/parts) into
         rag_corpus.json (flat array for browser lunr.js indexing).

Usage:
    python export_corpus.py <path_to_full_extract.json> [--source-name everflow_catalog_2026.pdf]

Output:
    data/rag_corpus.json   — The browser-ready corpus
    data/rejected_log.json — Records that failed pre-flight gates
"""
import json
import os
import sys
import re
import argparse
from difflib import SequenceMatcher

# ─── Configuration ───
MIN_CODE_LENGTH = 3
MAX_CODE_LENGTH = 30
CONFIDENCE_FLOOR = 0.40
CONFIDENCE_APPROVED = 0.80
OCR_CONFIDENCE_PENALTY = 0.30

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_CORPUS = os.path.join(SCRIPT_DIR, "data", "rag_corpus.json")
OUTPUT_REJECTED = os.path.join(SCRIPT_DIR, "data", "rejected_log.json")

# ─── Domain-Adaptive Inference ───
# Reads domain_schema.yaml (from domain_profiler.py) to determine material/category
# keywords. Falls back to hardcoded plumbing defaults if no schema exists.
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "domain_schema.yaml")
DOMAIN_TYPE = "parts_catalog"  # default
DOMAIN_MATERIAL_KEYWORDS = None
DOMAIN_CATEGORY_KEYWORDS = None
DOMAIN_ID_PREFIX = "PXR"

if os.path.exists(SCHEMA_PATH):
    try:
        import yaml
        with open(SCHEMA_PATH, "r", encoding="utf-8") as sf:
            _schema = yaml.safe_load(sf)
        _ds = _schema["domain_schema"]
        DOMAIN_TYPE = _ds.get("domain_type", "parts_catalog")
        DOMAIN_MATERIAL_KEYWORDS = _ds.get("inference_config", {}).get("material_keywords", None)
        DOMAIN_CATEGORY_KEYWORDS = _ds.get("inference_config", {}).get("category_keywords", None)
        DOMAIN_ID_PREFIX = _ds.get("field_profile", {}).get("id_prefix", "PXR")
        print(f"[EXPORT] Domain-adaptive mode: {DOMAIN_TYPE}")
        print(f"[EXPORT] ID prefix: {DOMAIN_ID_PREFIX}")
        if DOMAIN_MATERIAL_KEYWORDS:
            print(f"[EXPORT] Material keywords: {DOMAIN_MATERIAL_KEYWORDS[:8]}...")
    except Exception as e:
        print(f"[EXPORT] Schema read failed ({e}) — using plumbing defaults")


def infer_material(description, raw_line=""):
    """Infer material from description text using domain-adaptive keywords."""
    text = f"{description} {raw_line}".lower()

    # If domain_schema.yaml provided material keywords, use those
    if DOMAIN_MATERIAL_KEYWORDS and DOMAIN_TYPE != "parts_catalog":
        for kw in DOMAIN_MATERIAL_KEYWORDS:
            if kw.lower() in text:
                return kw.lower().replace(" ", "_")
        return ""

    # Fallback: original plumbing inference (backward-compatible)
    mappings = {
        "brass": ["brass", "brz"],
        "copper": ["copper", "cu "],
        "cast_iron": ["cast iron", "c.i."],
        "stainless_steel": ["stainless", " ss ", "s.s."],
        "black_iron": ["black iron", "b.i.", "black malleable"],
        "galvanized_steel": ["galvanized", "galv"],
        "composite": ["composite", "pex", "pushlock"],
        "cpvc": ["cpvc"],
        "abs": [" abs "],
        "chrome": ["chrome"],
        "csst": ["csst"],
    }
    for material, keywords in mappings.items():
        for kw in keywords:
            if kw in text:
                return material
    return ""


def infer_category(description):
    """Infer category from description using domain-adaptive keywords."""
    text = description.lower()

    # If domain_schema.yaml provided category keywords, use those
    if DOMAIN_CATEGORY_KEYWORDS and DOMAIN_TYPE != "parts_catalog":
        for kw in DOMAIN_CATEGORY_KEYWORDS:
            if kw.lower() in text:
                return kw.strip().title()
        return "General"

    # Fallback: original plumbing inference (backward-compatible)
    if "coupling" in text:
        if "press" in text: return "TitanPress > Couplings"
        if "pushlock" in text or "push" in text: return "PushLock > Couplings"
        return "Fittings > Couplings"
    if "elbow" in text or "ell " in text:
        if "pushlock" in text or "push" in text: return "PushLock > Elbows"
        if "45" in text: return "Fittings > Elbows"
        return "Fittings > Elbows"
    if "tee" in text: return "Fittings > Tees"
    if "ball valve" in text: return "Valves > Ball Valves"
    if "gate valve" in text: return "Valves > Gate Valves"
    if "nipple" in text: return "Nipples > Black Iron"
    if "faucet supply" in text or "supply line" in text: return "Water Supply > Faucet Supply"
    if "water heater" in text: return "Water Supply > Water Heater"
    if "p-trap" in text or "trap" in text:
        if "tubular" in text: return "Tubular > P-Traps"
        return "Drainage > P-Traps"
    if "flex" in text: return "Flex Connectors"
    if "gas connector" in text or "csst" in text: return "Gas Connectors"
    if "hanger" in text: return "Pipe Hangers > Ring Type"
    if "tubular" in text and "extension" in text: return "Tubular > Extensions"
    return "Uncategorized"


def infer_size(description, raw_line=""):
    """Extract size from description or raw_line."""
    text = f"{description} {raw_line}"
    match = re.search(r'(\d+-?\d*/?\d*")', text)
    if match:
        return match.group(1)
    match = re.search(r'(\d+-?\d*/?\d*)\s*(?:inch|in\.)', text, re.IGNORECASE)
    if match:
        return match.group(1) + '"'
    return ""


def apply_pre_flight_gates(code, description, confidence, engine):
    """Apply CCO-UPC §1 composition guards. Returns (pass, rejection_reasons)."""
    reasons = []

    if not code or not code.strip():
        reasons.append("Empty stock_code")
    elif len(code) < MIN_CODE_LENGTH:
        reasons.append(f"Too short ({len(code)} < {MIN_CODE_LENGTH})")
    elif len(code) > MAX_CODE_LENGTH:
        reasons.append(f"Too long ({len(code)} > {MAX_CODE_LENGTH})")

    if code and code.isdigit():
        reasons.append("All digits (likely dimension/page number)")
    if code and code.isalpha() and len(code) > 2:
        reasons.append("All letters (likely table header)")

    if confidence < CONFIDENCE_FLOOR:
        reasons.append(f"Below confidence floor ({confidence:.2f} < {CONFIDENCE_FLOOR})")

    return len(reasons) == 0, reasons


def export(source_path, source_name):
    """Main export pipeline."""
    print(f"[EXPORT] Loading: {source_path}")
    with open(source_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Detect format: V3/V4 nested pages or flat array
    if isinstance(data, list):
        # Already flat
        raw_parts = data
    elif isinstance(data, dict) and "pages" in data:
        # Nested pages[].parts[] format
        raw_parts = []
        for page in data["pages"]:
            page_num = page.get("page_number", page.get("page", 0))
            for part in page.get("parts", page.get("matches", [])):
                part["_page"] = page_num
                raw_parts.append(part)
    else:
        print("[ERROR] Unrecognized format. Expected list or {pages: [...]}.")
        sys.exit(1)

    print(f"[EXPORT] Found {len(raw_parts)} raw records")

    corpus = []
    rejected = []
    seq = 0

    # Determine ID prefix from domain_schema.yaml or source name
    prefix = DOMAIN_ID_PREFIX  # From schema (default: PXR)
    if DOMAIN_TYPE == "parts_catalog":
        # Parts catalogs still use source-name-based prefixes for backward compat
        if "everflow" in source_name.lower() or "evf" in source_name.lower():
            prefix = "EVF"
        elif "jones" in source_name.lower() or "js" in source_name.lower():
            prefix = "JS"

    for part in raw_parts:
        seq += 1
        code = part.get("stock_code", part.get("part_number", part.get("code", "")))
        desc = part.get("description", part.get("desc", ""))
        conf = float(part.get("confidence", 0.50))
        eng = part.get("engine", "text_layer")
        page = int(part.get("_page", part.get("page", 0)))
        raw = part.get("raw_line", part.get("raw_text", f"{code}  {desc}"))
        visual_anchor = part.get("visual_anchor_uri", part.get("crop_image_path", ""))

        # Apply OCR penalty
        if eng == "ocr" and conf > 0.3:
            conf = max(0.0, conf - OCR_CONFIDENCE_PENALTY)

        # Apply pre-flight gates
        passed, reasons = apply_pre_flight_gates(code, desc, conf, eng)

        if not passed:
            rejected.append({
                "id": f"{prefix}-{seq:03d}",
                "stock_code": code,
                "description": desc,
                "reasons": reasons,
            })
            continue

        record = {
            "id": f"{prefix}-{seq:03d}",
            "stock_code": code.strip(),
            "description": desc.strip(),
            "page": page,
            "engine": eng,
            "confidence": round(conf, 2),
            "material": infer_material(desc, raw),
            "size": infer_size(desc, raw),
            "category": infer_category(desc),
            "source": source_name,
            "raw_line": raw.strip(),
            "visual_anchor_uri": visual_anchor,
        }

        # Cross-reference check: stock_code should be in raw_line
        if conf >= 0.90 and code.strip() not in raw.strip():
            record["confidence"] = round(max(0.0, conf - 0.15), 2)

        corpus.append(record)

    # Write outputs
    os.makedirs(os.path.dirname(OUTPUT_CORPUS), exist_ok=True)

    with open(OUTPUT_CORPUS, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)
    print(f"[EXPORT] Corpus written: {OUTPUT_CORPUS} ({len(corpus)} records)")

    with open(OUTPUT_REJECTED, "w", encoding="utf-8") as f:
        json.dump(rejected, f, indent=2, ensure_ascii=False)
    print(f"[EXPORT] Rejected log: {OUTPUT_REJECTED} ({len(rejected)} records)")

    print(f"\n  Total raw:     {len(raw_parts)}")
    print(f"  Accepted:      {len(corpus)}")
    print(f"  Rejected:      {len(rejected)}")
    print(f"  Acceptance:    {len(corpus)/len(raw_parts)*100:.1f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export full_extract.json to WASM rag_corpus.json")
    parser.add_argument("source", help="Path to full_extract.json")
    parser.add_argument("--source-name", default="catalog.pdf", help="Source PDF filename for metadata")
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"[ERROR] Source file not found: {args.source}")
        sys.exit(1)

    export(args.source, args.source_name)
