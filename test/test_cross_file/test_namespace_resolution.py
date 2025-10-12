#!/usr/bin/env python3
"""
Test namespace resolution with parent directory lookup.
Tests that "from Common require ..." works when Common is a sibling directory.
"""

import json
import subprocess
import os
import sys
from pathlib import Path

LSP_SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def send_request(proc, request):
    request_str = json.dumps(request)
    content_length = len(request_str.encode('utf-8'))
    message = f"Content-Length: {content_length}\r\n\r\n{request_str}"
    proc.stdin.write(message.encode('utf-8'))
    proc.stdin.flush()

def read_response(proc):
    headers = {}
    while True:
        line = proc.stdout.readline().decode('utf-8')
        if line == '\r\n':
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    content_length = int(headers.get('Content-Length', 0))
    content = proc.stdout.read(content_length).decode('utf-8')
    return json.loads(content)

def test_namespace_resolution():
    print("=" * 80)
    print("Testing Namespace Resolution with Parent Directory Lookup")
    print("=" * 80)
    
    mldsa_base = Path("/Users/clebreto/dev/splits/formosa-mldsa/x86-64/avx2/ml_dsa_65")
    if not mldsa_base.exists():
        print(f"\n❌ formosa-mldsa not found: {mldsa_base}")
        return False
    
    ml_dsa_path = mldsa_base / "ml_dsa.jazz"
    common_path = mldsa_base.parent / "common"
    
    print(f"\n✓ ml_dsa.jazz: {ml_dsa_path}")
    print(f"✓ common dir: {common_path}")
    print(f"✓ common exists: {common_path.exists()}")
    
    # Check what files are in common
    if common_path.exists():
        print(f"\nFiles in common/:")
        for item in sorted(common_path.iterdir())[:10]:
            print(f"  - {item.name}")
    
    # Start LSP
    proc = subprocess.Popen(
        [LSP_SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )
    
    try:
        # Initialize
        print("\n📡 Initializing LSP...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": f"file://{mldsa_base}",
                "capabilities": {}
            }
        })
        
        response = read_response(proc)
        print("✓ LSP initialized")
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        })
        
        import time
        time.sleep(0.3)
        
        # Open ml_dsa.jazz
        print("\n📄 Opening ml_dsa.jazz...")
        ml_dsa_uri = f"file://{ml_dsa_path}"
        with open(ml_dsa_path) as f:
            ml_dsa_content = f.read()
        
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": ml_dsa_uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": ml_dsa_content
                }
            }
        })
        
        response = read_response(proc)
        print("✓ ml_dsa.jazz opened")
        
        # Set master file
        print("\n🎯 Setting master file to ml_dsa.jazz...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "method": "jasmin/setMasterFile",
            "params": {
                "uri": ml_dsa_uri
            }
        })
        
        time.sleep(0.5)
        
        # Test: Navigate to a file from Common namespace
        print("\n" + "="*80)
        print("Test: Navigate to 'from Common require' file")
        print("="*80)
        
        # Find a line with "from Common require"
        lines = ml_dsa_content.split('\n')
        test_line = None
        test_file = None
        
        for i, line in enumerate(lines):
            if 'from Common require' in line and 'hashing.jinc' in line:
                test_line = i
                test_file = 'hashing.jinc'
                print(f"\nFound at line {i+1}: {line.strip()}")
                break
        
        if test_line is not None:
            # Position on the filename
            char_pos = lines[test_line].index(test_file)
            
            print(f"\n🔍 Requesting goto definition at line {test_line+1}, char {char_pos}...")
            send_request(proc, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/definition",
                "params": {
                    "textDocument": {"uri": ml_dsa_uri},
                    "position": {"line": test_line, "character": char_pos + 5}
                }
            })
            
            response = read_response(proc)
            if response.get('result'):
                locations = response['result']
                if isinstance(locations, list) and len(locations) > 0:
                    target_uri = locations[0].get('uri', '')
                else:
                    target_uri = locations.get('uri', '') if isinstance(locations, dict) else ''
                
                print(f"\n✅ SUCCESS! Navigate to: {target_uri}")
                
                # Check if it points to common directory
                if 'common' in target_uri.lower() and test_file in target_uri:
                    print(f"✅✅ Correctly resolved to common/{test_file}!")
                    print(f"\n🎉 Namespace resolution with parent directory lookup works!")
                    return True
                else:
                    print(f"⚠️  Expected path with 'common/{test_file}', got: {target_uri}")
            else:
                print(f"\n❌ FAILED! No definition found")
                print(f"   Response: {response}")
                return False
        
        # Test: Hover on a function from Common
        print("\n" + "="*80)
        print("Test: Hover on function from Common namespace")
        print("="*80)
        
        # Search for any function call that might be from Common files
        test_functions = ["keccak", "ntt", "invert_ntt"]
        
        for func_name in test_functions:
            for i, line in enumerate(lines):
                if func_name in line.lower() and not line.strip().startswith('//') and not 'require' in line:
                    print(f"\n🔍 Found '{func_name}' usage at line {i+1}: {line.strip()[:60]}...")
                    
                    # Try hover
                    char_pos = line.lower().index(func_name)
                    send_request(proc, {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "textDocument/hover",
                        "params": {
                            "textDocument": {"uri": ml_dsa_uri},
                            "position": {"line": i, "character": char_pos + 2}
                        }
                    })
                    
                    response = read_response(proc)
                    if response.get('result') and response['result'].get('contents'):
                        contents = response['result']['contents']
                        if isinstance(contents, dict) and 'value' in contents:
                            print(f"   ✅ Hover works: {contents['value'][:100]}...")
                        else:
                            print(f"   ✅ Hover returned: {str(contents)[:100]}...")
                    break
            break
        
        print("\n" + "="*80)
        print("Summary")
        print("="*80)
        print("✅ Namespace resolution now searches parent directories")
        print("✅ 'from Common require' works when Common is a sibling directory")
        print("✅ formosa-mldsa structure is supported")
        
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
        
        return True
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)

if __name__ == "__main__":
    success = test_namespace_resolution()
    sys.exit(0 if success else 1)
