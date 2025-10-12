#!/usr/bin/env python3
"""
Comprehensive test for cross-file variable navigation
Tests realistic crypto library scenario
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

def read_response(proc, expected_id=None, timeout=2.0):
    import select
    while True:
        # Check if data is available with timeout
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

def test_crypto_example():
    """Test cross-file navigation in realistic crypto library"""
    print("="*70)
    print("Comprehensive Cross-File Variable Navigation Test")
    print("Testing: Crypto Library with params and globals")
    print("="*70)
    
    config_path = os.path.abspath("test/fixtures/crypto/config.jazz")
    state_path = os.path.abspath("test/fixtures/crypto/state.jazz")
    chacha_path = os.path.abspath("test/fixtures/crypto/chacha20.jazz")
    
    config_uri = f"file://{config_path}"
    state_uri = f"file://{state_path}"
    chacha_uri = f"file://{chacha_path}"
    
    proc = subprocess.Popen(
        [LSP_SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Initialize
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": f"file://{os.path.abspath('test/fixtures/crypto')}",
                "capabilities": {}
            }
        })
        read_response(proc, expected_id=1)
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        })
        
        import time
        time.sleep(0.1)
        
        # Open all files
        for path, uri in [(config_path, config_uri), (state_path, state_uri), (chacha_path, chacha_uri)]:
            with open(path) as f:
                content = f.read()
            send_request(proc, {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": uri,
                        "languageId": "jasmin",
                        "version": 1,
                        "text": content
                    }
                }
            })
        
        print("\n✓ Opened config.jazz, state.jazz, and chacha20.jazz")
        
        # Read chacha20.jazz to find test positions
        with open(chacha_path) as f:
            chacha_lines = f.read().split('\n')
        
        test_cases = [
            ("CHACHA_ROUNDS", config_uri, "config.jazz"),
            ("BLOCK_SIZE", config_uri, "config.jazz"),
            ("KEY_SIZE", config_uri, "config.jazz"),
            ("NONCE_SIZE", config_uri, "config.jazz"),
            ("chacha_state", state_uri, "state.jazz"),
            ("counter_state", state_uri, "state.jazz"),
        ]
        
        passed = 0
        failed = 0
        request_id = 2
        
        for symbol_name, expected_uri, expected_file in test_cases:
            # Find the symbol in chacha20.jazz
            found_line = None
            for i, line in enumerate(chacha_lines):
                if symbol_name in line and '=' in line and not line.strip().startswith('//'):
                    found_line = i
                    break
            
            if found_line is None:
                print(f"\n❌ Could not find {symbol_name} in chacha20.jazz")
                failed += 1
                continue
            
            # Find character position
            char_pos = chacha_lines[found_line].index(symbol_name)
            
            print(f"\n{'='*70}")
            print(f"Test: {symbol_name} → {expected_file}")
            print(f"{'='*70}")
            print(f"Line {found_line}: {chacha_lines[found_line].strip()}")
            
            # Send definition request
            send_request(proc, {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "textDocument/definition",
                "params": {
                    "textDocument": {"uri": chacha_uri},
                    "position": {"line": found_line, "character": char_pos + 2}
                }
            })
            
            response = read_response(proc, expected_id=request_id, timeout=5.0)
            request_id += 1
            
            if response is None:
                print(f"❌ FAIL: Timeout waiting for response")
                failed += 1
                continue
            
            if "result" in response and response["result"]:
                locations = response["result"]
                if isinstance(locations, list) and len(locations) > 0:
                    loc = locations[0]
                elif isinstance(locations, dict):
                    loc = locations
                else:
                    print(f"❌ FAIL: No location in response")
                    failed += 1
                    continue
                
                target_uri = loc.get("uri", "")
                if expected_uri in target_uri or expected_file in target_uri:
                    print(f"✅ PASS: Correctly points to {expected_file}")
                    print(f"   Range: line {loc['range']['start']['line']}")
                    passed += 1
                else:
                    print(f"❌ FAIL: Expected {expected_file}, got {target_uri}")
                    failed += 1
            else:
                error_msg = response.get("error", {}).get("message", "Unknown error")
                print(f"❌ FAIL: {error_msg}")
                failed += 1
        
        print(f"\n{'='*70}")
        print(f"Results: {passed}/{len(test_cases)} passed")
        print(f"{'='*70}")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️  {failed} test(s) failed")
            return False
        
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    success = test_crypto_example()
    sys.exit(0 if success else 1)
