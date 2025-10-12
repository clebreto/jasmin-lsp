#!/usr/bin/env python3
"""
Comprehensive crash testing for jasmin-lsp server.
Tests various real-world scenarios that could cause crashes:
- Concurrent requests
- Rapid document changes
- Invalid input
- Edge cases
- Resource exhaustion
"""

import subprocess
import json
import time
import threading
import os
import sys
import random
import string

SERVER = "_build/default/jasmin-lsp/jasmin_lsp.exe"

class LSPClient:
    def __init__(self):
        self.proc = subprocess.Popen(
            [SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        self.msg_id = 0
        self.lock = threading.Lock()
        self.crashed = False
        
    def send_message(self, method, params=None, is_notification=False):
        """Send a JSON-RPC message to the server"""
        with self.lock:
            if self.proc.poll() is not None:
                self.crashed = True
                return None
            
            self.msg_id += 1
            msg = {
                "jsonrpc": "2.0",
                "method": method
            }
            
            if not is_notification:
                msg["id"] = self.msg_id
                
            if params is not None:
                msg["params"] = params
            
            msg_str = json.dumps(msg)
            content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
            
            try:
                self.proc.stdin.write(content.encode('utf-8'))
                self.proc.stdin.flush()
                return self.msg_id
            except:
                self.crashed = True
                return None
    
    def is_alive(self):
        """Check if server process is still running"""
        return self.proc.poll() is None and not self.crashed
    
    def get_stderr(self):
        """Get stderr output"""
        try:
            return self.proc.stderr.read().decode('utf-8', errors='replace')
        except:
            return ""
    
    def shutdown(self):
        """Gracefully shutdown the server"""
        try:
            self.proc.terminate()
            self.proc.wait(timeout=2)
        except:
            self.proc.kill()

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        
    def run_test(self, name, test_func):
        """Run a single test"""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print('='*60)
        self.tests_run += 1
        
        try:
            test_func()
            print(f"✓ PASSED: {name}")
            self.tests_passed += 1
            return True
        except AssertionError as e:
            print(f"✗ FAILED: {name}")
            print(f"  Error: {e}")
            self.tests_failed += 1
            return False
        except Exception as e:
            print(f"✗ ERROR: {name}")
            print(f"  Exception: {e}")
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            return False
    
    def summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print('='*60)
        print(f"Total: {self.tests_run}")
        print(f"Passed: {self.tests_passed} ✓")
        print(f"Failed: {self.tests_failed} ✗")
        print('='*60)
        
        if self.tests_failed == 0:
            print("ALL TESTS PASSED! 🎉")
            return 0
        else:
            print(f"SOME TESTS FAILED ({self.tests_failed}/{self.tests_run})")
            return 1


# =============================================================================
# TEST SCENARIOS
# =============================================================================

def test_basic_initialization():
    """Test basic server initialization doesn't crash"""
    client = LSPClient()
    
    try:
        # Initialize
        client.send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        })
        
        time.sleep(0.5)
        assert client.is_alive(), "Server crashed during initialization"
        
        # Send initialized notification
        client.send_message("initialized", {}, is_notification=True)
        
        time.sleep(0.5)
        assert client.is_alive(), "Server crashed after initialized"
        
    finally:
        client.shutdown()


