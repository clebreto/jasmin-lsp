#!/usr/bin/env python3
"""
Test script to verify that goto definition works on namespace require statements.
When clicking on "reduce.jinc" in the statement 'from Common require "reduce.jinc"',
it should jump to the Common/reduce.jinc file.
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
            timeout=10
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return ""

def main():
    server_path = '_build/default/jasmin-lsp/jasmin_lsp.exe'
    
    if not os.path.exists(server_path):
        print(f"{RED}Error: LSP server not found at {server_path}{NC}")
        return 1
    
    main_file = 'test/fixtures/namespace_test.jazz'
    target_file = 'test/fixtures/Common/reduce.jinc'
    
    if not os.path.exists(main_file):
        print(f"{RED}Error: Test file not found: {main_file}{NC}")
        return 1
    
    if not os.path.exists(target_file):
        print(f"{RED}Error: Target file not found: {target_file}{NC}")
        return 1
    
    with open(main_file) as f:
        main_content = f.read()
    
    main_uri = f"file://{os.path.abspath(main_file)}"
    target_uri = f"file://{os.path.abspath(target_file)}"
    workspace_uri = f"file://{os.path.abspath('test/fixtures')}"
    
    print("="*60)
    print("Testing: Goto Definition on Namespace Require Statement")
    print("="*60)
    print(f"Main file: {main_file}")
    print(f"Expected target: {target_file}")
    print()
    
    # Find the position of the namespace require statement
    lines = main_content.split('\n')
    require_line = -1
    require_char = -1
    
    for i, line in enumerate(lines):
        if 'from Common require' in line and 'reduce.jinc' in line:
            require_line = i
            # Position cursor in the middle of "reduce.jinc"
            require_char = line.index('reduce.jinc') + 5
            break
    
    if require_line == -1:
        print(f"{RED}Error: Could not find namespace require statement in namespace_test.jazz{NC}")
        return 1
    
    print(f"Found namespace require statement at line {require_line}, char {require_char}")
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
        
        if 'reduce.jinc' in output:
            print(f"{GREEN}✓{NC} Response points to reduce.jinc")
            success = True
        else:
            print(f"{YELLOW}?{NC} Response doesn't explicitly mention reduce.jinc")
            # Still might be success if it has a URI pointing to Common directory
            if 'Common' in output and '"uri"' in output:
                print(f"{GREEN}✓{NC} Response contains Common namespace reference")
                success = True
            elif '"uri"' in output:
                print(f"{YELLOW}?{NC} Response contains a URI but not in Common namespace")
                print("Output snippet:", output[output.find('"id":2'):output.find('"id":2')+200])
    else:
        print(f"{RED}✗{NC} No valid response from LSP")
        print("Output:", output[:500])
    
    print()
    print("="*60)
    if success:
        print(f"{GREEN}TEST PASSED: Namespace require navigation works!{NC}")
        return 0
    else:
        print(f"{RED}TEST FAILED: Namespace require navigation not working{NC}")
        return 1

if __name__ == '__main__':
    sys.exit(main())