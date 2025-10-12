#!/usr/bin/env python3
"""
Test for multi-file project with requires - simulates the real crash scenario.
"""

import subprocess
import json
import time
import os
import sys
import tempfile
import shutil

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

def test_multi_file_project():
    """Test with multiple files and require statements"""
    print("Testing multi-file project with requires...")
    
    # Create temp directory with test files
    tmpdir = tempfile.mkdtemp()
    
    try:
        # Create test files
        params_file = os.path.join(tmpdir, "params.jinc")
        with open(params_file, 'w') as f:
            f.write('param int ETA = 2;\nparam int K = 4;\n')
        
        eta_file = os.path.join(tmpdir, "eta.jinc")
        with open(eta_file, 'w') as f:
            f.write('require "params.jinc"\n\nfn pack_eta() {\n  reg u64 x;\n  x = ETA;\n}\n')
        
        main_file = os.path.join(tmpdir, "main.jazz")
        with open(main_file, 'w') as f:
            f.write(f'''require "{os.path.basename(params_file)}"
require "{os.path.basename(eta_file)}"

fn main() {{
  pack_eta();
}}
''')
        
        # Start server
        proc = subprocess.Popen(
            [SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        
        msg_id = 0
        
        def send(method, params=None, is_notification=False):
            nonlocal msg_id
            msg = {"jsonrpc": "2.0", "method": method}
            
            if not is_notification:
                msg_id += 1
                msg["id"] = msg_id
            
            if params:
                msg["params"] = params
            
            msg_str = json.dumps(msg)
            content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
            
            try:
                proc.stdin.write(content.encode('utf-8'))
                proc.stdin.flush()
                return True
            except:
                return False
        
        # Initialize
        send("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{tmpdir}",
            "capabilities": {}
        })
        time.sleep(0.3)
        
        if proc.poll() is not None:
            print("✗ CRASH during initialization!")
            return False
        
        send("initialized", {}, is_notification=True)
        time.sleep(0.3)
        
        # Open main file (which requires other files)
        main_uri = f"file://{main_file}"
        with open(main_file, 'r') as f:
            main_content = f.read()
        
        print(f"  Opening main file...")
        send("textDocument/didOpen", {
            "textDocument": {
                "uri": main_uri,
                "languageId": "jasmin",
                "version": 1,
                "text": main_content
            }
        }, is_notification=True)
        
        time.sleep(0.5)
        
        if proc.poll() is not None:
            print("✗ CRASH after opening main file!")
            stderr = proc.stderr.read().decode('utf-8', errors='replace')
            print("=== STDERR ===")
            print(stderr[-3000:])
            return False
        
        print(f"  Main file opened")
        
        # Open eta file
        eta_uri = f"file://{eta_file}"
        with open(eta_file, 'r') as f:
            eta_content = f.read()
        
        print(f"  Opening eta file...")
        send("textDocument/didOpen", {
            "textDocument": {
                "uri": eta_uri,
                "languageId": "jasmin",
                "version": 1,
                "text": eta_content
            }
        }, is_notification=True)
        
        time.sleep(0.5)
        
        if proc.poll() is not None:
            print("✗ CRASH after opening eta file!")
            stderr = proc.stderr.read().decode('utf-8', errors='replace')
            print("=== STDERR ===")
            print(stderr[-3000:])
            return False
        
        print(f"  Eta file opened")
        
        # Open params file
        params_uri = f"file://{params_file}"
        with open(params_file, 'r') as f:
            params_content = f.read()
        
        print(f"  Opening params file...")
        send("textDocument/didOpen", {
            "textDocument": {
                "uri": params_uri,
                "languageId": "jasmin",
                "version": 1,
                "text": params_content
            }
        }, is_notification=True)
        
        time.sleep(0.5)
        
        if proc.poll() is not None:
            print("✗ CRASH after opening params file!")
            stderr = proc.stderr.read().decode('utf-8', errors='replace')
            print("=== STDERR ===")
            print(stderr[-3000:])
            return False
        
        print(f"  Params file opened")
        
        # Request document symbols (this triggered the crash)
        print(f"  Requesting document symbols...")
        send("textDocument/documentSymbol", {
            "textDocument": {"uri": eta_uri}
        })
        
        time.sleep(0.5)
        
        if proc.poll() is not None:
            print("✗ CRASH after documentSymbol request!")
            stderr = proc.stderr.read().decode('utf-8', errors='replace')
            print("=== STDERR ===")
            print(stderr[-3000:])
            return False
        
        # Request hover on ETA (this also triggered the crash)
        print(f"  Requesting hover on ETA...")
        # Find line with ETA
        lines = eta_content.split('\n')
        eta_line = -1
        eta_char = -1
        for i, line in enumerate(lines):
            if 'ETA' in line and 'x = ETA' in line:
                eta_line = i
                eta_char = line.index('ETA')
                break
        
        if eta_line >= 0:
            send("textDocument/hover", {
                "textDocument": {"uri": eta_uri},
                "position": {"line": eta_line, "character": eta_char}
            })
            
            time.sleep(0.5)
            
            if proc.poll() is not None:
                print("✗ CRASH after hover request on ETA!")
                stderr = proc.stderr.read().decode('utf-8', errors='replace')
                print("=== STDERR ===")
                print(stderr[-3000:])
                return False
        
        print("✓ Multi-file project test passed!")
        
        proc.terminate()
        proc.wait(timeout=2)
        return True
        
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        try:
            proc.kill()
        except:
            pass
        
        # Cleanup temp directory
        shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == "__main__":
    success = test_multi_file_project()
    sys.exit(0 if success else 1)
