#!/usr/bin/env python3
import json
import subprocess
import sys

server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'

test_code = """fn test() {
  reg u32 i, j;
  stack u64 x, y, z;
}"""

print("Test code:")
print(test_code)
print("\nCharacter positions:")
for i, line in enumerate(test_code.split('\n')):
    print(f"Line {i}: {repr(line)}")
    for j, char in enumerate(line):
        print(f"  [{j}] = '{char}'")

# Test x at position (2, 13)
messages = [
    {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
     'params': {'processId': None, 'rootUri': 'file:///tmp', 'capabilities': {}}},
    {'jsonrpc': '2.0', 'method': 'initialized', 'params': {}},
    {'jsonrpc': '2.0', 'method': 'textDocument/didOpen',
     'params': {'textDocument': {'uri': 'file:///test.jazz', 'languageId': 'jasmin',
                                  'version': 1, 'text': test_code}}},
    {'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/hover',
     'params': {'textDocument': {'uri': 'file:///test.jazz'},
                'position': {'line': 2, 'character': 13}}}
]

input_data = ''
for msg in messages:
    content = json.dumps(msg)
    content_bytes = content.encode('utf-8')
    header = f'Content-Length: {len(content_bytes)}\r\n\r\n'
    input_data += header + content

proc = subprocess.Popen([server_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = proc.communicate(input=input_data.encode('utf-8'), timeout=5)

print("\nSTDERR:")
print(stderr.decode('utf-8', errors='ignore'))

print("\nResponse:")
output = stdout.decode('utf-8', errors='ignore')
if 'Content-Length:' in output:
    parts = output.split('Content-Length:')
    for part in parts[1:]:
        try:
            header_end = part.index('\r\n\r\n')
            length = int(part[:header_end].strip())
            body = part[header_end+4:header_end+4+length]
            resp = json.loads(body)
            print(json.dumps(resp, indent=2))
        except: pass
