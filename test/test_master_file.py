#!/usr/bin/env python3
"""
Test script to verify master file feature works correctly
"""

import json
import subprocess
import sys
import time
from pathlib import Path

def send_message(proc, message):
    """Send a JSON-RPC message to the LSP server"""
    content = json.dumps(message)
    header = f"Content-Length: {len(content)}\r\n\r\n"
    proc.stdin.write(header + content)
    proc.stdin.flush()

def read_message(proc):
    """Read a JSON-RPC message from the LSP server"""
    # Read headers
    headers = {}
    while True:
        line = proc.stdout.readline().strip()
        if not line:
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    # Read content
    content_length = int(headers.get('Content-Length', 0))
    content = proc.stdout.read(content_length)
    return json.loads(content)

def test_master_file():
    """Test setting master file via custom notification"""
    
    # Start LSP server
    lsp_exe = Path("_build/default/jasmin-lsp/jasmin_lsp.exe")
    if not lsp_exe.exists():
        print(f"ERROR: LSP executable not found at {lsp_exe}")
        return False
    
    proc = subprocess.Popen(
        [str(lsp_exe)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    try:
        # 1. Send initialize request
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": "file:///test",
                "capabilities": {}
            }
        }
        send_message(proc, initialize_request)
        
        # Read initialize response
        response = read_message(proc)
        print(f"Initialize response: {json.dumps(response, indent=2)}")
        
        # 2. Send initialized notification
        initialized_notif = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        send_message(proc, initialized_notif)
        
        # 3. Send custom jasmin/setMasterFile notification
        set_master_file = {
            "jsonrpc": "2.0",
            "method": "jasmin/setMasterFile",
            "params": {
                "uri": "file:///test/main.jazz"
            }
        }
        send_message(proc, set_master_file)
        
        # Give server time to process
        time.sleep(0.5)
        
        # 4. Check stderr logs for confirmation
        stderr_output = proc.stderr.read()
        if "Master file set to: file:///test/main.jazz" in stderr_output:
            print("✓ Master file successfully set")
            return True
        else:
            print("✗ Master file not set in logs")
            print(f"Stderr: {stderr_output}")
            return False
            
    finally:
        proc.terminate()
        proc.wait(timeout=1)

if __name__ == "__main__":
    print("Testing master file feature...")
    success = test_master_file()
    sys.exit(0 if success else 1)
