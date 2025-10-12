#!/usr/bin/env python3
"""
Test cross-file variable goto definition
"""

import subprocess
import json
import sys
import os

# Paths
LSP_SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

# Test fixture with global variable
GLOBALS_FILE = """// globals.jazz - defines global variables
param int BUFFER_SIZE = 256;

u64[4] shared_data = {1, 2, 3, 4};
"""

MAIN_FILE = """// main.jazz - uses globals from globals.jazz
require "globals.jazz"

fn use_globals() -> reg u64 {
  reg u64 result;
  reg u64 size;
  
  // Reference to parameter from globals.jazz
  size = BUFFER_SIZE;
  
  // Reference to global array from globals.jazz
  result = shared_data[0];
  
  return result;
}
"""

def create_test_files():
    """Create test fixture files"""
    os.makedirs("test/fixtures/variables", exist_ok=True)
    
    with open("test/fixtures/variables/globals.jazz", "w") as f:
        f.write(GLOBALS_FILE)
    
    with open("test/fixtures/variables/main.jazz", "w") as f:
        f.write(MAIN_FILE)
    
    return (
        os.path.abspath("test/fixtures/variables/globals.jazz"),
        os.path.abspath("test/fixtures/variables/main.jazz")
    )

def send_request(proc, request):
    """Send a JSON-RPC request to LSP server"""
    content = json.dumps(request)
    message = f"Content-Length: {len(content)}\r\n\r\n{content}"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

def read_response(proc, expected_id=None):
    """Read a JSON-RPC response from LSP server"""
    while True:
        # Read headers
        headers = {}
        while True:
            line = proc.stdout.readline().decode().strip()
            if not line:
                break
            if ": " not in line:
                continue
            key, value = line.split(": ", 1)
            headers[key] = value
        
        # Read content
        content_length = int(headers.get("Content-Length", 0))
        if content_length == 0:
            return None
        content = proc.stdout.read(content_length).decode()
        response = json.loads(content)
        
        # Skip notifications (no id field) unless we're not looking for a specific ID
        if expected_id is not None and "id" not in response:
            continue
        
        # If we're looking for a specific ID and this doesn't match, keep reading
        if expected_id is not None and "id" in response:
            if response["id"] == expected_id:
                return response
            # Otherwise, skip this response and keep reading
        else:
            return response

def test_variable_goto():
    """Test goto definition for cross-file variables"""
    print("="*60)
    print("Testing Cross-File Variable Goto Definition")
    print("="*60)
    
    # Create test files
    globals_path, main_path = create_test_files()
    print(f"Created test files:")
    print(f"  globals.jazz: {globals_path}")
    print(f"  main.jazz: {main_path}")
    
    globals_uri = f"file://{globals_path}"
    main_uri = f"file://{main_path}"
    
    # Start LSP server
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
                "rootUri": f"file://{os.path.abspath('test/fixtures/variables')}",
                "capabilities": {}
            }
        })
        response = read_response(proc)
        print(f"\n✓ Initialized LSP server")
        
        # Send initialized notification
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        })
        
        # Read any responses (might be config request)
        import time
        time.sleep(0.1)
        
        # Open globals.jazz
        with open(globals_path) as f:
            globals_content = f.read()
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": globals_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": globals_content
                }
            }
        })
        print(f"✓ Opened globals.jazz")
        
        # Open main.jazz
        with open(main_path) as f:
            main_content = f.read()
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": main_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": main_content
                }
            }
        })
        print(f"✓ Opened main.jazz")
        
        # Test 1: Goto definition for BUFFER_SIZE (parameter)
        print("\n" + "="*60)
        print("Test 1: Parameter Reference (BUFFER_SIZE)")
        print("="*60)
        
        # Find line with "size = BUFFER_SIZE;"
        main_lines = main_content.split('\n')
        buffer_size_line = None
        for i, line in enumerate(main_lines):
            if 'BUFFER_SIZE' in line and '=' in line:
                buffer_size_line = i
                print(f"Found BUFFER_SIZE at line {i}: {line.strip()}")
                break
        
        if buffer_size_line is not None:
            # Position on BUFFER_SIZE (after the =)
            char_pos = main_lines[buffer_size_line].index('BUFFER_SIZE')
            
            send_request(proc, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/definition",
                "params": {
                    "textDocument": {"uri": main_uri},
                    "position": {"line": buffer_size_line, "character": char_pos + 5}
                }
            })
            
            response = read_response(proc, expected_id=2)
            print(f"\nResponse: {json.dumps(response, indent=2)}")
            
            if "result" in response and response["result"]:
                locations = response["result"]
                if isinstance(locations, list) and len(locations) > 0:
                    loc = locations[0]
                elif isinstance(locations, dict):
                    loc = locations
                else:
                    print("❌ FAILED: No location in response")
                    return False
                
                target_uri = loc.get("uri", "")
                if "globals.jazz" in target_uri:
                    print(f"✅ PASS: Points to globals.jazz")
                    print(f"   URI: {target_uri}")
                    print(f"   Range: {loc.get('range')}")
                else:
                    print(f"❌ FAIL: Should point to globals.jazz, got {target_uri}")
                    return False
            else:
                print(f"❌ FAILED: No definition found for BUFFER_SIZE")
                return False
        
        # Test 2: Goto definition for shared_data (global array)
        print("\n" + "="*60)
        print("Test 2: Global Array Reference (shared_data)")
        print("="*60)
        
        shared_data_line = None
        for i, line in enumerate(main_lines):
            if 'shared_data' in line:
                shared_data_line = i
                print(f"Found shared_data at line {i}: {line.strip()}")
                break
        
        if shared_data_line is not None:
            char_pos = main_lines[shared_data_line].index('shared_data')
            
            send_request(proc, {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "textDocument/definition",
                "params": {
                    "textDocument": {"uri": main_uri},
                    "position": {"line": shared_data_line, "character": char_pos + 5}
                }
            })
            
            response = read_response(proc, expected_id=3)
            print(f"\nResponse: {json.dumps(response, indent=2)}")
            
            if "result" in response and response["result"]:
                locations = response["result"]
                if isinstance(locations, list) and len(locations) > 0:
                    loc = locations[0]
                elif isinstance(locations, dict):
                    loc = locations
                else:
                    print("❌ FAILED: No location in response")
                    return False
                
                target_uri = loc.get("uri", "")
                if "globals.jazz" in target_uri:
                    print(f"✅ PASS: Points to globals.jazz")
                    print(f"   URI: {target_uri}")
                    print(f"   Range: {loc.get('range')}")
                else:
                    print(f"❌ FAIL: Should point to globals.jazz, got {target_uri}")
                    return False
            else:
                print(f"❌ FAILED: No definition found for shared_data")
                return False
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        return True
        
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    success = test_variable_goto()
    sys.exit(0 if success else 1)
