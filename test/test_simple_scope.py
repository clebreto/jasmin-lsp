#!/usr/bin/env python3
"""
Simple test to verify scope resolution fix
"""

import subprocess
import json
import sys
import os

LSP_SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def send_request(proc, request):
    content = json.dumps(request)
    message = f"Content-Length: {len(content)}\r\n\r\n{content}"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

def read_response(proc, expected_id=None, timeout=3.0):
    import select
    while True:
        ready, _, _ = select.select([proc.stdout], [], [], timeout)
        if not ready:
            return None
        
        headers = {}
        while True:
            line = proc.stdout.readline().decode().strip()
            if not line:
                break
            if ": " not in line:
                continue
            key, value = line.split(": ", 1)
            headers[key] = value
        
        content_length = int(headers.get("Content-Length", 0))
        if content_length == 0:
            return None
        content = proc.stdout.read(content_length).decode()
        response = json.loads(content)
        
        if expected_id is not None and "id" not in response:
            continue
        
        if expected_id is not None and "id" in response:
            if response["id"] == expected_id:
                return response
        else:
            return response

def test_scope_resolution():
    """Test that go-to-definition respects function scope"""
    
    # Create test file with two functions, each with a 'status' variable
    test_content = """export fn ml_dsa_44_sign(
    #public reg ptr u8[32] sig,
    #public reg ptr u32[3] ctx_m_rand,
    #public reg ptr u32[2] ctxlen_mlen,
    #secret reg ptr u8[64] signing_key
) -> #public reg ptr u8[32], #public reg u32
{
    reg u32 status;

    status = 0;

    return sig, status;
}

export fn ml_dsa_44_verify(
    #public reg ptr u8[32] sig,
    #public reg ptr u32[2] ctx_m,
    #public reg ptr u32[2] ctxlen_mlen,
    #public reg ptr u8[64] verification_key
) -> #public reg u32 {
    reg u32 status;

    status = 1;
    status = status;

    return status;
}
"""
    
    test_file = "/tmp/test_scope_fix.jazz"
    with open(test_file, "w") as f:
        f.write(test_content)
    
    file_uri = f"file://{test_file}"
    
    print("🔍 Testing scope resolution fix...")
    print("=" * 70)
    
    # Start LSP server
    lsp_path = "_build/default/jasmin-lsp/jasmin_lsp.exe"
    if not os.path.exists(lsp_path):
        print(f"❌ LSP server not found: {lsp_path}")
        return False
    
    proc = subprocess.Popen(
        [lsp_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Initialize
        print("\n📡 Initializing LSP server...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": "file:///tmp",
                "capabilities": {}
            }
        })
        response = read_response(proc, expected_id=1)
        if not response or "error" in response:
            print(f"❌ Failed to initialize: {response}")
            return False
        print("✓ Initialized")
        
        # Initialized notification
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        })
        
        # Open document
        print("📂 Opening document...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": file_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": test_content
                }
            }
        })
        
        # Wait a bit for parsing
        import time
        time.sleep(1.0)
        print("✓ Document opened and parsed")
        
        # Test: Go to definition on second 'status' in 'status = status;' in ml_dsa_44_verify
        # This should jump to line 20 (0-indexed, line 21 in editor), NOT line 7
        print("\n📍 Test: Second 'status' in 'status = status;' in ml_dsa_44_verify")
        print("   Looking at line 23 (0-indexed), character 15")
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/definition",
            "params": {
                "textDocument": {"uri": file_uri},
                "position": {"line": 23, "character": 15}  # 0-indexed: line 24 in editor
            }
        })
        
        def_response = read_response(proc, expected_id=2)
        
        if not def_response:
            print("❌ ERROR: No response received")
            return False
        
        print(f"\nResponse: {json.dumps(def_response, indent=2)}")
        
        if "result" in def_response and def_response["result"]:
            result = def_response["result"]
            if isinstance(result, list) and len(result) > 0:
                location = result[0]
            else:
                location = result
            
            def_line = location["range"]["start"]["line"]
            print(f"\n✓ Definition found at line {def_line} (0-indexed)")
            
            # Should be line 20 (0-indexed) - the declaration in ml_dsa_44_verify
            if def_line == 20:
                print("✅ SUCCESS: Correctly jumped to 'reg u32 status;' in ml_dsa_44_verify!")
                print("   The scope resolution bug is FIXED!")
                return True
            else:
                print(f"❌ BUG STILL EXISTS: Expected line 20 (0-indexed), got line {def_line}")
                if def_line == 7:
                    print("   Still jumping to 'status' in ml_dsa_44_sign instead of ml_dsa_44_verify")
                return False
        else:
            print("❌ ERROR: No definition found in result")
            return False
        
    finally:
        proc.terminate()
        proc.wait(timeout=2)
        
        # Read and print stderr logs
        if proc.stderr:
            stderr_output = proc.stderr.read().decode('utf-8', errors='ignore')
            if stderr_output:
                print("\n" + "="*70)
                print("LSP SERVER LOGS (stderr):")
                print("="*70)
                print(stderr_output)
        
        print("\n✓ LSP server stopped")

if __name__ == "__main__":
    try:
        success = test_scope_resolution()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
