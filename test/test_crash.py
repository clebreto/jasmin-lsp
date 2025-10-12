#!/usr/bin/env python3
import subprocess
import json
import os
import sys

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

proc = subprocess.Popen(
    [SERVER],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

def send_message(msg):
    msg_str = json.dumps(msg)
    content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
    proc.stdin.write(content.encode())
    proc.stdin.flush()

try:
    # Initialize
    send_message({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"processId": None, "rootUri": "file:///tmp", "capabilities": {}}
    })
    
    import time
    time.sleep(1)
    
    # Check if process is still alive
    if proc.poll() is not None:
        print("SERVER CRASHED DURING INIT!")
        stderr = proc.stderr.read().decode('utf-8')
        print("=== STDERR ===")
        print(stderr)
        sys.exit(1)
    
    # Send initialized
    send_message({"jsonrpc": "2.0", "method": "initialized", "params": {}})
    time.sleep(0.2)
    
    # Check again
    if proc.poll() is not None:
        print("SERVER CRASHED AFTER INITIALIZED!")
        stderr = proc.stderr.read().decode('utf-8')
        print("=== STDERR ===")
        print(stderr)
        sys.exit(1)
    
    print("Server is running OK!")
    proc.terminate()
    proc.wait(timeout=1)
    stderr = proc.stderr.read().decode('utf-8')
    print("=== STDERR ===")
    print(stderr[-2000:])  # Last 2000 chars
    
except Exception as e:
    print(f"Error: {e}")
    proc.kill()
finally:
    try:
        proc.kill()
    except:
        pass
