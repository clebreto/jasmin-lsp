#!/usr/bin/env python3
"""Quick test to verify the new expandable hover format for constants."""

import subprocess
import json
import os
import time
from pathlib import Path

def send_message(proc, msg):
    """Send a JSON-RPC message to the LSP server."""
    content = json.dumps(msg)
    message = f"Content-Length: {len(content)}\r\n\r\n{content}"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

def read_message(proc):
    """Read a JSON-RPC message from the LSP server."""
    # Read headers
    headers = {}
    while True:
        line = proc.stdout.readline().decode('utf-8').strip()
        if not line:
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    # Read content
    content_length = int(headers.get('Content-Length', 0))
    if content_length == 0:
        return None
    
    content = proc.stdout.read(content_length).decode('utf-8')
    return json.loads(content)

def read_until_response(proc, request_id):
    """Read messages until we get the response with the matching ID."""
    while True:
        msg = read_message(proc)
        if msg is None:
            return None
        if 'id' in msg and msg['id'] == request_id:
            return msg

def main():
    """Test hover on various constants."""
    server_path = "./_build/default/jasmin-lsp/jasmin_lsp.exe"
    
    # Use existing test file
    test_file_path = str(Path(__file__).parent / "test/fixtures/constant_computation/constants.jinc")
    
    if not os.path.exists(test_file_path):
        print(f"❌ Test file not found: {test_file_path}")
        return False
    
    # Read content
    with open(test_file_path, 'r') as f:
        content = f.read()
    
    print("Testing Hover with Expandable Value Sections")
    print("=" * 60)
    
    # Start LSP server
    proc = subprocess.Popen(
        [server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Initialize
        init_msg = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": f"file://{Path.cwd()}",
                "capabilities": {}
            }
        }
        send_message(proc, init_msg)
        init_response = read_until_response(proc, 0)
        
        if not init_response or 'result' not in init_response:
            print("❌ Failed to initialize LSP server")
            return False
        
        print("✓ LSP server initialized")
        
        # Notify initialized
        send_message(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        time.sleep(0.1)
        
        # Open document
        send_message(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{test_file_path}",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": content
                }
            }
        })
        time.sleep(0.2)
        
        # Test cases: (name, line, char, description)
        # Line numbers: 0=comment, 1=BASE, 2=OFFSET, 3=TOTAL, 4=DOUBLED, 5=SHIFTED
        tests = [
            ("BASE", 1, 11, "Simple constant (100)"),
            ("OFFSET", 2, 11, "Simple constant (50)"),
            ("TOTAL", 3, 11, "Computed constant (BASE + OFFSET = 150)"),
            ("DOUBLED", 4, 11, "Computed constant (TOTAL * 2 = 300)"),
            ("SHIFTED", 5, 11, "Bit shift constant (1 << 10 = 1024)"),
        ]
        
        print("\nTesting hover responses:")
        print("-" * 60)
        
        all_passed = True
        for name, line, char, description in tests:
            hover_msg = {
                "jsonrpc": "2.0",
                "id": line + 10,
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": f"file://{test_file_path}"},
                    "position": {"line": line, "character": char}
                }
            }
            send_message(proc, hover_msg)
            hover_response = read_until_response(proc, line + 10)
            
            if not hover_response or 'result' not in hover_response:
                print(f"❌ {name:15} - No hover response")
                all_passed = False
                continue
            
            result = hover_response['result']
            if not result:
                print(f"❌ {name:15} - Null result")
                all_passed = False
                continue
            
            hover_content = result.get("contents", {})
            if isinstance(hover_content, dict):
                value = hover_content.get("value", "")
            else:
                value = str(hover_content)
            
            # Check for expandable section
            has_details = "<details>" in value and "<summary>Value</summary>" in value
            has_name = name in value
            
            print(f"\n{name:15} ({description})")
            print(f"  Has expandable section: {'✓' if has_details else '✗'}")
            print(f"  Contains name: {'✓' if has_name else '✗'}")
            
            if has_details and has_name:
                print(f"  ✅ PASS")
                # Show a snippet of the hover
                lines = value.split('\n')
                print(f"  Preview: {lines[0] if lines else 'N/A'}")
            else:
                print(f"  ❌ FAIL")
                print(f"  Full content:\n{value}")
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        print("=" * 60)
        
        return all_passed
        
    finally:
        try:
            send_message(proc, {"jsonrpc": "2.0", "id": 999, "method": "shutdown"})
            time.sleep(0.1)
            send_message(proc, {"jsonrpc": "2.0", "method": "exit"})
        except:
            pass
        proc.terminate()

if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
