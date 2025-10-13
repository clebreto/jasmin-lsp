#!/usr/bin/env python3
"""Quick test for indented documentation."""

import subprocess
import json
import time
from pathlib import Path

def send_message(proc, msg):
    content = json.dumps(msg)
    message = f"Content-Length: {len(content)}\r\n\r\n{content}"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

def read_message(proc):
    headers = {}
    while True:
        line = proc.stdout.readline().decode('utf-8').strip()
        if not line:
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    content_length = int(headers.get('Content-Length', 0))
    if content_length == 0:
        return None
    
    content = proc.stdout.read(content_length).decode('utf-8')
    return json.loads(content)

def read_until_response(proc, request_id):
    while True:
        msg = read_message(proc)
        if msg is None:
            return None
        if 'id' in msg and msg['id'] == request_id:
            return msg

server_path = "./_build/default/jasmin-lsp/jasmin_lsp.exe"
test_file = Path(__file__).parent.parent / "fixtures" / "indented_doc.jazz"
content = test_file.read_text()
uri = f"file://{test_file.absolute()}"

proc = subprocess.Popen([server_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    # Initialize
    send_message(proc, {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {"processId": None, "rootUri": f"file://{Path.cwd()}", "capabilities": {}}
    })
    read_until_response(proc, 0)
    send_message(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
    time.sleep(0.1)
    
    # Open document
    send_message(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {"uri": uri, "languageId": "jasmin", "version": 1, "text": content}
        }
    })
    time.sleep(0.2)
    
    # Hover on poly_add
    send_message(proc, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": uri},
            "position": {"line": 9, "character": 4}
        }
    })
    response = read_until_response(proc, 1)
    
    if response and response.get('result'):
        value = response['result']['contents']['value']
        print("Hover content:")
        print(value)
        print("\n=== ANALYZING INDENTATION ===")
        lines = value.split('\n')
        for i, line in enumerate(lines):
            if 'Arguments:' in line or '- poly' in line or '- const' in line:
                spaces = len(line) - len(line.lstrip(' '))
                print(f"Line {i}: {spaces} leading spaces | {repr(line)}")
    else:
        print("No hover response")
        
finally:
    proc.terminate()
