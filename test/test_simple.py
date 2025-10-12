#!/usr/bin/env python3
import subprocess
import json
import os

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def send_message(proc, msg):
    msg_str = json.dumps(msg)
    content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
    proc.stdin.write(content.encode())
    proc.stdin.flush()
    print(f"SENT: {msg.get('method', msg.get('id', 'unknown'))}")

def read_response(proc):
    # Read headers
    headers = {}
    while True:
        line = proc.stdout.readline().decode('utf-8')
        if line == '\r\n' or line == '\n':
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    # Read content
    content_length = int(headers.get('Content-Length', 0))
    if content_length > 0:
        content = proc.stdout.read(content_length).decode('utf-8')
        return json.loads(content)
    return None

# Start server
proc = subprocess.Popen(
    [SERVER],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

try:
    # 1. Initialize
    print("\n=== INITIALIZE ===")
    send_message(proc, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": None,
            "rootUri": "file:///tmp",
            "capabilities": {}
        }
    })
    resp = read_response(proc)
    print(f"Response: {json.dumps(resp, indent=2)}")
    
    # 2. Initialized notification
    print("\n=== INITIALIZED ===")
    send_message(proc, {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    })
    
    # 3. Open document
    print("\n=== DID OPEN ===")
    content = """fn add_numbers(reg u64 x, reg u64 y) -> reg u64 {
  reg u64 result;
  result = x + y;
  return result;
}

export fn main(reg u64 input) -> reg u64 {
  reg u64 temp;
  temp = add_numbers(input, #42);
  return temp;
}"""
    
    send_message(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": "file:///tmp/test.jazz",
                "languageId": "jasmin",
                "version": 1,
                "text": content
            }
        }
    })
    
    # Give server time to process
    import time
    time.sleep(0.5)
    
    # 4. Go to definition
    print("\n=== GO TO DEFINITION ===")
    send_message(proc, {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/definition",
        "params": {
            "textDocument": {"uri": "file:///tmp/test.jazz"},
            "position": {"line": 8, "character": 9}  # "add_numbers" call
        }
    })
    resp = read_response(proc)
    print(f"Response: {json.dumps(resp, indent=2)}")
    
    # Check stderr for logs
    print("\n=== SERVER LOGS ===")
    proc.terminate()
    proc.wait(timeout=1)
    stderr = proc.stderr.read().decode('utf-8')
    print(stderr)
    
except Exception as e:
    print(f"Error: {e}")
    proc.kill()
finally:
    proc.kill()
