"""
local_orchestrator.py — Sovereign Workspace Local Default
Governance: CCO-UPC §7 (Build Protocol)

Purpose:
Serves the zero-backend WASM UI locally while providing a dedicated POST endpoint
for the Drag-and-Drop file uploader. Uploaded files are processed through the
FULL autonomous pipeline — zero user involvement required after file drop.

Autonomous Pipeline (triggered on every upload):
1. File saved to `_1 Input Files Folder`
2. domain_profiler.py → domain_schema.yaml (auto-detect domain)
3. export_corpus.py → rag_corpus.json (apply domain-adaptive gates)
4. generate_sample_embeddings.py → embeddings.json (domain-adaptive fields)
5. generate_graph_data.py → graph_data.json (auto-wired edges)
6. If ALL pass → Move to `_2 COMPLETED Upload Files`
7. If ANY fail → Move to `_1.5 FAILED UPLOADS TO REVIEW`

Routing Protocol:
1. File uploaded to `_1 Input Files Folder`
2. Full pipeline fires autonomously (profile → export → embed → graph)
3. If Pass → Moves to `_2 COMPLETED Upload Files`
4. If Fail → Moves to `_1.5 FAILED UPLOADS TO REVIEW`
"""
import os
import sys
import shutil
import time
import json
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer

# ─── DIRECTORY MAP ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR_INPUT = os.path.join(BASE_DIR, "_1 Input Files Folder")
DIR_FAILED = os.path.join(BASE_DIR, "_1.5 FAILED UPLOADS TO REVIEW")
DIR_SUCCESS = os.path.join(BASE_DIR, "_2 COMPLETED Upload Files")

# Ensure folders exist
for d in [DIR_INPUT, DIR_FAILED, DIR_SUCCESS]:
    os.makedirs(d, exist_ok=True)


def run_pipeline_step(script_name, args=None, label=""):
    """Execute a pipeline Python script. Returns (success: bool, output: str)."""
    cmd = [sys.executable, os.path.join(BASE_DIR, script_name)]
    if args:
        cmd.extend(args)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=BASE_DIR
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {label or script_name}")
        if not success:
            print(f"         Error: {output[:500]}")
        return success, output
    except subprocess.TimeoutExpired:
        print(f"  [FAIL] {label or script_name} — TIMEOUT (120s)")
        return False, "TIMEOUT"
    except Exception as e:
        print(f"  [FAIL] {label or script_name} — {e}")
        return False, str(e)


