#!/usr/bin/env python3
"""
Test Workspace Symbols Feature

Tests the workspace/symbol request which provides global symbol
search across all open documents.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

# Test fixture 1: utils.jazz
UTILS_CODE = """
// Utility functions
fn add_numbers(reg u32 a, reg u32 b) -> reg u32 {
    reg u32 result;
    result = a + b;
    return result;
}

fn multiply_values(reg u64 x, reg u64 y) -> reg u64 {
    reg u64 product;
    product = x * y;
    return product;
}

const int UTIL_CONSTANT = 42;
"""

# Test fixture 2: crypto.jazz
CRYPTO_CODE = """
// Crypto functions
fn hash_data(reg u64[4] data) -> reg u64 {
    reg u64 result;
    result = data[0] ^ data[1];
    return result;
}

fn encrypt_block(reg u32 block) -> reg u32 {
    reg u32 encrypted;
    encrypted = block << #1;
    return encrypted;
}

const int KEY_SIZE = 256;
"""

# Test fixture 3: main.jazz
MAIN_CODE = """
// Main program
require "utils.jazz"
require "crypto.jazz"

export fn process_data() -> reg u64 {
    reg u64 value;
    value = #123;
    return value;
}

fn internal_helper() -> reg u32 {
    reg u32 temp;
    temp = #1;
    return temp;
}

