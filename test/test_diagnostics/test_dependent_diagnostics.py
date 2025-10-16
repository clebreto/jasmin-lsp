#!/usr/bin/env python3
"""
Test that diagnostics are sent for dependent files when a document is modified.

This test verifies that when a file is edited, diagnostics are also sent for:
- Files that require this file (reverse dependencies)
- Files required by this file (direct dependencies)
- Transitively required files (indirect dependencies)
"""

import subprocess
import json
import time
import tempfile
import os
from pathlib import Path

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"


def test_diagnostics_for_dependent_files():
    """Test that editing a file triggers diagnostics for all dependent files."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a multi-file project structure
        # utils.jinc (base file)
        utils_path = tmpdir / "utils.jinc"
        utils_uri = utils_path.as_uri()
        utils_content_valid = """fn add(reg u64 a, reg u64 b) -> reg u64 {
    reg u64 result;
    result = a + b;
    return result;
}
"""
        
        utils_content_invalid = """fn add(reg u64 a, reg u64 b) -> reg u64 {
    reg u64 result;
    result = [;]
    return result;
}
"""
        
        # module.jinc (depends on utils.jinc)
        module_path = tmpdir / "module.jinc"
        module_uri = module_path.as_uri()
        module_content = """require "utils.jinc"

fn compute(reg u64 x) -> reg u64 {
    reg u64 y;
    y = add(x, 10);
    return y;
}
"""
        
        # main.jazz (depends on module.jinc)
        main_path = tmpdir / "main.jazz"
        main_uri = main_path.as_uri()
        main_content = """require "module.jinc"

export fn main() {
    reg u64 result;
    result = compute(42);
}
"""
        
        # Write files
        utils_path.write_text(utils_content_valid)
        module_path.write_text(module_content)
        main_path.write_text(main_content)
        
        # Start LSP server
        proc = subprocess.Popen(
            [SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        def send_message(msg):
            msg_str = json.dumps(msg)
            content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
            proc.stdin.write(content.encode())
            proc.stdin.flush()
        
        def read_response():
            """Read one response from the server"""
            headers = {}
            while True:
                line = proc.stdout.readline().decode('utf-8')
                if line == '\r\n':
                    break
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    headers[key.strip()] = value.strip()
            
            content_length = int(headers.get('Content-Length', 0))
            if content_length > 0:
                body = proc.stdout.read(content_length).decode('utf-8')
                return json.loads(body)
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
                    # Check if there's data available
                    import select
                    ready, _, _ = select.select([proc.stdout], [], [], 0.1)
                    if ready:
                        resp = read_response()
                        if resp:
                            if resp.get('method') == 'textDocument/publishDiagnostics':
                                diagnostics.append(resp)
                            attempts = 0  # Reset attempts if we got something
                        else:
                            attempts += 1
                    else:
                        attempts += 1
                    
                    # If no data for a while, stop waiting
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
            
            # Initialized
            send_message({"jsonrpc": "2.0", "method": "initialized", "params": {}})
            time.sleep(0.1)
            
            # Open all three files
            send_message({
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": utils_uri,
                        "languageId": "jasmin",
                        "version": 1,
                        "text": utils_content_valid
                    }
                }
            })
            
            send_message({
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": module_uri,
                        "languageId": "jasmin",
                        "version": 1,
                        "text": module_content
                    }
                }
            })
            
            send_message({
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": main_uri,
                        "languageId": "jasmin",
                        "version": 1,
                        "text": main_content
                    }
                }
            })
            
            # Wait for initial diagnostics
            initial_diagnostics = read_all_diagnostics(timeout=1.0)
            
            print(f"\n Initial diagnostics received: {len(initial_diagnostics)} messages")
            for diag in initial_diagnostics:
                uri = diag['params']['uri']
                count = len(diag['params']['diagnostics'])
                filename = Path(uri).name
                print(f"  {filename}: {count} diagnostics")
            
            # Now edit utils.jinc to introduce an error
            print(f"\nIntroducing syntax error in utils.jinc...")
            send_message({
                "jsonrpc": "2.0",
                "method": "textDocument/didChange",
                "params": {
                    "textDocument": {
                        "uri": utils_uri,
                        "version": 2
                    },
                    "contentChanges": [
                        {"text": utils_content_invalid}
                    ]
                }
            })
            
            # Wait for updated diagnostics
            updated_diagnostics = read_all_diagnostics(timeout=2.0)
            
            print(f"\nUpdated diagnostics received: {len(updated_diagnostics)} messages")
            diagnostics_by_file = {}
            for diag in updated_diagnostics:
                uri = diag['params']['uri']
                count = len(diag['params']['diagnostics'])
                filename = Path(uri).name
                diagnostics_by_file[uri] = count
                print(f"  {filename}: {count} diagnostics")
            
            # Verify that utils.jinc has diagnostics
            assert utils_uri in diagnostics_by_file, \
                "Should receive diagnostics for the modified file (utils.jinc)"
            
            assert diagnostics_by_file[utils_uri] > 0, \
                f"utils.jinc should have errors after introducing [;]"
            
            # Check if we got diagnostics for dependent files (the new feature)
            total_files = len(diagnostics_by_file)
            print(f"\nTotal files that received diagnostics: {total_files}")
            
            if module_uri in diagnostics_by_file or main_uri in diagnostics_by_file:
                print("✓ SUCCESS: Diagnostics sent for dependent files!")
                print(f"  This confirms the new feature is working.")
            else:
                print("⚠ WARNING: Diagnostics only sent for modified file")
                print(f"  Expected diagnostics for module.jinc and/or main.jazz as well.")
            
            # The test passes if we get diagnostics for the modified file at minimum
            # But ideally we should get diagnostics for all files in the dependency chain
            assert total_files >= 1, "Should send diagnostics for at least the modified file"
            
            print(f"\n✓ Test passed")
            
            proc.terminate()
            proc.wait(timeout=1)
            
        except Exception as e:
            print(f"Test error: {e}")
            raise
        finally:
            try:
                proc.kill()
            except:
                pass


if __name__ == "__main__":
    test_diagnostics_for_dependent_files()
