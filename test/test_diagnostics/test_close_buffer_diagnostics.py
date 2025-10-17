#!/usr/bin/env python3
"""
Test that closing a file removes diagnostics only if it's NOT in the dependency tree
of the master file.

This test verifies that:
1. Files in the master file dependency tree keep diagnostics even when closed
2. Files NOT in the dependency tree have diagnostics cleared when closed
3. Open buffers always get diagnostics regardless of master file
"""

import subprocess
import json
import time
import tempfile
import os
from pathlib import Path

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"


def test_close_buffer_diagnostics():
    """Test that closing files removes diagnostics only if not in master file tree"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test files
        # utils.jinc - will be in master file dependency tree, WITH AN ERROR
        utils_path = tmpdir / "utils.jinc"
        utils_uri = utils_path.as_uri()
        utils_content = """fn add(reg u64 a, reg u64 b) -> reg u64 {
    reg u64 result;
    result = a + b
    // MISSING SEMICOLON - syntax error!
    return result;
}
"""
        
        # module.jinc - depends on utils.jinc, in master file tree
        module_path = tmpdir / "module.jinc"
        module_uri = module_path.as_uri()
        module_content = """require "utils.jinc"

fn compute(reg u64 x) -> reg u64 {
    reg u64 y;
    y = add(x, 10);
    return y;
}
"""
        
        # main.jazz - master file, depends on module.jinc
        main_path = tmpdir / "main.jazz"
        main_uri = main_path.as_uri()
        main_content = """require "module.jinc"

