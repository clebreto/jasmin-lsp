#!/usr/bin/env python3
"""
Intensive test that runs for longer to reproduce VSCode crashes.
"""

import subprocess
import json
import time
import os
import sys

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def intensive_test():
    """Run intensive editing for 2 minutes"""
    print("Running intensive 2-minute test...")
    
    proc = subprocess.Popen(
        [SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )
    
    msg_id = 0
    
    def send(method, params=None, is_notification=False):
        nonlocal msg_id
        msg = {"jsonrpc": "2.0", "method": method}
        
        if not is_notification:
            msg_id += 1
            msg["id"] = msg_id
        
        if params:
            msg["params"] = params
        
        msg_str = json.dumps(msg)
        content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
        
        try:
            proc.stdin.write(content.encode('utf-8'))
            proc.stdin.flush()
            return True
        except:
            return False
    
    try:
        # Initialize
        send("initialize", {"processId": os.getpid(), "rootUri": f"file://{os.getcwd()}", "capabilities": {}})
        time.sleep(0.3)
        send("initialized", {}, is_notification=True)
        time.sleep(0.3)
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < 120:  # 2 minutes
            if proc.poll() is not None:
                elapsed = time.time() - start_time
                print(f"✗ CRASH after {elapsed:.1f} seconds, iteration {iteration}!")
                stderr = proc.stderr.read().decode('utf-8', errors='replace')
                print("=== STDERR (last 4000 chars) ===")
                print(stderr[-4000:])
                return False
            
            uri = f"file:///tmp/intensive_{iteration % 5}.jazz"
            
            # Open
            send("textDocument/didOpen", {
                "textDocument": {
                    "uri": uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": f"fn func{iteration}() {{ }}"
                }
            }, is_notification=True)
            
            time.sleep(0.05)
            
            # Changes
            for v in range(2, 6):
                if not send("textDocument/didChange", {
                    "textDocument": {"uri": uri, "version": v},
                    "contentChanges": [{"text": f"fn func{iteration}_v{v}() {{ }}"}]
                }, is_notification=True):
                    print(f"✗ Failed to send at iteration {iteration}")
                    return False
                
                time.sleep(0.02)
            
            # Hover
            send("textDocument/hover", {
                "textDocument": {"uri": uri},
                "position": {"line": 0, "character": 3}
            })
            
            time.sleep(0.05)
            
            # Close
            send("textDocument/didClose", {"textDocument": {"uri": uri}}, is_notification=True)
            
            iteration += 1
            
            if iteration % 10 == 0:
                elapsed = time.time() - start_time
                print(f"  {iteration} iterations, {elapsed:.1f}s elapsed...")
        
        print(f"✓ Completed {iteration} iterations over 2 minutes without crashing!")
        proc.terminate()
        return True
        
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        try:
            proc.kill()
        except:
            pass

if __name__ == "__main__":
    success = intensive_test()
    sys.exit(0 if success else 1)
