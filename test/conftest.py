"""
Pytest configuration and shared fixtures for jasmin-lsp tests.

This module provides common utilities and fixtures used across all test categories.
"""

import json
import subprocess
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import pytest


# Get the LSP server path
LSP_SERVER = Path(__file__).parent.parent / "_build" / "default" / "jasmin-lsp" / "jasmin_lsp.exe"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class LSPClient:
    """
    A helper class to interact with the jasmin-lsp server via JSON-RPC.
    
    This class handles:
    - Starting and stopping the LSP server process
    - Sending JSON-RPC requests and notifications
    - Reading JSON-RPC responses
    - Managing document lifecycle (open, change, close)
    """
    
    def __init__(self, server_path: Path = LSP_SERVER):
        """Initialize the LSP client with a server path."""
        self.server_path = server_path
        self.process = None
        self.msg_id = 0
        self.initialized = False
        
    def start(self):
        """Start the LSP server process."""
        if not self.server_path.exists():
            raise FileNotFoundError(
                f"LSP server not found at {self.server_path}. "
                "Please build it first with: pixi run build"
            )
        
        self.process = subprocess.Popen(
            [str(self.server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        
    def stop(self):
        """Stop the LSP server process."""
        if self.process:
            try:
                self.send_notification("exit")
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            finally:
                self.process = None
                self.initialized = False
    
    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        Send a JSON-RPC request to the server.
        
        Args:
            method: The LSP method name (e.g., "textDocument/hover")
            params: The parameters for the request
            
        Returns:
            The request ID
        """
        self.msg_id += 1
        msg = {
            "jsonrpc": "2.0",
            "id": self.msg_id,
            "method": method
        }
        if params is not None:
            msg["params"] = params
        
        self._send_message(msg)
        return self.msg_id
    
    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """
        Send a JSON-RPC notification to the server (no response expected).
        
        Args:
            method: The LSP method name (e.g., "textDocument/didOpen")
            params: The parameters for the notification
        """
        msg = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params is not None:
            msg["params"] = params
        
        self._send_message(msg)
    
    def _send_message(self, msg: Dict[str, Any]):
        """Internal method to send a JSON-RPC message with proper headers."""
        msg_str = json.dumps(msg)
        msg_bytes = msg_str.encode('utf-8')
        header = f"Content-Length: {len(msg_bytes)}\r\n\r\n"
        
        self.process.stdin.write(header.encode('utf-8'))
        self.process.stdin.write(msg_bytes)
        self.process.stdin.flush()
    
    def read_response(self, timeout: float = 5.0, expect_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Read a JSON-RPC response from the server.
        
        Args:
            timeout: Maximum time to wait for a response
            expect_id: If provided, keep reading until we get a response with this ID
            
        Returns:
            The parsed JSON response, or None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Read headers
            headers = {}
            while True:
                line = self.process.stdout.readline()
                if not line:
                    return None
                
                line = line.decode('utf-8').strip()
                if not line:
                    break
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
            
            # Read content
            content_length = int(headers.get('Content-Length', 0))
            if content_length == 0:
                return None
            
            content = self.process.stdout.read(content_length)
            response = json.loads(content.decode('utf-8'))
            
            # If we're looking for a specific ID, check if this is it
            if expect_id is not None:
                # Skip notifications (no id field)
                if "id" not in response:
                    continue
                # Return if this is the response we want
                if response.get("id") == expect_id:
                    return response
                # Otherwise keep reading
                continue
            
            # If not looking for specific ID, return first response
            return response
        
        return None
    
    def initialize(self, root_uri: str = "file:///tmp") -> Dict[str, Any]:
        """
        Send the initialize request and wait for response.
        
        Args:
            root_uri: The root URI of the workspace
            
        Returns:
            The initialize response
        """
        params = {
            "processId": os.getpid(),
            "rootUri": root_uri,
            "capabilities": {
                "textDocument": {
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "definition": {"linkSupport": True},
                    "references": {"context": {"includeDeclaration": True}},
                }
            }
        }
        
        req_id = self.send_request("initialize", params)
        response = self.read_response()
        
        # Send initialized notification
        self.send_notification("initialized", {})
        self.initialized = True
        
        return response
    
    def open_document(self, uri: str, text: str, language_id: str = "jasmin", version: int = 1):
        """
        Open a document in the LSP server.
        
        Args:
            uri: The document URI
            text: The document content
            language_id: The language ID (default: "jasmin")
            version: The document version (default: 1)
        """
        params = {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": version,
                "text": text
            }
        }
        self.send_notification("textDocument/didOpen", params)
        # Give server time to process
        time.sleep(0.1)
    
    def close_document(self, uri: str):
        """
        Close a document in the LSP server.
        
        Args:
            uri: The document URI
        """
        params = {"textDocument": {"uri": uri}}
        self.send_notification("textDocument/didClose", params)
    
    def change_document(self, uri: str, text: str, version: int):
        """
        Send a document change notification.
        
        Args:
            uri: The document URI
            text: The new document content
            version: The new document version
        """
        params = {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": [{"text": text}]
        }
        self.send_notification("textDocument/didChange", params)
        time.sleep(0.1)
    
    def hover(self, uri: str, line: int, character: int) -> Optional[Dict[str, Any]]:
        """
        Request hover information at a position.
        
        Args:
            uri: The document URI
            line: The line number (0-indexed)
            character: The character position (0-indexed)
            
        Returns:
            The hover response
        """
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character}
        }
        req_id = self.send_request("textDocument/hover", params)
        return self.read_response(expect_id=req_id)
    
    def definition(self, uri: str, line: int, character: int) -> Optional[Dict[str, Any]]:
        """
        Request go-to-definition at a position.
        
        Args:
            uri: The document URI
            line: The line number (0-indexed)
            character: The character position (0-indexed)
            
        Returns:
            The definition response
        """
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character}
        }
        req_id = self.send_request("textDocument/definition", params)
        return self.read_response(expect_id=req_id)
    
    def references(self, uri: str, line: int, character: int, 
                   include_declaration: bool = True) -> Optional[Dict[str, Any]]:
        """
        Request find references at a position.
        
        Args:
            uri: The document URI
            line: The line number (0-indexed)
            character: The character position (0-indexed)
            include_declaration: Whether to include the declaration
            
        Returns:
            The references response
        """
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": include_declaration}
        }
        req_id = self.send_request("textDocument/references", params)
        return self.read_response(expect_id=req_id)
    
    def document_symbols(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Request document symbols.
        
        Args:
            uri: The document URI
            
        Returns:
            The document symbols response
        """
        params = {"textDocument": {"uri": uri}}
        req_id = self.send_request("textDocument/documentSymbol", params)
        return self.read_response(expect_id=req_id)
    
    def workspace_symbols(self, query: str = "") -> Optional[Dict[str, Any]]:
        """
        Request workspace symbols.
        
        Args:
            query: The search query
            
        Returns:
            The workspace symbols response
        """
        params = {"query": query}
        req_id = self.send_request("workspace/symbol", params)
        return self.read_response(expect_id=req_id)
    
    def rename(self, uri: str, line: int, character: int, 
               new_name: str) -> Optional[Dict[str, Any]]:
        """
        Request rename symbol.
        
        Args:
            uri: The document URI
            line: The line number (0-indexed)
            character: The character position (0-indexed)
            new_name: The new name for the symbol
            
        Returns:
            The rename response
        """
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "newName": new_name
        }
        req_id = self.send_request("textDocument/rename", params)
        return self.read_response(expect_id=req_id)
    
    def is_alive(self) -> bool:
        """Check if the server process is still running."""
        return self.process is not None and self.process.poll() is None
    
    def collect_diagnostics(self, timeout: float = 1.0) -> Dict[str, List[Dict[str, Any]]]:
        """
        Collect diagnostic notifications from the server.
        
        Args:
            timeout: Maximum time to wait for diagnostics
            
        Returns:
            Dictionary mapping URIs to lists of diagnostics
        """
        import select
        
        diagnostics_by_uri = {}
        end_time = time.time() + timeout
        attempts = 0
        
        while time.time() < end_time:
            remaining = end_time - time.time()
            if remaining <= 0:
                break
            
            try:
                # Check if there's data available
                ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                if ready:
                    resp = self.read_response(timeout=0.1)
                    if resp:
                        if resp.get('method') == 'textDocument/publishDiagnostics':
                            uri = resp['params']['uri']
                            diagnostics = resp['params']['diagnostics']
                            diagnostics_by_uri[uri] = diagnostics
                        attempts = 0  # Reset attempts if we got something
                    else:
                        attempts += 1
                else:
                    attempts += 1
                
                # If no data for a while, stop waiting
                if attempts > 5:
                    break
                    
                time.sleep(0.05)
            except Exception:
                attempts += 1
                time.sleep(0.05)
        
        return diagnostics_by_uri
    
    def set_master_file(self, uri: str):
        """
        Set the master file for the workspace.
        
        Args:
            uri: The URI of the master file
        """
        self.send_notification("jasmin/setMasterFile", {"uri": uri})


# Pytest Fixtures

@pytest.fixture
def lsp_server_path():
    """Provide the path to the LSP server executable."""
    return LSP_SERVER


@pytest.fixture
def fixtures_dir():
    """Provide the path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def lsp_client(lsp_server_path):
    """
    Provide an LSP client that starts and stops automatically.
    
    The client is initialized and ready to use. It will be
    properly shut down after the test completes.
    """
    client = LSPClient(lsp_server_path)
    client.start()
    client.initialize()
    
    yield client
    
    client.stop()


@pytest.fixture
def temp_document(lsp_client, tmp_path):
    """
    Provide a helper to create and open temporary documents.
    
    Usage:
        def test_something(temp_document):
            uri = temp_document("fn test() { }")
            # Document is opened in LSP server
    """
    opened_documents = []
    
    def create_temp_doc(content: str, filename: str = "test.jazz") -> str:
        file_path = tmp_path / filename
        file_path.write_text(content)
        uri = f"file://{file_path}"
        lsp_client.open_document(uri, content)
        opened_documents.append(uri)
        return uri
    
    yield create_temp_doc
    
    # Cleanup
    for uri in opened_documents:
        lsp_client.close_document(uri)


@pytest.fixture
def fixture_file(lsp_client, fixtures_dir):
    """
    Provide a helper to open fixture files.
    
    Usage:
        def test_something(fixture_file):
            uri = fixture_file("simple_function.jazz")
            # Fixture file is opened in LSP server
    """
    opened_documents = []
    
    def open_fixture(filename: str) -> tuple[str, str]:
        """
        Open a fixture file and return (uri, content).
        
        Args:
            filename: The fixture filename
            
        Returns:
            A tuple of (file_uri, file_content)
        """
        file_path = fixtures_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Fixture not found: {filename}")
        
        content = file_path.read_text()
        uri = f"file://{file_path.absolute()}"
        lsp_client.open_document(uri, content)
        opened_documents.append(uri)
        return uri, content
    
    yield open_fixture
    
    # Cleanup
    for uri in opened_documents:
        lsp_client.close_document(uri)


def file_uri(path: Path) -> str:
    """Convert a file path to a file:// URI."""
    return f"file://{path.absolute()}"


def assert_response_ok(response: Optional[Dict[str, Any]], request_type: str = "request"):
    """
    Assert that a response is not None and doesn't contain an error.
    
    Args:
        response: The JSON-RPC response
        request_type: Description of the request type for error messages
    """
    assert response is not None, f"{request_type} returned no response"
    assert "error" not in response, f"{request_type} returned error: {response.get('error')}"


def assert_has_result(response: Dict[str, Any], request_type: str = "request"):
    """
    Assert that a response has a 'result' field.
    
    Args:
        response: The JSON-RPC response
        request_type: Description of the request type for error messages
    """
    assert "result" in response, f"{request_type} has no 'result' field"


def assert_result_not_null(response: Dict[str, Any], request_type: str = "request"):
    """
    Assert that a response's result is not null.
    
    Args:
        response: The JSON-RPC response
        request_type: Description of the request type for error messages
    """
    assert_has_result(response, request_type)
    assert response["result"] is not None, f"{request_type} returned null result"
