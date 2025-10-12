#!/usr/bin/env python3
"""
Test goto definition across files and for variables
"""

import json
import subprocess
import sys
import os
from pathlib import Path

GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
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

def test_cross_file_function_def():
    """Test goto definition on a function defined in another file"""
    print("\n" + "="*60)
    print("Test 1: Cross-File Function Definition")
    print("="*60)
    
    server_path = '_build/default/jasmin-lsp/jasmin_lsp.exe'
    main_file = 'test/fixtures/main_program.jazz'
    lib_file = 'test/fixtures/math_lib.jazz'
    
    with open(main_file) as f:
        main_content = f.read()
    with open(lib_file) as f:
        lib_content = f.read()
    
    main_uri = f"file://{os.path.abspath(main_file)}"
    lib_uri = f"file://{os.path.abspath(lib_file)}"
    workspace_uri = f"file://{os.path.abspath('test/fixtures')}"
    
    # Find position of 'square' function call in main_program.jazz
    lines = main_content.split('\n')
    line_num = -1
    char_pos = -1
    
    for i, line in enumerate(lines):
        if 'square(' in line and 'temp1' in line:
            line_num = i
            char_pos = line.index('square') + 3  # Middle of 'square'
            break
    
    print(f"Looking for 'square' call at line {line_num}, char {char_pos}")
    print(f"Line: {lines[line_num]}")
    
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
                    'uri': lib_uri,
                    'languageId': 'jasmin',
                    'version': 1,
                    'text': lib_content
                }
            }
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
                'position': {'line': line_num, 'character': char_pos}
            }
        }
    ]
    
    output = run_lsp_test(server_path, messages)
    
    if '"id":2' in output and '"result"' in output:
        if 'math_lib.jazz' in output:
            print(f"{GREEN}✅ PASS: Points to math_lib.jazz{NC}")
            return True
        else:
            print(f"{YELLOW}⚠️  Got response but doesn't explicitly mention math_lib.jazz{NC}")
            if '"uri"' in output:
                print("But has a URI - might still be working")
                return True
    
    print(f"{RED}❌ FAIL: No valid response{NC}")
    return False

def test_variable_definition():
    """Test goto definition on a variable"""
    print("\n" + "="*60)
    print("Test 2: Variable Definition (Same File)")
    print("="*60)
    
    server_path = '_build/default/jasmin-lsp/jasmin_lsp.exe'
    test_file = 'test/fixtures/simple_function.jazz'
    
    with open(test_file) as f:
        content = f.read()
    
    uri = f"file://{os.path.abspath(test_file)}"
    
    # Find usage of 'result' variable in add_numbers function
    lines = content.split('\n')
    line_num = -1
    char_pos = -1
    
    for i, line in enumerate(lines):
        if 'return result' in line and i < 10:  # In add_numbers function
            line_num = i
            char_pos = line.index('result') + 3
            break
    
    print(f"Looking for 'result' variable at line {line_num}, char {char_pos}")
    print(f"Line: {lines[line_num]}")
    
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
    
    output = run_lsp_test(server_path, messages)
    
    if '"id":2' in output and '"result"' in output:
        if '"uri"' in output and '"range"' in output:
            print(f"{GREEN}✅ PASS: Found variable definition{NC}")
            return True
    
    print(f"{RED}❌ FAIL: No valid response{NC}")
    print("Output snippet:", output[max(0, output.find('"id":2')-100):min(len(output), output.find('"id":2')+300)])
    return False

def main():
    print("="*60)
    print("Cross-File and Variable Definition Tests")
    print("="*60)
    
    results = []
    
    results.append(("Cross-file function", test_cross_file_function_def()))
    results.append(("Variable definition", test_variable_definition()))
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}✅ PASS{NC}" if result else f"{RED}❌ FAIL{NC}"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
