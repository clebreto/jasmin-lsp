#!/usr/bin/env python3
"""Test that hover correctly prioritizes symbol definitions.

When multiple files define the same symbol, hover should prefer:
1. Definitions in the current file
2. Definitions in directly required files (in order of require statements)
3. Other files in the dependency tree

This test ensures that a param definition takes precedence over a reg definition
when both are available.
"""
import json
import subprocess
import sys
import os

def test_symbol_priority():
    """Test that param K from params.jinc is found instead of reg K from hashing.jinc"""
    server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'
    fixture_path = 'test/test_hover/fixtures/main_use_k.jazz'
    
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
        # Open params.jinc first (defines K as param)
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
        # Open hashing.jinc (defines K as reg)
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
        # Open main file (requires both)
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
        # Hover over K in main file (line 7, character 8: "x = K;")
        {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'textDocument/hover',
            'params': {
                'textDocument': {'uri': f'file://{main_path}'},
                'position': {'line': 7, 'character': 8}  # Position on K
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
    
    print("=== Hover Response ===")
    # Find the response to request id=2
    hover_response = None
    for line in result.stdout.split('\n'):
        if '"id":2' in line or '"id": 2' in line:
            hover_response = line
            print(line)
            break
    
    print("\n=== STDERR (relevant) ===")
    found_symbol_log = None
    for line in result.stderr.split('\n'):
        if 'Hover: Found symbol' in line and "'K'" in line:
            print(line)
            found_symbol_log = line
        elif 'hover' in line.lower() or 'symbol' in line.lower():
            print(line)
    
    # Verify the response
    if hover_response:
        try:
            # Parse the JSON response
            response_json = json.loads(hover_response)
            if 'result' in response_json and response_json['result']:
                result_content = response_json['result']
                if 'contents' in result_content:
                    contents = result_content['contents']
                    if isinstance(contents, dict) and 'value' in contents:
                        markdown = contents['value']
                        print(f"\n=== Hover Markdown ===")
                        print(markdown)
                        
                        # Check if it mentions param (correct)
                        if 'param' in markdown and 'K' in markdown:
                            print("\n✅ SUCCESS: Hover shows param K definition")
                            
                            # Verify it's NOT showing the reg definition
                            if 'reg u32 K' not in markdown:
                                print("✅ SUCCESS: Hover does not show reg u32 K")
                                
                                # Verify it found the symbol in params.jinc, not hashing.jinc
                                if found_symbol_log:
                                    if 'params.jinc' in found_symbol_log:
                                        print("✅ SUCCESS: Found K in params.jinc (correct file)")
                                        return True
                                    elif 'hashing.jinc' in found_symbol_log:
                                        print("❌ FAIL: Found K in hashing.jinc (wrong file)")
                                        print(f"   Expected to find in params.jinc but found in hashing.jinc")
                                        return False
                                    else:
                                        print("⚠️  WARNING: Could not determine which file K was found in")
                                        return True  # Assume success if markdown is correct
                                else:
                                    print("⚠️  WARNING: No 'Found symbol' log found")
                                    return True  # Assume success if markdown is correct
                            else:
                                print("❌ FAIL: Hover shows reg u32 K (should show param)")
                                return False
                        else:
                            print("❌ FAIL: Hover does not show param K definition")
                            print(f"   Got: {markdown}")
                            return False
        except json.JSONDecodeError as e:
            print(f"❌ FAIL: Could not parse JSON response: {e}")
            return False
    
    print("❌ FAIL: No hover response received")
    return False

if __name__ == '__main__':
    success = test_symbol_priority()
    sys.exit(0 if success else 1)
