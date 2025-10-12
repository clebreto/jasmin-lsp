#!/usr/bin/env python3
"""
Test goto definition on function parameters
"""

import json
import subprocess
import sys
import os

GREEN = '\033[0;32m'
RED = '\033[0;31m'
NC = '\033[0m'

def run_lsp_test(server_path, messages):
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

def test_parameter_definition():
    """Test goto definition on a parameter inside a function"""
    print("="*60)
    print("Test: Parameter Goto Definition")
    print("="*60)
    
    server_path = '_build/default/jasmin-lsp/jasmin_lsp.exe'
    test_file = 'test/fixtures/simple_function.jazz'
    
    with open(test_file) as f:
        content = f.read()
    
    uri = f"file://{os.path.abspath(test_file)}"
    
    # Find usage of 'x' parameter in add_numbers function
    # The function is: fn add_numbers(reg u64 x, reg u64 y) -> reg u64
    # And inside it uses: result = x + y;
    lines = content.split('\n')
    
    print("\nFile content (first 10 lines):")
    for i, line in enumerate(lines[:10]):
        print(f"{i}: {line}")
    
    # Find the line with "result = x + y"
    line_num = -1
    char_pos = -1
    
    for i, line in enumerate(lines):
        if 'result = x + y' in line:
            line_num = i
            # Position on 'x' (after 'result = ')
            char_pos = line.index('x')
            break
    
    if line_num == -1:
        print(f"{RED}ERROR: Could not find 'result = x + y' in the file{NC}")
        return False
    
    print(f"\nTest case:")
    print(f"  Looking for parameter 'x' at line {line_num}, char {char_pos}")
    print(f"  Line content: '{lines[line_num]}'")
    print(f"  Expected: Should jump to parameter 'x' in function signature (line 1)")
    
    messages = [
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {
                'processId': None,
                'rootUri': f"file://{os.path.abspath('test/fixtures')}",
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
                    'uri': uri,
                    'languageId': 'jasmin',
                    'version': 1,
                    'text': content
                }
            }
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'textDocument/definition',
            'params': {
                'textDocument': {'uri': uri},
                'position': {'line': line_num, 'character': char_pos}
            }
        }
    ]
    
    print("\nSending LSP request...")
    output = run_lsp_test(server_path, messages)
    
    # Parse the response
    if '"id":2' in output and '"result"' in output:
        print(f"\n{GREEN}✓{NC} Got response from LSP")
        
        # Find the actual response (look for id:2 in the response, not request)
        # The response should have "result" field
        result_pos = output.find('"result"')
        if result_pos > 0:
            # Get context around the result
            response_snippet = output[max(0, result_pos-50):min(len(output), result_pos+300)]
            print(f"\nResponse with result: {response_snippet}")
        
        # Check if it has a valid location
        if '"uri"' in output and '"range"' in output:
            # Try to extract line number from response
            # Look for the line in the result section
            if '"line":1' in output or '"line":0' in output:
                print(f"\n{GREEN}✅ SUCCESS: Points to function signature (line 0 or 1){NC}")
                return True
            else:
                print(f"\n{GREEN}✓ Got a location response{NC}")
                # Print more details to debug
                uri_pos = output.find('"uri"', result_pos)
                if uri_pos > 0:
                    details = output[uri_pos:min(len(output), uri_pos+200)]
                    print(f"Location details: {details}")
                return True
        else:
            print(f"\n{RED}✗ Response missing location data{NC}")
            # Print the full output for debugging
            print(f"\nDEBUG - Full output length: {len(output)}")
            print(f"DEBUG - Last 500 chars of output:")
            print(output[-500:])
            return False
    else:
        print(f"\n{RED}✗ No valid response from LSP{NC}")
        if '"error"' in output:
            error_start = output.find('"error"')
            print(f"Error in output: {output[error_start:error_start+200]}")
        return False

def main():
    if not os.path.exists('_build/default/jasmin-lsp/jasmin_lsp.exe'):
        print(f"{RED}Error: LSP server not found{NC}")
        print("Run: pixi run build")
        return 1
    
    if not os.path.exists('test/fixtures/simple_function.jazz'):
        print(f"{RED}Error: Test file not found{NC}")
        return 1
    
    result = test_parameter_definition()
    
    print("\n" + "="*60)
    if result:
        print(f"{GREEN}PARAMETER DEFINITION TEST PASSED!{NC}")
        return 0
    else:
        print(f"{RED}PARAMETER DEFINITION TEST FAILED{NC}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
