#!/usr/bin/env python3
import json
import subprocess
import sys

server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'

# Test with syntax error - missing closing brace
text_with_error = """fn unclosed_brace(reg u64 a) -> reg u64 {
  reg u64 b;
  b = a;
  return b;
// Missing closing brace

fn extra_token(reg u64 c) -> reg u64 } {
  return c;
}
"""

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
                'uri': 'file:///tmp/test.jazz',
                'languageId': 'jasmin',
                'version': 1,
                'text': text_with_error
            }
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

print("=== STDOUT ===")
print(result.stdout)

print("\n=== STDERR (last 30 lines) ===")
lines = result.stderr.split('\n')
for line in lines[-30:]:
    print(line)

# Check for diagnostics
if 'publishDiagnostics' in result.stdout:
    print("\n✅ Diagnostics notification sent")
    if '"diagnostics":[]' in result.stdout:
        print("❌ But diagnostics list is empty - no errors detected!")
    else:
        print("✅ Diagnostics contains errors")
else:
    print("\n❌ No diagnostics notification")
