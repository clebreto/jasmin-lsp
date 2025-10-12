#!/usr/bin/env python3
"""Test that constants built from other constants show computed values."""

import subprocess
import json
import os
import sys
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
        # Skip notifications and other messages

def test_constant_computation():
    """Test that constants built from other constants show computed values."""
    server_path = "./_build/default/jasmin-lsp/jasmin_lsp.exe"
    
    # Get absolute path to test file
    test_file = Path(__file__).parent / "test/fixtures/constant_computation/constants.jinc"
    test_file_path = str(test_file.absolute())
    
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file_path}")
        return False
    
    # Read test file content
    with open(test_file_path, 'r') as f:
        content = f.read()
    
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
            print("Failed to initialize LSP server")
            return False
        
        print("✓ Initialized LSP server")
        
        # Notify initialized
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        send_message(proc, initialized_msg)
        time.sleep(0.1)
        
        # Open document
        open_msg = {
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
        send_message(proc, open_msg)
        time.sleep(0.2)
        
        print("✓ Opened document")
        
        # Test cases: (line, column, constant_name, expected_value)
        # Lines are 0-indexed, columns should point to start of constant name
        test_cases = [
            (3, 11, "TOTAL", "150"),  # BASE + OFFSET = 100 + 50
            (4, 11, "DOUBLED", "300"),  # TOTAL * 2 = 150 * 2
            (5, 11, "SHIFTED", "1024"),  # 1 << 10
            (8, 11, "SIGNATURE_SIZE", "350"),  # 200 + 150
        ]
        
        all_passed = True
        
        for line, char, name, expected_val in test_cases:
            print(f"\n=== Testing {name} (expected value: {expected_val}) ===")
            
            hover_msg = {
                "jsonrpc": "2.0",
                "id": line + 10,  # Use line as part of ID to make unique
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": f"file://{test_file_path}"},
                    "position": {"line": line, "character": char}
                }
            }
            send_message(proc, hover_msg)
            hover_response = read_until_response(proc, line + 10)
            
            if not hover_response or 'result' not in hover_response:
                print(f"❌ FAILED: No hover response for {name}")
                all_passed = False
                continue
            
            result = hover_response['result']
            if not result:
                print(f"❌ FAILED: Null hover result for {name}")
                all_passed = False
                continue
            
            hover_content = result.get("contents", {})
            if isinstance(hover_content, dict):
                value = hover_content.get("value", "")
            elif isinstance(hover_content, str):
                value = hover_content
            else:
                print(f"❌ FAILED: Unexpected hover content format for {name}")
                all_passed = False
                continue
            
            print(f"Hover content:\n{value}")
            
            # Check if the computed value appears in the hover
            if expected_val in value and name in value:
                print(f"✅ SUCCESS: {name} shows computed value {expected_val}")
            else:
                print(f"❌ FAILED: Expected to see '{expected_val}' in hover for {name}")
                all_passed = False
        
        return all_passed
        
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
    success = test_constant_computation()
    sys.exit(0 if success else 1)
