#!/usr/bin/env python3
"""Test that hover finds the correct symbol when requires are in "wrong" order.

Even when hashing.jinc (which defines K as reg) is required before params.jinc (which defines K as param),
hover should still prefer the param definition because it's the correct one for the usage context.
"""
import json
import subprocess
import sys
import os

def test_symbol_priority_wrong_order():
    """Test that param K from params.jinc is found even when hashing.jinc is required first"""
    server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'
    fixture_path = 'test/test_hover/fixtures/main_wrong_order.jazz'
    
    # Get absolute paths for all files
    main_path = os.path.abspath(fixture_path)
    params_path = os.path.abspath('test/test_hover/fixtures/params.jinc')
    hashing_path = os.path.abspath('test/test_hover/fixtures/hashing.jinc')
    
    with open(fixture_path) as f:
        main_content = f.read()
    with open('test/test_hover/fixtures/params.jinc') as f:
        params_content = f.read()
    with open('test/test_hover/fixtures/hashing.jinc') as f:
        hashing_content = f.read()
    
    messages = [
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {
                'processId': None,
                'rootUri': f'file://{os.path.abspath(".")}',
                'capabilities': {}
            }
        },
        {
            'jsonrpc': '2.0',
            'method': 'initialized',
            'params': {}
        },
        # Open hashing.jinc first (defines K as reg)
        {
            'jsonrpc': '2.0',
            'method': 'textDocument/didOpen',
            'params': {
                'textDocument': {
                    'uri': f'file://{hashing_path}',
                    'languageId': 'jasmin',
                    'version': 1,
                    'text': hashing_content
                }
            }
        },
        # Open params.jinc second (defines K as param)
        {
            'jsonrpc': '2.0',
            'method': 'textDocument/didOpen',
            'params': {
                'textDocument': {
                    'uri': f'file://{params_path}',
                    'languageId': 'jasmin',
                    'version': 1,
                    'text': params_content
                }
            }
        },
        # Open main file (requires hashing.jinc first, then params.jinc)
        {
            'jsonrpc': '2.0',
            'method': 'textDocument/didOpen',
            'params': {
                'textDocument': {
                    'uri': f'file://{main_path}',
                    'languageId': 'jasmin',
                    'version': 1,
                    'text': main_content
                }
            }
        },
        # Hover over K in main file (line 8, character 8: "x = K;")
        {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'textDocument/hover',
            'params': {
                'textDocument': {'uri': f'file://{main_path}'},
                'position': {'line': 8, 'character': 8}  # Position on K
            }
        }
    ]
    
    input_data = ''
    for msg in messages:
        content = json.dumps(msg)
        content_bytes = content.encode('utf-8')
        input_data += f'Content-Length: {len(content_bytes)}\r\n\r\n{content}'
    
    result = subprocess.run(
        [server_path],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=5
    )
    
    print("=== STDERR (relevant) ===")
    found_symbol_log = None
    for line in result.stderr.split('\n'):
        if 'Hover: Found symbol' in line and "'K'" in line:
            print(line)
            found_symbol_log = line
        elif 'Hover:' in line and 'K' in line:
            print(line)
            if 'Found' in line:
                found_symbol_log = line
    
    # Check which file K was found in
    if found_symbol_log:
        if 'params.jinc' in found_symbol_log:
            print("✅ SUCCESS: Found K in params.jinc (correct - param definition)")
            return True
        elif 'hashing.jinc' in found_symbol_log:
            print("❌ FAIL: Found K in hashing.jinc (wrong - should find param, not reg)")
            print("   This demonstrates the bug: hover returns first match instead of best match")
            return False
        else:
            print("⚠️  WARNING: Could not determine which file K was found in")
            return False
    else:
        print("❌ FAIL: No 'Found symbol' log found")
        return False

if __name__ == '__main__':
    success = test_symbol_priority_wrong_order()
    sys.exit(0 if success else 1)
