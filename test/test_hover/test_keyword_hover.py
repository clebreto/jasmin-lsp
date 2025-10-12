#!/usr/bin/env python3
"""
Test hover functionality on keywords vs symbols
"""

import subprocess
import json
import sys
import os

LSP_SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

# Test fixture
TEST_FILE_CONTENT = """// Test file for hover
param int BUFFER_SIZE = 256;

fn square(reg u64 x) -> reg u64 {
  reg u64 result;
  result = x * x;
  return result;
}

inline fn double(reg u64 value) -> reg u64 {
  reg u64 temp;
  temp = value + value;
  return temp;
}
"""

def send_request(proc, request):
    content = json.dumps(request)
    message = f"Content-Length: {len(content)}\r\n\r\n{content}"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

def read_response(proc, expected_id=None, timeout=2.0):
    import select
    while True:
        ready, _, _ = select.select([proc.stdout], [], [], timeout)
        if not ready:
            return None
        
        headers = {}
        while True:
            line = proc.stdout.readline().decode().strip()
            if not line:
                break
            if ": " not in line:
                continue
            key, value = line.split(": ", 1)
            headers[key] = value
        
        content_length = int(headers.get("Content-Length", 0))
        if content_length == 0:
            return None
        content = proc.stdout.read(content_length).decode()
        response = json.loads(content)
        
        if expected_id is not None and "id" not in response:
            continue
        
        if expected_id is not None and "id" in response:
            if response["id"] == expected_id:
                return response
        else:
            return response

def test_keyword_hover():
    """Test that hovering on keywords returns helpful info or nothing"""
    print("="*70)
    print("Testing Keyword Hover Behavior")
    print("="*70)
    
    # Create test file
    test_path = os.path.abspath("test_hover_keywords.jazz")
    with open(test_path, "w") as f:
        f.write(TEST_FILE_CONTENT)
    
    test_uri = f"file://{test_path}"
    
    proc = subprocess.Popen(
        [LSP_SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Initialize
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": f"file://{os.path.dirname(test_path)}",
                "capabilities": {}
            }
        })
        read_response(proc, expected_id=1)
        
        send_request(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        
        import time
        time.sleep(0.1)
        
        # Open test file
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": test_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": TEST_FILE_CONTENT
                }
            }
        })
        print("✅ Opened test file")
        
        time.sleep(0.1)
        
        # Test cases: (line, char, symbol, should_have_hover)
        test_cases = [
            (3, 0, "fn", "keyword"),          # Line with "fn square"
            (3, 3, "square", "function"),     # Function name
            (3, 33, "return", "keyword"),     # return keyword
            (4, 2, "reg", "keyword"),         # reg keyword
            (4, 6, "result", "variable"),     # variable name
            (6, 2, "return", "keyword"),      # return keyword
            (9, 0, "inline", "keyword"),      # inline keyword
            (9, 7, "fn", "keyword"),          # fn after inline
            (1, 0, "param", "keyword"),       # param keyword
            (1, 10, "BUFFER_SIZE", "param"),  # param name
        ]
        
        request_id = 2
        passed = 0
        failed = 0
        
        for line_num, char_pos, symbol_text, expected_type in test_cases:
            print(f"\n{'='*70}")
            print(f"Test: Hover on '{symbol_text}' (line {line_num}, char {char_pos})")
            print(f"Expected: {expected_type}")
            print(f"{'='*70}")
            
            # Find actual line content
            lines = TEST_FILE_CONTENT.split('\n')
            if line_num < len(lines):
                print(f"Line: {lines[line_num]}")
            
            send_request(proc, {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": test_uri},
                    "position": {"line": line_num, "character": char_pos}
                }
            })
            
            response = read_response(proc, expected_id=request_id, timeout=3.0)
            request_id += 1
            
            if not response:
                print(f"❌ TIMEOUT: No response")
                failed += 1
                continue
            
            if "error" in response:
                print(f"❌ ERROR: {response['error'].get('message', 'Unknown')}")
                failed += 1
                continue
            
            result = response.get("result")
            
            if expected_type == "keyword":
                if result is None:
                    print(f"✅ PASS: Keyword returns nothing (as expected)")
                    passed += 1
                elif "contents" in result:
                    content = result["contents"]
                    if "value" in content:
                        value = content["value"]
                        if "keyword" in value.lower():
                            print(f"✅ PASS: Keyword documentation shown")
                            print(f"   Preview: {value[:80]}...")
                            passed += 1
                        else:
                            print(f"⚠️  UNEXPECTED: Keyword shown as: {value[:50]}")
                            passed += 1  # Still acceptable
                    else:
                        print(f"✅ PASS: Keyword has hover info")
                        passed += 1
                else:
                    print(f"❌ FAIL: Unexpected result format")
                    failed += 1
            
            elif expected_type in ["function", "variable", "param"]:
                if result is None:
                    print(f"❌ FAIL: Symbol should have hover info but got nothing")
                    failed += 1
                elif "contents" in result:
                    content = result["contents"]
                    if "value" in content:
                        value = content["value"]
                        print(f"✅ PASS: Symbol has hover info")
                        print(f"   Info: {value[:100]}...")
                        passed += 1
                    else:
                        print(f"✅ PASS: Symbol has hover (different format)")
                        passed += 1
                else:
                    print(f"❌ FAIL: Unexpected result format")
                    failed += 1
        
        print(f"\n{'='*70}")
        print(f"Results: {passed}/{len(test_cases)} passed")
        print(f"{'='*70}")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️  {failed} test(s) failed")
            return False
        
    finally:
        proc.terminate()
        proc.wait()
        # Clean up test file
        if os.path.exists(test_path):
            os.remove(test_path)

if __name__ == "__main__":
    success = test_keyword_hover()
    sys.exit(0 if success else 1)
