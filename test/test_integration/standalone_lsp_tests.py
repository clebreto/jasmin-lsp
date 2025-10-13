#!/usr/bin/env python3
"""
Comprehensive test suite for jasmin-lsp server.
Tests all LSP features: diagnostics, go-to-definition, find references, hover, etc.
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import time

class LSPClient:
    """Simple LSP client for testing"""
    
    def __init__(self, server_path: str):
        self.server_path = server_path
        self.process = None
        self.request_id = 0
        
    def start(self):
        """Start the LSP server process"""
        self.process = subprocess.Popen(
            [self.server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False  # Use bytes for precise control
        )
        
    def stop(self):
        """Stop the LSP server"""
        if self.process:
            self.send_notification("exit", {})
            self.process.terminate()
            self.process.wait(timeout=5)
            
    def send_message(self, message: Dict) -> None:
        """Send a JSON-RPC message with proper Content-Length header"""
        content = json.dumps(message)
        content_bytes = content.encode('utf-8')
        header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
        
        self.process.stdin.write(header.encode('utf-8'))
        self.process.stdin.write(content_bytes)
        self.process.stdin.flush()
        
    def read_message(self) -> Optional[Dict]:
        """Read a JSON-RPC message from the server"""
        # Read headers
        headers = {}
        while True:
            line = self.process.stdout.readline().decode('utf-8')
            if line == '\r\n' or line == '\n':
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
                
        if 'content-length' not in headers:
            return None
            
        # Read content
        content_length = int(headers['content-length'])
        content = self.process.stdout.read(content_length).decode('utf-8')
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"Failed to decode: {content}", file=sys.stderr)
            return None
            
    def send_request(self, method: str, params: Dict) -> int:
        """Send a request and return the request ID"""
        self.request_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        self.send_message(message)
        return self.request_id
        
    def send_notification(self, method: str, params: Dict) -> None:
        """Send a notification (no response expected)"""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self.send_message(message)
        
    def read_response(self, timeout: float = 2.0) -> Optional[Dict]:
        """Read responses until we get a response (not notification)"""
        start = time.time()
        while time.time() - start < timeout:
            msg = self.read_message()
            if msg and 'id' in msg:
                return msg
            elif msg and 'method' in msg:
                # It's a notification, keep reading
                continue
        return None
        
    def initialize(self, root_uri: str) -> Dict:
        """Initialize the LSP server"""
        params = {
            "processId": os.getpid(),
            "rootUri": root_uri,
            "capabilities": {
                "textDocument": {
                    "publishDiagnostics": {}
                }
            }
        }
        req_id = self.send_request("initialize", params)
        
        # Read response (might have configuration request first)
        response = self.read_response()
        
        # Send initialized notification
        self.send_notification("initialized", {})
        
        return response


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def add_pass(self, test_name: str):
        self.passed += 1
        print(f"✅ {test_name}")
        
    def add_fail(self, test_name: str, reason: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {reason}")
        print(f"❌ {test_name}: {reason}")
        
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*60}")
        return self.failed == 0


def file_uri(path: str) -> str:
    """Convert file path to URI"""
    abs_path = os.path.abspath(path)
    return f"file://{abs_path}"


def test_initialization(lsp_client: LSPClient, results: TestResults):
    """Test server initialization"""
    response = lsp_client.initialize(file_uri("."))
    
    if response and 'result' in response:
        capabilities = response['result'].get('capabilities', {})
        
        # Check for expected capabilities
        expected = [
            'textDocumentSync',
            'hoverProvider',
            'definitionProvider',
            'referencesProvider'
        ]
        
        for cap in expected:
            if cap in capabilities:
                results.add_pass(f"Initialization: {cap} capability")
            else:
                results.add_fail(f"Initialization: {cap} capability", "Not found")
    else:
        results.add_fail("Initialization", "No valid response")


def test_diagnostics(lsp_client: LSPClient, results: TestResults, test_file: str):
    """Test syntax diagnostics"""
    with open(test_file, 'r') as f:
        content = f.read()
        
    # Open document
    lsp_client.send_notification("textDocument/didOpen", {
        "textDocument": {
            "uri": file_uri(test_file),
            "languageId": "jasmin",
            "version": 1,
            "text": content
        }
    })
    
    # Read diagnostics notification
    time.sleep(0.5)  # Give server time to parse
    msg = client.read_message()
    
    if msg and msg.get('method') == 'textDocument/publishDiagnostics':
        diagnostics = msg['params'].get('diagnostics', [])
        
        if 'syntax_errors.jazz' in test_file:
            # Should have errors
            if len(diagnostics) > 0:
                results.add_pass(f"Diagnostics: Detected {len(diagnostics)} errors in {os.path.basename(test_file)}")
            else:
                results.add_fail(f"Diagnostics: {os.path.basename(test_file)}", "No errors detected")
        else:
            # Should be clean
            if len(diagnostics) == 0:
                results.add_pass(f"Diagnostics: Clean file {os.path.basename(test_file)}")
            else:
                results.add_fail(f"Diagnostics: {os.path.basename(test_file)}", f"Unexpected {len(diagnostics)} errors")
    else:
        results.add_fail(f"Diagnostics: {os.path.basename(test_file)}", "No diagnostics received")


def test_goto_definition(lsp_client: LSPClient, results: TestResults, test_file: str):
    """Test go-to-definition"""
    with open(test_file, 'r') as f:
        content = f.read()
        
    # Open document
    lsp_client.send_notification("textDocument/didOpen", {
        "textDocument": {
            "uri": file_uri(test_file),
            "languageId": "jasmin",
            "version": 1,
            "text": content
        }
    })
    
    time.sleep(0.3)
    
    # Find position of a function call (e.g., "add_numbers" call in main)
    lines = content.split('\n')
    test_position = None
    for i, line in enumerate(lines):
        if 'add_numbers(' in line and 'fn add_numbers' not in line:
            # Found a call, not the definition
            col = line.index('add_numbers')
            test_position = {"line": i, "character": col + 1}
            break
            
    if test_position:
        req_id = client.send_request("textDocument/definition", {
            "textDocument": {"uri": file_uri(test_file)},
            "position": test_position
        })
        
        response = client.read_response()
        
        if response and 'result' in response:
            result = response['result']
            if result and len(result) > 0:
                location = result[0] if isinstance(result, list) else result
                results.add_pass(f"Go-to-definition: Found definition in {os.path.basename(test_file)}")
            else:
                results.add_fail(f"Go-to-definition: {os.path.basename(test_file)}", "No definition found")
        else:
            results.add_fail(f"Go-to-definition: {os.path.basename(test_file)}", "No response")
    else:
        results.add_fail(f"Go-to-definition: {os.path.basename(test_file)}", "Could not find test position")


def test_find_references(lsp_client: LSPClient, results: TestResults, test_file: str):
    """Test find references"""
    with open(test_file, 'r') as f:
        content = f.read()
        
    # Open document
    lsp_client.send_notification("textDocument/didOpen", {
        "textDocument": {
            "uri": file_uri(test_file),
            "languageId": "jasmin",
            "version": 1,
            "text": content
        }
    })
    
    time.sleep(0.3)
    
    # Find position of 'value' parameter
    lines = content.split('\n')
    test_position = None
    for i, line in enumerate(lines):
        if 'reg u64 value' in line:
            col = line.index('value')
            test_position = {"line": i, "character": col + 1}
            break
            
    if test_position:
        req_id = client.send_request("textDocument/references", {
            "textDocument": {"uri": file_uri(test_file)},
            "position": test_position,
            "context": {"includeDeclaration": True}
        })
        
        response = client.read_response()
        
        if response and 'result' in response:
            result = response['result']
            if result and len(result) > 0:
                results.add_pass(f"Find references: Found {len(result)} references in {os.path.basename(test_file)}")
            else:
                results.add_fail(f"Find references: {os.path.basename(test_file)}", "No references found")
        else:
            results.add_fail(f"Find references: {os.path.basename(test_file)}", "No response")
    else:
        results.add_fail(f"Find references: {os.path.basename(test_file)}", "Could not find test position")


def test_hover(lsp_client: LSPClient, results: TestResults, test_file: str):
    """Test hover information"""
    with open(test_file, 'r') as f:
        content = f.read()
        
    # Open document
    lsp_client.send_notification("textDocument/didOpen", {
        "textDocument": {
            "uri": file_uri(test_file),
            "languageId": "jasmin",
            "version": 1,
            "text": content
        }
    })
    
    time.sleep(0.3)
    
    # Find position of a function definition
    lines = content.split('\n')
    test_position = None
    for i, line in enumerate(lines):
        if 'fn process_u64' in line:
            col = line.index('process_u64')
            test_position = {"line": i, "character": col + 1}
            break
            
    if test_position:
        req_id = client.send_request("textDocument/hover", {
            "textDocument": {"uri": file_uri(test_file)},
            "position": test_position
        })
        
        response = client.read_response()
        
        if response and 'result' in response and response['result']:
            hover = response['result']
            if 'contents' in hover:
                results.add_pass(f"Hover: Got hover info in {os.path.basename(test_file)}")
            else:
                results.add_fail(f"Hover: {os.path.basename(test_file)}", "No contents in hover")
        else:
            results.add_fail(f"Hover: {os.path.basename(test_file)}", "No hover response")
    else:
        results.add_fail(f"Hover: {os.path.basename(test_file)}", "Could not find test position")


def test_document_change(lsp_client: LSPClient, results: TestResults, test_file: str):
    """Test document change notifications"""
    with open(test_file, 'r') as f:
        content = f.read()
        
    # Open document
    lsp_client.send_notification("textDocument/didOpen", {
        "textDocument": {
            "uri": file_uri(test_file),
            "languageId": "jasmin",
            "version": 1,
            "text": content
        }
    })
    
    time.sleep(0.3)
    
    # Change document
    new_content = content + "\n// New comment\n"
    lsp_client.send_notification("textDocument/didChange", {
        "textDocument": {
            "uri": file_uri(test_file),
            "version": 2
        },
        "contentChanges": [
            {"text": new_content}
        ]
    })
    
    time.sleep(0.3)
    
    # Should receive new diagnostics
    msg = client.read_message()
    if msg and msg.get('method') == 'textDocument/publishDiagnostics':
        results.add_pass(f"Document change: Received updated diagnostics for {os.path.basename(test_file)}")
    else:
        results.add_fail(f"Document change: {os.path.basename(test_file)}", "No diagnostics after change")


def test_document_close(lsp_client: LSPClient, results: TestResults, test_file: str):
    """Test document close notification"""
    with open(test_file, 'r') as f:
        content = f.read()
        
    # Open document
    lsp_client.send_notification("textDocument/didOpen", {
        "textDocument": {
            "uri": file_uri(test_file),
            "languageId": "jasmin",
            "version": 1,
            "text": content
        }
    })
    
    time.sleep(0.2)
    
    # Close document
    lsp_client.send_notification("textDocument/didClose", {
        "textDocument": {"uri": file_uri(test_file)}
    })
    
    time.sleep(0.2)
    results.add_pass(f"Document close: Successfully closed {os.path.basename(test_file)}")


def main():
    """Main test runner"""
    # Get server path
    server_path = os.environ.get(
        'LSP_SERVER_PATH',
        '_build/default/jasmin-lsp/jasmin_lsp.exe'
    )
    
    if not os.path.exists(server_path):
        print(f"Error: LSP server not found at {server_path}")
        print("Build it with: pixi run build")
        print("Or set LSP_SERVER_PATH environment variable")
        return 1
        
    # Test fixtures directory
    fixtures_dir = Path(__file__).parent / 'fixtures'
    
    test_files = {
        'simple': fixtures_dir / 'simple_function.jazz',
        'errors': fixtures_dir / 'syntax_errors.jazz',
        'references': fixtures_dir / 'references_test.jazz',
        'types': fixtures_dir / 'types_test.jazz',
        'arrays': fixtures_dir / 'arrays_test.jazz',
    }
    
    # Verify test files exist
    for name, path in test_files.items():
        if not path.exists():
            print(f"Error: Test file not found: {path}")
            return 1
            
    results = TestResults()
    
    print("Starting jasmin-lsp test suite...")
    print(f"Server: {server_path}\n")
    
    # Test 1: Initialization
    print("=" * 60)
    print("Test 1: Server Initialization")
    print("=" * 60)
    client = LSPClient(server_path)
    lsp_client.start()
    test_initialization(client, results)
    lsp_client.stop()
    
    # Test 2: Diagnostics
    print("\n" + "=" * 60)
    print("Test 2: Syntax Diagnostics")
    print("=" * 60)
    client = LSPClient(server_path)
    lsp_client.start()
    lsp_client.initialize(file_uri("."))
    test_diagnostics(client, results, str(test_files['simple']))
    test_diagnostics(client, results, str(test_files['errors']))
    lsp_client.stop()
    
    # Test 3: Go to Definition
    print("\n" + "=" * 60)
    print("Test 3: Go to Definition")
    print("=" * 60)
    client = LSPClient(server_path)
    lsp_client.start()
    lsp_client.initialize(file_uri("."))
    test_goto_definition(client, results, str(test_files['simple']))
    lsp_client.stop()
    
    # Test 4: Find References
    print("\n" + "=" * 60)
    print("Test 4: Find References")
    print("=" * 60)
    client = LSPClient(server_path)
    lsp_client.start()
    lsp_client.initialize(file_uri("."))
    test_find_references(client, results, str(test_files['references']))
    lsp_client.stop()
    
    # Test 5: Hover Information
    print("\n" + "=" * 60)
    print("Test 5: Hover Information")
    print("=" * 60)
    client = LSPClient(server_path)
    lsp_client.start()
    lsp_client.initialize(file_uri("."))
    test_hover(client, results, str(test_files['types']))
    lsp_client.stop()
    
    # Test 6: Document Lifecycle
    print("\n" + "=" * 60)
    print("Test 6: Document Lifecycle")
    print("=" * 60)
    client = LSPClient(server_path)
    lsp_client.start()
    lsp_client.initialize(file_uri("."))
    test_document_change(client, results, str(test_files['simple']))
    test_document_close(client, results, str(test_files['simple']))
    lsp_client.stop()
    
    # Summary
    success = results.summary()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
