#!/usr/bin/env python3
"""Test that parameters don't get wrong documentation from nearby functions."""

import subprocess
import json
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

server_path = "./_build/default/jasmin-lsp/jasmin_lsp.exe"
test_file = Path(__file__).parent.parent / "fixtures" / "param_doc_test.jazz"
content = test_file.read_text()
uri = f"file://{test_file.absolute()}"

proc = subprocess.Popen([server_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    # Initialize
    send_message(proc, {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {"processId": None, "rootUri": f"file://{Path.cwd()}", "capabilities": {}}
    })
    read_until_response(proc, 0)
    send_message(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
    time.sleep(0.1)
    
    # Open document
    send_message(proc, {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {"uri": uri, "languageId": "jasmin", "version": 1, "text": content}
        }
    })
    time.sleep(0.2)
    
    print("=" * 60)
    print("Test 1: Hover on parameter 'a' in _cddq (line 11)")
    print("Expected: Should NOT show _caddq's documentation")
    print("=" * 60)
    
    # Hover on parameter 'a' in _cddq function (line 11 is "fn _cddq(reg u32 a)")
    send_message(proc, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": uri},
            "position": {"line": 10, "character": 17}  # Line 10 in 0-indexed, position of 'a' parameter
        }
    })
    response = read_until_response(proc, 1)
    
    if response and response.get('result'):
        value = response['result']['contents']['value']
        print("\nHover content:")
        print(value)
        print()
        
        # Check if it incorrectly contains _caddq's documentation
        if "_caddq" in value or "comment for _caddq" in value:
            print("❌ FAIL: Parameter 'a' incorrectly shows _caddq's documentation!")
            success = False
        elif "---" in value:
            print("❌ FAIL: Parameter 'a' has documentation section (should have none)!")
            success = False
        else:
            print("✅ PASS: Parameter 'a' has no documentation (correct!)")
            success = True
    else:
        print("❌ FAIL: No hover response")
        success = False
    
    print()
    print("=" * 60)
    print("Test 2: Hover on parameter 'value' in main_function (line 19)")
    print("Expected: Should NOT show any documentation")
    print("=" * 60)
    
    # Hover on parameter 'value' in main_function
    send_message(proc, {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": uri},
            "position": {"line": 19, "character": 27}  # Position of 'value' parameter
        }
    })
    response = read_until_response(proc, 2)
    
    if response and response.get('result'):
        value = response['result']['contents']['value']
        print("\nHover content:")
        print(value)
        print()
        
        if "---" in value:
            print("❌ FAIL: Parameter 'value' has documentation section (should have none)!")
            success = False
        else:
            print("✅ PASS: Parameter 'value' has no documentation (correct!)")
    else:
        print("❌ FAIL: No hover response")
        success = False
    
    print()
    print("=" * 60)
    print("Test 3: Hover on function name 'main_function' (line 19)")
    print("Expected: SHOULD show the function's documentation")
    print("=" * 60)
    
    # Hover on function name
    send_message(proc, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": uri},
            "position": {"line": 19, "character": 3}  # Position of function name
        }
    })
    response = read_until_response(proc, 3)
    
    if response and response.get('result'):
        value = response['result']['contents']['value']
        print("\nHover content:")
        print(value)
        print()
        
        if "Documentation for main_function" in value:
            print("✅ PASS: Function shows its documentation correctly!")
        else:
            print("❌ FAIL: Function documentation not found!")
            success = False
    else:
        print("❌ FAIL: No hover response")
        success = False
    
    if success:
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✅")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("SOME TESTS FAILED! ❌")
        print("=" * 60)
        
finally:
    proc.terminate()
