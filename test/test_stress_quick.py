#!/usr/bin/env python3
"""
Quick stress test for jasmin-lsp server.
"""

import subprocess
import json
import time
import os
import sys

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def test_stress():
    """Test with 20 documents changing rapidly"""
    print("\nSTRESS TEST: 20 documents with rapid changes")
    
    proc = subprocess.Popen(
        [SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )
    
    def send(msg):
        msg_str = json.dumps(msg)
        content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
        proc.stdin.write(content.encode('utf-8'))
        proc.stdin.flush()
    
    try:
        # Initialize
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", 
              "params": {"processId": os.getpid(), "rootUri": f"file://{os.getcwd()}", "capabilities": {}}})
        time.sleep(0.3)
        send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        time.sleep(0.3)
        
        # Create 20 documents with changes
        for i in range(20):
            uri = f"file:///tmp/stress{i}.jazz"
            
            # Open
            send({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
                "textDocument": {"uri": uri, "languageId": "jasmin", "version": 1, "text": f"fn func{i}() {{ }}"}
            }})
            
            # Changes
            for v in range(2, 5):
                send({"jsonrpc": "2.0", "method": "textDocument/didChange", "params": {
                    "textDocument": {"uri": uri, "version": v},
                    "contentChanges": [{"text": f"fn func{i}_v{v}() {{ }}"}]
                }})
            
            # Close
            send({"jsonrpc": "2.0", "method": "textDocument/didClose", "params": {
                "textDocument": {"uri": uri}
            }})
            
            time.sleep(0.05)
            if proc.poll() is not None:
                print(f"✗ CRASH at document {i}!")
                return False
        
        time.sleep(0.5)
        if proc.poll() is None:
            print("✓ PASSED: Server handled 20 documents with 80 operations!")
            proc.terminate()
            return True
        else:
            print("✗ FAILED: Server crashed")
            return False
            
    finally:
        try:
            proc.kill()
        except:
            pass

if __name__ == "__main__":
    success = test_stress()
    sys.exit(0 if success else 1)