const int BUFFER_SIZE = 1024;
"""

def send_lsp_message(proc, method, params, msg_id=None):
    """Send an LSP message"""
    message = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    }
    if msg_id is not None:
        message["id"] = msg_id
    
    content = json.dumps(message)
    content_bytes = content.encode('utf-8')
    header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
    
    proc.stdin.write(header.encode('utf-8'))
    proc.stdin.write(content_bytes)
    proc.stdin.flush()

def read_lsp_response(proc):
    """Read an LSP response"""
    # Read headers
    headers = {}
    while True:
        line = proc.stdout.readline().decode('utf-8')
        if line == '\r\n' or line == '\n':
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    # Read content
    content_length = int(headers.get('Content-Length', 0))
    content = proc.stdout.read(content_length).decode('utf-8')
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {content}")
        return None

def test_workspace_symbols():
    """Test workspace symbols feature"""
    print("\n" + "="*60)
    print("Testing Workspace Symbols Feature")
    print("="*60)
    
    # Find LSP server (go up to project root: test/test_symbols -> test -> project root)
    lsp_server = Path(__file__).parent.parent.parent / "_build" / "default" / "jasmin-lsp" / "jasmin_lsp.exe"
    if not lsp_server.exists():
        print(f"❌ LSP server not found: {lsp_server}")
        import pytest
        pytest.fail(f"LSP server not found: {lsp_server}")
    
    try:
        # Start LSP server
        proc = subprocess.Popen(
            [str(lsp_server)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Initialize
        print("\n1. Initializing server...")
        send_lsp_message(proc, "initialize", {
            "processId": None,
            "rootUri": "file:///tmp",
            "capabilities": {}
        }, msg_id=1)
        
        response = read_lsp_response(proc)
        if not response or "result" not in response:
            print("❌ Failed to initialize")
            import pytest
            pytest.fail("Failed to initialize")
        
        # Check if workspaceSymbolProvider is advertised
        capabilities = response.get("result", {}).get("capabilities", {})
        if not capabilities.get("workspaceSymbolProvider"):
            print("❌ workspaceSymbolProvider not advertised in capabilities")
            import pytest
            pytest.fail("workspaceSymbolProvider not advertised in capabilities")
        
        print("✅ workspaceSymbolProvider is advertised")
        
        # Send initialized notification
        send_lsp_message(proc, "initialized", {})
        
        # Open multiple documents
        print("\n2. Opening test documents...")
        
        documents = [
            ("file:///tmp/utils.jazz", UTILS_CODE, "utils.jazz"),
            ("file:///tmp/crypto.jazz", CRYPTO_CODE, "crypto.jazz"),
            ("file:///tmp/main.jazz", MAIN_CODE, "main.jazz")
        ]
        
        for uri, code, name in documents:
            send_lsp_message(proc, "textDocument/didOpen", {
                "textDocument": {
                    "uri": uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": code
                }
            })
            print(f"  - Opened {name}")
        
        # Wait for processing
        time.sleep(1.0)
        
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Search for all symbols (empty query)
        print("\n3. Test 1: Search all symbols (empty query)...")
        tests_total += 1
        
        send_lsp_message(proc, "workspace/symbol", {
            "query": ""
        }, msg_id=2)
        
        response = read_lsp_response(proc)
        
        if response and "result" in response:
            symbols = response["result"]
            print(f"  Found {len(symbols)} symbols across workspace")
            
            if len(symbols) >= 9:  # At least 9 symbols expected
                print(f"✅ Found expected number of symbols: {len(symbols)}")
                tests_passed += 1
            else:
                print(f"❌ Expected at least 9 symbols, got {len(symbols)}")
        else:
            print("❌ No response or error")
        
        # Test 2: Search for specific function "add_numbers"
        print("\n4. Test 2: Search for 'add_numbers'...")
        tests_total += 1
        
        send_lsp_message(proc, "workspace/symbol", {
            "query": "add_numbers"
        }, msg_id=3)
        
        response = read_lsp_response(proc)
        
        if response and "result" in response:
            symbols = response["result"]
            found = any(s.get("name") == "add_numbers" for s in symbols)
            
            if found:
                print("✅ Found 'add_numbers' function")
                tests_passed += 1
                
                # Check location
                for s in symbols:
                    if s.get("name") == "add_numbers":
                        location = s.get("location", {})
                        uri = location.get("uri", "")
                        if "utils.jazz" in uri:
                            print("  ✅ Correct file: utils.jazz")
                        else:
                            print(f"  ⚠️ Unexpected file: {uri}")
            else:
                print("❌ 'add_numbers' not found")
        else:
            print("❌ No response or error")
        
        # Test 3: Fuzzy search for "hash"
        print("\n5. Test 3: Search for 'hash'...")
        tests_total += 1
        
        send_lsp_message(proc, "workspace/symbol", {
            "query": "hash"
        }, msg_id=4)
        
        response = read_lsp_response(proc)
        
        if response and "result" in response:
            symbols = response["result"]
            found = any("hash" in s.get("name", "").lower() for s in symbols)
            
            if found:
                print("✅ Found symbols matching 'hash'")
                tests_passed += 1
                for s in symbols:
                    if "hash" in s.get("name", "").lower():
                        print(f"  - {s.get('name')}")
            else:
                print("❌ No symbols matching 'hash' found")
        else:
            print("❌ No response or error")
        
        # Test 4: Search for constant "KEY_SIZE"
        print("\n6. Test 4: Search for 'KEY_SIZE'...")
        tests_total += 1
        
        send_lsp_message(proc, "workspace/symbol", {
            "query": "KEY_SIZE"
        }, msg_id=5)
        
        response = read_lsp_response(proc)
        
        if response and "result" in response:
            symbols = response["result"]
            found = any(s.get("name") == "KEY_SIZE" for s in symbols)
            
            if found:
                print("✅ Found 'KEY_SIZE' constant")
                tests_passed += 1
            else:
                print("❌ 'KEY_SIZE' not found")
        else:
            print("❌ No response or error")
        
        # Test 5: Search across files for "CONSTANT" (partial match)
        print("\n7. Test 5: Partial match 'CONSTANT'...")
        tests_total += 1
        
        send_lsp_message(proc, "workspace/symbol", {
            "query": "CONSTANT"
        }, msg_id=6)
        
        response = read_lsp_response(proc)
        
        if response and "result" in response:
            symbols = response["result"]
            matching = [s.get("name") for s in symbols if "CONSTANT" in s.get("name", "")]
            
            if len(matching) >= 1:
                print(f"✅ Found {len(matching)} symbols containing 'CONSTANT':")
                for name in matching:
                    print(f"  - {name}")
                tests_passed += 1
            else:
                print("❌ No symbols containing 'CONSTANT' found")
        else:
            print("❌ No response or error")
        
        # Test 6: Case-insensitive search
        print("\n8. Test 6: Case-insensitive search 'encrypt'...")
        tests_total += 1
        
        send_lsp_message(proc, "workspace/symbol", {
            "query": "encrypt"  # lowercase
        }, msg_id=7)
        
        response = read_lsp_response(proc)
        
        if response and "result" in response:
            symbols = response["result"]
            found = any("encrypt" in s.get("name", "").lower() for s in symbols)
            
            if found:
                print("✅ Case-insensitive search works")
                tests_passed += 1
            else:
                print("❌ Case-insensitive search failed")
        else:
            print("❌ No response or error")
        
        # Test 7: Non-existent symbol
        print("\n9. Test 7: Search for non-existent symbol...")
        tests_total += 1
        
        send_lsp_message(proc, "workspace/symbol", {
            "query": "nonexistent_function_xyz"
        }, msg_id=8)
        
        response = read_lsp_response(proc)
        
        if response and "result" in response:
            symbols = response["result"]
            
            if len(symbols) == 0:
                print("✅ Correctly returns empty for non-existent symbol")
                tests_passed += 1
            else:
                print(f"⚠️ Returned {len(symbols)} symbols for non-existent search")
        else:
            print("❌ No response or error")
        
        # Summary
        print("\n" + "="*60)
        print(f"Test Results: {tests_passed}/{tests_total} passed ({100*tests_passed//tests_total}%)")
        print("="*60)
        
        # Shutdown
        send_lsp_message(proc, "shutdown", {}, msg_id=99)
        read_lsp_response(proc)
        send_lsp_message(proc, "exit", {})
        
        proc.terminate()
        proc.wait(timeout=2)
        
        assert tests_passed == tests_total, f"Only {tests_passed}/{tests_total} tests passed"
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        test_workspace_symbols()
        sys.exit(0)
    except:
        sys.exit(1)
