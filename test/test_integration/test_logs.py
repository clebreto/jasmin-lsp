#!/usr/bin/env python3
"""Simple test to capture stderr from LSP server."""

import subprocess
import json
import time
from pathlib import Path

def send_message(proc, msg):
    """Send a JSON-RPC message to the LSP server."""
    content = json.dumps(msg)
    message = f"Content-Length: {len(content)}\r\n\r\n{content}"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

def test_with_logs():
    """Test and capture all logs."""
    server_path = "./_build/default/jasmin-lsp/jasmin_lsp.exe"
    
    # Get the correct path to fixtures directory (go up two levels from test/test_integration/)
    test_file = Path(__file__).parent.parent / "fixtures/constant_computation/constants.jinc"
    test_file_path = str(test_file.absolute())
    
    with open(test_file_path, 'r') as f:
        content = f.read()
    
    # Start LSP server - don't use PIPE for stderr, let it go to console
    proc = subprocess.Popen(
        [server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None  # Let stderr go directly to console
    )
    
    try:
        print("Sending initialize...")
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
        time.sleep(0.5)
        
        print("Sending initialized...")
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        send_message(proc, initialized_msg)
        time.sleep(0.2)
        
        print("Sending didOpen...")
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
        time.sleep(0.3)
        
        print("Sending hover request for TOTAL...")
        hover_msg = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": f"file://{test_file_path}"},
                "position": {"line": 3, "character": 11}
            }
        }
        send_message(proc, hover_msg)
        time.sleep(1.0)
        
        print("\nTest complete. Check logs above.")
        
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
    test_with_logs()
