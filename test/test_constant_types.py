#!/usr/bin/env python3
"""Test hovering over different types of constants."""

import subprocess
import json
import os
import time

def send_message(proc, msg):
    """Send a JSON-RPC message to the LSP server."""
    content = json.dumps(msg)
    message = f"Content-Length: {len(content)}\r\n\r\n{content}"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

def read_message(proc):
    """Read a JSON-RPC message from the LSP server."""
    headers = {}
    while True:
        line = proc.stdout.readline().decode('utf-8')
        if line == '\r\n':
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    content_length = int(headers.get('Content-Length', 0))
    content = proc.stdout.read(content_length).decode('utf-8')
    return json.loads(content)

def read_until_response(proc, request_id):
    """Read messages until we get the response with the matching ID."""
    while True:
        msg = read_message(proc)
        if msg.get("id") == request_id:
            return msg

def test_constant_types():
    """Test hovering over various constant types."""
    
    lsp_path = os.path.join(os.path.dirname(__file__), 
                            "_build/default/jasmin-lsp/jasmin_lsp.exe")
    
    proc = subprocess.Popen(
        [lsp_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Initialize
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": f"file://{os.path.dirname(__file__)}",
                "capabilities": {}
            }
        }
        send_message(proc, init_msg)
        read_until_response(proc, 1)
        
        # Send initialized notification
        send_message(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        time.sleep(0.2)
        
        # Open test file
        test_file_path = os.path.join(os.path.dirname(__file__), "test_constants.jinc")
        with open(test_file_path, 'r') as f:
            content = f.read()
        
        didopen_msg = {
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
        }
        send_message(proc, didopen_msg)
        time.sleep(0.5)
        
        # Test cases: (line, character, expected_substring)
        test_cases = [
            (1, 10, "SIMPLE", "42"),
            (2, 10, "EXPRESSION", "(1 << 19) - 1"),
            (3, 10, "HEX_VALUE", "0x1000"),
            (4, 10, "LARGE", "18446744073709551615"),
        ]
        
        all_passed = True
        for i, (line, char, name, expected_value) in enumerate(test_cases):
            hover_msg = {
                "jsonrpc": "2.0",
                "id": i + 2,
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": f"file://{test_file_path}"},
                    "position": {"line": line, "character": char}
                }
            }
            send_message(proc, hover_msg)
            hover_response = read_until_response(proc, i + 2)
            
            if "result" in hover_response and hover_response["result"]:
                hover_content = hover_response["result"].get("contents", {})
                if isinstance(hover_content, dict):
                    value = hover_content.get("value", "")
                    print(f"\n{name}:")
                    print(f"  {value}")
                    
                    if expected_value in value and name in value:
                        print(f"  ✅ PASS")
                    else:
                        print(f"  ❌ FAIL: Expected '{expected_value}' in hover")
                        all_passed = False
                else:
                    print(f"\n{name}: ❌ FAIL: Unexpected format")
                    all_passed = False
            else:
                print(f"\n{name}: ❌ FAIL: No hover result")
                all_passed = False
        
        if all_passed:
            print("\n🎉 All tests passed!")
        else:
            print("\n⚠️  Some tests failed")
        
        return all_passed
            
    finally:
        try:
            shutdown_msg = {"jsonrpc": "2.0", "id": 999, "method": "shutdown"}
            send_message(proc, shutdown_msg)
            time.sleep(0.1)
            exit_msg = {"jsonrpc": "2.0", "method": "exit"}
            send_message(proc, exit_msg)
        except:
            pass
        
        proc.terminate()
        proc.wait(timeout=2)

if __name__ == "__main__":
    import sys
    success = test_constant_types()
    sys.exit(0 if success else 1)
