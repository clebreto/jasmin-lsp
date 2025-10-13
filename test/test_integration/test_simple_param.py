#!/usr/bin/env python3
import json
import subprocess

server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'
test_code = "fn test(reg u32 a, b) { }"

messages = [
    {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
     'params': {'processId': None, 'rootUri': 'file:///tmp', 'capabilities': {}}},
    {'jsonrpc': '2.0', 'method': 'initialized', 'params': {}},
    {'jsonrpc': '2.0', 'method': 'textDocument/didOpen',
     'params': {'textDocument': {'uri': 'file:///test.jazz', 'languageId': 'jasmin',
                                  'version': 1, 'text': test_code}}},
    {'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/documentSymbol',
     'params': {'textDocument': {'uri': 'file:///test.jazz'}}}
]

input_data = ''
for msg in messages:
    content = json.dumps(msg)
    header = f'Content-Length: {len(content.encode())}\r\n\r\n'
    input_data += header + content

proc = subprocess.Popen([server_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    stdout, stderr = proc.communicate(input=input_data.encode(), timeout=5)
except subprocess.TimeoutExpired:
    proc.kill()
    proc.communicate()
    raise
finally:
    # Ensure process is terminated
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

output = stdout.decode('utf-8', errors='ignore')
print("STDERR:\n", stderr.decode('utf-8', errors='ignore'))
print("\nResponse parsing...")
while 'Content-Length:' in output:
    try:
        idx = output.index('Content-Length:')
        output = output[idx:]
        header_end = output.index('\r\n\r\n')
        length = int(output[:header_end].split(':')[1].strip())
        body = output[header_end+4:header_end+4+length]
        resp = json.loads(body)
        if 'id' in resp and resp['id'] == 2:
            print("\nDocument symbols:")
            print(json.dumps(resp, indent=2))
        output = output[header_end+4+length:]
    except: break
