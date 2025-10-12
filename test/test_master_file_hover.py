#!/usr/bin/env python3
"""
Test cross-file hover with master file support using existing test fixtures.

This test verifies that:
1. Master file can be set via jasmin/setMasterFile notification
2. Hover on variables/functions defined in required files works
3. Complete dependency tree is built from master file
"""

import json
import subprocess
import os
import sys
from pathlib import Path

# Path to the LSP server executable
LSP_SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def send_request(proc, request):
    """Send a request to the LSP server."""
    request_str = json.dumps(request)
    content_length = len(request_str.encode('utf-8'))
    
    message = f"Content-Length: {content_length}\r\n\r\n{request_str}"
    proc.stdin.write(message.encode('utf-8'))
    proc.stdin.flush()

def read_response(proc):
    """Read a response from the LSP server."""
    # Read headers
    headers = {}
    while True:
        line = proc.stdout.readline().decode('utf-8')
        if line == '\r\n':
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    # Read content
    content_length = int(headers.get('Content-Length', 0))
    content = proc.stdout.read(content_length).decode('utf-8')
    return json.loads(content)

def test_master_file_hover():
    """Test hover on variables defined in required files using existing fixtures."""
    print("=" * 80)
    print("Testing Cross-File Hover with Master File")
    print("=" * 80)
    
    test_dir = Path("test/fixtures/transitive")
    if not test_dir.exists():
        print(f"Error: Test directory {test_dir} not found")
        return False
    
    print(f"\n✓ Using test files in {test_dir}")
    
    # Start LSP server
    proc = subprocess.Popen(
        [LSP_SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )
    
    success = True
    
    try:
        # Initialize
        print("\n1. Initializing LSP server...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": f"file://{os.getcwd()}/{test_dir}",
                "capabilities": {
                    "textDocument": {
                        "hover": {
                            "contentFormat": ["markdown", "plaintext"]
                        }
                    }
                }
            }
        })
        
        response = read_response(proc)
        if 'result' in response:
            print(f"   ✓ Server initialized")
        else:
            print(f"   ✗ Initialization failed")
            success = False
        
        # Send initialized notification
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        })
        
        # Open top.jazz (master file)
        print("\n2. Opening top.jazz (master file)...")
        top_path = test_dir / "top.jazz"
        top_uri = f"file://{top_path.absolute()}"
        top_content = top_path.read_text()
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": top_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": top_content
                }
            }
        })
        
        # Read diagnostics
        response = read_response(proc)
        print(f"   ✓ Opened top.jazz")
        
        # Set master file
        print(f"\n3. Setting master file to: top.jazz")
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "jasmin/setMasterFile",
            "params": {
                "uri": top_uri
            }
        })
        
        # Give server time to process
        import time
        time.sleep(0.5)
        
        # Test 1: Hover on 'middle_function' (defined in middle.jinc)
        print("\n4. Testing hover on 'middle_function' (defined in middle.jinc)...")
        # In top.jazz, middle_function is called on line 8
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": top_uri},
                "position": {"line": 7, "character": 12}  # Position of 'middle_function'
            }
        })
        
        response = read_response(proc)
        if response.get('result') and response['result'].get('contents'):
            contents = response['result']['contents']
            if isinstance(contents, dict) and 'value' in contents:
                hover_text = contents['value']
                print(f"   ✓ Hover on 'middle_function': {hover_text}")
                if 'middle_function' in hover_text:
                    print(f"   ✓ Found function definition")
                else:
                    print(f"   ⚠ Unexpected hover content")
            else:
                print(f"   ✗ Unexpected content format: {contents}")
                success = False
        else:
            print(f"   ✗ No hover information for 'middle_function'")
            print(f"   Response: {response}")
            success = False
        
        # Test 2: Hover on 'BASE_CONSTANT' (defined in base.jinc, transitively required)
        print("\n5. Testing hover on 'BASE_CONSTANT' (defined in base.jinc)...")
        # BASE_CONSTANT is referenced on line 9
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": top_uri},
                "position": {"line": 8, "character": 22}  # Position of 'BASE_CONSTANT'
            }
        })
        
        response = read_response(proc)
        if response.get('result') and response['result'].get('contents'):
            contents = response['result']['contents']
            if isinstance(contents, dict) and 'value' in contents:
                hover_text = contents['value']
                print(f"   ✓ Hover on 'BASE_CONSTANT': {hover_text}")
                
                # Verify constant value is shown
                if "= 42" in hover_text or "42" in hover_text:
                    print(f"   ✓✓ Constant value computed correctly (from transitively required file)!")
                else:
                    print(f"   ⚠ Constant value not shown")
            else:
                print(f"   ✗ Unexpected content format: {contents}")
                success = False
        else:
            print(f"   ✗ No hover information for 'BASE_CONSTANT'")
            print(f"   Response: {response}")
            success = False
        
        # Open middle.jinc
        print("\n6. Opening middle.jinc...")
        middle_path = test_dir / "middle.jinc"
        middle_uri = f"file://{middle_path.absolute()}"
        middle_content = middle_path.read_text()
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": middle_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": middle_content
                }
            }
        })
        
        # Read diagnostics
        response = read_response(proc)
        print(f"   ✓ Opened middle.jinc")
        
        time.sleep(0.3)
        
        # Test 3: Hover on 'base_function' in middle.jinc (defined in base.jinc)
        print("\n7. Testing hover on 'base_function' in middle.jinc...")
        # base_function is called on line 7 in middle.jinc
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": middle_uri},
                "position": {"line": 6, "character": 12}  # Position of 'base_function'
            }
        })
        
        response = read_response(proc)
        if response.get('result') and response['result'].get('contents'):
            contents = response['result']['contents']
            if isinstance(contents, dict) and 'value' in contents:
                hover_text = contents['value']
                print(f"   ✓ Hover on 'base_function': {hover_text}")
                if 'base_function' in hover_text:
                    print(f"   ✓ Found function definition from base.jinc")
                else:
                    print(f"   ⚠ Unexpected hover content")
            else:
                print(f"   ✗ Unexpected content format: {contents}")
                success = False
        else:
            print(f"   ✗ No hover information for 'base_function'")
            print(f"   Response: {response}")
            success = False
        
        # Test 4: Hover on local variable 'result' in middle.jinc
        print("\n8. Testing hover on local variable 'result' in middle.jinc...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": middle_uri},
                "position": {"line": 5, "character": 8}  # Position of 'result' declaration
            }
        })
        
        response = read_response(proc)
        if response.get('result') and response['result'].get('contents'):
            contents = response['result']['contents']
            if isinstance(contents, dict) and 'value' in contents:
                hover_text = contents['value']
                print(f"   ✓ Hover on 'result': {hover_text}")
                if 'u64' in hover_text or 'result' in hover_text:
                    print(f"   ✓ Variable type shown")
                else:
                    print(f"   ⚠ Type information missing")
            else:
                print(f"   ✗ Unexpected content format: {contents}")
                success = False
        else:
            print(f"   ✗ No hover information for 'result'")
            print(f"   Response: {response}")
            success = False
        
        print("\n" + "=" * 80)
        if success:
            print("✓✓✓ All tests PASSED! ✓✓✓")
        else:
            print("✗✗✗ Some tests FAILED ✗✗✗")
        print("=" * 80)
        
        # Shutdown
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 999,
            "method": "shutdown",
            "params": {}
        })
        
        read_response(proc)
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "exit",
            "params": {}
        })
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    
    return success

if __name__ == "__main__":
    success = test_master_file_hover()
    sys.exit(0 if success else 1)