export fn main() {
    reg u64 result;
    result = compute(42);
}
"""
        
        # unrelated.jinc - NOT in master file dependency tree
        unrelated_path = tmpdir / "unrelated.jinc"
        unrelated_uri = unrelated_path.as_uri()
        unrelated_content = """fn other(reg u64 x) -> reg u64 {
    reg u64 y;
    y = x + 1;
    return y;
}
"""
        
        # Write files
        utils_path.write_text(utils_content)
        module_path.write_text(module_content)
        main_path.write_text(main_content)
        unrelated_path.write_text(unrelated_content)
        
        # Start LSP server
        proc = subprocess.Popen(
            [SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        def send_message(msg):
            msg_json = json.dumps(msg)
            msg_content = f"Content-Length: {len(msg_json)}\r\n\r\n{msg_json}"
            proc.stdin.write(msg_content.encode())
            proc.stdin.flush()
        
        def read_response():
            """Read one response from the server"""
            try:
                header = b""
                while not header.endswith(b"\r\n\r\n"):
                    char = proc.stdout.read(1)
                    if not char:
                        return None
                    header += char
                
                content_length = 0
                for line in header.decode().split("\r\n"):
                    if line.startswith("Content-Length:"):
                        content_length = int(line.split(":")[1].strip())
                        break
                
                if content_length == 0:
                    return None
                
                content = proc.stdout.read(content_length)
                return json.loads(content.decode())
            except Exception as e:
                print(f"Error reading response: {e}")
                return None
        
        def read_all_diagnostics(timeout=1.0):
            """Read all diagnostic messages within timeout"""
            diagnostics = []
            end_time = time.time() + timeout
            attempts = 0
            while time.time() < end_time:
                remaining = end_time - time.time()
                if remaining <= 0:
                    break
                try:
                    import select
                    ready, _, _ = select.select([proc.stdout], [], [], 0.1)
                    if ready:
                        resp = read_response()
                        if resp:
                            if resp.get('method') == 'textDocument/publishDiagnostics':
                                diagnostics.append(resp)
                            attempts = 0
                        else:
                            attempts += 1
                    else:
                        attempts += 1
                    
                    if attempts > 5:
                        break
                    time.sleep(0.05)
                except Exception as e:
                    print(f"Error reading: {e}")
                    attempts += 1
                    time.sleep(0.05)
            return diagnostics
        
        try:
            # Initialize
            send_message({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "processId": os.getpid(),
                    "rootUri": tmpdir.as_uri(),
                    "capabilities": {}
                }
            })
            resp = read_response()
            print("✓ Initialized")
            
            # Send initialized notification
            send_message({"jsonrpc": "2.0", "method": "initialized", "params": {}})
            time.sleep(0.1)
            
            # Set master file to main.jazz
            print(f"\n1. Setting master file to: {main_uri}")
            send_message({
                "jsonrpc": "2.0",
                "method": "jasmin/setMasterFile",
                "params": {
                    "uri": main_uri
                }
            })
            time.sleep(0.2)
            
            # Open all files
            print("\n2. Opening all files...")
            for uri, content, name in [
                (utils_uri, utils_content, "utils.jinc"),
                (module_uri, module_content, "module.jinc"),
                (main_uri, main_content, "main.jazz"),
                (unrelated_uri, unrelated_content, "unrelated.jinc")
            ]:
                send_message({
                    "jsonrpc": "2.0",
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": uri,
                            "languageId": "jasmin",
                            "version": 1,
                            "text": content
                        }
                    }
                })
                print(f"  Opened {name}")
            
            # Read initial diagnostics - diagnostics are sent per file opened
            # We should get diagnostics for each file as it's opened
            initial_diagnostics = read_all_diagnostics(timeout=1.5)
            print(f"\n3. Initial diagnostics received: {len(initial_diagnostics)} messages")
            initial_files = set()
            for diag in initial_diagnostics:
                uri = diag['params']['uri']
                filename = Path(uri).name if uri.startswith('file://') else uri
                count = len(diag['params']['diagnostics'])
                initial_files.add(uri)
                print(f"  {filename}: {count} diagnostics")
            
            # Note: Depending on implementation, we might only get diagnostics for
            # files that were just opened, not all open files
            print(f"✓ Initial diagnostics received for {len(initial_files)} files")
            
            # TEST 1: Close a file that IS in the dependency tree (utils.jinc)
            print("\n4. TEST 1: Closing utils.jinc (IN dependency tree)...")
            send_message({
                "jsonrpc": "2.0",
                "method": "textDocument/didClose",
                "params": {
                    "textDocument": {
                        "uri": utils_uri
                    }
                }
            })
            time.sleep(0.3)
            
            # Read diagnostics after closing
            after_close_utils = read_all_diagnostics(timeout=0.5)
            print(f"  Diagnostics after close: {len(after_close_utils)} messages")
            
            # Check all diagnostics received
            utils_diagnostics_count = None
            files_with_diags = {}
            for diag in after_close_utils:
                uri = diag['params']['uri']
                filename = Path(uri).name if uri.startswith('file://') else uri
                count = len(diag['params']['diagnostics'])
                if filename not in files_with_diags:
                    files_with_diags[filename] = []
                files_with_diags[filename].append(count)
                
            print(f"  Files that received diagnostics:")
            for filename, counts in files_with_diags.items():
                print(f"    {filename}: {counts} (total {sum(counts)} diagnostics across {len(counts)} messages)")
            
            # Check if utils.jinc diagnostics were cleared
            utils_cleared = False
            for diag in after_close_utils:
                uri = diag['params']['uri']
                if uri == utils_uri:
                    count = len(diag['params']['diagnostics'])
                    if utils_diagnostics_count is None:
                        utils_diagnostics_count = count
                    if count == 0:
                        utils_cleared = True
                        print(f"  ✗ FAIL: utils.jinc diagnostics cleared (should be kept)")
                    else:
                        print(f"  ✓ utils.jinc still has {count} diagnostics (correct)")
            
            # Expected: utils.jinc should STILL have diagnostics in Problems panel
            # even though it's closed, because it's in the master file dependency tree
            if utils_cleared:
                print("  ✗ FAIL: Files in dependency tree should keep diagnostics when closed")
                assert False, "Files in dependency tree should keep diagnostics when closed"
            elif utils_diagnostics_count is None:
                print("  ⚠ WARNING: No diagnostics message received for utils.jinc")
                print("  This means diagnostics were implicitly removed from Problems panel")
                print("  ✗ FAIL: Should explicitly keep diagnostics for files in dependency tree")
                assert False, "Should receive diagnostics for files in dependency tree even when closed"
            else:
                print("  ✓ SUCCESS: Diagnostics kept for file in dependency tree")
            
            # TEST 2: Close a file that is NOT in the dependency tree (unrelated.jinc)
            print("\n5. TEST 2: Closing unrelated.jinc (NOT in dependency tree)...")
            send_message({
                "jsonrpc": "2.0",
                "method": "textDocument/didClose",
                "params": {
                    "textDocument": {
                        "uri": unrelated_uri
                    }
                }
            })
            time.sleep(0.3)
            
            # Read diagnostics after closing
            after_close_unrelated = read_all_diagnostics(timeout=0.5)
            print(f"  Diagnostics after close: {len(after_close_unrelated)} messages")
            
            # Check if unrelated.jinc diagnostics were cleared
            unrelated_cleared = False
            for diag in after_close_unrelated:
                uri = diag['params']['uri']
                if uri == unrelated_uri:
                    count = len(diag['params']['diagnostics'])
                    if count == 0:
                        unrelated_cleared = True
                        print(f"  ✓ unrelated.jinc diagnostics cleared (expected behavior)")
                    else:
                        print(f"  ✗ unrelated.jinc still has {count} diagnostics (should be cleared)")
            
            # Expected: unrelated.jinc SHOULD have its diagnostics cleared
            # because it's NOT in the master file dependency tree
            if unrelated_cleared:
                print("  ✓ SUCCESS: Diagnostics cleared for file not in dependency tree")
            else:
                print("  ✗ FAIL: Diagnostics should be cleared for files not in dependency tree")
            
            # TEST 3: Modify an open file and verify all relevant files get diagnostics
            print("\n6. TEST 3: Modifying main.jazz (still open)...")
            main_content_modified = """require "module.jinc"

