#!/usr/bin/env python3
import subprocess, json
from pathlib import Path

lsp = Path(__file__).parent.parent / "_build/default/jasmin-lsp/jasmin_lsp.exe"
code = """fn test_arrays(reg ptr u32[2] data) -> reg u64 {
  reg ptr u32[2] local_ptr;
  return #0;
}"""

proc = subprocess.Popen([str(lsp)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=0)

def send(r):
    c = json.dumps(r)
    return f"Content-Length: {len(c)}\r\n\r\n{c}"

def recv(expected_id=None):
    for _ in range(20):
        line = proc.stdout.readline()
        if not line: return None
        if line.startswith("Content-Length"):
            length = int(line.split(":")[1].strip())
            proc.stdout.readline()
            r = json.loads(proc.stdout.read(length))
            if expected_id is None or r.get("id") == expected_id:
                return r

proc.stdin.write(send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":None,"rootUri":"file:///tmp","capabilities":{}}}))
proc.stdin.flush()
recv(1)

proc.stdin.write(send({"jsonrpc":"2.0","method":"initialized","params":{}}))
proc.stdin.flush()

proc.stdin.write(send({"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":"file:///tmp/t.jazz","languageId":"jasmin","version":1,"text":code}}}))
proc.stdin.flush()

import time
time.sleep(0.2)

proc.stdin.write(send({"jsonrpc":"2.0","id":2,"method":"textDocument/documentSymbol","params":{"textDocument":{"uri":"file:///tmp/t.jazz"}}}))
proc.stdin.flush()
r = recv(2)

print("Symbols:")
if "result" in r:
    for sym in r["result"]:
        print(f"  - {sym['name']:15} (kind={sym['kind']:2}): {sym.get('detail', 'no detail')}")

proc.terminate()
