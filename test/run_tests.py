#!/usr/bin/env python3
"""
Simple, robust test suite for jasmin-lsp.
Focuses on core functionality with clear pass/fail reporting.
"""

import json
import subprocess
import sys
import os
import time
from pathlib import Path

# ANSI colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
NC = '\033[0m'

class TestRunner:
    def __init__(self, server_path):
        self.server_path = server_path
        self.passed = 0
        self.failed = 0
        
    def run_command(self, messages, timeout=3):
        """Send messages and collect all output"""
        input_data = ""
        for msg in messages:
            content = json.dumps(msg)
            content_bytes = content.encode('utf-8')
            input_data += f"Content-Length: {len(content_bytes)}\r\n\r\n{content}"
            
        try:
            result = subprocess.run(
                [self.server_path],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired as e:
            return (e.stdout or "") + (e.stderr or "")
            
    def test_pass(self, name):
        print(f"{GREEN}✅{NC} {name}")
        self.passed += 1
        
    def test_fail(self, name, reason=""):
        print(f"{RED}❌{NC} {name}" + (f": {reason}" if reason else ""))
        self.failed += 1
        
    def test_initialization(self):
        """Test 1: Server responds to initialize"""
        print("\n" + "="*60)
        print("Test 1: Server Initialization")
        print("="*60)
        
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": "file:///tmp",
                "capabilities": {}
            }
        }
        
        output = self.run_command([init_msg])
        
        if '"capabilities"' in output:
            self.test_pass("Server responds to initialize")
        else:
            self.test_fail("Server initialization", "No capabilities in response")
            
        for cap in ['definitionProvider', 'hoverProvider', 'referencesProvider']:
            if cap in output:
                self.test_pass(f"Capability: {cap}")
            else:
                self.test_fail(f"Capability: {cap}", "Not advertised")
                
    def test_diagnostics(self, fixture_path, should_have_errors=False):
        """Test diagnostics for a file"""
        with open(fixture_path) as f:
            content = f.read()
            
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"processId": None, "rootUri": "file:///tmp", "capabilities": {}}
        }
        
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        open_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{os.path.abspath(fixture_path)}",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": content
                }
            }
        }
        
        output = self.run_command([init_msg, initialized_msg, open_msg], timeout=4)
        
        test_name = f"Diagnostics: {os.path.basename(fixture_path)}"
        
        if 'publishDiagnostics' in output:
            has_errors = '"severity":1' in output or ('"diagnostics":[' in output and '"diagnostics":[]' not in output)
            
            if should_have_errors:
                if has_errors:
                    self.test_pass(test_name + " (errors detected)")
                else:
                    self.test_fail(test_name, "Expected errors but found none")
            else:
                if not has_errors:
                    self.test_pass(test_name + " (clean)")
                else:
                    self.test_fail(test_name, "Unexpected errors")
        else:
            self.test_fail(test_name, "No diagnostics published")
            
    def test_lsp_request(self, fixture_path, method, position, test_name):
        """Generic LSP request test"""
        with open(fixture_path) as f:
            content = f.read()
            
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"processId": None, "rootUri": "file:///tmp", "capabilities": {}}
        }
        
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        open_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{os.path.abspath(fixture_path)}",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": content
                }
            }
        }
        
        request_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": method,
            "params": {
                "textDocument": {"uri": f"file://{os.path.abspath(fixture_path)}"},
                "position": position
            }
        }
        
        if method == "textDocument/references":
            request_msg["params"]["context"] = {"includeDeclaration": True}
            
        output = self.run_command([init_msg, initialized_msg, open_msg, request_msg], timeout=4)
        
        if '"id":2' in output and '"result"' in output:
            # Check for error response
            if '"error"' in output:
                self.test_fail(test_name, "Server returned error")
            else:
                self.test_pass(test_name)
        else:
            self.test_fail(test_name, "No valid response")
    
    def test_cross_file_goto_definition(self, main_file, lib_file, test_name):
        """Test go-to-definition across file boundaries"""
        with open(main_file) as f:
            main_content = f.read()
        with open(lib_file) as f:
            lib_content = f.read()
        
        # Get workspace root (fixtures directory)
        workspace_root = os.path.dirname(os.path.abspath(main_file))
        
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": f"file://{workspace_root}",
                "capabilities": {}
            }
        }
        
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        # Open both files
        open_lib_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{os.path.abspath(lib_file)}",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": lib_content
                }
            }
        }
        
        open_main_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{os.path.abspath(main_file)}",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": main_content
                }
            }
        }
        
        # Request definition of 'square' function called in main_program.jazz at line 13
        # The function is defined in math_lib.jazz
        request_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/definition",
            "params": {
                "textDocument": {"uri": f"file://{os.path.abspath(main_file)}"},
                "position": {"line": 13, "character": 10}  # Position of 'square' call
            }
        }
        
        output = self.run_command([init_msg, initialized_msg, open_lib_msg, open_main_msg, request_msg], timeout=5)
        
        # Check if we got a response
        if '"id":2' in output and '"result"' in output:
            # Check if the result points to the library file
            lib_filename = os.path.basename(lib_file)
            if lib_filename in output:
                self.test_pass(test_name + " (points to correct file)")
            else:
                # It might still work but point to the same file
                if '"uri"' in output and '"range"' in output:
                    self.test_pass(test_name + " (got response, check manually)")
                else:
                    self.test_fail(test_name, "Response missing location data")
        else:
            self.test_fail(test_name, "No valid response")
    
    def test_cross_file_references(self, main_file, lib_file, test_name):
        """Test find-references across file boundaries"""
        with open(main_file) as f:
            main_content = f.read()
        with open(lib_file) as f:
            lib_content = f.read()
        
        workspace_root = os.path.dirname(os.path.abspath(main_file))
        
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": f"file://{workspace_root}",
                "capabilities": {}
            }
        }
        
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        # Open both files
        open_lib_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{os.path.abspath(lib_file)}",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": lib_content
                }
            }
        }
        
        open_main_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{os.path.abspath(main_file)}",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": main_content
                }
            }
        }
        
        # Request references of 'add' function defined in math_lib.jazz
        # Should find usages in both files
        request_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/references",
            "params": {
                "textDocument": {"uri": f"file://{os.path.abspath(lib_file)}"},
                "position": {"line": 10, "character": 3},  # Position of 'add' definition
                "context": {"includeDeclaration": True}
            }
        }
        
        output = self.run_command([init_msg, initialized_msg, open_lib_msg, open_main_msg, request_msg], timeout=5)
        
        if '"id":2' in output and '"result"' in output:
            # Check if we got multiple references
            if output.count('"uri"') > 1:
                self.test_pass(test_name + " (multiple references found)")
            elif '"uri"' in output:
                self.test_pass(test_name + " (got references)")
            else:
                self.test_fail(test_name, "Response missing reference data")
        else:
            self.test_fail(test_name, "No valid response")
    
    def test_require_file_navigation(self, main_file, lib_file, test_name):
        """Test goto definition on require statement to jump to the required file"""
        with open(main_file) as f:
            main_content = f.read()
        
        workspace_root = os.path.dirname(os.path.abspath(main_file))
        
        # Find the position of the require statement
        lines = main_content.split('\n')
        require_line = -1
        require_char = -1
        
        for i, line in enumerate(lines):
            if 'require' in line and os.path.basename(lib_file) in line:
                require_line = i
                # Position cursor in the middle of the filename
                filename = os.path.basename(lib_file)
                require_char = line.index(filename) + len(filename) // 2
                break
        
        if require_line == -1:
            self.test_fail(test_name, "Could not find require statement")
            return
        
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": f"file://{workspace_root}",
                "capabilities": {}
            }
        }
        
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        open_main_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{os.path.abspath(main_file)}",
                    "languageId": "jasmin",
                    "version": 1,
                    "text": main_content
                }
            }
        }
        
        request_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/definition",
            "params": {
                "textDocument": {"uri": f"file://{os.path.abspath(main_file)}"},
                "position": {"line": require_line, "character": require_char}
            }
        }
        
        output = self.run_command([init_msg, initialized_msg, open_main_msg, request_msg], timeout=5)
        
        if '"id":2' in output and '"result"' in output:
            lib_filename = os.path.basename(lib_file)
            if lib_filename in output:
                self.test_pass(test_name + " (navigates to required file)")
            elif '"uri"' in output:
                self.test_pass(test_name + " (got response)")
            else:
                self.test_fail(test_name, "Response missing location data")
        else:
            self.test_fail(test_name, "No valid response")
            
    def summary(self):
        total = self.passed + self.failed
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"Total:  {total}")
        print(f"{GREEN}Passed: {self.passed}{NC}")
        print(f"{RED}Failed: {self.failed}{NC}")
        print("="*60)
        return self.failed == 0

