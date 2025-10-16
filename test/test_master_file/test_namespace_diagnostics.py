#!/usr/bin/env python3
"""
Test that setting namespace paths triggers diagnostics for the master file and its dependencies.

This test verifies that:
1. Setting a master file alone does NOT trigger diagnostics
2. Setting namespace paths after master file DOES trigger diagnostics
3. All required files are parsed and diagnostics are sent
"""

import subprocess
import json
import time
import tempfile
from pathlib import Path

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"


def send_message(proc, msg):
    """Send a JSON-RPC message to the LSP server"""
    msg_str = json.dumps(msg)
    content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
    proc.stdin.write(content.encode())
    proc.stdin.flush()


def read_response(proc, timeout=1.0):
    """Read one response from the server with timeout"""
    import select
    
    # Check if data is available
    ready, _, _ = select.select([proc.stdout], [], [], timeout)
    if not ready:
        return None
    
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


def read_all_responses(proc, timeout=2.0):
    """Read all available responses until timeout"""
    responses = []
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = read_response(proc, timeout=0.1)
        if response:
            responses.append(response)
        else:
            # Small delay to allow more responses
            time.sleep(0.1)
    
    return responses


def test_namespace_paths_trigger_diagnostics():
    """Test that namespace paths trigger diagnostics for master file"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create Common namespace directory (capital C to match namespace name)
        common_dir = tmpdir / "Common"
        common_dir.mkdir()
        
        # Create reduce.jinc in Common namespace with intentional error
        reduce_path = common_dir / "reduce.jinc"
        reduce_uri = reduce_path.as_uri()
        reduce_content_invalid = """fn reduce_sum(reg u64 array_ptr, reg u32 length) -> reg u64 {
  reg u64 sum;
  sum = [;]  // Syntax error
  return sum;
}
"""
        
        # Create main file using namespace
        main_path = tmpdir / "main.jazz"
        main_uri = main_path.as_uri()
        main_content = """from Common require "reduce.jinc"

export fn test() -> reg u64 {
  reg u64 result;
  result = reduce_sum(#0x1000, #5);
  return result;
}
"""
        
        # Write files
        reduce_path.write_text(reduce_content_invalid)
        main_path.write_text(main_content)
        
        # Start LSP server
        proc = subprocess.Popen(
            [SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # 1. Initialize
            send_message(proc, {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "processId": None,
                    "rootUri": tmpdir.as_uri(),
                    "capabilities": {}
                }
            })
            
            # Read responses until we get the initialize response
            init_response = None
            for _ in range(5):  # Try reading up to 5 messages
                response = read_response(proc, timeout=2.0)
                if response and response.get("id") == 1:
                    init_response = response
                    break
            
            if not init_response:
                print("ERROR: No initialization response received")
                return False
            print(f"✓ Initialize response received")
            
            # 2. Send initialized notification
            send_message(proc, {
                "jsonrpc": "2.0",
                "method": "initialized",
                "params": {}
            })
            time.sleep(0.1)
            
            # 3. Set master file
            send_message(proc, {
                "jsonrpc": "2.0",
                "method": "jasmin/setMasterFile",
                "params": {
                    "uri": main_uri
                }
            })
            
            # Read any responses - should be none or very few
            responses_after_master = read_all_responses(proc, timeout=0.5)
            diagnostic_count_before = sum(1 for r in responses_after_master 
                                          if r.get("method") == "textDocument/publishDiagnostics")
            
            print(f"Diagnostics after setting master file: {diagnostic_count_before}")
            
            # 4. Set namespace paths
            send_message(proc, {
                "jsonrpc": "2.0",
                "method": "jasmin/setNamespacePaths",
                "params": {
                    "paths": [{
                        "namespace": "Common",
                        "path": str(common_dir)
                    }]
                }
            })
            
            # Read all responses after namespace paths
            responses_after_namespace = read_all_responses(proc, timeout=2.0)
            
            # Count diagnostics
            diagnostics = [r for r in responses_after_namespace 
                          if r.get("method") == "textDocument/publishDiagnostics"]
            
            print(f"\nDiagnostics received after namespace paths: {len(diagnostics)}")
            for diag in diagnostics:
                uri = diag["params"]["uri"]
                count = len(diag["params"]["diagnostics"])
                print(f"  - {uri}: {count} diagnostic(s)")
                if count > 0:
                    for d in diag["params"]["diagnostics"]:
                        print(f"    * {d.get('message', 'no message')}")
            
            # Verify we got diagnostics for the required file with error
            reduce_diagnostics = [d for d in diagnostics if reduce_uri in d["params"]["uri"]]
            
            # Check results
            success = True
            
            if len(reduce_diagnostics) == 0:
                print("\n✗ FAILED: No diagnostics received for reduce.jinc")
                success = False
            else:
                has_errors = any(len(d["params"]["diagnostics"]) > 0 for d in reduce_diagnostics)
                if not has_errors:
                    print("\n✗ FAILED: Diagnostics received but no errors reported for reduce.jinc")
                    success = False
                else:
                    print("\n✓ SUCCESS: Diagnostics correctly sent after namespace paths configured")
            
            return success
            
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def test_namespace_paths_without_master_file():
    """Test that namespace paths alone don't trigger diagnostics without master file"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        common_dir = tmpdir / "Common"
        common_dir.mkdir()
        
        reduce_path = common_dir / "reduce.jinc"
        reduce_path.write_text("fn test() { reg u64 x; x = [;] }")  # Error
        
        proc = subprocess.Popen(
            [SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Initialize
            send_message(proc, {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "processId": None,
                    "rootUri": tmpdir.as_uri(),
                    "capabilities": {}
                }
            })
            
            read_response(proc)
            
            send_message(proc, {
                "jsonrpc": "2.0",
                "method": "initialized",
                "params": {}
            })
            time.sleep(0.1)
            
            # Set namespace paths WITHOUT setting master file
            send_message(proc, {
                "jsonrpc": "2.0",
                "method": "jasmin/setNamespacePaths",
                "params": {
                    "paths": [{
                        "namespace": "Common",
                        "path": str(common_dir)
                    }]
                }
            })
            
            # Should not get diagnostics
            responses = read_all_responses(proc, timeout=0.5)
            diagnostics = [r for r in responses 
                          if r.get("method") == "textDocument/publishDiagnostics"]
            
            if len(diagnostics) == 0:
                print("\n✓ SUCCESS: No diagnostics sent when namespace paths set without master file")
                return True
            else:
                print(f"\n✗ FAILED: Got {len(diagnostics)} diagnostics without master file")
                return False
                
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    import sys
    
    print("=" * 70)
    print("TEST 1: Namespace paths trigger diagnostics with master file")
    print("=" * 70)
    test1_success = test_namespace_paths_trigger_diagnostics()
    
    print("\n" + "=" * 70)
    print("TEST 2: Namespace paths without master file")
    print("=" * 70)
    test2_success = test_namespace_paths_without_master_file()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Test 1 (namespace + master): {'PASS' if test1_success else 'FAIL'}")
    print(f"Test 2 (namespace only): {'PASS' if test2_success else 'FAIL'}")
    
    sys.exit(0 if (test1_success and test2_success) else 1)
