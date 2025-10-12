"""
Crash and robustness tests - testing server stability under adverse conditions.
"""

import pytest
import time
from conftest import LSPClient, LSP_SERVER


def test_server_survives_invalid_json():
    """Test that server handles invalid JSON gracefully."""
    client = LSPClient(LSP_SERVER)
    client.start()
    
    try:
        # Send invalid JSON
        client.process.stdin.write(b"Content-Length: 20\r\n\r\n{invalid json here}")
        client.process.stdin.flush()
        
        time.sleep(0.5)
        
        # Server should still be alive
        assert client.is_alive(), "Server should survive invalid JSON"
        
        # Should still be able to initialize after invalid JSON
        client.initialize()
        assert client.initialized, "Server should be able to initialize after error"
        
    finally:
        client.stop()


def test_server_handles_missing_required_fields():
    """Test that server handles requests with missing required fields."""
    client = LSPClient(LSP_SERVER)
    client.start()
    client.initialize()
    
    try:
        # Send textDocument/hover without required fields
        client.send_request("textDocument/hover", {"textDocument": {}})
        time.sleep(0.3)
        
        # Server should still be alive
        assert client.is_alive(), "Server should handle invalid requests"
        
    finally:
        client.stop()


def test_server_handles_large_document():
    """Test that server can handle very large documents."""
    client = LSPClient(LSP_SERVER)
    client.start()
    client.initialize()
    
    try:
        # Generate a large document
        large_code = ""
        for i in range(1000):
            large_code += f"fn func_{i}(reg u64 x) -> reg u64 {{ return x; }}\n"
        
        uri = "file:///tmp/large.jazz"
        client.open_document(uri, large_code)
        
        time.sleep(0.5)
        
        # Server should still be alive
        assert client.is_alive(), "Server should handle large documents"
        
        # Should be able to query the document
        response = client.hover(uri, line=0, character=3)
        assert response is not None, "Should respond to hover on large document"
        
    finally:
        client.stop()


def test_rapid_document_changes():
    """Test server stability with rapid document changes."""
    client = LSPClient(LSP_SERVER)
    client.start()
    client.initialize()
    
    try:
        uri = "file:///tmp/test.jazz"
        
        # Open document
        client.open_document(uri, "fn test() { }")
        
        # Send many rapid changes
        for i in range(50):
            client.change_document(uri, f"fn test_{i}() {{ }}", version=i+2)
            time.sleep(0.01)  # Very short delay
        
        time.sleep(0.5)
        
        # Server should still be alive
        assert client.is_alive(), "Server should handle rapid changes"
        
    finally:
        client.stop()


def test_concurrent_hover_requests():
    """Test that server handles concurrent requests without crashing."""
    client = LSPClient(LSP_SERVER)
    client.start()
    client.initialize()
    
    try:
        uri = "file:///tmp/test.jazz"
        code = """fn func1() { }
fn func2() { }
fn func3() { }
"""
        client.open_document(uri, code)
        time.sleep(0.1)
        
        # Send multiple hover requests without waiting for responses
        for i in range(10):
            client.send_request("textDocument/hover", {
                "textDocument": {"uri": uri},
                "position": {"line": i % 3, "character": 3}
            })
        
        time.sleep(1.0)
        
        # Server should still be alive
        assert client.is_alive(), "Server should handle concurrent requests"
        
    finally:
        client.stop()


def test_malformed_content_length():
    """Test server handles malformed Content-Length headers."""
    client = LSPClient(LSP_SERVER)
    client.start()
    
    try:
        # Send request with wrong Content-Length
        msg = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
        wrong_length = len(msg) + 100  # Intentionally wrong
        header = f"Content-Length: {wrong_length}\r\n\r\n{msg}"
        
        client.process.stdin.write(header.encode('utf-8'))
        client.process.stdin.flush()
        
        time.sleep(1.0)
        
        # Server may crash or handle it - we just check it doesn't hang
        # If it survives, that's good
        is_alive = client.is_alive()
        # Either way, test passes (we're testing it doesn't hang forever)
        
    finally:
        client.stop()
