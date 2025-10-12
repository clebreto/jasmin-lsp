#!/usr/bin/env python3
"""Test that hovering over constants shows their values."""

import subprocess
import json
import os
import sys
import time

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

def read_until_response(proc, request_id):
    """Read messages until we get the response with the matching ID."""
    while True:
        msg = read_message(proc)
        if msg.get("id") == request_id:
            return msg
        # Skip notifications and other messages
        print(f"Skipping message: {msg.get('method', 'response')}")


def test_constant_hover():
    """Test hovering over a constant to see its value."""
    
    # Start LSP server
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
                "rootUri": f"file://{os.path.dirname(__file__)}/test/fixtures",
                "capabilities": {}
            }
        }
        send_message(proc, init_msg)
        response = read_until_response(proc, 1)
        print(f"Initialize response: {json.dumps(response, indent=2)}")
        
        # Send initialized notification
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        send_message(proc, initialized_msg)
        time.sleep(0.2)
        
        # Open a test file with a param constant
        test_file_path = os.path.join(os.path.dirname(__file__), 
                                     "test/fixtures/transitive/base.jinc")
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
        time.sleep(0.5)  # Give server time to process
        
        # Hover over BASE_CONSTANT (line 1, column 10 is in "BASE_CONSTANT")
        # param int BASE_CONSTANT = 42;
        #           ^
        hover_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": f"file://{test_file_path}"},
                "position": {"line": 1, "character": 15}
            }
        }
        send_message(proc, hover_msg)
        hover_response = read_until_response(proc, 2)
        
        print(f"\nHover response: {json.dumps(hover_response, indent=2)}")
        
        # Check if the hover contains the value "42"
        if "result" in hover_response and hover_response["result"]:
            hover_content = hover_response["result"].get("contents", {})
            if isinstance(hover_content, dict):
                value = hover_content.get("value", "")
                print(f"\nHover content:\n{value}")
                
                # Verify it contains the value 42
                if "42" in value and "BASE_CONSTANT" in value:
                    print("\n✅ SUCCESS: Constant value is displayed in hover!")
                    return True
                else:
                    print(f"\n❌ FAILED: Expected to see '42' and 'BASE_CONSTANT' in hover")
                    return False
            else:
                print(f"\n❌ FAILED: Unexpected hover content format")
                return False
        else:
            print(f"\n❌ FAILED: No hover result returned")
            return False
            
    finally:
        # Shutdown
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
    success = test_constant_hover()
    sys.exit(0 if success else 1)
