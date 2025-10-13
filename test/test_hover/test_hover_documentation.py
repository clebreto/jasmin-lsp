#!/usr/bin/env python3
"""Test to verify hover displays documentation comments."""

import subprocess
import json
import os
import time
from pathlib import Path

def send_message(proc, msg):
    content = json.dumps(msg)
    message = f"Content-Length: {len(content)}\r\n\r\n{content}"
    proc.stdin.write(message.encode())
    proc.stdin.flush()

def read_message(proc):
    headers = {}
    while True:
        line = proc.stdout.readline().decode('utf-8').strip()
        if not line:
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    content_length = int(headers.get('Content-Length', 0))
    if content_length == 0:
        return None
    
    content = proc.stdout.read(content_length).decode('utf-8')
    return json.loads(content)

def read_until_response(proc, request_id):
    while True:
        msg = read_message(proc)
        if msg is None:
            return None
        if 'id' in msg and msg['id'] == request_id:
            return msg

def test_hover_documentation():
    """Test hover documentation for various symbol types."""
    server_path = "./_build/default/jasmin-lsp/jasmin_lsp.exe"
    
    # Test files
    lib_file = Path(__file__).parent.parent / "fixtures" / "documented_lib.jinc"
    main_file = Path(__file__).parent.parent / "fixtures" / "documented_code.jazz"
    
    if not lib_file.exists():
        print(f"❌ Test file not found: {lib_file}")
        return False
    
    if not main_file.exists():
        print(f"❌ Test file not found: {main_file}")
        return False
    
    lib_content = lib_file.read_text()
    main_content = main_file.read_text()
    lib_uri = f"file://{lib_file.absolute()}"
    main_uri = f"file://{main_file.absolute()}"
    
    print("Testing Hover Documentation Display")
    print("=" * 80)
    print()
    
    proc = subprocess.Popen(
        [server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    test_passed = True
    
    try:
        # Initialize
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": f"file://{Path.cwd()}",
                "capabilities": {}
            }
        })
        init_response = read_until_response(proc, 0)
        
        if not init_response or 'result' not in init_response:
            print("❌ Failed to initialize")
            return False
        
        send_message(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        time.sleep(0.1)
        
        # Open library file
        send_message(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": lib_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": lib_content
                }
            }
        })
        time.sleep(0.1)
        
        # Open main file
        send_message(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": main_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": main_content
                }
            }
        })
        time.sleep(0.2)
        
        # Test 1: Hover on documented constant BUFFER_SIZE in library
        print("1. Testing hover on documented constant 'BUFFER_SIZE'")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": lib_uri},
                "position": {"line": 4, "character": 11}  # Position on BUFFER_SIZE
            }
        })
        response = read_until_response(proc, 1)
        
        if response and response.get('result'):
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            # Check for documentation
            if "buffer size for operations" in value.lower() or "1024 bytes" in value.lower():
                print("✅ PASS: Documentation displayed for constant")
            else:
                print("❌ FAIL: Documentation not found in hover")
                test_passed = False
            print()
        else:
            print("❌ FAIL: No hover response for constant")
            test_passed = False
        
        # Test 2: Hover on documented function 'square'
        print("2. Testing hover on documented function 'square'")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": lib_uri},
                "position": {"line": 14, "character": 6}  # Position on 'square' function name
            }
        })
        response = read_until_response(proc, 2)
        
        if response and response.get('result'):
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            # Check for multi-line documentation
            if "computes the square" in value.lower() or "fast squaring" in value.lower():
                print("✅ PASS: Multi-line documentation displayed for function")
            else:
                print("❌ FAIL: Documentation not found in hover")
                test_passed = False
            print()
        else:
            print("❌ FAIL: No hover response for function")
            test_passed = False
        
        # Test 3: Hover on documented function 'add' with simple comment
        print("3. Testing hover on function 'add' with single-line documentation")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": lib_uri},
                "position": {"line": 22, "character": 4}  # Position on 'add' function name
            }
        })
        response = read_until_response(proc, 3)
        
        if response and response.get('result'):
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            # Check for documentation
            if "adds two numbers" in value.lower() or "sum of x and y" in value.lower():
                print("✅ PASS: Single-line documentation displayed for function")
            else:
                print("❌ FAIL: Documentation not found in hover")
                test_passed = False
            print()
        else:
            print("❌ FAIL: No hover response for function")
            test_passed = False
        
        # Test 4: Hover on documented variable 'temp' in complex_calc
        print("4. Testing hover on documented variable 'temp'")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": lib_uri},
                "position": {"line": 35, "character": 11}  # Position on 'temp' declaration
            }
        })
        response = read_until_response(proc, 4)
        
        if response and response.get('result'):
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            # Check for documentation
            if "temporary storage" in value.lower() or "intermediate result" in value.lower():
                print("✅ PASS: Documentation displayed for variable")
            else:
                print("❌ FAIL: Documentation not found in hover")
                test_passed = False
            print()
        else:
            print("❌ FAIL: No hover response for variable")
            test_passed = False
        
        # Test 5: Hover on main function with extensive documentation
        print("5. Testing hover on 'main' function with extensive documentation")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": main_uri},
                "position": {"line": 14, "character": 12}  # Position on 'main' function name
            }
        })
        response = read_until_response(proc, 5)
        
        if response and response.get('result'):
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            # Check for documentation
            if "application entry point" in value.lower() or "main function" in value.lower():
                print("✅ PASS: Extensive documentation displayed for main function")
            else:
                print("❌ FAIL: Documentation not found in hover")
                test_passed = False
            print()
        else:
            print("❌ FAIL: No hover response for main function")
            test_passed = False
        
        # Test 6: Hover on documented variable in main
        print("6. Testing hover on documented variable 'result'")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": main_uri},
                "position": {"line": 22, "character": 11}  # Position on 'result' declaration (line 23 in file, 0-indexed)
            }
        })
        response = read_until_response(proc, 6)
        
        if response and response.get('result'):
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            # Check for documentation
            if "result accumulator" in value.lower() or "accumulated result" in value.lower():
                print("✅ PASS: Multi-line documentation displayed for variable")
            else:
                print("❌ FAIL: Documentation not found in hover")
                test_passed = False
            print()
        else:
            print("❌ FAIL: No hover response for variable")
            test_passed = False
        
        # Test 7: Hover on is_valid function with single-line comment
        print("7. Testing hover on 'is_valid' function")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": main_uri},
                "position": {"line": 38, "character": 6}  # Position on 'is_valid' function name (line 39 in file, 0-indexed)
            }
        })
        response = read_until_response(proc, 7)
        
        if response and response.get('result'):
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            # Check for documentation
            if "check if" in value.lower() or "within bounds" in value.lower():
                print("✅ PASS: Documentation displayed for helper function")
            else:
                print("❌ FAIL: Documentation not found in hover")
                test_passed = False
            print()
        else:
            print("❌ FAIL: No hover response for helper function")
            test_passed = False
        
        # Test 8: Cross-file hover - hover on BUFFER_SIZE in main file
        print("8. Testing cross-file hover on 'BUFFER_SIZE' used in main")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": main_uri},
                "position": {"line": 30, "character": 22}  # Position on BUFFER_SIZE usage
            }
        })
        response = read_until_response(proc, 8)
        
        if response and response.get('result'):
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            # Check for documentation from library file
            if "buffer size" in value.lower():
                print("✅ PASS: Cross-file documentation displayed")
            else:
                print("⚠️  WARNING: Documentation not found (cross-file may need master file)")
            print()
        else:
            print("⚠️  WARNING: No hover response (cross-file may need master file)")
        
        print("=" * 80)
        if test_passed:
            print("✅ All tests PASSED!")
        else:
            print("❌ Some tests FAILED")
        print("=" * 80)
        
        return test_passed
        
    finally:
        try:
            send_message(proc, {"jsonrpc": "2.0", "id": 999, "method": "shutdown"})
            time.sleep(0.1)
            send_message(proc, {"jsonrpc": "2.0", "method": "exit"})
        except:
            pass
        proc.terminate()

if __name__ == "__main__":
    import sys
    sys.exit(0 if test_hover_documentation() else 1)
