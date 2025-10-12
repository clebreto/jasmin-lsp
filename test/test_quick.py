#!/usr/bin/env python3
"""Quick test to check error messages"""
import subprocess
import json
import time
import threading

server = subprocess.Popen(
    ['_build/default/jasmin-lsp/jasmin_lsp.exe'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=0
)

# Print stderr in background
def print_stderr():
    for line in iter(server.stderr.readline, ''):
        if line:
            print(f"[STDERR]: {line.rstrip()}")

stderr_thread = threading.Thread(target=print_stderr, daemon=True)
stderr_thread.start()

def send_request(method, params, req_id=None):
    request = {'jsonrpc': '2.0', 'method': method, 'params': params}
    if req_id is not None:
        request['id'] = req_id
    message = json.dumps(request)
    content = f'Content-Length: {len(message)}\r\n\r\n{message}'
    print(f"\n>>> SENDING: {method} (id={req_id})")
    server.stdin.write(content)
    server.stdin.flush()
    
def read_response():
    try:
        line = server.stdout.readline()
        if not line:
            return None
        while line and not line.startswith('Content-Length:'):
            if line.strip():
                print(f"[LOG]: {line.strip()}")
            line = server.stdout.readline()
        if line.startswith('Content-Length:'):
            length = int(line.split(':')[1].strip())
            server.stdout.readline()  # empty line
            response = server.stdout.read(length)
            return json.loads(response)
    except:
        return None
    return None

# Initialize
send_request('initialize', {'processId': None, 'rootUri': None, 'capabilities': {}}, 1)
resp = read_response()
print(f"<<< RESPONSE 1: {json.dumps(resp, indent=2)[:200]}...")

# Handle workspace/configuration request if sent
if resp and resp.get('method') == 'workspace/configuration':
    # Send empty config response
    send_request(None, {}, resp['id'])
    # Now read the actual initialize response
    resp = read_response()
    print(f"<<< INIT RESPONSE: {json.dumps(resp, indent=2)[:200]}...")

# Send initialized notification
send_request('initialized', {})
time.sleep(0.1)

# Open document
send_request('textDocument/didOpen', {
    'textDocument': {
        'uri': 'file:///test.jazz',
        'languageId': 'jasmin',
        'version': 1,
        'text': 'fn test() { reg u64 x = 1; return x; }'
    }
})
time.sleep(0.2)

# Try hover
send_request('textDocument/hover', {
    'textDocument': {'uri': 'file:///test.jazz'},
    'position': {'line': 0, 'character': 5}
}, 2)

resp = read_response()
print(f"\n<<< HOVER RESPONSE:")
print(json.dumps(resp, indent=2))

server.terminate()
