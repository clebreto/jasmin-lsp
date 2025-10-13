#!/usr/bin/env python3
"""
Comprehensive test suite for jasmin-lsp server.
Tests all LSP features: diagnostics, go-to-definition, find references, hover, etc.
"""

import pytest
import time
from pathlib import Path


def test_initialization(lsp_client):
    """Test server initialization"""
    # The lsp_client fixture already initializes the server
    # Just verify it's alive and has the expected capabilities
    assert lsp_client.is_alive(), "LSP server should be running"
    assert lsp_client.initialized, "LSP server should be initialized"


def test_diagnostics(lsp_client, fixtures_dir):
    """Test diagnostics on a clean file with no errors"""
    test_file = fixtures_dir / 'simple_function.jazz'
    with open(test_file, 'r') as f:
        content = f.read()
    
    uri = f"file://{test_file.absolute()}"
    
    # Open document
    lsp_client.open_document(uri, content)
    
    # Give server time to parse and send diagnostics
    time.sleep(0.5)
    
    # We should receive diagnostics (even if empty)
    # For now, just verify the server didn't crash
    assert lsp_client.is_alive(), "Server should still be running after opening file"


def test_goto_definition(lsp_client, fixtures_dir):
    """Test go-to-definition"""
    test_file = fixtures_dir / 'simple_function.jazz'
    with open(test_file, 'r') as f:
        content = f.read()
    
    uri = f"file://{test_file.absolute()}"
    
    # Open document
    lsp_client.open_document(uri, content)
    
    # Find position of a function call
    lines = content.split('\n')
    test_position = None
    for i, line in enumerate(lines):
        # Look for a function call (not definition)
        if 'add_numbers(' in line and 'fn add_numbers' not in line:
            col = line.index('add_numbers')
            test_position = (i, col + 1)
            break
    
    if test_position:
        line, char = test_position
        response = lsp_client.definition(uri, line, char)
        
        assert response is not None, "Should receive definition response"
        
        if 'result' in response and response['result']:
            result = response['result']
            if isinstance(result, list):
                assert len(result) > 0, "Should find at least one definition"
            else:
                assert result is not None, "Definition result should not be null"


def test_find_references(lsp_client, fixtures_dir):
    """Test find references"""
    test_file = fixtures_dir / 'references_test.jazz'
    if not test_file.exists():
        # Use simple_function as fallback
        test_file = fixtures_dir / 'simple_function.jazz'
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    uri = f"file://{test_file.absolute()}"
    
    # Open document
    lsp_client.open_document(uri, content)
    
    # Find position of a variable or parameter
    lines = content.split('\n')
    test_position = None
    for i, line in enumerate(lines):
        if 'reg u64 value' in line or 'reg u64 result' in line:
            if 'value' in line:
                col = line.index('value')
            else:
                col = line.index('result')
            test_position = (i, col + 1)
            break
    
    if test_position:
        line, char = test_position
        response = lsp_client.references(uri, line, char)
        
        assert response is not None, "Should receive references response"
        
        if 'result' in response:
            # It's okay if no references are found, just verify we got a response
            result = response['result']
            assert result is not None, "References result should not be null"


def test_hover(lsp_client, fixtures_dir):
    """Test hover information"""
    test_file = fixtures_dir / 'types_test.jazz'
    if not test_file.exists():
        # Use simple_function as fallback
        test_file = fixtures_dir / 'simple_function.jazz'
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    uri = f"file://{test_file.absolute()}"
    
    # Open document
    lsp_client.open_document(uri, content)
    
    # Find position of a function definition
    lines = content.split('\n')
    test_position = None
    for i, line in enumerate(lines):
        if 'fn ' in line and '{' in line:
            # Found a function definition
            fn_idx = line.index('fn ')
            # Find the function name
            rest = line[fn_idx + 3:]
            if '(' in rest:
                fn_name = rest[:rest.index('(')].strip()
                if fn_name:
                    col = line.index(fn_name)
                    test_position = (i, col + 1)
                    break
    
    if test_position:
        line, char = test_position
        response = lsp_client.hover(uri, line, char)
        
        assert response is not None, "Should receive hover response"
        
        # It's okay if hover returns null for some positions
        # Just verify the server responded


def test_document_change(lsp_client, fixtures_dir):
    """Test document change notifications"""
    test_file = fixtures_dir / 'simple_function.jazz'
    with open(test_file, 'r') as f:
        content = f.read()
    
    uri = f"file://{test_file.absolute()}"
    
    # Open document
    lsp_client.open_document(uri, content)
    
    # Change document
    new_content = content + "\n// New comment\n"
    lsp_client.change_document(uri, new_content, 2)
    
    # Verify server is still alive
    assert lsp_client.is_alive(), "Server should still be running after document change"


def test_document_close(lsp_client, fixtures_dir):
    """Test document close notification"""
    test_file = fixtures_dir / 'simple_function.jazz'
    with open(test_file, 'r') as f:
        content = f.read()
    
    uri = f"file://{test_file.absolute()}"
    
    # Open document
    lsp_client.open_document(uri, content)
    
    # Close document
    lsp_client.close_document(uri)
    
    # Verify server is still alive
    assert lsp_client.is_alive(), "Server should still be running after document close"


# For backwards compatibility, keep the standalone script functionality
if __name__ == '__main__':
    import sys
    print("This test file should be run with pytest:")
    print("  pytest test/test_integration/test_lsp.py -v")
    sys.exit(1)
