#!/usr/bin/env python3
import json
import subprocess
import sys
import os

server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'
fixture_path = 'test/fixtures/simple_function.jazz'

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
        'method': 'textDocument/definition',
        'params': {
            'textDocument': {'uri': f'file://{os.path.abspath(fixture_path)}'},
            'position': {'line': 17, 'character': 10}  # Position of 'add_numbers' call (line 18, 0-indexed as 17)
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

print("=== Definition Response ===")
# Find the response to request id=2
for line in result.stdout.split('\n'):
    if '"id":2' in line or '"result"' in line or '"error"' in line:
        print(line)

print("\n=== STDERR (relevant) ===")
for line in result.stderr.split('\n'):
    if 'definition' in line.lower() or 'error' in line.lower():
        print(line)
