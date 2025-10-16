#!/usr/bin/env python3
"""
Test that diagnostics are published after textDocument/didChange notifications.

This test verifies the fix for the issue where PROBLEMS are not updated upon writing in the file.
"""
import subprocess
import json
import time

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def test_didchange_sends_diagnostics():
    """Test that textDocument/didChange triggers diagnostic publishing"""
    
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

    def read_response():
        """Read one response from the server"""
        # Read headers
        headers = {}
        while True:
            line = proc.stdout.readline().decode('utf-8')
            if line == '\r\n':
                break
            if ': ' in line:
                key, value = line.split(': ', 1)
                headers[key.strip()] = value.strip()
        
        # Read body
        content_length = int(headers.get('Content-Length', 0))
        if content_length > 0:
            body = proc.stdout.read(content_length).decode('utf-8')
            return json.loads(body)
        return None

    try:
        # Initialize
        send_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": "file:///tmp",
                "capabilities": {
                    "textDocument": {
                        "synchronization": {
                            "dynamicRegistration": True,
                            "willSave": True,
                            "willSaveWaitUntil": True,
                            "didSave": True
                        }
                    }
                }
            }
        })
        resp = read_response()
        print(f"RECEIVED initialize response: {resp['id']}")
        
        # Initialized
        send_message({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        time.sleep(0.1)
        
        # didOpen with valid content
        print("\n=== SENDING DIDOPEN WITH VALID CONTENT ===")
        send_message({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///tmp/test.jazz",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": "fn test() -> reg u64 {\n  reg u64 x;\n  x = 42;\n  return x;\n}\n"
                }
            }
        })
        
        # Read diagnostics response from didOpen
        time.sleep(0.2)
        initial_diagnostics = None
        while True:
            try:
                resp = read_response()
                if resp and resp.get('method') == 'textDocument/publishDiagnostics':
                    initial_diagnostics = resp
                    print(f"RECEIVED diagnostics after didOpen: {len(resp['params']['diagnostics'])} diagnostics")
                    break
            except:
                break
        
        # Now send didChange with invalid content (introduce syntax error)
        print("\n=== SENDING DIDCHANGE WITH INVALID CONTENT ===")
        send_message({
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {
                    "uri": "file:///tmp/test.jazz",
                    "version": 2
                },
                "contentChanges": [
                    {
                        "text": "fn test() -> reg u64 {\n  invalid_syntax here\n}\n"
                    }
                ]
            }
        })
        
        # Read diagnostics response from didChange
        time.sleep(0.3)
        updated_diagnostics = None
        attempt = 0
        while attempt < 5:
            try:
                resp = read_response()
                if resp and resp.get('method') == 'textDocument/publishDiagnostics':
                    updated_diagnostics = resp
                    print(f"RECEIVED diagnostics after didChange: {len(resp['params']['diagnostics'])} diagnostics")
                    break
            except Exception as e:
                print(f"Attempt {attempt}: {e}")
            attempt += 1
            time.sleep(0.1)
        
        # Verify results
        if updated_diagnostics is None:
            print("\n!!! TEST FAILED: No diagnostics received after didChange !!!")
            print("This is the bug: diagnostics should be published after textDocument/didChange")
            return_code = 1
        else:
            print(f"\n=== TEST PASSED: Diagnostics published after didChange ===")
            diagnostic_count = len(updated_diagnostics['params']['diagnostics'])
            print(f"Received {diagnostic_count} diagnostics")
            if diagnostic_count > 0:
                for diag in updated_diagnostics['params']['diagnostics']:
                    print(f"  - {diag['message']} at line {diag['range']['start']['line']}")
            return_code = 0
        
        # Cleanup
        proc.terminate()
        proc.wait(timeout=1)
        return return_code
        
    except Exception as e:
        print(f"\n!!! TEST ERROR: {e} !!!")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        try:
            proc.kill()
        except:
            pass


if __name__ == "__main__":
    exit(test_didchange_sends_diagnostics())
