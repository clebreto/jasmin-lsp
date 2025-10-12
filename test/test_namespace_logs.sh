#!/bin/bash
# Quick test to see namespace resolution logs

cd /Users/clebreto/dev/splits/jasmin-lsp

echo "Starting LSP server and checking logs..."
echo ""

# Start LSP in background, capture stderr
_build/default/jasmin-lsp/jasmin_lsp.exe 2>&1 &
LSP_PID=$!

# Send a simple test via Python
python3 << 'EOF'
import json, subprocess, time

LSP_SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"
proc = subprocess.Popen([LSP_SERVER], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def send(req):
    s = json.dumps(req)
    msg = f"Content-Length: {len(s)}\r\n\r\n{s}"
    proc.stdin.write(msg.encode())
    proc.stdin.flush()

# Initialize
send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "processId": None,
    "rootUri": "file:///Users/clebreto/dev/splits/formosa-mldsa/x86-64/avx2/ml_dsa_65",
    "capabilities": {}
}})

time.sleep(0.2)

send({"jsonrpc": "2.0", "method": "initialized", "params": {}})

# Open ml_dsa.jazz
with open("/Users/clebreto/dev/splits/formosa-mldsa/x86-64/avx2/ml_dsa_65/ml_dsa.jazz") as f:
    content = f.read()

send({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
    "textDocument": {
        "uri": "file:///Users/clebreto/dev/splits/formosa-mldsa/x86-64/avx2/ml_dsa_65/ml_dsa.jazz",
        "languageId": "jasmin",
        "version": 1,
        "text": content
    }
}})

time.sleep(1)

# Check stderr for logs
stderr_output = proc.stderr.read(1000).decode('utf-8', errors='ignore')
print("=== LSP stderr output ===")
print(stderr_output if stderr_output else "(no output)")

proc.terminate()
proc.wait()
EOF

# Kill background LSP
kill $LSP_PID 2>/dev/null

echo ""
echo "Check above for namespace resolution logs"
