#!/usr/bin/env python3
import subprocess
import json
import time

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
    print(f"SENT: {msg.get('method', 'id=' + str(msg.get('id')))}")

try:
    # Initialize
    send_message({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"processId": None, "rootUri": "file:///tmp", "capabilities": {}}
    })
    time.sleep(0.3)
    
    # Initialized
    send_message({"jsonrpc": "2.0", "method": "initialized", "params": {}})
    time.sleep(0.3)
    
    # didOpen
    print("\n=== ABOUT TO SEND DIDOPEN ===")
    send_message({
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": "file:///tmp/test.jazz",
                "languageId": "jasmin",
                "version": 1,
                "text": "fn test() -> reg u64 { reg u64 x; return x; }"
            }
        }
    })
    
    print("Waiting for server response...")
    time.sleep(2)
    
    # Check if crashed
    returncode = proc.poll()
    if returncode is not None:
        print(f"\n!!! SERVER CRASHED with return code {returncode} !!!")
    else:
        print("\nServer still running")
    
    proc.terminate()
    proc.wait(timeout=1)
    
except Exception as e:
    print(f"\nError: {e}")
finally:
    try:
        stderr = proc.stderr.read().decode('utf-8')
        print("\n=== SERVER STDERR ===")
        print(stderr)
    except:
        pass
    try:
        proc.kill()
    except:
        pass
