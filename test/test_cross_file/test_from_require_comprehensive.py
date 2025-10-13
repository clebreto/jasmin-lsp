#!/usr/bin/env python3
"""
Comprehensive test for 'from NAMESPACE require' syntax with various scenarios.
"""

import json
import subprocess
import os
import tempfile

server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'

def test_scenario(name, setup_func, test_line, test_char, expected_file_rel):
    """Generic test scenario"""
    print(f"\n{'='*70}")
    print(f"Test: {name}")
    print('='*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        main_file, expected_file = setup_func(tmpdir)
        main_uri = f"file://{main_file}"
        
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
             'params': {'processId': None, 'rootUri': f'file://{tmpdir}', 'capabilities': {}}},
            {'jsonrpc': '2.0', 'method': 'initialized', 'params': {}},
            {'jsonrpc': '2.0', 'method': 'textDocument/didOpen',
             'params': {'textDocument': {'uri': main_uri, 'languageId': 'jasmin',
                                         'version': 1, 'text': open(main_file).read()}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/definition',
             'params': {'textDocument': {'uri': main_uri},
                        'position': {'line': test_line, 'character': test_char}}}
        ]
        
        input_data = ''
        for msg in messages:
            content = json.dumps(msg)
            header = f'Content-Length: {len(content.encode())}\r\n\r\n'
            input_data += header + content
        
        proc = subprocess.Popen([server_path], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = proc.communicate(input=input_data.encode(), timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise
        finally:
            # Ensure process is terminated
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
        
        # Parse responses
        responses = []
        output = stdout.decode('utf-8', errors='ignore')
        while 'Content-Length:' in output:
            try:
                idx = output.index('Content-Length:')
                output = output[idx:]
                header_end = output.index('\r\n\r\n')
                length = int(output[:header_end].split(':')[1].strip())
                body = output[header_end+4:header_end+4+length]
                responses.append(json.loads(body))
                output = output[header_end+4+length:]
            except: break
        
        # Check result
        for resp in responses:
            if 'id' in resp and resp['id'] == 2:
                if 'result' in resp and resp['result']:
                    result = resp['result']
                    if isinstance(result, list) and len(result) > 0:
                        target_uri = result[0]['uri']
                        target_file = target_uri.replace('file://', '')
                        if os.path.samefile(target_file, expected_file):
                            print(f"✅ PASS: Resolved to {expected_file_rel}")
                            return True
                        else:
                            print(f"❌ FAIL: Wrong file")
                            print(f"   Expected: {expected_file}")
                            print(f"   Got: {target_file}")
                            return False
                print(f"❌ FAIL: No definition found")
                return False
        print(f"❌ FAIL: No response")
        return False

def test1_simple_namespace(tmpdir):
    """from Common require "file.jinc" """
    os.makedirs(os.path.join(tmpdir, 'Common'))
    
    poly = os.path.join(tmpdir, 'Common', 'poly.jinc')
    with open(poly, 'w') as f:
        f.write('fn poly_add() { }')
    
    main = os.path.join(tmpdir, 'main.jazz')
    with open(main, 'w') as f:
        f.write('from Common require "poly.jinc"\nfn test() { poly_add(); }')
    
    return main, poly

def test2_nested_path(tmpdir):
    """from Common require "crypto/aes.jinc" """
    os.makedirs(os.path.join(tmpdir, 'Common', 'crypto'))
    
    aes = os.path.join(tmpdir, 'Common', 'crypto', 'aes.jinc')
    with open(aes, 'w') as f:
        f.write('fn aes_encrypt() { }')
    
    main = os.path.join(tmpdir, 'main.jazz')
    with open(main, 'w') as f:
        f.write('from Common require "crypto/aes.jinc"\nfn test() { aes_encrypt(); }')
    
    return main, aes

def test3_no_namespace(tmpdir):
    """require "file.jinc" (no from clause) """
    poly = os.path.join(tmpdir, 'poly.jinc')
    with open(poly, 'w') as f:
        f.write('fn poly_add() { }')
    
    main = os.path.join(tmpdir, 'main.jazz')
    with open(main, 'w') as f:
        f.write('require "poly.jinc"\nfn test() { poly_add(); }')
    
    return main, poly

def test4_lowercase_folder(tmpdir):
    """from common require "file.jinc" (lowercase namespace) """
    os.makedirs(os.path.join(tmpdir, 'common'))
    
    poly = os.path.join(tmpdir, 'common', 'poly.jinc')
    with open(poly, 'w') as f:
        f.write('fn poly_add() { }')
    
    main = os.path.join(tmpdir, 'main.jazz')
    with open(main, 'w') as f:
        f.write('from common require "poly.jinc"\nfn test() { poly_add(); }')
    
    return main, poly

def test5_multiple_requires(tmpdir):
    """Multiple from/require statements """
    os.makedirs(os.path.join(tmpdir, 'Common'))
    os.makedirs(os.path.join(tmpdir, 'Crypto'))
    
    poly = os.path.join(tmpdir, 'Common', 'poly.jinc')
    with open(poly, 'w') as f:
        f.write('fn poly_add() { }')
    
    aes = os.path.join(tmpdir, 'Crypto', 'aes.jinc')
    with open(aes, 'w') as f:
        f.write('fn aes_encrypt() { }')
    
    main = os.path.join(tmpdir, 'main.jazz')
    with open(main, 'w') as f:
        f.write('''from Common require "poly.jinc"
from Crypto require "aes.jinc"
fn test() { 
  poly_add();
  aes_encrypt();
}''')
    
    return main, poly  # Test poly_add

if __name__ == "__main__":
    print("="*70)
    print("COMPREHENSIVE FROM/REQUIRE TESTS")
    print("="*70)
    
    tests = [
        ("Simple namespace", test1_simple_namespace, 1, 12, "Common/poly.jinc"),
        ("Nested path in namespace", test2_nested_path, 1, 12, "Common/crypto/aes.jinc"),
        ("No namespace (plain require)", test3_no_namespace, 1, 12, "poly.jinc"),
        ("Lowercase namespace folder", test4_lowercase_folder, 1, 12, "common/poly.jinc"),
        ("Multiple from/require", test5_multiple_requires, 3, 2, "Common/poly.jinc"),
    ]
    
    results = []
    for name, setup, line, char, expected_rel in tests:
        passed = test_scenario(name, setup, line, char, expected_rel)
        results.append((name, passed))
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        exit(1)
