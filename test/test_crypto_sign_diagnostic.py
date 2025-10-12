#!/usr/bin/env python3
"""
Diagnostic test for finding _crypto_sign_signature_ctx_seed in ml_dsa.jazz

This test specifically checks why the symbol cannot be found.
"""

import json
import subprocess
import os
import sys
from pathlib import Path

LSP_SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

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

def find_symbol_in_file(filepath, symbol_name):
    """Search for a symbol in a file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if symbol_name in content:
                for i, line in enumerate(content.split('\n'), 1):
                    if symbol_name in line:
                        return i, line.strip()
    except:
        pass
    return None, None

def test_crypto_sign_hover():
    """Test why _crypto_sign_signature_ctx_seed cannot be found."""
    print("=" * 80)
    print("Diagnostic: Finding _crypto_sign_signature_ctx_seed in ml_dsa.jazz")
    print("=" * 80)
    
    # Check if formosa-mldsa exists
    mldsa_base = Path("/Users/clebreto/dev/splits/formosa-mldsa/x86-64/avx2/ml_dsa_65")
    if not mldsa_base.exists():
        print(f"\n❌ formosa-mldsa directory not found: {mldsa_base}")
        print("Please clone it: git clone https://github.com/formosa-crypto/formosa-mldsa.git")
        return False
    
    ml_dsa_path = mldsa_base / "ml_dsa.jazz"
    if not ml_dsa_path.exists():
        print(f"\n❌ ml_dsa.jazz not found: {ml_dsa_path}")
        return False
    
    print(f"\n✓ Found ml_dsa.jazz at: {ml_dsa_path}")
    
    # Step 1: Find where _crypto_sign_signature_ctx_seed is defined
    print("\n" + "="*80)
    print("Step 1: Searching for _crypto_sign_signature_ctx_seed definition")
    print("="*80)
    
    symbol_name = "_crypto_sign_signature_ctx_seed"
    found_in = []
    
    # Search in all .jazz and .jinc files
    for ext in ['*.jazz', '*.jinc']:
        for filepath in mldsa_base.rglob(ext):
            line_num, line_content = find_symbol_in_file(filepath, symbol_name)
            if line_num:
                rel_path = filepath.relative_to(mldsa_base)
                found_in.append((rel_path, line_num, line_content))
                print(f"\n  Found in: {rel_path}")
                print(f"  Line {line_num}: {line_content}")
    
    if not found_in:
        print(f"\n❌ Symbol '{symbol_name}' not found in any file!")
        print("Searching with partial match...")
        
        # Try partial matches
        partial_name = "crypto_sign"
        for ext in ['*.jazz', '*.jinc']:
            for filepath in mldsa_base.rglob(ext):
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        if partial_name in content and 'fn ' in content:
                            rel_path = filepath.relative_to(mldsa_base)
                            # Find function definitions
                            for i, line in enumerate(content.split('\n'), 1):
                                if 'fn ' in line and partial_name in line:
                                    print(f"\n  Found function in: {rel_path}")
                                    print(f"  Line {i}: {line.strip()}")
                except:
                    pass
        return False
    
    # Step 2: Check the dependency chain from ml_dsa.jazz
    print("\n" + "="*80)
    print("Step 2: Analyzing dependency chain from ml_dsa.jazz")
    print("="*80)
    
    with open(ml_dsa_path, 'r') as f:
        ml_dsa_content = f.read()
    
    print("\nRequire statements in ml_dsa.jazz:")
    for i, line in enumerate(ml_dsa_content.split('\n'), 1):
        if 'require' in line.lower() and not line.strip().startswith('//'):
            print(f"  Line {i}: {line.strip()}")
    
    # Check if the file containing the symbol is directly or transitively required
    target_file = found_in[0][0]  # First file where symbol was found
    print(f"\nTarget file: {target_file}")
    print(f"Need to check if ml_dsa.jazz requires this file (directly or transitively)")
    
    # Step 3: Test with LSP
    print("\n" + "="*80)
    print("Step 3: Testing with LSP server")
    print("="*80)
    
    if not os.path.exists(LSP_SERVER):
        print(f"\n❌ LSP server not found: {LSP_SERVER}")
        print("Please build it: dune build")
        return False
    
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
        
        # Consume diagnostics
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
        
        # Try to hover on the symbol if it appears in ml_dsa.jazz
        print(f"\n🔍 Searching for '{symbol_name}' usage in ml_dsa.jazz...")
        symbol_line = None
        for i, line in enumerate(ml_dsa_content.split('\n')):
            if symbol_name in line and not line.strip().startswith('//'):
                symbol_line = i
                print(f"  Found at line {i+1}: {line.strip()}")
                break
        
        if symbol_line is not None:
            # Find position in line
            char_pos = ml_dsa_content.split('\n')[symbol_line].index(symbol_name)
            
            print(f"\n💬 Requesting hover at line {symbol_line+1}, char {char_pos}...")
            send_request(proc, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": ml_dsa_uri},
                    "position": {"line": symbol_line, "character": char_pos + 5}
                }
            })
            
            response = read_response(proc)
            if response.get('result'):
                contents = response['result'].get('contents', {})
                if isinstance(contents, dict) and 'value' in contents:
                    print(f"\n✅ SUCCESS! Hover returned:")
                    print(f"  {contents['value']}")
                else:
                    print(f"\n✅ Hover returned (raw): {contents}")
            else:
                print(f"\n❌ FAILED! No hover information")
                print(f"  Response: {response}")
                
                # Additional diagnostics
                print(f"\n🔍 Let's check what files the LSP loaded...")
                print(f"  Expected to find: {target_file}")
        else:
            print(f"\n⚠️  Symbol '{symbol_name}' not used in ml_dsa.jazz directly")
            print("  Try opening the file where it's defined and hovering there")
        
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
    
    return True

if __name__ == "__main__":
    success = test_crypto_sign_hover()
    sys.exit(0 if success else 1)
