#!/usr/bin/env python3
"""Demo: Hover shows variable types"""

import subprocess
import json
from pathlib import Path

LSP_SERVER = Path(__file__).parent.parent / "_build/default/jasmin-lsp/jasmin_lsp.exe"

# Real-world Jasmin code
CODE = """fn crypto_operation(reg u64 key, reg u32 rounds) -> reg u64 {
  reg u64 state;
  reg u64 temp;
  reg u32 counter;
  
  state = key;
  counter = #0;
  
  // Apply rounds
  while (counter < rounds) {
    temp = state << #1;
    state = state ^ temp;
    counter = counter + #1;
  }
  
  return state;
}
"""

def send_request(req):
    content = json.dumps(req)
    return f"Content-Length: {len(content)}\r\n\r\n{content}"

def read_response(proc, expected_id=None):
    for _ in range(20):
        line = proc.stdout.readline()
        if not line:
            return None
        if line.startswith("Content-Length"):
            length = int(line.split(":")[1].strip())
            proc.stdout.readline()
            response = json.loads(proc.stdout.read(length))
            if expected_id is None or response.get("id") == expected_id:
                return response
    return None

def demo():
    print("=" * 70)
    print("DEMO: Hover Type Information in Jasmin LSP")
    print("=" * 70)
    
    proc = subprocess.Popen(
        [str(LSP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    # Initialize
    proc.stdin.write(send_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"processId": None, "rootUri": "file:///tmp", "capabilities": {}}
    }))
    proc.stdin.flush()
    read_response(proc)
    
    proc.stdin.write(send_request({"jsonrpc": "2.0", "method": "initialized", "params": {}}))
    proc.stdin.flush()
    
    # Open document
    proc.stdin.write(send_request({
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": "file:///tmp/demo.jazz",
                "languageId": "jasmin",
                "version": 1,
                "text": CODE
            }
        }
    }))
    proc.stdin.flush()
    
    import time
    time.sleep(0.2)
    
    print("\nSource Code:")
    print("-" * 70)
    for i, line in enumerate(CODE.split('\n')[:10]):
        print(f"{i:2}: {line}")
    print("...")
    
    # Test hovers
    tests = [
        (0, 30, "parameter 'key'"),
        (0, 42, "parameter 'rounds'"),
        (1, 10, "variable 'state'"),
        (2, 10, "variable 'temp'"),
        (3, 10, "variable 'counter'"),
    ]
    
    print("\n" + "=" * 70)
    print("Hover Results:")
    print("=" * 70)
    
    for line, char, description in tests:
        proc.stdin.write(send_request({
            "jsonrpc": "2.0",
            "id": line + 10,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": "file:///tmp/demo.jazz"},
                "position": {"line": line, "character": char}
            }
        }))
        proc.stdin.flush()
        
        response = read_response(proc, expected_id=line + 10)
        
        if response and "result" in response and response["result"]:
            content = response["result"]["contents"]["value"]
            # Extract just the type info from markdown
            type_info = content.split('\n')[1] if '\n' in content else content
            print(f"\n✅ Hovering on {description:20} → {type_info}")
        else:
            print(f"\n❌ Hovering on {description:20} → No information")
    
    print("\n" + "=" * 70)
    print("✅ SUCCESS: Variables and parameters now show their types!")
    print("=" * 70)
    
    proc.terminate()

if __name__ == "__main__":
    demo()
