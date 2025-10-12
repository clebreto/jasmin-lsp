#!/usr/bin/env python3
"""Test hover for complex types"""

import subprocess
import json
import sys
from pathlib import Path

LSP_SERVER = Path(__file__).parent.parent.parent / "_build/default/jasmin-lsp/jasmin_lsp.exe"

# Test with complex types
TEST_CODE = """fn process_arrays(reg ptr u32[2] data, stack u64[8] buffer) -> reg u64 {
  reg ptr u32[2] local_ptr;
  stack u64[8] local_buf;
  reg u64 result;
  
  local_ptr = data;
  local_buf = buffer;
  result = #42;
  
  return result;
}

fn multi_return_types(reg u64 a, reg u32 b) -> reg u64, reg u32 {
  reg u64 sum;
  reg u32 product;
  
  sum = a + #100;
  product = b * #2;
  
  return sum, product;
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

def test_complex_types():
    print("=" * 80)
    print("TEST: Complex Type Hover (Arrays, Pointers, Multiple Returns)")
    print("=" * 80)
    
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
                "uri": "file:///tmp/complex_types.jazz",
                "languageId": "jasmin",
                "version": 1,
                "text": TEST_CODE
            }
        }
    }))
    proc.stdin.flush()
    
    import time
    time.sleep(0.3)
    
    print("\nSource Code:")
    print("-" * 80)
    for i, line in enumerate(TEST_CODE.split('\n')[:15]):
        print(f"{i:2}: {line}")
    
    # Test cases: (line, char, description, expected_in_hover)
    tests = [
        (0, 25, "parameter 'data' (array pointer)", "ptr u32[2]"),
        (0, 47, "parameter 'buffer' (stack array)", "stack u64[8]"),
        (1, 10, "variable 'local_ptr' (array pointer)", "ptr u32[2]"),
        (2, 10, "variable 'local_buf' (stack array)", "stack u64[8]"),
        (0, 3, "function 'process_arrays'", "reg ptr u32[2] data"),
        (11, 3, "function 'multi_return_types'", "reg u64, reg u32"),
    ]
    
    print("\n" + "=" * 80)
    print("Hover Test Results:")
    print("=" * 80)
    
    all_passed = True
    
    for line, char, description, expected in tests:
        proc.stdin.write(send_request({
            "jsonrpc": "2.0",
            "id": line + 100,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": "file:///tmp/complex_types.jazz"},
                "position": {"line": line, "character": char}
            }
        }))
        proc.stdin.flush()
        
        response = read_response(proc, expected_id=line + 100)
        
        if response and "result" in response and response["result"]:
            content = response["result"]["contents"]["value"]
            # Extract the actual content from markdown
            lines = content.split('\n')
            actual = lines[1] if len(lines) > 1 else content
            
            # Check if expected text is in the hover content
            if expected in actual:
                print(f"\n✅ {description:40}")
                print(f"   → {actual}")
            else:
                print(f"\n❌ {description:40}")
                print(f"   Expected to contain: {expected}")
                print(f"   Got: {actual}")
                all_passed = False
        else:
            error_msg = response.get("error", {}).get("message", "No response") if response else "No response"
            print(f"\n❌ {description:40}")
            print(f"   Error: {error_msg}")
            all_passed = False
    
    proc.terminate()
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED - Complex types are displayed correctly!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    success = test_complex_types()
    sys.exit(0 if success else 1)
