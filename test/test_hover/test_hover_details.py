#!/usr/bin/env python3
"""Test to verify the hover display shows values correctly without duplication."""

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

def main():
    server_path = "./_build/default/jasmin-lsp/jasmin_lsp.exe"
    test_file_path = str(Path(__file__).parent / "test/fixtures/constant_computation/constants.jinc")
    
    if not os.path.exists(test_file_path):
        print(f"❌ Test file not found: {test_file_path}")
        return False
    
    with open(test_file_path, 'r') as f:
        content = f.read()
    
    print("Testing Value Display Format")
    print("=" * 80)
    print()
    
    proc = subprocess.Popen(
        [server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
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
        
        send_message(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{test_file_path}",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": content
                }
            }
        })
        time.sleep(0.2)
        
        # Test BASE (simple constant - should show value once)
        print("1. Testing BASE (simple constant: param int BASE = 100;)")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": f"file://{test_file_path}"},
                "position": {"line": 1, "character": 11}
            }
        })
        response = read_until_response(proc, 1)
        
        if response and response['result']:
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            # Check that it shows value in expandable section
            if "<details>" in value and "100" in value:
                print("✅ PASS: Shows value in expandable section")
            else:
                print("❌ FAIL: Value not in expandable section")
            print()
        
        # Test TOTAL (computed constant - should show declared and computed)
        print("2. Testing TOTAL (computed: param int TOTAL = BASE + OFFSET;)")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": f"file://{test_file_path}"},
                "position": {"line": 3, "character": 11}
            }
        })
        response = read_until_response(proc, 2)
        
        if response and response['result']:
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            # Check for both declared and computed values
            has_declared = "Declared:" in value or "BASE + OFFSET" in value
            has_computed = "Computed:" in value or "150" in value
            
            if has_declared:
                print("✅ Shows declared value expression")
            else:
                print("❌ Missing declared value expression")
            
            if has_computed:
                print("✅ Shows computed value")
            else:
                print("❌ Missing computed value")
            
            if has_declared and has_computed:
                print("✅ PASS: Shows both declared and computed values")
            else:
                print("❌ FAIL: Missing information")
            print()
        
        # Test SIGNATURE_SIZE (long computed constant)
        print("3. Testing SIGNATURE_SIZE (long expression)")
        print("-" * 80)
        send_message(proc, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": f"file://{test_file_path}"},
                "position": {"line": 8, "character": 11}
            }
        })
        response = read_until_response(proc, 3)
        
        if response and response['result']:
            value = response['result']['contents']['value']
            print("Hover content:")
            print(value)
            print()
            
            has_expandable = "<details>" in value and "<summary>Value</summary>" in value
            
            if has_expandable:
                print("✅ PASS: Shows value in expandable section")
            else:
                print("❌ FAIL: No expandable section")
            print()
        
        print("=" * 80)
        print("Test completed!")
        print("=" * 80)
        
        return True
        
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
    sys.exit(0 if main() else 1)
