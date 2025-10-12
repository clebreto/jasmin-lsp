#!/usr/bin/env python3
"""
Test to reproduce the VSCode crash scenario.
Simulates what VSCode does with rapid edits.
"""

import subprocess
import json
import time
import os
import sys

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def test_vscode_editing():
    """Simulate realistic VSCode editing session"""
    print("Simulating VSCode editing session...")
    
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
        msg = {
            "jsonrpc": "2.0",
            "method": method
        }
        
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
        send("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {
                "textDocument": {
                    "synchronization": {
                        "didSave": True
                    }
                }
            }
        })
        
        time.sleep(0.5)
        
        if proc.poll() is not None:
            print("✗ CRASH during initialization!")
            stderr = proc.stderr.read().decode('utf-8', errors='replace')
            print(stderr[-2000:])
            return False
        
        send("initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        # Open a document
        uri = "file:///tmp/test_vscode.jazz"
        text = """fn test_function(x: u64) -> u64 {
    reg u64 y;
    y = x + 1;
    return y;
}"""
        
        send("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": "jasmin",
                "version": 1,
                "text": text
            }
        }, is_notification=True)
        
        time.sleep(0.5)
        
        if proc.poll() is not None:
            print("✗ CRASH after didOpen!")
            stderr = proc.stderr.read().decode('utf-8', errors='replace')
            print(stderr[-2000:])
            return False
        
        print("  Document opened successfully")
        
        # Simulate typing - rapid changes
        changes = [
            "fn test_function(x: u64) -> u64 {\n    reg u64 y;\n    y = x + 1;\n    return y;\n}\n",
            "fn test_function(x: u64) -> u64 {\n    reg u64 y;\n    y = x + 1;\n    return y;\n}\n\n",
            "fn test_function(x: u64) -> u64 {\n    reg u64 y;\n    y = x + 1;\n    return y;\n}\n\nfn ",
            "fn test_function(x: u64) -> u64 {\n    reg u64 y;\n    y = x + 1;\n    return y;\n}\n\nfn another",
            "fn test_function(x: u64) -> u64 {\n    reg u64 y;\n    y = x + 1;\n    return y;\n}\n\nfn another(",
        ]
        
        for i, new_text in enumerate(changes, start=2):
            print(f"  Change {i}...")
            send("textDocument/didChange", {
                "textDocument": {"uri": uri, "version": i},
                "contentChanges": [{"text": new_text}]
            }, is_notification=True)
            
            time.sleep(0.2)
            
            if proc.poll() is not None:
                print(f"✗ CRASH after change {i}!")
                stderr = proc.stderr.read().decode('utf-8', errors='replace')
                print("=== STDERR (last 3000 chars) ===")
                print(stderr[-3000:])
                return False
        
        print("  All changes completed successfully")
        
        # Request hover to trigger diagnostics
        for attempt in range(3):
            print(f"  Hover request {attempt + 1}...")
            send("textDocument/hover", {
                "textDocument": {"uri": uri},
                "position": {"line": 0, "character": 3}
            })
            
            time.sleep(0.3)
            
            if proc.poll() is not None:
                print(f"✗ CRASH after hover request {attempt + 1}!")
                stderr = proc.stderr.read().decode('utf-8', errors='replace')
                print("=== STDERR (last 3000 chars) ===")
                print(stderr[-3000:])
                return False
        
        print("  Hover requests completed successfully")
        
        # Close document
        send("textDocument/didClose", {
            "textDocument": {"uri": uri}
        }, is_notification=True)
        
        time.sleep(0.5)
        
        if proc.poll() is not None:
            print("✗ CRASH after didClose!")
            stderr = proc.stderr.read().decode('utf-8', errors='replace')
            print(stderr[-2000:])
            return False
        
        print("✓ VSCode simulation completed successfully!")
        
        proc.terminate()
        proc.wait(timeout=2)
        return True
        
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        
        if proc.poll() is None:
            proc.terminate()
        
        stderr = proc.stderr.read().decode('utf-8', errors='replace')
        print("=== STDERR ===")
        print(stderr[-3000:])
        return False
        
    finally:
        try:
            proc.kill()
        except:
            pass

if __name__ == "__main__":
    success = test_vscode_editing()
    sys.exit(0 if success else 1)
