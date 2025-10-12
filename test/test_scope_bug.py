#!/usr/bin/env python3
"""
Test for scope resolution bug where go-to-definition on a variable
in one function jumps to a variable with the same name in a different function.
"""

import socket
import json
import sys
import time

class LSPClient:
    def __init__(self):
        self.sock = None
        self.request_id = 0
    
    def connect(self, port=9257):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", port))
        time.sleep(0.1)
    
    def send_message(self, method, params):
        self.request_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        self.sock.sendall(header.encode() + content.encode())
        return self.request_id
    
    def send_notification(self, method, params):
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        self.sock.sendall(header.encode() + content.encode())
    
    def receive_response(self):
        # Read header
        header = b""
        while not header.endswith(b"\r\n\r\n"):
            chunk = self.sock.recv(1)
            if not chunk:
                return None
            header += chunk
        
        # Parse content length
        header_str = header.decode()
        content_length = int(header_str.split("Content-Length: ")[1].split("\r\n")[0])
        
        # Read content
        content = b""
        while len(content) < content_length:
            chunk = self.sock.recv(content_length - len(content))
            if not chunk:
                return None
            content += chunk
        
        return json.loads(content.decode())
    
    def close(self):
        if self.sock:
            self.sock.close()

def test_scope_resolution():
    """Test that go-to-definition respects function scope"""
    
    # Create test file with two functions, each with a 'status' variable
    test_content = """export fn first_function(
    #public reg ptr u8[32] sig
) -> #public reg u32
{
    reg u32 status;
    
    status = 0;
    
    return status;
}

export fn second_function(
    #public reg ptr u8[64] data
) -> #public reg u32 {
    reg u32 status;
    
    status = 1;
    status = status;
    
    return status;
}
"""
    
    test_file = "/tmp/test_scope_bug.jazz"
    with open(test_file, "w") as f:
        f.write(test_content)
    
    print("🔍 Testing scope resolution bug...")
    print("=" * 60)
    
    client = LSPClient()
    try:
        client.connect()
        print("✓ Connected to LSP server")
        
        # Initialize
        init_id = client.send_message("initialize", {
            "processId": None,
            "rootUri": "file:///tmp",
            "capabilities": {}
        })
        init_response = client.receive_response()
        assert init_response["id"] == init_id
        print("✓ Initialized")
        
        client.send_notification("initialized", {})
        
        # Open document
        file_uri = f"file://{test_file}"
        client.send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": file_uri,
                "languageId": "jasmin",
                "version": 1,
                "text": test_content
            }
        })
        time.sleep(0.5)
        print("✓ Document opened")
        
        # Test 1: Go to definition on 'status' in first function (line 6, should stay in first function)
        print("\n📍 Test 1: 'status' in first_function (line 6)")
        def_id = client.send_message("textDocument/definition", {
            "textDocument": {"uri": file_uri},
            "position": {"line": 6, "character": 4}  # The 'status' in 'status = 0;'
        })
        
        def_response = client.receive_response()
        print(f"Response: {json.dumps(def_response, indent=2)}")
        
        if "result" in def_response and def_response["result"]:
            location = def_response["result"][0] if isinstance(def_response["result"], list) else def_response["result"]
            def_line = location["range"]["start"]["line"]
            print(f"Definition found at line {def_line}")
            
            # Should be line 4 (the declaration in first_function)
            if def_line == 4:
                print("✅ CORRECT: Jumped to declaration in first_function")
            else:
                print(f"❌ WRONG: Expected line 4, got line {def_line}")
        else:
            print("❌ ERROR: No definition found")
        
        # Test 2: Go to definition on second 'status' in 'status = status;' in second function
        # This should jump to line 15 (declaration in second_function), NOT line 4 (first_function)
        print("\n📍 Test 2: Second 'status' in 'status = status;' in second_function (line 18)")
        def_id = client.send_message("textDocument/definition", {
            "textDocument": {"uri": file_uri},
            "position": {"line": 18, "character": 15}  # The second 'status' in 'status = status;'
        })
        
        def_response = client.receive_response()
        print(f"Response: {json.dumps(def_response, indent=2)}")
        
        if "result" in def_response and def_response["result"]:
            location = def_response["result"][0] if isinstance(def_response["result"], list) else def_response["result"]
            def_line = location["range"]["start"]["line"]
            print(f"Definition found at line {def_line}")
            
            # Should be line 15 (the declaration in second_function)
            if def_line == 15:
                print("✅ CORRECT: Jumped to declaration in second_function")
            else:
                print(f"❌ BUG REPRODUCED: Expected line 15, got line {def_line}")
                print("    The LSP jumped to 'status' in first_function instead!")
                return False
        else:
            print("❌ ERROR: No definition found")
        
        # Test 3: Go to definition on first 'status' in 'status = status;' (should also go to line 15)
        print("\n📍 Test 3: First 'status' in 'status = status;' in second_function (line 18)")
        def_id = client.send_message("textDocument/definition", {
            "textDocument": {"uri": file_uri},
            "position": {"line": 18, "character": 4}  # The first 'status' in 'status = status;'
        })
        
        def_response = client.receive_response()
        print(f"Response: {json.dumps(def_response, indent=2)}")
        
        if "result" in def_response and def_response["result"]:
            location = def_response["result"][0] if isinstance(def_response["result"], list) else def_response["result"]
            def_line = location["range"]["start"]["line"]
            print(f"Definition found at line {def_line}")
            
            if def_line == 15:
                print("✅ CORRECT: Jumped to declaration in second_function")
            else:
                print(f"❌ WRONG: Expected line 15, got line {def_line}")
        else:
            print("❌ ERROR: No definition found")
        
        client.send_notification("textDocument/didClose", {
            "textDocument": {"uri": file_uri}
        })
        
        return True
        
    finally:
        client.close()
        print("\n✓ Closed connection")

if __name__ == "__main__":
    try:
        success = test_scope_resolution()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
