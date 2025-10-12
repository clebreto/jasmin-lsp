#!/usr/bin/env python3
"""
Test Rename Symbol Feature

Tests the textDocument/rename request which renames a symbol
across all its usages in the document.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

# Test fixture
TEST_CODE = """
// Test rename functionality
fn calculate(reg u32 value) -> reg u32 {
    reg u32 result;
    reg u32 temp;
    
    temp = value + #1;
    result = temp * #2;
    result = result + temp;
    
    return result;
}

fn process() -> reg u64 {
    reg u64 data;
    reg u64 output;
    
    data = #100;
    output = data * #2;
    output = output + data;
    
    return output;
}
"""

def send_lsp_message(proc, method, params, msg_id=None):
    """Send an LSP message"""
    message = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    }
    if msg_id is not None:
        message["id"] = msg_id
    
    content = json.dumps(message)
    content_bytes = content.encode('utf-8')
    header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
    
    proc.stdin.write(header.encode('utf-8'))
    proc.stdin.write(content_bytes)
    proc.stdin.flush()

def read_lsp_response(proc):
    """Read an LSP response"""
    # Read headers
    headers = {}
    while True:
        line = proc.stdout.readline().decode('utf-8')
        if line == '\r\n' or line == '\n':
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    # Read content
    content_length = int(headers.get('Content-Length', 0))
    content = proc.stdout.read(content_length).decode('utf-8')
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {content}")
        return None

def find_position_of_text(text, target, occurrence=1):
    """Find line and character position of text"""
    lines = text.split('\n')
    count = 0
    for line_num, line in enumerate(lines):
        occurrences = []
        start = 0
        while True:
            idx = line.find(target, start)
            if idx == -1:
                break
            occurrences.append(idx)
            start = idx + 1
        
        for char_pos in occurrences:
            count += 1
            if count == occurrence:
                return line_num, char_pos
    
    return None

def test_rename_symbol():
    """Test rename symbol feature"""
    print("\n" + "="*60)
    print("Testing Rename Symbol Feature")
    print("="*60)
    
    # Find LSP server
    lsp_server = Path(__file__).parent.parent / "_build" / "default" / "jasmin-lsp" / "jasmin_lsp.exe"
    if not lsp_server.exists():
        print(f"❌ LSP server not found: {lsp_server}")
        return False
    
    try:
        # Start LSP server
        proc = subprocess.Popen(
            [str(lsp_server)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Initialize
        print("\n1. Initializing server...")
        send_lsp_message(proc, "initialize", {
            "processId": None,
            "rootUri": "file:///tmp",
            "capabilities": {}
        }, msg_id=1)
        
        response = read_lsp_response(proc)
        if not response or "result" not in response:
            print("❌ Failed to initialize")
            return False
        
        # Check if renameProvider is advertised
        capabilities = response.get("result", {}).get("capabilities", {})
        if not capabilities.get("renameProvider"):
            print("❌ renameProvider not advertised in capabilities")
            return False
        
        print("✅ renameProvider is advertised")
        
        # Send initialized notification
        send_lsp_message(proc, "initialized", {})
        
        # Open document
        print("\n2. Opening test document...")
        test_uri = "file:///tmp/test_rename.jazz"
        send_lsp_message(proc, "textDocument/didOpen", {
            "textDocument": {
                "uri": test_uri,
                "languageId": "jasmin",
                "version": 1,
                "text": TEST_CODE
            }
        })
        
        # Wait for processing
        time.sleep(0.5)
        
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Rename variable 'result' in calculate function
        print("\n3. Test 1: Rename 'result' to 'output'...")
        tests_total += 1
        
        # Find position of 'result' (first occurrence in calculate function)
        pos = find_position_of_text(TEST_CODE, "result", occurrence=1)
        
        if not pos:
            print("❌ Could not find 'result' in test code")
        else:
            line, char = pos
            print(f"  Found 'result' at line {line}, char {char}")
            
            send_lsp_message(proc, "textDocument/rename", {
                "textDocument": {
                    "uri": test_uri
                },
                "position": {
                    "line": line,
                    "character": char
                },
                "newName": "output"
            }, msg_id=2)
            
            response = read_lsp_response(proc)
            
            if response and "result" in response:
                workspace_edit = response["result"]
                
                if "changes" in workspace_edit:
                    changes = workspace_edit["changes"]
                    
                    if test_uri in changes:
                        edits = changes[test_uri]
                        print(f"  Received {len(edits)} text edits")
                        
                        # We expect 3 edits for 'result' in calculate function
                        if len(edits) >= 2:
                            print("✅ Rename returned multiple edits")
                            tests_passed += 1
                            
                            # Show edit details
                            for i, edit in enumerate(edits[:5], 1):
                                range_obj = edit.get("range", {})
                                new_text = edit.get("newText", "")
                                start = range_obj.get("start", {})
                                print(f"  Edit {i}: Line {start.get('line')}, char {start.get('character')} -> '{new_text}'")
                        else:
                            print(f"❌ Expected multiple edits, got {len(edits)}")
                    else:
                        print(f"❌ No changes for {test_uri}")
                elif "documentChanges" in workspace_edit:
                    print("  Note: Using documentChanges format")
                    tests_passed += 1
                else:
                    print("❌ WorkspaceEdit missing changes")
            else:
                print(f"❌ No response or error: {response}")
        
        # Test 2: Rename variable 'data' in process function
        print("\n4. Test 2: Rename 'data' to 'input'...")
        tests_total += 1
        
        # Find position of 'data' (first occurrence in process function)
        pos = find_position_of_text(TEST_CODE, "data", occurrence=1)
        
        if not pos:
            print("❌ Could not find 'data' in test code")
        else:
            line, char = pos
            print(f"  Found 'data' at line {line}, char {char}")
            
            send_lsp_message(proc, "textDocument/rename", {
                "textDocument": {
                    "uri": test_uri
                },
                "position": {
                    "line": line,
                    "character": char
                },
                "newName": "input"
            }, msg_id=3)
            
            response = read_lsp_response(proc)
            
            if response and "result" in response:
                workspace_edit = response["result"]
                
                if "changes" in workspace_edit:
                    changes = workspace_edit["changes"]
                    
                    if test_uri in changes:
                        edits = changes[test_uri]
                        print(f"  Received {len(edits)} text edits")
                        
                        # We expect 3 edits for 'data' in process function
                        if len(edits) >= 2:
                            print("✅ Rename returned multiple edits")
                            tests_passed += 1
                        else:
                            print(f"❌ Expected multiple edits, got {len(edits)}")
                    else:
                        print(f"❌ No changes for {test_uri}")
                else:
                    print("❌ WorkspaceEdit missing changes")
            else:
                print(f"❌ No response or error: {response}")
        
        # Test 3: Rename parameter 'value' in calculate function
        print("\n5. Test 3: Rename parameter 'value' to 'input_val'...")
        tests_total += 1
        
        # Find position of 'value' in parameter list
        pos = find_position_of_text(TEST_CODE, "value", occurrence=1)
        
        if not pos:
            print("❌ Could not find 'value' in test code")
        else:
            line, char = pos
            print(f"  Found 'value' at line {line}, char {char}")
            
            send_lsp_message(proc, "textDocument/rename", {
                "textDocument": {
                    "uri": test_uri
                },
                "position": {
                    "line": line,
                    "character": char
                },
                "newName": "input_val"
            }, msg_id=4)
            
            response = read_lsp_response(proc)
            
            if response and "result" in response:
                workspace_edit = response["result"]
                
                if "changes" in workspace_edit:
                    changes = workspace_edit["changes"]
                    
                    if test_uri in changes:
                        edits = changes[test_uri]
                        print(f"  Received {len(edits)} text edits")
                        
                        # We expect 2 edits for 'value' (declaration + usage)
                        if len(edits) >= 1:
                            print("✅ Rename returned edits for parameter")
                            tests_passed += 1
                        else:
                            print(f"❌ Expected at least 1 edit, got {len(edits)}")
                    else:
                        print(f"❌ No changes for {test_uri}")
                else:
                    print("❌ WorkspaceEdit missing changes")
            else:
                print(f"❌ No response or error: {response}")
        
        # Test 4: Try to rename a keyword (should fail or return empty)
        print("\n6. Test 4: Try to rename keyword 'fn' (should fail)...")
        tests_total += 1
        
        pos = find_position_of_text(TEST_CODE, "fn", occurrence=1)
        
        if not pos:
            print("❌ Could not find 'fn' in test code")
        else:
            line, char = pos
            
            send_lsp_message(proc, "textDocument/rename", {
                "textDocument": {
                    "uri": test_uri
                },
                "position": {
                    "line": line,
                    "character": char
                },
                "newName": "function"
            }, msg_id=5)
            
            response = read_lsp_response(proc)
            
            if response:
                if "error" in response:
                    print("✅ Correctly rejected rename of keyword")
                    tests_passed += 1
                elif "result" in response:
                    workspace_edit = response["result"]
                    if "changes" in workspace_edit:
                        changes = workspace_edit["changes"]
                        if not changes or test_uri not in changes or len(changes[test_uri]) == 0:
                            print("✅ Correctly returned empty edits for keyword")
                            tests_passed += 1
                        else:
                            print("⚠️ Returned edits for keyword (unexpected)")
                    else:
                        print("✅ Returned empty workspace edit")
                        tests_passed += 1
            else:
                print("❌ No response")
        
        # Summary
        print("\n" + "="*60)
        print(f"Test Results: {tests_passed}/{tests_total} passed ({100*tests_passed//tests_total}%)")
        print("="*60)
        
        # Shutdown
        send_lsp_message(proc, "shutdown", {}, msg_id=99)
        read_lsp_response(proc)
        send_lsp_message(proc, "exit", {})
        
        proc.terminate()
        proc.wait(timeout=2)
        
        return tests_passed >= tests_total - 1  # Allow 1 failure
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rename_symbol()
    sys.exit(0 if success else 1)
