#!/usr/bin/env python3
"""
Test exact user scenario: from Common require "poly.jinc"
"""
import json, subprocess, os, tempfile
import pytest

server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'


def test_from_common_require_navigation():
    """Test that 'from Common require "poly.jinc"' navigation works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create Common folder with poly.jinc (note: user said polyvec.jinc but example uses poly.jinc)
        os.makedirs(os.path.join(tmpdir, 'Common'))
        poly_file = os.path.join(tmpdir, 'Common', 'poly.jinc')
        with open(poly_file, 'w') as f:
            f.write('param int KYBER_N = 256;\nfn poly_add() { }')
        
        # Create main file with from/require
        main_file = os.path.join(tmpdir, 'main.jazz')
        with open(main_file, 'w') as f:
            f.write('from Common require "poly.jinc"\nfn test() { poly_add(); }')
        
        main_uri = f"file://{main_file}"
        
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
             'params': {'processId': None, 'rootUri': f'file://{tmpdir}', 'capabilities': {}}},
            {'jsonrpc': '2.0', 'method': 'initialized', 'params': {}},
            {'jsonrpc': '2.0', 'method': 'textDocument/didOpen',
             'params': {'textDocument': {'uri': main_uri, 'languageId': 'jasmin',
                                         'version': 1, 'text': open(main_file).read()}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/definition',
             'params': {'textDocument': {'uri': main_uri}, 'position': {'line': 1, 'character': 12}}}
        ]
        
        input_data = ''.join(f'Content-Length: {len(json.dumps(m).encode())}\r\n\r\n{json.dumps(m)}' for m in messages)
        
        proc = subprocess.Popen([server_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, _ = proc.communicate(input=input_data.encode(), timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            pytest.fail("LSP server timed out after 10 seconds")
        finally:
            # Ensure process is terminated
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
        
        # Parse response
        output = stdout.decode('utf-8', errors='ignore')
        found_response = False
        
        while 'Content-Length:' in output:
            try:
                idx = output.index('Content-Length:')
                output = output[idx:]
                header_end = output.index('\r\n\r\n')
                length = int(output[:header_end].split(':')[1].strip())
                body = output[header_end+4:header_end+4+length]
                resp = json.loads(body)
                
                if 'id' in resp and resp['id'] == 2:
                    found_response = True
                    assert 'result' in resp and resp['result'], "Expected definition result but got none"
                    target = resp['result'][0]['uri'].replace('file://', '')
                    assert os.path.samefile(target, poly_file), \
                        f"Expected navigation to {poly_file} but got {target}"
                    print("✅ SUCCESS: Go to Definition works!")
                    print(f"   from Common require \"poly.jinc\"")
                    print(f"   Resolved to: Common/poly.jinc")
                    print(f"   Full path: {poly_file}")
                    return  # Test passed
                
                output = output[header_end+4+length:]
            except: 
                break
        
        assert found_response, "No response received from LSP server for definition request"
