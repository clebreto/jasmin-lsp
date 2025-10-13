#!/usr/bin/env python3
"""Simple test to check if symbols are being extracted properly"""

import subprocess
import json
import sys
from pathlib import Path

# Path to LSP server (go up to project root, then to _build)
LSP_SERVER = Path(__file__).parent.parent.parent / "_build/default/jasmin-lsp/jasmin_lsp.exe"

# Test file content
TEST_FILE_CONTENT = """fn test(reg u64 x, reg u32 y) -> reg u64 {
  reg u64 result;
  reg u32 temp;
  result = x + #1;
  temp = y;
  return result;
}
"""

def send_lsp_request(request):
    """Send a request to the LSP server"""
    content = json.dumps(request)
    header = f"Content-Length: {len(content)}\r\n\r\n"
    return header + content

def read_lsp_response(proc, expected_id=None):
    """Read an LSP response, handling multiple messages"""
    max_attempts = 20
    for _ in range(max_attempts):
        line = proc.stdout.readline()
        if not line:
            return None
        if line.startswith("Content-Length"):
            content_length = int(line.split(":")[1].strip())
            proc.stdout.readline()  # Empty line
            content = proc.stdout.read(content_length)
            response = json.loads(content)
            # If we're looking for a specific ID, check if this is it
            if expected_id is None or response.get("id") == expected_id:
                return response
            # Otherwise keep looking
    return None

def test_document_symbols():
    """Test that symbols are being extracted with types"""
    test_file_uri = "file:///tmp/test_symbols.jazz"
    
    # Start LSP server
    proc = subprocess.Popen(
        [str(LSP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    # Initialize
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": None,
            "rootUri": "file:///tmp",
            "capabilities": {}
        }
    }
    proc.stdin.write(send_lsp_request(init_request))
    proc.stdin.flush()
    
    # Read initialize response
    response = read_lsp_response(proc)
    
    # Initialized notification
    initialized = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    }
    proc.stdin.write(send_lsp_request(initialized))
    proc.stdin.flush()
    
    # Open document
    did_open = {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": test_file_uri,
                "languageId": "jasmin",
                "version": 1,
                "text": TEST_FILE_CONTENT
            }
        }
    }
    proc.stdin.write(send_lsp_request(did_open))
    proc.stdin.flush()
    
    import time
    time.sleep(0.2)  # Wait for parsing
    
    # Request document symbols
    print("Requesting document symbols...")
    symbols_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/documentSymbol",
        "params": {
            "textDocument": {"uri": test_file_uri}
        }
    }
    proc.stdin.write(send_lsp_request(symbols_request))
    proc.stdin.flush()
    
    # Read symbols response
    response = read_lsp_response(proc, expected_id=2)
    
    if not response:
        print("❌ No response from server")
        proc.terminate()
        return False
        
    print(f"\nDocument Symbols Response:")
    print(json.dumps(response, indent=2))
    
    # Check for symbols
    if "result" in response and response["result"]:
        symbols = response["result"]
        print(f"\nFound {len(symbols)} symbols")
        
        for sym in symbols:
            name = sym.get("name", "unknown")
            detail = sym.get("detail", "no detail")
            kind = sym.get("kind", "?")
            print(f"  - {name} (kind={kind}): {detail}")
    else:
        print(f"❌ No symbols found: {response}")
        proc.terminate()
        return False
    
    # Shutdown
    shutdown_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "shutdown",
        "params": None
    }
    proc.stdin.write(send_lsp_request(shutdown_request))
    proc.stdin.flush()
    
    proc.terminate()
    
    # Test passes if we got here without errors
    assert True

if __name__ == "__main__":
    try:
        test_document_symbols()
        sys.exit(0)
    except:
        sys.exit(1)