export fn main() {
    reg u64 result;
    result = compute(42);
    result = result + 1;  // Add a line
}
"""
            send_message({
                "jsonrpc": "2.0",
                "method": "textDocument/didChange",
                "params": {
                    "textDocument": {
                        "uri": main_uri,
                        "version": 2
                    },
                    "contentChanges": [
                        {
                            "text": main_content_modified
                        }
                    ]
                }
            })
            time.sleep(0.3)
            
            # Read diagnostics after change
            after_change = read_all_diagnostics(timeout=1.0)
            print(f"  Diagnostics after change: {len(after_change)} messages")
            files_with_diagnostics = set()
            for diag in after_change:
                uri = diag['params']['uri']
                filename = Path(uri).name if uri.startswith('file://') else uri
                count = len(diag['params']['diagnostics'])
                files_with_diagnostics.add(uri)
                print(f"  {filename}: {count} diagnostics")
            
            # Expected: main.jazz, module.jinc should get diagnostics (both open)
            # utils.jinc should NOT (closed and not open)
            # unrelated.jinc should NOT (closed and not in tree)
            expected_files = {main_uri, module_uri}
            if files_with_diagnostics == expected_files:
                print("  ✓ SUCCESS: Only open files in dependency tree got diagnostics")
            else:
                print(f"  Expected files: {expected_files}")
                print(f"  Got files: {files_with_diagnostics}")
            
            print("\n" + "="*70)
            print("SUMMARY:")
            print("  - Files in master dependency tree should keep diagnostics when closed")
            print("  - Files NOT in master dependency tree should clear diagnostics when closed")
            print("  - All open buffers should always get diagnostics")
            print("="*70)
            
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    test_close_buffer_diagnostics()
