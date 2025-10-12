#!/usr/bin/env python3
"""
Final comprehensive test for multi-declaration hover fix.

Key findings:
1. Variable declarations CAN use commas: reg u32 i, j;
2. Function parameters DO NOT use commas: fn f(reg u32 a b)
3. Both should show correct types for each identifier
"""

import json
import subprocess
import sys

server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'

# Test code with both variable and parameter multi-declarations
test_code = """fn test(reg u32 a b, stack u64 x y z) -> reg u32 {
  reg u16 i, j, k;
  stack u8 p, q;
  return a;
}"""

def test_hover(line, char, expected_name, expected_type, description):
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
                    'uri': 'file:///test_comprehensive.jazz',
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
                'textDocument': {'uri': 'file:///test_comprehensive.jazz'},
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
                        print(f"✓ {description}: {actual}")
                        return True
                    else:
                        print(f"✗ {description} FAILED")
                        print(f"  Expected: {expected}")
                        print(f"  Got: {actual}")
                        return False
    
    print(f"✗ {description} returned no result")
    return False

if __name__ == "__main__":
    print("=" * 70)
    print("COMPREHENSIVE MULTI-DECLARATION HOVER TEST")
    print("=" * 70)
    print("\nTest code:")
    for i, line in enumerate(test_code.split('\n')):
        print(f"  {i}: {line}")
    print()
    
    # Character analysis for line 0
    line0 = test_code.split('\n')[0]
    print(f"Line 0 analysis: {repr(line0)}")
    print("Parameters (no commas in Jasmin):")
    for i, char in enumerate(line0):
        if char in 'abxyz' and i < 40:  # only params
            print(f"  [{i}] = '{char}'")
    print()
    
    # Character analysis for line 1
    line1 = test_code.split('\n')[1]
    print(f"Line 1 analysis: {repr(line1)}")
    print("Variables (with commas):")
    for i, char in enumerate(line1):
        if char in 'ijk':
            print(f"  [{i}] = '{char}'")
    print()
    
    tests = [
        # Function parameters (whitespace-separated, no commas)
        (0, 16, "a", "reg u32", "Param 'a'"),
        (0, 18, "b", "reg u32", "Param 'b'"),
        (0, 31, "x", "stack u64", "Param 'x'"),
        (0, 33, "y", "stack u64", "Param 'y'"),
        (0, 35, "z", "stack u64", "Param 'z'"),
        # Variable declarations (comma-separated)
        (1, 11, "i", "reg u16", "Var 'i'"),
        (1, 14, "j", "reg u16", "Var 'j'"),
        (1, 17, "k", "reg u16", "Var 'k'"),
        (2, 12, "p", "stack u8", "Var 'p'"),
        (2, 15, "q", "stack u8", "Var 'q'"),
    ]
    
    all_passed = True
    print("Running tests:")
    print("-" * 70)
    for line, char, name, typ, desc in tests:
        passed = test_hover(line, char, name, typ, desc)
        all_passed = all_passed and passed
    
    print("-" * 70)
    print()
    if all_passed:
        print("✅ ALL TESTS PASSED! The fix is working correctly.")
        print()
        print("Summary:")
        print("  • Variables with commas: reg u32 i, j; ✓")
        print("  • Parameters without commas: fn f(reg u32 a b) ✓")
        print("  • Each identifier shows only its own type ✓")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
