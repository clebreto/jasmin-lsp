#!/usr/bin/env python3
"""
Test transitive dependency resolution.
This tests that symbols defined in transitively required files can be found.

File structure:
- base.jinc: defines BASE_CONSTANT
- middle.jinc: requires base.jinc, defines MIDDLE_CONSTANT
- top.jazz: requires middle.jinc, uses BASE_CONSTANT (from base.jinc)

The test verifies that when in top.jazz, hovering/goto on BASE_CONSTANT works
even though base.jinc is not directly required by top.jazz.
"""

import json
import subprocess
import sys
import os
import time

def send_message(proc, message):
    """Send a JSON-RPC message to the LSP server."""
    content = json.dumps(message)
    header = f"Content-Length: {len(content)}\r\n\r\n"
    proc.stdin.write(header + content)
    proc.stdin.flush()

def read_message(proc):
    """Read a JSON-RPC message from the LSP server."""
    # Read header
    headers = {}
    while True:
        line = proc.stdout.readline()
        if not line or line == '\r\n':
            break
        key, value = line.strip().split(': ', 1)
        headers[key] = value
    
    # Read content
    content_length = int(headers.get('Content-Length', 0))
    if content_length == 0:
        return None
    
    content = proc.stdout.read(content_length)
    return json.loads(content)

def test_transitive_requires():
    """Test transitive dependency resolution."""
    print("Starting LSP server...")
    
    # Start the LSP server
    proc = subprocess.Popen(
        ['./_build/default/jasmin-lsp/jasmin_lsp.exe'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    try:
        # Initialize
        print("Sending initialize request...")
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": f"file://{os.getcwd()}",
                "capabilities": {}
            }
        })
        
        # Read initialize response
        response = read_message(proc)
        print(f"Initialize response: {json.dumps(response, indent=2)}")
        
        # Send initialized notification
        send_message(proc, {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        })
        
        # Open top.jazz (which requires middle.jinc, which requires base.jinc)
        top_path = os.path.abspath("test/fixtures/transitive/top.jazz")
        top_uri = f"file://{top_path}"
        
        with open(top_path, 'r') as f:
            top_content = f.read()
        
        print(f"\nOpening {top_path}...")
        send_message(proc, {
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
        
        time.sleep(0.5)  # Give server time to process
        
        # Test 1: Hover on BASE_CONSTANT in top.jazz (line 7, column 20)
        # Line: "  result = result + BASE_CONSTANT;"
        print("\n=== Test 1: Hover on BASE_CONSTANT (transitively required) ===")
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": top_uri},
                "position": {"line": 7, "character": 20}
            }
        })
        
        response = read_message(proc)
        print(f"Hover response: {json.dumps(response, indent=2)}")
        
        # Check if we got hover info
        if response and 'result' in response and response['result']:
            print("✅ SUCCESS: Found hover info for BASE_CONSTANT")
        else:
            print("❌ FAILED: No hover info for BASE_CONSTANT (transitive dependency not resolved)")
            return False
        
        # Test 2: Go to definition for BASE_CONSTANT
        print("\n=== Test 2: Go to definition for BASE_CONSTANT ===")
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "textDocument/definition",
            "params": {
                "textDocument": {"uri": top_uri},
                "position": {"line": 7, "character": 20}
            }
        })
        
        response = read_message(proc)
        print(f"Definition response: {json.dumps(response, indent=2)}")
        
        # Check if we got a definition location
        if response and 'result' in response and response['result']:
            result = response['result']
            if isinstance(result, list) and len(result) > 0:
                location = result[0]
                if 'base.jinc' in location['uri']:
                    print("✅ SUCCESS: Found definition in base.jinc")
                else:
                    print(f"❌ FAILED: Definition not in base.jinc: {location['uri']}")
                    return False
            else:
                print("❌ FAILED: Empty definition result")
                return False
        else:
            print("❌ FAILED: No definition found (transitive dependency not resolved)")
            return False
        
        # Test 3: Hover on MIDDLE_CONSTANT (directly required)
        # Line: "  result = middle_function(z);"
        print("\n=== Test 3: Hover on middle_function (directly required) ===")
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": top_uri},
                "position": {"line": 5, "character": 13}
            }
        })
        
        response = read_message(proc)
        print(f"Hover response: {json.dumps(response, indent=2)}")
        
        if response and 'result' in response and response['result']:
            print("✅ SUCCESS: Found hover info for middle_function")
        else:
            print("⚠️  WARNING: No hover info for middle_function")
        
        # Shutdown
        print("\n=== Shutting down ===")
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "shutdown",
            "params": {}
        })
        
        response = read_message(proc)
        print(f"Shutdown response: {json.dumps(response, indent=2)}")
        
        send_message(proc, {
            "jsonrpc": "2.0",
            "method": "exit",
            "params": {}
        })
        
        print("\n✅ All transitive dependency tests passed!")
        return True
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)

if __name__ == '__main__':
    success = test_transitive_requires()
    sys.exit(0 if success else 1)
