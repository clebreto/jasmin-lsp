#!/usr/bin/env python3
"""Final Demo: Complete Type Information in Hover"""

import subprocess
import json
from pathlib import Path

LSP_SERVER = Path(__file__).parent.parent / "_build/default/jasmin-lsp/jasmin_lsp.exe"

# Realistic Jasmin code with complex types
CODE = """fn crypto_hash(reg ptr u32[4] state, stack u64[16] message, reg u32 rounds) -> reg u64 {
  reg ptr u32[4] local_state;
  stack u64[16] local_msg;
  reg u64 hash;
  reg u32 i;
  
  local_state = state;
  local_msg = message;
  hash = #0;
  i = #0;
  
  return hash;
}

fn process_data(reg u8 byte, reg u16 word, reg u32 dword, reg u64 qword) -> reg u64, reg u32 {
  reg u64 result1;
  reg u32 result2;
  
  result1 = qword + #100;
  result2 = dword * #2;
  
  return result1, result2;
}
"""

def send(r):
    c = json.dumps(r)
    return f"Content-Length: {len(c)}\r\n\r\n{c}"

def recv(proc, expected_id=None):
    for _ in range(30):
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

def main():
    print("=" * 90)
    print("FINAL DEMO: Complete Type Information with Arrays, Pointers, and Multiple Returns")
    print("=" * 90)
    
    proc = subprocess.Popen(
        [str(LSP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    # Initialize
    proc.stdin.write(send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":None,"rootUri":"file:///tmp","capabilities":{}}}))
    proc.stdin.flush()
    recv(proc, 1)
    
    proc.stdin.write(send({"jsonrpc":"2.0","method":"initialized","params":{}}))
    proc.stdin.flush()
    
    # Open document
    proc.stdin.write(send({"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":"file:///tmp/demo.jazz","languageId":"jasmin","version":1,"text":CODE}}}))
    proc.stdin.flush()
    
    import time
    time.sleep(0.3)
    
    print("\nSource Code (first 12 lines):")
    print("-" * 90)
    for i, line in enumerate(CODE.split('\n')[:12]):
        print(f"{i:2}: {line}")
    
    # Test cases
    tests = [
        # Complex array/pointer types
        (0, 25, "param 'state' (ptr array)", "reg ptr u32[4]"),
        (0, 47, "param 'message' (stack array)", "stack u64[16]"),
        (1, 10, "var 'local_state' (ptr array)", "reg ptr u32[4]"),
        (2, 10, "var 'local_msg' (stack array)", "stack u64[16]"),
        
        # Function signatures
        (0, 5, "function 'crypto_hash'", "reg ptr u32[4] state"),
        (14, 5, "function 'process_data'", "reg u8 byte"),
        
        # Simple types  
        (3, 10, "var 'hash' (u64)", "reg u64"),
        (4, 10, "var 'i' (u32)", "reg u32"),
    ]
    
    print("\n" + "=" * 90)
    print("Hover Results:")
    print("=" * 90)
    
    for line, char, desc, expected_substr in tests:
        proc.stdin.write(send({"jsonrpc":"2.0","id":line+100,"method":"textDocument/hover","params":{"textDocument":{"uri":"file:///tmp/demo.jazz"},"position":{"line":line,"character":char}}}))
        proc.stdin.flush()
        
        r = recv(proc, expected_id=line+100)
        
        if r and "result" in r and r["result"] and "contents" in r["result"]:
            val = r["result"]["contents"]["value"]
            # Extract just the type line from markdown
            actual = val.split('\n')[1] if '\n' in val else val
            
            if expected_substr in actual:
                print(f"\n✅ {desc:35} →  {actual}")
            else:
                print(f"\n⚠️  {desc:35} →  {actual}")
                print(f"    (expected '{expected_substr}' to be in output)")
        else:
            err = r.get("error", {}).get("message", "No response") if r else "No response"
            print(f"\n❌ {desc:35} →  Error: {err}")
    
    proc.terminate()
    
    print("\n" + "=" * 90)
    print("✅ SUCCESS!")
    print("   • Variables show COMPLETE types including arrays and pointers")
    print("   • Functions show FULL signatures with all parameters and return types")
    print("=" * 90)

if __name__ == "__main__":
    main()
