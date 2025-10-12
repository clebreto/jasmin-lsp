#!/usr/bin/env python3
"""
Test hover functionality across multiple files.
Tests that symbols from required files can be hovered over correctly.
"""

import json
import subprocess
import os
import tempfile
import time
from pathlib import Path

# Server path - use absolute path from project root
LSP_SERVER = Path(__file__).parent.parent.parent / "_build/default/jasmin-lsp/jasmin_lsp.exe"

def create_test_files():
    """Create test files for cross-file hover testing."""
    test_dir = Path("test_hover_files")
    test_dir.mkdir(exist_ok=True)
    
    # Create lib directory
    lib_dir = test_dir / "lib"
    lib_dir.mkdir(exist_ok=True)
    
    # Create lib/types.jinc with variable declarations
    types_content = """// Type definitions and variables
param int SIZE = 8;

fn add_one(reg u64 x) -> reg u64 {
    reg u64 result;
    result = x + 1;
    return result;
}

fn multiply(reg u64 a, reg u64 b) -> reg u64 {
    reg u64 result;
    result = a * b;
    return result;
}
"""
    (lib_dir / "types.jinc").write_text(types_content)
    
    # Create lib/utils.jinc with more variables
    utils_content = """// Utility functions
require "types.jinc";

fn process(reg u64 value) -> reg u64 {
    reg u64 temp;
    reg u64 output;
    
    temp = add_one(value);
    output = multiply(temp, SIZE);
    
    return output;
}
"""
    (lib_dir / "utils.jinc").write_text(utils_content)
    
    # Create main.jazz that requires both files
    main_content = """// Main file
require "lib/types.jinc";
require "lib/utils.jinc";

export fn main() -> reg u64 {
    reg u64 x;
    reg u64 y;
    
    x = 5;
    y = process(x);
    
    return y;
}
"""
    (test_dir / "main.jazz").write_text(main_content)
    
    return test_dir

def send_request(proc, request):
    """Send a request to the LSP server."""
    request_str = json.dumps(request)
    content_length = len(request_str.encode('utf-8'))
    
    message = f"Content-Length: {content_length}\r\n\r\n{request_str}"
    proc.stdin.write(message.encode('utf-8'))
    proc.stdin.flush()

def read_response(proc):
    """Read a response from the LSP server."""
    # Read headers
    headers = {}
    while True:
        line = proc.stdout.readline().decode('utf-8')
        if line == '\r\n':
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    # Read content
    content_length = int(headers.get('Content-Length', 0))
    content = proc.stdout.read(content_length).decode('utf-8')
    return json.loads(content)

def test_cross_file_hover():
    """Test hover on variables defined in required files."""
    print("=" * 80)
    print("Testing Cross-File Hover with Master File")
    print("=" * 80)
    
    # Create test files
    test_dir = create_test_files()
    print(f"\n✓ Created test files in {test_dir}")
    
    # Start LSP server
    proc = subprocess.Popen(
        [LSP_SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )
    
    try:
        # Initialize
        print("\n1. Initializing LSP server...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": f"file://{os.getcwd()}/{test_dir}",
                "capabilities": {}
            }
        })
        
        response = read_response(proc)
        print(f"   Initialize response: {response.get('result', {}).get('capabilities', {}).get('hoverProvider', 'N/A')}")
        
        # Send initialized notification
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        })
        
        # Open main.jazz
        print("\n2. Opening main.jazz...")
        main_path = test_dir / "main.jazz"
        main_uri = f"file://{main_path.absolute()}"
        main_content = main_path.read_text()
        
        send_request(proc, {
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
        
        # Set master file
        print(f"\n3. Setting master file to: {main_uri}")
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "jasmin/setMasterFile",
            "params": {
                "uri": main_uri
            }
        })
        
        # Give server time to process
        import time
        time.sleep(0.5)
        
        # Test 1: Hover on 'process' function (defined in lib/utils.jinc)
        print("\n4. Testing hover on 'process' function...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": main_uri},
                "position": {"line": 8, "character": 9}  # Position of 'process' in main.jazz
            }
        })
        
        response = read_response(proc)
        hover_content = None
        if response.get('result'):
            contents = response['result'].get('contents', {})
            if isinstance(contents, dict) and 'value' in contents:
                hover_content = contents['value']
            print(f"   ✓ Hover on 'process': {hover_content}")
        else:
            print(f"   ✗ No hover information for 'process'")
            print(f"   Response: {response}")
        
        # Test 2: Hover on 'add_one' function (defined in lib/types.jinc)
        print("\n5. Testing hover on 'add_one' function (from types.jinc)...")
        
        # First open lib/utils.jinc
        utils_path = test_dir / "lib" / "utils.jinc"
        utils_uri = f"file://{utils_path.absolute()}"
        utils_content = utils_path.read_text()
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": utils_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": utils_content
                }
            }
        })
        
        time.sleep(0.3)
        
        # Hover on 'add_one' in utils.jinc
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": utils_uri},
                "position": {"line": 7, "character": 11}  # Position of 'add_one' in utils.jinc
            }
        })
        
        response = read_response(proc)
        hover_content = None
        if response.get('result'):
            contents = response['result'].get('contents', {})
            if isinstance(contents, dict) and 'value' in contents:
                hover_content = contents['value']
            print(f"   ✓ Hover on 'add_one': {hover_content}")
        else:
            print(f"   ✗ No hover information for 'add_one'")
            print(f"   Response: {response}")
        
        # Test 3: Hover on 'SIZE' constant (defined in lib/types.jinc)
        print("\n6. Testing hover on 'SIZE' constant...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": utils_uri},
                "position": {"line": 8, "character": 28}  # Position of 'SIZE' in utils.jinc
            }
        })
        
        response = read_response(proc)
        hover_content = None
        if response.get('result'):
            contents = response['result'].get('contents', {})
            if isinstance(contents, dict) and 'value' in contents:
                hover_content = contents['value']
            print(f"   ✓ Hover on 'SIZE': {hover_content}")
            
            # Verify constant value is computed
            if "= 8" in hover_content:
                print(f"   ✓ Constant value computed correctly!")
            else:
                print(f"   ⚠ Constant value not shown or incorrect")
        else:
            print(f"   ✗ No hover information for 'SIZE'")
            print(f"   Response: {response}")
        
        # Test 4: Hover on local variable 'temp' in utils.jinc
        print("\n7. Testing hover on local variable 'temp'...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": utils_uri},
                "position": {"line": 7, "character": 5}  # Position of 'temp' assignment
            }
        })
        
        response = read_response(proc)
        hover_content = None
        if response.get('result'):
            contents = response['result'].get('contents', {})
            if isinstance(contents, dict) and 'value' in contents:
                hover_content = contents['value']
            print(f"   ✓ Hover on 'temp': {hover_content}")
        else:
            print(f"   ✗ No hover information for 'temp'")
            print(f"   Response: {response}")
        
        print("\n" + "=" * 80)
        print("Test completed!")
        print("=" * 80)
        
        # Shutdown
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 999,
            "method": "shutdown",
            "params": {}
        })
        
        read_response(proc)
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "exit",
            "params": {}
        })
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)

if __name__ == "__main__":
    test_cross_file_hover()