def test_concurrent_requests():
    """Test multiple concurrent requests don't cause crashes"""
    client = LSPClient()
    
    try:
        # Initialize first
        client.send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        })
        time.sleep(0.5)
        client.send_message("initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        # Send multiple requests concurrently
        def send_hover_request():
            for _ in range(5):
                client.send_message("textDocument/hover", {
                    "textDocument": {"uri": "file:///tmp/test.jazz"},
                    "position": {"line": 0, "character": 0}
                })
                time.sleep(0.01)
        
        threads = []
        for _ in range(3):
            t = threading.Thread(target=send_hover_request)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        time.sleep(0.5)
        assert client.is_alive(), "Server crashed during concurrent requests"
        
    finally:
        client.shutdown()


def test_rapid_document_changes():
    """Test rapid document open/change/close doesn't crash"""
    client = LSPClient()
    
    try:
        # Initialize
        client.send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        })
        time.sleep(0.5)
        client.send_message("initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        # Rapidly open, change, and close documents
        for i in range(10):
            uri = f"file:///tmp/test{i}.jazz"
            
            # Open
            client.send_message("textDocument/didOpen", {
                "textDocument": {
                    "uri": uri,
                    "languageId": "jasmin",
                    "version": 1,
                    "text": "fn test() { }"
                }
            }, is_notification=True)
            
            # Change multiple times
            for v in range(2, 5):
                client.send_message("textDocument/didChange", {
                    "textDocument": {"uri": uri, "version": v},
                    "contentChanges": [{"text": f"fn test{v}() {{ }}"}]
                }, is_notification=True)
            
            # Close
            client.send_message("textDocument/didClose", {
                "textDocument": {"uri": uri}
            }, is_notification=True)
            
            time.sleep(0.05)
        
        time.sleep(0.5)
        assert client.is_alive(), "Server crashed during rapid document changes"
        
    finally:
        client.shutdown()


def test_invalid_json():
    """Test that malformed JSON doesn't crash the server"""
    client = LSPClient()
    
    try:
        # Initialize normally first
        client.send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        })
        time.sleep(0.5)
        client.send_message("initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        # Send invalid JSON (missing closing brace)
        invalid_content = 'Content-Length: 50\r\n\r\n{"jsonrpc": "2.0", "method": "test"'
        try:
            client.proc.stdin.write(invalid_content.encode('utf-8'))
            client.proc.stdin.flush()
        except:
            pass
        
        time.sleep(0.5)
        assert client.is_alive(), "Server crashed on invalid JSON"
        
        # Server should still be able to process valid requests
        client.send_message("textDocument/hover", {
            "textDocument": {"uri": "file:///tmp/test.jazz"},
            "position": {"line": 0, "character": 0}
        })
        
        time.sleep(0.5)
        assert client.is_alive(), "Server crashed after recovering from invalid JSON"
        
    finally:
        client.shutdown()


def test_invalid_utf8():
    """Test that invalid UTF-8 doesn't crash the server"""
    client = LSPClient()
    
    try:
        # Initialize
        client.send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        })
        time.sleep(0.5)
        client.send_message("initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        # Open document with invalid UTF-8 sequences
        client.send_message("textDocument/didOpen", {
            "textDocument": {
                "uri": "file:///tmp/invalid_utf8.jazz",
                "languageId": "jasmin",
                "version": 1,
                "text": "fn test() { /* \xff\xfe Invalid UTF-8 */ }"
            }
        }, is_notification=True)
        
        time.sleep(0.5)
        assert client.is_alive(), "Server crashed on invalid UTF-8"
        
    finally:
        client.shutdown()


def test_missing_required_file():
    """Test that references to missing files don't crash"""
    client = LSPClient()
    
    try:
        # Initialize
        client.send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        })
        time.sleep(0.5)
        client.send_message("initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        # Open document with require to non-existent file
        client.send_message("textDocument/didOpen", {
            "textDocument": {
                "uri": "file:///tmp/with_require.jazz",
                "languageId": "jasmin",
                "version": 1,
                "text": 'require "this_file_does_not_exist.jazz"\n\nfn test() { }'
            }
        }, is_notification=True)
        
        time.sleep(0.5)
        assert client.is_alive(), "Server crashed on missing required file"
        
        # Try to get definition on the require statement
        client.send_message("textDocument/definition", {
            "textDocument": {"uri": "file:///tmp/with_require.jazz"},
            "position": {"line": 0, "character": 10}
        })
        
        time.sleep(0.5)
        assert client.is_alive(), "Server crashed trying to resolve missing file"
        
    finally:
        client.shutdown()


def test_large_document():
    """Test that large documents don't cause crashes"""
    client = LSPClient()
    
    try:
        # Initialize
        client.send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        })
        time.sleep(0.5)
        client.send_message("initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        # Generate a large document (10000 lines)
        lines = []
        for i in range(10000):
            lines.append(f"fn function_{i}(x: u64) -> u64 {{ return x + {i}; }}")
        large_text = "\n".join(lines)
        
        client.send_message("textDocument/didOpen", {
            "textDocument": {
                "uri": "file:///tmp/large.jazz",
                "languageId": "jasmin",
                "version": 1,
                "text": large_text
            }
        }, is_notification=True)
        
        time.sleep(2.0)  # Give it time to parse
        assert client.is_alive(), "Server crashed on large document"
        
    finally:
        client.shutdown()


def test_syntax_errors():
    """Test that syntax errors don't crash the server"""
    client = LSPClient()
    
    try:
        # Initialize
        client.send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        })
        time.sleep(0.5)
        client.send_message("initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        # Various syntax errors
        syntax_errors = [
            "fn test( { }",  # Missing param
            "fn { }",  # Missing name
            "fn test() -> { }",  # Missing return type
            "fn test() { return; }",  # Incomplete return
            "[[[[[[[[[[",  # Unmatched brackets
            "fn test() { fn nested() { } }",  # Nested function (might be invalid)
        ]
        
        for i, text in enumerate(syntax_errors):
            client.send_message("textDocument/didOpen", {
                "textDocument": {
                    "uri": f"file:///tmp/error{i}.jazz",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": text
                }
            }, is_notification=True)
            
            time.sleep(0.1)
            assert client.is_alive(), f"Server crashed on syntax error: {text}"
        
    finally:
        client.shutdown()


def test_recursive_requires():
    """Test that circular require dependencies don't cause infinite loops"""
    client = LSPClient()
    
    try:
        # Initialize
        client.send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        })
        time.sleep(0.5)
        client.send_message("initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        # Open file A that requires B
        client.send_message("textDocument/didOpen", {
            "textDocument": {
                "uri": "file:///tmp/a.jazz",
                "languageId": "jasmin",
                "version": 1,
                "text": 'require "b.jazz"\nfn a() { }'
            }
        }, is_notification=True)
        
        # Open file B that requires A (circular)
        client.send_message("textDocument/didOpen", {
            "textDocument": {
                "uri": "file:///tmp/b.jazz",
                "languageId": "jasmin",
                "version": 1,
                "text": 'require "a.jazz"\nfn b() { }'
            }
        }, is_notification=True)
        
        time.sleep(0.5)
        assert client.is_alive(), "Server crashed on circular requires"
        
        # Try operations that traverse dependencies
        client.send_message("textDocument/definition", {
            "textDocument": {"uri": "file:///tmp/a.jazz"},
            "position": {"line": 1, "character": 3}
        })
        
        time.sleep(1.0)
        assert client.is_alive(), "Server hung/crashed on circular require traversal"
        
    finally:
        client.shutdown()


def test_null_and_boundary_values():
    """Test edge cases with null/empty values"""
    client = LSPClient()
    
    try:
        # Initialize
        client.send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": f"file://{os.getcwd()}",
            "capabilities": {}
        })
        time.sleep(0.5)
        client.send_message("initialized", {}, is_notification=True)
        time.sleep(0.5)
        
        # Empty document
        client.send_message("textDocument/didOpen", {
            "textDocument": {
                "uri": "file:///tmp/empty.jazz",
                "languageId": "jasmin",
                "version": 1,
                "text": ""
            }
        }, is_notification=True)
        
        time.sleep(0.3)
        assert client.is_alive(), "Server crashed on empty document"
        
        # Position at end of empty document
        client.send_message("textDocument/hover", {
            "textDocument": {"uri": "file:///tmp/empty.jazz"},
            "position": {"line": 0, "character": 0}
        })
        
        time.sleep(0.3)
        assert client.is_alive(), "Server crashed on hover at position 0,0 in empty doc"
        
        # Very large position values
        client.send_message("textDocument/hover", {
            "textDocument": {"uri": "file:///tmp/empty.jazz"},
            "position": {"line": 999999, "character": 999999}
        })
        
        time.sleep(0.3)
        assert client.is_alive(), "Server crashed on out-of-bounds position"
        
    finally:
        client.shutdown()


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run all crash tests"""
    if not os.path.exists(SERVER):
        print(f"ERROR: Server executable not found at {SERVER}")
        print("Please build the server first with: dune build")
        return 1
    
    runner = TestRunner()
    
    # Run all tests
    runner.run_test("Basic Initialization", test_basic_initialization)
    runner.run_test("Concurrent Requests", test_concurrent_requests)
    runner.run_test("Rapid Document Changes", test_rapid_document_changes)
    runner.run_test("Invalid JSON", test_invalid_json)
    runner.run_test("Invalid UTF-8", test_invalid_utf8)
    runner.run_test("Missing Required File", test_missing_required_file)
    runner.run_test("Large Document", test_large_document)
    runner.run_test("Syntax Errors", test_syntax_errors)
    runner.run_test("Recursive Requires", test_recursive_requires)
    runner.run_test("Null and Boundary Values", test_null_and_boundary_values)
    
    return runner.summary()


if __name__ == "__main__":
    sys.exit(main())
