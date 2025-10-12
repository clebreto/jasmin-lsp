#!/usr/bin/env python3
"""
Debug script for rapid document changes crash.
"""

import subprocess
import json
import time
import os
import sys

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def send_message(proc, method, params=None, is_notification=False, msg_id=None):
    """Send a JSON-RPC message to the server"""
    msg = {
        "jsonrpc": "2.0",
        "method": method
    }
    
    if not is_notification and msg_id is not None:
        msg["id"] = msg_id
        
    if params is not None:
        msg["params"] = params
    
    msg_str = json.dumps(msg)
    content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
    
    print(f">>> {method} (id={msg_id}, notif={is_notification})")
    
    try:
        proc.stdin.write(content.encode('utf-8'))
        proc.stdin.flush()
        return True
    except Exception as e:
        print(f"!!! Failed to send: {e}")
        return False

def main():
    proc = subprocess.Popen(
        [SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )
    
    msg_id = 0
    
    try:
        # Initialize
        msg_id += 1
        send_message(proc, "initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        }, msg_id=msg_id)
        
        time.sleep(0.5)
        if proc.poll() is not None:
            print("CRASH: Server died during init!")
            print(proc.stderr.read().decode('utf-8'))
            return 1
        
        send_message(proc, "initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        if proc.poll() is not None:
            print("CRASH: Server died after initialized!")
            print(proc.stderr.read().decode('utf-8'))
            return 1
        
        print("\nStarting rapid document changes test...")
        
        # Test rapid changes
        for i in range(5):  # Reduced from 10
            uri = f"file:///tmp/test{i}.jazz"
            print(f"\n--- Document {i}: {uri} ---")
            
            # Open
            print(f"  Opening...")
            send_message(proc, "textDocument/didOpen", {
                "textDocument": {
                    "uri": uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": "fn test() { }"
                }
            }, is_notification=True)
            
            time.sleep(0.1)
            if proc.poll() is not None:
                print(f"CRASH: Server died after opening document {i}!")
                stderr = proc.stderr.read().decode('utf-8')
                print("=== STDERR ===")
                print(stderr[-5000:])
                return 1
            
            # Change multiple times
            for v in range(2, 6):  # versions 2-5
                print(f"  Changing to version {v}...")
                send_message(proc, "textDocument/didChange", {
                    "textDocument": {"uri": uri, "version": v},
                    "contentChanges": [{"text": f"fn test{v}() {{ }}"}]
                }, is_notification=True)
                
                time.sleep(0.05)
                if proc.poll() is not None:
                    print(f"CRASH: Server died during change v{v} of document {i}!")
                    stderr = proc.stderr.read().decode('utf-8')
                    print("=== STDERR ===")
                    print(stderr[-5000:])
                    return 1
            
            # Close
            print(f"  Closing...")
            send_message(proc, "textDocument/didClose", {
                "textDocument": {"uri": uri}
            }, is_notification=True)
            
            time.sleep(0.1)
            if proc.poll() is not None:
                print(f"CRASH: Server died after closing document {i}!")
                stderr = proc.stderr.read().decode('utf-8')
                print("=== STDERR ===")
                print(stderr[-5000:])
                return 1
        
        print("\n✓ All rapid changes completed successfully!")
        proc.terminate()
        proc.wait(timeout=1)
        
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        
        if proc.poll() is None:
            proc.kill()
        
        stderr = proc.stderr.read().decode('utf-8')
        print("=== STDERR ===")
        print(stderr[-5000:])
        return 1
    finally:
        try:
            proc.kill()
        except:
            pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
