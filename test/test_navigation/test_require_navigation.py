#!/usr/bin/env python3
"""
Test script to verify that goto definition works on require statements.
When clicking on "math_lib.jazz" in the require statement, it should jump to that file.
"""

import json
import subprocess
import sys
import os

GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

def send_lsp(server_path, messages):
    """Send messages to LSP server and get response"""
    input_data = ""
    for msg in messages:
        content = json.dumps(msg)
        input_data += f"Content-Length: {len(content)}\r\n\r\n{content}"
    
    try:
        result = subprocess.run(
            [server_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return ""

def main():
    server_path = '_build/default/jasmin-lsp/jasmin_lsp.exe'
    
    if not os.path.exists(server_path):
        print(f"{RED}Error: LSP server not found at {server_path}{NC}")
        return 1
    
    main_file = 'test/fixtures/main_program.jazz'
    lib_file = 'test/fixtures/math_lib.jazz'
    
    if not os.path.exists(main_file) or not os.path.exists(lib_file):
        print(f"{RED}Error: Test files not found{NC}")
        return 1
    
    with open(main_file) as f:
        main_content = f.read()
    
    main_uri = f"file://{os.path.abspath(main_file)}"
    lib_uri = f"file://{os.path.abspath(lib_file)}"
    workspace_uri = f"file://{os.path.abspath('test/fixtures')}"
    
    print("="*60)
    print("Testing: Goto Definition on require Statement")
    print("="*60)
    print(f"Main file: {main_file}")
    print(f"Expected target: {lib_file}")
    print()
    
    # Find the position of the require statement
    lines = main_content.split('\n')
    require_line = -1
    require_char = -1
    
    for i, line in enumerate(lines):
        if 'require' in line and 'math_lib.jazz' in line:
            require_line = i
            # Position cursor in the middle of "math_lib.jazz"
            require_char = line.index('math_lib.jazz') + 5
            break
    
    if require_line == -1:
        print(f"{RED}Error: Could not find require statement in main_program.jazz{NC}")
        return 1
    
    print(f"Found require statement at line {require_line}, char {require_char}")
    print(f"Line content: {lines[require_line]}")
    print()
    
    messages = [
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {
                'processId': None,
                'rootUri': workspace_uri,
                'capabilities': {}
            }
        },
        {
            'jsonrpc': '2.0',
            'method': 'initialized',
            'params': {}
        },
        {
            'jsonrpc': '2.0',
            'method': 'textDocument/didOpen',
            'params': {
                'textDocument': {
                    'uri': main_uri,
                    'languageId': 'jasmin',
                    'version': 1,
                    'text': main_content
                }
            }
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'textDocument/definition',
            'params': {
                'textDocument': {'uri': main_uri},
                'position': {'line': require_line, 'character': require_char}
            }
        }
    ]
    
    print("Sending LSP requests...")
    output = send_lsp(server_path, messages)
    
    # Parse output to find the definition response
    success = False
    
    if '"id":2' in output and '"result"' in output:
        print(f"{GREEN}✓{NC} Got response from LSP")
        
        if 'math_lib.jazz' in output:
            print(f"{GREEN}✓{NC} Response points to math_lib.jazz")
            success = True
        else:
            print(f"{YELLOW}?{NC} Response doesn't explicitly mention math_lib.jazz")
            # Still might be success if it has a URI
            if '"uri"' in output:
                print(f"{YELLOW}?{NC} But response contains a URI")
                print("Output snippet:", output[output.find('"id":2'):output.find('"id":2')+200])
    else:
        print(f"{RED}✗{NC} No valid response from LSP")
        print("Output:", output[:500])
    
    print()
    print("="*60)
    if success:
        print(f"{GREEN}TEST PASSED: Require file navigation works!{NC}")
        return 0
    else:
        print(f"{RED}TEST FAILED: Require file navigation not working{NC}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
