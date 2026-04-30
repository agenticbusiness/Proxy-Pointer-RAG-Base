"""
local_orchestrator.py — Sovereign Workspace Local Default
Governance: CCO-UPC §7 (Build Protocol)

Purpose:
Serves the zero-backend WASM UI locally while providing a dedicated POST endpoint
for the Drag-and-Drop file uploader. Uploaded PDFs are processed and routed cleanly.

Routing Protocol:
1. File uploaded to `_1 Input Files Folder`
2. Pipeline logic runs (or simulated for default template)
3. If Pass → Moves to `_2 COMPLETED Upload Files`
4. If Fail → Moves to `_1.5 FAILED UPLOADS TO REVIEW`
"""
import os, sys, shutil, time
from http.server import SimpleHTTPRequestHandler, HTTPServer
import cgi

# ─── DIRECTORY MAP ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR_INPUT = os.path.join(BASE_DIR, "_1 Input Files Folder")
DIR_FAILED = os.path.join(BASE_DIR, "_1.5 FAILED UPLOADS TO REVIEW")
DIR_SUCCESS = os.path.join(BASE_DIR, "_2 COMPLETED Upload Files")

# Ensure folders exist
for d in [DIR_INPUT, DIR_FAILED, DIR_SUCCESS]:
    os.makedirs(d, exist_ok=True)

class UploadHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            # Parse the multipart form data
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
                    
                    # 2. Execute Pipeline (Mocked logic for template)
                    print(f"[ORCHESTRATOR] Running pre-flight extraction gates...")
                    time.sleep(1.5) # Simulate processing
                    
                    # Simulated gate logic (Reject if filename contains 'reject')
                    passed_gates = "reject" not in filename.lower()
                    
                    if passed_gates:
                        print(f"[ORCHESTRATOR] Gate passed. Routing to _2 COMPLETED.")
                        target_path = os.path.join(DIR_SUCCESS, filename)
                        shutil.move(input_path, target_path)
                        status = "SUCCESS"
                    else:
                        print(f"[ORCHESTRATOR] Gate failed. Routing to _1.5 FAILED.")
                        target_path = os.path.join(DIR_FAILED, filename)
                        shutil.move(input_path, target_path)
                        status = "FAILED"
                        
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(bytes(f'{{"status": "{status}", "file": "{filename}"}}', 'utf-8'))
                    return
            
            self.send_response(400)
            self.end_headers()

if __name__ == '__main__':
    PORT = 5000
    os.chdir(BASE_DIR)
    with HTTPServer(('localhost', PORT), UploadHandler) as httpd:
        print(f"\n⚡ Sovereign Local Orchestrator Booted")
        print(f"UI Address: http://localhost:{PORT}")
        print(f"Drop Zone Active. Monitoring `_1 Input Files Folder`\n")
        httpd.serve_forever()
