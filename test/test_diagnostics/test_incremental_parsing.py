#!/usr/bin/env python3
"""
Test that diagnostics are correctly detected after incremental document changes.

This test captures a regression where tree-sitter's incremental parsing would
miss syntax errors that a full re-parse would detect. The fix forces a full
re-parse on each document change instead of using incremental parsing.
"""
import subprocess
import json
import time

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def test_incremental_parsing_detects_errors():
    """
    Test that editing a document to introduce syntax errors is detected.
    
    Regression: When using incremental parsing (passing old tree to parser),
    tree-sitter would not generate ERROR nodes for some syntax errors.
    With full re-parsing (passing None), errors are correctly detected.
    """
    
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

    def read_response():
        """Read one response from the server"""
        headers = {}
        while True:
            line = proc.stdout.readline().decode('utf-8')
            if line == '\r\n':
                break
            if ': ' in line:
                key, value = line.split(': ', 1)
                headers[key.strip()] = value.strip()
        
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
                "capabilities": {}
            }
        })
        resp = read_response()
        
        # Initialized
        send_message({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        time.sleep(0.1)
        
        # Open document with valid Jasmin code
        send_message({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///tmp/test_incremental.jazz",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": """fn test_consistency() -> reg bool {
    stack u8[32] keygen_randomness;
    reg u32 context = 0x3000;
    reg u32 context_size = 64;
    
    return true;
}
"""
                }
            }
        })
        
        # Read initial diagnostics
        time.sleep(0.2)
        initial_diagnostics = None
        while True:
            try:
                resp = read_response()
                if resp and resp.get('method') == 'textDocument/publishDiagnostics':
                    initial_diagnostics = resp
                    break
            except:
                break
        
        assert initial_diagnostics is not None, "Should receive initial diagnostics"
        initial_count = len(initial_diagnostics['params']['diagnostics'])
        print(f"Initial diagnostics: {initial_count}")
        
        # Now edit the document to introduce a syntax error
        # This simulates typing invalid syntax like '[;]' on a line
        send_message({
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {
                    "uri": "file:///tmp/test_incremental.jazz",
                    "version": 2
                },
                "contentChanges": [
                    {
                        "text": """fn test_consistency() -> reg bool {
    stack u8[32] keygen_randomness;
    reg u32 context = 0x3000;
    reg u32 context_size = 64;
    
[;]

    return true;
}
"""
                    }
                ]
            }
        })
        
        # Wait for updated diagnostics
        time.sleep(0.3)
        updated_diagnostics = None
        attempts = 0
        while attempts < 5:
            try:
                resp = read_response()
                if resp and resp.get('method') == 'textDocument/publishDiagnostics':
                    updated_diagnostics = resp
                    break
            except:
                pass
            attempts += 1
            time.sleep(0.1)
        
        assert updated_diagnostics is not None, \
            "Should receive diagnostics after document change"
        
        updated_count = len(updated_diagnostics['params']['diagnostics'])
        print(f"Updated diagnostics: {updated_count}")
        
        # The key assertion: after introducing '[;]', we should detect an error
        # Without the fix (using incremental parsing), tree-sitter would miss this
        # With the fix (full re-parse), tree-sitter detects the ERROR node
        assert updated_count > initial_count or updated_count > 0, \
            f"Should detect syntax error after introducing '[;]'. " \
            f"Initial: {initial_count}, Updated: {updated_count}. " \
            f"This test fails with incremental parsing, passes with full re-parse."
        
        print("✓ Test passed: Syntax error correctly detected after document change")
        
        proc.terminate()
        proc.wait(timeout=1)
        
    except Exception as e:
        print(f"Test error: {e}")
        raise
    finally:
        try:
            proc.kill()
        except:
            pass


if __name__ == "__main__":
    test_incremental_parsing_detects_errors()
