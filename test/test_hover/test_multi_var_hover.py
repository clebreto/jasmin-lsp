#!/usr/bin/env python3
"""
Test that hover shows correct type for variables declared together.
Issue: reg u32 i, j; should show "j: reg u32", not "j: reg u32 i, "
"""

import json
import subprocess
import sys
import os

server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'

test_code = """fn test() {
  reg u32 i, j;
  stack u64 x, y, z;
  i = 1;
  j = 2;
  x = 3;
  y = 4;
  z = 5;
}"""

def test_hover(line, char, expected_name, expected_type):
    """Test hover at a specific position"""
    
    messages = [
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {'processId': None, 'rootUri': 'file:///tmp', 'capabilities': {}}
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
                    'uri': 'file:///test_multi_var.jazz',
                    'languageId': 'jasmin',
                    'version': 1,
                    'text': test_code
                }
            }
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'textDocument/hover',
            'params': {
                'textDocument': {'uri': 'file:///test_multi_var.jazz'},
                'position': {'line': line, 'character': char}
            }
        }
    ]
    
    input_data = ''
    for msg in messages:
        content = json.dumps(msg)
        content_bytes = content.encode('utf-8')
        header = f'Content-Length: {len(content_bytes)}\r\n\r\n'
        input_data += header + content
    
    proc = subprocess.Popen(
        [server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = proc.communicate(input=input_data.encode('utf-8'), timeout=5)
    
    # Parse responses
    responses = []
    output = stdout.decode('utf-8', errors='ignore')
    while 'Content-Length:' in output:
        try:
            idx = output.index('Content-Length:')
            output = output[idx:]
            header_end = output.index('\r\n\r\n')
            header = output[:header_end]
            length_str = header.split(':')[1].strip()
            length = int(length_str)
            body_start = header_end + 4
            body = output[body_start:body_start + length]
            responses.append(json.loads(body))
            output = output[body_start + length:]
        except (ValueError, IndexError, json.JSONDecodeError):
            break
    
    # Find hover response
    for resp in responses:
        if 'id' in resp and resp['id'] == 2:
            if 'result' in resp and resp['result']:
                content = resp['result'].get('contents', {})
                if isinstance(content, dict) and 'value' in content:
                    value = content['value']
                    expected = f"{expected_name}: {expected_type}"
                    
                    # Extract actual content from markdown code block
                    if "```jasmin" in value:
                        actual = value.split("```jasmin\n")[1].split("\n```")[0]
                    else:
                        actual = value
                    
                    if expected == actual:
                        print(f"✓ Hover on '{expected_name}' correct: {actual}")
                        return True
                    else:
                        print(f"✗ Hover on '{expected_name}' FAILED")
                        print(f"  Expected: {expected}")
                        print(f"  Got: {actual}")
                        return False
    
    print(f"✗ Hover on '{expected_name}' returned no result")
    return False

if __name__ == "__main__":
    print("Testing multi-variable declaration hover...")
    print()
    
    # Test hover on each variable declaration
    tests = [
        # Line 1: reg u32 i, j;
        (1, 10, "i", "reg u32"),   # i is at character 10
        (1, 13, "j", "reg u32"),   # j is at character 13
        # Line 2: stack u64 x, y, z;
        (2, 12, "x", "stack u64"), # x is at character 12
        (2, 15, "y", "stack u64"), # y is at character 15
        (2, 18, "z", "stack u64"), # z is at character 18
    ]
    
    all_passed = True
    for line, char, name, typ in tests:
        passed = test_hover(line, char, name, typ)
        all_passed = all_passed and passed
    
    print()
    if all_passed:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
