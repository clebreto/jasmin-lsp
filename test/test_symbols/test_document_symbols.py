#!/usr/bin/env python3
"""
Test Document Symbols Feature

Tests the textDocument/documentSymbol request which provides
an outline view of the current file's symbols.
"""

import json
import subprocess
import sys
from pathlib import Path

# Test fixture content
TEST_CODE = """
// Test file for document symbols
param int BUFFER_SIZE = 256;

const int MAX_VALUE = 1000;

global u64[4] shared_data = {1, 2, 3, 4};

fn helper(reg u32 x) -> reg u32 {
    reg u32 result;
    result = x + #1;
    return result;
}

inline fn compute(reg u64 a, reg u64 b) -> reg u64 {
    reg u64 sum;
    reg u64 product;
    sum = a + b;
    product = a * b;
    return product;
}

export fn main() -> reg u64 {
    reg u64 value;
    reg u32 temp;
    
    temp = helper(#42);
    value = compute(#10, #20);
    
    return value;
}
"""

def run_lsp_command(server_path, messages, timeout=3):
    """Send messages to LSP server and collect all output"""
    input_data = ""
    for msg in messages:
        content = json.dumps(msg)
        content_bytes = content.encode('utf-8')
        input_data += f"Content-Length: {len(content_bytes)}\r\n\r\n{content}"
        
    try:
        result = subprocess.run(
            [server_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired as e:
        return (e.stdout or "") + (e.stderr or "")

def test_document_symbols():
    """Test document symbols feature"""
    print("\n" + "="*60)
    print("Testing Document Symbols Feature")
    print("="*60)
    
    # Find LSP server
    lsp_server = Path(__file__).parent.parent / "_build" / "default" / "jasmin-lsp" / "jasmin_lsp.exe"
    if not lsp_server.exists():
        print(f"❌ LSP server not found: {lsp_server}")
        return False
    
    try:
        # Prepare messages
        test_uri = "file:///tmp/test_symbols.jazz"
        
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"processId": None, "rootUri": "file:///tmp", "capabilities": {}}
        }
        
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        open_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": test_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": TEST_CODE
                }
            }
        }
        
        symbols_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/documentSymbol",
            "params": {
                "textDocument": {
                    "uri": test_uri
                }
            }
        }
        
        # Run command
        print("\n1. Sending LSP messages...")
        output = run_lsp_command(str(lsp_server), [init_msg, initialized_msg, open_msg, symbols_msg], timeout=5)
        
        # Parse output for responses
        responses = []
        for line in output.split('\n'):
            if line.strip() and '{' in line:
                try:
                    response = json.loads(line)
                    responses.append(response)
                except:
                    pass
        
        # Check for init response with capabilities
        print("\n2. Checking capabilities...")
        init_response = None
        for resp in responses:
            if resp.get("id") == 1 and "result" in resp:
                init_response = resp
                break
        
        if not init_response:
            print("❌ No initialization response found")
            return False
        
        capabilities = init_response.get("result", {}).get("capabilities", {})
        if not capabilities.get("documentSymbolProvider"):
            print("❌ documentSymbolProvider not advertised")
            return False
        
        print("✅ documentSymbolProvider is advertised")
        
        # Find document symbols response
        print("\n3. Checking document symbols response...")
        response = None
        for resp in responses:
            if resp.get("id") == 2:
                response = resp
                break
        
        if not response:
            print("❌ No response received")
            return False
        
        if "error" in response:
            print(f"❌ Error response: {response['error']}")
            return False
        
        if "result" not in response:
            print("❌ No result in response")
            return False
        
        symbols = response["result"]
        
        if symbols is None:
            print("❌ Symbols list is None")
            return False
        
        print(f"\n✅ Received {len(symbols)} symbols")
        
        # Analyze symbols
        print("\n4. Analyzing symbols...")
        
        expected_symbols = {
            "BUFFER_SIZE": "Parameter",
            "MAX_VALUE": "Constant",
            "shared_data": "Variable",
            "helper": "Function",
            "compute": "Function",
            "main": "Function"
        }
        
        found_symbols = {}
        
        for symbol in symbols:
            name = symbol.get("name", "")
            kind = symbol.get("kind", 0)
            
            # LSP SymbolKind enum
            kind_names = {
                1: "File", 2: "Module", 3: "Namespace", 4: "Package",
                5: "Class", 6: "Method", 7: "Property", 8: "Field",
                9: "Constructor", 10: "Enum", 11: "Interface", 12: "Function",
                13: "Variable", 14: "Constant", 15: "String", 16: "Number",
                17: "Boolean", 18: "Array", 19: "Object", 20: "Key",
                21: "Null", 22: "EnumMember", 23: "Struct", 24: "Event",
                25: "Operator", 26: "TypeParameter"
            }
            
            kind_name = kind_names.get(kind, f"Unknown({kind})")
            found_symbols[name] = kind_name
            
            print(f"  - {name}: {kind_name}")
            
            # Check range
            if "range" in symbol:
                range_obj = symbol["range"]
                start = range_obj.get("start", {})
                end = range_obj.get("end", {})
                print(f"    Range: ({start.get('line')},{start.get('character')}) to ({end.get('line')},{end.get('character')})")
        
        # Verify expected symbols
        print("\n5. Verifying expected symbols...")
        
        tests_passed = 0
        tests_total = 0
        
        # Test: BUFFER_SIZE (param)
        tests_total += 1
        if "BUFFER_SIZE" in found_symbols:
            print("✅ Found parameter: BUFFER_SIZE")
            tests_passed += 1
        else:
            print("❌ Missing parameter: BUFFER_SIZE")
        
        # Test: MAX_VALUE (const)
        tests_total += 1
        if "MAX_VALUE" in found_symbols:
            print("✅ Found constant: MAX_VALUE")
            tests_passed += 1
        else:
            print("❌ Missing constant: MAX_VALUE")
        
        # Test: shared_data (global)
        tests_total += 1
        if "shared_data" in found_symbols:
            print("✅ Found global variable: shared_data")
            tests_passed += 1
        else:
            print("❌ Missing global variable: shared_data")
        
        # Test: helper function
        tests_total += 1
        if "helper" in found_symbols and "Function" in found_symbols["helper"]:
            print("✅ Found function: helper")
            tests_passed += 1
        else:
            print("❌ Missing or wrong kind for function: helper")
        
        # Test: compute function
        tests_total += 1
        if "compute" in found_symbols and "Function" in found_symbols["compute"]:
            print("✅ Found function: compute")
            tests_passed += 1
        else:
            print("❌ Missing or wrong kind for function: compute")
        
        # Test: main function
        tests_total += 1
        if "main" in found_symbols and "Function" in found_symbols["main"]:
            print("✅ Found function: main (export)")
            tests_passed += 1
        else:
            print("❌ Missing or wrong kind for function: main")
        
        # Summary
        print("\n" + "="*60)
        print(f"Test Results: {tests_passed}/{tests_total} passed ({100*tests_passed//tests_total if tests_total > 0 else 0}%)")
        print("="*60)
        
        return tests_passed == tests_total
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_document_symbols()
    sys.exit(0 if success else 1)