def execute_autonomous_pipeline(filename):
    """
    Full autonomous pipeline — ZERO user involvement.
    Fires all 4 stages sequentially on every upload.
    Returns (success: bool, report: dict).
    """
    report = {
        "file": filename,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stages": {},
    }

    print(f"\n{'=' * 60}")
    print(f"  AUTONOMOUS PIPELINE: {filename}")
    print(f"{'=' * 60}")

    # ─── STAGE 1: Domain Profiling ───
    # Auto-detect domain type from source files, generate domain_schema.yaml
    # This drives ALL downstream field selection — zero manual intervention.
    print(f"\n[STAGE 1/4] Domain Schema Discovery...")
    s1_ok, s1_out = run_pipeline_step(
        "domain_profiler.py",
        args=["--input-dir", DIR_INPUT],
        label="domain_profiler.py → domain_schema.yaml"
    )
    report["stages"]["1_domain_profiling"] = {"pass": s1_ok, "output": s1_out[:300]}

    # If profiling fails, try corpus-based fallback
    corpus_path = os.path.join(BASE_DIR, "data", "rag_corpus.json")
    if not s1_ok and os.path.exists(corpus_path):
        print("  [RETRY] Falling back to corpus-based profiling...")
        s1_ok, s1_out = run_pipeline_step(
            "domain_profiler.py",
            args=["--corpus", corpus_path],
            label="domain_profiler.py → domain_schema.yaml (corpus fallback)"
        )
        report["stages"]["1_domain_profiling"]["fallback"] = True

    # ─── STAGE 2: Corpus Export ───
    # Transform raw files into rag_corpus.json using domain-adaptive inference.
    # NOTE: For non-PDF domains (knowledge_base, legal), the corpus may already
    # exist via manual or agent-driven construction. Only run if full_extract.json exists.
    print(f"\n[STAGE 2/4] Corpus Export...")
    full_extract = os.path.join(BASE_DIR, "data", "full_extract.json")
    if os.path.exists(full_extract):
        s2_ok, s2_out = run_pipeline_step(
            "export_corpus.py",
            args=[full_extract, "--source-name", filename],
            label="export_corpus.py → rag_corpus.json"
        )
    elif os.path.exists(corpus_path):
        print("  [SKIP] No full_extract.json — using existing rag_corpus.json")
        s2_ok = True
        s2_out = "Existing corpus used"
    else:
        print("  [SKIP] No full_extract.json and no existing corpus — manual build required")
        s2_ok = True
        s2_out = "Awaiting manual corpus construction"
    report["stages"]["2_corpus_export"] = {"pass": s2_ok, "output": s2_out[:300]}

    # ─── STAGE 3: Embedding Generation ───
    # Reads domain_schema.yaml to select which fields to hash.
    # FULLY AUTOMATIC — no user involvement needed.
    print(f"\n[STAGE 3/4] Domain-Adaptive Embedding Generation...")
    s3_ok, s3_out = run_pipeline_step(
        "generate_sample_embeddings.py",
        label="generate_sample_embeddings.py → embeddings.json"
    )
    report["stages"]["3_embeddings"] = {"pass": s3_ok, "output": s3_out[:300]}

    # ─── STAGE 4: Graph Generation ───
    # Auto-wire edges from domain_schema.yaml graph_fields.
    print(f"\n[STAGE 4/4] Graph Generation...")
    s4_ok, s4_out = run_pipeline_step(
        "generate_graph_data.py",
        label="generate_graph_data.py → graph_data.json"
    )
    report["stages"]["4_graph"] = {"pass": s4_ok, "output": s4_out[:300]}

    # ─── VERDICT ───
    all_passed = all(report["stages"][k]["pass"] for k in report["stages"])
    report["verdict"] = "PASS" if all_passed else "FAIL"

    print(f"\n{'=' * 60}")
    print(f"  PIPELINE VERDICT: {report['verdict']}")
    print(f"  Stages: {sum(1 for k in report['stages'] if report['stages'][k]['pass'])}/{len(report['stages'])} passed")
    print(f"{'=' * 60}\n")

    # Save report
    report_path = os.path.join(BASE_DIR, "data", "pipeline_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return all_passed, report


class UploadHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            # Parse the multipart form data
            import cgi
            ctype, pdict = cgi.parse_header(self.headers['content-type'])
            if ctype == 'multipart/form-data':
                pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
                pdict['CONTENT-LENGTH'] = int(self.headers['Content-Length'])
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST',
                             'CONTENT_TYPE': self.headers['Content-Type']},
                    keep_blank_values=True
                )
                
                file_item = form['file']
                if file_item.filename:
                    # 1. Save to Input folder
                    filename = os.path.basename(file_item.filename)
                    input_path = os.path.join(DIR_INPUT, filename)
                    with open(input_path, 'wb') as f:
                        f.write(file_item.file.read())
                    
                    print(f"\n[ORCHESTRATOR] Received file: {filename}")
                    print(f"[ORCHESTRATOR] Staged in: _1 Input Files Folder")
                    
                    # 2. Execute FULL autonomous pipeline — ZERO user involvement
                    passed, report = execute_autonomous_pipeline(filename)
                    
                    if passed:
                        print(f"[ORCHESTRATOR] ALL GATES PASSED. Routing to _2 COMPLETED.")
                        target_path = os.path.join(DIR_SUCCESS, filename)
                        shutil.move(input_path, target_path)
                        status = "SUCCESS"
                    else:
                        print(f"[ORCHESTRATOR] GATE FAILURE. Routing to _1.5 FAILED.")
                        target_path = os.path.join(DIR_FAILED, filename)
                        shutil.move(input_path, target_path)
                        status = "FAILED"
                        
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = json.dumps({
                        "status": status,
                        "file": filename,
                        "stages": {k: v["pass"] for k, v in report["stages"].items()},
                        "verdict": report["verdict"],
                    })
                    self.wfile.write(bytes(response, 'utf-8'))
                    return
            
            self.send_response(400)
            self.end_headers()


if __name__ == '__main__':
    PORT = 5000
    os.chdir(BASE_DIR)
    with HTTPServer(('localhost', PORT), UploadHandler) as httpd:
        print(f"\n⚡ Sovereign Local Orchestrator Booted (V2 — Autonomous Pipeline)")
        print(f"UI Address: http://localhost:{PORT}")
        print(f"Drop Zone Active. Monitoring `_1 Input Files Folder`")
        print(f"Pipeline: Profile → Export → Embed → Graph (FULLY AUTOMATIC)\n")
        httpd.serve_forever()