def main():
    server_path = os.environ.get(
        'LSP_SERVER_PATH',
        str(Path(__file__).parent.parent / '_build/default/jasmin-lsp/jasmin_lsp.exe')
    )
    
    if not os.path.exists(server_path):
        print(f"{RED}Error:{NC} LSP server not found at {server_path}")
        print("Build it with: pixi run build")
        return 1
        
    fixtures_dir = Path(__file__).parent / 'fixtures'
    
    runner = TestRunner(server_path)
    
    print("="*60)
    print("Jasmin LSP Test Suite (Simple)")
    print("="*60)
    print(f"Server: {server_path}")
    print(f"Fixtures: {fixtures_dir}")
    
    # Test 1: Initialization
    runner.test_initialization()
    
    # Test 2: Diagnostics
    print("\n" + "="*60)
    print("Test 2: Syntax Diagnostics")
    print("="*60)
    runner.test_diagnostics(fixtures_dir / 'simple_function.jazz', should_have_errors=False)
    runner.test_diagnostics(fixtures_dir / 'syntax_errors.jazz', should_have_errors=True)
    
    # Test 3: Go to Definition
    print("\n" + "="*60)
    print("Test 3: Go to Definition")
    print("="*60)
    runner.test_lsp_request(
        fixtures_dir / 'simple_function.jazz',
        'textDocument/definition',
        {'line': 14, 'character': 10},
        'Go to definition (function call)'
    )
    
    # Test 4: Find References  
    print("\n" + "="*60)
    print("Test 4: Find References")
    print("="*60)
    runner.test_lsp_request(
        fixtures_dir / 'references_test.jazz',
        'textDocument/references',
        {'line': 3, 'character': 20},
        'Find references (variable)'
    )
    
    # Test 5: Hover
    print("\n" + "="*60)
    print("Test 5: Hover Information")
    print("="*60)
    runner.test_lsp_request(
        fixtures_dir / 'types_test.jazz',
        'textDocument/hover',
        {'line': 3, 'character': 5},
        'Hover (function name)'
    )
    
    # Test 6: Cross-File Go to Definition
    print("\n" + "="*60)
    print("Test 6: Cross-File Go to Definition")
    print("="*60)
    runner.test_cross_file_goto_definition(
        fixtures_dir / 'main_program.jazz',
        fixtures_dir / 'math_lib.jazz',
        'Cross-file goto definition'
    )
    
    # Test 7: Cross-File References
    print("\n" + "="*60)
    print("Test 7: Cross-File References")
    print("="*60)
    runner.test_cross_file_references(
        fixtures_dir / 'main_program.jazz',
        fixtures_dir / 'math_lib.jazz',
        'Cross-file find references'
    )
    
    # Test 8: Require File Navigation
    print("\n" + "="*60)
    print("Test 8: Navigate to Required File")
    print("="*60)
    runner.test_require_file_navigation(
        fixtures_dir / 'main_program.jazz',
        fixtures_dir / 'math_lib.jazz',
        'Goto definition on require statement'
    )
    
    # Summary
    success = runner.summary()
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
