#!/usr/bin/env python3
"""
Test that 'from NAMESPACE require "file.jinc"' syntax works correctly.
The namespace should be treated as a folder name.
"""

import json
import subprocess
import os
import tempfile
import shutil

server_path = './_build/default/jasmin-lsp/jasmin_lsp.exe'

def test_from_require():
    """Test from/require with namespace as folder"""
    
    # Create temporary directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create Common folder
        common_dir = os.path.join(tmpdir, 'Common')
        os.makedirs(common_dir)
        
        # Create poly.jinc in Common folder
        poly_file = os.path.join(common_dir, 'poly.jinc')
        with open(poly_file, 'w') as f:
            f.write("""fn poly_add() -> reg u32 {
  reg u32 result;
  result = 42;
  return result;
}
""")
        
        # Create main.jazz that requires from Common
        main_file = os.path.join(tmpdir, 'main.jazz')
        with open(main_file, 'w') as f:
            f.write("""from Common require "poly.jinc"

fn main() -> reg u32 {
  reg u32 x;
  x = poly_add();
  return x;
}
""")
        
        # Test: Go to definition on poly_add
        main_uri = f"file://{main_file}"
        
        messages = [
            {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'initialize',
                'params': {
                    'processId': None,
                    'rootUri': f'file://{tmpdir}',
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
                        'text': open(main_file).read()
                    }
                }
            },
            {
                'jsonrpc': '2.0',
                'id': 2,
                'method': 'textDocument/definition',
                'params': {
                    'textDocument': {'uri': main_uri},
                    'position': {'line': 4, 'character': 7}  # poly_add
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
        
        try:
            stdout, stderr = proc.communicate(input=input_data.encode('utf-8'), timeout=10)
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
                header = output[:header_end]
                length_str = header.split(':')[1].strip()
                length = int(length_str)
                body_start = header_end + 4
                body = output[body_start:body_start + length]
                responses.append(json.loads(body))
                output = output[body_start + length:]
            except (ValueError, IndexError, json.JSONDecodeError):
                break
        
        # Check stderr for logging
        stderr_text = stderr.decode('utf-8', errors='ignore')
        print("=== LSP Server Log ===")
        for line in stderr_text.split('\n'):
            if 'Common' in line or 'poly' in line or 'require' in line.lower():
                print(line)
        print()
        
        # Find definition response
        for resp in responses:
            if 'id' in resp and resp['id'] == 2:
                if 'result' in resp and resp['result']:
                    result = resp['result']
                    if isinstance(result, list) and len(result) > 0:
                        location = result[0]
                        target_uri = location['uri']
                        target_file = target_uri.replace('file://', '')
                        
                        expected_file = poly_file
                        if os.path.samefile(target_file, expected_file):
                            print(f"✅ SUCCESS: Go to definition resolved to correct file")
                            print(f"   Expected: {expected_file}")
                            print(f"   Got: {target_file}")
                            return True
                        else:
                            print(f"❌ FAIL: Wrong file resolved")
                            print(f"   Expected: {expected_file}")
                            print(f"   Got: {target_file}")
                            return False
                    else:
                        print(f"❌ FAIL: Definition not found")
                        print(f"   Response: {resp}")
                        return False
                else:
                    print(f"❌ FAIL: No result in response")
                    print(f"   Response: {resp}")
                    return False
        
        print(f"❌ FAIL: No definition response received")
        return False

if __name__ == "__main__":
    print("Testing 'from Common require \"poly.jinc\"' syntax...")
    print("=" * 70)
    print()
    
    success = test_from_require()
    
    print()
    print("=" * 70)
    if success:
        print("✅ TEST PASSED")
        exit(0)
    else:
        print("❌ TEST FAILED")
        exit(1)
