#!/usr/bin/env python3
import json
import subprocess
import sys
import os

server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'
fixture_path = 'test/fixtures/types_test.jazz'

with open(fixture_path) as f:
    content = f.read()

messages = [
    {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'initialize',
        'params': {'processId': None, 'rootUri': 'file:///tmp', 'capabilities': {}}
    },
    {
        'jsonrpc': '2.0',
        'method': 'initialized',
        'params': {}
    },
    {
        'jsonrpc': '2.0',
        'method': 'textDocument/didOpen',
        'params': {
            'textDocument': {
                'uri': f'file://{os.path.abspath(fixture_path)}',
                'languageId': 'jasmin',
                'version': 1,
                'text': content
            }
        }
    },
    {
        'jsonrpc': '2.0',
        'id': 2,
        'method': 'textDocument/hover',
        'params': {
            'textDocument': {'uri': f'file://{os.path.abspath(fixture_path)}'},
            'position': {'line': 3, 'character': 5}  # Position in function name
        }
    }
]

input_data = ''
for msg in messages:
    content = json.dumps(msg)
    content_bytes = content.encode('utf-8')
    input_data += f'Content-Length: {len(content_bytes)}\r\n\r\n{content}'

result = subprocess.run(
    [server_path],
    input=input_data,
    capture_output=True,
    text=True,
    timeout=5
)

print("=== Hover Response ===")
# Find the response to request id=2
for line in result.stdout.split('\n'):
    if '"id":2' in line or ('"result"' in line and 'hover' in line.lower()) or '"error"' in line:
        print(line[:200])

print("\n=== STDERR (relevant) ===")
for line in result.stderr.split('\n'):
    if 'hover' in line.lower() or 'error' in line.lower() or 'exception' in line.lower():
        print(line)
