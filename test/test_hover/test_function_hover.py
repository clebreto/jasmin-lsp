#!/usr/bin/env python3
"""Test hover on function name"""

import subprocess
import json
import sys
from pathlib import Path

LSP_SERVER = Path(__file__).parent.parent.parent / "_build/default/jasmin-lsp/jasmin_lsp.exe"

TEST_CONTENT = """fn process_u8(reg u8 byte_val) -> reg u8 {
  reg u8 result;
  result = byte_val + #1;
  return result;
}
"""

def send_lsp_request(request):
    content = json.dumps(request)
    header = f"Content-Length: {len(content)}\r\n\r\n"
    return header + content

def read_lsp_response(proc, expected_id=None):
    max_attempts = 20
    for _ in range(max_attempts):
        line = proc.stdout.readline()
        if not line:
            return None
        if line.startswith("Content-Length"):
            content_length = int(line.split(":")[1].strip())
            proc.stdout.readline()
            content = proc.stdout.read(content_length)
            response = json.loads(content)
            if expected_id is None or response.get("id") == expected_id:
                return response
    return None

def test_hover_on_function_name():
    test_file_uri = "file:///tmp/test_fn_hover.jazz"
    
    proc = subprocess.Popen(
        [str(LSP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    # Initialize
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"processId": None, "rootUri": "file:///tmp", "capabilities": {}}
    }
    proc.stdin.write(send_lsp_request(init_request))
    proc.stdin.flush()
    read_lsp_response(proc)
    
    # Initialized
    initialized = {"jsonrpc": "2.0", "method": "initialized", "params": {}}
    proc.stdin.write(send_lsp_request(initialized))
    proc.stdin.flush()
    
    # Open document
    did_open = {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": test_file_uri,
                "languageId": "jasmin",
                "version": 1,
                "text": TEST_CONTENT
            }
        }
    }
    proc.stdin.write(send_lsp_request(did_open))
    proc.stdin.flush()
    
    import time
    time.sleep(0.2)
    
    # Hover on function name "process_u8" at line 0, character 5 (the 'r' in process_u8)
    print("Hovering on function name 'process_u8' at line 0, character 5...")
    hover_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": test_file_uri},
            "position": {"line": 0, "character": 5}
        }
    }
    proc.stdin.write(send_lsp_request(hover_request))
    proc.stdin.flush()
    
    response = read_lsp_response(proc, expected_id=2)
    
    if not response:
        print("❌ No response")
        proc.terminate()
        return False
        
    print(f"\nResponse: {json.dumps(response, indent=2)}")
    
    if "error" in response:
        print(f"❌ Error: {response['error']['message']}")
        proc.terminate()
        return False
    
    if "result" in response and response["result"] and "contents" in response["result"]:
        hover_content = response["result"]["contents"]["value"]
        print(f"\n✅ Hover on function name works: {hover_content}")
    else:
        print("❌ No hover information on function name")
        proc.terminate()
        return False
    
    # Hover on variable "result" at line 2, character 2
    print("\nHovering on variable 'result' at line 2, character 2...")
    hover_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": test_file_uri},
            "position": {"line": 2, "character": 2}
        }
    }
    proc.stdin.write(send_lsp_request(hover_request))
    proc.stdin.flush()
    
    response = read_lsp_response(proc, expected_id=3)
    
    if not response:
        print("❌ No response")
        proc.terminate()
        return False
        
    print(f"\nResponse: {json.dumps(response, indent=2)}")
    
    if "error" in response:
        print(f"❌ Error: {response['error']['message']}")
        proc.terminate()
        return False
    
    if "result" in response and response["result"] and "contents" in response["result"]:
        hover_content = response["result"]["contents"]["value"]
        print(f"\n✅ Hover content: {hover_content}")
        if "u8" in hover_content:
            print("✅ Variable hover shows type information!")
        proc.terminate()
        return True
    else:
        print("❌ No hover information")
        proc.terminate()
        return False
